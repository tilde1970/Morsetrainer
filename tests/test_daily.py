"""Tests für die Regeln der Tagesübung (core/daily.py): Stufen, Ablauf,
Tagestempo, Aufstieg, Sterne, Rückblick und Vorwochenvergleich."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import daily, db, koch, review, stats

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
                blocks = daily.plan(lesson, due, 0)
                self.assertEqual([b.kind for b in blocks], [daily.WARMUP, daily.MAIN, daily.OUTRO])
                self.assertAlmostEqual(sum(b.minutes for b in blocks), daily.TOTAL_MINUTES)
                self.assertGreaterEqual(blocks[1].minutes, daily.MAIN_MIN_MINUTES)

    def test_many_due_lengthen_warmup_up_to_limit(self):
        self.assertEqual(daily.warmup_minutes(15, 7), daily.WARMUP_MINUTES)
        self.assertGreater(daily.warmup_minutes(15, 8), daily.WARMUP_MINUTES)
        self.assertEqual(daily.warmup_minutes(15, 30), daily.WARMUP_MAX_MINUTES)
        self.assertEqual(daily.warmup_minutes(daily.POST_KOCH, 30), daily.WARMUP_POST_MINUTES)

    def test_warmup_gives_each_due_char_its_attempts(self):
        """Wie viele Versuche in der Zeit Platz haben, hängt von MIN_ATTEMPTS ab."""
        for due in (4, 9, 11):
            minutes = daily.warmup_minutes(15, due)
            attempts = minutes * 60 / daily.ATTEMPT_SECONDS
            self.assertGreaterEqual(attempts, due * review.MIN_ATTEMPTS)
        self.assertLessEqual(daily.warmup_minutes(15, 40), daily.WARMUP_MAX_MINUTES)
        self.assertAlmostEqual(sum(b.minutes for b in daily.plan(15, 40, 0)), daily.TOTAL_MINUTES)

    def test_block_summary_counts_undecided_due_chars(self):
        block = daily.Block(daily.WARMUP, "single", 3)
        result = {"correct": 20, "total": 24, "chars": {"R": [8, 8], "S": [8, 6], "K": [3, 3]}}
        summary = daily.block_summary(block, result, "RSKM")
        self.assertEqual(summary["due_undecided"], 2)  # K (3 Versuche) und M (nicht geübt)

    def test_too_tight_needs_many_misses_and_share(self):
        self.assertFalse(daily.too_tight({"timeouts": 4, "total": 8}))
        self.assertFalse(daily.too_tight({"timeouts": 5, "total": 40}))
        self.assertTrue(daily.too_tight({"timeouts": 12, "total": 24}))
        self.assertFalse(daily.too_tight({}))

    def test_nothing_due_uses_confusions(self):
        self.assertEqual(daily.plan(15, 0, 0)[0].params["focus"], "confusions")
        self.assertEqual(daily.plan(15, 2, 0)[0].params["focus"], "due")

    def test_practice_days_count_days_with_blocks_before_today(self):
        state = {"days": {}}
        self.assertEqual(daily.practice_days(state, TODAY), 0)
        # Jeden zweiten Kalendertag geübt: der Ausklang wechselt trotzdem.
        for i in (6, 4, 2):
            state["days"][(TODAY - timedelta(days=i)).isoformat()] = {"blocks": [{"kind": daily.MAIN}]}
        state["days"][(TODAY - timedelta(days=1)).isoformat()] = {"blocks": []}  # nur angefangen
        state["days"][TODAY.isoformat()] = {"blocks": [{"kind": daily.MAIN}]}  # heute zählt nicht mit
        self.assertEqual(daily.practice_days(state, TODAY), 3)
        outros = [daily.plan(35, 0, daily.practice_days(state, TODAY - timedelta(days=i)))[2].mode
                  for i in (6, 4, 2)]
        self.assertEqual(outros, ["word", "callsign", "word"])

    def test_post_koch_outro_cycle(self):
        both = {daily.QSO_HEAD, daily.QSO_LOG}
        modes = [daily.plan(daily.POST_KOCH, 0, turn, both, "wpx")[2] for turn in range(8)]
        self.assertEqual([b.mode for b in modes[:4]], ["callsign", daily.QSO_HEAD, "callsign", daily.QSO_LOG])
        self.assertEqual(modes[3].params, {"kind": "wpx"})
        self.assertTrue(all(b.minutes == daily.OUTRO_POST_MINUTES for b in modes))
        # Passt kein QSO (oder fehlen die Betriebszeichen), bleibt es bei Rufzeichen.
        self.assertEqual({daily.plan(daily.POST_KOCH, 0, turn)[2].mode for turn in range(4)}, {"callsign"})
        self.assertEqual(daily.plan(daily.POST_KOCH, 0, 1, {daily.QSO_LOG})[2].mode, "callsign")
        for turn in range(4):
            blocks = daily.plan(daily.POST_KOCH, 0, turn, both)
            self.assertAlmostEqual(sum(b.minutes for b in blocks), daily.TOTAL_MINUTES)

    def test_band_outro_takes_every_second_contest_run(self):
        both = {daily.QSO_HEAD, daily.QSO_LOG}
        outros = [daily.plan(daily.POST_KOCH, 0, turn, both, "wpx", "light")[2] for turn in range(16)]
        self.assertEqual([b.mode for b in outros[3::4]], [daily.QSO_LOG, "continuous", daily.QSO_LOG, "continuous"])
        self.assertEqual(outros[7].params, {"content": "chars", "group_len": 5, "band": True,
                                            daily.BAND_PRESET: "light"})
        self.assertEqual(outros[7].minutes, daily.OUTRO_POST_MINUTES)
        # Noch keine Stufe (Tempo zu niedrig): Contest-Run wie bisher.
        self.assertEqual(daily.plan(daily.POST_KOCH, 0, 7, both)[2].mode, daily.QSO_LOG)
        # Passt kein Contest-Run, kommt das Band, ohne beides Rufzeichen.
        self.assertEqual(daily.plan(daily.POST_KOCH, 0, 3, set(), "wpx", "medium")[2].params[daily.BAND_PRESET],
                         "medium")
        self.assertEqual(daily.plan(daily.POST_KOCH, 0, 7, set())[2].mode, "callsign")
        # Die übrigen Plätze bleiben.
        self.assertEqual([b.mode for b in outros[:3]], ["callsign", daily.QSO_HEAD, "callsign"])

    def test_band_level_rises_after_two_good_days_and_falls_back(self):
        state = {"days": {}}

        def outro(day, preset, correct, total=200, band_min=None):
            entry = state["days"].setdefault((TODAY - timedelta(days=day)).isoformat(), {"blocks": []})
            entry["blocks"].append({"kind": daily.OUTRO, "mode": "continuous", "band": preset, "correct": correct,
                                    "total": total, "extra_keys": 0, "band_min": band_min or preset})

        self.assertEqual(daily.band_level(state, TODAY), "light")
        outro(9, "light", 190)
        outro(9, "light", 195)  # derselbe Tag zählt einmal
        outro(8, "light", 190, total=50)  # zu wenige Zeichen
        outro(7, "light", 190, band_min=None)
        state["days"][(TODAY - timedelta(days=7)).isoformat()]["blocks"][-1]["band_min"] = None  # zwischendurch aus
        self.assertEqual(daily.band_level(state, TODAY), "light")
        outro(6, "light", 180)
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        self.assertEqual(daily.band_level(state, TODAY - timedelta(days=6)), "light")  # wirksam ab dem Tag danach
        outro(5, "medium", 150)
        outro(4, "medium", 170)  # dazwischen gut: kein Rückfall
        outro(3, "medium", 150)
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        outro(2, "medium", 150)
        self.assertEqual(daily.band_level(state, TODAY), "light")
        outro(1, "light", 200)  # alte gute Tage vor dem Rückfall zählen nicht mehr
        self.assertEqual(daily.band_level(state, TODAY), "light")

    def test_band_level_easier_run_counts_only_against_the_level(self):
        # Auf „mittel“ zwischendurch leichter gestellt: Ein Scheitern ist ein
        # Fehlversuch, ein gutes Ergebnis löscht den vorigen nicht.
        def days(*runs):
            # Tag 9 und 8 gut auf „leicht“: ab Tag 7 auf „mittel“.
            runs = ((9, "light", 190, "light"), (8, "light", 190, "light")) + runs
            state = {"days": {}}
            for day, preset, correct, band_min in runs:
                state["days"][(TODAY - timedelta(days=day)).isoformat()] = {"blocks": [
                    {"kind": daily.OUTRO, "mode": "continuous", "band": preset, "correct": correct,
                     "total": 200, "extra_keys": 0, "band_min": band_min}]}
            return daily.band_level(state, TODAY)

        self.assertEqual(days(), "medium")
        m = "medium"
        self.assertEqual(days((3, m, 150, m), (2, m, 170, "light"), (1, m, 150, m)), "light")
        self.assertEqual(days((3, m, 150, m), (2, m, 170, m), (1, m, 150, m)), "medium")
        self.assertEqual(days((2, m, 150, "light"), (1, m, 150, None)), "light")  # Scheitern trotz Erleichterung

    def test_band_level_counts_one_whole_outro_a_day(self):
        state = {"days": {}}

        def outro(day, preset, correct, **extra):
            entry = state["days"].setdefault((TODAY - timedelta(days=day)).isoformat(), {"blocks": []})
            entry["blocks"].append({"kind": daily.OUTRO, "mode": "continuous", "band": preset, "correct": correct,
                                    "total": 200, "extra_keys": 0, "band_min": preset, **extra})

        outro(9, "light", 190)
        outro(8, "light", 190, stopped=True)  # abgebrochen: zählt nicht als zweiter Tag
        self.assertEqual(daily.band_level(state, TODAY), "light")
        outro(7, "light", 190)
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        outro(6, "medium", 150)
        outro(6, "medium", 150)  # zweiter am selben Tag (Zugabe): nicht „in Folge“
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        outro(5, "medium", 150, stopped=True)
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        outro(4, "medium", 170)
        outro(4, "medium", 150)  # nur der erste des Tages zählt: gut
        outro(3, "medium", 150)
        self.assertEqual(daily.band_level(state, TODAY), "medium")
        outro(2, "medium", 150)
        self.assertEqual(daily.band_level(state, TODAY), "light")

    def test_band_change_and_star_only_for_a_new_stage(self):
        state = {"days": {}}

        def outro(day, preset, correct):
            today = TODAY - timedelta(days=day)
            result = {"correct": correct, "total": 200, "extra_keys": 0, "minutes": 4.0, "band_min": preset}
            return daily.finish_block(state, today, daily.band_outro(preset), result), daily.band_change(state, today)

        self.assertEqual(outro(9, "light", 190), ([], None))  # erster guter Tag: noch kein Wechsel
        self.assertEqual(outro(8, "light", 190), ([daily.WEITER], ("light", "medium")))
        self.assertEqual(outro(7, "medium", 150), ([], None))
        self.assertEqual(outro(6, "medium", 150), ([], ("medium", "light")))  # Rückfall, Sterne bleiben
        outro(5, "light", 190)
        stars, change = outro(4, "light", 190)
        self.assertEqual(change, ("light", "medium"))
        self.assertEqual(stars, [])  # wieder mittel: schon einmal erreicht, kein ★ Weiter
        self.assertIsNone(daily.band_change(state, TODAY))  # heute kein Band-Ausklang

    def test_band_outro_is_stored_with_its_stage(self):
        state = {"days": {}}
        daily.finish_block(state, TODAY, daily.band_outro("medium"), {"correct": 1, "total": 1, "minutes": 4.0})
        self.assertEqual(state["days"][TODAY.isoformat()]["blocks"][-1]["band"], "medium")

    def test_qso_outros_need_time_tempo_and_prosigns(self):
        fits = lambda mode: True  # noqa: E731
        everything = koch.FINAL_CHARSET + koch.PROSIGN_ORDER
        self.assertEqual(daily.qso_outros(20, everything, fits), {daily.QSO_HEAD, daily.QSO_LOG})
        self.assertEqual(daily.qso_outros(20, koch.FINAL_CHARSET + "+(*", fits), {daily.QSO_LOG})  # BK fehlt
        self.assertEqual(daily.qso_outros(daily.QSO_HEAD_MIN_EFFECTIVE - 1, everything, fits), {daily.QSO_LOG})
        self.assertEqual(daily.qso_outros(20, everything, lambda mode: mode == daily.QSO_LOG), {daily.QSO_LOG})
        self.assertEqual(daily.qso_outros(20, everything, lambda mode: False), set())

    def test_word_outro_mixes_phrases_from_lesson_35(self):
        def word_block(lesson):
            return next(daily.plan(lesson, 0, turn)[2] for turn in range(2) if daily.plan(lesson, 0, turn)[2].mode == "word")
        self.assertEqual(word_block(daily.PHRASES_FROM_LESSON - 1).params, {})
        self.assertEqual(word_block(daily.PHRASES_FROM_LESSON).params, {"content": "mixed"})
        self.assertEqual(word_block(20).params, {})

    def test_outro_by_stage(self):
        self.assertEqual(daily.plan(5, 0, 0)[2].mode, "continuous")
        self.assertEqual(daily.plan(15, 0, 0)[2].mode, "word")
        mixed = {daily.plan(35, 0, turn)[2].mode for turn in range(2)}
        self.assertEqual(mixed, {"word", "callsign"})  # im Wechsel der Übungstage
        post = daily.plan(daily.POST_KOCH, 0, 0)
        self.assertEqual((post[1].mode, post[2].mode), ("continuous", "callsign"))


class TempoTest(unittest.TestCase):
    def test_no_tempo_up_when_not_allowed(self):
        start = {"wpm": 20, "effective": 12}
        self.assertEqual(daily.next_tempo(start, main_result(95, 100), allow_up=False), start)
        self.assertEqual(daily.next_tempo(start, main_result(70, 100), allow_up=False),
                         {"wpm": 20, "effective": 11})

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


class RefresherTest(unittest.TestCase):
    """Wiedereinsteiger: schneller Aufstieg und Start mit 15 WPM."""

    def test_lessons_per_day_by_first_try_share(self):
        steps = lambda correct, **kw: daily.lesson_steps(main_result(correct, 100, **kw), 20, True)
        self.assertEqual([steps(c) for c in (100, 95, 94, 90, 85, 84, 0)], [3, 3, 1, 1, 1, 0, 0])
        # Zu wenige Zeichen oder zu langsame Zeichen zählen nicht.
        self.assertEqual(daily.lesson_steps(main_result(40, 40), 20, True), 0)
        self.assertEqual(daily.lesson_steps(main_result(100, 100), koch.SLOW_CHAR_WPM - 1, True), 0)
        # Ohne den Haken gilt die Regel wie bisher: eine Lektion bei 90 %.
        self.assertEqual([daily.lesson_steps(main_result(c, 100), 20) for c in (100, 90, 89)], [1, 1, 0])

    def test_pending_lesson_jumps_and_stops_at_koch_end(self):
        state = {"days": {}, "lesson": 12, "tempo": {"wpm": 15, "effective": 15}}
        daily.finish_block(state, TODAY, main_block(), main_result(97, 100), refresh=True)
        self.assertEqual(state["pending_lesson"], 15)
        state = {"days": {}, "lesson": 40, "tempo": {"wpm": 15, "effective": 15}}
        daily.finish_block(state, TODAY, main_block(), main_result(100, 100), refresh=True)
        self.assertEqual(state["pending_lesson"], daily.POST_KOCH)
        # Ohne den Haken bleibt es bei einer Lektion.
        state = {"days": {}, "lesson": 12}
        daily.finish_block(state, TODAY, main_block(), main_result(97, 100))
        self.assertEqual(state["pending_lesson"], 13)

    def test_only_one_jump_per_day(self):
        state = {"days": {}, "lesson": 12, "tempo": {"wpm": 15, "effective": 15}}
        daily.finish_block(state, TODAY, main_block(), main_result(97, 100), refresh=True)
        daily.finish_block(state, TODAY, main_block(), main_result(100, 100), refresh=True)
        self.assertEqual(state["pending_lesson"], 15)

    def test_start_tempo_is_15_without_farnsworth_only_when_nothing_saved(self):
        self.assertEqual(daily.current_tempo({}, 20, 10, refresh=True), {"wpm": 15, "effective": 15})
        self.assertEqual(daily.current_tempo({}, 20, 10), {"wpm": 20, "effective": 10})
        saved = {"tempo": {"wpm": 22, "effective": 18}}
        self.assertEqual(daily.current_tempo(saved, 20, 10, refresh=True), {"wpm": 22, "effective": 18})

    def test_outlook_names_the_regained_characters(self):
        state = {"days": {}, "lesson": 12}
        self.assertEqual(daily.refresh_known(state), (13, 41))
        self.assertEqual(daily.refresh_known({"lesson": daily.POST_KOCH}), (41, 41))
        daily.finish_block(state, TODAY, main_block(), main_result(80, 100), refresh=True)
        outlook = daily.lesson_outlook(state, TODAY, refresh=True)
        self.assertEqual((outlook["lesson"], outlook["missing"], outlook["refresh"]), (13, 5, (13, 41)))
        self.assertNotIn("refresh", daily.lesson_outlook(state, TODAY))

    def test_outlook_line_shows_progress(self):
        from morsetrainer.widgets import daily_panel
        line = daily_panel.outlook_line({"lesson": 13, "missing": 5, "refresh": (13, 41)})
        self.assertIn("Noch 5 %", line)
        self.assertIn("13 von 41 Zeichen wiedererlangt", line)
        self.assertNotIn("wiedererlangt", daily_panel.outlook_line({"lesson": 13, "missing": 5}))


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

    def test_tempo_outlook_names_the_reason(self):
        self.day(0, 95)
        outlook = daily.tempo_outlook(self.state, TODAY)
        self.assertEqual((outlook["change"], outlook["share"], outlook["tempo"]["effective"]), (1, 95, 13))
        self.day(1, 80)
        self.assertEqual(daily.tempo_outlook(self.state, TODAY + timedelta(days=1))["change"], 0)
        self.day(2, 60)
        self.assertEqual(daily.tempo_outlook(self.state, TODAY + timedelta(days=2))["change"], -1)
        self.assertIsNone(daily.tempo_outlook(self.state, TODAY + timedelta(days=5)))  # nichts vorgemerkt

    def test_plateau_after_ten_days_at_same_tempo_once_in_a_while(self):
        for offset in range(daily.PLATEAU_DAYS):
            self.day(offset, 80)  # Tempo bleibt
        last = TODAY + timedelta(days=daily.PLATEAU_DAYS - 1)
        self.assertTrue(daily.tempo_outlook(self.state, last)["plateau"])
        self.state[daily.PLATEAU_HINT] = last.isoformat()
        self.assertFalse(daily.plateau_due(self.state, last + timedelta(days=1)))
        self.assertTrue(daily.plateau_due(self.state, last + timedelta(days=daily.PLATEAU_REPEAT_DAYS)))

    def test_no_plateau_while_lessons_come(self):
        """Im Koch-Teil bleibt das Tempo fest; steigt die Lektion, geht es voran."""
        for offset in range(daily.PLATEAU_DAYS):
            self.state["lesson"] = 3 + offset // 2
            self.day(offset, 80)
            daily.day_entry(self.state, TODAY + timedelta(days=offset))["lesson"] = self.state["lesson"]
        self.assertFalse(daily.plateau_due(self.state, TODAY + timedelta(days=daily.PLATEAU_DAYS)))

    def test_plateau_in_the_same_lesson(self):
        for offset in range(daily.PLATEAU_DAYS):
            self.state["lesson"] = 12
            self.day(offset, 80)
        self.assertTrue(daily.plateau_due(self.state, TODAY + timedelta(days=daily.PLATEAU_DAYS)))
        self.assertEqual(daily.tempo_outlook(self.state, TODAY + timedelta(days=daily.PLATEAU_DAYS - 1))["lesson"], 12)

    def test_slower_tomorrow_only_with_a_pending_slowdown(self):
        self.day(0, 60)
        self.assertTrue(daily.slower_tomorrow(self.state, TODAY))
        self.assertFalse(daily.slower_tomorrow(self.state, TODAY + timedelta(days=1)))
        self.day(1, 80)
        self.assertFalse(daily.slower_tomorrow(self.state, TODAY + timedelta(days=1)))

    def test_sure_before_pause_and_pause_check(self):
        boxes = {"K": {"box": 4}, "M": {"box": 2}, "R": {"box": 3}, "S": "kaputt", "T": {"box": None}}
        self.assertEqual(daily.sure_before_pause(boxes, "KMRST"), "KR")
        result = {"chars": {"K": (8, 8), "R": (4, 2), "M": (9, 9)}}
        self.assertEqual(daily.pause_check(result, "KR"), (2, 1))
        self.assertIsNone(daily.pause_check(result, "K"))  # unter zwei geprüften
        self.assertIsNone(daily.pause_check({"chars": {"K": (2, 2), "R": (2, 2)}}, "KR"))  # zu wenige Versuche

    def test_pause_check_limits(self):
        self.assertEqual(daily.pause_check({"chars": {"K": (3, 3), "R": (3, 3)}}, "KR"), (2, 2))  # 3 Versuche zählen
        self.assertIsNone(daily.pause_check({"chars": {"K": (2, 2), "R": (3, 3)}}, "KR"))  # 2 nicht
        exact = daily.pause_check({"chars": {"K": (10, 9), "R": (10, 9)}}, "KR")
        self.assertEqual(exact, (2, 2))  # genau 90 %: wieder sicher
        self.assertEqual(daily.pause_check({"chars": {"K": (10, 8), "R": (10, 8)}}, "KR"), (2, 0))

    def test_days_since_practice_and_today_numbers(self):
        self.assertIsNone(daily.days_since_practice(self.state, TODAY))
        self.day(0, 80)
        self.assertEqual(daily.days_since_practice(self.state, TODAY + timedelta(days=20)), 20)
        self.assertIsNone(daily.days_since_practice(self.state, TODAY))  # nur vor dem Tag
        entry = daily.day_entry(self.state, TODAY)
        entry["blocks"].append({"kind": "warmup", "total": 40, "best_streak": 9})
        numbers = daily.today_numbers(self.state, TODAY)
        self.assertEqual(numbers, {"chars": 140, "streak": 9})

    def test_errors_are_not_stored_in_the_day(self):
        daily.finish_block(self.state, TODAY, main_block(), main_result(90, 100, errors={"total": 10}))
        self.assertNotIn("errors", self.state["days"][TODAY.isoformat()]["blocks"][-1])

    def test_no_plateau_when_tempo_moved(self):
        for offset in range(daily.PLATEAU_DAYS):
            self.day(offset, 80 if offset != 4 else 60)
        self.assertFalse(daily.plateau_due(self.state, TODAY + timedelta(days=daily.PLATEAU_DAYS)))

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
        result = {"correct": 40, "total": 44, "best_streak": 12, "chars": {"R": [8, 8], "S": [8, 6], "K": [2, 2]}}
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

    def test_prosign_hint_once_after_lesson_41(self):
        self.assertFalse(daily.prosign_hint_due({"lesson": 41}, 41, ""))
        self.assertTrue(daily.prosign_hint_due({"lesson": 41, "pending_lesson": daily.POST_KOCH}, 41, ""))
        state = {"lesson": daily.POST_KOCH}
        self.assertTrue(daily.prosign_hint_due(state, 41, ""))
        self.assertFalse(daily.prosign_hint_due(state, 42, ""))     # schon bei den Betriebszeichen
        self.assertFalse(daily.prosign_hint_due(state, 41, "AB+"))  # AR in der Lernkartei
        state[daily.PROSIGN_HINT] = TODAY.isoformat()
        self.assertFalse(daily.prosign_hint_due(state, 41, ""))

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


class PanelTextTest(unittest.TestCase):
    def test_tempo_lines_are_neutral_and_give_the_scale_after_koch(self):
        from morsetrainer.widgets.daily_panel import tempo_lines
        slower = tempo_lines({"tempo": {"wpm": 20, "effective": 11}, "change": -1, "share": 62, "lesson": 12})
        self.assertIn("einen Schritt langsamer, damit es wieder sitzt", slower[0])
        self.assertNotIn("nur", slower[0])
        same_koch = tempo_lines({"tempo": {"wpm": 20, "effective": 12}, "change": 0, "share": 82, "lesson": 12})
        self.assertNotIn("Ab 90 %", same_koch[0])  # im Koch-Teil steigt das Tempo nicht mit der Quote
        same_post = tempo_lines({"tempo": {"wpm": 20, "effective": 12}, "change": 0, "share": 82,
                                 "lesson": daily.POST_KOCH})
        self.assertIn("Ab 90 % geht es schneller.", same_post[0])

    def test_plateau_advice_fits_the_lesson(self):
        from morsetrainer.widgets.daily_panel import tempo_lines
        base = {"tempo": {"wpm": 20, "effective": 12}, "change": 0, "share": 80, "plateau": True}
        early = tempo_lines(dict(base, lesson=5))[-1]
        words = tempo_lines(dict(base, lesson=daily.WORDS_FROM_LESSON))[-1]
        calls = tempo_lines(dict(base, lesson=daily.CALLS_FROM_LESSON))[-1]
        self.assertTrue(early.endswith("Oft hilft ein Tag Pause."))
        self.assertNotIn("Wörter", early)
        self.assertTrue(words.endswith("Wörter statt Gruppen."))
        self.assertNotIn("Rufzeichen", words)
        self.assertTrue(calls.endswith("Wörter und Rufzeichen statt Gruppen."))

    def test_end_note_without_a_star(self):
        from morsetrainer.widgets.daily_panel import end_note
        self.assertEqual(end_note(True, []), "Tagesübung geschafft.")
        self.assertIn("deine Sterne bleiben", end_note(False, [daily.DABEI]))
        self.assertIn("kein Stern", end_note(False, []))
        self.assertNotIn("Sterne bleiben", end_note(False, []))

    def test_today_line_only_states_what_there_is(self):
        from morsetrainer.widgets.daily_panel import today_line
        self.assertEqual(today_line({"chars": 190, "streak": 14}, 5),
                         "Heute: 190 Zeichen gehört, beste Serie 14, 5 Zeichen schon in Fach 2 oder höher.")
        self.assertEqual(today_line({"chars": 190, "streak": 2}, 0), "Heute: 190 Zeichen gehört.")
        self.assertEqual(today_line({"chars": 0, "streak": 0}, 3), "")
