"""Tests für die Lernhilfen: Koch-Lektionen, Wörter, Auswertung von
Gruppen per Alignment und die mitwachsende Gruppenlänge."""
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_user_words_file_in_ansi_or_with_bom_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "woerter.txt"
            path.write_bytes("# Grüße aus Köln\nUFB = super\n".encode("cp1252"))  # älterer Windows-Editor
            self.assertEqual(words.load_words(path)[1], {"UFB": "super"})
            path.write_bytes("\ufeffUFB = super\nTNX\n".encode("utf-8"))  # BOM gehört nicht zur ersten Zeile
            combined, user, skipped = words.load_words(path)
            self.assertEqual((user, skipped), ({"UFB": "super", "TNX": ""}, []))

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
        self.assertEqual(koch.MAX_LESSON, 45)
        self.assertEqual("".join(koch.newest_char(n) for n in range(42, 46)), "+(*#")
        self.assertTrue(all(ch in PROSIGN_KEYS for ch in "+(*#"))
        self.assertEqual(key_hint(koch.newest_char(44)), "<SK> · Taste *")
        self.assertEqual(key_hint("K"), "K")
        self.assertEqual(display_text("K*#"), "K<SK><BK>")


class KochPassedTest(unittest.TestCase):
    def test_needs_enough_chars_and_accuracy(self):
        self.assertTrue(koch.passed(45, 50))
        self.assertFalse(koch.passed(44, 50))   # 88 %
        self.assertFalse(koch.passed(40, 40))   # zu wenige Zeichen
        self.assertFalse(koch.can_advance(koch.lesson_charset(koch.MAX_LESSON), 50, 50))
        # Bis zur Abschlusslektion 41 von selbst, zu den Betriebszeichen nur von Hand.
        self.assertTrue(koch.can_advance(koch.lesson_charset(40), 50, 50))
        self.assertFalse(koch.can_advance(koch.lesson_charset(41), 50, 50))
        self.assertTrue(koch.can_advance(koch.lesson_charset(42), 50, 50))  # AR sitzt: weiter mit KN
        self.assertTrue(koch.can_advance(koch.lesson_charset(44), 50, 50))
        self.assertFalse(koch.can_advance(koch.lesson_charset(45), 50, 50))

    def test_final_lesson_has_all_chars_and_none_new(self):
        final = koch.lesson_charset(koch.FINAL_LESSON)
        self.assertEqual(koch.FINAL_LESSON, 41)
        self.assertEqual(set(final), set(koch.lesson_charset(40)))
        self.assertTrue(final.startswith("ABC"))
        self.assertEqual(koch.lesson_of(final), 41)
        self.assertEqual(koch.lesson_of(koch.lesson_charset(40)), 40)
        self.assertEqual(koch.newest_char(41), "")
        self.assertEqual(koch.lesson_charset(42), koch.LCWO_ORDER + "+")


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


class FarnsworthTest(unittest.TestCase):
    def test_gap_matches_paris_norm(self):
        from morsetrainer.core import morse
        gap = morse.char_gap_seconds(20, 10)
        # PARIS bei 20/10 WpM: 31 Einheiten Ton (0,06 s) plus 19 Einheiten Pause = 6,0 s
        self.assertAlmostEqual(31 * 0.06 + 19 / 3 * gap, 6.0, places=6)
        self.assertAlmostEqual(morse.char_gap_seconds(20, None), 0.18)
        self.assertAlmostEqual(morse.char_gap_seconds(20, 20), 0.18)
        self.assertAlmostEqual(morse.word_gap_extra_seconds(20, 10), gap * 4 / 3)


class PracticeTest(unittest.TestCase):
    def test_add_reads_and_writes_in_one_transaction(self):
        from datetime import date
        from unittest import mock
        from morsetrainer.core import db, practice, stats
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(stats, "STATS_DIR", Path(tmp)):
            with mock.patch.object(db, "transaction", wraps=db.transaction) as transaction:
                practice.add(60, date(2026, 9, 26))
            transaction.assert_called()

    def test_add_with_locked_database_neither_raises_nor_overwrites(self):
        import sqlite3
        from datetime import date
        from unittest import mock
        from morsetrainer.core import db, practice, stats
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(stats, "STATS_DIR", Path(tmp)):
            day = date(2026, 9, 26)
            practice.add(60, day)
            with mock.patch.object(db, "save_state", side_effect=sqlite3.OperationalError("locked")):
                practice.add(30, day)
            self.assertEqual(practice.seconds_on(practice.load(), day), 60.0)

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

    def test_upper_bound(self):
        from morsetrainer.modes.single_mode import next_limit
        self.assertEqual(next_limit(1.4, False, upper=1.5), 1.5)

    def test_limit_settles_near_nine_in_ten(self):
        """Das Limit sinkt erst, wenn deutlich mehr als acht von zehn Zeichen
        rechtzeitig kommen (verpasst statt richtig); bei vier von fünf wird es
        wieder länger."""
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
            with mock.patch.object(stats, "STATS_DIR", directory):
                session = stats.SessionStats("group", "KM", 20, 600)
                session.record_char("K", "K", True, 0.5, 20.0)
                session.finalize({"wpm_reached": 27, "wpm_end": 25})  # ältere Dateien
                self.assertEqual(stats.load_history()[0]["wpm"], 27)

    def test_history_uses_effective_tempo(self):
        from unittest import mock
        from morsetrainer.core import stats
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with mock.patch.object(stats, "STATS_DIR", directory):
                for extra in (None, {"wpm_effective_reached": 13}):
                    session = stats.SessionStats("group", "KM", 20, 600, farnsworth_wpm=10)
                    session.record_char("K", "K", True, 0.5, 20.0)
                    session.finalize(extra)
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



class ReviewThresholdsTest(unittest.TestCase):
    """Befunde der Gesamtprüfung Didaktik (Lernkartei, Tagestempo, Gewichtung)."""

    def _entry(self, n, fluent, due=True):
        from datetime import date, timedelta
        from morsetrainer.core import review
        entry = {"box": 2, "n": n, "fluent": fluent, "pn": n, "pfluent": fluent, "decided": False,
                 "day": date.today().isoformat()}
        if due:
            entry["due"] = (date.today() - timedelta(days=1)).isoformat()
        return entry, review

    def test_too_few_attempts_do_not_decide(self):
        from datetime import date
        entry, review = self._entry(7, 0)
        review._decide("K", entry, date.today())
        self.assertFalse(entry["decided"])

    def test_close_to_the_threshold_keeps_the_box(self):
        from datetime import date
        entry, review = self._entry(10, 8)  # 80 %: Zeitlimit pendelt bei etwa 88 %
        review._decide("K", entry, date.today())
        self.assertFalse(entry["decided"])
        self.assertEqual(entry["box"], 2)

    def test_clearly_weak_goes_back(self):
        from datetime import date
        entry, review = self._entry(10, 7)  # 70 %
        review._decide("K", entry, date.today())
        self.assertTrue(entry["decided"])
        self.assertEqual(entry["box"], 0)

    def test_sure_moves_up(self):
        from datetime import date
        entry, review = self._entry(10, 10)
        review._decide("K", entry, date.today())
        self.assertEqual(entry["box"], 3)


class ReviewShadowTest(unittest.TestCase):
    """Das Schattenmodell (FSRS-6) schreibt mit und ändert Fach und Termin nicht."""

    def test_formulas_match_py_fsrs(self):
        from morsetrainer.core import fsrs_shadow as fs
        stability, difficulty = fs.first(fs.GOOD)  # Werte aus py-fsrs 6.3.2 mit denselben Gewichten
        self.assertAlmostEqual(stability, 2.3065, places=4)
        self.assertAlmostEqual(difficulty, 2.1181, places=4)
        stability, difficulty = fs.review(stability, difficulty, 4, fs.GOOD)
        self.assertAlmostEqual(stability, 16.1773, places=3)
        self.assertAlmostEqual(difficulty, 2.1112, places=4)
        stability, difficulty = fs.first(fs.AGAIN)
        stability, difficulty = fs.review(stability, difficulty, 3, fs.GOOD)
        self.assertAlmostEqual(stability, 2.761, places=3)
        stability, difficulty = fs.review(stability, difficulty, 10, fs.HARD)
        self.assertGreater(stability, 0)
        self.assertAlmostEqual(fs.retrievability(0, 5.0), 1.0)
        self.assertAlmostEqual(fs.retrievability(5.0, 5.0), 0.9, places=6)  # nach S Tagen 90 %

    def _decide(self, entry, n, fluent, today):
        from morsetrainer.core import review
        entry.update(n=n, fluent=fluent, pn=n, pfluent=fluent, decided=False, day=today.isoformat())
        review._decide("K", entry, today)

    def test_new_and_old_entries_get_shadow_fields_without_changing_the_boxes(self):
        from datetime import date, timedelta
        today = date.today()
        new = {}
        self._decide(new, 10, 10, today)
        self.assertEqual(new["box"], 0)
        self.assertEqual((round(new["s"], 4), new["last"]), (2.3065, today.isoformat()))
        old = {"box": 2, "due": (today - timedelta(days=1)).isoformat()}
        self._decide(old, 10, 10, today)
        self.assertEqual(old["box"], 3)  # Fach wie ohne Schattenmodell
        self.assertGreater(old["s"], 0)
        self.assertEqual(old["last"], today.isoformat())
        weak = {"box": 3, "due": today.isoformat(), "s": 8.0, "d": 5.0, "last": (today - timedelta(days=8)).isoformat()}
        self._decide(weak, 10, 6, today)
        self.assertEqual(weak["box"], 0)
        self.assertLess(weak["s"], 8.0)  # Again verkürzt die Stabilität

    def test_decisions_land_in_the_log_and_reset_clears_it(self):
        from datetime import date, timedelta
        from morsetrainer.core import review
        review.reset()
        today = date.today()
        stat = {"good": 10, "wrong": 0, "latencies": [0.5] * 10}
        review.update({"K": stat}, promote=True, today=today)
        later = today + timedelta(days=3)
        review.update({"K": dict(stat, good=6, wrong=4, latencies=[0.5] * 6)}, promote=True, today=later)
        log = review.load_log()
        self.assertEqual([e["c"] for e in log], ["K", "K"])
        self.assertEqual((log[0]["r"], log[0]["t"], log[0]["p"], log[0]["from"], log[0]["to"]), (3, None, None, 0, 0))
        self.assertEqual((log[1]["r"], log[1]["t"], log[1]["from"], log[1]["to"]), (1, 3, 0, 0))
        self.assertTrue(0 < log[1]["p"] < 1)
        self.assertEqual(log[1]["day"], later.isoformat())
        review.reset()
        self.assertEqual(review.load_log(), [])

    def test_log_is_capped_and_survives_garbage(self):
        from morsetrainer.core import db, review
        review.reset()
        db.save_state(review.LOG_KEY, "kaputt")
        self.assertEqual(review.load_log(), [])
        db.save_state(review.LOG_KEY, [{"c": "A"}, "x", {"c": "B"}])
        self.assertEqual([e["c"] for e in review.load_log()], ["A", "B"])
        with mock.patch.object(review, "LOG_MAX", 3):
            review._save_log([{"c": "C"}, {"c": "D"}])
        self.assertEqual([e["c"] for e in review.load_log()], ["B", "C", "D"])
        review.reset()

    def test_no_decision_leaves_the_shadow_alone(self):
        from datetime import date, timedelta
        today = date.today()
        entry = {"box": 2, "due": (today - timedelta(days=1)).isoformat()}
        self._decide(entry, 7, 7, today)  # zu wenige Versuche
        self.assertNotIn("s", entry)
        self._decide(entry, 10, 8, today)  # Neutralzone
        self.assertNotIn("s", entry)

    def test_broken_shadow_fields_are_dropped_on_load(self):
        from morsetrainer.core import review
        for bad in ({"s": "x", "d": 5.0, "last": "2026-01-01"}, {"s": float("nan"), "d": 5.0, "last": "2026-01-01"},
                    {"s": 3.0, "d": -1.0, "last": "2026-01-01"}, {"s": 3.0, "d": 5.0, "last": "morgen"},
                    {"s": 3.0}):
            entry = review._clean({"box": 1, **bad})
            self.assertFalse(any(key in entry for key in review.SHADOW_FIELDS), bad)
        ok = review._clean({"box": 1, "s": 3.0, "d": 5.0, "last": "2026-01-01"})
        self.assertEqual(ok["s"], 3.0)

    def test_corrupt_box_does_not_break_the_decision(self):
        from datetime import date
        today = date.today()
        entry = {"box": 99, "due": today.isoformat()}
        self._decide(entry, 10, 10, today)  # IndexError im Schattenmodell darf nichts stören
        self.assertTrue(entry["decided"])


class DailyPausesTest(unittest.TestCase):
    def test_in_the_koch_phase_only_the_pauses_get_shorter(self):
        from morsetrainer.core import daily
        current = {"wpm": 20, "effective": 10}
        good = {"first_try_correct": 98, "first_try_total": 100}
        self.assertEqual(daily.next_tempo(current, good, allow_up="pauses"), {"wpm": 20, "effective": 11})
        ok = {"first_try_correct": 92, "first_try_total": 100}  # 92 % reicht für die Pausen nicht
        self.assertEqual(daily.next_tempo(current, ok, allow_up="pauses"), current)
        at_limit = {"wpm": 20, "effective": 20}  # die Zeichen werden vor Koch nicht schneller
        self.assertEqual(daily.next_tempo(at_limit, good, allow_up="pauses"), at_limit)
        self.assertEqual(daily.next_tempo(current, good, allow_up=False), current)


class WeightingRecentTest(unittest.TestCase):
    def test_recent_errors_count_more_than_old_ones(self):
        from unittest import mock
        from morsetrainer.core import stats
        from morsetrainer.core.weighting import CharPicker
        old_bad = {"K": {"good": 100, "wrong": 100}}  # früher oft falsch, jetzt sicher
        with mock.patch.object(stats, "load_all_time", return_value=old_bad), \
                mock.patch.object(stats, "recent_char_data", return_value={"K": {"good": 20, "wrong": 0}}):
            fixed = CharPicker("K", weighted=True)._error_rate("K")
        with mock.patch.object(stats, "load_all_time", return_value=old_bad), \
                mock.patch.object(stats, "recent_char_data", return_value={"K": {"good": 0, "wrong": 20}}):
            weak = CharPicker("K", weighted=True)._error_rate("K")
        self.assertLess(fixed, 0.5)
        self.assertGreater(weak, 0.5)
        self.assertGreater(weak, fixed + 0.15)


class RelaxedDailyTest(unittest.TestCase):
    def test_relaxed_block_skips_the_review(self):
        from morsetrainer.core import review, stats
        with tempfile.TemporaryDirectory() as tmp, __import__("unittest.mock", fromlist=["patch"]).patch.object(
                stats, "STATS_DIR", Path(tmp)):
            for relaxed in (False, True):
                session = stats.SessionStats("single", "KMURESNAP", 20, 600, review_promote=True,
                                             config_extra={"relaxed": True} if relaxed else None)
                for _ in range(10):
                    session.record_char("K" if not relaxed else "M", "K" if not relaxed else "M", True, 0.5, 20.0,
                                        latency=0.5)
                session.finalize()
            data = review.load()
            self.assertIn("K", data)
            self.assertNotIn("M", data)


class ShortNumbersTest(unittest.TestCase):
    def test_short_numbers_use_cut_numbers(self):
        from morsetrainer.modes import content
        random.seed(3)
        values = {content._short_number() for _ in range(200)}
        self.assertIn("5NN", values)
        self.assertTrue(any(v.startswith("T") for v in values))


class FsrsReportTest(unittest.TestCase):
    def _entry(self, p, share, box=0):
        return {"c": "K", "day": "2026-10-24", "r": 3, "share": share, "n": 10, "t": 3, "p": p, "from": box, "to": box}

    def test_empty_and_garbage_logs(self):
        from morsetrainer.core import fsrs_shadow
        report = fsrs_shadow.report([])
        self.assertEqual((report["entries"], report["predicted"], report["verdict"], report["brier"]), (0, 0, "few", None))
        report = fsrs_shadow.report(["x", {"p": "a", "share": 1}, {"p": None, "share": 0.9, "day": "2026-10-01"}])
        self.assertEqual((report["entries"], report["predicted"], report["first"]), (2, 0, "2026-10-01"))

    def test_too_little_data_gives_no_verdict(self):
        from morsetrainer.core import fsrs_shadow
        report = fsrs_shadow.report([self._entry(0.9, 0.9)] * (fsrs_shadow.MIN_REPORT - 1))
        self.assertEqual(report["verdict"], "few")
        self.assertAlmostEqual(report["brier"]["fsrs"], 0.0)

    def test_verdict_follows_the_brier_values(self):
        from morsetrainer.core import fsrs_shadow
        n = fsrs_shadow.MIN_REPORT
        # Wirklichkeit hängt von p ab, nicht vom Fach (alle Fach 0): FSRS gewinnt.
        good = [self._entry(0.95, 0.95)] * n + [self._entry(0.55, 0.55)] * n
        self.assertEqual(fsrs_shadow.report(good)["verdict"], "fsrs")
        # Wirklichkeit hängt vom Fach ab, p ist Rauschen: das Fach gewinnt.
        bad = [self._entry(0.55, 0.95, box=3)] * n + [self._entry(0.95, 0.55, box=0)] * n
        self.assertEqual(fsrs_shadow.report(bad)["verdict"], "box")
        same = [self._entry(0.9, 0.9)] * (2 * n)
        self.assertEqual(fsrs_shadow.report(same)["verdict"], "equal")

    def test_bins_and_boxes(self):
        from morsetrainer.core import fsrs_shadow
        report = fsrs_shadow.report([self._entry(0.95, 1.0, 2), self._entry(0.6, 0.5, 0), self._entry(1.0, 1.0, 2)])
        self.assertEqual([b["n"] for b in report["bins"]], [1, 2])  # 0,5–0,7 und 0,9–1,0 (1,0 gehört dazu)
        self.assertEqual([(b["box"], b["n"]) for b in report["boxes"]], [(0, 1), (2, 2)])
