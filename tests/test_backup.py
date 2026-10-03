"""Sichern und Einlesen aller Daten (core/backup.py)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import tests  # noqa: F401  (Pfad und Sprache)
from morsetrainer.core import backup


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


if __name__ == "__main__":
    unittest.main()
