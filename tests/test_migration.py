"""Tests für die Übernahme der alten JSON-Dateien in die Datenbank
(core/migration.py)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import db, migration


def _write_lines(path: Path, lines) -> None:
    path.write_text("".join(json.dumps(obj, ensure_ascii=False) + "\n" for obj in lines), encoding="utf-8")


CONFIG = {"type": "config", "mode": "single", "charset": "KM", "wpm": 20, "freq": 600,
          "group_len": None, "start_time": "2026-10-03T10:48:55"}
CHAR = {"type": "char", "char": "K", "typed": "K", "correct": True, "reaction_time_s": 0.8,
        "effective_wpm": 12.0, "latency_s": 0.5}
SUMMARY = {"type": "summary", "total": 1, "correct": 1, "per_char": {"K": {"good": 1, "wrong": 0}}}


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stats = Path(self.tmp.name) / "stats"
        self.stats.mkdir()
        db.use(self.stats / "morsetrainer.db")

    def tearDown(self):
        db.use(None)
        self.tmp.cleanup()

    def _session_file(self, name="2026-10-03_104855-single.jsonl", lines=None):
        path = self.stats / name
        _write_lines(path, lines if lines is not None else [CONFIG, CHAR, SUMMARY])
        return path

    def test_nothing_to_do(self):
        self.assertEqual(migration.run(self.stats), 0)
        self.assertFalse((self.stats / "alt-json").exists())

    def test_session_is_imported_and_file_archived(self):
        self._session_file()
        self.assertEqual(migration.run(self.stats), 1)
        [session] = db.sessions(events=True)
        self.assertEqual(session.config, CONFIG)
        self.assertEqual(session.events, [CHAR])
        self.assertEqual(session.summary, SUMMARY)
        self.assertEqual(list(self.stats.glob("*.jsonl")), [])
        self.assertTrue((self.stats / "alt-json" / "2026-10-03_104855-single.jsonl").is_file())

    def test_group_lines_and_order_are_kept(self):
        group = {"type": "group", "sent": "KM", "typed": "KN", "first": False}
        self._session_file(lines=[CONFIG, CHAR, {**CHAR, "char": "M"}, group, SUMMARY])
        migration.run(self.stats)
        self.assertEqual([e.get("char") or e["sent"] for e in db.sessions(events=True)[0].events], ["K", "M", "KM"])

    def test_aborted_session_without_summary(self):
        self._session_file(lines=[CONFIG, CHAR])
        with (self.stats / "2026-10-03_104855-single.jsonl").open("a", encoding="utf-8") as fp:
            fp.write('{"type": "char", "ch')
        migration.run(self.stats)
        [session] = db.sessions(events=True)
        self.assertIsNone(session.summary)
        self.assertEqual(session.events, [CHAR])  # halb geschriebene Zeile fällt weg

    def test_missing_config_is_taken_from_file_name(self):
        self._session_file("2026-09-24_174310-callsign.jsonl", lines=[CHAR])
        migration.run(self.stats)
        [session] = db.sessions()
        self.assertEqual(session.config["start_time"], "2026-09-24T17:43:10")
        self.assertEqual(session.config["mode"], "callsign")

    def test_unusable_file_is_archived_without_session(self):
        self._session_file("20-kaputt.jsonl", lines=[CHAR])
        self.assertEqual(migration.run(self.stats), 1)
        self.assertEqual(db.sessions(), [])
        self.assertTrue((self.stats / "alt-json" / "20-kaputt.jsonl").is_file())

    def test_results_and_states(self):
        _write_lines(self.stats / "results.jsonl", [
            {"time": "2026-10-03T11:00:00", "mode": "qso_quiz", "correct": 3, "total": 4},
            {"mode": "contest"},  # ohne Zeit: übergangen wie bisher
        ])
        states = {"all_time.json": {"K": {"good": 3}}, "daily.json": {"days": {}},
                  "awards.json": {"seals": {}, "seeded": True}, "review.json": {"K": {"box": 2}},
                  "practice.json": {"2026-10-03": 600.0}, "reset.json": {"time": "2026-09-30T10:00:00"}}
        for name, data in states.items():
            (self.stats / name).write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(migration.run(self.stats), 7)
        self.assertEqual([r["mode"] for r in db.results()], ["qso_quiz"])
        for name, data in states.items():
            self.assertEqual(db.load_state(migration.STATE_FILES[name], {}), data)
        self.assertEqual(sorted(p.name for p in (self.stats / "alt-json").iterdir()),
                         sorted(["results.jsonl", *states]))

    def test_broken_state_file_is_set_aside_not_imported(self):
        (self.stats / "daily.json").write_text('{"days": ', encoding="utf-8")
        migration.run(self.stats)
        self.assertEqual(db.load_state("daily", {"leer": True}), {"leer": True})
        self.assertEqual(len(list(self.stats.glob("daily.json.defekt-*"))), 1)

    def test_other_files_stay(self):
        for name in ("diplom.html", "antwortbogen.html", "2026-10-03_173421-netzwerk.csv"):
            (self.stats / name).write_text("x", encoding="utf-8")
        self._session_file()
        migration.run(self.stats)
        self.assertEqual(sorted(p.name for p in self.stats.iterdir() if p.is_file() and "morsetrainer.db" not in p.name),
                         ["2026-10-03_173421-netzwerk.csv", "antwortbogen.html", "diplom.html"])

    def test_failed_import_changes_nothing(self):
        self._session_file()
        self._session_file("2026-10-03_110221-single.jsonl")
        (self.stats / "practice.json").write_text('{"2026-10-03": 60}', encoding="utf-8")
        real = migration._import_session
        calls = []

        def failing(path):
            calls.append(path)
            if len(calls) == 2:
                raise db.Error("Platte voll")
            real(path)

        with mock.patch.object(migration, "_import_session", failing):
            with self.assertRaises(db.Error):
                migration.run(self.stats)
        self.assertEqual(db.sessions(), [])
        self.assertEqual(len(list(self.stats.glob("20*.jsonl"))), 2)
        self.assertFalse((self.stats / "alt-json").exists())
        # Nächster Start: neuer Versuch, diesmal vollständig.
        self.assertEqual(migration.run(self.stats), 3)
        self.assertEqual(len(db.sessions()), 2)
        self.assertEqual(db.load_state("practice", {}), {"2026-10-03": 60})

    def test_failed_move_does_not_import_twice(self):
        self._session_file()
        with mock.patch("os.replace", side_effect=OSError("gesperrt")):
            migration.run(self.stats)
        self.assertTrue((self.stats / "2026-10-03_104855-single.jsonl").exists())
        self.assertEqual(migration.run(self.stats), 0)
        self.assertEqual(len(db.sessions()), 1)
        self.assertFalse((self.stats / "2026-10-03_104855-single.jsonl").exists())

    def test_archive_does_not_overwrite(self):
        (self.stats / "alt-json").mkdir()
        (self.stats / "alt-json" / "daily.json").write_text('{"alt": 1}', encoding="utf-8")
        (self.stats / "daily.json").write_text('{"days": {}}', encoding="utf-8")
        migration.run(self.stats)
        self.assertEqual((self.stats / "alt-json" / "daily.json").read_text(encoding="utf-8"), '{"alt": 1}')
        self.assertEqual(len(list((self.stats / "alt-json").glob("daily.json.*"))), 1)


if __name__ == "__main__":
    unittest.main()
