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
from morsetrainer.core import stats
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


class QsoRevealTest(AppTestCase):
    def test_text_hidden_until_quiz_checked(self):
        q = self.mode("QSO")
        q.qso, q.running, q.quiz_ready, q.quiz_checked = object(), False, True, False
        q._update_reveal_button()
        self.assertEqual(str(q.reveal_button["state"]), "disabled")
        q.quiz_checked = True
        q._update_reveal_button()
        self.assertEqual(str(q.reveal_button["state"]), "normal")


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
