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

    def test_lag_counts_each_run_once_with_its_median(self):
        for day in range(5):
            # Jeder Lauf: 10 Zeichen mit Rückstand, eines davon ohne Taste (nicht getippt)
            self.write(1 + day, [("K", "K", {"lag_chars": 2.0})] * 9 + [("K", "", {"lag_chars": 4.0})],
                       mode="continuous")
            self.write(30 + day, [("K", "K", {"lag_chars": 1.0})] * 10, mode="continuous")
        self.write(1, [("K", "K", {"lag_chars": 9.0})] * 40, mode="single")  # anderer Modus zählt nicht
        lag = insights.lag_chars()
        self.assertEqual((lag["recent"], lag["before"]), ([2.0] * 5, [1.0] * 5))
        self.assertEqual(panel.lag_text(lag),
                         "Rückstand am Stück (Median der Durchgänge): letzte 14 Tage: 2,0 Zeichen, 90 % richtig, "
                         "10 % nicht getippt (aus 5 Durchgängen), früher: 1,0 Zeichen, 100 % richtig, "
                         "0 % nicht getippt (aus 5 Durchgängen).")

    def test_a_single_long_run_is_not_enough_for_the_lag(self):
        self.write(1, [("K", "K", {"lag_chars": 1.2})] * 150, mode="continuous")  # ein Lauf, viele Werte
        self.write(1, [("K", "K", {})] * 40, mode="continuous")  # Durchgang ohne Rückstand
        self.assertEqual(panel.lag_text(insights.lag_chars()), "")

    def test_lag_ignores_unusable_values(self):
        rows = [("K", "K", {"lag_chars": value}) for value in (True, -1, float("inf"), "2", None, [1])] * 6
        for day in range(6):
            self.write(1 + day, rows, mode="continuous")
        self.assertEqual(insights.lag_chars()["recent"], [])

    def test_causes_are_split_per_week_and_small_weeks_are_not(self):
        self.write(1, [("K", "M", {})] * 6 + [("R", "", {})] * 2 + [("K", "K", {})] * 5)  # ohne Ursache aufgezeichnet
        self.write(8, [("K", "", {})] * 2)
        lines = panel.causes_text(insights.causes_by_week()).split("\n")
        self.assertEqual(len(lines), 2)  # älteste Woche zuerst
        self.assertTrue(lines[0].endswith("2 Fehler (zu wenige für eine Aufteilung)"))
        self.assertTrue(lines[1].endswith("61,5 Fehler je 100 Zeichen, davon verwechselt 75 %, nicht erkannt 25 % "
                                          "(8 Fehler); nicht erkannt vor allem: R"))

    def test_the_running_week_is_marked(self):
        self.write(0, [("K", "", {})] * 6)
        self.assertIn("(läuft noch)", panel.causes_text(insights.causes_by_week()))

    def test_error_kinds_are_mixed_up_swapped_or_not_recognised(self):
        rows = [("K", "M", {"cause": "swap"}), ("K", "M", {"cause": "late"}), ("K", "M", {"cause": "replay"}),
                ("K", "", {"cause": "missed"}), ("K", "", {"cause": "late"}), ("K", "M", {"cause": "heard"})]
        self.write(1, rows)
        self.assertTrue(panel.causes_text(insights.causes_by_week()).endswith(
            "100,0 Fehler je 100 Zeichen, davon nicht erkannt 67 %, vertauscht 17 %, verwechselt 17 % "
            "(6 Fehler); nicht erkannt vor allem: K"))

    def test_weak_characters_need_enough_unrecognised_errors(self):
        self.write(1, [("X", "", {})] * 5 + [("Ä", "", {})] * 4 + [("6", "B", {})] * 9 + [("K", "K", {})] * 5)
        self.assertEqual(insights.weak_chars(), [("X", 5)])  # Ä zu selten, 6 wurde verwechselt

    def test_retries_do_not_count(self):
        self.write(1, [("K", "M", {"retry": True})] * 10)
        self.assertEqual(insights.causes_by_week(), [])

    def _fatigue_sessions(self, count, drop_every=1):
        for day in range(1, count + 1):
            first = [("K", "K", {})] * 10
            middle = [("K", "K", {})] * 8 + [("K", "M", {})] * 2
            last = [("K", "K", {})] * 6 + [("K", "M", {})] * 4
            if drop_every == 1 or day % drop_every:
                self.write(day, first + middle + last)
            else:  # Durchgang ohne Abfall, mit wechselnder Richtung
                self.write(day, last + middle + first)

    def test_fatigue_gives_the_drop_with_a_range_and_a_verdict_only_from_enough_runs(self):
        self._fatigue_sessions(10)
        text = panel.fatigue_text(insights.fatigue())
        self.assertIn("Erstes Drittel: 100 % richtig", text)
        self.assertIn("Letztes Drittel: 60 % richtig", text)
        self.assertIn("Erstes minus letztes Drittel: 40,0 Punkte (zwischen +40 und +40)", text)
        self.assertTrue(text.endswith("Für ein Urteil zum Nachlassen sind es noch zu wenige Durchgänge (ab 30)."))
        self._fatigue_sessions(30)
        text = panel.fatigue_text(insights.fatigue())
        self.assertTrue(text.endswith("könnten sich lohnen."))

    def test_fatigue_with_mixed_runs_has_no_reliable_verdict(self):
        self._fatigue_sessions(30, drop_every=2)  # jeder zweite Lauf umgekehrt: Mittel 0, große Streuung
        text = panel.fatigue_text(insights.fatigue())
        self.assertIn("Erstes minus letztes Drittel: 0,0 Punkte", text)
        self.assertTrue(text.endswith("Kein sicheres Nachlassen erkennbar."))

    def test_spoken_week_line_spells_the_characters(self):
        # „=“ oder „.“ liest die Stimme nicht; buchstabiert klingt es wie bei den anderen Zeichen.
        self.write(1, [("=", "", {})] * 5 + [("K", "K", {})] * 20)
        week = insights.causes_by_week()[-1]
        self.assertIn("nicht erkannt vor allem: =", panel._week_line(week))
        self.assertIn("nicht erkannt vor allem: Trennung", panel._week_line(week, spoken=True))

    def test_fatigue_is_calculated_per_mode(self):
        for day in range(1, 11):  # Einzeln: deutlicher Abfall
            self.write(day, [("K", "K", {})] * 10 + [("K", "K", {})] * 10 + [("K", "M", {})] * 10, mode="single")
        for day in range(1, 11):  # Gruppen: kein Abfall
            self.write(day, [("K", "K", {})] * 30, mode="group")
        for day in range(1, 6):   # Am Stück: zu wenige Durchgänge
            self.write(day, [("K", "K", {})] * 30, mode="continuous")
        by_mode = insights.fatigue_by_mode()
        self.assertEqual(sorted(by_mode), ["group", "single"])
        text = panel.fatigue_text_by_mode(panel.fatigue_blocks(by_mode))
        self.assertIn("Einzeln:\nErstes Drittel: 100 % richtig", text)
        self.assertIn("Gruppen:\nErstes Drittel: 100 % richtig", text)
        self.assertNotIn("Am Stück", text)
        groups, single = text.split("Gruppen:")[1].split("Einzeln:")  # gleich viele Durchgänge: nach Namen
        self.assertIn("Letztes Drittel: 100 % richtig", groups)
        self.assertIn("Letztes Drittel: 0 % richtig", single)  # der Abfall gehört nur zu Einzeln

    def test_fatigue_needs_enough_long_runs(self):
        self.write(1, [("K", "K", {})] * 40)
        self.write(2, [("K", "K", {})] * 10)  # zu kurz
        self.assertEqual(panel.fatigue_text(insights.fatigue()), "")

    def test_pairs_compare_recent_with_before(self):
        self.write(40, [("D", "U", {})] * 8 + [("D", "D", {})] * 32 + [("U", "U", {})] * 10)  # davor 20 % von 40
        self.write(2, [("D", "U", {})] * 2 + [("D", "D", {})] * 38)                        # zuletzt 5 % von 40
        self.write(2, [("K", "M", {})] * 1 + [("K", "K", {})] * 2)                         # zu wenig Vorkommen
        text = panel.pairs_text(insights.confusion_trend())
        self.assertIn("D als U getippt: seltener\n    früher 20 % (8 von 40), zuletzt 5 % (2 von 40)", text)
        self.assertNotIn("häufiger", text)
        spoken = panel.pairs_text(insights.confusion_trend(), spoken=True)  # eine Zeile je Paar für die Stimme
        self.assertNotIn("\n    ", spoken)
        self.assertIn("früher 20 % (8 von 40), zuletzt 5 % (2 von 40): seltener", spoken)

    def test_a_difference_within_chance_is_not_reported(self):
        def old(days_ago, rows):  # Durchgang aus der Zeit vor der Ursachenangabe
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            lines = [{"type": "config", "mode": "single", "start_time": start, "wpm": 20}]
            lines += [{"type": "char", "char": c, "typed": t, "correct": c == t} for c, t in rows]
            tests.write_session(lines + [{"type": "summary"}])
        old(40, [("B", "6")] * 8 + [("B", "B")] * 32 + [("6", "6")] * 10)  # auch ohne Ursache gezählt
        self.write(2, [("B", "6", {})] * 4 + [("B", "B", {})] * 36 + [("6", "6", {})] * 10)
        rows = insights.confusion_trend()
        self.assertEqual(insights.pair_verdict(rows[0]), insights.UNSURE)  # 10 Punkte, aber bei 40 Fällen Zufall
        self.assertIn("B als 6 getippt: kein sicherer Unterschied\n    früher 20 % (8 von 40), zuletzt 10 % (4 von 40)",
                      panel.pairs_text(rows))

    def test_small_differences_are_unchanged_and_big_ones_clear(self):
        row = {"before": 10.0, "recent": 11.0, "n_before": 5000, "n_recent": 5000}
        self.assertEqual(insights.pair_verdict(row), insights.SAME)
        self.assertEqual(insights.pair_verdict({**row, "n_before": 300, "n_recent": 300}), insights.UNSURE)  # zu ungenau
        self.assertEqual(insights.pair_verdict({**row, "recent": 20.0}), insights.MORE)
        self.assertEqual(insights.pair_verdict({**row, "before": 20.0, "recent": 10.0}), insights.LESS)

    def test_a_difference_resting_on_a_single_case_is_not_reported(self):
        row = {"before": 7 / 103 * 100, "recent": 1 / 99 * 100, "n_before": 103, "n_recent": 99}  # 7 gegen 1 Fall
        self.assertEqual(insights.pair_verdict(row), insights.UNSURE)

    def test_both_directions_of_a_pair_stay_together(self):
        self.write(40, [("B", "6", {})] * 4 + [("B", "B", {})] * 36 + [("6", "B", {})] * 8 + [("6", "6", {})] * 32)
        self.write(2, [("B", "6", {})] * 4 + [("B", "B", {})] * 36 + [("6", "B", {})] * 8 + [("6", "6", {})] * 32)
        self.write(2, [("D", "U", {})] * 3 + [("D", "D", {})] * 37 + [("U", "U", {})] * 40)
        lines = panel.pairs_text(insights.confusion_trend()).split("\n")
        heads = [line for line in lines if not line.startswith(" ")]  # die Zahlen stehen eingerückt darunter
        self.assertEqual([line.split(":")[0] for line in heads], ["6 als B getippt", "B als 6 getippt", "D als U getippt"])
        self.assertTrue(lines[1].startswith("    früher"))  # „neu dabei“ (D → U) hat nur eine Zeile
        self.assertEqual(panel.pair_chars(insights.confusion_trend()), "6BDU")

    def test_pairs_with_too_few_cases_are_not_compared(self):
        self.write(40, [("D", "U", {})] * 4 + [("D", "D", {})] * 11 + [("U", "U", {})] * 10)  # 15 Fälle: zu wenig
        self.write(2, [("D", "U", {})] * 1 + [("D", "D", {})] * 19)
        self.assertIn("D als U getippt: 5-mal verwechselt, für den Vergleich zu wenig Daten",
                      panel.pairs_text(insights.confusion_trend()))

    def test_pair_with_a_character_not_seen_before_is_new(self):
        self.write(40, [("K", "K", {})] * 20)
        self.write(2, [("B", "6", {})] * 3 + [("B", "B", {})] * 17)
        text = panel.pairs_text(insights.confusion_trend())
        self.assertIn("B als 6 getippt: neu dabei, zuletzt 15 %", text)
        self.assertNotIn("häufiger", text)

    def test_fatigue_ignores_characters_without_timing(self):
        for day in range(1, 11):
            self.write(day, [("K", "K", {})] * 30 + [("K", "M", {"untimed": True})] * 60)
        text = panel.fatigue_text(insights.fatigue())
        self.assertIn("Letztes Drittel: 100 % richtig", text)

    def test_wobbly_characters_dropped_two_boxes_from_box_three_or_higher(self):
        data = {"6": {"due": "2026-10-01", "box": 0, "best_box": 4},       # Fach 5 -> 1
                "X": {"due": "2026-10-01", "box": 2, "best_box": 4},       # Fach 5 -> 3
                "I": {"due": "2026-10-01", "box": 0, "best_box": 2},       # Fach 3 -> 1
                "K": {"due": "2026-10-01", "box": 0, "best_box": 1},       # Fach 2 -> 1: normales Hin und Her
                "A": {"due": "2026-10-01", "box": 1, "best_box": 2},       # Fach 3 -> 2: nur ein Fach
                "R": {"due": "2026-10-01", "box": 3, "best_box": 4},       # nur ein Fach
                "M": {"box": 0, "best_box": 5}}                            # nicht in der Kartei
        rows = insights.wobbly(data)
        self.assertEqual(rows, [("6", 5, 1), ("I", 3, 1), ("X", 5, 3)])
        self.assertEqual(panel.wobbly_text(rows), "6 (Fach 5 → 1), I (Fach 3 → 1), X (Fach 5 → 3)")

    def test_the_first_week_is_marked_when_the_data_start_mid_week(self):
        # Der erste Tag muss ein Mittwoch sein, sonst ist die Woche je nach Wochentag des Testlaufs vollständig.
        wednesday = (datetime.now().weekday() - 2) % 7 + 7
        self.write(0, [("K", "", {})] * 6)
        self.write(wednesday, [("K", "", {})] * 6)
        weeks = insights.causes_by_week()
        self.assertTrue(weeks[0]["partial"])
        self.assertFalse(weeks[-1]["partial"])
        self.assertIn("(unvollständig, Daten erst ab Wochenmitte)", panel.causes_text(weeks).split("\n")[0])

    def test_wobbly_stays_empty_with_a_hint_until_a_high_box_is_reached(self):
        self.assertFalse(insights.reached_high_box({"K": {"due": "2026-10-01", "box": 1, "best_box": 1}}))
        self.assertTrue(insights.reached_high_box({"K": {"due": "2026-10-01", "box": 0, "best_box": 2}}))
        self.assertFalse(insights.reached_high_box({"K": {"box": 0, "best_box": 5}}))  # nicht in der Kartei

    def test_characters_over_time_need_enough_answers_on_both_sides(self):
        self.write(40, [("6", "B", {})] * 30 + [("6", "6", {})] * 50 + [("K", "K", {})] * 10)
        self.write(2, [("6", "B", {})] * 20 + [("6", "6", {})] * 60 + [("K", "K", {})] * 50)
        rows = insights.char_trend()
        self.assertEqual([row["char"] for row in rows], ["6"])  # K hatte davor zu wenige Antworten
        self.assertEqual((rows[0]["n_before"], rows[0]["n_recent"]), (80, 80))
        self.assertEqual(panel.chars_text(rows),
                         "6 (Einzeln): kein sicherer Unterschied\n"
                         "    früher 38 % falsch (30 von 80), zuletzt 25 % (20 von 80)")
        self.assertEqual(panel.chars_text(rows, spoken=True).replace("Sechs", "6"),
                         "6 (Einzeln): früher 38 % falsch (30 von 80), zuletzt 25 % (20 von 80): kein sicherer Unterschied")

    def _six_sessions(self, days_ago, wrong_per_session, mode="single", count=5):
        for day in range(count):
            wrong = wrong_per_session[day % len(wrong_per_session)]
            self.write(days_ago + day, [("6", "B", {})] * wrong + [("6", "6", {})] * (20 - wrong), mode=mode)

    def test_a_clear_change_of_a_character_is_named(self):
        self._six_sessions(40, [14])  # davor 70 % falsch in jedem Durchgang
        self._six_sessions(2, [6])    # zuletzt 30 %
        self.assertIn("6 (Einzeln): weniger Fehler\n", panel.chars_text(insights.char_trend()))

    def test_one_session_per_side_is_never_a_clear_change(self):
        # Die Antworten eines Durchgangs hängen zusammen; mit einem Durchgang je Seite ist die Streuung
        # unbekannt, auch bei 70 % gegen 30 %.
        self.write(40, [("6", "B", {})] * 70 + [("6", "6", {})] * 30)
        self.write(2, [("6", "B", {})] * 30 + [("6", "6", {})] * 70)
        self.assertEqual(insights.char_trend()[0]["verdict"], insights.UNSURE)

    def test_swinging_sessions_are_no_clear_change_although_the_pooled_numbers_look_clear(self):
        self._six_sessions(40, [20, 0], count=6)   # davor 50 %, aber mal alles, mal nichts falsch
        self._six_sessions(2, [12, 0], count=6)    # zuletzt 30 %
        row = insights.char_trend()[0]
        self.assertEqual((row["before"], row["recent"]), (50.0, 30.0))
        self.assertEqual(insights.rate_verdict(row["before"], row["recent"], row["n_before"], row["n_recent"]),
                         insights.LESS)  # Antworten einzeln gezählt: scheinbar klar
        self.assertEqual(row["verdict"], insights.UNSURE)  # Durchgänge gezählt: nicht belegt

    def test_characters_are_compared_per_mode(self):
        # Davor nur in Gruppen, zuletzt nur am Stück: kein Vergleich, der den Modus-Wechsel als Fortschritt zeigt.
        self._six_sessions(40, [14], mode="group")
        self._six_sessions(2, [6], mode="continuous")
        self.assertEqual(insights.char_trend(), [])
        # Mit beiden Zeiträumen in beiden Modi: je Modus eine Zeile mit eigenem Urteil.
        self._six_sessions(40, [14], mode="continuous")
        self._six_sessions(2, [14], mode="group")
        rows = {row["mode"]: row["verdict"] for row in insights.char_trend()}
        self.assertEqual(rows, {"continuous": insights.LESS, "group": insights.SAME})
        text = panel.chars_text(insights.char_trend())
        self.assertIn("6 (Am Stück): weniger Fehler", text)
        self.assertIn("6 (Gruppen): unverändert", text)

    def test_unexpected_values_in_old_lines_do_not_break_the_insights(self):
        start = datetime.now().isoformat(timespec="seconds")
        lines = [{"type": "config", "mode": "continuous", "start_time": start, "wpm": float("inf")}]
        lines += [{"type": "char", "char": 5, "typed": "N", "correct": False},
                  {"type": "char", "char": ["K"], "typed": "N", "correct": False},
                  {"type": "char", "char": "K", "typed": 5, "correct": False, "cause": ["x"]},
                  {"type": "char", "char": "K", "typed": ["N"], "correct": False, "cause": 7},
                  {"type": "char", "char": "K", "typed": None, "correct": None, "lag_chars": [1]},
                  {"type": "char", "char": None}]
        tests.write_session(lines + [{"type": "summary"}])
        data = insights.load()
        insights.lag_chars(data), insights.causes_by_week(data), insights.weak_chars(data)
        insights.fatigue(data), insights.confusion_trend(data)

    def test_loading_reaches_back_exactly_the_insight_days(self):
        self.write(89.5, [("K", "K", {})])
        self.write(90.5, [("K", "K", {})])
        self.assertEqual(len(insights.load()), 1)


NOW = datetime(2026, 11, 25, 12, 0)  # ein Mittwoch


def _row(char, typed, extra=None):
    extra = extra or {}
    row = {"type": "char", "char": char, "typed": typed, "correct": char == typed, **extra}
    if char != typed:
        row.setdefault("cause", "heard" if typed else "missed")
    return row


def _session(days_ago, rows, mode="single"):
    """Ein Durchgang so, wie insights.load() ihn liefert: (Startzeit, Konfiguration, Zeichen-Zeilen)."""
    return NOW - timedelta(days=days_ago), {"mode": mode}, [_row(*row) for row in rows]


class InsightsLimitsTest(unittest.TestCase):
    """Die Schwellen der Auswertungen auf den Wert genau: eine Stufe darunter noch kein Urteil,
    auf dem Wert das Urteil."""

    def test_weeks_shown(self):
        data = [_session(7 * week, [("K", "", {})] * 6) for week in range(8)]
        self.assertEqual(len(insights.causes_by_week(data, NOW)), 6)

    def test_lag_needs_enough_values_per_run(self):
        short = _session(1, [("K", "K", {"lag_chars": 1.0})] * 9, "continuous")
        enough = _session(1, [("K", "K", {"lag_chars": 3.0})] * 10, "continuous")
        self.assertEqual(insights.lag_chars([short, enough], NOW)["recent"], [3.0])

    def test_lag_is_shown_from_enough_runs_per_side(self):
        lag = {"recent": [2.0] * 4, "before": [1.0] * 5}
        text = panel.lag_text(lag)
        self.assertNotIn("letzte 14 Tage", text)
        self.assertIn("früher: 1,0 Zeichen", text)

    def _week_text(self, rows):
        return panel.causes_text(insights.causes_by_week([_session(1, rows)], NOW))

    def test_a_week_is_split_from_enough_errors(self):
        self.assertIn("zu wenige für eine Aufteilung",
                      self._week_text([("K", "M", {})] * 4 + [("K", "K", {})] * 20))
        self.assertIn("Fehler je 100 Zeichen",
                      self._week_text([("K", "M", {})] * 5 + [("K", "K", {})] * 20))

    def test_a_week_names_the_most_frequent_unrecognised_characters(self):
        text = self._week_text([(char, "", {}) for char in "KKKKRRRMMSS"])
        self.assertTrue(text.endswith("nicht erkannt vor allem: K, R, M"), text)  # S ist das vierte
        text = self._week_text([("K", "", {})] * 4 + [("R", "", {})] * 1)
        self.assertTrue(text.endswith("nicht erkannt vor allem: K"), text)  # R nur einmal

    def test_a_run_needs_enough_characters_for_the_thirds(self):
        short = _session(1, [("K", "K", {})] * 29)
        long = _session(1, [("K", "K", {})] * 30)
        self.assertEqual(insights.fatigue([short, long], NOW)["sessions"], 1)

    def test_a_mode_needs_enough_runs_for_the_fatigue(self):
        runs = [_session(day, [("K", "K", {})] * 30) for day in range(10)]
        self.assertEqual(list(insights.fatigue_by_mode(runs[:-1], NOW)), [])
        self.assertEqual(list(insights.fatigue_by_mode(runs, NOW)), ["single"])

    def test_weak_characters_are_limited(self):
        data = [_session(1, [(char, "", {}) for char in "ABCDEF" * 5])]
        self.assertEqual(len(insights.weak_chars(data, NOW)), 5)

    def test_pair_rates_need_enough_cases_of_the_sent_character(self):
        def rows(n):
            return [("D", "U", {})] * 3 + [("D", "D", {})] * (n - 3)
        few = insights.confusion_trend([_session(40, rows(19)),
                                        _session(2, rows(20))], NOW)[0]
        self.assertIsNone(few["before"])
        self.assertIsNotNone(few["recent"])
        enough = insights.confusion_trend([_session(40, rows(20))], NOW)[0]
        self.assertIsNotNone(enough["before"])

    def test_pairs_are_limited(self):
        pairs = ("DU", "B6", "SH", "V4")
        data = [_session(2, [(sent, typed, {}) for sent, typed in pairs for _ in range(3)])]
        rows = insights.confusion_trend(data, NOW)
        self.assertEqual(len({frozenset((row["sent"], row["typed"])) for row in rows}), 3)

    def test_a_rate_changes_from_the_smallest_difference(self):
        big = 100000  # so genau, dass nur die Mindestdifferenz entscheidet
        self.assertEqual(insights.rate_verdict(10.0, 13.0, big, big), insights.MORE)
        self.assertEqual(insights.rate_verdict(13.0, 10.0, big, big), insights.LESS)
        self.assertEqual(insights.rate_verdict(10.0, 12.9, big, big), insights.SAME)

    def test_a_rate_change_must_exceed_the_noise_twice(self):
        # 5 Punkte Unterschied: bei 224 Fällen je Seite 1,6 Standardfehler, bei 504 Fällen 2,4
        self.assertEqual(insights.rate_verdict(10.0, 15.0, 224, 224), insights.UNSURE)
        self.assertEqual(insights.rate_verdict(10.0, 15.0, 504, 504), insights.MORE)

    def test_a_rate_change_needs_enough_expected_cases(self):
        self.assertEqual(insights.rate_verdict(0.0, 40.0, 25, 25), insights.MORE)    # erwartet 5,0 je Seite
        self.assertEqual(insights.rate_verdict(0.0, 40.0, 22, 22), insights.UNSURE)  # erwartet 4,4

    def test_unchanged_needs_a_narrow_interval(self):
        self.assertEqual(insights.rate_verdict(10.0, 10.0, 2400, 2400), insights.SAME)    # Breite 1,7 Punkte
        self.assertEqual(insights.rate_verdict(10.0, 10.0, 1100, 1100), insights.UNSURE)  # Breite 2,5 Punkte

    def test_a_character_needs_enough_sessions_on_each_side(self):
        before, recent = [(14, 20)], [(6, 20)]
        self.assertEqual(insights.cluster_verdict(before * 2, recent * 2), insights.UNSURE)
        self.assertEqual(insights.cluster_verdict(before * 3, recent * 3), insights.LESS)

    def test_a_character_changes_from_the_smallest_difference(self):
        self.assertEqual(insights.cluster_verdict([(10, 100)] * 3, [(13, 100)] * 3), insights.MORE)
        self.assertEqual(insights.cluster_verdict([(10, 100)] * 3, [(129, 1000)] * 3), insights.SAME)

    def test_a_character_is_unchanged_only_with_a_narrow_interval(self):
        narrow = [(9, 90), (10, 90), (11, 90)]    # Intervall 1,8 Punkte breit
        wide = [(10, 130), (12, 130), (14, 130)]  # Intervall 2,5 Punkte breit
        self.assertEqual(insights.cluster_verdict(narrow, narrow), insights.SAME)
        self.assertEqual(insights.cluster_verdict(wide, wide), insights.UNSURE)

    def test_a_character_needs_enough_answers_on_each_side(self):
        def rows(n):
            return [("6", "B", {})] * (n // 2) + [("6", "6", {})] * (n - n // 2)
        enough = 40
        self.assertEqual(len(insights.char_trend([_session(40, rows(enough)), _session(2, rows(enough))], NOW)), 1)
        self.assertEqual(insights.char_trend([_session(40, rows(39)), _session(2, rows(enough))], NOW), [])
        self.assertEqual(insights.char_trend([_session(40, rows(enough)), _session(2, rows(39))], NOW), [])

    def test_characters_over_time_are_limited(self):
        rows = [(char, "", {}) for char in "ABCDEFG" for _ in range(40)]
        data = [_session(40, rows), _session(2, rows)]
        self.assertEqual(len(insights.char_trend(data, NOW)), 6)


if __name__ == "__main__":
    unittest.main()
