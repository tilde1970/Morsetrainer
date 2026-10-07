"""Tests für die Auswertung in den Trainingsreitern mit echtem Tk-Fenster,
aber ohne Ton; ohne Anzeige (kein $DISPLAY) werden sie übersprungen. Die
Wiedergabe wird übersprungen: die Tests setzen den Zustand nach dem Ton
direkt und rufen die Auswertung auf."""
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import app as app_module
from morsetrainer.core import db, koch, stats
from morsetrainer.modes import continuous_mode, run_mode, single_mode
from morsetrainer.modes import sequence_mode as sq
from morsetrainer.widgets import theme


class AppTestCase(unittest.TestCase):
    """Hauptfenster mit allen Reitern, Daten in einem Temp-Verzeichnis."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
            mock.patch.object(app_module, "WINDOW_STATE_FILE", directory / "window_state.json"),
        ]
        for patch in self.patches:
            patch.start()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()
        self.app = app_module.MorseTrainerApp(self.root)
        self.app.charset_var.set("KMUR")

    def mode(self, title):
        return self.app.modes[self.app.mode_titles.index(title)]

    def tearDown(self):
        from morsetrainer.widgets import announcer
        announcer._instance = None  # nicht über ein zerstörtes Fenster weitersprechen
        if hasattr(self, "root"):
            for mode in self.app.modes:
                mode.running = False
            self.root.destroy()
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()



class GroupEvaluationTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.group = self.mode("Gruppen")

    def _start(self, style=sq.COPY):
        self.group.style_var.set(style)
        self.group.start()
        self.group.running = True

    def _answer(self, sequence, typed, replayed=False, seconds_after_tone=0.1):
        """Eine neue Sequenz beantworten (erster Versuch)."""
        g = self.group
        g.current_sequence, g.attempts, g.replayed, g.repeat_pending = sequence, 0, replayed, False
        g.voice = (20, 600)
        g.tone_starts = [time.time() - 1.0] * len(sequence)
        g.tone_ends = [time.time() - seconds_after_tone] * len(sequence)
        g.enter_time = None
        g.waiting_for_input = True
        g.input_var.set(typed)
        g.on_submit()

    def test_clean_first_attempt_counts(self):
        self._start()
        self._answer("KMU", "KMU")
        self.assertEqual((self.group.first_try_correct, self.group.first_try_total), (3, 3))
        self.assertTrue(self.group.feedback_var.get().startswith("Richtig: KMU"))

    def test_session_log_has_lesson_conditions_and_first_tries(self):
        self._start()
        self._answer("KMU", "KMU")
        session_id = self.group.session_stats.session_id
        self.group._finalize_session()
        lines = list(tests.session_lines(session_id))
        config, summary = lines[0], lines[-1]
        self.assertEqual((config["lesson"], config["band"], config["adaptive_tempo"]), (3, None, False))
        self.assertNotIn("band_gain", config)
        self.assertEqual((summary["first_try_correct"], summary["first_try_total"]), (3, 3))

    def test_group_lines_mark_clean_first_try(self):
        self._start()
        self._answer("KMU", "KMU")
        self._answer("KMU", "KMU", replayed=True)
        self._answer("KMU", "KMM")
        session_id = self.group.session_stats.session_id
        self.group._finalize_session()
        firsts = [line["first"] for line in tests.session_lines(session_id) if line["type"] == "group"]
        self.assertEqual(firsts, [True, False, False])

    def test_replayed_slow_or_overtyped_do_not_count(self):
        self._start()
        self._answer("KMU", "KMU", replayed=True)
        self._answer("KMU", "KMU", seconds_after_tone=sq.answer_limit(3) + 1)
        self._answer("KMKMK", "KMKMKMKMKM")
        self.assertEqual(self.group.first_try_correct, 0)
        self.assertEqual(self.group.first_try_total, 3 + 3 + 5)

    def test_slow_answers_count_as_unsure(self):
        self._start(sq.MEMORIZE)
        self._answer("KMU", "KMM", seconds_after_tone=sq.answer_limit(3) + 1)
        rounds = self.group.session_stats.rounds
        self.assertEqual([r["correct"] for r in rounds], [True, True, False])  # Quote ehrlich
        self.assertTrue(all(r["latency_s"] == stats.LATENCY_CAP_S for r in rounds if r["correct"]))

    def test_recognized_only_after_replay_counts_as_missed(self):
        # Wie bei Einzelzeichen: erst nach der Leertaste erkannt = nicht erkannt.
        self._start()
        self._answer("KMU", "KMM", replayed=True)
        rounds = self.group.session_stats.rounds
        self.assertEqual([(r["typed"], r["correct"]) for r in rounds], [("", False), ("", False), ("M", False)])

    def test_unsure_latency_is_twice_the_usual(self):
        with mock.patch.object(sq.CharPicker, "median_latency", lambda self: 0.8):
            self._start(sq.MEMORIZE)
        self._answer("KMU", "KMU", seconds_after_tone=sq.answer_limit(3) + 1)
        self.assertEqual({r["latency_s"] for r in self.group.session_stats.rounds}, {1.6})

    def test_second_attempt_hides_solution_and_is_not_recorded(self):
        self._start()
        self.group.give_up_var.set(2)
        self._answer("KMU", "KKK")
        self.assertNotIn("gesendet", self.group.diff_var.get())
        self.assertEqual(len(self.group.session_stats.rounds), 3)
        g = self.group
        g.waiting_for_input, g.repeat_pending = True, False
        g.input_var.set("KMU")
        g.on_submit()
        self.assertEqual(len(g.session_stats.rounds), 3)  # zweiter Versuch nicht gezählt
        self.assertEqual(g.first_try_correct, 1)  # nur das K aus dem ersten Versuch

    def test_lesson_hint_and_legend(self):
        self._start()
        g = self.group
        g.current_sequence, g.attempts, g.replayed, g.submit_pending = "KMU", 0, False, False
        g.on_playback_done()
        self.assertIn("zügig", g.status_var.get())
        self._answer("KMU", "KKK")
        self.assertIn("– fehlt/zu viel, ^ falsch", g.diff_var.get())

    def test_give_up_shows_solution(self):
        self._start()  # Standard: Lösung nach dem ersten Fehlversuch
        self._answer("KMU", "KKK")
        self.assertIn("gesendet", self.group.diff_var.get())
        self.assertIn("Lösung: KMU", self.group.feedback_var.get())

    def test_head_copy_is_self_assessed(self):
        self._start(sq.HEAD)
        g = self.group
        g.current_sequence, g.attempts, g.voice = "KMU", 0, (20, 600)
        g.waiting_for_input = True
        g.reveal()
        g.assess(True)
        self.assertEqual(g.first_try_total, 0)
        g.stop()
        self.assertIsNone(g.koch_result)
        self.assertEqual(stats.load_all_time(), {})

    def test_growing_tempo_passes_character_speed(self):
        self.app.wpm_var.set(20)
        self.app.farnsworth_wpm_var.set(19)
        self.app.farnsworth_enabled_var.set(True)
        self.group.tempo_var.set(True)
        self._start()
        self.assertEqual(self.group.tempo_info_var.get(), "aktuell 20/19 WPM")
        self._answer("KMU", "KMU")
        self.assertEqual(self.group.tempo_info_var.get(), "aktuell 20 WPM")
        self._answer("KMU", "KMU")
        self.assertEqual(self.group.tempo_info_var.get(), "aktuell 21 WPM")
        self._answer("KMU", "KKK")
        self._answer("KMU", "KKK")
        self.assertEqual(self.group.tempo_info_var.get(), "aktuell 19 WPM")

    def test_word_mode_has_no_lesson_note(self):
        words = self.mode("Wörter")
        words.style_var.set(sq.COPY)
        self.app.charset_var.set("KMURESNAPTLWI")
        words.start()
        words.running = True
        words.current_sequence, words.attempts, words.replayed, words.voice = "ES", 0, True, (20, 600)
        words.tone_starts = words.tone_ends = [time.time()] * 2
        words.enter_time, words.waiting_for_input = None, True
        words.input_var.set("ES")
        words.on_submit()
        self.assertNotIn("Lektion", words.feedback_var.get())


class WordModeTest(AppTestCase):
    def test_memorize_is_default_for_words(self):
        self.assertEqual(self.mode("Wörter").style_var.get(), sq.MEMORIZE)
        self.assertEqual(self.mode("Gruppen").style_var.get(), sq.COPY)

    def test_old_settings_switch_to_memorize_once(self):
        w = self.mode("Wörter")
        w.restore_settings({"input_style": sq.COPY})  # von vor dem neuen Standard
        self.assertEqual(w.style_var.get(), sq.MEMORIZE)
        self.assertIn("Erst merken", w.status_var.get())
        w.style_var.set(sq.COPY)
        w.restore_settings(w.settings())  # danach bewusst gewählt: bleibt
        self.assertEqual(w.style_var.get(), sq.COPY)

    def test_slow_answer_is_noted(self):
        w = self.mode("Wörter")
        self.app.charset_var.set(koch.lesson_charset(20))
        w.style_var.set(sq.MEMORIZE)
        w.start()
        w.current_sequence, w.attempts, w.replayed, w.repeat_pending = "TNX", 0, False, False
        w.voice = (20, 600)
        w.tone_starts = [time.time() - 10] * 3
        w.tone_ends = [time.time() - sq.answer_limit(3) - 1] * 3
        w.enter_time, w.waiting_for_input = None, True
        w.input_var.set("TNX")
        w.on_submit()
        self.assertIn("zu langsam", w.feedback_var.get())

    def test_too_few_words_points_to_groups(self):
        w = self.mode("Wörter")
        self.app.charset_var.set("KMUR")  # Lektion 3: nur RR und UR
        self.assertFalse(w._validate_settings())
        self.assertIn("Gruppen", w.status_var.get())


class CallsignTest(AppTestCase):
    def test_learned_only_explains_missing_digit(self):
        calls = self.mode("Rufzeichen")
        calls.all_calls = ["DL4YM", "DK1AB"] * 40
        self.app.charset_var.set("KMURESNAPTLWI")  # noch keine Ziffer
        self.assertFalse(calls._validate_settings())
        self.assertIn("Ziffer", calls.status_var.get())
        calls.learned_var.set(False)
        self.assertTrue(calls._validate_settings())


class RufzTest(AppTestCase):
    def _answer(self, g, call, typed):
        g.current_sequence, g.attempts, g.replayed, g.repeat_pending = call, 0, False, False
        g.voice = (g.tempo, 600)
        g.tone_starts = [time.time() - 1.0] * len(call)
        g.tone_ends = [time.time() - 0.1] * len(call)
        g.enter_time, g.waiting_for_input = None, True
        g.input_var.set(typed)
        g.on_submit()

    def test_run_of_50_scores_logs_and_keeps_best(self):
        g = self.mode("Rufzeichen")
        g.all_calls = [f"DL{i}YM" for i in range(60)]
        g.learned_var.set(False)
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(False)
        g.rufz_var.set(True)
        g.style_var.set(sq.COPY)
        g.start()
        self.assertTrue(g.running)
        g.repeat_sequence()
        self.assertFalse(g.replayed)  # kein Wiederholen im Rufz
        self.assertEqual(str(g.repeat_button["state"]), "disabled")
        for i in range(50):
            call = "DL4YM"
            self._answer(g, call, call if i % 5 else "DL4YN")  # jedes 5. falsch
        self.assertEqual((g.rufz_done, g.rufz_correct), (50, 40))
        self.assertGreater(g.rufz_score, 40 * 5 * 20)  # Tempo ist mitgewachsen
        g.next_sequence()  # vor dem 51. Rufzeichen: Ende
        self.assertFalse(g.running)
        self.assertIn("40 von 50 richtig", g.status_var.get())
        self.assertIn("Bestwert", g.status_var.get())
        self.assertEqual(g.settings()["rufz_best"], g.rufz_score)
        self.assertIn("rufz", [e["mode"] for e in stats.load_history()])
        # Verpasste nachhören und Starttempo beim Bestwert
        self.assertEqual(len(g.rufz_missed), 10)
        self.assertEqual(g.rufz_missed[0][:2], ("DL4YM", "DL4YN"))
        self.assertIn("(10, F6)", g.review_button["text"])
        self.assertIn("Start 20 WPM", g.rufz_best_var.get())
        from morsetrainer.modes import callsign_mode
        with mock.patch.object(g.review_button, "winfo_viewable", lambda: True), \
                mock.patch.object(callsign_mode.audio, "play") as play:
            g._review_missed()
            play.assert_called_once()
            # Erst unvoreingenommen hören: weder Lösung noch eigene Eingabe.
            self.assertIn("hör hin", g.status_var.get())
            self.assertNotIn("DL4Y", g.status_var.get())
            g._review_reveal(0, g.review_token)  # nach dem Ton: aufdecken, noch einmal
            self.assertEqual(play.call_count, 2)
        self.assertIn("Verpasst 1/10: DL4YM", g.status_var.get())
        self.assertIn("du: DL4YN", g.status_var.get())
        g.on_key(mock.Mock(keysym="Escape"))
        self.assertIsNone(g.review_index)
        self.assertIn("angehalten", g.status_var.get())

    def test_slow_correct_call_is_reviewed(self):
        g = self._start_rufz([f"DL{i}ABC" for i in range(60)])
        g.current_sequence, g.attempts, g.replayed, g.voice = "DL1ABC", 0, False, (20, 600)
        g.tone_starts = [time.time() - 10] * 6
        g.tone_ends = [time.time() - sq.answer_limit(6) - 1] * 6
        g.enter_time, g.waiting_for_input = None, True
        g.input_var.set("DL1ABC")
        g.on_submit()
        self.assertEqual(len(g.rufz_missed), 1)
        self.assertEqual(g.rufz_missed[0][0], "DL1ABC")
        self.assertTrue(g.rufz_missed[0][-1])  # richtig, aber zu langsam

    def _start_rufz(self, calls):
        g = self.mode("Rufzeichen")
        g.all_calls = calls
        g.learned_var.set(False)
        g.affix_var.set(False)
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(False)
        g.rufz_var.set(True)
        g.style_var.set(sq.COPY)
        g.start()
        return g

    def test_slow_correct_answer_gets_no_points(self):
        g = self._start_rufz([f"DL{i}ABC" for i in range(60)])
        g.current_sequence, g.attempts, g.replayed, g.voice = "DL1ABC", 0, False, (20, 600)
        g.tone_starts = [time.time() - 10] * 6
        g.tone_ends = [time.time() - sq.answer_limit(6) - 1] * 6
        g.enter_time, g.waiting_for_input = None, True
        g.input_var.set("DL1ABC")
        g.on_submit()
        self.assertEqual((g.rufz_done, g.rufz_score), (1, 0))
        self.assertIn("keine Punkte", g.feedback_var.get())

    def test_no_call_twice_and_history_only_as_rufz(self):
        calls = [f"DL{i}ABC" for i in range(60)]
        g = self._start_rufz(calls)
        sent = [g._generate_sequence() for _ in range(50)]
        self.assertEqual(len(set(sent)), 50)
        for call in sent:
            self._answer(g, call, call)
        g.next_sequence()
        modes = [e["mode"] for e in stats.load_history()]
        self.assertEqual(modes, ["rufz"])  # nicht zusätzlich als „Rufzeichen“
        self.assertEqual(stats.load_history()[0]["score"], g.rufz_score)
        result = db.results()[-1]
        self.assertEqual((result["start_wpm"], result["prefixes"], result["learned_only"]), (20, [], False))

    def test_rufz_needs_enough_calls(self):
        g = self.mode("Rufzeichen")
        g.all_calls = [f"DL{i}ABC" for i in range(40)]
        g.learned_var.set(False)
        g.rufz_var.set(True)
        self.assertFalse(g._validate_settings())

    def test_head_copy_not_allowed(self):
        g = self.mode("Rufzeichen")
        g.rufz_var.set(True)
        g.style_var.set(sq.HEAD)
        self.assertFalse(g._validate_settings())


class SingleCharTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.single = self.mode("Einzelzeichen")
        self.single.start()

    def _key(self, ch):
        self.single.on_key(type("E", (), {"keysym": ch, "char": ch})())

    def test_streak_of_first_hearing_answers(self):
        s = self.single
        for char, typed in (("K", "K"), ("M", "M"), ("U", "R"), ("R", "R")):
            s.current_char, s.voice, s.waiting_for_input, s.replayed = char, (20, 600), True, False
            s.play_start_time = time.time() - 0.5
            self._key(typed)
        self.assertEqual((s.best_streak, s.streak), (2, 1))

    def test_correct_after_repeat_counts_as_not_recognized(self):
        s = self.single
        s.current_char, s.voice, s.waiting_for_input = "K", (20, 600), True
        s.repeat_char()
        s.waiting_for_input = True  # Wiederholung zu Ende gespielt
        self._key("K")
        self.assertEqual(s.session_stats.summary()["correct"], 0)
        self.assertIn("K", s.retries.waiting)

    def test_wrong_answer_plays_both_and_shows_latency_when_right(self):
        s = self.single
        s.current_char, s.voice, s.waiting_for_input = "K", (20, 600), True
        s.play_start_time = time.time() - 0.5
        self._key("R")
        s._play_correction(s.timeout_token)
        self.assertIn("und so R (dein Tipp)", s.status_var.get())
        s.current_char, s.waiting_for_input, s.correcting = "M", True, False
        s.play_start_time = time.time() - 0.6
        self._key("M")
        self.assertRegex(s.feedback_var.get(), r"Richtig: M  \(\d+,\d\d s, Limit \d+,\d\d s\)")

    def test_space_during_feedback_pause_is_ignored(self):
        s = self.single
        s.current_char, s.voice, s.waiting_for_input = "K", (20, 600), True
        self._key("K")
        s.repeat_char()
        self.assertFalse(s.replayed)
        self.assertFalse(s.waiting_for_input)

    def test_small_charset_does_not_exclude_waiting_char(self):
        s = self.single
        s.charset = "KM"
        s.picker = single_mode.CharPicker("KM", False)
        s.retries.add("K")
        seen = set()
        for _ in range(40):
            s.retries.waiting = {"K": 3}
            s.play_current = lambda: None
            s.next_char()
            seen.add(s.current_char)
        self.assertEqual(seen, {"K", "M"})  # K kann weiter zufällig kommen

    def _answer(self, char, typed):
        s = self.single
        s.current_char, s.voice, s.waiting_for_input, s.replayed = char, (20, 600), True, False
        s.first_hearing, s.correcting = True, False
        s.play_start_time = time.time() - 0.5
        self._key(typed)

    def test_wrong_answer_in_time_keeps_limit(self):
        s = self.single
        s.limit = 1.0
        self._answer("K", "R")
        self.assertEqual(s.limit, 1.0)
        self._answer("K", "K")
        self.assertLess(s.limit, 1.0)
        s.current_char, s.waiting_for_input, s.first_hearing = "M", True, True
        limit = s.limit
        s._on_timeout(s.timeout_token)
        self.assertGreater(s.limit, limit)  # verpasst: länger

    def test_daily_block_caps_limit_and_shows_no_numbers(self):
        s = self.single
        s.daily_minutes = 3
        s.limit = 1.45
        s.current_char, s.voice, s.waiting_for_input, s.first_hearing = "M", (20, 600), True, True
        s._on_timeout(s.timeout_token)
        self.assertEqual(s.limit, 1.5)
        self.assertNotIn("Limit", s.feedback_var.get())
        self._answer("K", "K")
        self.assertEqual(s.feedback_var.get(), "Richtig: K")
        s.daily_minutes = None

    def test_groups_hint_needs_limit_whole_session(self):
        s = self.single
        s.icr_var.set(False)
        s._on_icr_toggle()
        s.stop()
        self.assertIsNone(s.groups_result)


class DailyInterfaceTest(AppTestCase):
    """Schnittstelle der Reiter für die Tagesübung (modes/daily_support.py)."""

    def test_configure_hides_options_and_release_restores_only_daily_keys(self):
        g = self.mode("Gruppen")
        g.restore_settings({"input_style": sq.MEMORIZE, "adaptive_tempo": True, "band": "light",
                            "give_up": 3, "adaptive": False, "min_len": 3, "max_len": 4})
        position = g.options_card.master.pack_slaves().index(g.options_card)
        g.daily_configure(4.5, input_style=sq.COPY, adaptive_tempo=False, band=None, give_up=1,
                          adaptive=True, min_len=2, max_len=6)
        self.assertEqual((g.style_var.get(), g.tempo_var.get(), g.band_var.get(), g.max_len_var.get()),
                         (sq.COPY, False, False, 6))
        self.assertEqual(g.options_card.winfo_manager(), "")
        g.saved_length = 5  # beim Üben erreicht: bleibt
        g.daily_release()
        self.assertEqual((g.style_var.get(), g.tempo_var.get(), g.band_var.get(), g.give_up_var.get(),
                          g.adaptive_var.get(), g.min_len_var.get(), g.max_len_var.get()),
                         (sq.MEMORIZE, True, True, 3, False, 3, 4))
        self.assertEqual(g.options_card.master.pack_slaves().index(g.options_card), position)
        self.assertEqual(g.saved_length, 5)
        self.assertIsNone(g.daily_minutes)

    def test_daily_block_sets_deadline_flag_and_result(self):
        g = self.mode("Gruppen")
        g.daily_configure(0.5, input_style=sq.COPY, adaptive_tempo=False, band=None, give_up=1)
        g.start()
        self.assertAlmostEqual(g.deadline - time.time(), 30, delta=2)
        session_id = g.session_stats.session_id
        g.running = True
        g.current_sequence, g.attempts, g.replayed, g.repeat_pending = "KM", 0, False, False
        g.voice = (20, 600)
        g.tone_starts = [time.time() - 1.0] * 2
        g.tone_ends = [time.time() - 0.1] * 2
        g.enter_time = None
        g.waiting_for_input = True
        g.input_var.set("KM")
        g.on_submit()
        g.stop()
        self.assertTrue(list(tests.session_lines(session_id))[0]["daily"])
        result = g.daily_result()
        self.assertEqual((result["first_try_correct"], result["first_try_total"], result["total"]), (2, 2, 2))
        self.assertEqual(result["best_streak"], 1)
        self.assertEqual(result["chars"]["K"][0], 1)
        self.assertEqual(result["wpm"], self.app.wpm_var.get())

    def test_copy_submits_without_enter_at_full_length(self):
        g = self.mode("Gruppen")
        g.start()
        g.current_sequence, g.attempts, g.replayed, g.repeat_pending = "KM", 0, False, False
        g.voice = (20, 600)
        g.tone_starts = [time.time() - 1.0] * 2
        g.tone_ends = [time.time() - 0.1] * 2
        g.enter_time = None
        g.waiting_for_input = True
        g._set_input_open(True)
        g.input_var.set("K")
        self.root.update()
        self.assertEqual(g.attempts, 0)  # noch nicht vollständig
        g.input_var.set("KM")
        self.root.update()
        self.assertEqual((g.attempts, g.first_try_correct), (1, 2))
        g.stop()

    def test_single_block_ends_between_chars(self):
        s = self.mode("Einzelzeichen")
        s.daily_configure(1, icr=True)
        s.start()
        self.assertIsNotNone(s.block_end)
        s.block_end = time.time() - 1
        s.next_char()
        self.assertFalse(s.running)
        self.assertIsNotNone(s.daily_result())
        s.daily_release()
        s.start()
        self.assertIsNone(s.block_end)  # ohne Tagesübung kein Blockende
        s.stop()


class ContinuousTest(AppTestCase):
    def test_guessing_ahead_and_overtyping_do_not_count(self):
        c = self.mode("Kontinuierlich")
        c.charset = "KM"
        c.session_stats = stats.SessionStats("continuous", "KM", 20, 600)
        now = 1000.0
        c.sent_log = [{"char": ch, "end_time": now + i} for i, ch in enumerate("KMKM")]
        # K vorab geraten (vor dem Ton), M richtig, dann zweimal doppelt getippt.
        c.typed_log = [{"char": "K", "time": now - 2}, {"char": "M", "time": now + 1.3},
                       {"char": "K", "time": now + 2.3}, {"char": "K", "time": now + 2.4},
                       {"char": "M", "time": now + 3.3}, {"char": "M", "time": now + 3.4}]
        c._finalize_session()
        charset, correct, total = c.koch_result
        self.assertEqual(total, 4)
        # 3 Treffer (M, K, M) minus 3 überzählige Tasten: die zwei doppelten und
        # das vorab geratene K (zählt als verpasst plus überzählig).
        self.assertEqual(correct, 0)
        self.assertTrue(continuous_mode.plausible(now + 0.5, now))
        self.assertFalse(continuous_mode.plausible(now - 1, now))


class ContinuousStopTest(AppTestCase):
    def _session(self, c, sent, typed):
        c.charset = "KM"
        c.session_stats = stats.SessionStats("continuous", "KM", 20, 600)
        c.sent_log = [{"char": ch, "end_time": t} for ch, t in sent]
        c.typed_log = [{"char": ch, "time": t} for ch, t in typed]

    def test_manual_stop_does_not_count_last_chars_and_shows_diff(self):
        c = self.mode("Kontinuierlich")
        now = time.time()
        # K und M gehört und getippt, das letzte K kam 0,5 s vor dem Stopp.
        self._session(c, [("K", now - 5), ("M", now - 4), ("K", now - 0.5)],
                      [("K", now - 4.6), ("M", now - 3.5)])
        session_id = c.session_stats.session_id
        c._finalize_session(stopped_at=now)
        summary = list(tests.session_lines(session_id))[-1]
        self.assertEqual((summary["extra_keys"], summary["completed"]), (0, False))  # von Hand gestoppt
        self.assertEqual((c.daily_result()["extra_keys"], c.daily_result()["completed"]), (0, False))
        self.assertEqual(c.koch_result[1:], (2, 2))  # das letzte K zählt nicht als verpasst
        self.assertIn("gesendet  K M", c.diff_var.get())
        self.assertIn("fehlt/zu viel", c.diff_var.get())

    def test_function_keys_start_and_stop(self):
        c = self.mode("Kontinuierlich")
        with mock.patch.object(c, "start") as start, mock.patch.object(c, "stop") as stop:
            c.on_function_key("F5")
            start.assert_called_once()
            c.running = True
            c.on_key(type("E", (), {"keysym": "Escape", "char": ""})())
            stop.assert_called_once()


    def test_f5_starts_and_stops_in_one_by_one(self):
        for title in ("Einzelzeichen", "Gruppen", "Wörter", "Rufzeichen"):
            m = self.mode(title)
            with mock.patch.object(m, "toggle_running") as toggle:
                m.on_function_key("F5")
                toggle.assert_called_once()
                m.start_button.state(["disabled"])  # etwa in der Tagesübung
                m.on_function_key("F5")
                toggle.assert_called_once()
                m.start_button.state(["!disabled"])


class ContinuousGroupingTest(AppTestCase):
    def test_word_gap_after_each_group(self):
        import contextlib
        c = self.mode("Kontinuierlich")

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        from morsetrainer.modes.content import ItemSource
        c.content, c.source = "chars", ItemSource("groups", "KM", 3)
        c.wpm, c.freq, c.fw, c.group_len = 20, 600, None, 3
        c.sent_log, c.running, c.deadline = [], True, None
        c.play_thread = threading.current_thread()  # Wiedergabe hier im Test-Thread
        word_gap = continuous_mode.word_gap_extra_seconds(20, None)
        gaps = []
        real_silence = continuous_mode.silence

        def counting_silence(seconds):
            if abs(seconds - word_gap) < 1e-9:
                gaps.append(seconds)
                if len(gaps) == 4:
                    c.running = False  # nach der vierten Wortpause aufhören
            return real_silence(seconds)

        with mock.patch.object(continuous_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())), \
                mock.patch.object(continuous_mode, "silence", counting_silence):
            c._play_session()
        self.assertEqual(len(c.sent_log), 12)  # 4 Wortpausen nach je 3 Zeichen
        self.assertEqual([e["group"] for e in c.sent_log], [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])


class ContinuousFullViewTest(AppTestCase):
    def test_grouped_lines_keep_groups_together(self):
        rows = [(ch, ch, " ", i // 5) for i, ch in enumerate("KMRSUKMRSUKM")]
        rows[2] = ("R", "S", "^", 0)
        rows.insert(5, ("–", "K", "^", 0))  # überzählige Taste am Ende der ersten Gruppe
        lines = continuous_mode.grouped_lines(rows, 13)
        self.assertEqual(lines[0], (1, "KMRSU–  KMRSU", "KMSSUK  KMRSU", "  ^  ^"))
        self.assertEqual(lines[1], (3, "KM", "KM", ""))
        # Zu schmal für zwei Gruppen: je Zeile eine, keine wird zerteilt.
        self.assertEqual([line[0] for line in continuous_mode.grouped_lines(rows, 4)], [1, 2, 3])
        self.assertEqual(continuous_mode.grouped_lines([], 20), [])

    def test_whole_session_in_a_separate_window(self):
        c = self.mode("Kontinuierlich")
        now = 1000.0
        c.charset = "KMRSU"
        c.session_stats = stats.SessionStats("continuous", "KMRSU", 20, 600)
        c.sent_log = [{"char": ch, "end_time": now + i, "group": i // 5} for i, ch in enumerate("KMRSU" * 10)]
        c.typed_log = [{"char": ch, "time": now + i + 0.5} for i, ch in enumerate("KMRSU" * 10) if i != 7]
        self.assertEqual(str(c.full_button.cget("state")), "disabled")
        c._finalize_session()
        self.assertEqual(len(c.full_rows), 50)  # alle, nicht nur die letzten DIFF_TAIL
        self.assertEqual(str(c.full_button.cget("state")), "normal")
        c.show_full()
        self.root.update()
        content = c.full_text.get("1.0", "end").splitlines()
        self.assertTrue(content[0].strip().startswith("1  KMRSU  KMRSU"))
        self.assertIn("KMRSU  KM–SU", content[1])  # das verpasste R
        self.assertTrue(c.full_text.tag_ranges("error"))
        c.sent_only_var.set(True)
        c._render_full()
        sent_only = c.full_text.get("1.0", "end")
        self.assertNotIn("–", sent_only)
        self.assertEqual(sent_only.replace(" ", "").replace("\n", "").lstrip("0123456789").count("KMRSU"), 10)
        c.copy_full()
        self.assertIn("KMRSU", self.root.clipboard_get())
        size = c.full_font.cget("size")
        c.zoom_full(1)
        self.assertGreater(c.full_font.cget("size"), size)
        window = c.full_window
        c.close_full()
        self.assertFalse(window.winfo_exists())


class SequenceBandTest(AppTestCase):
    def test_start_and_end_signs_carry_the_band_conditions(self):
        from morsetrainer.core import band
        s = self.mode("Gruppen")
        s.band_var.set(True)
        with mock.patch.object(sq.audio, "play") as play, \
                mock.patch.object(sq.audio, "play_quietly") as quietly:
            s.send_prosigns = True
            s._play_intro()
            intro = play.call_args[0][0]
            clean = sq.build_text(sq.START_TEXT + " ", *s._audio_settings(), s.farnsworth_wpm())
            self.assertEqual(len(intro), len(clean) + int(sum(band.PRESET_LEAD_SECONDS) * sq.SAMPLE_RATE))
            self.assertGreater(abs(intro[:100]).max(), 0)  # Rauschen gleich am Anfang
            s.stop()
            ending = quietly.call_args[0][0]
            self.assertGreater(len(ending), len(sq.build_text(sq.END_TEXT, *s._audio_settings())))


class ContinuousBandTest(AppTestCase):
    def test_band_conditions_run_under_the_whole_session(self):
        import numpy as np
        from morsetrainer.core import band
        c = self.mode("Kontinuierlich")
        c.restore_settings({"band": "medium"})  # Stufe aus Version 2.35: an
        self.assertIs(c.settings()["band"], True)
        c.band = band.preset_conditions("medium", 600)
        written = []
        stream = type("S", (), {"write": lambda self, block: written.append(block)})()
        c.running, c.play_thread = True, threading.current_thread()
        self.assertTrue(c._write(stream, np.zeros(4800, dtype=np.float32)))
        c.running = False
        self.assertEqual(sum(len(block) for block in written), 4800)
        self.assertGreater(max(abs(block).max() for block in written), 0)  # Rauschen auch in Pausen


class AudioThreadTest(AppTestCase):
    """Der Audio-Thread gehört zu seiner Sitzung und beendet sie auch bei
    unerwarteten Fehlern."""

    def test_old_thread_does_not_write_into_a_new_session(self):
        import numpy as np
        c = self.mode("Kontinuierlich")
        written = []
        stream = type("S", (), {"write": lambda self, block: written.append(block)})()
        c.running, c.play_thread = True, threading.Thread(target=lambda: None)  # neue Sitzung, anderer Thread
        self.assertFalse(c._write(stream, np.zeros(4800, dtype=np.float32)))
        self.assertEqual(written, [])
        c.running = False

    def test_unexpected_error_ends_the_session(self):
        for name, play in (("Kontinuierlich", "_play_session"), ("QSO", "_play_qso")):
            frame = self.mode(name)
            frame.audio_error, frame.play_thread = None, threading.current_thread()
            with mock.patch.object(frame, play, side_effect=RuntimeError("kaputt")):
                with self.assertRaises(RuntimeError):  # weiter ins Fehlerprotokoll
                    frame._play_loop()
            self.assertIn("kaputt", frame.audio_error)
            frame.audio_error, frame.play_thread = None, threading.Thread(target=lambda: None)
            with mock.patch.object(frame, play, side_effect=RuntimeError("alt")):
                with self.assertRaises(RuntimeError):
                    frame._play_loop()
            self.assertIsNone(frame.audio_error)  # alter Thread beendet die neue Sitzung nicht

    def test_contest_mixer_reports_unexpected_error(self):
        mixer = run_mode.Mixer(None)
        with mock.patch.object(mixer, "_mix", side_effect=RuntimeError("kaputt")):
            with self.assertRaises(RuntimeError):
                mixer._run()
        self.assertIn("kaputt", mixer.error)


class PlainTextStatsTest(AppTestCase):
    def test_words_do_not_count_for_the_char_statistics(self):
        self.assertFalse(self.mode("Wörter").char_stats)
        self.assertTrue(self.mode("Gruppen").char_stats)
        self.assertTrue(self.mode("Rufzeichen").char_stats)

    def test_qso_copy_ignores_keys_typed_ahead(self):
        q = self.mode("QSO")
        q.qso = mock.Mock(text=lambda: "DE")
        q.session_stats = stats.SessionStats("qso", "QSO-Text", 20, 600, char_stats=False)
        now = 1000.0
        q.sent_log = [{"char": "D", "end_time": now}, {"char": "E", "end_time": now + 1}]
        # „D“ vorausgeahnt, bevor es zu hören war; „E“ gehört.
        q.typed_log = [{"char": "D", "time": now - 2}, {"char": "E", "time": now + 1.3}]
        self.assertEqual(q._finalize_session(), 0.5)
        self.assertEqual(q.char_marks, (2, {0}))
        self.assertEqual(stats.load_all_time(), {})


class SlowTempoHintTest(AppTestCase):
    def test_header_warns_about_slow_characters(self):
        self.app.wpm_var.set(12)
        self.assertIn("12 WPM", self.app.slow_hint_var.get())
        self.assertEqual(self.app.slow_hint.winfo_manager(), "grid")
        self.app.wpm_var.set(koch.SLOW_CHAR_WPM)
        self.assertEqual(self.app.slow_hint.winfo_manager(), "")


class DrillDueTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, app_module.review, "focus", set())

    def test_due_chars_are_added_only_for_one_run(self):
        with mock.patch.object(app_module.review, "due_chars", lambda: ["Q", "K"]):
            self.app._drill_due()
            self.assertEqual(self.app.charset_var.get(), "KMURQ")
            self.app._drill_due()  # zweimal gedrückt: nicht doppelt
            self.assertEqual(self.app.charset_var.get(), "KMURQ")
        self.app._restore_drill_charset()
        self.assertEqual(self.app.charset_var.get(), "KMUR")

    def test_charset_changed_by_hand_stays(self):
        with mock.patch.object(app_module.review, "due_chars", lambda: ["Q"]):
            self.app._drill_due()
        self.app.charset_var.set("KMURES")
        self.app._restore_drill_charset()
        self.assertEqual(self.app.charset_var.get(), "KMURES")


class QsoRevealTest(AppTestCase):
    def test_text_hidden_until_quiz_checked(self):
        q = self.mode("QSO")
        q.qso, q.running, q.quiz_ready, q.quiz_checked = object(), False, True, False
        q._update_reveal_button()
        self.assertEqual(str(q.reveal_button["state"]), "disabled")
        q.quiz_checked = True
        q._update_reveal_button()
        self.assertEqual(str(q.reveal_button["state"]), "normal")


class QsoHeadCopyTest(AppTestCase):
    def _qso(self, mode):
        from morsetrainer.core import qso_text
        from morsetrainer.modes import qso_mode
        q = self.mode("QSO")
        q.eval_var.set(qso_mode.EVAL_LABELS[mode])
        q.qso = qso_text.generate_qso(qso_text.RAGCHEW, qso_text.LENGTH_NORMAL)
        q.voices, q.fw = ((20, 600), (20, 700)), None
        q.quiz_checked, q.replays = False, 0
        return q, qso_mode

    def test_head_copy_asks_a_few_content_questions(self):
        q, qso_mode = self._qso("head")
        view = q._quiz_view()
        self.assertEqual(len(view.quiz_rows), qso_mode.HEAD_QUESTIONS)
        self.assertEqual(view.quiz_columns, ("Antwort (wie gesendet)",))
        q.quiz.reset(view)
        q.quiz_ready = True
        q._update_layout()
        self.assertEqual(q.notes_box.winfo_manager(), "")  # kein Notizfeld beim Kopfhören
        self.assertEqual(q.quiz_box.winfo_manager(), "pack")

    def test_head_copy_blocks_replay_and_keeps_tempo(self):
        q, _ = self._qso("head")
        q.qso_eval = "head"
        q.adaptive_var.set(True)
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(False)
        q.replay()
        self.assertEqual(q.replays, 0)
        self.assertFalse(q.running)
        q._on_quiz_checked(3, 3)
        self.assertEqual(self.app.wpm_var.get(), 20)
        self.assertEqual(db.results()[-1]["mode"], "qso_head")

    def test_skipped_head_copy_counts_as_failed_but_not_in_history(self):
        q, _ = self._qso("head")
        q.qso_eval, q.quiz_ready = "head", True
        with mock.patch.object(q, "_play"):
            q.start_new()  # ohne „Prüfen“ weiter
        last = db.results()[-1]
        self.assertEqual((last["mode"], last["correct"], last.get("skipped")), ("qso_head", 0, True))
        self.assertFalse(any(e["mode"] == "qso_head" for e in stats.load_history()))
        with mock.patch.object(q, "_play"):
            q.start_new()  # das neue QSO lief noch nicht zu Ende: nichts eintragen
        self.assertEqual(len(db.results()), 1)

    def test_mode_is_fixed_at_start(self):
        q, qso_mode = self._qso("quiz")
        q.qso_eval = "quiz"
        q.eval_var.set(qso_mode.EVAL_LABELS["head"])  # nach dem Hören umgeschaltet
        q._on_quiz_checked(5, 8)
        self.assertEqual(db.results()[-1]["mode"], "qso_quiz")

    def test_replays_before_check_are_logged_and_freeze_tempo(self):
        q, _ = self._qso("quiz")
        q.adaptive_var.set(True)
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(False)
        q.replays = 2
        q._on_quiz_checked(8, 8)
        self.assertIn("2× „Nochmal“", q.status_var.get())
        self.assertEqual(self.app.wpm_var.get(), 20)
        self.assertEqual(db.results()[-1]["replays"], 2)

    def test_pileups_only_for_contests_and_short_default(self):
        from morsetrainer.core import qso_text
        q = self.mode("QSO")
        self.assertEqual(q.length_var.get(), "Kurz")
        self.assertEqual(str(q.pileup_combo["state"]), "disabled")  # normales QSO
        q.kind_var.set(qso_text.QSO_TYPES["cqww"])
        self.assertEqual(str(q.pileup_combo["state"]), "readonly")
        self.assertEqual(q.pileup_var.get(), "aus")
        self.assertIn("Min.", q.length_hint_var.get())


class QsoTempoTest(AppTestCase):
    def test_automatic_tempo_changes_pauses_first(self):
        q = self.mode("QSO")
        q.adaptive_var.set(True)
        self.app.wpm_var.set(20)
        self.app.farnsworth_wpm_var.set(10)
        self.app.farnsworth_enabled_var.set(True)
        self.assertIn("20/10 WPM → 20/11 WPM", q._adapt_speed(1.0))
        self.assertEqual(self.app.wpm_var.get(), 20)
        self.assertIn("→ 20/10 WPM", q._adapt_speed(0.3))


class ContestBustedTest(AppTestCase):
    def _contest_with_caller(self):
        from morsetrainer.core import qso_text
        self.app.station_call_var.set("DL0ABC")  # zieht ins Contest-Feld mit
        r = self.mode("Contest")
        patches = [mock.patch.object(run_mode.Mixer, "start"), mock.patch.object(run_mode.Mixer, "stop")]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        r.start()
        caller = run_mode.Caller(call="DL1ABC", exchange="14", exchange_kind=qso_text.TEXT, station=1,
                                 wpm=20, freq=600.0, strength=1.0, patience=3)
        r.callers = [caller]
        return r, caller

    def test_near_call_gets_answer_and_correction_with_tu_logs_ok(self):
        r, caller = self._contest_with_caller()
        with mock.patch.object(run_mode.random, "random", return_value=0.0):
            r._react("exchange", "DL1ABD", r.msg_id)
        self.assertEqual(caller.state, "worked")  # antwortet trotz falschem Call
        r.exchange_sent_to = "DL1ABD"
        r.call_var.set("DL1ABC")  # Hörfehler bemerkt und korrigiert
        r.exch_var.set("14")
        r._on_enter()
        self.assertEqual(r.log[-1]["ok"], True)
        self.assertIn("DL1ABC TU", r.status_var.get())
        r.stop()
        # Erst nach der Korrektur richtig: zählt nicht fürs WPX-Diplom.
        self.assertEqual(db.results()[-1]["calls"], [])

    def test_wpx_calls_only_without_query(self):
        r, caller = self._contest_with_caller()
        second = run_mode.Caller(call="OK1XY", exchange="15", exchange_kind=caller.exchange_kind, station=2,
                                 wpm=20, freq=650.0, strength=1.0, patience=3)
        for qso, query in ((caller, False), (second, True)):
            r.callers = [qso]
            if query:
                r._react("hiscall", "OK?XY", r.msg_id)  # nachgefragt
            r._react("exchange", qso.call, r.msg_id)
            r.call_var.set(qso.call)
            r.exch_var.set(qso.exchange)
            r._log_qso()
        self.assertEqual([e["ok"] for e in r.log], [True, True])
        r.stop()
        self.assertEqual(db.results()[-1]["calls"], ["DL1ABC"])

    def test_unnoticed_busted_call_is_marked(self):
        r, caller = self._contest_with_caller()
        with mock.patch.object(run_mode.random, "random", return_value=0.0):
            r._react("exchange", "DL1ABD", r.msg_id)
        r.exchange_sent_to = "DL1ABD"
        r.call_var.set("DL1ABD")
        r.exch_var.set("14")
        r._on_enter()
        self.assertEqual(r.log[-1]["ok"], False)
        item = r.log_tree.get_children()[0]
        self.assertIn("Busted", r.log_tree.item(item)["values"][3])
        r.stop()

    def test_partial_call_sends_only_call_and_matches_wildcards(self):
        self.assertEqual(run_mode.call_matches("DL1?", "DL1ABC"), "similar")
        self.assertEqual(run_mode.call_matches("DL?ABC", "DL1ABC"), "similar")
        self.assertEqual(run_mode.call_matches("DK?ABC", "DL1ABC"), "")
        r, caller = self._contest_with_caller()
        r.call_var.set("DL1?")
        r._on_enter()
        self.assertIn("Sende: DL1?", r.status_var.get())
        self.assertNotIn("5NN", r.status_var.get())
        r.stop()

    def test_nil_names_caller_and_summary_counts_errors(self):
        r, caller = self._contest_with_caller()
        r.call_var.set("DL1ABD")
        r.exch_var.set("14")
        r._log_qso()  # niemand hat einen Austausch gegeben
        item = r.log_tree.get_children()[0]
        self.assertIn("ähnlich ruft: DL1ABC", r.log_tree.item(item)["values"][3])
        caller.state = "done"  # schon geloggt: nicht mehr nennen
        r.call_var.set("DL1ABD")
        r.exch_var.set("14")
        r._log_qso()
        item = r.log_tree.get_children()[0]
        self.assertNotIn("DL1ABC", r.log_tree.item(item)["values"][3])
        r.stop()
        self.assertIn("2 NIL", r.status_var.get())

    def test_f10_starts_and_stops(self):
        r = self.mode("Contest")
        with mock.patch.object(r, "toggle_running") as toggle:
            r.on_function_key("F10")
            toggle.assert_called_once()

    def test_new_call_before_logging_is_not_a_correction(self):
        r, caller = self._contest_with_caller()
        r.exchange_sent_to = "DL1ABC"
        r.exch_var.set("14")
        r.call_var.set("K3LR")  # nächste Station, nicht geloggt
        r._on_enter()
        self.assertEqual(r.log, [])
        self.assertIn("K3LR 5NN", r.status_var.get())
        r.stop()


class StationTest(AppTestCase):
    def test_contest_and_network_follow_until_changed(self):
        contest, network = self.mode("Contest").my_call_var, self.mode("Netzwerk").name_var
        self.assertEqual(contest.get(), "")  # kein fremdes Rufzeichen als Vorgabe
        self.app.station_call_var.set("dl0abc")
        self.assertEqual((contest.get(), network.get()), ("DL0ABC", "DL0ABC"))  # ohne Name: Rufzeichen
        self.app.station_name_var.set("Erika")
        self.assertEqual(network.get(), "Erika")
        contest.set("DA0HQ")  # eigenes Contest-Rufzeichen bleibt
        self.app.station_call_var.set("DL0XYZ")
        self.assertEqual((contest.get(), network.get()), ("DA0HQ", "Erika"))

    def test_contest_hints_without_own_call(self):
        r = self.mode("Contest")
        self.assertIn("ausgedacht", r.call_hint_var.get())
        self.app.station_call_var.set("DL0ABC")
        self.assertEqual(r.call_hint_var.get(), "")

    def test_old_settings_are_taken_over_except_old_default(self):
        for saved_call, central, contest in (("DL4YM", "", ""), ("DK1AB", "DK1AB", "DK1AB")):
            self.app.saved_state = {"modes": {}}
            self.mode("Contest").my_call_var.set(saved_call)
            self.mode("Netzwerk").name_var.set("Erika")
            self.app.station_call_var.set("")
            self.app._follow_station()
            self.assertEqual((self.app.station_call_var.get(), self.mode("Contest").my_call_var.get(),
                              self.app.station_name_var.get()), (central, contest, "Erika"))


class ContestLogTest(AppTestCase):
    def test_tu_without_call_or_exchange_does_not_log(self):
        self.app.station_call_var.set("DL0ABC")
        r = self.mode("Contest")
        with mock.patch.object(run_mode.Mixer, "start"), mock.patch.object(run_mode.Mixer, "stop"):
            r.start()
            self.assertTrue(r.running)
            r.on_function_key("F3")
            r.call_var.set("DL1ABC")
            r.on_function_key("F3")
            self.assertEqual(r.log, [])
            self.assertIn("nicht geloggt", r.status_var.get())
            r.stop()


if __name__ == "__main__":
    unittest.main()


class HelpWindowTest(AppTestCase):
    def test_markdown_blocks(self):
        from morsetrainer.widgets import help_window
        blocks = help_window.parse("# Titel\n\nEin **fetter**\nAbsatz.\n\n- Punkt eins\n  weiter\n"
                                   "| A | B |\n|---|---|\n| **X** | y |\n```\ncode\n```\n")
        self.assertEqual(blocks[0], ("h1", "Titel"))
        self.assertIn(("p", "Ein **fetter** Absatz."), blocks)
        self.assertIn(("li", "• Punkt eins weiter"), blocks)
        self.assertIn(("row", "**X**\ty"), blocks)
        self.assertIn(("code", "code"), blocks)
        images = help_window.parse('Text\n\n![Bild](a.png)\n\n<img src="b.png" width="640" alt="x">\n')
        self.assertEqual([b for b in images if b[0] != "gap"], [("p", "Text")])

    def test_help_shows_changelog_and_readme(self):
        from morsetrainer.widgets import help_window
        help_window.HelpWindow.show(self.root)
        window = help_window.HelpWindow._open
        changelog = window.texts["CHANGELOG.md"].get("1.0", "end")
        readme = window.texts["docs/Anleitung.md"].get("1.0", "end")
        self.assertIn(app_module.__version__, changelog)  # aktuelle Version steht drin
        self.assertIn("Die Reiter", readme)
        self.assertNotIn("**", readme)
        self.assertNotIn("<img", readme)
        help_window.HelpWindow.show(self.root)  # zweiter Aufruf: dasselbe Fenster
        self.assertIs(help_window.HelpWindow._open, window)


    def test_search_with_ctrl_f(self):
        from morsetrainer.widgets import help_window
        help_window.HelpWindow.show(self.root)
        window = help_window.HelpWindow._open
        try:
            window.notebook.select(1)  # Anleitung
            self.root.update()
            self.assertTrue(window.top.bind("<Control-f>"))
            window.focus_search()
            window.search_var.set("KOCH-LEKTION")  # Groß-/Kleinschreibung egal
            text = window.texts["docs/Anleitung.md"]
            total = len(window.matches)
            self.assertGreater(total, 1)
            self.assertEqual(len(text.tag_ranges("match")), 2 * total)
            first = text.index("match_current.first")
            self.assertEqual(text.get(first, f"{first}+12c").lower(), "koch-lektion")
            self.assertEqual(window.search_info_var.get(), f"Treffer 1 von {total}")
            window.find(1)
            self.assertNotEqual(text.index("match_current.first"), first)
            window.find(-1)
            self.assertEqual(text.index("match_current.first"), first)
            window.search_var.set("gibtesnichtxyz")
            self.assertEqual(window.search_info_var.get(), "nicht gefunden")
            self.assertEqual(text.tag_ranges("match"), ())
            # Anderes Wort für dasselbe: „Hotkey“ findet „Tastenkürzel“.
            window.search_var.set("Hotkey")
            self.assertTrue(window.matches)
            self.assertTrue(window.search_info_var.get().startswith("„Hotkey“ nicht gefunden, dafür"))
            first = text.index("match_current.first")
            self.assertIn("kürzel", text.get(first, "match_current.last").lower())
            # Umlaut-Schreibweise und Bindestrich egal.
            window.search_var.set("Tastenkuerzel")
            self.assertEqual(text.get("match_current.first", "match_current.last"), "Tastenkürzel")
            window.search_var.set("Koch Lektion")
            self.assertGreater(len(window.matches), 1)
            # Nur im anderen Reiter: sagt, wo.
            window.search_var.set("Intern:")
            self.assertRegex(window.search_info_var.get(), r"^nicht gefunden – im Reiter Änderungen: \d+ Treffer$")
            # Esc im Suchfeld mit Text leert die Suche, das Fenster bleibt.
            window._escape(type("E", (), {"widget": window.search_entry})())
            self.assertEqual(window.search_var.get(), "")
            self.assertTrue(window.top.winfo_exists())
        finally:
            window.top.destroy()


class DecimalTest(AppTestCase):
    def test_statistics_use_the_decimal_comma(self):
        panel = self.mode("Einzelzeichen").stats_panel
        panel.refresh({"correct": 9, "total": 10, "accuracy_pct": 90.0, "avg_effective_wpm": 8.25},
                      [("K", 9, 1, 10, 2.27, 5.9, "")])
        self.assertEqual(panel.speed_var.get(), "Ø effektive Geschwindigkeit: 8,2 WPM")
        row = panel.char_tree.item(panel.char_tree.get_children()[0])["values"]
        self.assertEqual([str(v) for v in row[3:5]], ["2,27", "5,9"])

    def test_progress_text_uses_the_decimal_comma(self):
        from datetime import datetime
        panel = self.app.progress_panel
        history = [{"time": datetime(2026, 9, 25, 10), "mode": "single", "accuracy_pct": 97.6, "wpm": 15,
                    "total": 50},
                   {"time": datetime(2026, 10, 3, 10), "mode": "single", "accuracy_pct": 94.7, "wpm": 20,
                    "total": 50}]
        with mock.patch.object(stats, "load_history", return_value=history):
            panel.refresh()
        self.assertIn("Trefferquote 97,6 % → 94,7 %", panel.info_var.get())
        row = panel.table.item(panel.table.get_children()[0])["values"]
        self.assertEqual(str(row[1]), "94,7 %")


class ContestNamesTest(AppTestCase):
    def test_contest_tab_shows_names_without_prefix(self):
        from morsetrainer.core import qso_text
        contest = self.mode("Contest")
        self.assertEqual(set(qso_text.CONTEST_NAMES), set(qso_text.QSO_TYPES) - {qso_text.RAGCHEW})
        self.assertEqual(contest.kind_combo.get(), "CQ WW (Zone)")
        self.assertNotIn("Contest:", " ".join(contest.kind_combo.cget("values")))
        contest.kind_combo.set("WAG (DOK)")
        self.assertEqual(contest.settings()["kind"], "wag")
        contest.restore_settings({"kind": "iaru"})
        self.assertEqual(contest.kind_combo.get(), "IARU HF (ITU-Zone/HQ)")
        contest.restore_settings({"kind": "ragchew"})  # kein Contest: bleibt
        self.assertEqual(contest.settings()["kind"], "iaru")


class LayoutTest(AppTestCase):
    def test_group_length_row_only_while_it_has_text(self):
        groups = self.mode("Gruppen")
        self.assertEqual(groups.length_info_label.winfo_manager(), "")  # keine Leerzeile
        groups.length_info_var.set("Aktuelle Gruppenlänge: 3")
        self.assertEqual(groups.length_info_label.winfo_manager(), "pack")
        groups.length_info_var.set("")
        self.assertEqual(groups.length_info_label.winfo_manager(), "")

    def test_history_headings_name_their_length(self):
        from morsetrainer.modes import sequence_mode
        texts = []

        def collect(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TLabelframe":
                    texts.append(str(child.cget("text")))
                collect(child)
        collect(self.root)
        self.assertIn(f"Verlauf (letzte {single_mode.HISTORY_LEN})", texts)
        self.assertIn(f"Verlauf (letzte {sequence_mode.HISTORY_LEN})", texts)
        self.assertNotIn("Verlauf", texts)


class ThemeTest(AppTestCase):
    def test_choice_boxes_stay_readable_with_focus(self):
        # clam färbte die Schrift fokussierter Klapplisten weiß auf weißem Feld
        # (leeres Contest-Feld beim Öffnen des Reiters).
        style = ttk.Style()
        for state in (["readonly"], ["readonly", "focus"], ["readonly", "focus", "hover"]):
            foreground = style.lookup("TCombobox", "foreground", state)
            self.assertNotEqual(foreground, style.lookup("TCombobox", "fieldbackground", state), state)
            self.assertEqual(foreground, theme.TEXT, state)
        self.assertEqual(style.lookup("TCombobox", "foreground", ["disabled", "readonly"]), theme.DISABLED)


class IconTest(AppTestCase):
    def test_no_input_method_under_x11(self):
        # ibus machte den Aufbau des Hauptfensters zehnmal langsamer.
        if self.root.tk.call("tk", "windowingsystem") != "x11":
            self.skipTest("nur X11")
        self.assertEqual(str(self.root.tk.call("tk", "useinputmethods")), "0")

    def test_window_icon_is_set(self):
        self.assertEqual([icon.width() for icon in self.app.icons], list(app_module.ICON_SIZES))
