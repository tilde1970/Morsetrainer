"""Tests für die Auswertung in den Trainingsreitern mit echtem Tk-Fenster,
aber ohne Ton; ohne Anzeige (kein $DISPLAY) werden sie übersprungen. Die
Wiedergabe wird übersprungen: die Tests setzen den Zustand nach dem Ton
direkt und rufen die Auswertung auf."""
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import app as app_module
from morsetrainer.core import koch, stats
from morsetrainer.modes import continuous_mode, run_mode, single_mode
from morsetrainer.modes import sequence_mode as sq


class AppTestCase(unittest.TestCase):
    """Hauptfenster mit allen Reitern, Daten in einem Temp-Verzeichnis."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
            mock.patch.object(stats, "ALL_TIME_FILE", directory / "all_time.json"),
            mock.patch.object(stats, "RESULTS_FILE", directory / "results.jsonl"),
            mock.patch.object(stats, "RESET_FILE", directory / "reset.json"),
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

    def test_replayed_slow_or_overtyped_do_not_count(self):
        self._start()
        self._answer("KMU", "KMU", replayed=True)
        self._answer("KMU", "KMU", seconds_after_tone=sq.answer_limit(3) + 1)
        self._answer("KMKMK", "KMKMKMKMKM")
        self.assertEqual(self.group.first_try_correct, 0)
        self.assertEqual(self.group.first_try_total, 3 + 3 + 5)

    def test_unsure_answers_count_as_slow(self):
        self._start(sq.MEMORIZE)
        self._answer("KMU", "KMU", replayed=True)
        self._answer("KMU", "KMM", seconds_after_tone=sq.answer_limit(3) + 1)
        rounds = self.group.session_stats.rounds
        self.assertEqual([r["correct"] for r in rounds], [True] * 5 + [False])  # Quote ehrlich
        self.assertTrue(all(r["latency_s"] == stats.LATENCY_CAP_S for r in rounds if r["correct"]))

    def test_unsure_latency_is_twice_the_usual(self):
        with mock.patch.object(sq.CharPicker, "median_latency", lambda self: 0.8):
            self._start(sq.MEMORIZE)
        self._answer("KMU", "KMU", replayed=True)
        self.assertEqual({r["latency_s"] for r in self.group.session_stats.rounds}, {1.6})

    def test_second_attempt_hides_solution_and_is_not_recorded(self):
        self._start()
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
        self._start()
        self.group.give_up_var.set(1)
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

    def test_groups_hint_needs_limit_whole_session(self):
        s = self.single
        s.icr_var.set(False)
        s._on_icr_toggle()
        s.stop()
        self.assertIsNone(s.groups_result)


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
        c._finalize_session(stopped_at=now)
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


class ContinuousGroupingTest(AppTestCase):
    def test_word_gap_after_each_group(self):
        import contextlib
        c = self.mode("Kontinuierlich")

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        c.picker = single_mode.CharPicker("KM", False)
        c.wpm, c.freq, c.fw, c.group_len = 20, 600, None, 3
        c.sent_log, c.running, c.deadline = [], True, None
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
        self.assertEqual(list(stats._read_jsonl(stats.RESULTS_FILE))[-1]["mode"], "qso_head")

    def test_mode_is_fixed_at_start(self):
        q, qso_mode = self._qso("quiz")
        q.qso_eval = "quiz"
        q.eval_var.set(qso_mode.EVAL_LABELS["head"])  # nach dem Hören umgeschaltet
        q._on_quiz_checked(5, 8)
        self.assertEqual(list(stats._read_jsonl(stats.RESULTS_FILE))[-1]["mode"], "qso_quiz")

    def test_replays_before_check_are_logged_and_freeze_tempo(self):
        q, _ = self._qso("quiz")
        q.adaptive_var.set(True)
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(False)
        q.replays = 2
        q._on_quiz_checked(8, 8)
        self.assertIn("2× „Nochmal“", q.status_var.get())
        self.assertEqual(self.app.wpm_var.get(), 20)
        self.assertEqual(list(stats._read_jsonl(stats.RESULTS_FILE))[-1]["replays"], 2)

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


class ContestLogTest(AppTestCase):
    def test_tu_without_call_or_exchange_does_not_log(self):
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
