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
        self.assertEqual(len(list(self.file.parent.glob("morsetrainer.db.defekt-*"))), 1)

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


if __name__ == "__main__":
    unittest.main()
