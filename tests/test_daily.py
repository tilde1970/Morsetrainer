"""Tests für die Regeln der Tagesübung (core/daily.py): Stufen, Ablauf,
Tagestempo, Aufstieg und Sterne."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import daily, koch, stats

TODAY = date(2026, 10, 5)


def main_result(correct, total, wpm=20, **extra):
    return {"first_try_correct": correct, "first_try_total": total, "correct": correct, "total": total,
            "minutes": 5.0, "wpm": wpm, **extra}


def main_block():
    return daily.Block(daily.MAIN, "group", 5)


class StageAndPlanTest(unittest.TestCase):
    def test_stage_boundaries(self):
        self.assertEqual([daily.stage(n) for n in (1, 9, 10, 29, 30, 44, 45)],
                         [daily.EARLY, daily.EARLY, daily.WORDS, daily.WORDS, daily.MIXED, daily.MIXED,
                          daily.POST])
        self.assertEqual(daily.lesson_charset(daily.POST_KOCH), koch.KOCH_ORDER)

    def test_blocks_add_up_to_ten_minutes(self):
        for lesson in (3, 15, 35, 44, daily.POST_KOCH):
            for due in (0, 3, 8, 20):
                blocks = daily.plan(lesson, due, TODAY)
                self.assertEqual([b.kind for b in blocks], [daily.WARMUP, daily.MAIN, daily.OUTRO])
                self.assertAlmostEqual(sum(b.minutes for b in blocks), daily.TOTAL_MINUTES)
                self.assertGreaterEqual(blocks[1].minutes, daily.MAIN_MIN_MINUTES)

    def test_many_due_lengthen_warmup_up_to_limit(self):
        self.assertEqual(daily.warmup_minutes(15, 7), daily.WARMUP_MINUTES)
        self.assertGreater(daily.warmup_minutes(15, 8), daily.WARMUP_MINUTES)
        self.assertEqual(daily.warmup_minutes(15, 30), daily.WARMUP_MAX_MINUTES)
        self.assertEqual(daily.warmup_minutes(daily.POST_KOCH, 30), daily.WARMUP_POST_MINUTES)

    def test_nothing_due_uses_confusions(self):
        self.assertEqual(daily.plan(15, 0, TODAY)[0].params["focus"], "confusions")
        self.assertEqual(daily.plan(15, 2, TODAY)[0].params["focus"], "due")

    def test_outro_by_stage(self):
        self.assertEqual(daily.plan(5, 0, TODAY)[2].mode, "continuous")
        self.assertEqual(daily.plan(15, 0, TODAY)[2].mode, "word")
        mixed = {daily.plan(35, 0, TODAY + timedelta(days=i))[2].mode for i in range(2)}
        self.assertEqual(mixed, {"word", "callsign"})  # im Tageswechsel
        post = daily.plan(daily.POST_KOCH, 0, TODAY)
        self.assertEqual((post[1].mode, post[2].mode), ("continuous", "callsign"))


class TempoTest(unittest.TestCase):
    def test_initial_tempo_keeps_chars_fast(self):
        self.assertEqual(daily.initial_tempo(20, 10), {"wpm": 20, "effective": 10})
        self.assertEqual(daily.initial_tempo(15, None), {"wpm": 18, "effective": 15})
        self.assertEqual(daily.initial_tempo(25, None), {"wpm": 25, "effective": 25})

    def test_next_tempo(self):
        start = {"wpm": 20, "effective": 12}
        self.assertEqual(daily.next_tempo(start, main_result(95, 100)), {"wpm": 20, "effective": 13})
        self.assertEqual(daily.next_tempo(start, main_result(70, 100)), {"wpm": 20, "effective": 11})
        self.assertEqual(daily.next_tempo(start, main_result(80, 100)), start)
        self.assertEqual(daily.next_tempo(start, main_result(99, 99)), start)  # zu wenige Zeichen

    def test_slower_without_farnsworth_never_below_slow_char_wpm(self):
        tempo = {"wpm": koch.SLOW_CHAR_WPM, "effective": koch.SLOW_CHAR_WPM}
        slower = daily.next_tempo(tempo, main_result(50, 100))
        self.assertEqual(slower, {"wpm": koch.SLOW_CHAR_WPM, "effective": koch.SLOW_CHAR_WPM - 1})

    def test_broken_saved_tempo_falls_back(self):
        self.assertEqual(daily.current_tempo({"tempo": {"wpm": 10, "effective": 30}}, 20, 10),
                         {"wpm": 20, "effective": 10})


class LessonTest(unittest.TestCase):
    def test_pending_lesson_applies_next_day(self):
        state = {"days": {}, "lesson": 12, "tempo": {"wpm": 20, "effective": 12}}
        stars = daily.finish_block(state, TODAY, main_block(), main_result(90, 100))
        self.assertEqual(stars, [daily.SAUBER, daily.WEITER])  # Aufstieg ist Fortschritt
        self.assertEqual((state["lesson"], state["pending_lesson"]), (12, 13))
        self.assertFalse(daily.apply_pending_lesson(state, TODAY))  # erst morgen
        tomorrow = TODAY + timedelta(days=1)
        self.assertTrue(daily.apply_pending_lesson(state, tomorrow))
        self.assertEqual((state["lesson"], state["lesson_since"], state["pending_lesson"]),
                         (13, tomorrow.isoformat(), None))
        self.assertTrue(daily.is_new_lesson(state, tomorrow + timedelta(days=2)))
        self.assertFalse(daily.is_new_lesson(state, tomorrow + timedelta(days=3)))

    def test_no_advance_with_slow_chars_or_after_koch(self):
        state = {"days": {}, "lesson": 12}
        daily.finish_block(state, TODAY, main_block(), main_result(100, 100, wpm=koch.SLOW_CHAR_WPM - 1))
        self.assertNotIn("pending_lesson", state)
        state = {"days": {}, "lesson": daily.POST_KOCH}
        daily.finish_block(state, TODAY, main_block(), main_result(100, 100))
        self.assertNotIn("pending_lesson", state)

    def test_current_lesson(self):
        self.assertEqual(daily.current_lesson({}, 7), 7)
        self.assertEqual(daily.current_lesson({"lesson": 20}, 7), 20)
        self.assertEqual(daily.current_lesson({"lesson": "x"}, 99), daily.POST_KOCH)


class StarsTest(unittest.TestCase):
    def setUp(self):
        # Nach Koch: kein Aufstieg, der ★ Weiter nebenbei brächte.
        self.state = {"days": {}, "lesson": daily.POST_KOCH, "tempo": {"wpm": 20, "effective": 12}}

    def test_sauber_needs_share_and_enough_chars(self):
        self.assertEqual(daily.finish_block(self.state, TODAY, main_block(), main_result(40, 49)), [])
        self.assertEqual(daily.finish_block(self.state, TODAY, main_block(), main_result(44, 50)), [])
        self.assertEqual(daily.finish_block(self.state, TODAY, main_block(), main_result(45, 50)),
                         [daily.SAUBER])
        # am selben Tag nicht noch einmal
        self.assertEqual(daily.finish_block(self.state, TODAY, main_block(), main_result(50, 50)), [])

    def test_new_lesson_needs_less(self):
        self.state.update(lesson_since=TODAY.isoformat())
        self.assertEqual(daily.finish_block(self.state, TODAY, main_block(), main_result(41, 50)),
                         [daily.SAUBER])

    def test_weiter_only_for_real_progress(self):
        warmup = daily.Block(daily.WARMUP, "single", 3)
        events = [{"char": "K", "box": 1, "first": True}, {"char": "M", "box": 2, "first": False}]
        self.assertEqual(daily.finish_block(self.state, TODAY, warmup, {"review_events": events}), [])
        events = [{"char": "G", "box": 2, "first": True}]
        self.assertEqual(daily.finish_block(self.state, TODAY, warmup, {"review_events": events}),
                         [daily.WEITER])
        self.assertIn("box:G", daily.day_entry(self.state, TODAY)["progress"])

    def test_tempo_up_is_progress(self):
        stars = daily.finish_block(self.state, TODAY, main_block(), main_result(85, 100, wpm=20))
        self.assertEqual(stars, [])  # 85 %: Tempo bleibt, kein Stern
        stars = daily.finish_block(self.state, TODAY + timedelta(days=1), main_block(),
                                   main_result(89, 100, wpm=koch.SLOW_CHAR_WPM - 1))
        self.assertEqual(stars, [])
        stars = daily.finish_block(self.state, TODAY + timedelta(days=2), main_block(),
                                   main_result(92, 100, wpm=koch.SLOW_CHAR_WPM - 1))
        self.assertEqual(stars, [daily.SAUBER, daily.WEITER])
        self.assertEqual(self.state["tempo"]["effective"], 13)

    def test_continuous_counts_extra_keys(self):
        self.state["lesson"] = daily.POST_KOCH
        block = daily.Block(daily.MAIN, "continuous", 4)
        result = {"correct": 95, "total": 100, "extra_keys": 10, "minutes": 4.0, "wpm": 25}
        self.assertEqual(daily.finish_block(self.state, TODAY, block, result), [])

    def test_dabei_needs_completed_ten_minutes(self):
        entry = daily.day_entry(self.state, TODAY)
        entry["minutes"] = 9.5
        self.assertEqual(daily.finish_day(self.state, TODAY, completed=True), [])
        entry["minutes"] = 9.8
        self.assertEqual(daily.finish_day(self.state, TODAY, completed=False), [])
        self.assertEqual(daily.finish_day(self.state, TODAY, completed=True), [daily.DABEI])
        self.assertEqual(daily.finish_day(self.state, TODAY, completed=True), [])
        daily.finish_block(self.state, TODAY, main_block(), main_result(50, 50))
        self.assertEqual(daily.stars_on(self.state, TODAY), [daily.DABEI, daily.SAUBER])


class StorageTest(unittest.TestCase):
    def test_round_trip_and_broken_file(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(stats, "STATS_DIR", Path(tmp)):
            self.assertEqual(daily.load(), {"days": {}})
            state = daily.load()
            daily.finish_block(state, TODAY, main_block(), main_result(50, 50, wpm=koch.SLOW_CHAR_WPM - 1))
            daily.save(state)
            self.assertEqual(daily.stars_on(daily.load(), TODAY), [daily.SAUBER])
            (Path(tmp) / daily.DAILY_FILE_NAME).write_text("{kaputt", encoding="utf-8")
            self.assertEqual(daily.load(), {"days": {}})
            self.assertTrue(list(Path(tmp).glob("daily.json.defekt-*")))
