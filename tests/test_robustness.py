"""Tests für Fehlerbehandlung und Tempo: kaputte oder nicht schreibbare
Dateien, fehlende Tonausgabe und das Alignment langer Sitzungen."""
import json
import random
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import align, audio, stats, storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_atomic_write_replaces_and_leaves_no_temp_file(self):
        path = self.dir / "data.json"
        storage.write_json_atomic(path, {"a": 1})
        storage.write_json_atomic(path, {"a": 2})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})
        self.assertEqual([p.name for p in self.dir.iterdir()], ["data.json"])

    def test_failed_write_keeps_old_file(self):
        path = self.dir / "data.json"
        storage.write_json_atomic(path, {"a": 1})
        with mock.patch("os.replace", side_effect=OSError("Platte voll")):
            with self.assertRaises(OSError):
                storage.write_json_atomic(path, {"a": 2})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})
        self.assertFalse((self.dir / "data.json.tmp").exists())

    def test_broken_file_is_set_aside(self):
        path = self.dir / "all_time.json"
        path.write_text('{"K": {"good": 3', encoding="utf-8")
        self.assertEqual(storage.load_json(path, {}), {})
        self.assertFalse(path.exists())
        self.assertEqual(len(list(self.dir.glob("all_time.json.defekt-*"))), 1)

    def test_wrong_type_and_missing_file(self):
        path = self.dir / "state.json"
        self.assertEqual(storage.load_json(path, {}), {})
        path.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(storage.load_json(path, {}), {})


class StatsRobustnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
            mock.patch.object(stats, "ALL_TIME_FILE", directory / "all_time.json"),
            mock.patch.object(stats, "RESULTS_FILE", directory / "results.jsonl"),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def test_broken_all_time_does_not_block(self):
        stats.ALL_TIME_FILE.write_text("{kaputt", encoding="utf-8")
        self.assertEqual(stats.load_all_time(), {})
        session = stats.SessionStats("single", "K", 20, 600)
        session.record_char("K", "K", True, 0.5, 20.0)
        session.finalize()
        self.assertEqual(stats.load_all_time()["K"]["good"], 1)

    def test_unwritable_log_keeps_training(self):
        with mock.patch("builtins.open", side_effect=PermissionError("keine Schreibrechte")):
            session = stats.SessionStats("single", "K", 20, 600)
        self.assertIn("Schreibrechte", session.log_error)
        session.record_char("K", "K", True, 0.5, 20.0)
        self.assertIsNone(session.finalize())
        self.assertEqual(stats.load_all_time()["K"]["good"], 1)

    def test_history_skips_session_without_summary(self):
        done = stats.SessionStats("group", "KM", 20, 600)
        done.record_char("K", "K", True, 0.5, 20.0)
        done.finalize()
        crashed = stats.STATS_DIR / "2026-01-01_120000-group.jsonl"
        crashed.write_text('{"type": "config", "mode": "group", "wpm": 20, "start_time": "2026-01-01T12:00:00"}\n'
                           '{"type": "char", "char": "K"}\n{"type": "summ', encoding="utf-8")
        self.assertEqual(len(stats.load_history()), 1)


class AudioErrorTest(unittest.TestCase):
    def test_play_raises_readable_error(self):
        with mock.patch.object(audio.sd, "play", side_effect=OSError("Gerät belegt")):
            with self.assertRaises(audio.AudioError) as ctx:
                audio.play([0.0])
            self.assertIn("Gerät belegt", str(ctx.exception))
            audio.play_quietly([0.0])  # darf nicht werfen

    def test_stop_ignores_errors(self):
        with mock.patch.object(audio.sd, "stop", side_effect=OSError("weg")):
            audio.stop()


class LongAlignTest(unittest.TestCase):
    def test_long_session_is_fast_and_correct(self):
        rng = random.Random(7)
        sent = "".join(rng.choice("KMURESNAPT") for _ in range(3000))
        typed = sent[:1000] + sent[1010:2000] + "XX" + sent[2000:]
        started = time.perf_counter()
        ops = align.align(sent, typed)
        self.assertLess(time.perf_counter() - started, 2.0)
        self.assertEqual(sum(op.kind != align.OpKind.MATCH for op in ops), 12)
