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


class TimingTest(unittest.TestCase):
    """Zeitmaß auf Sample-Ebene: PARIS = 50 Einheiten, Punkt und Strich
    zwischen den Halbwertspunkten genau 1 bzw. 3 Einheiten."""

    @staticmethod
    def half_width(samples):
        from morsetrainer.core.morse import SAMPLE_RATE
        # Hüllkurve: gleitendes Maximum über gut eine Periode (600 Hz)
        envelope = np.abs(samples)
        window = 81
        padded = np.pad(envelope, (window // 2, window // 2))
        envelope = np.lib.stride_tricks.sliding_window_view(padded, window).max(axis=1)
        above = np.flatnonzero(envelope >= 0.5 * envelope.max())
        return (above[-1] - above[0]) / SAMPLE_RATE

    def test_paris_timing_exact(self):
        from morsetrainer.core.morse import SAMPLE_RATE, build_samples, build_text
        for wpm in (15, 20, 40, 60):
            unit = 1.2 / wpm
            # „PARIS “ = 50 Einheiten (Wortpause eingeschlossen)
            self.assertAlmostEqual(len(build_text("PARIS ", wpm, 600)) / SAMPLE_RATE, 50 * unit, delta=0.002)
            self.assertAlmostEqual(len(build_samples("E", wpm, 600)) / SAMPLE_RATE, 4 * unit, delta=0.001)
            # Halbwertsbreite (Messung per gleitendem Maximum: ±1 Periode)
            self.assertAlmostEqual(self.half_width(build_samples("E", wpm, 600)), unit, delta=0.002, msg=wpm)
            self.assertAlmostEqual(self.half_width(build_samples("T", wpm, 600)), 3 * unit, delta=0.002, msg=wpm)


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
        self.assertEqual(rows["S"][6], "")  # verpasst ist keine Verwechslung
        self.assertEqual(rows["S"][2], 1)  # zählt aber als falsch
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

    def _crashed_session(self, chars="KMK", hours_ago=5, mode="single"):
        """Durchgang, der nie abgeschlossen wurde: Zeichen gespeichert, keine Zusammenfassung."""
        from datetime import datetime, timedelta
        start = datetime.now() - timedelta(hours=hours_ago)
        session = stats.SessionStats(mode, "KM", 20, 600)
        session.start_time = start
        db._write("UPDATE sessions SET start_time = ?, config = json_set(config, '$.start_time', ?) WHERE id = ?",
                  (start.isoformat(timespec="seconds"),) * 2 + (session.session_id,))
        for char in chars:
            session.record_char(char, char, True, 0.8, 18.0, latency=0.5)
        return session

    def test_crashed_session_is_completed_at_the_next_start(self):
        crashed = self._crashed_session("KMK")
        self.assertIsNone(db.sessions()[0].summary)
        self.assertEqual(stats.load_all_time(), {})
        self.assertEqual(stats.recover_unfinished(), 1)
        summary = db.sessions()[0].summary
        self.assertEqual((summary["total"], summary["correct"], summary["recovered"]), (3, 3, True))
        self.assertEqual(stats.load_all_time()["K"]["good"], 2)
        self.assertEqual(stats.recover_unfinished(), 0)  # nicht noch einmal
        self.assertEqual(stats.load_all_time()["K"]["good"], 2)
        self.assertEqual(crashed.finalize(), crashed.session_id)  # ein anderes Fenster war schneller: kein Doppelzählen
        self.assertEqual(stats.load_all_time()["K"]["good"], 2)

    def test_recent_or_empty_sessions_are_handled_carefully(self):
        self._crashed_session("KM", hours_ago=0)  # könnte in einem anderen Fenster noch laufen
        self.assertEqual(stats.recover_unfinished(), 0)
        self.assertIsNone(db.sessions()[0].summary)
        empty = self._crashed_session("", hours_ago=9)
        self.assertEqual(stats.recover_unfinished(), 0)
        self.assertNotIn(empty.session_id, [s.id for s in db.sessions()])  # ohne eine Zeile entfernt

    def test_sessions_before_a_reset_do_not_come_back(self):
        self._crashed_session("KMK", hours_ago=30)
        stats.reset_all_time()
        stats.recover_unfinished()
        self.assertIsNotNone(db.sessions()[0].summary)  # abgeschlossen ...
        self.assertEqual(stats.load_all_time(), {})  # ... aber nicht zurückgeholt

    def test_last_days_are_compared_with_the_days_before(self):
        from datetime import datetime, timedelta
        from morsetrainer.widgets.stats_widget import comparison_text, trend_text

        def write(days_ago, rows, mode="single", start=None):
            start = start or (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": mode, "start_time": start}]
            lines += [{"type": "char", "char": c, "typed": t, "correct": c == t, **extra} for c, t, extra in rows]
            tests.write_session(lines + [{"type": "summary"}])
        self.assertEqual(comparison_text(stats.period_comparison()), "")
        write(60, [("K", "K", {"latency_s": 3.0})] * 5)  # vor beiden Zeiträumen
        write(20, [("K", "K", {"latency_s": 0.8})] * 6 + [("K", "M", {})] * 2 + [("M", "M", {"latency_s": 0.5})] * 2)
        write(2, [("K", "K", {"latency_s": 0.4})] * 5 + [("K", "K", {"latency_s": 2.0, "latency_assumed": True}),
                                                         ("K", "K", {"latency_s": 9.0}),  # gekappt
                                                         ("K", "K", {"latency_s": float("nan")}),
                                                         ("K", "K", {"latency_s": True})])  # unsinnig: keine Messung
        # Am Stück: Reaktion ab der vorigen Taste, zählt nur für die Trefferquote.
        write(3, [("K", "K", {"latency_s": 0.1})] * 4, mode="continuous")
        comparison = stats.period_comparison()
        accuracy, latency, count = stats.period_numbers(comparison[stats.BEFORE])
        self.assertEqual((round(accuracy), round(latency, 3), count), (80, 0.8, 8))  # Median, nicht Mittel (0,725)
        accuracy, latency, count = stats.period_numbers(comparison[stats.RECENT])
        self.assertEqual((accuracy, round(latency, 3), count), (100.0, 0.4, 6))  # Median, nicht Mittel (1,167)
        self.assertEqual(comparison[stats.RECENT]["good"], 13)  # 9 Einzeln + 4 Am Stück
        self.assertIsNone(stats.char_trend(comparison["chars"], "K"))  # zu wenige Messungen für den Trend
        self.assertEqual(trend_text((0.8, 0.4)), "0,80 → 0,40")
        self.assertEqual(comparison_text(comparison),
                         "Davor (30 Tage): Reaktion 0,80 s, 80 % richtig (aus 10 Zeichen) · "
                         "Letzte 7 Tage: Reaktion 0,40 s, 100 % richtig (aus 13 Zeichen). Reaktion: kleiner ist schneller.")
        # Vorlesen (F11): ohne Stichprobe des Vergleichszeitraums, ohne Merksatz
        self.assertEqual(comparison_text(comparison, spoken=True),
                         "Davor (30 Tage): Reaktion 0,80 s, 80 % richtig. "
                         "Letzte 7 Tage: Reaktion 0,40 s, 100 % richtig (aus 13 Zeichen).")
        stats.reset_all_time()
        self.assertEqual(comparison_text(stats.period_comparison()), "")

    def test_comparison_names_characters_that_are_new(self):
        from datetime import datetime, timedelta
        from morsetrainer.widgets.stats_widget import comparison_text

        def write(days_ago, rows):
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": "single", "start_time": start}]
            lines += [{"type": "char", "char": c, "typed": c, "correct": True, "latency_s": 0.5} for c in rows]
            tests.write_session(lines + [{"type": "summary"}])
        write(20, "K" * 12)
        write(2, "K" * 10 + "R" * 3 + "M")  # R neu und oft genug, M nur einmal
        comparison = stats.period_comparison()
        self.assertEqual(stats.new_chars(comparison), ["R"])
        self.assertTrue(comparison_text(comparison).endswith(
            "Neu dabei: R. Neue Zeichen machen den Schnitt anfangs langsamer."))
        self.assertTrue(comparison_text(comparison, spoken=True).endswith(
            "Neue Zeichen machen den Schnitt anfangs langsamer."))

    def test_new_chars_directly(self):
        def period(count):
            return {"good": count, "wrong": 0}
        both = lambda before, recent: {stats.BEFORE: period(before), stats.RECENT: period(recent)}  # noqa: E731
        self.assertEqual(stats.new_chars({}), [])
        chars = {"R": both(0, 3), "M": both(0, 2), "5": both(1, 9), "K": both(9, 9), "A": both(0, 4), "?": both(0, 3)}
        self.assertEqual(stats.new_chars({"chars": chars}), ["?", "A", "R"])  # 2 Antworten und „davor einmal“ zählen nicht

    def test_comparison_lists_at_most_six_new_characters_letters_first(self):
        from datetime import datetime, timedelta
        from morsetrainer.widgets.stats_widget import comparison_text

        def write(days_ago, rows):
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": "single", "start_time": start}]
            lines += [{"type": "char", "char": c, "typed": c, "correct": True, "latency_s": 0.5} for c in rows]
            tests.write_session(lines + [{"type": "summary"}])
        write(20, "K" * 12)
        write(2, "K" * 10 + "5" * 3 + "B" * 3 + "C" * 3 + "D" * 3 + "E" * 3 + "F" * 3)
        self.assertIn("Neu dabei: B C D E F 5.", comparison_text(stats.period_comparison()))  # genau 6: nichts weiter
        write(2, "G" * 3)
        self.assertIn("Neu dabei: B C D E F G und 1 weitere.", comparison_text(stats.period_comparison()))

    def test_comparison_names_no_new_characters_without_enough_in_both_periods(self):
        from datetime import datetime, timedelta
        from morsetrainer.widgets.stats_widget import comparison_text

        def write(days_ago, rows):
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": "single", "start_time": start}]
            lines += [{"type": "char", "char": c, "typed": c, "correct": True, "latency_s": 0.5} for c in rows]
            tests.write_session(lines + [{"type": "summary"}])
        write(20, "K" * 3)  # davor zu wenig: alles wäre „neu“
        write(2, "K" * 20 + "R" * 3)
        self.assertNotIn("Neu dabei", comparison_text(stats.period_comparison()))
        stats.reset_all_time()
        write(20, "K" * 20)
        write(2, "K" * 4 + "R" * 3)  # jetzt zu wenig
        self.assertNotIn("Neu dabei", comparison_text(stats.period_comparison()))

    def test_comparison_skips_runs_that_were_never_finished(self):
        from datetime import datetime, timedelta
        start = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
        rows = [{"type": "config", "mode": "single", "start_time": start}]
        rows += [{"type": "char", "char": "K", "typed": "K", "correct": True, "latency_s": 0.4}] * 12
        tests.write_session(rows)  # kein summary: Absturz oder Programm beendet
        self.assertEqual(stats.period_numbers(stats.period_comparison()[stats.RECENT]), (None, None, 0))
        tests.write_session(rows + [{"type": "summary"}])
        self.assertEqual(stats.period_numbers(stats.period_comparison()[stats.RECENT])[0], 100.0)

    def test_char_trend_is_a_median_from_enough_measurements(self):
        from datetime import datetime, timedelta

        def write(days_ago, latencies, start=None):
            start = start or (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            tests.write_session([{"type": "config", "mode": "single", "start_time": start}]
                                + [{"type": "char", "char": "K", "typed": "K", "correct": True, "latency_s": lat}
                                   for lat in latencies] + [{"type": "summary"}])
        write(20, [0.8] * (stats.MIN_TREND_COUNT - 1) + [5.0])  # ein Ausreißer verschiebt den Median nicht
        write(2, [0.5] * (stats.MIN_TREND_COUNT - 1))
        chars = stats.period_comparison()["chars"]
        self.assertIsNone(stats.char_trend(chars, "K"))  # eine Seite hat eine Messung zu wenig
        # Startzeit mit Zeitzone (von Hand eingetragen): zählt, statt abzubrechen.
        write(0, [0.5], start=(datetime.now().astimezone() - timedelta(days=1)).isoformat(timespec="seconds"))
        self.assertEqual(stats.char_trend(stats.period_comparison()["chars"], "K"), (0.8, 0.5))

    def test_untimed_answers_stay_out_of_speed_and_daily_latencies(self):
        from datetime import date
        from morsetrainer.core import daily
        session = stats.SessionStats("single", "K", 20, 600)
        session.record_char("K", "K", True, 0.5, 20.0, latency=0.3)
        session.record_char("K", "K", True, 7.0, 2.0, latency=None, timed=False)  # nach F11 ohne Zeitlimit
        session.finalize()
        data = stats.load_all_time()
        self.assertEqual(stats.all_time_char_rows(data)[0][5], 20.0)  # nicht 20 / 2 richtige
        self.assertEqual(stats.all_time_summary(data)["avg_effective_wpm"], 20.0)
        self.assertEqual(daily.latencies(date.today(), date.today()), {"K": {20: [0.3]}})  # kein „verpasst“

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

    def test_speed_column_counts_only_correct_answers(self):
        session = stats.SessionStats("single", "K", 20, 600)
        session.record_char("K", "K", True, 1.0, 18.0)
        session.record_char("K", "R", False, 3.0, 4.0)  # langsamer Fehlversuch zählt nicht
        rows = {row[0]: row for row in session.char_rows()}
        self.assertEqual(rows["K"][5], 18.0)

    def test_reaction_column_is_time_after_the_tone(self):
        # Gezeigt wird die gemessene Zeit vom Ende des Tons bis zur Eingabe
        # (nur richtige, ohne angenommene Werte), nicht die Zeit ab Beginn.
        session = stats.SessionStats("single", "KE", 20, 600)
        session.record_char("K", "K", True, 1.2, 20.0, latency=0.4)
        session.record_char("K", "K", True, 1.4, 20.0, latency=0.6)
        session.record_char("K", "K", True, 2.0, 20.0, latency=1.6, assumed=True)
        session.record_char("E", "S", False, 0.9, 20.0)
        rows = {row[0]: row for row in session.char_rows()}
        self.assertAlmostEqual(rows["K"][4], 0.5)
        self.assertIsNone(rows["E"][4])  # nur falsch: keine Messung
        self.assertEqual(rows["K"][5], 20.0)  # Tempo nur aus richtigen Antworten
        self.assertIsNone(rows["E"][5])
        session.finalize()
        rows = {row[0]: row for row in stats.all_time_char_rows(stats.load_all_time())}
        self.assertAlmostEqual(rows["K"][4], 0.5)
        self.assertIsNone(rows["E"][4])
        self.assertAlmostEqual(rows["K"][5], 20.0)
        self.assertIsNone(rows["E"][5])
        self.assertIsNone(stats.measured_latency(1.0, 1, 1.0, 1))  # nur angenommene

    def test_old_all_time_without_confusions_still_works(self):
        db.save_state("all_time", {"K": {
            "good": 3, "wrong": 1, "total_reaction_time_s": 2.0, "total_effective_wpm": 80.0,
            "correct_effective_wpm_total": 60.0, "attempts": 4,
        }})
        rows = stats.all_time_char_rows(stats.load_all_time())
        self.assertEqual(rows[0][6], "")
        self.assertIsNone(rows[0][4])  # alte Daten ohne Latenz: „–“
        self._session([("K", "R")]).finalize()
        self.assertEqual(stats.load_all_time()["K"]["confusions"], {"R": 1})

    def test_damaged_all_time_entries_do_not_stop_finalize(self):
        db.save_state("all_time", {
            "K": {"good": "viel", "wrong": None, "total_reaction_time_s": [], "untimed": "x", "confusions": []},
            "M": 17,
            "R": {"good": 2, "wrong": 1},
        })
        rows = {r[0]: r for r in stats.all_time_char_rows(stats.load_all_time())}
        self.assertEqual(set(rows), {"K", "R"})  # was kein Wörterbuch ist, entfällt
        self.assertEqual(rows["R"][1:4], (2, 1, 3))
        self._session([("K", "K"), ("R", "R")]).finalize()
        summary = stats.load_all_time()
        self.assertEqual(summary["K"]["good"], 1)
        self.assertEqual(summary["R"]["good"], 3)

    def test_reset_in_the_future_is_ignored(self):
        from datetime import datetime, timedelta
        db.save_state(stats.RESET_KEY, {"time": (datetime.now() + timedelta(days=400)).isoformat()})
        cutoff = datetime.now() - timedelta(days=7)
        self.assertEqual(stats._after_reset(cutoff), cutoff)
        past = datetime.now() - timedelta(days=2)
        db.save_state(stats.RESET_KEY, {"time": past.isoformat()})
        self.assertEqual(stats._after_reset(cutoff), past)

    def test_clock_ahead_names_the_latest_start_in_the_future(self):
        from datetime import datetime, timedelta
        self.assertIsNone(stats.clock_ahead())
        db.start_session({"type": "config", "mode": "single",
                          "start_time": datetime.now().isoformat(timespec="seconds")})
        self.assertIsNone(stats.clock_ahead())
        later = (datetime.now() + timedelta(days=30)).replace(microsecond=0)
        db.start_session({"type": "config", "mode": "single", "start_time": later.isoformat()})
        self.assertEqual(stats.clock_ahead(), later)

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