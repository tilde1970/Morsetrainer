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
        self.assertEqual(theme.zoom_step(100, -1), 100)


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
        # Bis 2.37 hatten Knöpfe und Schalter takefocus 0 (per Tab nicht erreichbar).
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
