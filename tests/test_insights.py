"""Auswertungen über mehrere Durchgänge (core/insights, widgets/insights_panel)."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import insights, stats
from morsetrainer.widgets import insights_panel as panel


class InsightsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(stats, "STATS_DIR", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def write(self, days_ago, rows, mode="single", **config):
        """rows: (gesendet, getippt, Zusatzfelder) – richtig, wenn gleich."""
        start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
        lines = [{"type": "config", "mode": mode, "start_time": start, "wpm": 20, **config}]
        for char, typed, extra in rows:
            entry = {"type": "char", "char": char, "typed": typed, "correct": char == typed, **extra}
            if char != typed:
                entry.setdefault("cause", "heard" if typed else "missed")
            lines.append(entry)
        tests.write_session(lines + [{"type": "summary"}])

    def test_lag_counts_characters_at_the_effective_tempo(self):
        # 20 WPM = 100 Zeichen je Minute: 1,2 s Rückstand sind 2 Zeichen.
        self.write(1, [("K", "K", {"lag_s": 1.2})] * 40, mode="continuous")
        self.write(30, [("K", "K", {"lag_s": 0.6})] * 40, mode="continuous")
        self.write(1, [("K", "K", {"lag_s": 9.0})] * 40, mode="single")  # anderer Modus zählt nicht
        lag = insights.lag_chars()
        self.assertAlmostEqual(insights.median(lag["recent"]), 2.0)
        self.assertAlmostEqual(insights.median(lag["before"]), 1.0)
        self.assertEqual(panel.lag_text(lag),
                         "Rückstand am Stück (Median): letzte 14 Tage: 2,0 Zeichen, davor: 1,0 Zeichen.")

    def test_lag_is_silent_without_enough_measurements(self):
        self.write(1, [("K", "K", {"lag_s": 1.2})] * 5, mode="continuous")
        self.write(1, [("K", "K", {})] * 40, mode="continuous")  # ältere Durchgänge ohne Rückstand
        self.assertEqual(panel.lag_text(insights.lag_chars()), "")

    def test_causes_are_split_per_week_and_small_weeks_are_not(self):
        self.write(1, [("K", "M", {})] * 6 + [("K", "", {})] * 2 + [("K", "K", {})] * 5)  # ohne Ursache aufgezeichnet
        self.write(8, [("K", "", {})] * 2)
        lines = panel.causes_text(insights.causes_by_week()).split("\n")
        self.assertEqual(len(lines), 2)  # älteste Woche zuerst
        self.assertTrue(lines[0].endswith("2 Fehler (zu wenige für eine Aufteilung)"))
        self.assertTrue(lines[1].endswith("61,5 Fehler je 100 Zeichen, davon verwechselt 75 %, nicht erkannt 25 % (8 Fehler)"))

    def test_slow_and_replayed_errors_count_as_not_recognised(self):
        rows = [("K", "M", {"cause": "swap"}), ("K", "M", {"cause": "late"}), ("K", "M", {"cause": "replay"}), ("K", "", {"cause": "missed"}),
                 ("K", "", {"cause": "late"}), ("K", "M", {"cause": "heard"})]
        self.write(1, rows)
        self.assertTrue(panel.causes_text(insights.causes_by_week()).endswith(
            "100,0 Fehler je 100 Zeichen, davon nicht erkannt 67 %, verwechselt 33 % (6 Fehler)"))

    def test_retries_do_not_count(self):
        self.write(1, [("K", "M", {"retry": True})] * 10)
        self.assertEqual(insights.causes_by_week(), [])

    def test_fatigue_compares_first_and_last_third(self):
        for day in range(1, 11):
            first = [("K", "K", {})] * 10
            middle = [("K", "K", {})] * 8 + [("K", "M", {})] * 2
            last = [("K", "K", {})] * 6 + [("K", "M", {})] * 4
            self.write(day, first + middle + last)
        text = panel.fatigue_text(insights.fatigue())
        self.assertIn("Erstes Drittel: 100 % richtig", text)
        self.assertIn("Letztes Drittel: 60 % richtig", text)
        self.assertTrue(text.endswith("könnten sich lohnen."))

    def test_fatigue_needs_enough_long_runs(self):
        self.write(1, [("K", "K", {})] * 40)
        self.write(2, [("K", "K", {})] * 10)  # zu kurz
        self.assertEqual(panel.fatigue_text(insights.fatigue()), "")

    def test_pairs_compare_recent_with_before(self):
        self.write(40, [("D", "U", {})] * 4 + [("D", "D", {})] * 16
                   + [("U", "U", {})] * 10)   # davor 20 % von 20, U kam auch vor
        self.write(2, [("D", "U", {})] * 1 + [("D", "D", {})] * 19)    # zuletzt 5 %
        self.write(2, [("K", "M", {})] * 1 + [("K", "K", {})] * 2)     # zu wenig Vorkommen
        text = panel.pairs_text(insights.confusion_trend())
        self.assertIn("D → U: davor 20 % (von 20), zuletzt 5 % (von 20): seltener", text)
        self.assertNotIn("(häufiger)", text)

    def test_pairs_count_old_errors_without_a_stored_cause(self):
        def old(days_ago, rows):  # Durchgang aus der Zeit vor der Ursachenangabe
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": "single", "start_time": start, "wpm": 20}]
            lines += [{"type": "char", "char": c, "typed": t, "correct": c == t} for c, t in rows]
            tests.write_session(lines + [{"type": "summary"}])
        old(40, [("B", "6")] * 4 + [("B", "B")] * 16 + [("6", "6")] * 10)
        self.write(2, [("B", "6", {})] * 2 + [("B", "B", {})] * 18 + [("6", "6", {})] * 10)
        self.assertIn("B → 6: davor 20 % (von 20), zuletzt 10 % (von 20): seltener", panel.pairs_text(insights.confusion_trend()))

    def test_pairs_with_too_few_cases_are_not_compared(self):
        self.write(40, [("D", "U", {})] * 4 + [("D", "D", {})] * 11 + [("U", "U", {})] * 10)  # 15 Fälle: zu wenig
        self.write(2, [("D", "U", {})] * 1 + [("D", "D", {})] * 19)
        self.assertIn("D → U: 5-mal verwechselt, für den Vergleich zu wenig Daten",
                      panel.pairs_text(insights.confusion_trend()))

    def test_pair_with_a_character_not_seen_before_is_new(self):
        self.write(40, [("K", "K", {})] * 20)
        self.write(2, [("B", "6", {})] * 3 + [("B", "B", {})] * 17)
        text = panel.pairs_text(insights.confusion_trend())
        self.assertIn("B → 6: neu dabei, zuletzt 15 %", text)
        self.assertNotIn("häufiger", text)


if __name__ == "__main__":
    unittest.main()
