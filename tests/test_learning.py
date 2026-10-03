"""Tests für die Lernhilfen: Koch-Lektionen, Wörter, Auswertung von
Gruppen per Alignment und die mitwachsende Gruppenlänge."""
import random
import tempfile
import time
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
        self.assertEqual(words.words_for_charset("KM"), ["K"])  # K = kommen, zählt nicht als Wort
        self.assertFalse(words.enough_words(["K", "R"] * 10))
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


class ProsignLessonTest(unittest.TestCase):
    def test_last_lessons_are_prosigns_with_key_hint(self):
        from morsetrainer.core.morse import PROSIGN_KEYS, display_text, key_hint
        self.assertEqual(koch.MAX_LESSON, 44)
        self.assertEqual("".join(koch.newest_char(n) for n in range(41, 45)), "+(*#")
        self.assertTrue(all(ch in PROSIGN_KEYS for ch in "+(*#"))
        self.assertEqual(key_hint(koch.newest_char(43)), "<SK> · Taste *")
        self.assertEqual(key_hint("K"), "K")
        self.assertEqual(display_text("K*#"), "K<SK><BK>")


class KochPassedTest(unittest.TestCase):
    def test_needs_enough_chars_and_accuracy(self):
        self.assertTrue(koch.passed(45, 50))
        self.assertFalse(koch.passed(44, 50))   # 88 %
        self.assertFalse(koch.passed(40, 40))   # zu wenige Zeichen
        self.assertFalse(koch.can_advance(koch.lesson_charset(koch.MAX_LESSON), 50, 50))


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
        self.assertEqual(length.update(False, 1), -1)
        self.assertEqual(length.length, 2)

    def test_shrinks_even_if_repeats_succeed(self):
        length = AdaptiveLength(2, 4, start=3)
        for _ in range(SHORTER_AFTER - 1):
            self.assertEqual(length.update(False, 1), 0)  # erster Versuch falsch …
            self.assertEqual(length.update(True, 2), 0)   # … Wiederholung richtig
        self.assertEqual(length.update(False, 1), -1)
        self.assertEqual(length.length, 2)

    def test_repeated_misses_of_one_group_do_not_shrink(self):
        length = AdaptiveLength(2, 4, start=3)
        self.assertEqual(length.update(False, 1), 0)   # erster Versuch falsch
        for attempts in range(2, 2 + 3 * SHORTER_AFTER):
            self.assertEqual(length.update(False, attempts), 0)  # dieselbe Gruppe nochmal falsch
        self.assertEqual(length.length, 3)

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

    def test_background_gain_scales_only_interference(self):
        import numpy as np
        from morsetrainer.core import band
        from morsetrainer.core.morse import build_text
        samples = build_text("KM", 20, 600)
        conditions = band.preset_conditions("heavy", 600)
        conditions.enabled["qsb"] = False  # QSB ändert das Signal selbst
        conditions.background_gain = 0.0
        mixed, lead = band.apply_preset(conditions, samples)
        start = round(lead * band.SAMPLE_RATE)
        np.testing.assert_allclose(mixed[start:start + len(samples)], band.soft_limit(samples), atol=1e-6)

        def background_rms(gain):
            conditions.background_gain = gain
            mixed, _ = band.apply_preset(conditions, np.zeros(0, dtype=np.float32))
            return float(np.sqrt(np.mean(mixed ** 2)))
        self.assertLess(background_rms(0.3), background_rms(1.0))


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

    def test_limit_settles_near_nine_in_ten(self):
        """Das Limit sinkt erst, wenn deutlich mehr als acht von zehn Zeichen
        rechtzeitig kommen; bei vier von fünf wird es wieder länger."""
        from morsetrainer.modes.single_mode import next_limit

        def run(right, missed):
            limit = 1.5
            for _ in range(10):
                for _ in range(right):
                    limit = next_limit(limit, True)
                for _ in range(missed):
                    limit = next_limit(limit, False)
            return limit
        self.assertLess(run(19, 1), 1.5)
        self.assertGreater(run(4, 1), 1.5)


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
                session.finalize({"wpm_reached": 27, "wpm_end": 25})  # ältere Dateien
                self.assertEqual(stats.load_history()[0]["wpm"], 27)

    def test_history_uses_effective_tempo(self):
        from unittest import mock
        from morsetrainer.core import stats
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with mock.patch.object(stats, "STATS_DIR", directory), \
                    mock.patch.object(stats, "ALL_TIME_FILE", directory / "all_time.json"), \
                    mock.patch.object(stats, "RESULTS_FILE", directory / "results.jsonl"):
                for extra in (None, {"wpm_effective_reached": 13}):
                    session = stats.SessionStats("group", "KM", 20, 600, farnsworth_wpm=10)
                    session.record_char("K", "K", True, 0.5, 20.0)
                    session.finalize(extra)
                    time.sleep(1.1)  # eigener Dateiname je Sekunde
                self.assertEqual([e["wpm"] for e in stats.load_history()], [10, 13])


class TempoRuleTest(unittest.TestCase):
    def test_faster_shortens_pauses_then_raises_char_speed(self):
        from morsetrainer.core import tempo
        self.assertEqual(tempo.step(20, 10, 1), (20, 11))
        self.assertEqual(tempo.step(20, 19, 1), (20, None))   # Farnsworth fällt weg
        self.assertEqual(tempo.step(20, None, 1), (21, None))

    def test_slower_never_stretches_characters_below_minimum(self):
        from morsetrainer.core import tempo
        self.assertEqual(tempo.step(20, 10, -1), (20, 9))      # nur die Pausen
        self.assertEqual(tempo.step(19, None, -1), (18, None))
        self.assertEqual(tempo.step(18, None, -1), (18, 17))   # ab hier Farnsworth
        self.assertEqual(tempo.step(12, None, -1), (12, 11))   # Start unter 18: Zeichen bleiben
        self.assertEqual(tempo.step(20, 5, -1), (20, 5))       # Untergrenze
        self.assertEqual(tempo.label(20, 12), "20/12 WPM")
        self.assertEqual(tempo.label(20, None), "20 WPM")


class RetryQueueTest(unittest.TestCase):
    def test_missed_char_returns_after_some_others(self):
        from morsetrainer.modes.single_mode import RETRY_AFTER, RetryQueue
        for seed in range(20):
            queue = RetryQueue(random.Random(seed))
            queue.add("B")
            others = 0
            while queue.next_due() is None:
                others += 1
            self.assertTrue(RETRY_AFTER[0] <= others <= RETRY_AFTER[1])
            self.assertIsNone(queue.next_due())

    def test_picker_skips_excluded_chars(self):
        from morsetrainer.core.weighting import CharPicker
        picker = CharPicker("KM", weighted=False)
        self.assertTrue(all(picker.pick(exclude="M") == "K" for _ in range(20)))
        self.assertIn(picker.pick(exclude="KM"), "KM")  # nichts übrig: Ausschluss entfällt


class CallsignFilterTest(unittest.TestCase):
    def test_filter_by_learned_chars_and_prefix(self):
        from morsetrainer.modes.callsign_mode import filter_calls
        calls = ["DL4YM", "DK1AB", "W1AW", "G3XYZ"]
        self.assertEqual(filter_calls(calls, [], set("DLYMK41AB")), ["DL4YM", "DK1AB"])
        self.assertEqual(filter_calls(calls, ["DK"], None), ["DK1AB"])

    def test_affixes_are_rare_and_use_only_allowed_chars(self):
        from morsetrainer.modes import callsign_mode
        random.seed(3)
        results = [callsign_mode.add_affix("DL4YM", set("DL4YMP/")) for _ in range(4000)]
        with_affix = [r for r in results if r != "DL4YM"]
        self.assertLess(len(with_affix) / len(results), 0.12)
        self.assertTrue(all(set(r) <= set("DL4YMP/") for r in results))  # nur /P möglich
        self.assertTrue(all(r == "DL4YM" for r in
                            (callsign_mode.add_affix("DL4YM", set("DL4YM")) for _ in range(200))))  # ohne "/"


class WordLessonTest(unittest.TestCase):
    def test_newest_char_is_favored(self):
        random.seed(5)
        pool = ["TNX", "ES", "UR", "RST", "NAME", "WX", "HW", "PSE", "AGN", "TEST"]
        picker = words.WordPicker(pool, favor="W")
        picks = [picker.pick() for _ in range(2000)]
        share = sum("W" in p for p in picks) / len(picks)
        self.assertGreater(share, 0.25)  # ohne Bevorzugung ~20 %

    def test_weak_char_raises_words_in_turn(self):
        from morsetrainer.core.weighting import CharPicker
        picker = CharPicker("ESTXQ", weighted=True)
        picker.weights = lambda: [0.1, 0.1, 0.1, 2.0, 0.1]  # X schwach
        random.seed(2)
        pool = ["TEST", "ES", "SET", "TEX", "EST", "SEE", "TEE", "TSE", "SETS", "TEES", "XES"]
        chooser = words.WordPicker(pool, picker)
        picks = [chooser.pick() for _ in range(1000)]
        self.assertGreater(sum("X" in p for p in picks) / len(picks), 0.3)  # gleichverteilt ~18 %
        # im Wechsel, kein Lieblingswort
        self.assertLess(max(picks.count(w) for w in pool) / len(picks), 0.22)

    def test_few_favored_words_are_capped(self):
        random.seed(6)
        pool = ["TNX", "ES", "UR", "RST", "NAME", "PSE", "UP", "AGN", "TEST", "HR", "OM", "GM", "GE", "FB"]
        picker = words.WordPicker(pool, favor="P")  # nur PSE und UP
        picks = [picker.pick() for _ in range(4000)]
        for word in ("PSE", "UP"):
            self.assertLess(picks.count(word) / len(picks), 0.17)

    def test_first_lesson_with_enough_words(self):
        lesson = words.first_lesson_with_words()
        self.assertGreaterEqual(len(words.words_for_charset(koch.lesson_charset(lesson))), words.MIN_WORDS)
        self.assertLess(len(words.words_for_charset(koch.lesson_charset(lesson - 1))), words.MIN_WORDS)

