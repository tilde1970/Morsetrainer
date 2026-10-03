"""Bandbedingungen/Mischer, Alignment und Statistik (in einem temporären
Verzeichnis, die echten Daten in stats/ bleiben unberührt)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import align
from morsetrainer.core import band
from morsetrainer.core import db
from morsetrainer.core import stats


class AlignTest(unittest.TestCase):
    def test_skipped_and_wrong_characters(self):
        ops = align.align("CQDE", "CQXE")
        kinds = [op.kind for op in ops]
        self.assertEqual(kinds.count(align.OpKind.MATCH), 3)
        self.assertEqual(kinds.count(align.OpKind.SUBSTITUTE), 1)
        ops = align.align("CQDE", "CQE")
        self.assertEqual([op.kind for op in ops].count(align.OpKind.DELETE), 1)


class BandTest(unittest.TestCase):
    def setUp(self):
        self.band = band.BandConditions(4)

    def test_everything_off_passes_signal_through(self):
        block = np.full(960, 0.5, dtype=np.float32)
        self.assertFalse(self.band.active)
        out = self.band.process(block, 1)
        np.testing.assert_allclose(out, block, atol=1e-6)
        self.assertEqual(self.band.station_gain(1, 10), 1.0)

    def test_all_effects_stay_in_range(self):
        for effect in band.EFFECTS:
            self.band.enabled[effect] = True
            self.band.levels[effect] = 1.0
        self.band.prepare(600)
        block = np.full(960, 0.5, dtype=np.float32)
        for i in range(300):
            out = self.band.mix([(block, i % 4), (block, None)], 960)
            self.assertEqual(out.dtype, np.float32)
            self.assertEqual(len(out), 960)
            self.assertLessEqual(np.abs(out).max(), 1.0)

    def test_mix_pads_short_blocks(self):
        out = self.band.mix([(np.ones(100, dtype=np.float32) * 0.1, 0)], 960)
        self.assertEqual(len(out), 960)
        self.assertEqual(out[500], 0.0)

    def test_chirp_only_when_enabled(self):
        station = next(i for i, c in enumerate(self.band.chirps) if c is not None)
        self.assertIsNone(self.band.chirp_for(station))
        self.band.enabled["chirp"] = True
        self.assertIsNotNone(self.band.chirp_for(station))

    def test_soft_limit(self):
        limited = band.soft_limit(np.array([0.5, 0.8, 3.0, -3.0]))
        self.assertEqual(limited[0], 0.5)
        self.assertLessEqual(limited[2], 1.0)
        self.assertGreaterEqual(limited[3], -1.0)


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def _session(self, pairs, mode="single", wpm=20):
        session = stats.SessionStats(mode, "HS5", wpm, 600)
        for sent, typed in pairs:
            session.record_char(sent, typed, sent == typed, 0.5, 20.0)
        return session

    def test_confusions_are_counted_and_merged(self):
        session = self._session([("H", "5"), ("H", "5"), ("H", "H"), ("S", ""), ("5", "H")])
        rows = {row[0]: row for row in session.char_rows()}
        self.assertEqual(rows["H"][6], "5 (2)")
        self.assertEqual(rows["S"][6], "– (1)")
        session.finalize()
        self._session([("H", "5")]).finalize()
        data = stats.load_all_time()
        self.assertEqual(data["H"]["confusions"], {"5": 3})
        top = stats.top_confusions(data)
        self.assertEqual(top[0][:3], ("H", "5", 3))
        self.assertNotIn("", [typed for _, typed, _, _ in top])  # verpasst zählt nicht als Paar

    def test_plain_text_stays_out_of_the_char_statistics(self):
        # Im Klartext verrät der Zusammenhang Zeichen: nur in den Verlauf.
        session = stats.SessionStats("word", "HS5", 20, 600, char_stats=False)
        session.record_char("H", "5", False, 0.5, 20.0)
        session.record_char("S", "S", True, 0.5, 20.0)
        session.finalize()
        self.assertEqual(stats.load_all_time(), {})
        self.assertEqual(stats.recent_char_data(), {})
        self.assertEqual([entry["mode"] for entry in stats.load_history()], ["word"])

    def test_confusion_drill_ignores_untrained_chars(self):
        from morsetrainer.app import MorseTrainerApp
        data = {
            "6": {"good": 30, "wrong": 3, "confusions": {"B": 2, "N": 1}},
            "8": {"good": 20, "wrong": 3, "confusions": {"9": 2, "7": 1}},
            "/": {"good": 20, "wrong": 1, "confusions": {"(": 1}},  # Vertipper mit Umschalttaste
            "5": {"good": 17, "wrong": 1, "confusions": {"H": 1}},
        }
        for ch in "B9HN7":
            data[ch] = {"good": 10, "wrong": 0, "confusions": {}}
        chars = MorseTrainerApp._confusion_charset(data)
        self.assertEqual(chars, "6B895HN")  # "/ → (" entfällt ("(" nie gesendet), "6 → N" rückt nach

    def test_recent_confusions_forget_old_sessions_and_reset(self):
        from datetime import datetime, timedelta
        def write(days_ago, pairs):
            start = datetime.now() - timedelta(days=days_ago)
            lines = [{"type": "config", "mode": "single", "start_time": start.isoformat(timespec="seconds")}]
            lines += [{"type": "char", "char": c, "typed": t, "correct": c == t} for c, t in pairs]
            tests.write_session(lines)
        write(60, [("B", "6")] * 5)   # zu alt
        write(2, [("8", "9"), ("8", "8")])
        data = stats.recent_char_data()
        self.assertNotIn("B", data)
        self.assertEqual(data["8"]["confusions"], {"9": 1})
        stats.reset_all_time()
        self.assertEqual(stats.recent_char_data(), {})

    def test_assumed_latencies_do_not_raise_the_usual_latency(self):
        from morsetrainer.core.weighting import CharPicker
        session = stats.SessionStats("group", "KM", 20, 600)
        for _ in range(4):
            session.record_char("K", "K", True, 0.5, 20.0, latency=0.6)
            session.record_char("M", "M", True, 0.5, 20.0, latency=0.6)
            session.record_char("M", "M", True, 0.5, 20.0, latency=1.2, assumed=True)
        session.finalize()
        self.assertEqual(stats.load_all_time()["M"]["assumed_latency_count"], 4)
        picker = CharPicker("KM", weighted=True)
        self.assertAlmostEqual(picker.median_latency(), 0.6)  # nur gemessen
        weights = dict(zip("KM", picker.weights()))
        self.assertGreater(weights["M"], weights["K"])  # für das Zeichen zählen sie mit

    def test_measured_cpm_counts_only_correct_characters(self):
        session = self._session([("H", "H"), ("S", "S"), ("5", "H")])  # je 0,5 s
        self.assertEqual(session.summary()["cpm"], 120.0)
        session.finalize()
        self.assertEqual(stats.all_time_summary(stats.load_all_time())["cpm"], 120.0)
        wrong_only = self._session([("H", "5")])
        self.assertEqual(wrong_only.summary()["cpm"], 0.0)
        wrong_only.finalize()

    def test_cpm_is_five_times_wpm(self):
        from morsetrainer.core import tempo
        self.assertEqual(tempo.cpm(20), 100)
        self.assertEqual(tempo.cpm(12), 60)

    def test_old_all_time_without_confusions_still_works(self):
        db.save_state("all_time", {"K": {
            "good": 3, "wrong": 1, "total_reaction_time_s": 2.0, "total_effective_wpm": 80.0,
            "correct_effective_wpm_total": 60.0, "attempts": 4,
        }})
        rows = stats.all_time_char_rows(stats.load_all_time())
        self.assertEqual(rows[0][6], "")
        self._session([("K", "R")]).finalize()
        self.assertEqual(stats.load_all_time()["K"]["confusions"], {"R": 1})

    def test_history_combines_sessions_and_results(self):
        self._session([("H", "H"), ("S", "5")], wpm=18).finalize()
        stats.log_result("qso_quiz", 6, 8, 22, kind="cqww")
        stats.log_result("contest", 9, 10, 25, contest="wpx")
        db._write("INSERT INTO results (time, mode, data) VALUES ('2026-01-01T00:00:00', 'x', '{kaputte Zeile')")
        history = stats.load_history()
        self.assertEqual([e["mode"] for e in history], ["single", "qso_quiz", "contest"])
        self.assertEqual(history[0]["accuracy_pct"], 50.0)
        self.assertEqual(history[0]["wpm"], 18)
        self.assertEqual(history[1]["accuracy_pct"], 75.0)

    def test_result_that_cannot_be_written_is_skipped(self):
        with mock.patch.object(db, "add_result", side_effect=db.Error("disk I/O error")):
            stats.log_result("contest", 9, 10, 25, contest="wpx")  # kein Fehler
        self.assertEqual(stats.load_history(), [])

    def test_empty_session_is_removed(self):
        session = stats.SessionStats("single", "K", 20, 600)
        self.assertIsNone(session.finalize())
        self.assertEqual(stats.load_history(), [])
        self.assertEqual(db.sessions(), [])


if __name__ == "__main__":
    unittest.main()