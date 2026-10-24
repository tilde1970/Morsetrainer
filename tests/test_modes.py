"""Tests für die Auswertung in den Trainingsreitern mit echtem Tk-Fenster,
aber ohne Ton; ohne Anzeige (kein $DISPLAY) werden sie übersprungen. Die
Wiedergabe wird übersprungen: die Tests setzen den Zustand nach dem Ton
direkt und rufen die Auswertung auf."""
import gc
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
from morsetrainer.core import audio, db, koch, stats
from morsetrainer.modes import continuous_mode, run_mode, single_mode
from morsetrainer.modes import sequence_mode as sq
from morsetrainer.widgets import announcer, theme


class AppTestCase(unittest.TestCase):
    """Hauptfenster mit allen Reitern, Daten in einem Temp-Verzeichnis."""

    # Aufgeräumt wird über addCleanup, gleich nach dem Anlegen: Das läuft auch,
    # wenn setUp mittendrin scheitert oder ein tearDown einen Fehler wirft.
    # Unterklassen dürfen self.patches noch Patches anhängen.

    def setUp(self):
        gc.collect()  # Reste früherer Tests hier im Hauptthread einsammeln
        audio._tone_until = 0.0  # kein „laufender“ Ton aus dem vorigen Test, auf den Ansagen warteten
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
            mock.patch.object(app_module, "WINDOW_STATE_FILE", directory / "window_state.json"),
            # Jeder Test ist ein „erster Start“; die Begrüßung prüft FirstStartTest.
            mock.patch.object(app_module.MorseTrainerApp, "_greet_first_start", lambda self: None),
        ]
        self.addCleanup(tests.stop_patches, self.patches)
        for patch in self.patches:
            patch.start()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.addCleanup(self._release)
        self.root.withdraw()
        self.app = app_module.MorseTrainerApp(self.root)
        self.app.charset_var.set("KMUR")

    def mode(self, title):
        return self.app.modes[self.app.mode_titles.index(title)]

    def _release(self):
        from morsetrainer.widgets import announcer
        announcer._instance = None  # nicht über ein zerstörtes Fenster weitersprechen
        if hasattr(self, "app"):
            for mode in self.app.modes:
                mode.running = False
            mode = None  # hielte sonst den Reiter samt App über das Einsammeln hinaus fest
        tests.release_root(self.root, owner=self)



class HeaderStateTest(AppTestCase):
    """Die Kopfleiste kommt nach dem Neustart so, wie sie beim Beenden war."""
    def setUp(self):
        patch = mock.patch.object(app_module.MorseTrainerApp, "_load_state",
                                  lambda app: {"shared": {"font_scale": 200}, "header_open": True})
        patch.start()
        self.addCleanup(patch.stop)
        # Ein hoher Bildschirm: sonst klappt der Kompaktmodus die Leiste wieder zu.
        tall = mock.patch.object(tk.Misc, "winfo_screenheight", lambda widget: 4000)
        tall.start()
        self.addCleanup(tall.stop)
        super().setUp()

    def test_open_header_is_remembered_at_200_percent(self):
        import json
        self.assertEqual(theme.scale(), 200)
        self.assertTrue(self.app.header_open)  # sonst bei 200 % zugeklappt
        self.assertEqual(self.app.header.winfo_manager(), "pack")
        self.assertEqual(self.app.header_row.winfo_manager(), "pack")  # Knopf zum Zuklappen da
        self.app._toggle_header()
        self.app._save_state()
        state = json.loads(app_module.WINDOW_STATE_FILE.read_text(encoding="utf-8"))
        self.assertIs(state["header_open"], False)
        self.app.font_scale_var.set(100)

    def test_open_header_stays_closed_when_the_screen_is_too_small(self):
        # Auf kleinem Bildschirm (hier gespielt) bliebe vom Reiter sonst nichts sichtbar.
        with mock.patch.object(self.app.root, "winfo_screenheight", return_value=600):
            self.assertFalse(self.app._header_fits_screen())
        self.assertTrue(self.app._header_fits_screen())  # Testbildschirm 1000 px hoch


class CompactByHeightTest(AppTestCase):
    """Der Kompaktmodus hängt an der Bildschirmhöhe, nicht nur an der Schriftgröße."""

    def test_small_screen_compacts_below_200_percent(self):
        app = self.app
        app.font_scale_var.set(100)
        app._update_compact()
        self.assertFalse(app.compact)
        self.assertEqual(app.header.winfo_manager(), "pack")
        with mock.patch.object(app.root, "winfo_screenheight", return_value=600):
            app._update_compact()
        self.assertTrue(app.compact)
        self.assertEqual(app.header.winfo_manager(), "")  # zugeklappt
        self.assertEqual(app.header_row.winfo_manager(), "pack")  # Knopf zum Aufklappen
        app._update_compact()  # wieder der normale Bildschirm
        self.assertFalse(app.compact)
        self.assertEqual(app.header.winfo_manager(), "pack")
        self.assertEqual(app.header_row.winfo_manager(), "")


    def test_open_header_is_closed_again_when_the_window_would_not_fit(self):
        app = self.app
        app.font_scale_var.set(100)
        with mock.patch.object(app.root, "winfo_screenheight", return_value=768):
            app._update_compact(header_open=True)  # gemerkt offen, Leiste allein klein genug
            self.assertTrue(app.compact)
            self.assertFalse(app.header_open)
        app._update_compact()

    def test_initial_geometry_is_capped_to_the_screen(self):
        app = self.app
        with mock.patch.object(app.root, "winfo_screenheight", return_value=600), \
                mock.patch.object(app.root, "winfo_screenwidth", return_value=1024):
            app.saved_state = {}
            self.assertEqual(app._initial_geometry(), "720x520")
            app.saved_state = {"geometry": "1600x1000+10+10"}
            with mock.patch.object(app, "_geometry_fits_screen", return_value=True):
                self.assertEqual(app._initial_geometry(), "984x520+10+10")

    def test_saved_height_is_raised_to_a_minimum(self):
        app = self.app
        with mock.patch.object(app.root, "winfo_screenheight", return_value=1080), \
                mock.patch.object(app.root, "winfo_screenwidth", return_value=1920):
            app.saved_state = {"geometry": "300x1+10+10"}
            with mock.patch.object(app, "_geometry_fits_screen", return_value=True):
                self.assertEqual(app._initial_geometry(), "720x400+10+10")

    def test_tempo_and_pitch_stay_in_range_whatever_is_typed(self):
        app = self.app
        for typed, wpm in ((0, 5), (-5, 5), (99, 40), (18, 18)):
            app.wpm_var.set(typed)
            self.assertEqual(app.wpm_var.get(), wpm)
        app.freq_var.set(5)
        self.assertEqual(app.freq_var.get(), 300)
        app.farnsworth_wpm_var.set(0)
        self.assertEqual(app.farnsworth_wpm_var.get(), 3)
        app.wpm_var.set(koch_default := 12)
        self.assertEqual(koch_default, app.wpm_var.get())

    def test_zoom_into_compact_mode_says_the_header_is_collapsed(self):
        app = self.app
        app.font_scale_var.set(100)
        app.compact_note = ""
        with mock.patch.object(app.root, "winfo_screenheight", return_value=768):
            app.font_scale_var.set(125)
        self.assertEqual(app.compact_note, "Kopfleiste zugeklappt.")
        app.font_scale_var.set(100)


class ReleaseTest(unittest.TestCase):
    """Nach dem Test ist das Hauptfenster samt App im Hauptthread eingesammelt.
    Bliebe es liegen, sammelte es irgendwann ein Netzwerk- oder Audio-Thread
    ein: je Tk-Objekt 1 s Warten auf die mainloop, dann Tcl_AsyncDelete."""

    def test_nothing_of_the_app_is_left_for_other_threads(self):
        from morsetrainer.widgets import announcer
        gc.collect()
        before = sum(isinstance(obj, tk.Variable) for obj in gc.get_objects())
        names_before = len(announcer._names)
        case = AppTestCase("setUp")
        case.setUp()
        try:
            self.assertGreater(len(announcer._names), names_before)
        finally:
            case.doCleanups()
        self.assertEqual(sum(isinstance(obj, tk.Variable) for obj in gc.get_objects()), before)
        self.assertEqual(len(announcer._names), names_before)
        thread = threading.Thread(target=gc.collect, daemon=True)
        start = time.monotonic()
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertLess(time.monotonic() - start, 0.5)


class CyclicGarbageTest(AppTestCase):
    """Im Programm dürfen Tk-Objekte nicht im zyklischen Müll landen: Den
    sammelt die Garbage Collection ein, wo sie gerade läuft, etwa im
    Audio-Rückruf; der wartete dann auf die mainloop, und schließt das
    Programm zugleich den Tonstrom, hängt es."""

    def test_tabs_and_windows_leave_no_tk_objects_behind(self):
        import tkinter.font
        from morsetrainer.widgets import help_window
        gc.collect()
        if gc.isenabled():
            gc.disable()
            self.addCleanup(gc.enable)
        for tab in self.app.notebook.tabs():
            self.app.notebook.select(tab)
            self.root.update()
        self.app.open_settings()
        self.root.update()
        self.app.close_settings()
        self.app.band_settings.open_window()
        self.root.update()
        self.app.band_settings.close_window()
        help_window.HelpWindow.show(self.root)
        self.root.update()
        help_window.HelpWindow._open.top.destroy()
        self.root.update()
        gc.set_debug(gc.DEBUG_SAVEALL)
        try:
            gc.collect()
            found = sorted({type(obj).__name__ for obj in gc.garbage
                            if isinstance(obj, (tk.Variable, tk.Image, tkinter.font.Font))})
        finally:
            gc.set_debug(0)
            gc.garbage.clear()
        self.assertEqual(found, [])


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


class PhraseTest(AppTestCase):
    """Wendungen im Reiter Wörter: mit Wortabstand gesendet, ohne Leerzeichen
    getippt, Zeitfenster zweigeteilt."""

    def setUp(self):
        super().setUp()
        self.w = self.mode("Wörter")
        self.w.content_var.set("Wendungen")
        self.app.charset_var.set(koch.lesson_charset(41))
        self.app.farnsworth_enabled_var.set(False)

    def _answer(self, phrase, typed, first_key_after, typing_s):
        w = self.w
        w.start()
        w.current_sequence, w.attempts, w.replayed, w.repeat_pending = phrase, 0, False, False
        w.voice = (20, 600)
        now = time.time()
        end = now - first_key_after - typing_s
        n = len(phrase.replace(" ", ""))
        w.tone_starts, w.tone_ends = [end - 1] * n, [end] * n
        w.input_var.set(typed)
        w.key_times = [end + first_key_after] * len(typed)
        w.enter_time, w.waiting_for_input = None, True
        w.on_submit()

    def test_too_few_phrases_points_to_words(self):
        self.app.charset_var.set(koch.lesson_charset(10))
        self.assertFalse(self.w._validate_settings())
        self.assertIn("Wendungen", self.w.status_var.get())
        self.assertIn("Übe bis dahin mit Wörtern.", self.w.status_var.get())
        self.app.charset_var.set(koch.lesson_charset(41))
        self.assertTrue(self.w._validate_settings())
        from morsetrainer.core import words
        self.assertTrue(set(self.w.words) <= set(words.PHRASES))

    def test_played_with_word_gaps_and_one_timing_per_character(self):
        w = self.w
        w.start()
        w.current_sequence, w.voice = "TNX FER CALL", (20, 600)
        played = []
        with mock.patch.object(w, "_play", lambda samples: played.append(samples) or True), \
                mock.patch.object(w, "_later"):
            w.play_current()
        self.assertEqual(len(w.tone_ends), 10)
        gap = w.tone_starts[3] - w.tone_ends[2]  # zwischen TNX und FER
        normal = w.tone_starts[2] - w.tone_ends[1]
        self.assertAlmostEqual(gap - normal, sq.word_gap_extra_seconds(20, None), places=3)

    def test_typed_without_spaces_is_right(self):
        self._answer("TNX FER CALL", "TNXFERCALL", first_key_after=1.0, typing_s=5.0)
        self.assertIn("Richtig: TNX FER CALL", self.w.feedback_var.get())
        self.assertNotIn("zu langsam", self.w.feedback_var.get())
        self.assertIn("danke für den Anruf", self.w.feedback_var.get())

    def test_late_first_key_is_too_slow(self):
        self._answer("TNX FER CALL", "TNXFERCALL", first_key_after=sq.FIRST_KEY_S + 0.5, typing_s=1.0)
        self.assertIn("zu langsam", self.w.feedback_var.get())

    def test_typing_has_its_own_window(self):
        n = 10
        self._answer("TNX FER CALL", "TNXFERCALL", first_key_after=0.5, typing_s=sq.ANSWER_PER_CHAR_S * n + 1)
        self.assertIn("zu langsam", self.w.feedback_var.get())
        self.w.stop()
        self._answer("TNX FER CALL", "TNXFERCALL", first_key_after=1.5, typing_s=sq.ANSWER_PER_CHAR_S * n - 0.5)
        self.assertNotIn("zu langsam", self.w.feedback_var.get())

    def test_status_names_both_windows(self):
        w = self.w
        w.start()
        w.current_sequence, w.attempts, w.replayed, w.submit_pending = "TNX FER CALL", 0, False, False
        w.on_playback_done()
        self.assertIn("in 2 s anfangen, dann 6 s zum Tippen", w.status_var.get())

    def test_saved_and_daily_practice_uses_words(self):
        self.assertEqual(self.w.settings()["content"], "phrases")
        self.w.content_var.set("Abkürzungen")
        self.w.restore_settings({"content": "phrases", "memorize_default": True})
        self.assertEqual(self.w.content_var.get(), "Wendungen")
        from morsetrainer import daily_runner
        self.w.daily_configure(4, **daily_runner.MODE_SETTINGS["word"])
        self.assertEqual(self.w.content_var.get(), "Abkürzungen")
        self.w.daily_release()
        self.assertEqual(self.w.content_var.get(), "Wendungen")

    def test_mixed_brings_about_a_third_phrases(self):
        from morsetrainer.core import words
        from morsetrainer.modes import word_mode
        w = self.w
        w.content_var.set("gemischt")
        self.assertTrue(w._validate_settings())
        w._setup_pickers(False)
        with mock.patch.object(word_mode.random, "random", side_effect=[0.1, 0.9] * 30), \
                mock.patch.object(w.phrase_picker, "pick", wraps=w.phrase_picker.pick) as phrase_pick:
            drawn = [w._generate_sequence() for _ in range(60)]
        self.assertEqual(phrase_pick.call_count, 30)  # bei random() < 1/3 eine Wendung
        phrase = next(d for d in drawn if " " in d)
        w.current_sequence = phrase
        self.assertEqual(w.first_key_limit, sq.FIRST_KEY_S)
        self.assertEqual(w._explain(phrase), words.PHRASES[phrase])
        w.current_sequence = "TNX"
        self.assertIsNone(w.first_key_limit)  # ein Wort: ein Fenster wie bisher
        self.assertEqual(w.settings()["content"], "mixed")

    def test_mixed_without_enough_phrases_brings_words(self):
        w = self.w
        w.content_var.set("gemischt")
        self.app.charset_var.set(koch.lesson_charset(20))
        self.assertTrue(w._validate_settings())
        w._setup_pickers(False)
        self.assertIsNone(w.phrase_picker)
        self.assertIn("reichen die Zeichen noch nicht", w.count_var.get())

    def test_plain_words_are_their_own_list(self):
        from morsetrainer.core import words
        from morsetrainer.modes import word_mode
        w = self.w
        w.content_var.set("Klartext")
        self.assertTrue(w._validate_settings())
        self.assertEqual(set(w.words), set(words.words_for_charset(w.charset, words.PLAIN_WORDS)))
        self.assertIn("WEATHER", w.words)
        self.assertNotIn("TNX", w.words)
        self.assertEqual(w._explain("KEY"), "")  # ausgeschrieben, ohne Bedeutung
        self.assertIn(f"von {len(words.PLAIN_WORDS)} Wörtern", w.count_var.get())
        self.assertEqual(w.settings()["content"], "plain")
        w.restore_settings({"content": "words", "memorize_default": True})
        self.assertEqual(w.content_var.get(), "Abkürzungen")
        w.content_var.set("Klartext")
        self.app.charset_var.set(koch.lesson_charset(9))  # 27 Wörter: zu wenige für Klartext
        with mock.patch.object(word_mode.announcer, "say") as say:
            self.assertFalse(w._validate_settings())
        self.assertIn("ab Koch-Lektion 10", w.status_var.get())
        self.assertIn("Nur 27 Wörter", say.call_args.args[0])  # angesagt, nicht nur angezeigt
        w.content_var.set("Abkürzungen")
        self.assertTrue(w._validate_settings())  # Abkürzungen reichen dort schon
        w.content_var.set("Wendungen")
        with mock.patch.object(word_mode.announcer, "say") as say:
            self.assertFalse(w._validate_settings())
        self.assertIn("Wendungen mit diesen Zeichen", say.call_args.args[0])

    def test_daily_word_outro_can_be_mixed(self):
        from morsetrainer import daily_runner
        self.w.content_var.set("Abkürzungen")
        self.w.daily_configure(2, **{**daily_runner.MODE_SETTINGS["word"], "content": "mixed"})
        self.assertEqual(self.w.content_var.get(), "gemischt")
        self.w.daily_release()
        self.assertEqual(self.w.content_var.get(), "Abkürzungen")

    def test_weighted_picker_handles_spaces(self):
        from morsetrainer.core import words
        from morsetrainer.core.weighting import CharPicker
        charset = koch.lesson_charset(41)
        picker = words.WordPicker(words.phrases_for_charset(charset), CharPicker(charset, True, None))
        self.assertIn(picker.pick(), words.PHRASES)


class CallsignTest(AppTestCase):
    def test_learned_only_explains_missing_digit(self):
        calls = self.mode("Rufzeichen")
        calls.all_calls = ["DL4YM", "DK1AB"] * 40
        self.app.charset_var.set("KMURESNAPTLWI")  # noch keine Ziffer
        self.assertFalse(calls._validate_settings())
        self.assertIn("Ziffer", calls.status_var.get())
        calls.learned_var.set(False)
        self.assertTrue(calls._validate_settings())

    def test_few_real_calls_from_learned_chars_are_made_up(self):
        calls = self.mode("Rufzeichen")
        calls.all_calls = ["DL4YM", "DK1AB"] * 40
        self.app.charset_var.set("KMURESNAPTLWI4")  # erste Ziffer, aber kaum echte Rufzeichen
        self.assertIn("erfunden", calls.list_info_var.get())
        self.assertTrue(calls._validate_settings())
        self.assertEqual(calls.pool, [])
        calls._setup_pickers(weighted=False)
        self.assertTrue(set(calls._pick_base_call()) <= set("KMURESNAPTLWI4"))
        calls.prefix_var.set("DL")  # erfundene Rufzeichen hielten den Filter nicht ein
        self.assertFalse(calls._validate_settings())


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

    def test_pool_stays_fixed_during_a_run_and_catches_up_after(self):
        # Das Feld „Zeichen“ oben ist im Durchgang bedienbar; die Auswahl darf sich nicht ändern.
        g = self._start_rufz([f"DL{i}ABC" for i in range(60)] + [f"DK{i}ABC" for i in range(60)])
        self.assertEqual(len(g.pool), 120)
        g.prefix_var.set("DK")
        self.assertEqual(len(g.pool), 120)
        self.assertIn(g._generate_sequence()[:2], ("DL", "DK"))
        g.stop()
        self.assertEqual(len(g.pool), 60)

    def test_made_up_run_without_learned_only_records_no_charset(self):
        g = self.mode("Rufzeichen")
        g.all_calls = []
        g.learned_var.set(False)
        info = g._session_group_len()
        self.assertEqual((info["learned_only"], info["charset"]), (False, None))

    def test_affixes_use_the_characters_from_the_start(self):
        from unittest import mock
        from morsetrainer.modes import callsign_mode
        g = self._start_rufz([f"DL{i}ABC" for i in range(60)])
        g._run_allowed = {"K", "M"}  # beim Start gemerkt
        g.learned_var.set(True)
        self.app.charset_var.set("AB")  # später im Feld geändert
        g.affix_var.set(True)
        with mock.patch.object(callsign_mode, "add_affix", side_effect=lambda call, allowed: call) as affix:
            g._generate_sequence()
        self.assertEqual(affix.call_args.args[1], {"K", "M"})

    def test_made_up_pattern_run_records_charset(self):
        g = self.mode("Rufzeichen")
        g.all_calls = []
        g.learned_var.set(True)
        self.app.charset_var.set("KMURESNAPTLWI4")
        info = g._session_group_len()
        self.assertEqual((info["learned_only"], info["charset"]), (True, "".join(sorted("KMURESNAPTLWI4"))))

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

    def _open_answer(self, char="K"):
        s = self.single
        s.icr_var.set(True)
        s.current_char, s.voice, s.waiting_for_input, s.replayed = char, (20, 600), True, False
        s.first_hearing, s.correcting, s.answer_open = True, False, True
        s.play_start_time = time.time() - 0.5

    def test_absent_player_stops_the_run_and_the_misses_do_not_count(self):
        from morsetrainer.modes import single_mode
        s = self.single
        with mock.patch.object(s.session_stats, "record_char") as record:
            for _ in range(single_mode.MISSES_BEFORE_PAUSE):
                self._open_answer()
                s._on_timeout(s.timeout_token)
        self.assertFalse(s.running)
        record.assert_not_called()
        self.assertIn("Angehalten", s.status_var.get())

    def test_misses_count_once_someone_answers(self):
        s = self.single
        with mock.patch.object(s.session_stats, "record_char") as record:
            for _ in range(2):
                self._open_answer()
                s._on_timeout(s.timeout_token)
            record.assert_not_called()  # noch unklar, ob jemand da ist
            self._open_answer()
            self._key("K")
        self.assertEqual(record.call_count, 3)  # 2 verpasst, 1 beantwortet
        self.assertTrue(s.running)
        self.assertEqual(s.pending_misses, [])

    def test_late_announcement_does_not_disturb_the_next_run(self):
        s = self.single
        late, current = mock.Mock(), mock.Mock()
        after_old = s._in_session(late)
        s.stop()
        s.start()
        after_old()
        late.assert_not_called()
        s._in_session(current)()
        current.assert_called_once()

    def test_f11_during_time_limit_drops_the_char(self):
        s = self.single
        self._open_answer()
        limit, token = s.limit, s.timeout_token
        with mock.patch.object(s, "next_char") as next_char:
            self.app.read_status()
            self.root.update()
        next_char.assert_called_once_with()
        self.assertFalse(s.waiting_for_input)
        self.assertNotEqual(s.timeout_token, token)
        s._on_timeout(token)  # die alte Frist verfällt
        s.on_playback_done(token)  # ebenso das Tonende des verworfenen Zeichens
        self.assertFalse(s.waiting_for_input)
        self.assertEqual(s.session_stats.summary()["total"], 0)
        self.assertEqual(s.limit, limit)
        self.assertEqual(s.history, [])
        self._key("K")  # Tippen während der Ansage wird nicht mehr gewertet
        self.assertEqual(s.session_stats.summary()["total"], 0)

    def test_f11_without_time_limit_keeps_the_answer_but_not_its_time(self):
        s = self.single
        self._open_answer("K")
        s.icr_var.set(False)
        with mock.patch.object(s, "next_char") as next_char:
            self.app.read_status()
        next_char.assert_not_called()  # das Zeichen bleibt offen
        self._key("K")
        entry = s.session_stats.rounds[-1]
        self.assertTrue(entry["correct"])
        self.assertNotIn("latency_s", entry)  # die Ansage steckte in der Zeit
        self.assertNotIn(" s)", s.feedback_var.get())
        # Weder im Tempo noch in den Zeichen pro Minute, und in der Lernkartei
        # weder flüssig noch langsam (sonst schönte bzw. bestrafte F11).
        summary = s.session_stats.summary()
        self.assertEqual((summary["correct"], summary["avg_effective_wpm"], summary["cpm"]), (1, 0.0, 0.0))
        e = s.session_stats.per_char["K"]
        self.assertEqual((e["good"], e["untimed"], e["correct_effective_wpms"]), (1, 1, []))
        from morsetrainer.core import review
        self.assertEqual(review.fluent_count(e), 0)
        review_data = review.update(s.session_stats.per_char)
        self.assertNotIn("K", review_data)  # zählt dort nicht als Versuch

    def test_timeout_closes_the_answer(self):
        # Sonst verwürfe ein F11 danach das schon als verpasst gewertete Zeichen ein zweites Mal.
        s = self.single
        self._open_answer("U")
        s.running = True
        with mock.patch.object(s, "_after_error"):
            s._on_timeout(s.timeout_token)
        self.assertFalse(s.answer_open)
        with mock.patch.object(s, "next_char") as next_char:
            self.app.read_status()
        next_char.assert_not_called()

    def test_shortcuts_with_ctrl_or_alt_are_not_answers(self):
        # Sonst zählte Strg+Plus (Schrift größer) als Antwort „+“ und Strg+Komma als „,“.
        s = self.single
        self._open_answer("K")
        for keysym, char, state in (("plus", "+", 0x4), ("0", "0", 0x4), ("comma", ",", 0x4), ("1", "1", 0x8)):
            self.app._dispatch_key(type("E", (), {"keysym": keysym, "char": char, "state": state,
                                                  "widget": self.root})())
        self.assertTrue(s.answer_open)
        self.assertEqual(s.session_stats.rounds, [])
        self.app._dispatch_key(type("E", (), {"keysym": "k", "char": "k", "state": 0, "widget": self.root})())
        self.assertEqual(len(s.session_stats.rounds), 1)  # ohne Zusatztaste ist es die Antwort

    def test_altgr_keeps_typed_characters_on_windows(self):
        event = type("E", (), {"state": 0x4 | 0x20000})()
        with mock.patch.object(app_module.sys, "platform", "win32"):
            self.assertFalse(app_module._is_shortcut(event))
            self.assertTrue(app_module._is_shortcut(type("E", (), {"state": 0x4})()))
            self.assertFalse(app_module._is_shortcut(type("E", (), {"state": 0x8})()))  # Num-Taste

    def test_f11_dropped_char_comes_again_later(self):
        # Sonst wäre F11 eine Taste zum Überspringen unbekannter Zeichen.
        s = self.single
        self._open_answer("U")
        with mock.patch.object(s, "next_char"):
            self.app.read_status()
        self.assertIn("U", s.retries.waiting)

    def test_f11_after_stop_and_restart_drops_nothing_old(self):
        # Neuer Durchgang wartet noch auf eine Ansage: kein Zeichen des alten verwerfen.
        s = self.single
        self._open_answer("R")
        s.stop()
        self.assertFalse(s.answer_open)
        s.retries.waiting.clear()
        with mock.patch.object(single_mode.announcer, "speaking", return_value=True), \
                mock.patch.object(single_mode.announcer, "when_quiet"):
            s.start()
        with mock.patch.object(s, "next_char"):
            self.app.read_status()
        self.assertEqual(s.retries.waiting, {})

    def test_f11_without_open_answer_changes_nothing(self):
        s = self.single
        self._open_answer()
        self._key("K")  # beantwortet
        token = s.timeout_token
        with mock.patch.object(s, "next_char") as next_char:
            self.app.read_status()
            self.root.update()
        next_char.assert_not_called()
        self.assertEqual(s.timeout_token, token)
        s.icr_var.set(False)
        self._open_answer()
        s.icr_var.set(False)
        with mock.patch.object(s, "next_char") as next_char:
            self.app.read_status()
            self.root.update()
        next_char.assert_not_called()
        self.assertTrue(s.waiting_for_input)

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


class ContinuousNumbersTest(AppTestCase):
    def test_numbers_are_offered_and_the_result_explains_them(self):
        c = self.mode("Kontinuierlich")
        self.assertIn("Zahlen", continuous_mode.CONTENTS)
        now = 1000.0
        c.charset = "5927"
        c.content = "numbers"
        c.session_stats = stats.SessionStats("continuous", "5927", 20, 600)
        c.number_meanings = [("599", "Rapport"), ("14", "CQ-Zone")]
        c.sent_log = [{"char": ch, "end_time": now + i, "group": 0} for i, ch in enumerate("59914")]
        c.typed_log = [{"char": ch, "time": now + i + 0.5} for i, ch in enumerate("59914")]
        c._finalize_session()
        shown = c.diff_var.get()
        self.assertIn("599 = Rapport", shown)
        self.assertIn("14 = CQ-Zone", shown)
        # Zufallszeichen haben keine Legende.
        c.content = "chars"
        c.session_stats = stats.SessionStats("continuous", "5927", 20, 600)
        c._finalize_session()
        self.assertNotIn("Bedeutung", c.diff_var.get())


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

    def test_heading_for_topic(self):
        """Erst der genaue Name, dann ein Kapitel, das so beginnt, zuletzt ein
        Unterabschnitt: „Network and security“ fängt „Network“ nicht ab."""
        from morsetrainer.widgets import help_window
        headings = [("h2", "3. Tabs"), ("h3", "Single"), ("h3", "Network and security"),
                    ("h2", "7. Network: practising as a group"), ("h3", "Statistics")]
        find = help_window.find_heading
        self.assertEqual(find(headings, "Single"), 1)
        self.assertEqual(find(headings, "Network"), 3)
        self.assertEqual(find(headings, "Stat"), 4)
        self.assertIsNone(find(headings, "Contest"))

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
            window.notebook.select(0)  # Anleitung
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

    def test_all_time_statistics_compare_the_last_days(self):
        from datetime import datetime, timedelta
        for days_ago, latency in ((20, 0.8), (2, 0.45)):
            start = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            tests.write_session([{"type": "config", "mode": "single", "start_time": start}]
                                + [{"type": "char", "char": "K", "typed": "K", "correct": True,
                                    "latency_s": latency}] * stats.MIN_TREND_COUNT
                                + [{"type": "summary"}])
        db.save_state(stats.ALL_TIME_KEY, {"K": {"good": 10, "wrong": 0, "confusions": {}}})  # Tabelle: Gesamtstand
        self.app._refresh_all_time(with_awards=False)
        panel = self.app.all_time_panel
        self.assertEqual(panel.compare_var.get(),
                         "Davor (30 Tage): Reaktion 0,80 s, 100 % richtig (aus 20 Zeichen) · "
                         "Letzte 7 Tage: Reaktion 0,45 s, 100 % richtig (aus 20 Zeichen). Reaktion: kleiner ist schneller.")
        tree = panel.char_tree
        row = dict(zip(tree["columns"], tree.item(tree.get_children()[0])["values"]))
        self.assertEqual(row["trend"], "0,80 → 0,45")
        self.assertIn("Letzte 7 Tage: Reaktion 0,45 s", self.app.statistics_spoken())
        self.assertNotIn("trend", self.mode("Einzelzeichen").stats_panel.char_tree["columns"])  # nur gesamt

    def test_statistics_tab_has_jump_buttons_and_a_short_empty_table(self):
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        names = ("Woche", "Diplome", "Lebenslinie", "Lernkartei", "Verwechslungen", "Fortschritt")
        buttons = {w.cget("text"): w for w in walk(self.app.root)
                   if w.winfo_class() == "TButton" and w.cget("text") in names}
        self.assertEqual(sorted(buttons), sorted(names))
        self.app.notebook.select(self.app.notebook.tabs()[-1])  # Reiter Statistik
        self.app.root.update()
        widths = [button.winfo_width() for button in buttons.values()]
        self.assertLessEqual(max(widths) - min(widths), 1)  # gleich breit (ein Pixel Rundung)
        self.assertGreater(min(widths), 50)
        up = [w for w in walk(self.app.root) if w.winfo_class() == "TButton" and w.cget("text") == "▲ Nach oben"]
        self.assertEqual(len(up), len(names))  # je Abschnitt ein Rücksprung
        for button in list(buttons.values()) + up:
            button.invoke()  # darf nicht scheitern, auch wenn der Reiter nicht sichtbar ist
        self.app._refresh_all_time(with_awards=False)
        self.assertEqual(int(self.app.all_time_panel.char_tree.cget("height")), theme.MIN_TREE_ROWS)

    def test_jump_moves_focus_into_the_section_and_back(self):
        from morsetrainer.widgets import announcer

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        buttons = {w.cget("text"): w for w in walk(self.app.root)
                   if w.winfo_class() == "TButton" and w.cget("text") in ("Woche", "Lernkartei")}
        said = []
        with mock.patch.object(announcer, "say", side_effect=lambda text, *a, **k: said.append(text)):
            self.root.deiconify()
            self.root.geometry("1024x600")
            self.app.notebook.select(self.app.notebook.tabs()[-1])  # Reiter Statistik
            self.root.update()
            buttons["Lernkartei"].invoke()
            self.root.update()
            self.assertEqual(said[-1], "Abschnitt Lernkartei.")
            focus = self.root.focus_get()
            self.assertIsNotNone(focus)
            self.assertIs(focus, self.app.review_button)  # im Abschnitt, nicht auf dem Sprungknopf
            canvas = next(w for w in self.root.nametowidget(self.app.stats_tab).winfo_children()
                          if w.winfo_class() == "Canvas")
            self.assertGreater(canvas.yview()[0], 0.2)  # tatsächlich hinuntergerollt
            up = [w for w in walk(self.app.root) if w.winfo_class() == "TButton" and w.cget("text") == "▲ Nach oben"]
            up[3].invoke()  # der des Abschnitts Lernkartei
            self.root.update()
            self.assertEqual(said[-1], "Sprungzeile.")
            self.assertLess(canvas.yview()[0], 0.02)
            self.assertIs(self.root.focus_get(), buttons["Woche"])  # wieder oben, in der Sprungzeile
        self.assertNotIn("▲", announcer.describe(up[0]))

    def test_hidden_fsrs_tab_is_read_by_f11_and_never_counts_as_last_tab(self):
        stats_tab = self.app.stats_tab
        self.app.toggle_fsrs_tab()
        panel = self.app.fsrs_panel
        self.assertEqual(self.app.notebook.select(), str(panel.frame))
        said = []
        with mock.patch.object(self.app.announcer, "say", side_effect=lambda text, *a, **k: said.append(text)):
            self.app.read_status()
        self.assertEqual(said[-1], panel.text_var.get())
        self.app.select_tab(-1)  # Alt+0: die Statistik, nicht der versteckte Reiter
        self.assertEqual(self.app.notebook.select(), stats_tab)
        self.app.toggle_fsrs_tab()
        self.assertNotIn(str(panel.frame), self.app.notebook.tabs())

    def test_hidden_fsrs_tab_stays_closed_during_the_daily_practice(self):
        self.app.daily.active = True
        try:
            before = self.app.notebook.tabs()
            self.app.toggle_fsrs_tab()
            self.assertEqual(self.app.notebook.tabs(), before)
        finally:
            self.app.daily.active = False

    def test_table_columns_grow_with_the_font_and_scroll_sideways(self):
        from tkinter import font as tkfont
        panel = self.app.all_time_panel
        tree = panel.char_tree
        self.assertEqual(panel.compare_var.get(), "")
        compare_label = next(w for w in tree.master.winfo_children()
                             if str(w.cget("textvariable") if "textvariable" in w.keys() else "") == str(panel.compare_var))
        self.assertEqual(compare_label.winfo_manager(), "")  # leer: keine Lücke
        narrow = tree.column("trend", "width")
        self.app.font_scale_var.set(200)
        heading = tkfont.Font(name=theme.HEADING, exists=True).measure(tree.heading("trend", "text"))
        self.assertGreaterEqual(tree.column("trend", "width"), heading)
        self.assertGreater(tree.column("trend", "width"), narrow)
        self.root.deiconify()
        self.root.geometry("1024x700")
        self.app.select_tab(len(self.app.notebook.tabs()) - 1)
        self.root.update()
        self.assertLess(tree.xview()[1], 1.0)  # passt nicht: rollt
        self.assertEqual(tree._mt_xbar.winfo_manager(), "pack")
        tree.focus_force()
        self.root.update()
        tree.event_generate("<Right>")
        self.root.update()
        self.assertGreater(tree.xview()[0], 0.0)
        self.app.font_scale_var.set(100)

    def test_progress_table_shows_its_scroll_bar_again(self):
        panel = self.app.progress_panel
        self.root.deiconify()
        self.root.geometry("1024x700")
        panel.table._mt_columns = {column: 400 for column in panel.table["columns"]}  # breiter als das Fenster
        theme._size_columns(panel.table)
        self.app.select_tab(len(self.app.notebook.tabs()) - 1)
        for _ in range(3):  # Tabelle, Diagramm, wieder Tabelle
            panel._toggle_table()
            self.root.update()
        self.assertEqual(panel.table._mt_xbar.winfo_manager(), "pack")

    def test_progress_text_on_a_single_day(self):
        from datetime import datetime
        from morsetrainer.widgets.progress_widget import span_text
        day = [{"time": datetime(2026, 9, 30, h)} for h in (12, 18, 19)]
        self.assertEqual(span_text(day), "3 Durchgänge am 30.09.2026")
        self.assertEqual(span_text(day[:1]), "1 Durchgang am 30.09.2026")

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
        self.assertTrue(panel.info_var.get().startswith("2 Durchgänge vom 25.09.2026 bis 03.10.2026 an 2 Tagen"))
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


class UsabilityTest(AppTestCase):
    """Bedienung: Platz im Durchgang, einheitliche Tasten, sichtbares Ziel und
    Ergebnis, Hilfe zum Reiter, Optionsgruppen als ein Tab-Stopp."""

    def _esc(self, widget):
        self.app._dispatch_key(type("E", (), {"keysym": "Escape", "char": "\x1b", "widget": widget})())

    def test_options_card_hidden_while_running(self):
        # Bei großer Schrift oder kleinem Bildschirm schob die Karte Antwortfeld,
        # Status und Stop aus dem sichtbaren Bereich.
        for title in ("Gruppen", "Kontinuierlich"):
            mode = self.mode(title)
            card = mode.options_card
            siblings = card.master.pack_slaves()
            self.app.show_mode(title)
            # Am Stück: ohne Audio-Thread (die Attrappe hat keinen Tonstrom).
            with mock.patch.object(type(mode), "_play_loop", create=True):
                mode.start()
            self.assertTrue(mode.running, title)
            self.assertEqual(card.winfo_manager(), "", title)
            mode.stop()
            self.assertEqual(card.master.pack_slaves(), siblings, title)  # an derselben Stelle zurück

    def test_focus_leaves_the_hidden_card(self):
        group = self.mode("Gruppen")
        self.app.show_mode("Gruppen")
        spin = next(w for w in group.options_card.winfo_children()[-1].winfo_children()
                    if isinstance(w, ttk.Spinbox))
        spin.focus_force()
        self.root.update()
        group.start()
        self.root.update()
        self.assertNotEqual(self.root.focus_get(), spin)
        group.stop()

    def test_escape_stops_in_every_practice_tab(self):
        single = self.mode("Einzelzeichen")
        self.app.show_mode("Einzelzeichen")
        single.start()
        self._esc(self.root)
        self.assertFalse(single.running)
        group = self.mode("Gruppen")
        self.app.show_mode("Gruppen")
        group.start()
        self._esc(group.entry)  # auch aus dem Antwortfeld
        self.assertFalse(group.running)

    def test_start_buttons_name_their_key(self):
        self.assertEqual(self.mode("Einzelzeichen").start_button.cget("text"), "Start (F5)")
        self.assertEqual(self.mode("Gruppen").start_button.cget("text"), "Start (F5)")
        self.assertEqual(self.mode("Contest").start_button.cget("text"), "Start (F10)")
        self.assertIn("F12", self.app.daily_bar.start_button.cget("text"))

    def test_f5_in_contest_points_to_f10(self):
        contest = self.mode("Contest")
        contest.on_function_key("F5")
        self.assertFalse(contest.running)
        self.assertIn("F10", contest.status_var.get())

    def test_single_shows_goal_and_result(self):
        single = self.mode("Einzelzeichen")
        single.start()
        self.assertEqual(single.progress_var.get(), "0 von 50 Zeichen, Ziel 90 %")
        single.current_char, single.voice, single.waiting_for_input, single.replayed = "K", (20, 600), True, False
        single.play_start_time = time.time() - 0.5
        single.on_key(type("E", (), {"keysym": "K", "char": "K"})())
        self.assertEqual(single.progress_var.get(), "1 von 50 Zeichen, Ziel 90 %")
        single.stop()
        self.assertEqual(single.status_var.get(), "Durchgang beendet: 1 von 1 Zeichen richtig (100 %).")
        self.assertEqual(single.progress_var.get(), "")

    def test_stop_without_answers_says_stopped(self):
        single = self.mode("Einzelzeichen")
        single.start()
        single.stop()
        self.assertEqual(single.status_var.get(), "Gestoppt.")

    def test_tempo_hint_names_the_effective_speed(self):
        self.app.wpm_var.set(20)
        self.app.farnsworth_wpm_var.set(10)
        self.app.farnsworth_enabled_var.set(True)
        self.assertEqual(self.app.cpm_var.get(), "≈ 50 ZpM effektiv")
        self.app.farnsworth_enabled_var.set(False)
        self.assertEqual(self.app.cpm_var.get(), "20 WPM ≈ 100 ZpM")

    def test_help_opens_the_guide_at_the_tab(self):
        from morsetrainer.widgets import help_window
        help_window.HelpWindow.show(self.root, "Am Stück")
        window = help_window.HelpWindow._open
        try:
            self.assertEqual(window.notebook.index("current"), 0)  # Anleitung zuerst
            text = window.texts["docs/Anleitung.md"]
            window.top.update()
            top_line = text.get("@0,0 linestart", "@0,0 lineend")
            self.assertEqual(top_line.strip(), "Am Stück")
            window.show_topic("Netzwerk")  # Abschnitt mit Nummer: „7. Netzwerk: …“
            window.top.update()
            self.assertIn("Netzwerk", text.get("@0,0 linestart", "@0,0 lineend"))
        finally:
            window.top.destroy()

    def test_choice_group_is_one_tab_stop(self):
        buttons = self.app.one_by_one_buttons
        self.assertEqual([bool(b.cget("takefocus")) for b in buttons], [True, False, False, False])
        self.app.show_content(app_module.ONE_BY_ONE[2])
        self.assertEqual([bool(b.cget("takefocus")) for b in buttons], [False, False, True, False])

    def test_daily_goal_is_in_the_settings_window(self):
        def spinboxes(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Spinbox):
                    yield child
                yield from spinboxes(child)
        variables = [str(s.cget("textvariable")) for s in spinboxes(self.app.settings_window)]
        self.assertIn(str(self.app.daily_goal_var), variables)

    def test_settings_window_fits_a_small_screen_at_200_percent(self):
        app = self.app
        window = app.settings_window

        def hints_below():
            return all(int(hint.grid_info()["row"]) == 1 for row, controls in app.settings_hinted
                       for hint in row.winfo_children() if hint is not controls and hint.grid_info())

        def contrast_hint():
            return next(hint for row, controls in app.settings_hinted for hint in row.winfo_children()
                        if str(hint.cget("textvariable") if hint is not controls else "") == str(app.contrast_hint_var))
        app.font_scale_var.set(200)
        with mock.patch.object(window, "winfo_screenwidth", return_value=1024), \
                mock.patch.object(window, "winfo_screenheight", return_value=600):
            app._fit_settings()
            window.update_idletasks()
            self.assertTrue(hints_below())
            self.assertEqual(contrast_hint().winfo_manager(), "")  # leer: keine Leerzeile darunter
            app.contrast_var.set(not app.contrast_var.get())
            app._contrast_toggled()
            self.assertEqual(int(contrast_hint().grid_info()["row"]), 1)  # „wirkt nach Neustart“ erscheint
            app.contrast_var.set(not app.contrast_var.get())
            app._contrast_toggled()
            self.assertLessEqual(window.winfo_reqwidth(), 1024 - 40)
            self.assertLessEqual(window.winfo_reqheight(), 600)
            self.assertLess(int(app.settings_scroller.canvas.cget("height")), app.settings_body.winfo_reqheight())
        app.font_scale_var.set(100)
        with mock.patch.object(window, "winfo_screenwidth", return_value=4000), \
                mock.patch.object(window, "winfo_screenheight", return_value=3000):
            app._fit_settings()
            self.assertFalse(hints_below())
            self.assertEqual(int(app.settings_scroller.canvas.cget("height")), app.settings_body.winfo_reqheight())

    def test_data_folder_button_opens_the_folder_or_names_it(self):
        app = self.app

        def find(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button) and str(child.cget("text")) == "Datenordner öffnen":
                    return child
                found = find(child)
                if found is not None:
                    return found
        button = find(app.settings_window)
        with mock.patch.object(app_module.storage, "open_with_system") as opened, \
                mock.patch.object(announcer, "say") as say:
            button.invoke()
        opened.assert_called_once_with(app_module.DATA_DIR)
        say.assert_called_once_with("Datenordner wird geöffnet.")
        with mock.patch.object(app_module.storage, "open_with_system", side_effect=FileNotFoundError("xdg-open")), \
                mock.patch.object(app_module.dialog, "showerror") as error:
            button.invoke()
        self.assertIn(str(app_module.DATA_DIR), error.call_args[0][1])

    def test_settings_window_fits_when_opened_after_a_zoom(self):
        app = self.app
        window = app.settings_window
        app.font_scale_var.set(200)  # geschlossen vergrößert
        with mock.patch.object(window, "winfo_screenwidth", return_value=1024), \
                mock.patch.object(window, "winfo_screenheight", return_value=600):
            app.open_settings()
            window.update_idletasks()
            self.assertLessEqual(window.winfo_reqwidth(), 1024 - 40)
            self.assertLessEqual(window.winfo_reqheight(), 600)
        app.close_settings()
        app.font_scale_var.set(100)

    def tall_screen(self):
        """Ein hoher Bildschirm: der Kompaktmodus hängt dann nur an der Schriftgröße."""
        patch = mock.patch.object(self.root, "winfo_screenheight", return_value=4000)
        patch.start()
        self.addCleanup(patch.stop)

    def test_header_toggle_hands_focus_on_when_it_disappears(self):
        self.tall_screen()
        app = self.app
        app.font_scale_var.set(200)
        self.root.deiconify()
        app.header_toggle.focus_force()
        self.root.update()
        app.font_scale_var.set(175)
        self.root.update()
        self.assertEqual(self.root.focus_get(), app.lesson_spinbox)

    def test_header_survives_focus_in_an_open_drop_down_list(self):
        app = self.app
        app.font_scale_var.set(200)
        with mock.patch.object(self.root, "focus_get", side_effect=KeyError("popdown")):
            app._place_header(open_=False)
        self.assertFalse(app.header_open)
        self.assertEqual(app.header.winfo_manager(), "")

    def test_week_strip_and_legend_hide_at_200_percent(self):
        self.tall_screen()
        bar = self.app.daily_bar
        bar.show_week([], 0)  # noch kein Stern: Legende wird gezeigt
        self.assertEqual((bar.week_label.winfo_manager(), bar.legend.winfo_manager()), ("pack", "pack"))
        self.app.font_scale_var.set(200)
        self.assertEqual((bar.week_label.winfo_manager(), bar.legend.winfo_manager()), ("", ""))
        self.assertEqual(bar.goal_label.winfo_manager(), "pack")  # das Wochenziel bleibt
        bar.show_week([], 0)
        self.assertEqual(bar.legend.winfo_manager(), "")
        self.app.font_scale_var.set(175)
        self.assertEqual((bar.week_label.winfo_manager(), bar.legend.winfo_manager()), ("pack", "pack"))
        self.assertEqual(bar.week_label.master.pack_slaves()[0], bar.week_label)  # wieder vor dem Ziel

    def test_feedback_is_scrolled_into_view_at_200_percent(self):
        self.root.deiconify()
        self.root.geometry("984x520")  # 1024×600 abzüglich Rand: die kleinste Anzeige, für die das gilt
        self.app.font_scale_var.set(200)
        for name in ("Einzelzeichen", "Gruppen"):
            self.app.show_mode(name)
            mode = self.mode(name)
            mode.scroller.canvas.yview_moveto(0)
            self.root.update()
            mode.status_var.set("Höre zu…")
            if hasattr(mode, "diff_var"):
                mode.diff_var.set("gesendet  KMU\ngetippt   KMR\n              ^")
            mode.feedback_var.set("Falsch: war K, du: M")
            self.root.update()
            canvas = mode.scroller.canvas
            shown = [mode.feedback_label] + [w for w in mode.feedback_label.master.winfo_children()
                                             if hasattr(mode, "diff_var") and w is not mode.feedback_label]
            for label in shown:  # Rückmeldung und, in Gruppen, die Gegenüberstellung ganz im Bild
                top = label.winfo_rooty() - canvas.winfo_rooty()
                self.assertGreaterEqual(top, 0, name)
                self.assertLessEqual(top + label.winfo_height(), canvas.winfo_height(), name)
        self.app.font_scale_var.set(100)

    def test_hint_wraps_inside_its_right_padding(self):
        self.root.deiconify()
        self.root.geometry("1024x700")
        self.app.font_scale_var.set(200)
        self.app.show_mode("Wörter")
        self.root.update()
        parent = self.mode("Wörter").scroller.inner
        intro = parent.winfo_children()[0]  # Erklärtext, padx=10
        self.assertLessEqual(intro.winfo_x() + intro.winfo_reqwidth(), parent.winfo_width() - 10)
        self.app.font_scale_var.set(100)

    def test_hint_beside_another_widget_wraps_at_its_own_room(self):
        row = ttk.Frame(self.root, width=400)
        row.pack()
        ttk.Label(row, text="Vorne", width=20).pack(side="left")
        hint = theme.hint(row, text="Ein langer Hinweis " * 10, wrap=560)
        hint.pack(side="left", padx=(0, 10))
        self.root.update_idletasks()
        theme._fit_wrap(hint, 400)
        room = 400 - hint.winfo_x() - 10 - theme.scaled(theme.WRAP_MARGIN)
        self.assertEqual(int(float(str(hint.cget("wraplength")))), room)  # ab seinem Anfang, ohne rechten Rand

    def test_header_collapses_at_200_percent(self):
        self.tall_screen()
        app = self.app
        self.assertEqual(app.header_row.winfo_manager(), "")  # 100 %: keine Zeile, Leiste offen
        self.assertEqual(app.header.winfo_manager(), "pack")
        app.charset_var.set("KMURESNAPTLWI.JZ=FOY")
        app.wpm_var.set(22)
        app.font_scale_var.set(200)
        self.assertEqual(app.header_row.winfo_manager(), "pack")
        self.assertEqual(app.header.winfo_manager(), "")
        self.assertEqual(app.header_settings.winfo_manager(), "pack")  # Einstellungen auch zugeklappt
        self.root.update_idletasks()
        self.assertLessEqual(app.footer.winfo_reqwidth(), 1024)  # Fußzeile passt auf 1024 Pixel
        self.assertNotIn("entwickelt", app.version_label.cget("text"))
        self.assertEqual(app.header_toggle.cget("text"),
                         "▸ Koch-Lektion 19 · 22/10 WPM · 600 Hz · KMURESNAPTLW…")
        self.assertEqual(announcer.describe(app.header_toggle),
                         "Kopfleiste, Knopf, zugeklappt, Koch-Lektion 19, 22 WPM, effektiv 10, 600 Hz.")
        app.charset_var.set("KMQ")  # eigene Zeichen werden buchstabiert
        self.assertIn("eigene Zeichen: Ka, Emm, Ku, 22 WPM", announcer.describe(app.header_toggle))
        app.charset_var.set("KMURESNAPTLWI.JZ=FOY")
        with mock.patch.object(announcer, "say") as say:
            app.header_toggle.invoke()
        say.assert_called_once_with("Kopfleiste aufgeklappt.")
        self.assertEqual(app.header.winfo_manager(), "pack")
        self.assertTrue(app.header_toggle.cget("text").startswith("▾ "))
        self.assertEqual(app.header_settings.winfo_manager(), "")  # offen steht er in der Leiste
        # Zuklappen mit dem Fokus in der Leiste: der Fokus geht auf den Knopf.
        self.root.deiconify()
        charset_entry = next(w for w in app.header.grid_slaves() if isinstance(w, ttk.Entry))
        charset_entry.focus_force()
        self.root.update()
        app.header_toggle.invoke()
        self.root.update()
        self.assertEqual(self.root.focus_get(), app.header_toggle)
        app.font_scale_var.set(175)
        self.assertEqual(app.header_row.winfo_manager(), "")
        self.assertEqual(app.header.winfo_manager(), "pack")

    def test_hint_never_wraps_wider_than_its_room(self):
        self.app.font_scale_var.set(200)
        box = ttk.Frame(self.root, width=500, height=200)
        box.pack_propagate(False)
        box.pack()
        hint = theme.hint(box, text="Eins nach dem anderen: hören, antworten, das nächste. " * 3, wrap=640)
        hint.pack(anchor="w")
        self.root.deiconify()
        self.root.update()
        self.assertLessEqual(int(float(str(hint.cget("wraplength")))), 500)
        self.assertLessEqual(hint.winfo_width(), 500)

    def test_header_shows_effective_tempo_and_follows_farnsworth(self):
        app = self.app
        app.font_scale_var.set(200)
        app.wpm_var.set(20)
        app.farnsworth_enabled_var.set(True)
        app.farnsworth_wpm_var.set(12)
        self.assertIn("20/12 WPM", app.header_toggle.cget("text"))
        app.farnsworth_enabled_var.set(False)
        self.assertIn("· 20 WPM ·", app.header_toggle.cget("text"))

    def test_settings_button_in_collapsed_header_opens_settings(self):
        app = self.app
        app.font_scale_var.set(200)
        with mock.patch.object(app, "open_settings") as open_settings:
            app.header_settings.invoke()
        open_settings.assert_called_once_with()

    def test_hint_wrap_settles_when_it_sets_its_parents_width(self):
        # Ohne fill bestimmt der Hinweis die Breite seines Rahmens: nicht schrumpfen, nicht pendeln.
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        window.geometry("720x600")
        box = ttk.Frame(window)
        box.pack(anchor="w")
        hint = theme.hint(box, text="Eins nach dem anderen: hören, antworten, das nächste. " * 4, wrap=540)
        hint.pack(anchor="w")
        window.update()
        values = set()
        for _ in range(50):
            self.root.update()
            values.add(str(hint.cget("wraplength")))
        # Weder enger (der Text steht nicht über) noch hin und her.
        self.assertEqual(values, {str(theme.scaled(540))})

    def test_restart_button_only_while_a_restart_is_pending(self):
        self.assertEqual(self.app.restart_button.winfo_manager(), "")
        with mock.patch.object(app_module.update, "restart_command", return_value=["morsetrainer"]):
            self.app.contrast_var.set(not self.app.contrast_at_start)
            self.app._contrast_toggled()
            self.assertEqual(self.app.restart_button.winfo_manager(), "pack")
            self.app.contrast_var.set(self.app.contrast_at_start)
            self.app._contrast_toggled()
            self.assertEqual(self.app.restart_button.winfo_manager(), "")


class UsabilityFixesTest(AppTestCase):
    """Befunde der Gesamtprüfung Usability."""

    def test_typed_values_are_settled_when_the_field_is_left(self):
        from morsetrainer.widgets.ui_widgets import settle_on_leave
        self.app.wpm_var.set(100)  # wie getippt: das Feld hält 100, get() liefert 40
        self.assertEqual(self.app.wpm_var.get(), 40)
        spin = ttk.Spinbox(self.root, textvariable=self.app.wpm_var)
        settle_on_leave(spin, self.app.wpm_var)
        spin.event_generate("<FocusOut>")
        self.assertEqual(self.root.tk.globalgetvar(str(self.app.wpm_var)), 40)

    def test_typed_lesson_applies_without_enter_but_custom_chars_stay(self):
        self.app.lesson_var.set(5)
        self.app._lesson_field_left()
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(5))
        self.app.charset_var.set("XYZ")  # eigene Zeichen
        self.app._lesson_field_left()
        self.assertEqual(self.app.charset_var.get(), "XYZ")
        self.app.charset_var.set(koch.lesson_charset(2))
        self.app.lesson_var.set(999)
        self.app._lesson_field_left()
        self.assertEqual(self.app.lesson_var.get(), koch.MAX_LESSON)

    def test_one_by_one_hint_follows_the_content(self):
        hints = {}
        for title in ("Einzelzeichen", "Gruppen", "Wörter", "Rufzeichen"):
            self.app.one_by_one_var.set(title)
            self.app._show_one_by_one()
            hints[title] = self.app.one_by_one_hint_var.get()
        self.assertIn("Eins nach dem anderen", hints["Einzelzeichen"])
        self.assertIn("Mehrere Zeichen", hints["Gruppen"])
        self.assertEqual(hints["Wörter"], "")
        self.assertEqual(hints["Rufzeichen"], "")

    def test_input_style_is_explained(self):
        mode = self.mode("Gruppen")
        mode.style_var.set("head")
        self.assertIn("im Kopf", mode.style_hint_var.get())
        mode.style_var.set("copy")
        self.assertIn("während des Tons", mode.style_hint_var.get())

    def test_start_row_comes_before_the_options(self):
        for title in ("Gruppen", "Rufzeichen"):
            mode = self.mode(title)
            children = list(mode.options_card.master.winfo_children())
            self.assertLess(children.index(mode.start_button.master), children.index(mode.options_card), title)

    def test_help_button_names_no_key_in_the_contest_tab(self):
        self.app.show_mode("Contest")
        self.root.update()
        self.assertEqual(self.app.help_button.cget("text"), "Hilfe")
        self.app.show_mode("Einzelzeichen")
        self.root.update()
        self.assertEqual(self.app.help_button.cget("text"), "Hilfe (F1)")

    def test_destructive_question_defaults_to_no(self):
        from morsetrainer.widgets import dialog
        box = dialog.MessageDialog(self.root, "Frage", "Löschen?", question=True, confirm="Statistik löschen")
        self.addCleanup(box.close)
        box._enter()
        self.assertFalse(box.answer)
        box2 = dialog.MessageDialog(self.root, "Frage", "Weiter?", question=True)
        self.addCleanup(box2.close)
        box2._enter()
        self.assertTrue(box2.answer)

    def test_ctrl_q_quits(self):
        self.assertTrue(self.root.bind_all("<Control-q>"))


class AccessibilityFixesTest(AppTestCase):
    """Befunde der Gesamtprüfung Barrierefreiheit."""

    def setUp(self):
        super().setUp()
        self.said = []
        patch = mock.patch.object(announcer, "say", lambda text, *a, **k: self.said.append(text))
        patch.start()
        self.addCleanup(patch.stop)

    def test_empty_tempo_field_uses_the_last_valid_value(self):
        self.app.wpm_var.set(25)
        self.assertEqual(self.app.wpm_var.get(), 25)
        self.root.tk.globalsetvar(str(self.app.wpm_var), "")  # Feld leer getippt
        self.assertEqual(self.app.wpm_var.get(), 25)  # kein TclError beim Start

    def test_corrected_value_is_announced(self):
        from morsetrainer.widgets.ui_widgets import settle_on_leave
        self.app.wpm_var.set(100)
        spin = ttk.Spinbox(self.root, textvariable=self.app.wpm_var)
        settle_on_leave(spin, self.app.wpm_var, "Tempo", "WPM")
        spin.event_generate("<FocusOut>")
        self.assertTrue(any("40 WPM" in text for text in self.said), self.said)

    def test_lesson_clamped_is_announced(self):
        self.app.charset_var.set(koch.lesson_charset(2))
        self.app.lesson_var.set(999)
        self.app._lesson_field_left()
        self.assertTrue(any("Lektion" in text and "Zeichen" in text for text in self.said), self.said)

    def test_tab_change_takes_focus_from_a_hidden_widget(self):
        self.root.deiconify()
        self.root.update()
        self.mode("Einzelzeichen").start_button.focus_force()
        self.root.update()
        self.app.select_tab(1)
        self.root.update()
        focus = self.root.focus_get()
        self.assertTrue(focus is None or focus.winfo_viewable())
        self.assertIsNot(focus, self.mode("Einzelzeichen").start_button)

    def test_locked_tab_says_why(self):
        self.app._lock_tabs()
        self.said.clear()
        self.app.select_tab(1)
        self.assertTrue(any("gesperrt" in text for text in self.said), self.said)
        self.app._unlock_tabs()

    def test_locked_content_buttons_leave_the_tab_order(self):
        self.app._lock_tabs()
        self.assertTrue(all(str(b.cget("takefocus")) in ("0", "") or not b.cget("takefocus")
                            for b in self.app.one_by_one_buttons))
        self.app._unlock_tabs()
        self.assertEqual(sum(1 for b in self.app.one_by_one_buttons if str(b.cget("takefocus")) in ("1", "True")), 1)

    def test_contest_fields_and_input_style_have_spoken_names(self):
        from morsetrainer.widgets import announcer as ann
        run = self.mode("Contest")
        self.assertIn("Call", ann.describe(run.call_entry))
        self.assertIn("Austausch", ann.describe(run.exch_entry))
        group = self.mode("Gruppen")
        group.style_var.set("copy")
        self.said.clear()
        group._style_chosen()
        self.assertTrue(any("während des Tons" in text for text in self.said), self.said)

    def test_header_leaves_the_tab_order_in_the_statistics_tab(self):
        self.app._set_header_tab_stops(False)
        stops = [w for w in self._descendants(self.app.header) if str(w.cget("takefocus")) == "1"]
        self.assertEqual(stops, [])
        self.app._set_header_tab_stops(True)

    @staticmethod
    def _descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from AccessibilityFixesTest._descendants(child)

    def test_ctrl_f1_opens_help_in_the_contest(self):
        self.app.show_mode("Contest")
        with mock.patch.object(self.app, "open_help") as opened:
            self.app._dispatch_key(mock.Mock(keysym="F1", char="", state=0x4))
        opened.assert_called_once()

    def test_ctrl_shift_q_also_quits(self):
        self.assertTrue(self.root.bind_all("<Control-Q>"))

    def test_contrast_palette_meets_seven_to_one(self):
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(a, b):
            high, low = sorted((luminance(a), luminance(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)

        palette = theme.PALETTES["contrast"]
        for fg, bg in (("OK", "OK_BG"), ("ERROR", "ERROR_BG")):
            self.assertGreaterEqual(ratio(palette[fg], palette[bg]), 7.0, fg)
        self.assertGreaterEqual(ratio(palette["TROUGH"], palette["BG"]), 3.0)
        light = theme.PALETTES["light"]
        for fg, bg in (("OK", "OK_BG"), ("ERROR", "ERROR_BG"), ("MUTED", "BUTTON_ACTIVE")):
            self.assertGreaterEqual(ratio(light[fg], light[bg]), 4.5, fg)


class FsrsTabTest(AppTestCase):
    def test_tab_is_hidden_until_the_shortcut_and_toggles(self):
        from morsetrainer.widgets.fsrs_panel import TAB_NAME, report_text
        before = self.app.notebook.tabs()
        self.assertNotIn(TAB_NAME, [self.app.notebook.tab(t, "text") for t in before])
        for sequence in ("<Control-Shift-F>", "<Control-Shift-f>"):
            self.assertTrue(self.app.root.bind_all(sequence))  # das Kürzel ist belegt
        self.app.toggle_fsrs_tab()
        self.app.root.update()
        tabs = self.app.notebook.tabs()
        self.assertEqual(len(tabs), len(before) + 1)
        self.assertEqual(self.app.notebook.tab("current", "text"), TAB_NAME)
        self.assertIn("Zu früh für ein Urteil", self.app.fsrs_panel.text_var.get())
        self.app.toggle_fsrs_tab()
        self.assertEqual(self.app.notebook.tabs(), before)
        self.assertNotEqual(self.app.notebook.tab("current", "text"), TAB_NAME)
        self.assertIn("Entscheidungen im Protokoll: 0", report_text({"entries": 0, "predicted": 0, "first": None,
                                                                      "last": None, "brier": None, "bins": [],
                                                                      "boxes": [], "verdict": "few"}))
