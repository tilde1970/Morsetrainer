"""Barrierefreiheit: Schriftgröße im Programm (Strg+Plus/Minus/0)."""
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
