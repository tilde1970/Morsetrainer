"""Tests für die Regeln der Tagesübung (core/daily.py): Stufen, Ablauf,
Tagestempo, Aufstieg, Sterne, Rückblick und Vorwochenvergleich."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import daily, db, koch, stats

TODAY = date(2026, 10, 5)


def main_result(correct, total, wpm=20, **extra):
    return {"first_try_correct": correct, "first_try_total": total, "correct": correct, "total": total,
            "minutes": 5.0, "wpm": wpm, **extra}


def main_block():
    return daily.Block(daily.MAIN, "group", 5)


class StageAndPlanTest(unittest.TestCase):
    def test_stage_boundaries(self):
        self.assertEqual([daily.stage(n) for n in (1, 9, 10, 29, 30, 41, 42)],
                         [daily.EARLY, daily.EARLY, daily.WORDS, daily.WORDS, daily.MIXED, daily.MIXED,
                          daily.POST])
        # Nach Koch alle Zeichen; Betriebszeichen nur, wenn schon gelernt.
        self.assertEqual(daily.lesson_charset(daily.POST_KOCH), koch.FINAL_CHARSET)
        self.assertEqual(daily.lesson_charset(daily.POST_KOCH, "KMU"), koch.FINAL_CHARSET)
        self.assertEqual(daily.lesson_charset(daily.POST_KOCH, "+K"), koch.lesson_charset(42))
        self.assertEqual(daily.lesson_charset(daily.POST_KOCH, "*+("), koch.lesson_charset(44))
        self.assertEqual(koch.lesson_of(daily.lesson_charset(daily.POST_KOCH, "#")), koch.MAX_LESSON)
        self.assertEqual(daily.lesson_charset(41, "+"), koch.FINAL_CHARSET)  # Abschlusslektion selbst ohne

    def test_blocks_add_up_to_ten_minutes(self):
        for lesson in (3, 15, 35, 41, daily.POST_KOCH):
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
    def test_no_tempo_up_when_not_allowed(self):
        start = {"wpm": 20, "effective": 12}
        self.assertEqual(daily.next_tempo(start, main_result(95, 100), allow_up=False), start)
        self.assertEqual(daily.next_tempo(start, main_result(70, 100), allow_up=False),
                         {"wpm": 20, "effective": 11})

    def test_warmup_limit(self):
        self.assertEqual(daily.warmup_limit({}), 1.5)
        self.assertEqual(daily.warmup_limit({"icr_limit": 0.7}), 0.7)
        self.assertEqual(daily.warmup_limit({"icr_limit": 2.6}), 1.5)
        self.assertEqual(daily.warmup_limit({"icr_limit": "x"}), 1.5)

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
        # Höhere gespeicherte Lektion aus alten Daten (45) gilt als „nach Koch“.
        self.assertEqual(daily.current_lesson({"lesson": 45}, 7), daily.POST_KOCH)
        state = {"lesson": 41, "pending_lesson": 45, "pending_since": "2026-01-01"}
        daily.apply_pending_lesson(state, TODAY)
        self.assertEqual(state["lesson"], daily.POST_KOCH)


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

    def day(self, offset, correct, total=100):
        """Tagesübung am Tag TODAY + offset: Tempo vom Vortag übernehmen, Hauptteil."""
        today = TODAY + timedelta(days=offset)
        daily.apply_pending_tempo(self.state, today)
        return daily.finish_block(self.state, today, main_block(), main_result(correct, total))

    def test_tempo_up_is_progress_only_at_a_new_best(self):
        self.assertEqual(self.day(0, 85), [])  # 85 %: Tempo bleibt, kein Stern
        self.assertEqual(self.day(1, 92), [daily.SAUBER, daily.WEITER])
        self.assertEqual(self.state["tempo"]["effective"], 12)  # erst ab morgen
        self.assertEqual(self.state["pending_tempo"]["effective"], 13)
        self.assertEqual(self.day(2, 70), [])
        self.assertEqual(self.state["tempo"]["effective"], 13)
        self.assertEqual(self.day(3, 92), [daily.SAUBER])  # zurück auf 13: kein neuer Höchstwert
        self.assertEqual(self.day(4, 92), [daily.SAUBER, daily.WEITER])  # morgen 14: neu
        self.assertEqual(self.state["tempo_best"], 14)

    def test_tempo_changes_once_a_day(self):
        self.day(0, 95)
        self.assertEqual(self.state["pending_tempo"]["effective"], 13)
        daily.finish_block(self.state, TODAY, main_block(), main_result(50, 100))  # zweite Tagesübung
        self.assertEqual(self.state["pending_tempo"]["effective"], 13)
        self.assertEqual(self.state["tempo"]["effective"], 12)

    def test_no_faster_tempo_while_lessons_come(self):
        self.state["lesson"] = 12
        self.day(0, 95)
        self.assertEqual(self.state["pending_tempo"]["effective"], 12)  # neues Zeichen reicht
        self.assertEqual(self.state["pending_lesson"], 13)
        self.day(1, 60)
        self.assertEqual(self.state["pending_tempo"]["effective"], 11)  # langsamer schon

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
            db._write("UPDATE state SET data = '{kaputt' WHERE key = 'daily'")
            self.assertEqual(daily.load(), {"days": {}})
            self.assertEqual(len(db._read("SELECT key FROM state WHERE key LIKE 'daily.defekt-%'")), 1)


def write_session(directory: Path, day: date, mode: str, chars=(), config=None, summary=None, index=0):
    """Durchgang wie von SessionStats: config, Zeichen, summary.
    `chars`: (Zeichen, Latenz) – richtig erkannt; Latenz None = verpasst."""
    lines = [{"type": "config", "mode": mode, "wpm": 20, "farnsworth_wpm": 12,
              "start_time": f"{day.isoformat()}T12:00:{index:02d}", **(config or {})}]
    lines += [{"type": "char", "char": ch, "correct": True, "latency_s": lat} if lat is not None
              else {"type": "char", "char": ch, "correct": False} for ch, lat in chars]
    lines.append({"type": "summary", "total": len(chars), **(summary or {})})
    tests.write_session(lines)


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        patch = mock.patch.object(stats, "STATS_DIR", self.dir)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def latency_week(self, day, char, latency, count=daily.LATENCY_WEEK_MIN, **kwargs):
        write_session(self.dir, day, "single", [(char, latency)] * count, **kwargs)

    def test_latency_better_needs_both_thresholds(self):
        before = TODAY - timedelta(days=8)
        self.latency_week(before, "R", 0.65)
        self.latency_week(TODAY, "R", 0.41)
        self.latency_week(before, "K", 0.50, index=1)
        self.latency_week(TODAY, "K", 0.42, index=1)   # 16 %, aber unter 0,1 s
        result = daily.week_comparison(TODAY)
        self.assertEqual(result["status"], daily.BETTER)
        self.assertEqual(result["better"], [{"kind": "latency", "char": "R", "before": 0.65, "now": 0.41}])

    def test_held_and_too_few(self):
        self.assertEqual(daily.week_comparison(TODAY), {"status": daily.FEW, "better": []})
        self.latency_week(TODAY - timedelta(days=8), "R", 0.5)
        self.latency_week(TODAY, "R", 0.6)   # langsamer: nie „schlechter“, nur gehalten
        self.assertEqual(daily.week_comparison(TODAY), {"status": daily.HELD, "better": []})

    def test_self_assessed_and_assumed_do_not_count(self):
        self.latency_week(TODAY - timedelta(days=8), "R", 0.9)
        self.latency_week(TODAY, "R", 0.3, config={"self_assessed": True})
        self.assertEqual(daily.week_comparison(TODAY)["status"], daily.FEW)

    def test_latency_only_from_single_at_similar_char_speed(self):
        before = TODAY - timedelta(days=8)
        self.latency_week(before, "R", 0.8)
        write_session(self.dir, TODAY, "group", [("R", 0.3)] * 30)  # Mitschreiben: anderes Maß
        self.assertEqual(daily.week_comparison(TODAY)["status"], daily.FEW)
        self.latency_week(TODAY, "R", 0.4, config={"wpm": 25}, index=1)  # Zeichen deutlich schneller
        self.assertEqual(daily.week_comparison(TODAY)["status"], daily.FEW)
        self.latency_week(TODAY, "R", 0.4, config={"wpm": 22}, index=2)
        self.assertEqual(daily.week_comparison(TODAY)["better"],
                         [{"kind": "latency", "char": "R", "before": 0.8, "now": 0.4}])

    def test_missed_chars_count_as_slow(self):
        """Ein kürzeres Limit macht langsame Antworten zu verpassten; das
        darf nicht als schneller zählen."""
        before = TODAY - timedelta(days=8)
        write_session(self.dir, before, "single", [("R", 0.4)] * 10 + [("R", 0.9)] * 10)
        write_session(self.dir, TODAY, "single", [("R", 0.4)] * 10 + [("R", None)] * 10)
        self.assertEqual(daily.week_comparison(TODAY), {"status": daily.HELD, "better": []})

    def test_group_share_at_same_tempo(self):
        summary = {"first_try_correct": 170, "first_try_total": 200}
        write_session(self.dir, TODAY - timedelta(days=9), "group", summary=summary)
        write_session(self.dir, TODAY, "group", summary={"first_try_correct": 188, "first_try_total": 200})
        write_session(self.dir, TODAY, "group", config={"farnsworth_wpm": 15}, index=1,
                      summary={"first_try_correct": 200, "first_try_total": 200})  # anderes Tempo
        result = daily.week_comparison(TODAY)
        self.assertEqual(result["better"], [{"kind": "groups", "wpm": 12, "before": 0.85, "now": 0.94}])

    def test_char_moments_today_against_last_week(self):
        self.latency_week(TODAY - timedelta(days=3), "R", 0.8)
        self.latency_week(TODAY, "R", 0.4, count=daily.LATENCY_TODAY_MIN)
        self.latency_week(TODAY, "K", 0.2, count=daily.LATENCY_TODAY_MIN - 1, index=1)
        self.assertEqual(daily.char_moments(TODAY), [{"kind": "latency", "char": "R", "before": 0.8, "now": 0.4}])

    def test_block_summary(self):
        warmup = daily.Block(daily.WARMUP, "single", 3)
        result = {"correct": 40, "total": 44, "best_streak": 12, "chars": {"R": [6, 6], "S": [6, 4], "K": [2, 2]}}
        summary = daily.block_summary(warmup, result, due="RSKX")
        self.assertEqual((summary["due_practiced"], summary["due_sure"], summary["streak"]), (3, 1, 12))
        summary = daily.block_summary(main_block(), main_result(90, 100))
        self.assertEqual((summary["correct"], summary["total"]), (90, 100))

    def test_lesson_outlook(self):
        state = {"lesson": 12, "days": {}}
        self.assertIsNone(daily.lesson_outlook(state, TODAY))
        daily.finish_block(state, TODAY, main_block(), main_result(84, 100, wpm=12))  # zu langsame Zeichen
        self.assertEqual(daily.lesson_outlook(state, TODAY), {"lesson": 13, "missing": 6})
        daily.finish_block(state, TODAY, main_block(), main_result(95, 100))
        self.assertEqual(daily.lesson_outlook(state, TODAY), {"lesson": 13, "pending": True})

    def test_extra_offer_once_and_only_after_good_main_part(self):
        state = {"lesson": 30, "days": {}}
        self.assertIsNone(daily.extra_offer(state, TODAY, 30, ""))
        daily.finish_block(state, TODAY, main_block(), main_result(70, 100))
        self.assertIsNone(daily.extra_offer(state, TODAY, 30, ""))
        daily.finish_block(state, TODAY, main_block(), main_result(80, 100))
        self.assertEqual(daily.extra_offer(state, TODAY, 30, "BD"), (daily.CONFUSIONS, "BD"))
        self.assertEqual(daily.extra_offer(state, TODAY, 30, ""), (daily.RUFZ, ""))
        self.assertEqual(daily.extra_offer(state, TODAY, 15, ""), (daily.WORD, ""))
        self.assertIsNone(daily.extra_offer(state, TODAY, 5, ""))
        state["days"][TODAY.isoformat()][daily.EXTRA] = True
        self.assertIsNone(daily.extra_offer(state, TODAY, 30, "BD"))
