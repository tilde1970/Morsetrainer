"""Tests für die Lernhilfen: Koch-Lektionen, Wörter, Auswertung von
Gruppen per Alignment und die mitwachsende Gruppenlänge."""
import tempfile
import unittest
from pathlib import Path

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import align, koch, words
from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.modes.group_mode import LONGER_AFTER, SHORTER_AFTER, AdaptiveLength


class KochTest(unittest.TestCase):
    def test_lessons(self):
        self.assertEqual(koch.lesson_charset(1), "KM")
        self.assertEqual(koch.lesson_charset(koch.MAX_LESSON), koch.KOCH_ORDER)
        self.assertEqual(koch.lesson_of("KMU"), 2)
        self.assertIsNone(koch.lesson_of("KMX"))
        self.assertIsNone(koch.lesson_of("K"))
        self.assertEqual(koch.newest_char(2), "U")
        self.assertTrue(all(ch in MORSE_CODE for ch in koch.KOCH_ORDER))

    def test_advance_needs_accuracy_and_enough_chars(self):
        self.assertTrue(koch.can_advance("KMU", 90, 100))
        self.assertFalse(koch.can_advance("KMU", 89, 100))
        self.assertFalse(koch.can_advance("KMU", 10, 10))
        self.assertFalse(koch.can_advance("ABC", 100, 100))
        self.assertFalse(koch.can_advance(koch.KOCH_ORDER, 100, 100))


class WordsTest(unittest.TestCase):
    def test_all_words_are_sendable(self):
        for word in words.WORDS:
            self.assertTrue(word and all(ch in MORSE_CODE for ch in word), word)

    def test_only_words_from_charset(self):
        found = words.words_for_charset(koch.lesson_charset(8))
        self.assertIn("NAME", found)
        self.assertNotIn("TNX", found)
        self.assertEqual(words.words_for_charset("KM"), [])
        self.assertEqual(words.words_for_charset(koch.KOCH_ORDER), sorted(words.WORDS))

    def test_user_words_are_parsed(self):
        found, skipped = words.parse_user_words(
            "# Kommentar\n\ndok = Distrikts-Ortsverbandskenner\nOelde\nGrüße\nGOOD LUCK\nA=B = C\nÄ€\n"
        )
        self.assertEqual(found, {"DOK": "Distrikts-Ortsverbandskenner", "OELDE": "", "GRUESSE": "", "A": "B = C"})
        self.assertEqual(skipped, ["GOOD LUCK", "Ä€"])

    def test_user_words_extend_builtin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "woerter.txt"
            combined, user, _ = words.load_words(path)
            self.assertEqual((combined, user), (words.WORDS, {}))
            words.ensure_user_file(path)
            self.assertEqual(words.load_words(path)[1], {})  # Vorlage enthält nur Kommentare
            path.write_text("UFB = super\nTNX\nQTH = mein Standort\n", encoding="utf-8")
            combined, user, _ = words.load_words(path)
            self.assertEqual(len(user), 3)
            self.assertEqual(combined["UFB"], "super")
            self.assertEqual(combined["TNX"], words.WORDS["TNX"])  # ohne Bedeutung bleibt die eingebaute
            self.assertEqual(combined["QTH"], "mein Standort")
            self.assertIn("UFB", words.words_for_charset("UFB", combined))

    def test_picker_avoids_direct_repeat(self):
        picker = words.WordPicker(["ES", "UR"])
        picks = [picker.pick() for _ in range(20)]
        self.assertTrue(all(a != b for a, b in zip(picks, picks[1:])))


class GroupScoringTest(unittest.TestCase):
    def test_missed_char_is_one_error(self):
        results = align.char_results("KMR", "KR")
        self.assertEqual([(exp, got) for exp, got, _ in results], [("K", "K"), ("M", ""), ("R", "R")])
        self.assertEqual(results[2][2], 1)  # R steht im getippten Text an Stelle 1

    def test_extra_char_is_ignored(self):
        results = align.char_results("KM", "KXM")
        self.assertEqual([got for _, got, _ in results], ["K", "M"])

    def test_diff_rows(self):
        sent, typed, marks = align.diff_rows("KMUR", "KUS")
        self.assertEqual(sent, "K M U R")
        self.assertEqual(typed, "K – U S")
        self.assertEqual(marks, "  ^   ^")


class AdaptiveLengthTest(unittest.TestCase):
    def test_grows_after_streak_and_shrinks_after_errors(self):
        length = AdaptiveLength(2, 4)
        for _ in range(LONGER_AFTER - 1):
            self.assertEqual(length.update(True, 1), 0)
        self.assertEqual(length.update(True, 1), 1)
        self.assertEqual(length.length, 3)
        for _ in range(SHORTER_AFTER - 1):
            self.assertEqual(length.update(False, 1), 0)
        self.assertEqual(length.update(False, 2), -1)
        self.assertEqual(length.length, 2)

    def test_success_after_repeat_breaks_streak(self):
        length = AdaptiveLength(2, 5)
        for _ in range(LONGER_AFTER - 1):
            length.update(True, 1)
        length.update(True, 2)
        self.assertEqual(length.update(True, 1), 0)

    def test_stays_in_range(self):
        length = AdaptiveLength(2, 2, start=7)
        self.assertEqual(length.length, 2)
        for _ in range(3 * LONGER_AFTER):
            length.update(True, 1)
        self.assertEqual(length.length, 2)
        for _ in range(3 * SHORTER_AFTER):
            length.update(False, 1)
        self.assertEqual(length.length, 2)


class PracticeTest(unittest.TestCase):
    def test_streak_counts_days_with_goal(self):
        from datetime import date
        from morsetrainer.core import practice
        today = date(2026, 9, 26)
        data = {"2026-09-23": 900, "2026-09-24": 900, "2026-09-25": 1000, "2026-09-26": 300}
        # Heute noch nicht erreicht: Serie bis gestern bleibt stehen.
        self.assertEqual(practice.streak(data, 900, today), 3)
        data["2026-09-26"] = 950
        self.assertEqual(practice.streak(data, 900, today), 4)
        data["2026-09-24"] = 100
        self.assertEqual(practice.streak(data, 900, today), 2)
        # Ohne Ziel zählt jeder Tag mit Übung.
        self.assertEqual(practice.streak(data, 0, today), 4)
        self.assertEqual(practice.streak({}, 900, today), 0)

    def test_add_accumulates(self):
        from datetime import date
        from unittest import mock
        from morsetrainer.core import practice, stats
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(stats, "STATS_DIR", Path(tmp)):
            day = date(2026, 9, 26)
            practice.add(60, day)
            practice.add(30.5, day)
            practice.add(-5, day)
            self.assertEqual(practice.seconds_on(practice.load(), day), 90.5)


class VariationTest(unittest.TestCase):
    def test_vary_voice_stays_in_range(self):
        import random
        from morsetrainer.core.morse import vary_voice
        rng = random.Random(1)
        for _ in range(200):
            wpm, freq = vary_voice(20, 950, rng)
            self.assertTrue(18 <= wpm <= 22)
            self.assertTrue(850 <= freq <= 1000)
        self.assertGreaterEqual(vary_voice(5, 300, rng)[0], 5)

    def test_band_preset_adds_lead_in_and_stays_in_range(self):
        import numpy as np
        from morsetrainer.core import band
        from morsetrainer.core.morse import SAMPLE_RATE, build_text
        samples = build_text("KM", 20, 600)
        for preset in band.PRESETS:
            mixed, lead = band.apply_preset(band.preset_conditions(preset, 600), samples)
            extra = sum(band.PRESET_LEAD_SECONDS) * SAMPLE_RATE
            self.assertAlmostEqual(len(mixed), len(samples) + extra, delta=2)
            self.assertEqual(lead, band.PRESET_LEAD_SECONDS[0])
            self.assertLessEqual(float(np.max(np.abs(mixed))), 1.0)


class IcrLimitTest(unittest.TestCase):
    def test_limit_adapts_within_range(self):
        from morsetrainer.modes.single_mode import ICR_RANGE, ICR_START, next_limit
        self.assertLess(next_limit(ICR_START, True), ICR_START)
        self.assertGreater(next_limit(ICR_START, False), ICR_START)
        limit = ICR_START
        for _ in range(200):
            limit = next_limit(limit, True)
        self.assertEqual(limit, ICR_RANGE[0])
        for _ in range(200):
            limit = next_limit(limit, False)
        self.assertEqual(limit, ICR_RANGE[1])


class TempoHistoryTest(unittest.TestCase):
    def test_reached_tempo_is_used_in_history(self):
        from unittest import mock
        from morsetrainer.core import stats
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with mock.patch.object(stats, "STATS_DIR", directory), \
                    mock.patch.object(stats, "ALL_TIME_FILE", directory / "all_time.json"), \
                    mock.patch.object(stats, "RESULTS_FILE", directory / "results.jsonl"):
                session = stats.SessionStats("group", "KM", 20, 600)
                session.record_char("K", "K", True, 0.5, 20.0)
                session.finalize({"wpm_reached": 27, "wpm_end": 25})
                self.assertEqual(stats.load_history()[0]["wpm"], 27)
