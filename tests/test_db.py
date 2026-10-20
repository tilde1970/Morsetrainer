"""Tests für die Datenbank (core/db.py): Zustände, Durchgänge, Ergebnisse,
Transaktionen, kaputte Dateien und zwei Fenster gleichzeitig."""
import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import db


def _config(start: str, mode="single", **extra) -> dict:
    return {"type": "config", "mode": mode, "start_time": start, "wpm": 20, **extra}


class DbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.file = self.dir / "stats" / "morsetrainer.db"
        db.use(self.file)

    def tearDown(self):
        db.use(None)
        self.tmp.cleanup()

    # --- Zustände ------------------------------------------------------------

    def test_state_roundtrip_and_overwrite(self):
        self.assertEqual(db.load_state("daily", {}), {})
        db.save_state("daily", {"days": {"2026-10-03": {"done": True}}, "ä": "ö"})
        db.save_state("daily", {"days": {}})
        self.assertEqual(db.load_state("daily", {}), {"days": {}})
        self.assertTrue(self.file.exists())  # Ordner stats/ wird angelegt

    def test_state_of_wrong_type_is_set_aside(self):
        db.save_state("review", [1, 2])
        self.assertEqual(db.load_state("review", {}), {})
        keys = [k for (k,) in db._read("SELECT key FROM state")]
        self.assertEqual(len(keys), 1)
        self.assertTrue(keys[0].startswith("review.defekt-"))

    def test_unreadable_state_is_set_aside(self):
        db._write("INSERT INTO state (key, data) VALUES ('awards', '{\"seals\": ')")
        self.assertEqual(db.load_state("awards", {}), {})
        self.assertEqual(db.load_state("awards", {"x": 1}), {"x": 1})

    def test_delete_state(self):
        db.save_state("all_time", {"K": {"good": 1}})
        db.delete_state("all_time")
        self.assertEqual(db.load_state("all_time", {}), {})

    # --- Durchgänge ----------------------------------------------------------

    def test_session_with_events_and_summary(self):
        sid = db.start_session(_config("2026-10-03T10:00:00"))
        db.add_event(sid, {"type": "char", "char": "K", "typed": "K", "correct": True})
        db.add_event(sid, {"type": "group", "sent": "KM", "typed": "KN"})
        db.finish_session(sid, {"type": "summary", "total": 1, "correct": 1})
        [session] = db.sessions(events=True)
        self.assertEqual(session.id, sid)
        self.assertEqual(session.config["wpm"], 20)
        self.assertEqual(session.summary["total"], 1)
        self.assertEqual([e["type"] for e in session.events], ["char", "group"])
        self.assertEqual(db.session_events(sid), session.events)

    def test_unfinished_session_has_no_summary(self):
        sid = db.start_session(_config("2026-10-03T10:00:00"))
        db.add_event(sid, {"type": "char", "char": "E", "correct": False})
        [session] = db.sessions()
        self.assertIsNone(session.summary)
        self.assertIsNone(session.events)  # nur auf Wunsch mitgelesen

    def test_filter_by_day_time_and_mode(self):
        for start, mode in (("2026-09-30T23:59:59", "single"), ("2026-10-01T00:00:00", "group"),
                            ("2026-10-02T12:00:00", "single"), ("2026-10-03T08:00:00", "single")):
            db.start_session(_config(start, mode))

        def starts(**kw):
            return [s.config["start_time"] for s in db.sessions(**kw)]

        self.assertEqual(starts(since=date(2026, 10, 1), until=date(2026, 10, 2)),
                         ["2026-10-01T00:00:00", "2026-10-02T12:00:00"])
        self.assertEqual(starts(since=datetime(2026, 10, 2, 12, 0, 1)), ["2026-10-03T08:00:00"])
        self.assertEqual(starts(until=date(2026, 9, 30)), ["2026-09-30T23:59:59"])
        self.assertEqual(starts(mode="group"), ["2026-10-01T00:00:00"])

    def test_sessions_sorted_by_start_time(self):
        db.start_session(_config("2026-10-03T12:00:00"))
        db.start_session(_config("2026-10-03T08:00:00"))
        self.assertEqual([s.config["start_time"] for s in db.sessions()],
                         ["2026-10-03T08:00:00", "2026-10-03T12:00:00"])

    def test_delete_session_removes_events(self):
        sid = db.start_session(_config("2026-10-03T10:00:00"))
        db.add_event(sid, {"type": "char", "char": "K"})
        db.delete_session(sid)
        self.assertEqual(db.sessions(), [])
        self.assertEqual(db._read("SELECT COUNT(*) FROM events"), [(0,)])

    def test_unreadable_rows_are_skipped(self):
        sid = db.start_session(_config("2026-10-03T10:00:00"))
        db.add_event(sid, {"type": "char", "char": "K"})
        db._write("INSERT INTO events (session_id, type, data) VALUES (?, 'char', '{\"char\": ')", (sid,))
        db._write("INSERT INTO sessions (start_time, mode, config) VALUES ('2026-10-03T11:00:00', 'x', 'kaputt')")
        sessions = db.sessions(events=True)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].events, [{"type": "char", "char": "K"}])

    def test_many_sessions_with_events(self):
        with db.transaction():
            for i in range(1200):
                sid = db.start_session(_config(f"2026-10-03T10:{i // 60 % 60:02d}:{i % 60:02d}"))
                db.add_event(sid, {"type": "char", "n": i})
        sessions = db.sessions(events=True)
        self.assertEqual(len(sessions), 1200)
        self.assertTrue(all(len(s.events) == 1 for s in sessions))

    # --- Ergebnisse und Verwaltung -------------------------------------------

    def test_finished_sessions_are_read_once(self):
        # Abgeschlossene Durchgänge kommen beim zweiten Mal aus dem
        # Zwischenspeicher; laufende werden jedes Mal neu gelesen.
        done = db.start_session(_config("2026-10-01T19:00:00"))
        db.finish_session(done, {"type": "summary", "total": 5})
        running = db.start_session(_config("2026-10-02T19:00:00"))
        self.assertEqual([s.summary for s in db.sessions()], [{"type": "summary", "total": 5}, None])
        with mock.patch.object(db, "_load", side_effect=db._load) as load:
            db.sessions()
        self.assertEqual(load.call_count, 1)  # nur die config des laufenden
        db.finish_session(running, {"type": "summary", "total": 7})
        self.assertEqual([s.summary["total"] for s in db.sessions()], [5, 7])

    def test_cache_follows_file_and_rollback(self):
        first = db.start_session(_config("2026-10-01T19:00:00"))
        db.finish_session(first, {"type": "summary", "total": 5})
        db.sessions()
        # Eine andere Datei (Import, Tests): dieselbe id meint dort etwas anderes.
        db.use(self.dir / "andere.db")
        other = db.start_session(_config("2026-10-01T20:00:00", mode="group"))
        db.finish_session(other, {"type": "summary", "total": 9})
        self.assertEqual(other, first)
        self.assertEqual([(s.config["mode"], s.summary["total"]) for s in db.sessions()], [("group", 9)])
        # Verworfener Abschluss bleibt verworfen, auch wenn er gelesen wurde.
        running = db.start_session(_config("2026-10-02T19:00:00"))
        with self.assertRaises(RuntimeError):
            with db.transaction():
                db.finish_session(running, {"type": "summary", "total": 1})
                self.assertEqual(db.sessions()[-1].summary["total"], 1)
                raise RuntimeError
        self.assertIsNone(db.sessions()[-1].summary)

    def test_deleted_id_reused_by_new_session(self):
        first = db.start_session(_config("2026-10-01T19:00:00"))
        db.add_event(first, {"type": "char", "char": "A"})
        db.sessions()
        db.delete_session(first)
        again = db.start_session(_config("2026-10-02T19:00:00", mode="word"))
        db.finish_session(again, {"type": "summary", "total": 3})
        self.assertEqual([s.config["mode"] for s in db.sessions()], ["word"])

    def test_results_in_order(self):
        db.add_result({"time": "2026-10-03T10:00:00", "mode": "qso_quiz", "correct": 3})
        db.add_result({"time": "2026-10-02T10:00:00", "mode": "contest", "score": 7})
        self.assertEqual([r["mode"] for r in db.results()], ["qso_quiz", "contest"])

    def test_meta(self):
        self.assertIsNone(db.get_meta("migrated"))
        db.set_meta("migrated", "2026-10-03T10:00:00")
        db.set_meta("migrated", "2026-10-04T10:00:00")
        self.assertEqual(db.get_meta("migrated"), "2026-10-04T10:00:00")

    # --- Transaktionen -------------------------------------------------------

    def test_transaction_rolls_back_together(self):
        sid = db.start_session(_config("2026-10-03T10:00:00"))
        with self.assertRaises(RuntimeError):
            with db.transaction():
                db.finish_session(sid, {"total": 1})
                with db.transaction():  # verschachtelt
                    db.save_state("all_time", {"K": {"good": 1}})
                raise RuntimeError("Absturz mittendrin")
        self.assertIsNone(db.sessions()[0].summary)
        self.assertEqual(db.load_state("all_time", {}), {})
        # Danach geht es normal weiter.
        db.save_state("all_time", {"K": {"good": 2}})
        self.assertEqual(db.load_state("all_time", {}), {"K": {"good": 2}})

    def test_failed_write_inside_transaction_rolls_back(self):
        db.save_state("practice", {"2026-10-03": 60.0})
        with self.assertRaises(KeyError):
            with db.transaction():
                db.save_state("practice", {"2026-10-03": 120.0})
                db.start_session({"mode": "single"})  # ohne start_time
        self.assertEqual(db.load_state("practice", {}), {"2026-10-03": 60.0})

    # --- Datei und Verbindung ------------------------------------------------

    def test_data_survives_reopen(self):
        db.save_state("practice", {"2026-10-03": 60.0})
        db.close()
        self.assertEqual(db.load_state("practice", {}), {"2026-10-03": 60.0})

    def test_broken_file_is_set_aside(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b"das ist keine Datenbank, nur Text " * 200)
        db.close()
        self.assertEqual(db.load_state("daily", {}), {})
        db.save_state("daily", {"days": {}})
        self.assertEqual(db.load_state("daily", {}), {"days": {}})
        self.assertEqual(len(list(self.file.parent.glob("morsetrainer.db.defekt-*[0-9]"))), 1)

    def test_journal_of_a_broken_file_goes_with_it(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b"das ist keine Datenbank, nur Text " * 200)
        wal = self.file.with_name(self.file.name + "-wal")
        wal.write_bytes(b"altes Journal")
        self.file.with_name(self.file.name + "-shm").write_bytes(b"index")
        db.close()
        db.save_state("daily", {"days": {}})
        aside = list(self.file.parent.glob("morsetrainer.db.defekt-*-wal"))
        self.assertEqual([p.read_bytes() for p in aside], [b"altes Journal"])
        self.assertEqual(db.load_state("daily", {}), {"days": {}})
        self.assertFalse(self.file.with_name(self.file.name + "-shm").read_bytes() == b"index"
                         if self.file.with_name(self.file.name + "-shm").exists() else False)

    def test_locked_file_is_not_set_aside(self):
        db.save_state("daily", {"days": {}})
        db.close()
        with mock.patch.object(db, "_open", side_effect=sqlite3.OperationalError("database is locked")):
            self.assertEqual(db.load_state("daily", {}), {})
            with self.assertRaises(db.Error):
                db.save_state("daily", {"days": {"x": 1}})
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        self.assertEqual(db.load_state("daily", {}), {"days": {}})

    def test_folder_not_creatable(self):
        blocker = self.dir / "datei"
        blocker.write_text("x", encoding="utf-8")
        db.use(blocker / "stats" / "morsetrainer.db")
        self.assertEqual(db.load_state("daily", {}), {})
        self.assertEqual(db.sessions(), [])
        with self.assertRaises(OSError):
            db.save_state("daily", {})

    def test_two_windows_write_the_same_file(self):
        db.save_state("practice", {})
        other = db._open(self.file)  # zweites Programmfenster
        try:
            other.execute("INSERT INTO results (time, mode, data) VALUES ('2026-10-03T10:00:00', 'contest', '{}')")
            sid = db.start_session(_config("2026-10-03T10:00:00"))
            db.add_event(sid, {"type": "char", "char": "K"})
            self.assertEqual(other.execute("SELECT COUNT(*) FROM events").fetchone(), (1,))
            self.assertEqual(len(db.results()), 1)
        finally:
            other.close()

    def test_wal_mode(self):
        db.save_state("x", {})
        self.assertEqual(db._read("PRAGMA journal_mode"), [("wal",)])
        self.assertEqual(db._read("PRAGMA user_version"), [(db.SCHEMA_VERSION,)])

    def test_too_new_tells_a_newer_file_from_a_normal_one(self):
        self.assertFalse(db.too_new())
        db.close()
        raw = sqlite3.connect(self.file)
        raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        raw.close()
        self.assertTrue(db.too_new())

    def test_newer_schema_is_refused_and_untouched(self):
        db.save_state("daily", {"days": {}})
        db.close()
        raw = sqlite3.connect(self.file)
        raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        raw.close()
        self.assertEqual(db.load_state("daily", {}), {})
        with self.assertRaises(db.SchemaTooNew):
            db.save_state("daily", {"days": {"x": 1}})
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        raw = sqlite3.connect(self.file)
        self.assertEqual(raw.execute("SELECT data FROM state").fetchone(), ('{"days": {}}',))
        raw.close()

    def test_migration_runs_stepwise_with_copy(self):
        db.save_state("daily", {"days": {}})
        db.close()
        raw = sqlite3.connect(self.file)
        raw.execute("PRAGMA user_version = 1")
        raw.close()
        steps = []

        def step(conn):
            steps.append(1)
            conn.execute("CREATE TABLE neu (x INTEGER)")
        with mock.patch.object(db, "SCHEMA_VERSION", 2), mock.patch.dict(db.MIGRATIONS, {1: step}):
            self.assertEqual(db.load_state("daily", {}), {"days": {}})
            self.assertEqual(db._read("PRAGMA user_version"), [(2,)])
            self.assertEqual(db._read("SELECT COUNT(*) FROM neu"), [(0,)])
        self.assertEqual(steps, [1])
        self.assertTrue(self.file.with_name("morsetrainer.db.vor-v1").is_file())

    def test_failed_migration_step_keeps_old_state(self):
        db.save_state("daily", {"days": {}})
        db.close()

        def step(conn):
            conn.execute("CREATE TABLE neu (x INTEGER)")
            raise sqlite3.OperationalError("kaputt")
        with mock.patch.object(db, "SCHEMA_VERSION", 2), mock.patch.dict(db.MIGRATIONS, {1: step}):
            with self.assertRaises(db.Error):
                db.save_state("daily", {"days": {"x": 1}})
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        db.close()
        raw = sqlite3.connect(self.file)
        self.assertEqual(raw.execute("PRAGMA user_version").fetchone(), (1,))
        self.assertEqual(raw.execute("SELECT name FROM sqlite_master WHERE name = 'neu'").fetchall(), [])
        raw.close()

    def migrate_with(self, step, version=2):
        """Öffnet die Datenbank mit `step` als Migration von Schema 1."""
        return (mock.patch.object(db, "SCHEMA_VERSION", version), mock.patch.dict(db.MIGRATIONS, {1: step}))

    def old_database(self, **state):
        """Datenbank im Schema 1 mit Zuständen; danach geschlossen."""
        for key, value in state.items():
            db.save_state(key, value)
        db.close()

    def test_every_version_has_a_migration_step(self):
        self.assertEqual(set(db.MIGRATIONS), set(range(1, db.SCHEMA_VERSION)))

    def test_constraint_error_in_a_step_does_not_set_the_file_aside(self):
        # Ein IntegrityError ist eine DatabaseError: Er darf die gesunde Datei
        # nicht zur „kaputten“ machen, die beiseitegelegt wird.
        self.old_database(daily={"days": {}})

        def step(conn):
            conn.execute("CREATE TABLE neu (x INTEGER NOT NULL)")
            conn.execute("INSERT INTO neu VALUES (NULL)")
        patches = self.migrate_with(step)
        with patches[0], patches[1]:
            with self.assertRaises(db.MigrationError):
                db.save_state("daily", {"days": {"x": 1}})
            with self.assertRaises(db.Error):
                db._connection()  # auch beim nächsten Versuch: nicht beiseitegelegt
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        db.close()
        raw = sqlite3.connect(self.file)
        self.assertEqual(raw.execute("PRAGMA user_version").fetchone(), (1,))
        self.assertEqual(raw.execute("SELECT data FROM state").fetchone(), ('{"days": {}}',))
        raw.close()

    def test_missing_step_is_a_migration_error_and_leaves_the_file(self):
        self.old_database(daily={"days": {}})
        with mock.patch.object(db, "SCHEMA_VERSION", 2), mock.patch.dict(db.MIGRATIONS, {}, clear=True):
            with self.assertRaises(db.MigrationError):
                db.save_state("daily", {})
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        db.close()
        self.assertEqual(db.load_state("daily", {}), {"days": {}})

    def test_overlapping_migration_runs_the_step_once(self):
        # Zwei Programmfenster öffnen dieselbe alte Datei fast gleichzeitig:
        # Der Schritt läuft einmal, das zweite Fenster wartet und übernimmt.
        import threading
        import time
        self.old_database(daily={"days": {}})
        calls, errors, results = [], [], {}

        def step(conn):
            calls.append(1)
            time.sleep(0.8)
            conn.execute("CREATE TABLE neu (x INTEGER)")

        def open_window(name):
            try:
                conn = db._open(self.file)
                results[name] = conn.execute("PRAGMA user_version").fetchone()[0]
                conn.close()
            except Exception as exc:  # noqa: BLE001 (der Test meldet jeden)
                errors.append((name, repr(exc)))
        patches = self.migrate_with(step)
        with patches[0], patches[1]:
            first = threading.Thread(target=open_window, args=("a",))
            first.start()
            time.sleep(0.3)
            open_window("b")
            first.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(results, {"a": 2, "b": 2})
        # Die Kopie hält den Stand vor dem Schritt.
        copy = sqlite3.connect(self.file.with_name("morsetrainer.db.vor-v1"))
        self.assertEqual(copy.execute("SELECT name FROM sqlite_master WHERE name = 'neu'").fetchall(), [])
        self.assertEqual(copy.execute("PRAGMA user_version").fetchone(), (1,))
        copy.close()

    def test_copy_before_migration_replaces_an_older_one_without_leftovers(self):
        self.old_database(daily={"days": {"neu": 1}})
        old_copy = self.file.with_name("morsetrainer.db.vor-v1")
        raw = sqlite3.connect(old_copy)
        raw.execute("CREATE TABLE alt (x)")
        raw.close()
        patches = self.migrate_with(lambda conn: None)
        with patches[0], patches[1]:
            self.assertEqual(db.load_state("daily", {}), {"days": {"neu": 1}})
        copy = sqlite3.connect(old_copy)
        self.assertEqual(copy.execute("SELECT data FROM state").fetchone(), ('{"days": {"neu": 1}}',))
        self.assertEqual(copy.execute("SELECT name FROM sqlite_master WHERE name = 'alt'").fetchall(), [])
        copy.close()
        self.assertEqual(list(self.file.parent.glob("*.tmp")), [])

    def test_failed_copy_keeps_the_old_copy_and_the_file(self):
        self.old_database(daily={"days": {}})
        old_copy = self.file.with_name("morsetrainer.db.vor-v1")
        raw = sqlite3.connect(old_copy)
        raw.execute("CREATE TABLE alt (x)")
        raw.close()
        patches = self.migrate_with(lambda conn: None)
        real = sqlite3.connect

        def connect(target, *args, **kwargs):
            if str(target).endswith(".vor-v1.tmp"):  # Platte voll beim Anlegen der Kopie
                raise sqlite3.OperationalError("database or disk is full")
            return real(target, *args, **kwargs)
        with patches[0], patches[1], mock.patch.object(db.sqlite3, "connect", connect):
            with self.assertRaises(db.MigrationError):
                db.save_state("daily", {})
        raw = sqlite3.connect(old_copy)
        self.assertEqual(raw.execute("SELECT name FROM sqlite_master WHERE name = 'alt'").fetchall(), [("alt",)])
        raw.close()
        self.assertEqual(list(self.file.parent.glob("*.defekt-*")), [])
        db.close()
        raw = sqlite3.connect(self.file)
        self.assertEqual(raw.execute("PRAGMA user_version").fetchone(), (1,))
        raw.close()

    def test_newer_schema_keeps_the_journal_mode(self):
        self.old_database(daily={"days": {}})
        raw = sqlite3.connect(self.file)
        raw.execute("PRAGMA journal_mode = DELETE")
        raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        raw.close()
        before = self.file.read_bytes()[:100]
        with self.assertRaises(db.SchemaTooNew):
            db._connection()
        db.close()
        self.assertEqual(self.file.read_bytes()[:100], before)  # Kopfbytes 18/19: Journal-Modus

    def test_close_empties_the_wal(self):
        db.save_state("x", {"a": 1})
        db.close()
        wal = self.file.with_name(self.file.name + "-wal")
        self.assertFalse(wal.exists() and wal.stat().st_size > 0)

    def test_network_drive_uses_classic_journal(self):
        db.close()
        with mock.patch.object(db, "_on_network_drive", return_value=True):
            db.save_state("x", {})
            self.assertEqual(db._read("PRAGMA journal_mode"), [("delete",)])
        db.close()
        db.save_state("x", {})  # wieder lokal: zurück auf WAL
        self.assertEqual(db._read("PRAGMA journal_mode"), [("wal",)])

    def test_network_drive_detection(self):
        mounts = "srv:/home /home nfs4 rw 0 0\n/dev/sda1 / ext4 rw 0 0\n"
        with mock.patch("builtins.open", mock.mock_open(read_data=mounts)):
            self.assertTrue(db._on_network_drive(Path("/home/x/stats/m.db")))
            self.assertFalse(db._on_network_drive(Path("/opt/m.db")))

    def test_network_drive_detection_decodes_escapes_and_new_types(self):
        mounts = ("/dev/sda1 / ext4 rw 0 0\n"
                  "share /media/a\\040b\\011c vboxsf rw 0 0\n"
                  "gvfsd-fuse /run/user/1000/gvfs fuse.gvfsd-fuse rw 0 0\n"
                  "tag /mnt/vm virtiofs rw 0 0\n")
        with mock.patch("builtins.open", mock.mock_open(read_data=mounts)):
            self.assertTrue(db._on_network_drive(Path("/media/a b\tc/stats/m.db")))
            self.assertTrue(db._on_network_drive(Path("/run/user/1000/gvfs/x/m.db")))
            self.assertTrue(db._on_network_drive(Path("/mnt/vm/m.db")))
            self.assertFalse(db._on_network_drive(Path("/media/a/m.db")))  # nicht der Punkt „a b<Tab>c“

    def test_network_drive_detection_on_macos(self):
        out = ("/dev/disk3s1s1 on / (apfs, sealed, local, read-only, journaled)\n"
               "//nutzer@nas/freigabe on /Volumes/freigabe (smbfs, nodev, nosuid, mounted by nutzer)\n"
               "srv:/export on /Volumes/nfs dir (nfs, nodev, nosuid)\n")
        with mock.patch.object(db.sys, "platform", "darwin"), \
                mock.patch.object(db.subprocess, "Popen",
                                  return_value=mock.Mock(communicate=mock.Mock(return_value=(out, None)))):
            self.assertTrue(db._on_network_drive(Path("/Volumes/freigabe/stats/m.db")))
            self.assertTrue(db._on_network_drive(Path("/Volumes/nfs dir/m.db")))
            self.assertFalse(db._on_network_drive(Path("/Users/x/m.db")))

    def test_network_drive_detection_survives_a_failing_mount_command(self):
        with mock.patch.object(db.sys, "platform", "darwin"), \
                mock.patch.object(db.subprocess, "Popen", side_effect=FileNotFoundError("mount")):
            self.assertFalse(db._on_network_drive(Path("/Users/x/m.db")))

    def test_hanging_mount_command_is_killed_and_not_waited_for(self):
        proc = mock.Mock(communicate=mock.Mock(side_effect=db.subprocess.TimeoutExpired("mount", 3)))
        with mock.patch.object(db.sys, "platform", "darwin"), \
                mock.patch.object(db.subprocess, "Popen", return_value=proc):
            self.assertFalse(db._on_network_drive(Path("/Users/x/m.db")))
        proc.kill.assert_called_once()
        proc.wait.assert_not_called()


if __name__ == "__main__":
    unittest.main()
