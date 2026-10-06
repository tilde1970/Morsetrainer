"""Barrierefreiheit: Schriftgröße, Sprachansage, hoher Kontrast, Tastatur und Einstellungsfenster."""
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.widgets import theme
from tests.test_modes import AppTestCase


class FontScaleTest(AppTestCase):
    def size(self, name):
        return abs(int(tkfont.nametofont(name, root=self.root).cget("size")))

    def test_zoom_keys_and_reset(self):
        default, status = self.size("TkDefaultFont"), self.size(theme.STATUS)
        self.app.zoom(1)
        self.app.zoom(1)
        self.assertEqual(theme.scale(), 125)
        self.assertEqual(self.size("TkDefaultFont"), round(default * 1.25))
        self.assertEqual(self.size(theme.STATUS), round(status * 1.25))
        self.assertEqual(self.app.zoom_box.get(), "125 %")
        self.app.zoom(-1)
        self.assertEqual(theme.scale(), 110)
        self.app.zoom(0)
        self.assertEqual((theme.scale(), self.size("TkDefaultFont")), (100, default))
        for _ in range(10):
            self.app.zoom(1)
        self.assertEqual(theme.scale(), theme.ZOOM_STEPS[-1])  # nicht über die größte Stufe
        self.app.zoom(0)
        self.app.zoom(-1)
        self.assertEqual(theme.scale(), 90)
        for _ in range(10):
            self.app.zoom(-1)
        self.assertEqual(theme.scale(), 75)  # kleinste Stufe
        self.assertEqual(self.size("TkDefaultFont"), round(default * 0.75))
        self.app.zoom(0)
        self.assertEqual(theme.scale(), 100)

    def test_tables_and_wrapped_texts_grow(self):
        row = int(ttk.Style(self.root).lookup("Treeview", "rowheight"))
        label = theme.hint(self.root, text="x", wrap=400)
        self.app.set_font_scale(150)
        self.assertGreater(int(ttk.Style(self.root).lookup("Treeview", "rowheight")), row)
        self.assertEqual(int(float(str(label.cget("wraplength")))), 600)
        self.app.set_font_scale(100)
        self.assertEqual(int(float(str(label.cget("wraplength")))), 400)

    def test_later_windows_get_wider_wrapping(self):
        self.app.set_font_scale(200)
        window = tk.Toplevel(self.root)
        label = theme.hint(window, text="x", wrap=300)
        window.event_generate("<Map>")
        self.assertEqual(int(float(str(label.cget("wraplength")))), 600)
        window.destroy()

    def test_saved_with_shared_settings(self):
        self.app.set_font_scale(175)
        self.assertEqual(self.app._shared_settings()["font_scale"], 175)
        self.app.set_font_scale(100)
        self.app.saved_state = {"shared": {"font_scale": 150}}
        self.app._restore_shared_settings()
        self.assertEqual(theme.scale(), 150)
        self.app.saved_state = {"shared": {"font_scale": 900}}  # Unsinn: bleibt
        self.app._restore_shared_settings()
        self.assertEqual(theme.scale(), 150)

    def test_font_size_box_shows_normal_size_at_first_start(self):
        self.assertEqual(self.app.zoom_box.get(), "100 %")

    def test_zoom_steps(self):
        self.assertEqual(theme.zoom_step(100, 1), 110)
        self.assertEqual(theme.zoom_step(130, -1), 125)
        self.assertEqual(theme.zoom_step(100, -1), 90)
        self.assertEqual(theme.zoom_step(75, -1), 75)


class AnnouncerTest(AppTestCase):
    """Sprachansage: Ergebnis, Reiter und Status mit der eingebauten Stimme;
    der Ablauf geht erst nach der Ansage weiter."""

    def setUp(self):
        super().setUp()
        import numpy as np
        from morsetrainer.core import speech
        from morsetrainer.widgets import announcer
        self.announcer = announcer
        self.said, self.played = [], []
        self.patches = [
            mock.patch.object(speech.speaker, "available", lambda: None),
            # Geladen vortäuschen: sonst lüde die Ansage die echte Stimme im
            # Hintergrund, und ohne Piper bliebe ein Fehler an ihr hängen.
            mock.patch.object(speech.speaker, "voice", object()),
            mock.patch.object(speech.speaker, "synth",
                              lambda text: (self.said.append(text), np.zeros(4800, dtype=np.float32))[1]),
            mock.patch.object(announcer.audio, "play_quietly", lambda samples: self.played.append(len(samples))),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        super().tearDown()

    def pump_until(self, condition, timeout=3.0):
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end and not condition():
            self.root.update()
            time.sleep(0.01)
        return condition()

    def test_off_means_nothing_said_and_flow_goes_on(self):
        done = []
        self.app.announcer.say("Richtig.", then=lambda: done.append(True))
        self.assertEqual(done, [True])
        self.assertEqual(self.said, [])

    def test_flow_waits_for_the_announcement(self):
        self.app.announcer.var.set(True)
        done = []
        self.app.announcer.say("Richtig.", then=lambda: done.append(True))
        self.assertEqual(done, [])  # noch nicht: erst sprechen
        self.assertTrue(self.pump_until(lambda: done))
        self.assertIn("Richtig.", self.said)
        self.assertIn(4800, self.played)
        played = len(self.played)
        self.app.announcer.say("Richtig.")  # aus dem Zwischenspeicher
        self.assertTrue(self.pump_until(lambda: len(self.played) > played))
        self.assertEqual(self.said.count("Richtig."), 1)

    def test_flow_waits_until_the_speech_has_ended(self):
        # Kernversprechen für Blinde: Der nächste Morseton schneidet die Ansage
        # nicht ab. Eine Sekunde Sprache: `then` frühestens nach ihrem Ende.
        import time
        import numpy as np
        from morsetrainer.core import speech
        self.app.announcer.var.set(True)
        # Erst die Ansage des Reiters beim Fensteraufbau ausklingen lassen,
        # sonst verdrängt sie die hier geprüfte.
        self.pump_until(lambda: False, timeout=0.5)
        done = []
        with mock.patch.object(speech.speaker, "synth",
                               lambda text: np.zeros(self.announcer.SAMPLE_RATE, dtype=np.float32)):
            start = time.monotonic()
            self.app.announcer.say("Eine Sekunde lang.", then=lambda: done.append(time.monotonic()))
            self.assertTrue(self.pump_until(lambda: done, timeout=4))
        self.assertGreaterEqual(done[0] - start, 1.0 + self.announcer.AFTER_SPEECH_MS / 1000 - 0.05)

    def test_superseded_announcement_waits_for_the_new_one(self):
        # Eine schon sprechende, verdrängte Ansage darf ihren Ablauf erst nach
        # der neuen freigeben, sonst schneidet der nächste Morseton sie ab.
        import time
        import numpy as np
        from morsetrainer.core import speech
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)  # Reiter-Ansage beim Aufbau ausklingen lassen
        done = {}
        with mock.patch.object(speech.speaker, "synth",
                               lambda text: np.zeros(self.announcer.SAMPLE_RATE, dtype=np.float32)):
            self.app.announcer.say("Erste.", then=lambda: done.setdefault("first", time.monotonic()))
            self.assertTrue(self.pump_until(lambda: self.app.announcer.speaking_until > time.time()))
            second = time.monotonic()
            self.app.announcer.say("Zweite.", then=lambda: done.setdefault("second", time.monotonic()))
            self.assertTrue(self.pump_until(lambda: len(done) == 2, timeout=5))
        self.assertGreaterEqual(done["first"] - second, 1.0 + self.announcer.AFTER_SPEECH_MS / 1000 - 0.05)
        self.assertLessEqual(abs(done["first"] - done["second"]), 0.2)

    def test_long_announcement_starts_with_the_first_sentence(self):
        from morsetrainer.widgets import announcer
        self.assertEqual(announcer._chunks("Richtig."), ["Richtig."])
        text = "Statistik. " + " ".join(f"Satz Nummer {n} mit etwas Inhalt." for n in range(8))
        chunks = announcer._chunks(text)
        self.assertEqual(chunks[0], "Statistik.")
        self.assertTrue(all(len(chunk) <= announcer.CHUNK_CHARS for chunk in chunks[1:]))
        self.assertEqual(" ".join(chunks), text)
        done = []
        self.app.announcer.say(text, then=lambda: done.append(True), force=True)
        self.assertTrue(self.pump_until(lambda: done, timeout=5))
        self.assertEqual([s for s in self.said if not s.startswith("Reiter")], chunks)
        self.assertEqual(len(self.played), len(chunks) + sum(s.startswith("Reiter") for s in self.said))

    def test_f9_toggles_and_confirms(self):
        self.app._dispatch_key(mock.Mock(keysym="F9", char=""))
        self.assertTrue(self.app.announcer.enabled())
        self.assertTrue(self.pump_until(lambda: "Ansage an." in self.said))
        self.app._dispatch_key(mock.Mock(keysym="F9", char=""))
        self.assertFalse(self.app.announcer.enabled())
        self.assertTrue(self.pump_until(lambda: "Ansage aus." in self.said))
        self.assertIs(self.app._shared_settings()["announce"], False)

    def test_f11_reads_tab_and_status_even_when_off(self):
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertTrue(self.said[0].startswith("Einzelzeichen. Bereit"), self.said)

    def test_group_answers_are_spelled(self):
        from tests.test_modes import GroupEvaluationTest
        self.app.announcer.var.set(True)
        group = self.mode("Gruppen")
        helper = GroupEvaluationTest()
        helper.group = group
        group.give_up_var.set(1)
        group.style_var.set("copy")
        group.start()
        helper._answer("KMU", "KMM")
        self.assertTrue(self.pump_until(lambda: any("Gesendet" in s for s in self.said)))
        self.assertIn("Falsch. Gesendet: Ka, Emm, U. Getippt: Ka, Emm, Emm.", self.said)
        group.stop()
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Durchgang beendet.") for s in self.said)))

    def test_single_char_error_is_named(self):
        import time
        self.app.announcer.var.set(True)
        # Reiter-Ansage beim Aufbau ausklingen lassen: sie käme sonst
        # dazwischen, und der Ablauf wartet zu Recht, bis sie zu Ende ist.
        self.pump_until(lambda: False, timeout=0.5)
        self.said.clear()
        single = self.mode("Einzelzeichen")
        single.start()
        single.current_char, single.voice, single.waiting_for_input, single.replayed = "K", (20, 600), True, False
        single.play_start_time = time.time() - 0.5
        single.on_key(type("E", (), {"keysym": "m", "char": "m"})())
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertEqual(self.said[0], "Falsch. Ka, nicht Emm.")
        self.assertTrue(self.pump_until(lambda: single.correcting))  # Klangvergleich kommt danach
        single.stop()


class ContrastTest(AppTestCase):
    def test_palettes_have_the_same_keys_and_strong_contrast(self):
        light, contrast = theme.PALETTES["light"], theme.PALETTES["contrast"]
        self.assertEqual(set(light), set(contrast))

        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def ratio(a, b):
            high, low = sorted((luminance(a), luminance(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)

        # Text auf seinem Grund mindestens 7:1 (WCAG AAA).
        for fg, bg in (("TEXT", "BG"), ("MUTED", "BG"), ("TEXT", "BUTTON"), ("ACCENT", "BG"), ("SURFACE", "ACCENT"),
                       ("OK", "BG"), ("ERROR", "BG"), ("TEXT", "SELECT"), ("TEXT", "OK_BG"), ("TEXT", "ERROR_BG")):
            self.assertGreaterEqual(ratio(contrast[fg], contrast[bg]), 7, (fg, bg))
        for color in contrast["STATION_COLORS"]:
            self.assertGreaterEqual(ratio(color, contrast["SURFACE"]), 7, color)

    def test_chosen_at_start_and_saved(self):
        self.assertEqual(theme.PALETTE, "light")
        self.app.contrast_var.set(True)
        self.app._contrast_toggled()
        self.assertIn("Neustart", self.app.contrast_hint_var.get())
        self.assertIs(self.app._shared_settings()["contrast"], True)
        try:
            self.app.saved_state = {"shared": {"contrast": True}}
            with mock.patch.object(type(self.app), "_load_state", lambda app: {"shared": {"contrast": True}}):
                root = tk.Tk()
                root.withdraw()
                try:
                    from morsetrainer import app as app_module
                    second = app_module.MorseTrainerApp(root)
                    self.assertEqual(theme.PALETTE, "contrast")
                    self.assertEqual(theme.BG, "#000000")
                    self.assertTrue(second.contrast_var.get())
                    self.assertEqual(ttk.Style(root).lookup("Accent.TButton", "foreground"), "#000000")
                    for mode in second.modes:
                        if hasattr(mode, "on_close"):
                            mode.on_close()
                finally:
                    root.destroy()
        finally:
            theme.set_palette("light")


class KeyboardTest(AppTestCase):
    """Alles per Tastatur: Tab erreicht Knöpfe und Schalter, Kürzel für
    Reiter und Bandbedingungen."""

    def test_tab_reaches_buttons_and_check_boxes(self):
        # Knöpfe und Schalter dürfen nicht takefocus 0 haben, sonst erreicht Tab sie nicht.
        mode = self.mode("Gruppen")
        for widget in (mode.start_button, self.app.more_button,
                       ttk.Checkbutton(self.root), ttk.Radiobutton(self.root)):
            self.assertNotEqual(str(widget.cget("takefocus")), "0", widget)

    def test_mouse_click_does_not_move_focus_to_buttons(self):
        body = self.root.tk.eval("info body ::ttk::clickToFocus")
        self.assertIn("TButton", body)

    def test_space_on_a_focused_button_is_not_an_answer(self):
        mode = self.app._active_mode()
        button = mode.start_button
        with mock.patch.object(mode, "on_key") as on_key:
            self.app._dispatch_key(mock.Mock(keysym="space", char=" ", widget=button))
            on_key.assert_not_called()
            self.app._dispatch_key(mock.Mock(keysym="k", char="k", widget=button))
            on_key.assert_called_once()  # Buchstaben gehen weiter an den Reiter
            on_key.reset_mock()
            notes = tk.Text(self.root)
            self.app._dispatch_key(mock.Mock(keysym="k", char="k", widget=notes))
            on_key.assert_not_called()  # Tippen ins Notizfeld ist keine Antwort

    def test_alt_number_selects_tab_unless_locked(self):
        self.app.select_tab(1)
        self.assertEqual(self.app._tab_name(), "Gruppen")
        self.app.select_tab(8)
        self.assertEqual(self.app._tab_name(), "Netzwerk")
        self.app._lock_tabs()
        self.app.select_tab(0)
        self.assertEqual(self.app._tab_name(), "Netzwerk")  # gesperrt während eines Durchgangs
        self.assertTrue(self.root.bind_all("<Alt-Key-1>"))
        self.assertTrue(self.root.bind_all("<Control-b>"))

    def test_mac_quit_preferences_and_function_key_substitutes(self):
        # Mac (H1–H3 der Plattformprüfung 2.38): Cmd+Q ohne ::tk::mac::Quit
        # beendete ohne Speichern; F9/F11/F12 sind dort Medientasten.
        calls = []
        with mock.patch.object(self.app, "on_close", lambda: calls.append("close")), \
                mock.patch.object(self.app, "open_settings", lambda: calls.append("settings")), \
                mock.patch.object(self.app, "toggle_announce", lambda: calls.append("announce")), \
                mock.patch.object(self.app, "read_status", lambda: calls.append("status")), \
                mock.patch.object(self.app, "_start_daily", lambda: calls.append("daily")):
            self.app._bind_mac_keys()
        self.root.tk.call("::tk::mac::Quit")
        self.root.tk.call("::tk::mac::ShowPreferences")
        self.assertEqual(calls, ["close", "settings"])
        for letter in "AWT":
            self.assertTrue(self.root.bind_all(f"<Command-Shift-{letter}>"), letter)

    def test_footer_comes_last_in_tab_order(self):
        # Tab folgt der Stapelreihenfolge (winfo children von unten nach oben).
        order = [str(w) for w in self.root.winfo_children()]
        footer = order.index(str(self.app.footer))
        self.assertGreater(footer, order.index(str(self.app.notebook)))
        self.assertGreater(footer, order.index(str(self.app.daily_bar.frame)))

    def test_tab_leaves_text_fields(self):
        self.assertIn("break", self.root.bind_class("Text", "<Tab>"))


class SettingsWindowTest(AppTestCase):
    """Einmalige Einstellungen im eigenen Fenster, Übungsoptionen bleiben
    über den Reitern."""

    def test_open_and_close_keeps_values(self):
        window = self.app.settings_window
        self.assertEqual(window.state(), "withdrawn")
        self.root.deiconify()  # ein transient-Fenster zeigt sich nur mit seinem Hauptfenster
        self.assertIs(self.app.zoom_box.winfo_toplevel(), window)
        self.assertIs(self.app.language_box.winfo_toplevel(), window)
        self.app.open_settings()
        # Der Fenstermanager zeigt es nicht sofort (unter Last etwas später).
        end = time.monotonic() + 2
        while window.state() != "normal" and time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(window.state(), "normal")
        self.app.station_call_var.set("DL4YM")
        window.event_generate("<Escape>", when="now")
        self.assertEqual(window.state(), "withdrawn")
        self.app.open_settings()
        self.assertEqual(self.app.station_call_var.get(), "DL4YM")
        self.assertEqual(self.app._shared_settings()["station_call"], "DL4YM")
        self.app.close_settings()
        self.root.withdraw()

    def test_shortcut_and_practice_options_stay_above_tabs(self):
        self.assertTrue(self.root.bind_all("<Control-comma>"))
        more = {str(w) for w in self.app.more_frame.winfo_children()}
        texts = []

        def collect(widget):
            for child in widget.winfo_children():
                try:
                    texts.append(str(child.cget("text")))
                except tk.TclError:
                    pass
                collect(child)
        collect(self.app.more_frame)
        self.assertTrue(more)
        self.assertTrue(any("Farnsworth" in t for t in texts))
        self.assertFalse(any("Schriftgröße" in t or "Sichern" in t for t in texts))


class AnnouncerModesTest(AnnouncerTest):
    """Ansage in QSO, Contest und Statistik."""

    def test_contest_speaks_log_errors_into_the_mix(self):
        import numpy as np
        from morsetrainer.core import band, qso_text
        from morsetrainer.modes import run_mode
        self.app.announcer.var.set(True)
        self.app.station_call_var.set("DL0ABC")
        contest = self.mode("Contest")
        for patch in (mock.patch.object(run_mode.Mixer, "start"), mock.patch.object(run_mode.Mixer, "stop")):
            patch.start()
            self.addCleanup(patch.stop)
        contest.start()
        caller = run_mode.Caller(call="DL1ABC", exchange="14", exchange_kind=qso_text.TEXT, station=1,
                                 wpm=20, freq=600.0, strength=1.0, patience=3)
        caller.state = "worked"
        contest.callers = [caller]
        contest.exchange_sent_to = "DL1ABD"
        contest.call_var.set("DL1ABD")
        contest.exch_var.set("14")
        contest._send("tu")
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Busted") for s in self.said)))
        self.assertIn("Busted. Richtig: Delta, Lima, Eins, Alfa, Bravo, Tschali.", self.said)
        self.assertTrue(self.pump_until(lambda: any(src[2] == band.VOICE for src in contest.mixer.sources)))
        contest.stop()
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Contest beendet. 0 von 1") for s in self.said)))
        # Die Sprache läuft ungefiltert wie der Mithörton.
        conditions = band.conditions({"levels": {"qrn": 0.01}, "gain": 1.0, "filter": 250}, 600)
        tone = np.full(960, 0.3, dtype=np.float32)
        self.assertAlmostEqual(float(np.max(conditions.mix([(tone, band.VOICE)], 960))), 0.3, delta=0.01)

    def test_qso_quiz_names_fields_and_reads_the_result(self):
        from morsetrainer.core import qso_text
        from morsetrainer.modes.qso_quiz import QuizPanel
        self.app.announcer.var.set(True)
        qso = mock.Mock(quiz_columns=("Station 1", "Station 2"),
                        quiz_rows=(("Rufzeichen", (("DL1ABC", qso_text.TEXT), ("DK2XY", qso_text.TEXT))),
                                   ("Name", (("Hans", qso_text.TEXT), ("Eva", qso_text.TEXT)))))
        quiz = QuizPanel(self.root, on_checked=lambda correct, total: None)
        quiz.reset(qso)
        quiz._announce_field((1, 0))
        self.assertTrue(self.pump_until(lambda: "Name, Station 1." in self.said))
        for key, typed in (((0, 0), "DL1ABC"), ((0, 1), "DK2XY"), ((1, 0), "Hans"), ((1, 1), "Ute")):
            quiz.vars[key].set(typed)
        quiz.check()
        self.assertEqual(quiz.spoken_result(), "3 von 4 richtig. Richtig wäre: Name, Station 2: Eva.")
        quiz._announce_field((1, 1))
        self.assertTrue(self.pump_until(lambda: "Name, Station 2. Falsch. Richtig wäre: Eva." in self.said))

    def test_statistics_are_read_out(self):
        text = self.app.statistics_spoken()
        self.assertTrue(text.startswith("Statistik. Noch keine Durchgänge."), text)
        self.assertIn("Lernkartei", text)
        self.app.select_tab(len(self.app.notebook.tabs()) - 1)
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Statistik.") for s in self.said)))

    def test_table_row_is_read_with_keyboard_focus_only(self):
        from morsetrainer.widgets import announcer
        self.app.announcer.var.set(True)
        tree = ttk.Treeview(self.root, columns=("call", "ok"), show="headings")
        tree.heading("call", text="Call")
        tree.heading("ok", text="Ergebnis")
        row = tree.insert("", "end", values=("DL1ABC", "Busted"))
        tree.selection_set(row)
        event = mock.Mock(widget=tree)
        with mock.patch.object(tree, "focus_get", return_value=None):
            announcer._read_row(event)  # beim Auffrischen: still
        with mock.patch.object(tree, "focus_get", return_value=tree):
            announcer._read_row(event)
        self.assertTrue(self.pump_until(lambda: "Call: DL1ABC. Ergebnis: Busted." in self.said))
        self.assertEqual(sum(s.startswith("Call:") for s in self.said), 1)


class VoiceLanguageTest(AppTestCase):
    """Ansage in der Sprache der Oberfläche; ohne Stimme ein Fehlerton."""

    def test_english_spelling(self):
        from morsetrainer.core import speech
        self.assertEqual(speech.spoken("KM U", lang="en"), "kay, em. you")
        self.assertEqual(speech.spoken("DL1ABC", "nato", lang="en"),
                         "Delta, Lima, one, Alfa, Bravo, Charlie")
        self.assertEqual(speech.spoken("DL1", "nato"), "Delta, Lima, Eins")  # deutsch unverändert

    def test_voice_follows_interface_language(self):
        from morsetrainer import i18n
        from morsetrainer.core import speech
        from morsetrainer.widgets import announcer
        self.assertIs(announcer.Announcer.speaker(), speech.speaker)
        with mock.patch.object(i18n, "LANG", "en"):
            self.assertEqual(announcer.Announcer.speaker().lang, "en")
            self.assertEqual(announcer.spell_nato("K1"), "Kilo, one")
            self.assertEqual(announcer.spell(""), "nichts")  # tr() bleibt in den Tests deutsch
        self.assertEqual(speech.speaker_for("xx").lang, "de")

    def test_missing_voice_plays_error_tone(self):
        from morsetrainer.widgets import announcer
        reason = "Sprachausgabe nicht verfügbar: Piper ist nicht installiert (pip install piper-tts)."
        with mock.patch.object(self.app.announcer, "available", return_value=reason), \
                mock.patch.object(announcer.sfx, "play_error") as tone:
            self.app._dispatch_key(mock.Mock(keysym="F9", char=""))
            self.assertEqual(tone.call_count, 1)
            self.assertEqual(self.app._active_mode().status_var.get(), reason)
            self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
            self.assertEqual(tone.call_count, 2)


class FocusAnnounceTest(AnnouncerTest):
    """Fokus-Ansage: mit Tab ins Element gesprungen sagt es, was es ist und
    wie es steht."""

    def test_settings_window_elements_are_described(self):
        from morsetrainer.widgets import announcer
        describe = announcer.describe
        self.assertEqual(describe(self.app.language_box), "Sprache / Language, Auswahl, Deutsch.")
        self.assertEqual(describe(self.app.zoom_box), "Schriftgröße, Auswahl, 100 %.")

    def test_roles_values_and_labels(self):
        from morsetrainer.widgets import announcer
        describe = announcer.describe
        frame = ttk.Frame(self.root)
        check_var = tk.BooleanVar(value=True)
        check = ttk.Checkbutton(frame, text="Hoher Kontrast", variable=check_var)
        ttk.Label(frame, text="Rufzeichen:").pack()
        entry = ttk.Entry(frame)
        entry.insert(0, "DL4YM")
        button = ttk.Button(frame, text="Sichern …", state="disabled")
        self.assertEqual(describe(check), "Hoher Kontrast, Schalter, an.")
        check_var.set(False)
        self.assertEqual(describe(check), "Hoher Kontrast, Schalter, aus.")
        self.assertEqual(describe(entry), f"Rufzeichen, Eingabefeld, {announcer.spell('DL4YM')}.")
        self.assertEqual(describe(button), "Sichern, Knopf, nicht verfügbar.")
        # Zeile im Raster: Beschriftung aus derselben Zeile, nicht aus der davor.
        grid = ttk.LabelFrame(self.root, text="Gruppe")
        ttk.Label(grid, text="Erste:").grid(row=0, column=0)
        ttk.Label(grid, text="30 %").grid(row=0, column=2)
        ttk.Label(grid, text="Zweite:").grid(row=1, column=0)
        spin = ttk.Spinbox(grid, from_=0, to=9)
        spin.set(4)
        spin.grid(row=1, column=1)
        self.assertEqual(describe(spin), "Zweite, Zahlenfeld, 4.")
        # Feld ohne Beschriftung: Titel der Gruppe; fester Name mit Wert geht vor.
        lonely = ttk.Entry(grid)
        lonely.grid(row=5, column=0)
        self.assertEqual(describe(lonely), "Gruppe, Eingabefeld, leer.")
        announcer.name(lonely, "Antwort", value=lambda: "bereit")
        self.assertEqual(describe(lonely), "Antwort, Eingabefeld, bereit.")

    def test_header_and_band_window(self):
        from morsetrainer.widgets import announcer
        texts = []

        def walk(widget):
            for child in widget.winfo_children():
                if child.winfo_class() in announcer.ROLES:
                    texts.append(announcer.describe(child))
                walk(child)
        walk(self.app.root)
        self.assertIn("Tempo, Zahlenfeld, 20 WPM.", texts)
        self.assertIn("Tonhöhe, Zahlenfeld, 600 Hz.", texts)
        self.assertFalse([t for t in texts if "PY_VAR" in t], texts)
        self.app.band_settings.open_window()
        try:
            texts.clear()
            walk(self.app.band_settings.window)
            self.assertTrue(any(t.startswith("Bandrauschen, Regler, S/N") for t in texts), texts)
            self.assertIn("Lautstärke der Störgeräusche, Regler, 100 %.", texts)
        finally:
            self.app.band_settings.close_window()

    def test_traverse_in_announces_but_program_focus_does_not(self):
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.2)
        self.said.clear()
        box = self.app.zoom_box
        box.focus_set()  # vom Programm gesetzt: still
        self.pump_until(lambda: False, timeout=0.2)
        self.assertEqual(self.said, [])
        box.event_generate("<<TraverseIn>>")  # mit Tab hineingesprungen
        self.assertTrue(self.pump_until(lambda: "Schriftgröße, Auswahl, 100 Prozent." in self.said))



class EveningSummaryAnnounceTest(AnnouncerTest):
    def test_evening_summary_is_read_in_sentences(self):
        from morsetrainer.core import daily
        from morsetrainer.widgets import announcer
        from morsetrainer.widgets.daily_panel import EveningSummary
        self.app.announcer.var.set(True)
        comparison = {"better": [{"kind": "char", "char": "K", "before": 0.52, "now": 0.41},
                                 {"kind": "groups", "wpm": 20, "before": 0.6, "now": 0.75}]}
        outlook = {"lesson": 5, "missing": 4}
        summary = EveningSummary(self.root, [daily.DABEI, daily.SAUBER], comparison, outlook,
                                 offer=(daily.CONFUSIONS, "SH"), on_extra=lambda offer: None, week_stars=7,
                                 seals=["QRN-fest, Stufe 1"])
        text = summary.spoken
        self.assertTrue(text.startswith("Tagesübung geschafft. 2 von 3 Sternen: Dabei, Sauber. "), text)
        self.assertIn("7 von", text)
        self.assertIn("Ka kommt schneller, von 0,52 auf 0,41 Sekunden", text)
        self.assertIn("Gruppen bei 20 WPM von 60 auf 75 Prozent beim ersten Versuch", text)
        self.assertIn("Neues Siegel: QRN-fest, Stufe 1", text)
        self.assertIn("Enter: Fertig. Mit Tab: Noch", text)
        self.assertNotIn("★", text)
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Tagesübung geschafft.") for s in self.said)))
        summary.close()

    def test_symbols_become_words(self):
        from morsetrainer.widgets import announcer
        self.assertEqual(announcer.speakable("84 % → 90 %"), "84 Prozent auf 90 Prozent")
        self.assertEqual(announcer.speakable("Abgebrochen – deine Sterne bleiben."), "Abgebrochen, deine Sterne bleiben.")
        self.assertEqual(announcer.speakable("✓ KM"), "richtig KM")
        self.assertEqual(announcer.speakable("≥ 50 Zeichen, ≤ 3 Fehler"), "mindestens 50 Zeichen, höchstens 3 Fehler")
        self.assertEqual(announcer.speakable("Warte auf den Trainer…"), "Warte auf den Trainer")



class DiplomaAnnounceTest(AnnouncerTest):
    def test_diploma_window_is_read_and_print_buttons_are_named(self):
        from datetime import date
        from morsetrainer.core import awards
        from morsetrainer.widgets import announcer
        from morsetrainer.widgets import awards_panel as panel
        self.app.announcer.var.set(True)
        window = panel.DiplomaWindow(self.root, [("koch", 2, date(2026, 10, 4)), ("qrn", 0, date(2026, 10, 5))],
                                     tk.StringVar(value="DL4YM"), tk.StringVar(value="Maik"))
        koch = panel.seal_name(awards.BY_KEY["koch"], 2)
        self.assertTrue(window.spoken.startswith("Neue Siegel. " + koch + ". "), window.spoken)
        self.assertIn("Erreicht am 04.10.2026", window.spoken)
        self.assertTrue(window.spoken.endswith("Escape schließt."))
        buttons = []

        def walk(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TButton" and str(child.cget("text")) == "Drucken":
                    buttons.append(announcer.describe(child))
                walk(child)
        walk(window.window)
        self.assertEqual(buttons[0], f"Drucken: {koch}, Knopf.")
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Neue Siegel.") for s in self.said)))
        with mock.patch.object(panel, "print_diploma", return_value=("Im Browser geöffnet, dort drucken: /x", True)):
            window._print(awards.BY_KEY["koch"], 2, date(2026, 10, 4))
        self.assertTrue(self.pump_until(lambda: "Diplom im Browser geöffnet." in self.said))
        window.close()


class ListenAnnounceTest(AnnouncerTest):
    """Reiter Sprechen: angesagt wird nur, was man sonst nur sieht."""

    def test_start_problem_end_and_progress(self):
        from morsetrainer.modes import listen_mode
        self.app.announcer.var.set(True)
        listen = self.mode("Sprechen")
        with mock.patch.object(listen, "_options", lambda: listen.status_var.set("Kein Zeichensatz") or None):
            listen.start()
        self.assertTrue(self.pump_until(lambda: "Kein Zeichensatz" in self.said))
        # Fortschritt für F11 als „3 von 20“
        self.app.select_tab(self.app.mode_titles.index("Sprechen"))
        listen.status_var.set("Hör zu …")
        listen.progress_var.set("3/20")
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: any("Hör zu. 3 von 20" in s for s in self.said)), self.said)
        # Ende eines Durchgangs
        with mock.patch.object(listen_mode.audio, "play"):
            listen.running, listen.done, listen.total = True, 20, 20
            listen._next_item()
        self.assertTrue(self.pump_until(lambda: "Fertig: 20 Einträge." in self.said))

    def test_export_result_without_path(self):
        self.app.announcer.var.set(True)
        listen = self.mode("Sprechen")
        listen.exporting = True
        listen.export_result = "Gespeichert: /home/maik/übung.mp3 (12 Min.)"
        listen.export_spoken = "MP3 gespeichert, 12 Minuten."
        listen._watch_export(20)
        self.assertTrue(self.pump_until(lambda: "MP3 gespeichert, 12 Minuten." in self.said))
        self.assertFalse([s for s in self.said if "/home" in s])
