"""Sichern und Einlesen aller Daten (core/backup.py)."""
import json
import tempfile
import unittest
import sqlite3
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und Sprache)
from morsetrainer.core import backup, db
from tests.test_modes import AppTestCase


def make_data(root: Path, tag: str) -> None:
    (root / "stats").mkdir(parents=True)
    (root / "stats" / "all_time.json").write_text(json.dumps({"tag": tag}), encoding="utf-8")
    (root / "stats" / f"2026-10-03_120000-{tag}.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "stats" / "daily.json.tmp").write_text("halb", encoding="utf-8")
    (root / "stats" / "awards.json.defekt-20261001-120000").write_text("kaputt", encoding="utf-8")
    (root / "window_state.json").write_text(json.dumps({"tag": tag}), encoding="utf-8")
    (root / "woerter.txt").write_text(tag, encoding="utf-8")
    (root / "fehler.log").write_text("log", encoding="utf-8")
    (root / "voices").mkdir()
    (root / "voices" / "stimme.onnx").write_text("gross", encoding="utf-8")


def damaged(raw: bytes, name: str, damage: str) -> bytes:
    """ZIP mit einem beschädigten Eintrag `name`: "data" (Inhalt), "encrypted"
    (als verschlüsselt markiert) oder "method" (unbekanntes Verfahren)."""
    raw = bytearray(raw)
    central = raw.index(b"PK\x01\x02")  # Einträge im zentralen Verzeichnis
    while raw[central + 46:central + 46 + len(name)] != name.encode():
        central = raw.index(b"PK\x01\x02", central + 4)
    if damage == "data":
        local = int.from_bytes(raw[central + 42:central + 46], "little")
        size = 30 + int.from_bytes(raw[local + 26:local + 28], "little") + int.from_bytes(raw[local + 28:local + 30], "little")
        raw[local + size] ^= 0xFF
    elif damage == "encrypted":
        raw[central + 8] |= 0x01
    else:
        raw[central + 10] = 99
    return bytes(raw)


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old, self.new = self.root / "alt", self.root / "neu"
        make_data(self.old, "alt")
        make_data(self.new, "neu")
        self.zip = self.root / "sicherung.zip"

    def test_export_contains_user_data_only(self):
        count = backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            names = set(archive.namelist())
            info = json.loads(archive.read(backup.MARKER))
        self.assertEqual(names, {backup.MARKER, "window_state.json", "woerter.txt", "stats/all_time.json",
                                 "stats/2026-10-03_120000-alt.jsonl"})
        self.assertEqual(count, 4)
        self.assertEqual(info["version"], "9.9")
        self.assertEqual(backup.read_info(self.zip)["format"], backup.FORMAT)

    def test_export_leaves_out_copies_made_before_a_migration(self):
        (self.old / "stats" / f"{db.DB_FILE_NAME}.vor-v1").write_bytes(b"alte Kopie")
        backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            self.assertFalse([n for n in archive.namelist() if ".vor-v" in n])

    def test_import_replaces_data_and_keeps_previous(self):
        backup.export_data(self.zip, "9.9", self.old)
        (self.new / "callsigns.scp").write_text("DL4YM\n", encoding="utf-8")
        previous = backup.import_data(self.zip, "9.9", self.new)

        self.assertEqual(json.loads((self.new / "window_state.json").read_text())["tag"], "alt")
        self.assertEqual((self.new / "woerter.txt").read_text(), "alt")
        stats = sorted(p.name for p in (self.new / "stats").iterdir())
        self.assertEqual(stats, ["2026-10-03_120000-alt.jsonl", "all_time.json"])
        # Nicht in der Sicherung: bleibt stehen.
        self.assertEqual((self.new / "callsigns.scp").read_text(), "DL4YM\n")
        self.assertTrue((self.new / "voices" / "stimme.onnx").exists())
        # Keine Reste vom Umkopieren.
        self.assertEqual(sorted(p.name for p in self.new.iterdir() if p.name.startswith(".")), [])
        # Der bisherige Stand liegt als Sicherung daneben.
        with zipfile.ZipFile(previous) as archive:
            self.assertIn("stats/2026-10-03_120000-neu.jsonl", archive.namelist())

    def test_rejects_foreign_zip(self):
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr("irgendwas.txt", "x")
        with self.assertRaises(backup.BackupError):
            backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual((self.new / "woerter.txt").read_text(), "neu")

    def test_rejects_not_a_zip(self):
        self.zip.write_text("kein zip", encoding="utf-8")
        with self.assertRaises(backup.BackupError):
            backup.read_info(self.zip)

    def test_rejects_paths_outside(self):
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr(backup.MARKER, json.dumps({"format": 1}))
            archive.writestr("stats/../../boese.txt", "x")
        with self.assertRaises(backup.BackupError):
            backup.import_data(self.zip, "9.9", self.new)
        self.assertFalse((self.root / "boese.txt").exists())

    def test_rejects_oversized_archives(self):
        # Zip-Bombe: zu viele Einträge, zu viel entpackt, zu große Kopfdaten.
        cases = {
            "Einträge": (lambda a: [a.writestr(f"stats/{n}.json", "") for n in range(11)], "MAX_ENTRIES", 10),
            "Gesamtgröße": (lambda a: a.writestr("stats/gross.json", "x" * 5000), "MAX_UNPACKED", 1000),
            "Kopfdaten": (lambda a: None, "MAX_MARKER", 5),
        }
        for label, (fill, limit, value) in cases.items():
            with self.subTest(label), mock.patch.object(backup, limit, value):
                with zipfile.ZipFile(self.zip, "w") as archive:
                    archive.writestr(backup.MARKER, json.dumps({"format": 1}))
                    fill(archive)
                with self.assertRaises(backup.BackupError):
                    backup.import_data(self.zip, "9.9", self.new)
                self.assertEqual((self.new / "woerter.txt").read_text(), "neu")

    def test_import_skips_database_companion_files(self):
        # Ein fremdes Journal würde beim nächsten Öffnen in die Datenbank eingespielt.
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr(backup.MARKER, json.dumps({"format": 1}))
            archive.writestr("stats/all_time.json", json.dumps({"tag": "fremd"}))
            for suffix in backup.DB_COMPANIONS:
                archive.writestr(f"stats/{db.DB_FILE_NAME}{suffix}", "boese")
        backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual(json.loads((self.new / "stats" / "all_time.json").read_text())["tag"], "fremd")
        for suffix in backup.DB_COMPANIONS:
            self.assertFalse((self.new / "stats" / f"{db.DB_FILE_NAME}{suffix}").exists())

    def test_rejects_newer_format(self):
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr(backup.MARKER, json.dumps({"format": backup.FORMAT + 1}))
        with self.assertRaises(backup.BackupError):
            backup.read_info(self.zip)

    def test_rejects_damaged_or_encrypted_member(self):
        # Was sich nicht entpacken lässt, fällt vor dem Ersetzen auf.
        for damage in ("data", "encrypted", "method"):
            with self.subTest(damage):
                backup.export_data(self.zip, "9.9", self.old)
                self.zip.write_bytes(damaged(self.zip.read_bytes(), "stats/all_time.json", damage))
                with self.assertRaises(backup.BackupError):
                    backup.read_info(self.zip)
                with self.assertRaises(backup.BackupError):
                    backup.import_data(self.zip, "9.9", self.new)
                self.assertEqual((self.new / "woerter.txt").read_text(), "neu")


class DatabaseBackupTest(unittest.TestCase):
    """Die Datenbank kommt als stimmiger Schnappschuss in die Sicherung,
    auch während sie offen ist und Änderungen noch im Journal stehen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old, self.new = self.root / "alt", self.root / "neu"
        make_data(self.old, "alt")
        make_data(self.new, "neu")
        self.zip = self.root / "sicherung.zip"
        self.addCleanup(db.use, None)
        db.use(self.old / "stats" / db.DB_FILE_NAME)
        db.save_state("all_time", {"tag": "alt"})  # Verbindung bleibt offen, Änderung steht im -wal

    def test_export_snapshots_open_database(self):
        self.assertTrue((self.old / "stats" / (db.DB_FILE_NAME + "-wal")).exists())
        count = backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            names = set(archive.namelist())
            raw = archive.read(f"stats/{db.DB_FILE_NAME}")
        self.assertIn(f"stats/{db.DB_FILE_NAME}", names)
        self.assertFalse(any(n.endswith(("-wal", "-shm")) for n in names))
        self.assertEqual(count, 5)
        copy = self.root / "kopie.db"
        copy.write_bytes(raw)
        db.use(copy)
        self.assertEqual(db.load_state("all_time", {}), {"tag": "alt"})

    def test_auto_backup_waits_a_week_and_keeps_four(self):
        folder = self.old / backup.AUTO_DIR
        day = date(2026, 10, 1)
        first = backup.auto_backup("9.9", self.old, today=day)
        self.assertEqual(first, folder / "auto-2026-10-01.zip")
        with zipfile.ZipFile(first) as archive:
            self.assertIn(f"stats/{db.DB_FILE_NAME}", archive.namelist())
        self.assertIsNone(backup.auto_backup("9.9", self.old, today=day + timedelta(days=6)))
        for week in range(1, 6):
            self.assertIsNotNone(backup.auto_backup("9.9", self.old, today=day + timedelta(days=7 * week)))
        names = sorted(p.name for p in folder.iterdir())
        self.assertEqual(names, [f"auto-2026-{m}.zip" for m in ("10-15", "10-22", "10-29", "11-05")])

    def test_failed_auto_backup_leaves_a_note_until_one_works(self):
        day = date(2026, 10, 1)
        self.assertIsNone(backup.auto_backup_failure(self.old))
        with mock.patch.object(backup, "export_data", side_effect=OSError("Platte voll")):
            with self.assertRaises(OSError):
                backup.auto_backup("9.9", self.old, today=day)
        self.assertEqual(backup.auto_backup_failure(self.old), "Platte voll")
        self.assertIsNotNone(backup.auto_backup("9.9", self.old, today=day))
        self.assertIsNone(backup.auto_backup_failure(self.old))

    def test_future_or_unreadable_names_neither_block_nor_count(self):
        folder = self.old / backup.AUTO_DIR
        folder.mkdir()
        today = date(2026, 10, 21)
        for name in ("auto-2099-01-01.zip", "auto-xxxx-xx-xx.zip", "auto-2026-13-45.zip"):
            (folder / name).write_bytes(b"fremd")
        made = backup.auto_backup("9.9", self.old, today=today)
        self.assertEqual(made, folder / "auto-2026-10-21.zip")
        self.assertIsNone(backup.auto_backup("9.9", self.old, today=today))  # und drosselt wie sonst
        for week in range(1, 7):
            backup.auto_backup("9.9", self.old, today=today + timedelta(days=7 * week))
        self.assertTrue((folder / "auto-2099-01-01.zip").exists())  # fremde bleiben, zählen nicht
        self.assertTrue((folder / "auto-xxxx-xx-xx.zip").exists())
        real = [p for p in folder.glob("auto-2026-1?-??.zip") if p.name != "auto-2026-13-45.zip"]
        self.assertEqual(len(real), backup.AUTO_KEEP)

    def test_leftover_holds_and_temp_files_stay_out_of_backups(self):
        stats_dir = self.old / "stats"
        for name in ("morsetrainer.db-wal.halt4711", "x.zip.tmp123", "y.json.tmp"):
            (stats_dir / name).write_bytes(b"Rest")
        backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            self.assertFalse(any(("halt" in n or ".tmp" in n) for n in archive.namelist()))

    def test_lost_race_is_not_a_failure(self):
        # Ein anderes Fenster war schneller: Sein Ergebnis liegt da, der Rest ist kein Fehler.
        folder = self.old / backup.AUTO_DIR
        target = folder / "auto-2026-10-21.zip"
        real_export = backup.export_data

        def other_window_wins(path, version, data_dir):
            real_export(target, "9.9", data_dir)
            raise FileNotFoundError(2, "No such file or directory")
        with mock.patch.object(backup, "export_data", side_effect=other_window_wins):
            self.assertIsNone(backup.auto_backup("9.9", self.old, today=date(2026, 10, 21)))
        self.assertIsNone(backup.auto_backup_failure(self.old))
        self.assertTrue(target.exists())

    def test_unreadable_new_backup_does_not_push_out_old_ones(self):
        folder = self.old / backup.AUTO_DIR
        day = date(2026, 10, 1)
        for week in range(4):
            backup.auto_backup("9.9", self.old, today=day + timedelta(days=7 * week))
        with mock.patch.object(backup, "read_info", side_effect=backup.BackupError("kaputt")):
            with self.assertRaises(backup.BackupError):
                backup.auto_backup("9.9", self.old, today=day + timedelta(days=28))
        self.assertEqual(len(list(folder.glob("auto-*.zip"))), 4)
        self.assertFalse((folder / "auto-2026-10-29.zip").exists())
        self.assertIn("kaputt", backup.auto_backup_failure(self.old))

    def _mark_set_aside(self, day):
        conn = sqlite3.connect(self.old / "stats" / db.DB_FILE_NAME)
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta VALUES (?, ?)", (db.ASIDE_KEY, day.isoformat()))
        conn.commit()
        conn.close()

    def test_backups_from_before_a_set_aside_file_are_not_pushed_out(self):
        folder = self.old / backup.AUTO_DIR
        (self.old / "stats" / db.DB_FILE_NAME).unlink(missing_ok=True)
        day = date(2026, 9, 1)
        for week in range(4):  # vier gute Sicherungen vor dem Beiseitelegen
            sqlite3.connect(self.old / "stats" / db.DB_FILE_NAME).close()
            backup.auto_backup("9.9", self.old, today=day + timedelta(days=7 * week))
        self._mark_set_aside(day + timedelta(days=21))  # die Datei war kaputt, die neue ist leer
        for week in range(4, 10):  # danach sichert der Start die leere Datei weiter
            backup.auto_backup("9.9", self.old, today=day + timedelta(days=7 * week))
        names = sorted(p.name for p in folder.glob("auto-*.zip"))
        for week in range(4):
            self.assertIn(f"auto-{day + timedelta(days=7 * week)}.zip", names)
        self.assertLess(len(names), 10)  # die leeren werden weiter beschnitten

    def test_import_keeps_set_aside_files_in_a_rescue_folder(self):
        backup.export_data(self.zip, "9.9", self.new)
        stats_dir = self.old / "stats"
        (stats_dir / "morsetrainer.db.defekt-20261001-120000").write_text("kaputt", encoding="utf-8")
        (stats_dir / "morsetrainer.db.defekt-20261001-120000-wal").write_text("wal", encoding="utf-8")
        (stats_dir / "morsetrainer.db.vor-v1").write_text("kopie", encoding="utf-8")
        backup.import_data(self.zip, "9.9", self.old)
        rescue = self.old / backup.RESCUE_DIR
        self.assertEqual(sorted(p.name for p in rescue.iterdir()),
                         ["awards.json.defekt-20261001-120000", "morsetrainer.db.defekt-20261001-120000",
                          "morsetrainer.db.defekt-20261001-120000-wal", "morsetrainer.db.vor-v1"])
        self.assertFalse(any(".defekt-" in p.name for p in (self.old / "stats").iterdir()))

    def test_leftover_work_folders_are_removed_after_a_day(self):
        import os
        import time
        old_snapshot = self.old / ".snapshot-abc"
        old_import = self.old / ".import-20260101-000000"
        young = self.old / ".snapshot-jung"
        alt = self.old / ".stats-alt-20260101-000000"
        for folder in (old_snapshot, old_import, young, alt):
            folder.mkdir()
            (folder / "x").write_text("daten", encoding="utf-8")
        long_ago = time.time() - 3 * 86400
        for folder in (old_snapshot, old_import, alt):
            os.utime(folder, (long_ago, long_ago))
        backup._remove_old_work_dirs(self.old)
        self.assertFalse(old_snapshot.exists() or old_import.exists())
        self.assertTrue(young.exists())  # könnte ein anderes Fenster gerade benutzen
        self.assertTrue(alt.exists())  # kann der einzige Stand sein

    def test_no_backup_while_a_broken_database_was_set_aside(self):
        with mock.patch.object(db, "aside_file", self.old / "x"):
            self.assertIsNone(backup.auto_backup("9.9", self.old, today=date(2026, 10, 1)))
        self.assertFalse((self.old / backup.AUTO_DIR).exists())

    def test_other_errors_leave_a_note_without_path(self):
        with mock.patch.object(backup, "export_data", side_effect=ValueError("zip64 fehlt")):
            with self.assertRaises(ValueError):
                backup.auto_backup("9.9", self.old, today=date(2026, 10, 1))
        self.assertEqual(backup.auto_backup_failure(self.old), "zip64 fehlt")
        with mock.patch.object(backup, "export_data",
                               side_effect=OSError(28, "No space left on device", "/home/x/geheim")):
            with self.assertRaises(OSError):
                backup.auto_backup("9.9", self.old, today=date(2026, 10, 1))
        self.assertEqual(backup.auto_backup_failure(self.old), "No space left on device")

    def test_auto_backup_needs_a_database_and_stays_out_of_manual_backup(self):
        self.assertIsNone(backup.auto_backup("9.9", self.new, today=date(2026, 10, 1)))
        backup.auto_backup("9.9", self.old, today=date(2026, 10, 1))
        backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            self.assertFalse(any(backup.AUTO_DIR in n for n in archive.namelist()))

    def test_import_brings_database_and_reopens(self):
        backup.export_data(self.zip, "9.9", self.old)
        db.use(self.new / "stats" / db.DB_FILE_NAME)
        db.save_state("all_time", {"tag": "neu"})
        backup.import_data(self.zip, "9.9", self.new)
        # Die offene Verbindung zur ersetzten Datei ist zu; der nächste
        # Zugriff liest die eingelesene.
        self.assertEqual(db.load_state("all_time", {}), {"tag": "alt"})

    def test_rejects_damaged_database(self):
        backup.export_data(self.zip, "9.9", self.old)
        with zipfile.ZipFile(self.zip) as archive:
            members = {n: archive.read(n) for n in archive.namelist()}
        members[f"stats/{db.DB_FILE_NAME}"] = b"keine Datenbank" * 100
        with zipfile.ZipFile(self.zip, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        with self.assertRaises(backup.BackupError):
            backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual((self.new / "woerter.txt").read_text(), "neu")

    def test_rejects_database_of_newer_version(self):
        backup.export_data(self.zip, "9.9", self.old)
        target = self.old.parent / "neuer.db"
        with zipfile.ZipFile(self.zip) as archive:
            members = {n: archive.read(n) for n in archive.namelist()}
        target.write_bytes(members[f"stats/{db.DB_FILE_NAME}"])
        raw = sqlite3.connect(target)
        raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        raw.close()
        members[f"stats/{db.DB_FILE_NAME}"] = target.read_bytes()
        with zipfile.ZipFile(self.zip, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        with self.assertRaises(backup.BackupError):
            backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual((self.new / "woerter.txt").read_text(), "neu")


class BeforeImportCopiesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old, self.new = self.root / "alt", self.root / "neu"
        make_data(self.old, "alt")
        make_data(self.new, "neu")
        self.zip = self.root / "sicherung.zip"
        backup.export_data(self.zip, "9.9", self.old)

    def test_failed_import_before_replacing_leaves_no_copy(self):
        with mock.patch.object(backup, "_check_database", side_effect=backup.BackupError("database")):
            with self.assertRaises(backup.BackupError):
                backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual(list(self.new.glob("vor-import-*.zip")), [])
        self.assertEqual((self.new / "woerter.txt").read_text(), "neu")

    def test_failed_import_after_replacing_keeps_the_copy(self):
        with mock.patch.object(backup, "_keep_rescue_files", side_effect=OSError("voll")):
            with self.assertRaises(OSError):
                backup.import_data(self.zip, "9.9", self.new)
        self.assertEqual(len(list(self.new.glob("vor-import-*.zip"))), 1)

    def test_only_the_last_copies_are_kept(self):
        for day in range(1, 6):
            (self.new / f"vor-import-2026010{day}-120000.zip").write_bytes(b"alt")
        previous = backup.import_data(self.zip, "9.9", self.new)
        kept = sorted(p.name for p in self.new.glob("vor-import-*.zip"))
        self.assertEqual(len(kept), backup.BEFORE_IMPORT_KEEP)
        self.assertIn(previous.name, kept)
        self.assertEqual(kept[0], "vor-import-20260104-120000.zip")


class ImportWhileRunningTest(AppTestCase):
    """„Daten einlesen“ während einer Übung."""

    def test_exercise_started_during_the_file_dialog_blocks_import(self):
        # Der Dateidialog öffnet erst nach seiner Ansage; wer in der Zeit eine
        # Übung startet, darf die Sicherung nicht einlesen (das Beenden danach
        # schriebe den laufenden Durchgang hinein).
        from morsetrainer import app as app_module
        chosen = []
        with mock.patch.object(app_module.dialog, "askopenfilename", lambda then, **options: chosen.append(then)), \
                mock.patch.object(app_module.instances, "others", return_value=0), \
                mock.patch.object(app_module.dialog, "showinfo") as info, \
                mock.patch.object(app_module.dialog, "askyesno", return_value=False), \
                mock.patch.object(backup, "read_info") as read_info, \
                mock.patch.object(backup, "import_data") as import_data:
            self.app._import_data()
            self.assertEqual(len(chosen), 1)
            self.app.running_mode = True  # während der Ansage gestartet
            chosen[0]("/irgendwo/sicherung.zip")
        info.assert_called_once()
        read_info.assert_not_called()
        import_data.assert_not_called()

    def test_another_window_blocks_import(self):
        from morsetrainer import app as app_module
        with mock.patch.object(app_module.instances, "others", return_value=1), \
                mock.patch.object(app_module.dialog, "showinfo") as info:
            self.assertTrue(self.app._exercise_blocks_import())
        info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
