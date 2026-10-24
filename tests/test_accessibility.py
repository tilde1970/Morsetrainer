"""Barrierefreiheit: Schriftgröße, Sprachansage, hoher Kontrast, Tastatur und Einstellungsfenster."""
import sys
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import i18n
from morsetrainer.widgets import theme
from tests.test_modes import AppTestCase, app_module


def announcer_targets(widget):
    """Alle Eingabefelder unter `widget`."""
    for child in widget.winfo_children():
        if child.winfo_class() == "TEntry":
            yield child
        yield from announcer_targets(child)


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

    def test_zoom_keys_are_announced(self):
        from morsetrainer.widgets import announcer
        with mock.patch.object(announcer, "say") as say:
            self.app.zoom(1)
            self.app.zoom(0)
            for _ in range(len(theme.ZOOM_STEPS)):
                self.app.zoom(-1)
        spoken = [call.args[0] for call in say.call_args_list]
        self.assertEqual(spoken[:2], ["Schriftgröße 110 %.", "Schriftgröße 100 %."])
        self.assertEqual(spoken[-1], "Schriftgröße 75 %, kleinste Stufe.")
        self.app.zoom(0)

    def test_zoom_announcement_does_not_cut_a_long_tone(self):
        from morsetrainer.core import audio
        from morsetrainer.widgets import announcer
        with mock.patch.object(announcer, "say") as say, mock.patch.object(audio, "tone_remaining", return_value=6.0):
            self.app.zoom(1)
        say.assert_not_called()  # die Größe ändert sich sichtbar, der Ton läuft weiter
        self.assertEqual(theme.scale(), 110)
        with mock.patch.object(announcer, "say") as say, mock.patch.object(audio, "tone_remaining", return_value=2.0):
            self.app.zoom(1)
        say.assert_called_once()  # kurze Töne wartet die Ansage selbst ab
        self.app.zoom(0)

    def test_arrow_keys_work_after_tabbing_into_a_table(self):
        # Ohne aktuelle Zeile täten die Pfeiltasten nichts (Diplome, Statistik).
        tree = ttk.Treeview(self.root, columns=("a",), show="headings")
        tree.pack()
        for i in range(3):
            tree.insert("", "end", values=(i,))
        self.root.deiconify()
        tree.focus_force()
        self.root.update()
        first = tree.get_children()[0]
        self.assertEqual((tree.focus(), tree.selection()), (first, (first,)))
        tree.event_generate("<KeyPress-Down>", when="now")
        self.assertEqual(tree.selection(), (tree.get_children()[1],))
        tree.destroy()
        self.root.withdraw()

    def test_tall_tables_show_fewer_rows_at_large_font(self):
        tree = ttk.Treeview(self.root, columns=("a",), show="headings", height=12)
        tree.heading("a", text="a")
        tree.pack()
        theme.fit_columns(tree, {"a": 60})
        small = ttk.Treeview(self.root, columns=("a",), show="headings", height=3)
        small.heading("a", text="a")
        small.pack()
        theme.fit_columns(small, {"a": 60})
        self.addCleanup(tree.destroy)
        self.addCleanup(small.destroy)
        self.app.set_font_scale(200)
        self.assertEqual((int(tree.cget("height")), int(small.cget("height"))), (6, 3))
        self.app.set_font_scale(100)
        self.assertEqual(int(tree.cget("height")), 12)

    def test_tree_rows_follow_the_zoom_from_the_wanted_height(self):
        self.app.set_font_scale(150)
        self.assertEqual((theme.tree_rows(20), theme.tree_rows(3)), (13, 3))
        self.app.set_font_scale(200)
        self.assertEqual((theme.tree_rows(7), theme.tree_rows(5), theme.tree_rows(20)), (4, 4, 10))
        self.app.set_font_scale(100)
        self.assertEqual(theme.tree_rows(20), 20)

    def test_table_height_set_by_the_program_survives_a_zoom_change(self):
        tree = ttk.Treeview(self.root, columns=("a",), show="headings", height=6)
        tree.heading("a", text="a")
        tree.pack()
        theme.fit_columns(tree, {"a": 60})
        self.addCleanup(tree.destroy)
        theme.set_tree_rows(tree, 12)
        self.assertEqual(int(tree.cget("height")), 12)
        self.app.set_font_scale(200)
        self.assertEqual(int(tree.cget("height")), 6)
        theme.set_tree_rows(tree, 12)  # Auffrischen bei großer Schrift: gleich gekürzt
        self.assertEqual(int(tree.cget("height")), 6)
        self.app.set_font_scale(100)
        self.assertEqual(int(tree.cget("height")), 12)

    def test_shortened_table_says_which_rows_are_missing(self):
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        tree = ttk.Treeview(window, columns=("a",), show="headings", height=4)
        tree.heading("a", text="a")
        tree.pack(fill="x")
        theme.fit_columns(tree, {"a": 60})
        for i in range(15):
            tree.insert("", "end", values=(i,))
        window.update()
        more = tree._mt_more
        self.assertEqual(more.winfo_manager(), "pack")
        self.assertIn("Zeilen 1 bis 4 von 15", str(more.cget("text")))
        tree.yview_moveto(1.0)
        window.update()
        self.assertIn("von 15", str(more.cget("text")))
        self.assertNotIn("Zeilen 1 bis", str(more.cget("text")))
        tree.configure(height=15)
        window.update()
        self.assertEqual(more.winfo_manager(), "")  # alles zu sehen: keine Zeile

    def test_tables_and_wrapped_texts_grow(self):
        row = int(ttk.Style(self.root).lookup("Treeview", "rowheight"))
        label = theme.hint(self.root, text="x", wrap=400)
        self.app.set_font_scale(150)
        self.assertGreater(int(ttk.Style(self.root).lookup("Treeview", "rowheight")), row)
        self.assertEqual(int(float(str(label.cget("wraplength")))), 600)
        self.app.set_font_scale(100)
        self.assertEqual(int(float(str(label.cget("wraplength")))), 400)

    def test_arrows_scrollbars_and_sliders_grow(self):
        style = ttk.Style(self.root)

        def size(widget, option="arrowsize"):
            return int(style.lookup(widget, option))
        self.assertEqual(size("TScrollbar"), theme.ARROW_SIZE)
        self.app.set_font_scale(200)
        for widget in ("TSpinbox", "TCombobox", "TScrollbar", "TScale"):
            self.assertEqual(size(widget), 2 * theme.ARROW_SIZE, widget)
        self.assertEqual(size("TScale", "sliderlength"), 2 * theme.SLIDER_LENGTH)
        self.app.set_font_scale(100)
        self.assertEqual(size("TScale", "sliderlength"), theme.SLIDER_LENGTH)

    def test_windows_with_own_font_start_at_the_program_size(self):
        # Ganze Auswertung (Kontinuierlich) und Auflösung (Netzwerk) haben
        # eigenes A−/A+, beginnen aber in der eingestellten Schriftgröße.
        self.assertEqual(theme.scaled_size(18, 10, 60), 18)
        self.app.set_font_scale(200)
        self.assertEqual(theme.scaled_size(18, 10, 60), 36)
        self.assertEqual(theme.scaled_size(40, 10, 60), 60)  # nicht über die Obergrenze
        mode = self.mode("Kontinuierlich")
        mode.full_rows = []
        mode.show_full()
        try:
            self.assertEqual(int(mode.full_font.cget("size")), 36)
        finally:
            mode.close_full()
        self.app.set_font_scale(100)

    def test_choice_rows_wrap_at_200_percent(self):
        # Sechs Inhalte in Am Stück passten bei großer Schrift nicht in eine Zeile.
        self.root.geometry("1024x600")
        self.app.set_font_scale(200)
        try:
            for title in ("Kontinuierlich", "Wörter", "Sprechen"):
                self.app.show_mode(title)
                row = self.mode(title).content_buttons
                for _ in range(5):
                    self.root.update()
                right = max(b.winfo_rootx() + b.winfo_width() for b in row.buttons)
                self.assertLessEqual(right, row.master.winfo_rootx() + row.master.winfo_width(), title)
                self.assertTrue(all(b.winfo_width() >= b.winfo_reqwidth() for b in row.buttons), title)
            self.assertGreater(len(self.mode("Kontinuierlich").content_buttons.rows), 1)
        finally:
            self.app.set_font_scale(100)
        for _ in range(5):
            self.root.update()
        self.assertEqual(len(self.mode("Kontinuierlich").content_buttons.rows), 1)

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


class AnnouncerCase(AppTestCase):
    """Grundlage der Ansage-Tests: Stimme und Ausgabe ersetzt, gesagte Texte
    in self.said. Ohne eigene Tests, damit Unterklassen keine erben."""

    def setUp(self):
        super().setUp()
        import numpy as np
        from morsetrainer.core import speech
        from morsetrainer.widgets import announcer
        self.announcer = announcer
        self.said, self.played = [], []
        self.speech_patches = [
            mock.patch.object(speech.speaker, "available", lambda: None),
            # Geladen vortäuschen: sonst lüde die Ansage die echte Stimme im
            # Hintergrund, und ohne Piper bliebe ein Fehler an ihr hängen.
            mock.patch.object(speech.speaker, "voice", object()),
            mock.patch.object(speech.speaker, "synth",
                              lambda text, rate=1.0: (self.said.append(text), np.zeros(4800, dtype=np.float32))[1]),
            mock.patch.object(announcer.audio, "play_quietly", lambda samples: self.played.append(len(samples))),
        ]
        for patch in self.speech_patches:
            patch.start()

    def tearDown(self):
        for patch in self.speech_patches:
            patch.stop()
        super().tearDown()

    def pump_until(self, condition, timeout=3.0):
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end and not condition():
            self.root.update()
            time.sleep(0.01)
        return condition()


class AnnouncerTest(AnnouncerCase):
    """Sprachansage: Ergebnis, Reiter und Status mit der eingebauten Stimme;
    der Ablauf geht erst nach der Ansage weiter."""

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
                               lambda text, rate=1.0: np.zeros(self.announcer.SAMPLE_RATE, dtype=np.float32)):
            start = time.monotonic()
            self.app.announcer.say("Eine Sekunde lang.", then=lambda: done.append(time.monotonic()))
            self.assertTrue(self.pump_until(lambda: done, timeout=4))
        self.assertGreaterEqual(done[0] - start, 1.0 + self.announcer.AFTER_SPEECH_MS / 1000 - 0.05)

    def test_number_fields_say_their_unit(self):
        # „Lösung zeigen nach [3] Fehlversuchen“: die Einheit dahinter gehört
        # zum Wert; „von [2] bis [5]“: „bis“ ist die Beschriftung des nächsten Feldes.
        from morsetrainer.widgets import announcer

        def spinbox_for(variable, widget=None):
            for child in (widget or self.root).winfo_children():
                if child.winfo_class() == "TSpinbox" and child.cget("textvariable") == str(variable):
                    return child
                found = spinbox_for(variable, child)
                if found is not None:
                    return found
            return None
        give_up = spinbox_for(self.mode("Wörter").give_up_var)
        self.mode("Wörter").give_up_var.set(1)
        self.assertTrue(announcer.describe(give_up).endswith("einem Fehlversuch."))  # nicht „eins Fehlversuchen“
        self.mode("Wörter").give_up_var.set(4)
        self.assertEqual(announcer._value(give_up), "4 Fehlversuchen")  # auch beim Hoch-/Runterzählen
        boxes = []

        def collect(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TSpinbox":
                    boxes.append(child)
                collect(child)
        collect(self.root)
        group_from = next(box for box in boxes if announcer._label(box) == "Gruppenlänge von")
        self.assertEqual(announcer._unit_after(group_from), "")

    def test_typing_in_settings_fields_is_spoken(self):
        # Wie ein Screenreader: neue Zeichen buchstabiert, Gelöschtes mit
        # „gelöscht“; im Antwortfeld still (sonst bräche der Morseton ab).
        from morsetrainer.widgets import announcer
        self.assertEqual(announcer.spell_chars("K.,/ 0"), "Ka, Punkt, Komma, Schrägstrich, Leerzeichen, Null")
        self.assertEqual(announcer.change_text("KMR", "KMRS"), "Ess")
        self.assertEqual(announcer.change_text("KMRS", "KMS"), "Err gelöscht")
        self.assertEqual(announcer.change_text("650", "7"), "Sieben")  # Auswahl ersetzt
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        entry = next(w for w in announcer_targets(self.root) if str(w) in announcer._echo_widgets
                     and w.cget("textvariable") == str(self.app.charset_var))
        self.app.charset_var.set("KM")
        announcer._echo_start(entry)
        self.app.charset_var.set("KMR")
        announcer._echo_key(mock.Mock(widget=entry, keysym="r"))
        self.assertTrue(self.pump_until(lambda: "Err" in self.said))
        self.assertIn("Zeichen", announcer.describe(entry))
        self.assertIn("Ka, Emm, Err", announcer.describe(entry))  # beim Hineinspringen buchstabiert
        answer = self.mode("Gruppen").entry
        self.assertNotIn(str(answer), announcer._echo_widgets)
        answer.state(["!disabled"])
        answer.insert(0, "K")
        announcer._echo_start(answer)
        answer.insert("end", "M")
        said = len(self.said)
        announcer._echo_key(mock.Mock(widget=answer, keysym="m"))
        self.pump_until(lambda: False, timeout=0.3)
        self.assertEqual(len(self.said), said)

    def test_announcer_ignores_widgets_tkinter_does_not_know(self):
        # Tks eigene Dialoge (Dateidialog unter Linux) bauen ttk-Felder ohne
        # tkinter; deren Ereignisse kommen mit dem Namen als Zeichenkette an.
        self.app.announcer.var.set(True)
        errors = []
        self.root.report_callback_exception = lambda *exc: errors.append(exc)
        for cls in ("ttk::entry", "ttk::spinbox", "ttk::checkbutton", "ttk::combobox"):
            name = f".raw{cls.split(':')[-1]}"
            self.root.tk.call(cls, name)
            self.root.tk.call("pack", name)
            self.root.update()
            self.root.tk.call("focus", "-force", name)
            for event in ("<FocusIn>", "<KeyRelease>", "<<TraverseIn>>", "<KeyRelease-space>",
                          "<<ComboboxSelected>>", "<<Increment>>"):
                self.root.tk.call("event", "generate", name, event)
            self.root.update()
            self.root.tk.call("destroy", name)
        self.pump_until(lambda: False, timeout=0.3)
        self.assertEqual(errors, [])

    def test_contest_calls_in_the_phonetic_alphabet(self):
        from morsetrainer.widgets import announcer
        contest = self.mode("Contest")
        contest.my_call_var.set("DL1ABC")
        self.assertIn("Delta, Lima, Eins, Alfa, Bravo", announcer.describe(contest.my_call_entry))
        self.assertEqual(announcer.change_text("DL", "DL1", "nato"), "Eins")
        self.assertEqual(announcer.change_text("DL1", "DL1A", "nato"), "Alfa")
        self.assertIn("Delta, Lima", announcer.describe(self.mode("Contest").call_entry) if contest.call_var.set("DL")
                      is None else "")
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        tree = contest.log_tree
        item = tree.insert("", "end", values=(1, "OE3XYZ", "599 15", "✓"))
        self.app.show_mode("Contest")
        self.root.deiconify()
        tree.focus_force()
        self.root.update()
        tree.selection_set(item)
        self.assertTrue(self.pump_until(lambda: any("Call: Oskar, Ekko, Drei" in text for text in self.said)))
        self.assertTrue(any("599 15" in text for text in self.said))  # Austausch nicht buchstabiert
        self.root.withdraw()

    def test_statistics_cells_are_spoken_clearly(self):
        # „?“ allein spräche die Stimme nicht; Verwechslungen als „B gleich 9 mal“.
        from morsetrainer.widgets import announcer
        self.assertEqual(announcer._cell_spoken("?"), "Fragezeichen")
        self.assertEqual(announcer._cell_spoken("K"), "Ka")
        self.assertEqual(announcer._cell_spoken("B (9), 5 (2)"), "Be gleich 9 mal, Fünf gleich 2 mal")
        self.assertEqual(announcer._cell_spoken("? (3)"), "Fragezeichen gleich 3 mal")
        self.assertEqual(announcer._cell_spoken("N (1)"), "Enn gleich einmal")  # nicht „1 mal“
        # Dateipfade: nur der letzte Teil, nicht „home oder maik oder …“.
        self.assertEqual(announcer.speakable("Einzelheiten stehen in\n/home/maik/.local/share/morsetrainer/fehler.log\n\nBitte"),
                         "Einzelheiten stehen in\nfehler.log\n\nBitte")
        self.assertEqual(announcer.speakable("Gespeichert: C:\\Users\\Max\\Musik\\cw.mp3."), "Gespeichert: cw.mp3.")
        self.assertEqual(announcer.speakable("Ordner /tmp, Seite https://github.com/a/b"), "Ordner /tmp, Seite https://github.com/a/b")
        self.assertEqual(announcer.speakable("Ordner ~/Musik/cw_neu.mp3."), "Ordner cw_neu.mp3.")
        self.assertEqual(announcer.speakable("Datei (/home/maik/x.log) fehlt"), "Datei, x.log, fehlt")
        self.assertEqual(announcer.speakable("Daten in /home/maik/.local/share/morsetrainer/."), "Daten in morsetrainer.")
        self.assertEqual(announcer.speakable("In /Users/maik/Library/Application Support/Morsetrainer/x.db"), "In x.db")
        self.assertEqual(announcer.speakable("In C:\\Users\\Max Muster\\AppData\\x.db"), "In x.db")
        self.assertEqual(announcer.speakable("Rufzeichen DL4YM/P, Zeit 10:30/11:00, Seite 3/5"),
                         "Rufzeichen DL4YM/P, Zeit 10:30/11:00, Seite 3/5")
        self.assertEqual(announcer.speakable("In /home/maik/.local/share/x/f.log", True),
                         "In home, maik, Punkt local, share, x, f.log")
        self.assertEqual(announcer.speakable("Mitschreiben und/oder Hören an/aus"), "Mitschreiben und oder Hören an oder aus")
        # Spaltenköpfe der Statistik.
        self.assertEqual(announcer.speakable("Ø Zeit (s)"), "Durchschnittszeit in Sekunden")
        self.assertEqual(announcer.speakable("Ø effektive Geschwindigkeit: 18 WPM"),
                         "durchschnittliche effektive Geschwindigkeit: 18 WPM")
        self.assertEqual(announcer.speakable("Median Zeit (s)"), "Median Zeit in Sekunden")
        self.assertEqual(announcer._cell_spoken("92 %"), "92 %")  # sonst unverändert
        self.assertEqual(announcer._cell_spoken("–"), "keine")  # keine Messung
        self.assertEqual(announcer._cell_spoken("OE3XYZ", nato_calls=True)[:11], "Oskar, Ekko")

    def test_contest_spread_fields_say_their_unit(self):
        from morsetrainer.widgets import announcer
        contest = self.mode("Contest")
        self.assertEqual(announcer.speakable(announcer.describe(contest.wpm_spread_spin)),
                         f"Tempo plus minus, Zahlenfeld, {contest.wpm_spread_var.get()} WPM.")
        self.assertIn("Hertz", announcer.speakable(announcer.describe(contest.freq_spread_spin)))

    def test_pin_field_says_pin_number_digit_by_digit(self):
        from morsetrainer.widgets import announcer
        network = self.mode("Netzwerk")
        network.pin_var.set("4711")
        self.assertEqual(announcer.describe(network.pin_entry), "PIN-Nummer, Eingabefeld, Vier, Sieben, Eins, Eins.")

    def test_new_window_says_its_name(self):
        # Sonst merkt ein Sehbehinderter nicht, dass er in einem neuen Fenster ist.
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)  # Reiter-Ansage beim Aufbau ausklingen lassen
        window = tk.Toplevel(self.root)
        window.title("Bandbedingungen")
        window.event_generate("<Map>")
        self.assertTrue(self.pump_until(lambda: "Fenster Bandbedingungen." in self.said))
        window.event_generate("<Map>")  # derselbe gleich noch einmal: nicht doppelt
        self.pump_until(lambda: False, timeout=0.3)
        self.assertEqual(self.said.count("Fenster Bandbedingungen."), 1)
        window.destroy()
        self.app.announcer.var.set(False)
        other = tk.Toplevel(self.root)
        other.title("Still")
        other.event_generate("<Map>")  # Ansage aus: nichts
        self.pump_until(lambda: False, timeout=0.3)
        self.assertNotIn("Fenster Still.", self.said)
        other.destroy()

    def test_minimizing_a_window_is_not_announced(self):
        from morsetrainer.widgets import announcer
        window = tk.Toplevel(self.root)
        try:
            with mock.patch.object(self.app.announcer, "window_closed") as closed, \
                    mock.patch.object(self.app.announcer, "window_shown") as shown, \
                    mock.patch.object(window, "wm_state", return_value="iconic"):
                announcer._window_closed(window)  # minimiert
                announcer._window_shown(window)  # wiederhergestellt
            closed.assert_not_called()
            shown.assert_not_called()
        finally:
            window.destroy()

    def test_closing_a_window_says_where_you_are(self):
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        self.root.deiconify()
        tab = self.app._tab_name()
        window = tk.Toplevel(self.root)
        window.title("Bandbedingungen")
        window.event_generate("<Map>")
        self.pump_until(lambda: False, timeout=0.3)
        self.root.focus_force()
        window.destroy()  # meldet Unmap und Destroy: nur eine Ansage
        expected = f"Zurück im Hauptfenster. Reiter {tab}."
        self.assertTrue(self.pump_until(lambda: expected in self.said))
        self.pump_until(lambda: False, timeout=0.3)
        self.assertEqual(self.said.count(expected), 1)
        # Liegt noch ein Fenster dahinter, heißt es dieses.
        # Den Fokus setzt hier der Test selbst: wann der Fenstermanager ihn
        # zurückgibt, schwankt unter Last.
        outer = tk.Toplevel(self.root)
        outer.title("Einstellungen")
        inner = tk.Toplevel(outer)
        inner.title("Diplome")
        self.root.update()
        with mock.patch.object(self.root, "focus_get", lambda: outer):
            inner.withdraw()
            self.assertTrue(self.pump_until(lambda: "Zurück im Fenster Einstellungen." in self.said))
        outer.destroy()
        self.root.withdraw()

    def test_window_name_joins_the_windows_own_announcement(self):
        # Fenster, die beim Öffnen selbst sprechen (Diplom, Abendbilanz):
        # Name und Inhalt in einer Ansage, egal in welcher Reihenfolge.
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        first = tk.Toplevel(self.root)
        first.title("Diplome")
        self.app.announcer.say("Neues Siegel.")
        first.event_generate("<Map>")
        self.assertTrue(self.pump_until(lambda: "Fenster Diplome. Neues Siegel." in self.said))
        self.pump_until(lambda: False, timeout=0.5)  # zweites Fenster später: gehört nicht zum ersten
        second = tk.Toplevel(self.root)
        second.title("Abendbilanz")
        second.event_generate("<Map>")
        self.app.announcer.say("Heute 20 Minuten.")
        self.assertTrue(self.pump_until(lambda: "Fenster Abendbilanz. Heute 20 Minuten." in self.said))
        self.assertFalse(any("Abendbilanz" in text and "Siegel" in text for text in self.said))
        first.destroy()
        second.destroy()

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
                               lambda text, rate=1.0: np.zeros(self.announcer.SAMPLE_RATE, dtype=np.float32)):
            self.app.announcer.say("Erste.", then=lambda: done.setdefault("first", time.monotonic()))
            self.assertTrue(self.pump_until(lambda: self.app.announcer.speaking_until > time.time()))
            second = time.monotonic()
            self.app.announcer.say("Zweite.", then=lambda: done.setdefault("second", time.monotonic()))
            self.assertTrue(self.pump_until(lambda: len(done) == 2, timeout=5))
        self.assertGreaterEqual(done["first"] - second, 1.0 + self.announcer.AFTER_SPEECH_MS / 1000 - 0.05)
        self.assertLessEqual(abs(done["first"] - done["second"]), 0.2)

    def test_flow_after_announcement_waits_for_one_started_just_after(self):
        # F11 gleich nach „Falsch …“: Die erste Ansage ist zu Ende gesprochen,
        # ihr Ablauf (Korrekturton) aber noch nicht dran – er wartet nun auf
        # die neue, statt sie abzuschneiden.
        import time
        import numpy as np
        from morsetrainer.core import speech
        announcer = self.app.announcer
        announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        done = {}
        with mock.patch.object(speech.speaker, "synth",
                               lambda text, rate=1.0: np.zeros(self.announcer.SAMPLE_RATE // 2, dtype=np.float32)):
            announcer.say("Falsch.", then=lambda: done.setdefault("first", time.monotonic()))
            first_token = announcer.token
            # Zu Ende gesprochen, der Ablauf kommt erst nach AFTER_SPEECH_MS.
            self.assertTrue(self.pump_until(lambda: announcer.done_token == first_token
                                            and time.time() >= announcer.speaking_until))
            self.assertNotIn("first", done)
            second = time.monotonic()
            announcer.say("Einzeln, Zeichen.", then=lambda: done.setdefault("second", time.monotonic()))
            self.assertTrue(self.pump_until(lambda: len(done) == 2, timeout=5))
        self.assertGreaterEqual(done["first"] - second, 0.5 + self.announcer.AFTER_SPEECH_MS / 1000 - 0.05)

    def test_speech_cache_is_limited(self):
        # Der Zwischenspeicher wächst nicht unbegrenzt (Statistik-Ansagen sind
        # lang und jedes Mal anders); der älteste Eintrag fällt heraus.
        announcer = self.app.announcer
        announcer.clear_cache()
        with mock.patch.object(self.announcer, "CACHE_SIZE", 3):
            for text in ("eins", "zwei", "drei", "vier", "fünf"):
                announcer._synth(text)
        self.assertEqual(list(announcer._cache), ["drei", "vier", "fünf"])

    def test_speech_cache_is_limited_by_size(self):
        # Lange Ansagen mit wechselnden Zahlen (F11) füllen den Speicher nicht:
        # Es zählt auch die Größe; was gerade gebraucht wurde, bleibt.
        import numpy as np
        from morsetrainer.core import speech
        announcer = self.app.announcer
        announcer.clear_cache()
        second = np.zeros(1000, dtype=np.float32)  # 4000 Bytes
        with mock.patch.object(speech.speaker, "synth", lambda text, rate=1.0: second), \
                mock.patch.object(self.announcer, "CACHE_BYTES", 10000):
            for text in ("eins", "zwei", "eins", "drei"):
                announcer._synth(text)
            self.assertEqual(list(announcer._cache), ["eins", "drei"])
            with mock.patch.object(speech.speaker, "synth", lambda text, rate=1.0: np.zeros(5000, dtype=np.float32)):
                self.assertIsNotNone(announcer._synth("zu lang"))
        self.assertNotIn("zu lang", announcer._cache)

    def test_speech_cache_holds_across_threads(self):
        import threading
        import numpy as np
        from morsetrainer.core import speech
        announcer = self.app.announcer
        announcer.clear_cache()
        errors = []

        def speak(offset):
            try:
                for i in range(300):
                    announcer._synth(f"Ansage {(i + offset) % 40}")
            except Exception as error:  # noqa: BLE001 – jeder Fehler ist hier ein Befund
                errors.append(error)

        interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)  # Threads wechseln oft: Wettläufe zeigen sich
        try:
            with mock.patch.object(speech.speaker, "synth", lambda text, rate=1.0: np.zeros(400, dtype=np.float32)), \
                    mock.patch.object(self.announcer, "CACHE_BYTES", 16000):
                threads = [threading.Thread(target=speak, args=(n * 7,)) for n in range(4)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        finally:
            sys.setswitchinterval(interval)
        self.assertEqual(errors, [])
        self.assertEqual(announcer._cache_size, sum(s.nbytes for s in announcer._cache.values()))
        self.assertLessEqual(announcer._cache_size, 16000)

    def test_speech_cache_lock_prevents_lost_updates(self):
        # Erzwungener Wettlauf: Das Lesen der Größe (nbytes) gibt den Thread
        # ab, mitten in „_cache_size += size“. Ohne _cache_lock ginge eine
        # Änderung verloren und die Summe stimmte nicht mehr.
        import threading
        import time
        from morsetrainer.core import speech
        announcer = self.app.announcer
        announcer.clear_cache()

        class Slow:
            @property
            def nbytes(self):
                time.sleep(0.002)
                return 100

        start = threading.Barrier(4)

        def speak(offset):
            start.wait()
            for i in range(25):
                announcer._synth(f"Wettlauf {offset} {i}")

        with mock.patch.object(speech.speaker, "synth", lambda text, rate=1.0: Slow()):
            threads = [threading.Thread(target=speak, args=(n,)) for n in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(announcer._cache_size, 100 * len(announcer._cache))

    def test_first_announcement_waits_until_the_window_is_drawn(self):
        # Ist die Stimme noch nicht geladen, lädt die erste Ansage sie – und
        # das hält die Oberfläche an. Deshalb erst, wenn das Fenster steht.
        from morsetrainer.core import speech
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        self.said.clear()
        with mock.patch.object(speech.speaker, "voice", None), mock.patch.object(speech.speaker, "preload", lambda: None):
            self.app.announcer.say("Reiter Gruppen.")
            time.sleep(0.1)
            self.assertEqual(self.said, [])
            self.assertTrue(self.pump_until(lambda: self.said, timeout=3))

    def test_failing_synthesis_does_not_stall_the_flow(self):
        import threading
        self.app.announcer.var.set(True)
        done = []
        with mock.patch.object(self.app.announcer, "_synth", side_effect=RuntimeError("Stimme kaputt")), \
                mock.patch.object(threading, "excepthook") as hook:
            self.app.announcer.say("Erster Satz. " + "Noch etwas mehr Text. " * 5, then=lambda: done.append(1))
            self.assertTrue(self.pump_until(lambda: done, timeout=3))
        self.assertTrue(hook.called)  # der Fehler kommt im Protokoll an
        self.assertIs(hook.call_args.args[0].exc_type, RuntimeError)

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

    def test_f1_opens_help_except_in_contest(self):
        """F1 öffnet die Hilfe beim aktuellen Reiter; im Contest sendet es
        CQ wie in Contest-Programmen und öffnet keine Hilfe."""
        from morsetrainer import app as app_module
        with mock.patch.object(app_module.HelpWindow, "show") as show:
            self.app._dispatch_key(mock.Mock(keysym="F1", char=""))
            show.assert_called_once_with(self.app.root, self.app.notebook.tab("current", "text"))
            self.app.show_mode("Contest")
            show.reset_mock()
            with mock.patch.object(self.mode("Contest"), "on_function_key") as contest_key:
                self.app._dispatch_key(mock.Mock(keysym="F1", char=""))
            show.assert_not_called()
            contest_key.assert_called_once_with("F1")

    def test_f11_reads_tab_and_status_even_when_off(self):
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertTrue(self.said[0].startswith("Einzeln, Zeichen. Bereit"), self.said)

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

    def test_f11_spells_punctuation_feedback(self):
        # „Falsch: war ., du: =“ verschluckte die Stimme; F11 buchstabiert.
        import time
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.5)
        single = self.mode("Einzelzeichen")
        single.start()
        single.current_char, single.voice, single.waiting_for_input, single.replayed = ".", (20, 600), True, False
        single.play_start_time = time.time() - 0.5
        single.on_key(type("E", (), {"keysym": "equal", "char": "="})())
        self.assertIn(".", single.feedback_var.get())
        spoken = self.announcer.spoken_value(single.feedback_var)
        self.assertIn(self.announcer.spell("."), spoken)
        self.assertIn(self.announcer.spell("="), spoken)
        self.assertNotIn(" .", spoken)
        # Ändert sich die Anzeige anders, gilt wieder der angezeigte Text.
        single.feedback_var.set("Etwas anderes")
        self.assertEqual(self.announcer.spoken_value(single.feedback_var), "Etwas anderes")
        single.stop()

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
        # Helle Palette: Text 4,5:1, Feldränder, Fokus und Reglergriff 3:1
        # (WCAG 1.4.3 und 1.4.11) – auf jedem Grund, auf dem sie stehen.
        for fg, bg in (("TEXT", "BG"), ("MUTED", "BG"), ("MUTED", "SURFACE"), ("MUTED", "BUTTON"),
                       ("TEXT", "SELECT"), ("ACCENT", "BG"), ("ACCENT", "SURFACE"), ("SURFACE", "ACCENT")):
            self.assertGreaterEqual(ratio(light[fg], light[bg]), 4.5, (fg, bg))
        for color in light["STATION_COLORS"]:
            self.assertGreaterEqual(ratio(color, light["SURFACE"]), 4.5, color)
        for fg, bg in (("FOCUS", "SURFACE"), ("FOCUS", "BG"), ("EDGE", "SURFACE"), ("EDGE", "BG"),
                       ("EDGE", "TROUGH"), ("EDGE", "BUTTON")):
            self.assertGreaterEqual(ratio(light[fg], light[bg]), 3, (fg, bg))

    def test_scrollbar_thumb_stands_out_from_its_trough(self):
        from tkinter import ttk
        style = ttk.Style(self.root)
        self.assertEqual(str(style.lookup("TScrollbar", "background")), theme.THUMB)
        self.assertEqual(str(style.lookup("TScrollbar", "troughcolor")), theme.BG)

    def test_scrollbar_arrows_are_readable_on_the_thumb(self):
        # Die Pfeilknöpfe haben die Farbe des Griffs (auch beim Darüberfahren).
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def ratio(a, b):
            high, low = sorted((luminance(a), luminance(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)
        for name, palette in theme.PALETTES.items():
            for ground in ("THUMB", "EDGE"):
                self.assertGreaterEqual(ratio(palette["THUMB_ARROW"], palette[ground]), 3, (name, ground))

    def test_week_spoken_on_the_first_day(self):
        from datetime import date
        from morsetrainer.core import week
        from morsetrainer.widgets.daily_panel import week_spoken
        days = [{"day": date(2026, 10, 12), "stars": 0, "status": week.NONE}] + [
            {"day": date(2026, 10, 13 + n), "stars": 0, "status": week.FUTURE} for n in range(6)]
        self.assertEqual(week_spoken(days), "heute noch offen")
        days[0]["stars"] = 1
        self.assertEqual(week_spoken(days), "heute geübt")

    def test_selection_without_focus_keeps_the_palette(self):
        # clam färbt sie sonst grau/weiß (2,8:1); TEXT auf SELECT prüft der Palettentest.
        from tkinter import ttk
        style = ttk.Style(self.root)
        for widget_style in ("TEntry", "TSpinbox", "TCombobox"):
            self.assertEqual(str(style.lookup(widget_style, "selectbackground", ["!focus"])), theme.SELECT)
            self.assertEqual(str(style.lookup(widget_style, "selectforeground", ["!focus"])), theme.TEXT)

    def test_info_texts_do_not_use_the_disabled_grey(self):
        # Das Grau für gesperrte Bedienelemente ist zu blass für Text, den man
        # lesen soll (2,2:1); Hinweise und abgeblendete Einträge nehmen MUTED.
        import pathlib
        package = pathlib.Path(theme.__file__).resolve().parents[1]
        for path in [*package.glob("modes/*.py"), *package.glob("widgets/*.py")]:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "theme.DISABLED" in line and "else theme.DISABLED" not in line:
                    self.fail(f"{path.name}:{number}: {line.strip()}")

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
                    tests.release_root(root)
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

    def test_focus_is_scrolled_into_view(self):
        # Große Schrift, kleines Fenster: Tab zu einem Feld unterhalb des
        # sichtbaren Teils rollt dorthin, und zurück nach oben ebenso.
        from morsetrainer.widgets.ui_widgets import ScrollableFrame
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        window.geometry("300x150")
        scroller = ScrollableFrame(window)
        entries = [ttk.Entry(scroller.inner) for _ in range(20)]
        for entry in entries:
            entry.pack(pady=4)
        window.update()

        def visible(widget):
            top = widget.winfo_rooty() - scroller.canvas.winfo_rooty()
            return top >= 0 and top + widget.winfo_height() <= scroller.canvas.winfo_height()

        self.assertFalse(visible(entries[-1]))
        entries[-1].focus_force()
        window.update()
        self.assertTrue(visible(entries[-1]))
        entries[0].focus_force()
        window.update()
        self.assertTrue(visible(entries[0]))
        self.assertEqual(scroller.canvas.yview()[0], 0.0)

    def test_table_with_hidden_columns_announces_the_arrow_keys(self):
        from morsetrainer.widgets import announcer
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        window.geometry("200x150")
        columns = ("a", "b", "c", "d")
        tree = ttk.Treeview(window, columns=columns, show="headings", height=3)
        for column in columns:
            tree.heading(column, text=column)
        tree.pack(fill="x")
        theme.fit_columns(tree, dict.fromkeys(columns, 150))
        window.update()
        self.assertIn("Pfeil links und rechts", announcer.describe(tree))
        window.geometry("900x150")
        window.update()
        self.assertNotIn("Pfeil links und rechts", announcer.describe(tree))

    def test_statistics_summary_wraps_instead_of_being_cut_off(self):
        from morsetrainer.widgets.stats_widget import StatsPanel
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        window.geometry("360x300")
        panel = StatsPanel(window)
        panel.speed_var.set("Ø effektive Geschwindigkeit: 123,4 WPM · 456 ZpM gemessen")
        summary = panel.speed_label.master
        window.update()
        self.assertLessEqual(panel.speed_label.winfo_x() + panel.speed_label.winfo_reqwidth(), summary.winfo_width())

    def test_selected_table_row_is_scrolled_into_view(self):
        # Eine Tabelle mit eigenem Rollbalken zeigt die gewählte Zeile, und eine
        # Tabelle, die höher ist als das Fenster, rollt die Seite zur Zeile.
        from morsetrainer.widgets.ui_widgets import ScrollableFrame
        window = tk.Toplevel(self.root)
        self.addCleanup(window.destroy)
        window.geometry("300x150")
        scroller = ScrollableFrame(window)
        small = ttk.Treeview(scroller.inner, columns=("a",), show="headings", height=3)
        small.pack()
        tall = ttk.Treeview(scroller.inner, columns=("a",), show="headings", height=30)
        tall.pack()
        small_rows = [small.insert("", "end", values=(n,)) for n in range(20)]
        tall_rows = [tall.insert("", "end", values=(n,)) for n in range(30)]
        window.update()
        small.selection_set(small_rows[-1])
        window.update()
        self.assertTrue(small.bbox(small_rows[-1]))
        tall.selection_set(tall_rows[-1])
        window.update()
        top = tall.winfo_rooty() - scroller.canvas.winfo_rooty() + tall.bbox(tall_rows[-1])[1]
        self.assertTrue(0 <= top < scroller.canvas.winfo_height(), top)

    def test_enter_presses_a_focused_button(self):
        # ttk kennt von sich aus nur die Leertaste; Enter soll genauso gehen
        # (z. B. „Schließen“ im Einstellungsfenster nach dem Durchtabben).
        pressed = []
        button = ttk.Button(self.root, command=lambda: pressed.append(1))
        button.pack()
        self.root.deiconify()
        button.focus_force()  # Tasten gehen an das Element mit Fokus
        self.root.update()
        for key in ("<Return>", "<KP_Enter>"):
            button.event_generate(key, when="now")
        self.assertEqual(pressed, [1, 1])
        button.state(["disabled"])
        button.event_generate("<Return>", when="now")
        self.assertEqual(pressed, [1, 1])  # gesperrt bleibt gesperrt
        button.destroy()
        window = self.app.settings_window
        self.app.open_settings()

        def buttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    yield child
                yield from buttons(child)
        [close] = [b for b in buttons(window) if b.cget("text") == "Schließen"]
        end = time.monotonic() + 2  # bis der Fenstermanager es zeigt
        while window.state() != "normal" and time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)
        close.focus_force()
        self.root.update()
        close.event_generate("<Return>", when="now")
        self.assertEqual(window.state(), "withdrawn")
        self.root.withdraw()

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

    def test_one_by_one_tab_holds_four_exercises(self):
        # Zeichen, Gruppen, Wörter, Rufzeichen teilen sich „Einzeln“; „Kontinuierlich“ heißt „Am Stück“.
        names = [self.app.notebook.tab(tab, "text") for tab in self.app.notebook.tabs()]
        self.assertEqual(names[:2], ["Einzeln", "Am Stück"])
        self.assertNotIn("Gruppen", names)
        self.app.show_mode("Wörter")
        self.assertEqual(self.app.one_by_one_var.get(), "Wörter")
        self.assertIs(self.app._active_mode(), self.mode("Wörter"))
        self.assertEqual(self.app.one_by_one_frames["Wörter"].winfo_manager(), "pack")
        self.assertEqual(self.app.one_by_one_frames["Gruppen"].winfo_manager(), "")  # nur die gewählte sichtbar
        self.app._lock_tabs()  # während eines Durchgangs keine andere Übung
        self.assertTrue(all(b.instate(["disabled"]) for b in self.app.one_by_one_buttons))
        self.app._unlock_tabs()
        self.assertFalse(any(b.instate(["disabled"]) for b in self.app.one_by_one_buttons))
        self.app.one_by_one_var.set("Rufzeichen")  # Auswahl per Knopf
        self.app._show_one_by_one()
        self.assertIs(self.app._active_mode(), self.mode("Rufzeichen"))
        self.assertEqual(self.app._tab_name(), "Einzeln, Rufzeichen")

    def test_one_by_one_choice_is_kept_after_restart(self):
        import json
        from morsetrainer import app as app_module
        self.app.show_mode("Wörter")
        self.app._save_state()
        self.assertEqual(json.loads(app_module.WINDOW_STATE_FILE.read_text())["one_by_one"], "Wörter")
        root = tk.Tk()
        root.withdraw()
        try:
            again = app_module.MorseTrainerApp(root)
            self.assertEqual(again.one_by_one_var.get(), "Wörter")
            self.assertIs(again._active_mode(), again.modes[again.mode_titles.index("Wörter")])
        finally:
            from morsetrainer.widgets import announcer
            announcer._instance = self.app.announcer
            tests.release_root(root)

    def test_alt_number_selects_tab_unless_locked(self):
        self.app.select_tab(1)
        self.assertEqual(self.app._tab_name(), "Am Stück")
        self.app.select_tab(5)
        self.assertEqual(self.app._tab_name(), "Netzwerk")
        self.app._lock_tabs()
        self.app.select_tab(0)
        self.assertEqual(self.app._tab_name(), "Netzwerk")  # gesperrt während eines Durchgangs
        self.app._unlock_tabs()
        self.assertTrue(self.root.bind_all("<Alt-Key-1>"))
        self.assertTrue(self.root.bind_all("<Control-b>"))

    def test_content_of_one_by_one_by_keyboard(self):
        from morsetrainer.widgets import announcer
        self.app.select_tab(0)
        self.app.show_content("Einzelzeichen")
        # Reiterleiste mit Fokus nennt auch den Inhalt.
        self.assertIn("Einzeln, Zeichen", announcer.describe(self.app.notebook))
        with mock.patch.object(announcer, "say") as say:
            self.app.select_tab(0)  # Alt+1 noch einmal: nächster Inhalt
        self.assertEqual(self.app.one_by_one_var.get(), "Gruppen")
        self.assertEqual(say.call_args.args[0], "Reiter Einzeln, Gruppen.")
        buttons = self.app.one_by_one_buttons
        self.assertIn("Inhalt Gruppen", announcer.describe(buttons[1]))
        self.assertTrue(buttons[1].bind("<Right>"))  # Pfeiltaste rechts:
        with mock.patch.object(announcer, "say") as say:
            self.app._step_content(1, focus=True)
        self.assertEqual(self.app.one_by_one_var.get(), "Wörter")
        self.assertEqual(say.call_args.args[0], "Inhalt Wörter.")
        self.app._lock_tabs()
        for button in buttons:
            button.state(["disabled"])
        self.app.select_tab(0)
        self.assertEqual(self.app.one_by_one_var.get(), "Wörter")  # nicht während eines Durchgangs
        for button in buttons:
            button.state(["!disabled"])
        self.app._unlock_tabs()

    def test_start_problem_is_announced(self):
        # Wendungen mit Lektion 1: zu wenige Zeichen, der Hinweis wird auch gesprochen.
        from morsetrainer.widgets import announcer
        from morsetrainer.core import koch
        m = self.mode("Kontinuierlich")
        self.app.charset_var.set(koch.lesson_charset(1))
        m.content_var.set("Wendungen")
        with mock.patch.object(announcer, "say") as say:
            m.start()
        self.assertFalse(m.running)
        self.assertTrue(m.status_var.get())
        say.assert_called_with(m.status_var.get(), full_paths=True)

    def test_one_before_a_unit_is_spoken_as_a_word(self):
        from morsetrainer.widgets import announcer
        m = self.mode("Kontinuierlich")
        spinboxes = []

        def walk(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TSpinbox":
                    spinboxes.append(child)
                walk(child)
        walk(m.options_card)
        units = {announcer._unit_after(box): box for box in spinboxes}
        m.duration_var.set(1)
        self.assertEqual(announcer.speakable(announcer.describe(units["Min."])), "Dauer, Zahlenfeld, eine Minute.")
        m.group_len_var.set(1)
        self.assertIn("ein Zeichen", announcer.describe(units["Zeichen"]))
        m.group_len_var.set(5)
        self.assertIn("5 Zeichen", announcer.describe(units["Zeichen"]))

    def test_content_of_non_stop_as_option_buttons(self):
        from morsetrainer.widgets import announcer
        m = self.mode("Kontinuierlich")
        row = m.content_buttons
        self.assertEqual(len(row.buttons), 7)
        self.assertNotEqual(row.master.master, m.options_card)  # oben im Reiter, nicht in den Einstellungen
        m.content_var.set("Abkürzungen")
        self.assertIn("Inhalt Abkürzungen", announcer.describe(row.buttons[1]))
        self.assertTrue(row.buttons[1].bind("<Right>"))
        with mock.patch.object(announcer, "say") as say:
            row.step(1)
        self.assertEqual(m.content_var.get(), "Klartext")
        self.assertEqual(say.call_args.args[0], "Inhalt Klartext.")
        row.state(["disabled"])
        row.step(1)
        self.assertEqual(m.content_var.get(), "Klartext")  # gesperrt
        row.state(["!disabled"])

    def test_content_of_speak_as_option_buttons_at_the_top(self):
        m = self.mode("Sprechen")
        self.assertEqual(len(m.content_buttons.buttons), 6)
        self.assertNotIn(m.content_buttons.master, m.group_len_box.master.master.winfo_children())
        m.content_buttons.buttons[1].invoke()
        self.assertEqual(m.content_var.get(), "Gruppen")
        self.assertTrue(m.group_len_box.instate(["!disabled"]))

    def test_alt_zero_goes_to_statistics_and_missing_tabs_are_announced(self):
        from morsetrainer.widgets import announcer
        self.app.select_tab(-1)  # Alt+0
        self.assertEqual(self.app._tab_name(), "Statistik")
        with mock.patch.object(announcer, "say") as say:
            self.app.select_tab(8)
        self.assertEqual(say.call_args.args[0], "Es gibt nur 7 Reiter.")
        self.assertEqual(self.app._tab_name(), "Statistik")

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


class AnnouncerModesTest(AnnouncerCase):
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

    def test_no_double_marks_in_describe_and_statistics(self):
        panel = self.app.lifeline_panel
        panel.info_var.set("Die Lebenslinie beginnt mit dem ersten Üben.")
        spoken = self.announcer.describe(panel.canvas)
        self.assertNotIn("..", spoken)
        self.assertTrue(spoken.endswith("springt eine Woche."), spoken)
        # Tastaturhinweis erst, wenn es Tage gibt.
        from datetime import date
        from morsetrainer.widgets import lifeline_widget
        panel.refresh()
        self.assertEqual(panel.keys_hint.winfo_manager(), "")
        with mock.patch.object(lifeline_widget.lifeline, "load", lambda: {"days": [date(2026, 10, 1)]}), \
                mock.patch.object(lifeline_widget, "summary_text", lambda line: "Seit 01.10.2026"), \
                mock.patch.object(panel, "draw"):
            panel.refresh()
        self.assertEqual(panel.keys_hint.winfo_manager(), "pack")
        self.assertIn("Pfeil\u00a0links", str(panel.keys_hint.cget("text")))
        self.assertEqual(self.announcer.describe(self.app.zoom_box).count("."), 1)
        self.assertNotIn("..", self.app.statistics_spoken())

    def test_f11_during_a_tone_waits_for_its_end(self):
        # sd.play der Ansage schnitte den laufenden Morseton ab: F11 wartet,
        # bis er zu Ende ist; ein langer Ton (Sprechen) wird nicht abgewartet.
        import time
        import numpy as np
        from morsetrainer.core import audio
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        with mock.patch.object(audio.sd, "play"):
            audio.play(np.zeros(int(0.6 * audio.SAMPLE_RATE), dtype=np.float32))
        started = time.time()
        del self.played[:]
        self.app.read_status()
        self.assertTrue(self.pump_until(lambda: self.played))
        self.assertGreater(time.time() - started, 0.6)
        with mock.patch.object(audio.sd, "play"):
            audio.play(np.zeros(int((self.announcer.TONE_WAIT_MAX_S + 5) * audio.SAMPLE_RATE), dtype=np.float32))
        started = time.time()
        del self.played[:]
        self.app.read_status()
        self.assertTrue(self.pump_until(lambda: self.played))
        self.assertLess(time.time() - started, 0.6)
        audio.stop()
        self.assertEqual(audio.tone_remaining(), 0.0)

    def test_f11_joins_sentences_without_double_marks(self):
        from morsetrainer.widgets.announcer import sentences
        self.assertEqual(sentences(["Reiter Einzeln", "Start mit F5.", "Deine Eingabe?", "",
                                               "Zeile eins\nZeile zwei."]),
                         "Reiter Einzeln. Start mit F5. Deine Eingabe? Zeile eins. Zeile zwei.")
        self.assertEqual(sentences(["Dauer 1 Min."]), "Dauer 1 Min..")  # speakable verschluckt den Abkürzungspunkt
        # Schon beantwortet: „Deine Eingabe?“ steht noch da, gilt aber nicht mehr.
        self.app.announcer.var.set(True)
        self.app.show_mode("Einzelzeichen")
        mode = self.mode("Einzelzeichen")
        mode.status_var.set("Deine Eingabe?")
        mode.feedback_var.set("Richtig: K")
        for waiting, expected in ((True, True), (False, False)):
            mode.waiting_for_input = waiting
            with mock.patch.object(self.app.announcer, "say") as say:
                self.app.read_status()
            spoken = say.call_args[0][0]
            self.assertNotIn("..", spoken)
            self.assertNotIn("?.", spoken)
            self.assertEqual("Deine Eingabe?" in spoken, expected, spoken)

    def test_f11_spells_the_contest_entry_with_focus(self):
        self.app.show_mode("Contest")
        mode = self.mode("Contest")
        mode.call_var.set("DL4YM")
        mode.exch_var.set("")
        cases = ((mode.call_entry, "Call: Delta"), (mode.exch_entry, "Austausch: leer"))
        for entry, expected in cases:
            with mock.patch.object(self.root, "focus_get", return_value=entry), \
                    mock.patch.object(self.app.announcer, "say") as say:
                self.app.read_status()
            self.assertTrue(say.call_args[0][0].startswith(expected), say.call_args[0][0])  # vor allem anderen
        with mock.patch.object(self.root, "focus_get", return_value=mode.call_entry), \
                mock.patch.object(self.app, "_window_of", return_value=self.root), \
                mock.patch.object(self.app.announcer, "say") as say:
            mode.exch_var.set("599 14")
            self.app.read_status()
        self.assertIn("Call: Delta", say.call_args[0][0])
        self.assertNotIn("Austausch:", say.call_args[0][0])

    def test_f11_spells_spaces_in_the_exchange(self):
        mode = self.mode("Contest")
        mode.exch_var.set("599 14")
        self.assertEqual(mode.field_text(mode.exch_entry), "Austausch: Fünf, Neun, Neun, Leerzeichen, Eins, Vier")

    def test_words_count_line_and_split_window_are_spoken(self):
        from morsetrainer.core import koch
        self.app.announcer.var.set(True)
        self.app.charset_var.set(koch.lesson_charset(12))
        self.app.show_mode("Wörter")
        w = self.mode("Wörter")
        w.content_var.set("gemischt")
        del self.said[:]
        self.app.read_status()  # F11 vor dem Start: auch die Zählzeile
        self.assertTrue(self.pump_until(lambda: "Mit dem aktuellen Zeichensatz:" in " ".join(self.said)))
        self.assertNotIn("Wörtern..", " ".join(self.said))
        # Wendungen: einmal je Durchgang das zweigeteilte Zeitfenster, vor dem Ton.
        self.app.charset_var.set(koch.lesson_charset(koch.FINAL_LESSON))
        w.content_var.set("Wendungen")
        rule = "Zügig heißt hier: in 2 Sekunden anfangen"
        with mock.patch.object(w, "play_current") as play, \
                mock.patch.object(w, "_play_intro", side_effect=lambda: w.next_sequence()):
            w.start()
            self.assertFalse(play.called)  # erst die Ansage, dann der Ton
            self.assertTrue(self.pump_until(lambda: play.called))
            self.assertIn(rule, " ".join(self.said))
            del self.said[:]
            w.next_sequence(waited=True)
            self.assertEqual(play.call_count, 2)
            w.stop()
        self.assertNotIn(rule, " ".join(self.said))

    def test_qso_quiz_names_fields_and_reads_the_result(self):
        from morsetrainer.core import qso_text
        from morsetrainer.modes.qso_quiz import QuizPanel
        from morsetrainer.widgets import announcer
        self.app.announcer.var.set(True)
        qso = mock.Mock(quiz_columns=("Station 1", "Station 2"),
                        quiz_rows=(("Rufzeichen", (("DL1ABC", qso_text.TEXT), ("DK2XY", qso_text.TEXT))),
                                   ("Name", (("Hans", qso_text.TEXT), ("Eva", qso_text.TEXT)))))
        playing = [False]
        quiz = QuizPanel(self.root, on_checked=lambda correct, total: None, busy=lambda: playing[0])
        quiz.reset(qso)
        quiz._announce_field((1, 0))
        self.assertTrue(self.pump_until(lambda: "Name, Station 1. Leer." in self.said))
        # Tippen wird buchstabiert, Löschen gesagt – nur nicht, solange das QSO läuft.
        quiz.vars[1, 0].set("H")
        quiz._echo((1, 0), "h")
        self.assertTrue(self.pump_until(lambda: announcer.change_text("", "H") in self.said))
        playing[0] = True
        quiz.vars[1, 0].set("Ha")
        quiz._echo((1, 0), "a")
        self.pump_until(lambda: False, timeout=0.3)
        self.assertNotIn(announcer.change_text("H", "Ha"), self.said)
        playing[0] = False
        quiz.vars[1, 0].set("H")
        quiz._echo((1, 0), "BackSpace")
        self.assertTrue(self.pump_until(lambda: announcer.change_text("Ha", "H") in self.said))
        for key, typed in (((0, 0), "DL1ABC"), ((0, 1), "DK2XY"), ((1, 0), "Hans"), ((1, 1), "Ute")):
            quiz.vars[key].set(typed)
        quiz.check()
        self.assertEqual(quiz.spoken_result(), "3 von 4 richtig. Richtig wäre: Name, Station 2: Eva.")
        quiz._announce_field((1, 1))
        self.assertTrue(self.pump_until(
            lambda: "Name, Station 2. Eingetragen: Ute. Falsch. Richtig wäre: Eva." in " ".join(self.said)))

    def test_statistics_are_read_out(self):
        text = self.app.statistics_spoken()
        self.assertTrue(text.startswith("Statistik. Noch keine Durchgänge."), text)
        self.assertIn("Lernkartei", text)
        self.assertIn("Diese Woche: ", text)
        self.assertIn("0 ★ diese Woche, Ziel 8", text)  # angesagt als „0 Sterne“ (speakable)
        self.assertTrue(self.app.week_strip_var.get().startswith("Mo "))  # auch bei 200 % sichtbar

    def test_week_strip_is_spoken_in_one_sentence(self):
        from datetime import date
        from morsetrainer.core import week
        from morsetrainer.widgets.daily_panel import week_spoken
        days = [{"day": date(2026, 10, 12), "stars": 3, "status": week.NONE},
                {"day": date(2026, 10, 13), "stars": 1, "status": week.NONE},
                {"day": date(2026, 10, 14), "stars": 0, "status": week.PRACTICED},
                {"day": date(2026, 10, 15), "stars": 0, "status": week.NONE},
                {"day": date(2026, 10, 16), "stars": 0, "status": week.FUTURE}]
        self.assertEqual(week_spoken(days),
                         "3 von 4 Tagen geübt, heute noch offen")
        days[3] = {"day": date(2026, 10, 15), "stars": 2, "status": week.NONE}
        self.assertEqual(week_spoken(days), "4 von 4 Tagen geübt")
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

    def test_shown_prosigns_are_spoken_by_name(self):
        from morsetrainer.widgets import announcer
        self.assertEqual(announcer.speakable("Neues Zeichen: <SK> · Taste *"),
                         "Neues Zeichen: Ende der Verbindung, Taste Stern")
        self.assertEqual(announcer.speakable("73 <KN>"), "73 bitte kommen")
        from morsetrainer.i18n_en import EN
        with mock.patch.object(i18n, "LANG", "en"), mock.patch.object(i18n, "_TABLE", EN):
            self.assertEqual(announcer.speakable("<BK> · key #"), "break, key hash")

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


class FocusAnnounceTest(AnnouncerCase):
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
            self.assertTrue(any(t.startswith("Rauschabstand, Regler, +") for t in texts), texts)
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



class EveningSummaryAnnounceTest(AnnouncerCase):
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
        self.assertIn("7 Sterne diese Woche, Ziel 8", text)
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
        self.assertEqual(announcer.speakable("0 ★ diese Woche, Ziel 8"), "0 Sterne diese Woche, Ziel 8")
        self.assertEqual(announcer.speakable("Letzte Woche: 1 Tag, 1 ★"), "Letzte Woche: 1 Tag, 1 Stern")
        # Einheiten als Wort, sonst buchstabiert die Stimme („HaZet“).
        self.assertEqual(announcer.speakable("Tonhöhe, Zahlenfeld, 650 Hz"), "Tonhöhe, Zahlenfeld, 650 Hertz")
        self.assertEqual(announcer.speakable("Filter 2,4 kHz, 500 Hz"), "Filter 2,4 Kilohertz, 500 Hertz")
        self.assertEqual(announcer.speakable("Hzx HzHz"), "Hzx HzHz")  # nur ganze Wörter
        self.assertEqual(announcer.speakable("▶ Tagesübung (10 Min)"), "▶ Tagesübung, 10 Minuten")
        self.assertEqual(announcer.speakable("Noch 1 Min"), "Noch eine Minute")  # nicht „eins Minute“
        self.assertEqual(announcer.speakable("Dauer, 1 Min."), "Dauer, eine Minute")
        self.assertEqual(announcer.speakable("Pause 1 s"), "Pause eine Sekunde")
        self.assertEqual(announcer.speakable("Tage mit ≥ 10 Min. Übung"), "Tage mit mindestens 10 Minuten Übung")
        self.assertEqual(announcer.speakable("K kommt schneller: 0,8 s → 0,6 s"),
                         "K kommt schneller: 0,8 Sekunden auf 0,6 Sekunden")
        self.assertEqual(announcer.speakable("10 Minuten, s wie Siegfried"), "10 Minuten, s wie Siegfried")
        # Englische Lehnwörter so, wie Funkamateure sie sprechen (nicht „Fäding“).
        self.assertEqual(announcer.speakable("QSB (Fading), Flatterfading (Aurora)"),
                         "QSB, Fehding, Flatterfehding, Aurora")
        self.assertEqual(announcer.speakable("Pile-ups, ein Pileup, pile-up"), "Peil-apps, ein Peil-app, Peil-app")
        # Contest-Arten buchstabiert wie unter Funkamateuren.
        from morsetrainer.core import qso_text
        spoken = [announcer.speakable(name) for name in qso_text.CONTEST_NAMES.values()]
        # Buchstabennamen wie bei Rufzeichen; Klammern als Pause, nicht „in Klammern“.
        self.assertEqual(spoken, ["Ze, Ku We, We, Zone", "Ze, Ku We, Pe, Ix, Nummer", "We, A, Ge, De, O, Ka",
                                  "A, Err, Err, Ell De, Ix, Staat oder Leistung",
                                  "I, A, Err, U Ha, Eff, I, Te, U Zone oder Ha, Ku"])
        self.assertEqual(announcer.speakable("CQ-Zone, DXCC, WWA"), "Ze, Ku Zone, DXCC, WWA")  # nur ganze Wörter
        self.assertEqual(announcer.speakable("TU/Log"), "TU/Log")  # kein „oder“ hinter einer Abkürzung
        # Englische Oberfläche: dieselben Abkürzungen mit englischen Buchstabennamen.
        from morsetrainer import i18n
        with mock.patch.object(i18n, "LANG", "en"):
            self.assertEqual(announcer.speakable("WAG (DOK)"), "double you, ay, gee, dee, oh, kay")
            self.assertEqual(announcer.speakable("IARU HF"), "eye, ay, ar, you aitch, eff")
        # Trainer: Adresse Zahl für Zahl, PIN Ziffer für Ziffer.
        self.assertEqual(announcer.speakable("Adresse 192.168.1.20:7400 · PIN 0815"),
                         "I, Pe Adresse 192 Punkt 168 Punkt 1 Punkt 20, Port 7400, PIN-Nummer Null, Acht, Eins, Fünf")
        self.assertEqual(announcer.speakable("≥ 50 Zeichen, ≤ 3 Fehler"), "mindestens 50 Zeichen, höchstens 3 Fehler")
        self.assertEqual(announcer.speakable("Warte auf den Trainer…"), "Warte auf den Trainer")



class DiplomaAnnounceTest(AnnouncerCase):
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


class ListenAnnounceTest(AnnouncerCase):
    """Reiter Sprechen: angesagt wird nur, was man sonst nur sieht."""

    def test_start_problem_end_and_progress(self):
        from morsetrainer.modes import listen_mode
        self.app.announcer.var.set(True)
        listen = self.mode("Sprechen")
        with mock.patch.object(listen, "_options", lambda: listen.status_var.set("Kein Zeichensatz") or None):
            listen.start()
        self.assertTrue(self.pump_until(lambda: "Kein Zeichensatz" in self.said))
        # Fortschritt für F11 als „3 von 20“
        self.app.show_mode("Sprechen")
        listen.status_var.set("Hör zu …")
        listen.progress_var.set("3/20")
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: any("Hör zu. 3 von 20" in s for s in self.said)), self.said)
        # Restzeit und Zwischenstand in Am Stück und im Contest
        self.app.show_mode("Kontinuierlich")
        self.mode("Kontinuierlich").live_var.set("Gesendet: 40 Zeichen · Restzeit 3:12")
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: any("Restzeit 3 Minuten 12 Sekunden" in s for s in self.said)),
                        self.said)
        self.app.show_mode("Contest")
        self.mode("Contest").score_var.set("QSOs: 5 · richtig: 4 · Rate: 80/h · Rest 1:00")
        self.app._dispatch_key(mock.Mock(keysym="F11", char=""))
        self.assertTrue(self.pump_until(lambda: any("80 pro Stunde, Rest eine Minute" in s for s in self.said)),
                        self.said)
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



# Vor dem Patch in AppTestCase gemerkt, der die Begrüßung sonst abschaltet.
REAL_GREETING = app_module.MorseTrainerApp._greet_first_start


class DialogSpeechTest(AnnouncerCase):
    """Eine wichtige Meldung wird auch bei ausgeschalteter Ansage gesprochen,
    eine gewöhnliche nicht."""

    def open(self, **kwargs):
        from morsetrainer.widgets import dialog
        self.app.announcer.var.set(False)
        del self.said[:]
        message = dialog.MessageDialog(self.root, "Titel", "Wichtiger Text", question=False, **kwargs)
        self.addCleanup(message.close)

    def test_important_message_is_spoken_with_announcer_off(self):
        self.open(always_speak=True)
        self.assertTrue(self.pump_until(lambda: any("Wichtiger Text" in s for s in self.said)))

    def test_ordinary_message_stays_silent_with_announcer_off(self):
        self.open()
        self.assertFalse(self.pump_until(lambda: self.said, timeout=0.5))


class DialogSymbolTest(AnnouncerCase):
    """Warnung und Fehler tragen ein Zeichen vor dem Text; gesprochen wird es nicht."""

    def labels(self, symbol):
        from morsetrainer.widgets import dialog
        message = dialog.MessageDialog(self.root, "Titel", "Text", question=False, symbol=symbol)
        self.addCleanup(message.close)

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        return message, [str(w.cget("text")) for w in walk(message.top) if w.winfo_class() == "TLabel"]

    def test_warning_and_error_show_a_symbol_that_is_not_spoken(self):
        message, texts = self.labels("\u26a0")
        self.assertIn("\u26a0", texts)
        self.assertNotIn("\u26a0", message.spoken)

    def test_plain_message_has_no_symbol(self):
        _message, texts = self.labels("")
        self.assertEqual(texts, ["Text"])

    def test_show_functions_pass_their_symbol(self):
        from morsetrainer.widgets import dialog
        for function, symbol in ((dialog.showwarning, "\u26a0"), (dialog.showerror, "\u2716")):
            with mock.patch.object(dialog, "MessageDialog") as made:
                function("T", "x", parent=self.root)
            self.assertEqual(made.call_args.kwargs["symbol"], symbol)


class DatabaseWarningTest(AnnouncerCase):
    """Der Hinweis auf zu neue Daten kommt vor der Begrüßung und wird gesprochen."""

    def test_warning_is_forced_and_greeting_follows_it(self):
        order = []
        self.app.first_start = True
        with mock.patch.object(app_module.db, "problem", return_value="too_new"), \
                mock.patch.object(app_module.dialog, "showwarning",
                                  lambda *a, **k: order.append(("warnung", k.get("always_speak")))), \
                mock.patch.object(self.app, "_greet_first_start", lambda: order.append(("begrüßung", None))):
            self.app._warn_if_database_too_new()
        self.assertEqual(order, [("warnung", True), ("begrüßung", None)])

    def test_no_warning_still_greets_at_first_start(self):
        order = []
        self.app.first_start = True
        with mock.patch.object(app_module.db, "problem", return_value=None), \
                mock.patch.object(app_module.dialog, "showwarning", lambda *a, **k: order.append("warnung")), \
                mock.patch.object(self.app, "_greet_first_start", lambda: order.append("begrüßung")):
            self.app._warn_if_database_too_new()
        self.assertEqual(order, ["begrüßung"])


class WindowKeysTest(AnnouncerCase):
    """F9 und F11 wirken in jedem Fenster, nicht nur im Hauptfenster."""

    def key(self, widget, keysym):
        return self.app._window_key(mock.Mock(widget=widget, keysym=keysym))

    def test_f9_and_f11_work_in_every_window(self):
        from morsetrainer.widgets import dialog, help_window
        self.assertTrue(self.root.bind_all("<F9>") and self.root.bind_all("<F11>"))
        self.app.open_settings()
        self.app.band_settings.open_window()
        help_window.HelpWindow.show(self.root)
        self.addCleanup(lambda: help_window.HelpWindow._open and help_window.HelpWindow._open.top.destroy())
        self.root.update()
        for window in (self.app.settings_window, self.app.band_settings.window, help_window.HelpWindow._open.top):
            del self.said[:]
            if window.bind("<F11>"):  # eigenes F11 (Bandbedingungen mit Stufe)
                self.assertIsNone(self.key(window, "F11"))
                self.app.band_settings._read_where()
            else:
                self.assertEqual(self.key(window, "F11"), "break")
            self.assertTrue(self.pump_until(lambda: self.said), window)
            self.assertIn("Fenster", " ".join(self.said), window)
            before = self.app.announcer.var.get()
            self.assertEqual(self.key(window, "F9"), "break")
            self.assertNotEqual(self.app.announcer.var.get(), before)
            self.app.announcer.var.set(before)
        # Im Hauptfenster gilt _dispatch_key, Fenster mit eigener Belegung
        # (Meldungen) machen es selbst: nichts doppelt.
        self.assertIsNone(self.key(self.root, "F9"))
        message = dialog.MessageDialog(self.root, "Titel", "Text", question=False)
        self.addCleanup(message.close)
        self.assertIsNone(self.key(message.top, "F11"))

    def test_f9_toggles_once_in_every_window(self):
        # Hauptfenster (über <Key>) und anderes Fenster (über bind_all):
        # je Druck genau ein Umschalten, nicht zwei.
        self.app.open_settings()
        self.root.deiconify()
        self.root.update()
        for window in (self.root, self.app.settings_window):
            window.focus_force()
            self.root.update()
            before = self.app.announcer.var.get()
            window.event_generate("<KeyPress-F9>", when="tail")
            self.root.update()
            self.assertNotEqual(self.app.announcer.var.get(), before, window)

    def test_f9_and_f11_work_with_an_open_drop_down_list(self):
        # Aufgeklappte Klappliste: Tk meldet ihre Liste nur als Pfad.
        self.app.open_settings()
        self.root.update()
        box = self.app.zoom_box
        listbox = str(box) + ".popdown.f.l"
        before = self.app.announcer.var.get()
        self.assertEqual(self.key(listbox, "F9"), "break")
        self.assertNotEqual(self.app.announcer.var.get(), before)
        self.app.announcer.var.set(before)
        del self.said[:]
        self.assertEqual(self.key(listbox, "F11"), "break")
        self.assertTrue(self.pump_until(lambda: self.said))
        spoken = " ".join(self.said)
        self.assertIn("Fenster", spoken)
        self.assertIn(", Auswahl, ", spoken)
        self.assertIsNone(self.key(".unbekannt.popdown.f.l", "F9"))

    def test_open_list_tells_marked_item_and_closing(self):
        # Echt aufgeklappt: F11 nennt den markierten Eintrag (der Wert gilt
        # erst mit Enter), Esc sagt, dass die Liste zu ist und was bleibt.
        self.app.open_settings()
        self.root.update()
        box = self.app.zoom_box
        self.root.tk.call("ttk::combobox::Post", str(box))
        self.root.update()
        listbox = str(box) + ".popdown.f.l"
        self.root.tk.call(listbox, "selection", "clear", 0, "end")
        self.root.tk.call(listbox, "selection", "set", 4)
        marked = str(self.root.tk.call(listbox, "get", 4))
        with mock.patch.object(self.app.announcer, "say") as say:
            self.assertEqual(self.key(listbox, "F11"), "break")
        spoken = say.call_args[0][0]
        self.assertIn("Fenster Einstellungen.", spoken)
        self.assertIn(f"Liste offen. {marked}, 5 von", spoken)
        self.app.announcer.var.set(True)
        with mock.patch.object(self.app.announcer, "say") as say:
            self.root.tk.call("event", "generate", listbox, "<Escape>")
            self.root.update()
        self.assertTrue(say.called)
        self.assertEqual(say.call_args[0][0], f"Liste zu. {box.get()} bleibt.")

    def test_f11_names_the_focused_control(self):
        self.app.open_settings()
        self.root.update()
        window = self.app.settings_window

        def controls(widget):
            for child in widget.winfo_children():
                yield child
                yield from controls(child)

        focus = next(w for w in controls(window) if w.winfo_class() == "TCombobox")
        with mock.patch.object(window, "focus_get", lambda: focus):
            self.app.read_window(window)
        self.pump_until(lambda: self.said)
        spoken = " ".join(self.said)
        self.assertIn("Fenster", spoken)
        self.assertIn(", Auswahl, ", spoken)


class StartProblemTest(AnnouncerCase):
    """Startet ein Reiter nicht, sagt die Ansage warum – sonst merkt man
    ohne Blick auf die Statuszeile nur, dass nichts passiert."""

    def test_start_problems_are_spoken_in_every_mode(self):
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        self.app.charset_var.set("äöü")  # kein Morsezeichen
        for title in ("Einzelzeichen", "Gruppen", "Kontinuierlich"):
            # Erst die vorige Ansage ganz fertig werden lassen: Ihr Thread legt
            # sie sonst womöglich nach dem Leeren noch in den Zwischenspeicher.
            self.assertTrue(self.pump_until(lambda: not self.announcer.speaking()))
            del self.said[:]
            self.app.announcer._cache.clear()  # gleicher Text käme sonst ohne neue Synthese
            self.mode(title).start()
            self.assertFalse(self.mode(title).running, title)
            self.assertTrue(self.pump_until(lambda: any("Kein gültiges Zeichen" in t for t in self.said)), title)
        self.app.charset_var.set("KMUR")  # Buchstaben, aber keine Ziffer
        callsign = self.mode("Rufzeichen")
        callsign.all_calls = []
        del self.said[:]
        callsign.start()
        self.assertTrue(self.pump_until(lambda: any("Rufzeichen" in t for t in self.said)), self.said)
        contest = self.mode("Contest")
        contest.my_call_var.set("")
        del self.said[:]
        contest.start()
        self.assertFalse(contest.running)
        self.assertTrue(self.pump_until(lambda: any("eigenes Rufzeichen" in t for t in self.said)), self.said)
        network = self.mode("Netzwerk")
        network.name_var.set("")
        del self.said[:]
        network.connect()
        self.assertTrue(self.pump_until(lambda: any("Name oder Rufzeichen" in t for t in self.said)), self.said)


class ComboboxListTest(AnnouncerCase):
    """Aufgeklappte Klapplisten sagen beim Blättern den Eintrag an."""

    def test_open_combobox_list_reads_items(self):
        self.app.announcer.var.set(True)
        self.root.deiconify()
        self.pump_until(lambda: False, timeout=0.3)
        combo = ttk.Combobox(self.root, values=["eins", "zwei", "drei"], state="readonly")
        combo.pack()
        combo.current(0)
        self.root.update()
        combo.focus_force()
        self.root.update()
        del self.said[:]
        combo.event_generate("<Down>")  # aufklappen
        self.root.update()
        listbox = f"{self.root.tk.call('ttk::combobox::PopdownWindow', str(combo))}.f.l"
        self.assertTrue(self.pump_until(lambda: any("Liste offen" in t for t in self.said)), self.said)
        self.assertIn("eins, 1 von 3.", " ".join(self.said))
        self.root.tk.call("event", "generate", listbox, "<Down>")
        self.assertTrue(self.pump_until(lambda: any("zwei, 2 von 3." in t for t in self.said)), self.said)
        self.root.tk.call("event", "generate", listbox, "<Escape>")
        self.root.update()


class BandWindowAnnounceTest(AnnouncerCase):
    """Bandbedingungen: Stufen benannt und bestätigt, F11 mit der Stufe,
    Tab beginnt bei den Stufen."""

    def setUp(self):
        super().setUp()
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        self.settings = self.app.band_settings
        self.settings.open_window()
        self.addCleanup(self.settings.close_window)
        self.root.update()

    def preset_buttons(self):
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        return [w for w in walk(self.settings.window) if w.winfo_class() == "TButton"
                and str(w.cget("text")) in ("leicht", "mittel", "stark")]

    def test_band_window_grid_cells_do_not_overlap(self):
        # Zwei Elemente in derselben Rasterzelle überdecken sich (so verschwand
        # einmal „Alle an“ hinter einem Hinweis).
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for container in [self.settings.window, *walk(self.settings.window)]:
            cells = [(int(i["row"]), int(i["column"])) for i in (c.grid_info() for c in container.grid_slaves())]
            self.assertEqual(len(cells), len(set(cells)), container)

    def test_opening_tells_the_focus(self):
        # Der Fokus steht beim Öffnen auf „leicht“; ohne Ansage wüsste man
        # nicht, wo Tab beginnt.
        self.settings.close_window()
        self.pump_until(lambda: False, timeout=0.3)
        with mock.patch.object(self.app.announcer, "say", wraps=self.app.announcer.say) as say:
            self.settings.open_window()
            self.settings.window.event_generate("<Map>")  # Hauptfenster versteckt: Tk zeigt es nicht selbst
            self.pump_until(lambda: False, timeout=0.3)
        spoken = [call.args[0] for call in say.call_args_list]
        self.assertIn("Fenster Bandbedingungen. Stufe leicht, Knopf.", spoken)

    def test_presets_are_named_and_confirmed(self):
        light, medium, heavy = self.preset_buttons()
        self.assertEqual(self.announcer.describe(medium), "Stufe mittel, Knopf.")
        del self.said[:]
        medium.invoke()
        self.assertTrue(self.pump_until(lambda: any("Stufe mittel eingestellt." in t for t in self.said)), self.said)
        self.assertEqual(band_rank(self.settings), "medium")

    def test_noise_slider_says_the_snr_once(self):
        scale = self.settings.widgets["noise"][0]
        self.preset_buttons()[0].invoke()
        self.root.update()
        spoken = self.announcer.describe(scale)
        self.assertEqual(spoken, "Rauschabstand, Regler, +8 dB.")

    def test_f11_tells_the_level(self):
        self.preset_buttons()[2].invoke()
        self.root.update()
        self.assertTrue(self.settings.window.bind("<F11>"))
        del self.said[:]
        self.settings._read_where()
        self.assertTrue(self.pump_until(lambda: self.said))
        spoken = " ".join(self.said)
        self.assertIn("Fenster Bandbedingungen", spoken)
        self.assertIn("Entspricht mindestens Stufe stark", spoken)
        self.assertIn("nicht für die Zeichenstatistik", spoken)

    def test_tab_starts_at_the_levels(self):
        # Erstes Bedienelement im Fenster (Tab-Folge): die Stufe „leicht“,
        # „Band in der Antwortpause“ folgt danach.
        light = self.preset_buttons()[0]
        content = light.master.master  # Tab folgt der Stapelfolge der Kinder
        order = [str(w) for w in content.winfo_children()]
        pause = next(w for w in content.winfo_children() if w.winfo_class() == "TCheckbutton")
        self.assertLess(order.index(str(light.master)), order.index(str(pause)))

    def test_level_feedback_sits_under_the_level_buttons(self):
        # Sichtbar, ob die Wahl gegriffen hat: die Stufen-Rückmeldung gleich
        # unter den Knöpfen, danach die Störungen; die Antwortpause gehört zu
        # keiner Stufe und steht erst dahinter.
        light = self.preset_buttons()[0]
        content = light.master.master
        shown = content.pack_slaves()
        rank = next(w for w in shown if w.winfo_class() == "TLabel"
                    and str(w.cget("textvariable")) == str(self.settings.rank_var))
        pause = next(w for w in shown if w.winfo_class() == "TCheckbutton")
        self.assertEqual(shown.index(rank), shown.index(light.master) + 1)
        cards = [w for w in shown if w.winfo_class() == "TLabelframe"]
        self.assertLess(shown.index(cards[0]), shown.index(pause))


def band_rank(settings):
    from morsetrainer.core import band
    return band.preset_rank(settings.spec())


class StatisticsAnnounceTest(AnnouncerCase):
    """Statistik ohne Maus: Diplome mit Bedingung, Lebenslinie per Pfeiltasten,
    F11 mit Fortschritt und Lebenslinie."""

    def setUp(self):
        super().setUp()
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)

    def test_diploma_row_reads_its_condition(self):
        tree = self.app.awards_panel.tree
        self.app.awards_panel.refresh()
        self.assertTrue(self.announcer.describe(tree).startswith("Diplome, Tabelle"), self.announcer.describe(tree))
        first = tree.get_children()[0]
        tree.selection_set(first)
        self.root.update()
        detail = self.app.awards_panel.detail_var.get()
        self.assertTrue(detail)
        del self.said[:]
        with mock.patch.object(tree, "focus_get", lambda: tree):
            tree.event_generate("<<TreeviewSelect>>")
            self.assertTrue(self.pump_until(lambda: self.said))
        spoken = " ".join(self.said)
        self.assertIn("Diplom:", spoken)
        self.assertIn(detail.split(".")[0][:25], spoken)

    def test_first_row_after_tabbing_in_keeps_name_and_role(self):
        # Die Tabelle wählt beim Tab die erste Zeile und liest sie vor; Name und
        # Rolle (eben angesagt) sind sonst weg.
        tree = ttk.Treeview(self.root, columns=("a",), show="headings")
        tree.heading("a", text="Spalte")
        tree.insert("", "end", values=("Wert",))
        tree.pack()
        self.addCleanup(tree.destroy)
        self.announcer.name(tree, "Meine Tabelle")
        self.app.announcer.var.set(True)
        self.root.update()
        tree.selection_set(tree.get_children()[0])
        instance = self.announcer._instance
        with mock.patch.object(tree, "focus_get", lambda: tree), \
                mock.patch.object(instance, "say", wraps=instance.say) as say:
            self.announcer._say_focus(tree)
            tree.event_generate("<<TreeviewSelect>>")
        spoken = say.call_args_list[-1].args[0]  # die letzte Ansage verdrängt die erste
        self.assertIn("Meine Tabelle, Tabelle", spoken)
        self.assertIn("Spalte: Wert", spoken)

    def _tabbed_table(self):
        tree = ttk.Treeview(self.root, columns=("a",), show="headings")
        tree.heading("a", text="Spalte")
        tree.insert("", "end", values=("Wert",))
        tree.pack()
        self.addCleanup(tree.destroy)
        self.announcer.name(tree, "Meine Tabelle.")
        tree.selection_set(tree.get_children()[0])
        return tree

    def _row_said(self, tree, recent):
        instance = self.announcer._instance
        instance.recent = recent
        with mock.patch.object(tree, "focus_get", lambda: tree), \
                mock.patch.object(instance, "say") as say:
            tree.event_generate("<<TreeviewSelect>>")
        return say.call_args.args[0]

    def test_row_is_not_joined_to_a_foreign_or_old_announcement(self):
        tree = self._tabbed_table()
        intro = self.announcer.speakable(self.announcer.describe(tree))
        self.assertEqual(self._row_said(tree, ("andere Ansage", time.time(), 0)), "Spalte: Wert.")
        self.assertEqual(self._row_said(tree, (intro, time.time() - 5, 0)), "Spalte: Wert.")
        self.assertEqual(self._row_said(tree, None), "Spalte: Wert.")
        joined = self._row_said(tree, (intro, time.time(), 0))
        self.assertTrue(joined.startswith(self.announcer.describe(tree)) and joined.endswith("Spalte: Wert."))
        # Mit Fensterkopf davor gilt es auch.
        self.assertIn("Meine Tabelle, Tabelle", self._row_said(tree, ("Fenster. " + intro, time.time(), 0)))

    def test_table_name_has_no_stray_period_and_says_the_row_count(self):
        tree = self._tabbed_table()
        self.assertTrue(self.announcer.describe(tree).startswith("Meine Tabelle, Tabelle, Pfeiltasten wählen"))
        tree.insert("", "end", values=("Zwei",))
        tree.insert("", "end", values=("Drei",))
        self.assertIn("3 Zeilen, Pfeiltasten wählen eine Zeile", self.announcer.describe(tree))

    def test_errors_speak_the_whole_path_and_other_messages_only_its_last_part(self):
        from tkinter import StringVar
        var = StringVar(master=self.root)
        with mock.patch.object(self.announcer, "say") as say:
            self.announcer.problem(var, "Kein Zugriff auf /media/maik/NAS/x.zip")
        say.assert_called_once_with("Kein Zugriff auf /media/maik/NAS/x.zip", full_paths=True)
        self.assertEqual(self.announcer.speakable("Gespeichert: /media/maik/NAS/x.zip"), "Gespeichert: x.zip")
        self.assertEqual(self.announcer.speakable("Kein Zugriff auf /media/maik/NAS/x.zip", True),
                         "Kein Zugriff auf media, maik, NAS, x.zip")

    def test_error_dialog_passes_full_paths_to_the_voice(self):
        from morsetrainer.widgets import dialog
        with mock.patch.object(self.announcer, "get") as get:
            for full in (True, False):
                box = dialog.MessageDialog(self.root, "Titel", "Pfad /a/b/c.txt", question=False, full_paths=full)
                self.addCleanup(box.top.destroy)
                self.assertEqual(get.return_value.say.call_args.kwargs["full_paths"], full)

    def test_lifeline_days_with_the_arrow_keys(self):
        from datetime import date, timedelta
        panel = self.app.lifeline_panel
        # Auffrischen und Neuzeichnen im Hintergrund (Diplome nach dem Start)
        # überschrieben sonst die Testdaten.
        for name in ("refresh", "draw"):
            patch = mock.patch.object(panel, name, lambda: None)
            patch.start()
            self.addCleanup(patch.stop)
        today = date.today()
        days = [today - timedelta(days=2), today - timedelta(days=1), today]
        panel.line = {"days": days, "stars": [1, 2, 4], "lesson": [3, 3, 4], "tempo": [12, 12, 13], "seals": {}}
        panel.info_var.set("Seit gestern")
        panel.xs = [10, 20, 30]
        del self.said[:]
        panel._step("End", None)
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertIn("Lektion 4", " ".join(self.said))
        self.assertTrue(self.pump_until(lambda: not self.announcer.speaking()))
        del self.said[:]
        self.app.announcer._cache.clear()
        panel._step("Left", -1)
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertIn(days[1].strftime("%d.%m.%Y"), " ".join(self.said))
        self.assertEqual(panel.day_index, 1)
        panel._step("Prior", -7)
        self.assertEqual(panel.day_index, 0)
        self.assertTrue(panel.canvas.bind("<Right>"))
        self.assertIn("Lebenslinie, Diagramm", self.announcer.describe(panel.canvas))

    def test_f11_in_statistics_mentions_progress_and_lifeline(self):
        spoken = self.app.statistics_spoken()
        self.assertIn("Lebenslinie:", spoken)


class VoiceSettingsTest(AnnouncerCase):
    """Sprechtempo und Lautstärke der Ansage einstellbar und gespeichert."""

    def test_rate_reaches_the_voice_and_volume_the_output(self):
        import numpy as np
        from morsetrainer.core import speech
        self.app.announcer.var.set(True)
        rates, played = [], []
        loud = np.full(4800, 0.5, dtype=np.float32)
        with mock.patch.object(speech.speaker, "synth", lambda text, rate=1.0: (rates.append(rate), loud)[1]), \
                mock.patch.object(self.announcer.audio, "play_quietly", lambda samples: played.append(samples)):
            self.app.announcer.rate_var.set(150)
            self.app.announcer.volume_var.set(50)
            self.app.announcer.say("Probe eins.")
            self.assertTrue(self.pump_until(lambda: played))
        self.assertEqual(rates[-1], 1.5)
        self.assertAlmostEqual(float(played[-1].max()), 0.25)

    def test_changing_the_rate_drops_cached_speech(self):
        self.app.announcer._cache["alt"] = object()
        self.app.announcer.rate_var.set(130)
        self.assertNotIn("alt", self.app.announcer._cache)
        self.app.announcer._cache["alt"] = object()
        self.app.announcer.volume_var.set(75)  # Lautstärke wirkt beim Abspielen, Speicher bleibt
        self.assertIn("alt", self.app.announcer._cache)

    def test_speech_made_at_the_old_rate_is_not_kept(self):
        # Ändert sich das Tempo, während eine Ansage noch erzeugt wird, kommt
        # sie nicht in den Speicher; sonst klänge sie später im alten Tempo.
        import numpy as np
        from morsetrainer.core import speech
        announcer = self.app.announcer
        announcer.clear_cache()

        def synth(text, rate=1.0):
            announcer.rate_var.set(140)
            return np.zeros(10, dtype=np.float32)

        with mock.patch.object(speech.speaker, "synth", synth):
            self.assertIsNotNone(announcer._synth("Tempo"))
        self.assertNotIn("Tempo", announcer._cache)

    def test_saved_and_restored(self):
        self.app.announcer.rate_var.set(175)
        self.app.announcer.volume_var.set(25)
        shared = self.app._shared_settings()
        self.assertEqual((shared["announce_rate"], shared["announce_volume"]), (175, 25))

    def test_real_voice_speaks_faster(self):
        from morsetrainer.core import speech
        voice = speech.Speaker()
        if voice.available() is not None:
            self.skipTest("keine Stimme")
        normal = len(voice.synth("Guten Abend, das ist eine Probe."))
        fast = len(voice.synth("Guten Abend, das ist eine Probe.", rate=1.5))
        self.assertLess(fast, normal * 0.9)  # Pausen bleiben, daher nicht ganz 1/1,5


class SmallAnnounceTest(AnnouncerCase):
    """Kleinere Lücken der Ansage (G1–G7 der Erstprüfung)."""

    def test_spoken_forms(self):
        speakable = self.announcer.speakable
        self.assertEqual(speakable("Einstellungen … (Strg+,)"), "Einstellungen, Strg+Komma")
        self.assertEqual(speakable("20/10 WPM"), "20 WPM, effektiv 10")
        self.assertEqual(speakable("Richtig: 3 / 10"), "Richtig: 3 von 10")
        self.assertEqual(speakable("im Filter S/N +8 dB"), "im Filter Rauschabstand plus 8 dB")
        self.assertEqual(speakable("S/N −4 dB"), "Rauschabstand minus 4 dB")
        self.assertEqual(speakable("Lautstärke 80\u00a0%"), speakable("Lautstärke 80 %"))
        self.assertEqual(speakable("Alt+1, Strg+B, Taste +"), "Alt+1, Strg+B, Taste Plus")

    def test_ready_text_names_f5(self):
        for title in ("Einzelzeichen", "Gruppen", "Kontinuierlich"):
            self.assertIn("F5", self.mode(title).status_var.get(), title)

    def test_more_options_and_restart_hint_are_spoken(self):
        self.app.announcer.var.set(True)
        before = self.app.more_var.get()
        self.app._toggle_more()
        expected = "Weitere Optionen aufgeklappt." if not before else "Weitere Optionen zugeklappt."
        self.assertTrue(self.pump_until(lambda: any(expected in t for t in self.said)), self.said)
        self.app._toggle_more()

    def test_new_speaking_rate_is_heard_at_once(self):
        # Die Bestätigung „130 Prozent.“ kommt schon im neuen Tempo: sie ist
        # selbst die Hörprobe, ein eigener Probesatz braucht es nicht.
        import numpy as np
        from morsetrainer.core import speech
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        self.app.open_settings()
        self.root.update()

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        box = next(w for w in walk(self.app.settings_window)
                   if w.winfo_class() == "TCombobox" and self.announcer.describe(w).startswith("Sprechtempo"))
        rates = []
        with mock.patch.object(speech.speaker, "synth",
                               lambda text, rate=1.0: (rates.append((text, rate)), np.zeros(4800, np.float32))[1]), \
                mock.patch.object(box, "focus_get", lambda: box):  # Fenster im Test nicht gezeichnet
            box.set("130 %")
            box.event_generate("<<ComboboxSelected>>")
            self.assertTrue(self.pump_until(lambda: rates))
        self.assertIn("130", rates[-1][0])
        self.assertAlmostEqual(rates[-1][1], 1.3)
        self.app.announcer.rate_var.set(100)

    def test_settings_open_on_the_first_control(self):
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        window = self.app.settings_window
        self.app.open_settings()
        window.event_generate("<Map>")  # Hauptfenster versteckt: Tk zeigt es nicht selbst
        self.pump_until(lambda: False, timeout=0.3)
        first = self.app.settings_first
        self.assertEqual(window.focus_lastfor(), first)
        # Gesprochen wird die letzte Ansage; die Fensteransage steht vorn dran.
        self.assertEqual(self.app.announcer.recent[0],
                         f"Fenster Einstellungen. {self.announcer.speakable(self.announcer.describe(first))}")
        self.app.close_settings()

    def test_settings_reopened_say_the_window_once(self):
        self.app.announcer.var.set(True)
        self.app.open_settings()
        self.root.update()
        self.pump_until(lambda: False, timeout=0.5)
        self.assertTrue(self.pump_until(lambda: not self.announcer.speaking()))
        del self.said[:]
        self.app.announcer._cache.clear()
        self.app.open_settings()  # schon offen: nur nach vorn, einmal „Fenster Einstellungen.“
        self.assertTrue(self.pump_until(lambda: self.said))
        self.assertEqual(self.app.announcer.recent[0].count("Einstellungen"), 1, self.app.announcer.recent)

    def test_new_character_card_spells_the_character(self):
        from morsetrainer.core import daily, koch
        self.app.charset_var.set(koch.lesson_charset(12))
        self.app.announcer.var.set(True)
        with mock.patch.object(daily, "is_new_lesson", lambda state, today: True), \
                mock.patch.object(self.app, "_play_new_char", lambda *_: None):
            self.app.daily.start()
        char = koch.newest_char(daily.load()["lesson"])
        self.assertIn(f"Neues Zeichen: {self.announcer.spell(char)}.", self.app.daily.card_text)
        self.app.daily.abort(quiet=True)

    def test_closing_summary_and_diploma_gives_focus_back(self):
        from morsetrainer.core import awards
        from datetime import date
        from morsetrainer.widgets.awards_panel import DiplomaWindow
        self.root.deiconify()
        self.app.show_mode("Gruppen")
        entry = self.mode("Gruppen").entry
        entry.state(["!disabled"])
        entry.focus_force()
        self.root.update()
        self.assertIs(self.root.focus_get(), entry)
        award = awards.AWARDS[0]
        window = DiplomaWindow(self.root, [(award.key, 0, date(2026, 10, 12))], self.app.station_call_var,
                               self.app.station_name_var)
        self.root.update()
        window.window.focus_force()  # wie mit Fenstermanager: das neue Fenster hat den Fokus
        self.root.update()
        self.assertIsNot(self.root.focus_get(), entry)
        window.close()
        self.root.update()
        self.assertIs(self.root.focus_get(), entry)


class FirstStartTest(AnnouncerCase):
    """Beim allerersten Start erfährt man, wie die Ansage angeht."""

    def greet(self, reader):
        from morsetrainer.core import screenreader
        with mock.patch.object(screenreader, "running", lambda: reader), \
                mock.patch.object(app_module, "SCREEN_READER_GREETING_MS", 50):
            REAL_GREETING(self.app)
            if reader:
                self.assertEqual(self.said, [])  # erst nach der Fensteransage des Screenreaders
        self.pump_until(lambda: False, timeout=0.3)
        return " ".join(self.said)

    def test_first_start_tells_how_to_switch_on(self):
        self.assertTrue(self.app.first_start)
        self.assertFalse(self.app.announcer.var.get())
        spoken = self.greet(reader=False)
        self.assertIn("F9 schaltet die Sprachansage ein.", spoken)
        self.assertIn("F11 sagt, wo du bist.", spoken)
        self.assertIn("F12 startet die Tagesübung.", spoken)
        self.assertNotIn("stumm", spoken)
        self.assertFalse(self.app.announcer.var.get())  # nur gesagt, nicht eingeschaltet

    def test_screen_reader_switches_it_on(self):
        spoken = self.greet(reader=True)
        self.assertTrue(self.app.announcer.var.get())
        self.assertIn("weil ein Screenreader läuft", spoken)
        self.assertIn("F12 startet die Tagesübung.", spoken)
        self.assertIn("Stell den Screenreader beim Üben stumm", spoken)

    def test_screen_reader_detection_says_no_on_errors(self):
        import subprocess
        from morsetrainer.core import screenreader
        answer = mock.Mock(returncode=0, stdout="true\n")
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch.object(screenreader, "_orca_process", lambda: False):
            with mock.patch.object(subprocess, "run", lambda *a, **k: answer):
                self.assertTrue(screenreader.running())
            with mock.patch.object(subprocess, "run", mock.Mock(side_effect=FileNotFoundError)):
                self.assertFalse(screenreader.running())
            with mock.patch.object(subprocess, "run", mock.Mock(side_effect=subprocess.TimeoutExpired("x", 1))):
                self.assertFalse(screenreader.running())

    def test_screen_reader_detection_reads_odd_process_names(self):
        # Ein Prozessname, der kein UTF-8 ist, darf die Suche nach Orca nicht abbrechen.
        import tempfile
        from pathlib import Path
        from morsetrainer.core import screenreader
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(screenreader, "Path", lambda path: Path(tmp)):
                for pid, name in (("1", b"\xff\xfe\n"), ("2", b"orca\n")):
                    (Path(tmp) / pid).mkdir()
                    (Path(tmp) / pid / "comm").write_bytes(name)
                    self.assertEqual(screenreader._orca_process(), name == b"orca\n")

    def test_screen_reader_detection_uses_the_system_libraries(self):
        # Im AppImage zeigt LD_LIBRARY_PATH auf die mitgelieferten Bibliotheken;
        # gsettings bekommt den ursprünglichen Wert.
        from morsetrainer.core import screenreader
        env = {"LD_LIBRARY_PATH": "/tmp/_MEI/lib", "LD_LIBRARY_PATH_ORIG": "/usr/lib", "HOME": "/home/x"}
        with mock.patch.dict(screenreader.os.environ, env, clear=True):
            self.assertEqual(screenreader._system_env()["LD_LIBRARY_PATH"], "/usr/lib")
        with mock.patch.dict(screenreader.os.environ, {"LD_LIBRARY_PATH": "/tmp/_MEI/lib"}, clear=True), \
                mock.patch.object(sys, "frozen", True, create=True):
            self.assertNotIn("LD_LIBRARY_PATH", screenreader._system_env())

    def test_later_starts_are_quiet(self):
        from morsetrainer import app as app_module
        self.app._save_state()
        self.assertTrue(app_module.WINDOW_STATE_FILE.exists())
        self.assertTrue(self.app._load_state())  # beim nächsten Start: first_start False


class HelpReadingTest(AnnouncerCase):
    """Die Hilfe ohne Hinsehen: Fokus im Text, Pfeiltasten lesen Absatz für
    Absatz, ein Suchtreffer liest seine Zeile."""

    def setUp(self):
        super().setUp()
        from morsetrainer.widgets import help_window
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        help_window.HelpWindow.show(self.root, "Einzeln")
        self.window = help_window.HelpWindow._open
        self.addCleanup(lambda: self.window.top.winfo_exists() and self.window.top.destroy())
        self.text = self.window.texts[help_window.GUIDE]

    @staticmethod
    def walk(widget):
        for child in widget.winfo_children():
            yield child
            yield from HelpReadingTest.walk(child)

    def spoken_after(self, action):
        del self.said[:]
        action()
        self.pump_until(lambda: False, timeout=0.3)
        return " ".join(self.said)

    def test_tab_out_of_the_help_text_is_announced(self):
        self.pump_until(lambda: False, timeout=0.3)
        target = self.text.tk_focusNext()
        spoken = self.spoken_after(lambda: self.text.event_generate("<Tab>"))
        self.assertEqual(str(self.text.tk.call("focus")), str(target))
        self.assertIn(self.announcer.describe(target), spoken)

    def test_help_text_reachable_again_with_tab(self):
        # Einmal mit Tab hinaus und rundherum: Der (gesperrte) Text muss
        # wieder den Fokus bekommen und seinen Absatz sagen.
        self.pump_until(lambda: False, timeout=0.3)
        self.text.focus_set()
        self.root.update()
        order = []
        widget = self.text
        for _ in range(12):
            widget = widget.tk_focusNext()
            order.append(widget)
            if widget is self.text:
                break
        self.assertIs(order[-1], self.text, order)
        # Sichtbar links steht „Online im Browser öffnen“, rechts „Schließen“: Tab in dieser Reihenfolge.
        labels = [str(w.cget("text")) for w in order if w.winfo_class() == "TButton"]
        self.assertEqual(labels, ["Online im Browser öffnen", "Schließen"])
        spoken = self.announcer.describe(self.text)
        self.assertTrue(spoken.startswith("Hilfetext, Textfeld, "), spoken)
        self.assertIn(self.window._line(self.text)[:20], spoken)

    def test_f1_in_the_help_window_returns_to_the_text(self):
        self.pump_until(lambda: False, timeout=0.3)
        search = next(w for w in self.walk(self.window.top) if w.winfo_class() == "TEntry")
        search.focus_set()
        self.root.update()
        from morsetrainer.widgets import help_window
        with mock.patch.object(help_window.announcer, "say") as say:
            self.window.top.event_generate("<F1>")
        self.assertIn("Pfeil runter liest weiter", say.call_args[0][0])
        self.assertEqual(str(self.root.tk.call("focus")), str(self.text))

    def test_help_is_read_with_the_arrow_keys(self):
        self.pump_until(lambda: False, timeout=0.3)
        self.assertIn("Überschrift: Einzeln", " ".join(self.said))
        self.assertIn("Pfeil runter liest weiter", " ".join(self.said))
        self.assertIs(self.root.focus_get() or self.text, self.text)  # ohne Fenstermanager evtl. None
        start = self.text.index("insert")
        spoken = self.spoken_after(lambda: self.text.event_generate("<Down>"))
        line = self.text.get("insert linestart", "insert lineend").strip()
        self.assertNotEqual(self.text.index("insert"), start)
        self.assertTrue(line)
        self.assertIn(line[:30], spoken)
        self.spoken_after(lambda: self.text.event_generate("<Up>"))
        self.assertEqual(self.text.index("insert"), start)
        self.text.mark_set("insert", "end-1c")
        self.assertIn("Ende der Hilfe.", self.spoken_after(lambda: self.text.event_generate("<Down>")))

    def test_search_hit_reads_its_line(self):
        def search():
            self.window.notebook.select(0)
            self.window.search_var.set("Koch-Lektion")
        spoken = self.spoken_after(search)
        pos = self.text.index("match_current.first")
        line = self.text.get(f"{pos} linestart", f"{pos} lineend").strip()
        self.assertIn("Treffer 1 von", spoken)
        self.assertIn(line[:30], spoken)
        self.assertEqual(self.text.index("insert"), self.text.index(f"{pos} linestart"))

    def test_browser_button_opens_this_version(self):
        from morsetrainer.widgets import help_window
        with mock.patch.object(help_window.webbrowser, "open") as browser:
            self.window.open_in_browser()
        url = browser.call_args[0][0]
        self.assertTrue(url.endswith(f"/blob/v{app_module.__version__}/docs/Anleitung.md"), url)

    def test_browser_button_says_what_happened(self):
        from morsetrainer.widgets import help_window
        with mock.patch.object(help_window.webbrowser, "open", lambda url: True):
            spoken = self.spoken_after(self.window.open_in_browser)
        self.assertIn("Im Browser geöffnet", spoken)
        with mock.patch.object(help_window.webbrowser, "open", lambda url: False):
            spoken = self.spoken_after(self.window.open_in_browser)
        self.assertIn("Kein Browser gefunden.", spoken)
        self.assertIn("/docs/Anleitung.md", self.window.search_info_var.get())

    def test_closed_help_is_not_kept(self):
        from morsetrainer.widgets import help_window
        self.window.top.destroy()
        self.assertIsNone(help_window.HelpWindow._open)


class DailyAnnounceTest(AnnouncerCase):
    """Tagesübung mit Ansage: kein Morseton über der Stimme."""

    def setUp(self):
        super().setUp()
        from morsetrainer.core import koch
        self.app.charset_var.set(koch.lesson_charset(12))
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        self.runner = self.app.daily

    def test_daily_block_waits_for_its_announcement(self):
        self.app.show_mode("Kontinuierlich")  # Wechsel zum ersten Block wäre sonst eine Reiteransage
        self.pump_until(lambda: False, timeout=0.3)
        del self.said[:]
        self.runner.start()
        mode = self.runner.mode
        self.assertFalse(mode.running)  # erst ansagen, dann spielen
        self.assertTrue(self.pump_until(lambda: mode.running), self.said)
        spoken = " ".join(self.said)
        self.assertIn("Tagesübung, Aufwärmen: Zeichen, 3 Minuten.", spoken)
        self.assertNotIn("Reiter", spoken)
        others = [t for t in self.app.notebook.tabs() if t != self.app.notebook.select()]
        self.assertTrue(all(self.app.notebook.tab(t, "state") == "disabled" for t in others))

    def test_f11_tells_block_time_and_stars(self):
        self.runner.start()
        self.assertTrue(self.pump_until(lambda: self.runner.mode.running))
        del self.said[:]
        self.app.read_status()
        self.assertTrue(self.pump_until(lambda: self.said))
        spoken = " ".join(self.said)
        from morsetrainer.widgets.daily_panel import mode_name
        mode = mode_name(self.runner.blocks[0])
        self.assertIn(f"Tagesübung, Aufwärmen: {mode}, Block 1 von", spoken)
        self.assertIn("von 10 Minuten", spoken)
        self.assertIn("noch kein Stern", spoken)
        self.assertNotRegex(spoken, r"\d:\d\d")  # Zeit gesprochen, nicht „0:05“

    def test_next_character_waits_for_a_running_announcement(self):
        # Der Esc-Hinweis (oder F11) wird nicht vom nächsten Zeichen abgeschnitten.
        from morsetrainer.widgets import announcer
        self.runner.start()
        mode = self.runner.mode
        self.assertTrue(self.pump_until(lambda: mode.running))
        played = []
        with mock.patch.object(mode, "play_current", lambda: played.append(announcer.speaking())):
            self.app._confirm_daily_end("Escape")
            self.assertTrue(announcer.speaking())
            mode.next_char()
            self.assertEqual(played, [])  # noch nicht
            self.assertTrue(self.pump_until(lambda: played))
        self.assertEqual(played, [False])  # erst nach der Ansage

    def test_only_one_character_waits_for_an_announcement(self):
        # F5 Stop und Start während einer Ansage: danach ein Ablauf, nicht zwei.
        from morsetrainer.widgets import announcer
        self.runner.start()
        mode = self.runner.mode
        self.assertTrue(self.pump_until(lambda: mode.running))
        played = []
        with mock.patch.object(mode, "play_current", lambda: played.append(mode.current_char)):
            self.app._confirm_daily_end("Escape")
            self.assertTrue(announcer.speaking())
            mode.next_char()
            mode.next_char()
            self.assertTrue(self.pump_until(lambda: played))
            self.pump_until(lambda: False, timeout=0.5)
        self.assertEqual(len(played), 1)
        self.assertFalse(mode.next_waiting)

    def test_next_sequence_waits_for_a_running_announcement(self):
        from morsetrainer.widgets import announcer
        mode = self.app.modes[self.app.mode_titles.index("Gruppen")]
        played = []
        with mock.patch.object(mode, "next_sequence", wraps=mode.next_sequence), \
                mock.patch.object(mode, "_generate_sequence",
                                  lambda: played.append(announcer.speaking()) or "ABCDE"):
            mode.running = True
            self.addCleanup(setattr, mode, "running", False)
            self.app.announcer.say("Eine Ansage, die gerade läuft.")
            self.assertTrue(announcer.speaking())
            mode.next_sequence()
            mode.next_sequence()
            self.assertEqual(played, [])  # noch nicht
            self.assertTrue(self.pump_until(lambda: played))
            mode.running = False  # nichts weiter abspielen
            self.pump_until(lambda: False, timeout=0.5)
        self.assertEqual(played, [False])  # erst nach der Ansage, und nur einmal

    def test_start_button_during_the_block_announcement_starts_once(self):
        self.runner.start()
        mode = self.runner.mode
        starts = []
        original = mode.start
        with mock.patch.object(mode, "start", lambda: starts.append(1) or original()):
            mode.start()  # Start-Knopf, während der Block noch angesagt wird
            self.assertTrue(self.pump_until(lambda: self.runner.block_started))
        self.assertEqual(len(starts), 1)
        self.assertTrue(mode.running)
        self.assertEqual(str(mode.start_button.cget("text")), "Tagesübung beenden (Esc)")

    def test_abort_during_the_announcement_starts_nothing(self):
        self.runner.start()
        mode = self.runner.mode
        self.runner.abort()
        self.pump_until(lambda: False, timeout=0.5)
        self.assertFalse(self.runner.active)
        self.assertFalse(mode.running)
        self.assertTrue(all(self.app.notebook.tab(t, "state") == "normal" for t in self.app.notebook.tabs()))

    def test_new_character_plays_after_the_card(self):
        from morsetrainer.core import daily
        played = []
        with mock.patch.object(daily, "is_new_lesson", lambda state, today: True), \
                mock.patch.object(self.app, "_play_new_char", lambda *_: played.append(len(self.said))):
            self.runner.start()
            self.assertTrue(self.pump_until(lambda: played))
        self.assertIn("Neues Zeichen", " ".join(self.said[:played[0]]))
        self.assertIn("Weiter mit Enter.", " ".join(self.said[:played[0]]))

    def test_new_character_is_dropped_when_the_card_was_continued(self):
        # Enter auf der Karte, bevor ihre Ansage zu Ende ist: Das Vorspielen
        # entfällt, sonst liefe es gleichzeitig mit dem ersten Zeichen des Blocks.
        from morsetrainer import daily_runner
        from morsetrainer.core import daily
        played = []
        with mock.patch.object(daily, "is_new_lesson", lambda state, today: True), \
                mock.patch.object(self.app, "_play_new_char", lambda *_: played.append(True)):
            self.runner.start()
            self.assertTrue(self.runner.card_open)
            self.runner.card_shown -= daily_runner.ENTER_GRACE_S
            self.runner.continue_now()
            mode = self.runner.mode
            self.assertTrue(self.pump_until(lambda: mode.running))
            self.pump_until(lambda: False, timeout=0.5)
        self.assertEqual(played, [])
        self.runner.abort(quiet=True)


class FocusReturnTest(AppTestCase):
    """Nach Rückfrage, Einstellungen, Bandfenster und Hilfe geht der Fokus
    dorthin zurück, wo er vorher war. Ohne Fenstermanager klappt das nur mit
    focus_force; hier zählt deshalb, wem er zurückgegeben wird."""

    def setUp(self):
        super().setUp()
        self.entry = ttk.Entry(self.root)
        self.entry.pack()
        self.root.update()
        self.returned = []
        for patch in (mock.patch.object(self.root, "focus_get", return_value=self.entry),
                      mock.patch.object(self.entry, "focus_force", lambda: self.returned.append("entry")),
                      mock.patch.object(self.entry, "winfo_viewable", lambda: True),  # Hauptfenster im Test versteckt
                      mock.patch.object(self.root, "focus_force", lambda: self.returned.append("root"))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_dialog_returns_focus(self):
        from morsetrainer.widgets import dialog
        window = dialog.MessageDialog(self.root, "Frage", "Weiter?", question=True)
        window.keys["<Escape>"]()
        self.assertEqual(self.returned, ["entry"])

    def test_settings_return_focus(self):
        self.app.open_settings()
        self.app.close_settings()
        self.assertEqual(self.returned, ["entry"])

    def test_band_window_returns_focus(self):
        self.app.band_settings.open_window()
        self.app.band_settings.close_window()
        self.assertEqual(self.returned, ["entry"])

    def test_help_returns_focus_only_if_it_had_it(self):
        from morsetrainer.widgets import help_window
        help_window.HelpWindow.show(self.root, "Einzeln")
        window = help_window.HelpWindow._open
        with mock.patch.object(window.top, "focus_get", return_value=None):
            window.top.destroy()
        self.assertEqual(self.returned, ["entry"])
        del self.returned[:]
        help_window.HelpWindow.show(self.root, "Einzeln")
        window = help_window.HelpWindow._open
        with mock.patch.object(window.top, "focus_get", return_value=self.entry):  # schon im Hauptfenster
            window.top.destroy()
        self.assertEqual(self.returned, [])

    def test_focus_keeper_falls_back_to_the_main_window(self):
        from morsetrainer.widgets.ui_widgets import focus_keeper
        restore = focus_keeper(self.root)
        self.entry.destroy()
        restore()
        self.assertEqual(self.returned, ["root"])


class DialogTest(AnnouncerCase):
    """Meldungen und Ja/Nein-Fragen (widgets/dialog.py) statt messagebox:
    angesagt, Enter und Escape entscheiden, die Leertaste nicht."""

    def open(self, question=True):
        from morsetrainer.widgets import dialog
        window = dialog.MessageDialog(self.root, "Nächste Koch-Lektion", "Mit Lektion 5 weitermachen?",
                                      question=question)
        self.addCleanup(window.close)
        return window

    def key(self, window, sequence):
        """Die Bindung des Fensters für `sequence` ausführen, wie ein Tastendruck."""
        self.assertTrue(window.top.bind(sequence), sequence)
        window.keys[sequence]()

    def button(self, window, text):
        frame = window.top.winfo_children()[0].winfo_children()[1]
        return [w for w in frame.winfo_children() if w.cget("text") == text][0]

    def test_questions_are_spoken_and_answer_only_with_enter_or_escape(self):
        self.app.announcer.var.set(True)
        window = self.open()
        self.assertTrue(self.pump_until(lambda: any("Mit Lektion 5 weitermachen?" in s for s in self.said)),
                        self.said)
        self.assertTrue(any("Enter: ja. Escape: nein." in s for s in self.said), self.said)
        self.key(window, "<Return>")
        self.assertTrue(window.answer)
        self.assertFalse(window.top.winfo_exists())
        window = self.open()
        self.key(window, "<Escape>")
        self.assertFalse(window.answer)
        self.assertFalse(window.top.winfo_exists())

    def send(self, window, key):
        """Eine Taste als echtes Ereignis an das Element mit Fokus im Dialog
        (sonst an das Fenster): über Fokus, Bindungsreihenfolge und
        Klassenbindungen, nicht an der Bindung vorbei."""
        self.root.update()
        target = self.root.focus_displayof()
        if target is None or target.winfo_toplevel() is not window.top:
            window.top.focus_force()
            self.root.update()
            target = window.top
        target.event_generate(key, when="now")
        self.root.update()

    def test_long_message_stays_narrower_than_the_screen_at_200_percent(self):
        # Der Umbruch wächst mit der Schrift; auf 1024 px Breite darf das Fenster
        # (Hinweis zur Datenbank beim Start) trotzdem nicht darüber hinausragen.
        from morsetrainer.widgets import dialog
        self.root.deiconify()
        self.addCleanup(self.root.withdraw)
        self.addCleanup(theme.set_scale, self.root, theme.scale())
        theme.set_scale(self.root, 200)
        text = i18n.tr(app_module.DATABASE_PROBLEMS["aside"])
        with mock.patch.object(tk.Misc, "winfo_screenwidth", return_value=1024):
            window = dialog.MessageDialog(self.root, "Daten", text, question=False, symbol="⚠")
            self.addCleanup(window.close)
            self.root.update()
        self.assertLessEqual(window.top.winfo_reqwidth(), 1024 - 2 * dialog.SCREEN_GAP + 2 * 14)

    def test_dialog_keys_by_real_events(self):
        # Mit echten Tastenereignissen statt direktem Aufruf der Bindung:
        # Enter = Ja, Escape = Nein, die Leertaste entscheidet nichts, und mit
        # Tab auf „Nein“ gilt Enter diesem Knopf – genau einmal.
        self.root.deiconify()
        self.addCleanup(self.root.withdraw)
        window = self.open()
        self.send(window, "<space>")
        self.assertTrue(window.top.winfo_exists())  # Leertaste aus dem Tippen entscheidet nichts
        self.send(window, "<Return>")
        self.assertTrue(window.answer)
        self.assertFalse(window.top.winfo_exists())

        window = self.open()
        self.send(window, "<Escape>")
        self.assertFalse(window.answer)
        self.assertFalse(window.top.winfo_exists())

        window = self.open()
        self.send(window, "<Tab>")
        self.assertEqual(self.root.focus_get(), self.button(window, "Ja"))  # „Ja“ vor „Nein“
        self.send(window, "<Tab>")
        self.assertEqual(self.root.focus_get(), self.button(window, "Nein"))
        self.send(window, "<Return>")
        self.assertFalse(window.answer)
        self.assertFalse(window.top.winfo_exists())

        window = self.open()
        self.send(window, "<Tab>")  # auf „Ja“: Enter und Leertaste gelten dem Knopf
        self.send(window, "<space>")
        self.assertTrue(window.answer)
        self.assertFalse(window.top.winfo_exists())

        window = self.open(question=False)  # Meldung: Enter schließt
        self.send(window, "<Return>")
        self.assertFalse(window.top.winfo_exists())

    def test_dialog_announcement_keys_by_real_events(self):
        # F11 wiederholt die Ansage, F9 schaltet sie aus und wieder an; der
        # Dialog bleibt dabei offen.
        self.root.deiconify()
        self.addCleanup(self.root.withdraw)
        self.app.announcer.var.set(True)
        window = self.open()
        self.assertTrue(self.pump_until(lambda: any("Mit Lektion 5 weitermachen?" in s for s in self.said)))
        # Erst den Fokus holen und die Fenstertitel-Ansage ausklingen lassen:
        # Eine neue Ansage verdrängt die ältere, F11 käme sonst darunter.
        window.top.focus_force()
        self.pump_until(lambda: False, timeout=0.5)
        # Die Taste muss den Dialog erreichen (nicht erst die Bindung des
        # Hauptfensters): Er wiederholt seine Ansage.
        with mock.patch.object(window, "_say") as say:
            self.send(window, "<F11>")
        say.assert_called_once_with(force=True)
        # Und gesprochen wird der Text noch einmal; er kommt aus dem Sprachspeicher
        # (nicht neu erzeugt, also nicht in self.said), wird aber abgespielt.
        before = len(self.played)
        self.send(window, "<F11>")
        self.assertTrue(self.pump_until(lambda: len(self.played) > before), (self.played, self.said))
        self.send(window, "<F9>")
        self.assertFalse(self.app.announcer.var.get())
        self.send(window, "<F9>")
        self.assertTrue(self.app.announcer.var.get())
        self.assertTrue(self.pump_until(lambda: any(s.startswith("Ansage an.") for s in self.said)), self.said)
        self.assertTrue(window.top.winfo_exists())

    def test_tab_reaches_yes_before_no(self):
        window = self.open()
        # Tab folgt der Reihenfolge, in der die Knöpfe angelegt sind.
        frame = window.top.winfo_children()[0].winfo_children()[1]
        self.assertEqual([w.cget("text") for w in frame.winfo_children()], ["Ja", "Nein"])

    def test_file_dialog_opens_only_after_its_announcement(self):
        # Tks Dateidialog ist stumm: erst ansagen, was kommt, dann öffnen.
        from morsetrainer.widgets import dialog
        self.app.announcer.var.set(True)
        opened, chosen = [], []
        ask = lambda **options: (opened.append(len(self.said)), "/tmp/x.zip")[1]
        with mock.patch.object(dialog.filedialog, "asksaveasfilename", ask):
            dialog.asksaveasfilename(chosen.append, parent=self.root, title="Daten sichern")
            self.assertTrue(self.pump_until(lambda: chosen))
        self.assertEqual(chosen, ["/tmp/x.zip"])
        spoken = " ".join(self.said[:opened[0]])
        self.assertIn("Dateiauswahl Daten sichern.", spoken)
        self.assertIn("Escape: abbrechen.", spoken)

    def test_second_press_during_the_announcement_opens_no_second_dialog(self):
        # Während der Ansage ist nichts zu sehen außer dem Wartezeiger; wer
        # noch einmal drückt, bekommt trotzdem nur einen Dateidialog.
        from morsetrainer.widgets import dialog
        self.app.announcer.var.set(True)
        opened, chosen = [], []
        ask = lambda **options: (opened.append(self.root.cget("cursor")), "/tmp/x.zip")[1]
        with mock.patch.object(dialog.filedialog, "askopenfilename", ask):
            dialog.askopenfilename(chosen.append, parent=self.root, title="Daten einlesen")
            self.assertEqual(self.root.cget("cursor"), "watch")
            dialog.askopenfilename(chosen.append, parent=self.root, title="Daten einlesen")
            self.assertTrue(self.pump_until(lambda: chosen))
            self.pump_until(lambda: False, timeout=0.5)
        self.assertEqual(len(opened), 1)
        self.assertEqual(chosen, ["/tmp/x.zip"])
        self.assertEqual(self.root.cget("cursor"), "")
        with mock.patch.object(dialog.filedialog, "askopenfilename", ask):  # danach wieder frei
            dialog.askopenfilename(chosen.append, parent=self.root, title="Daten einlesen")
            self.assertTrue(self.pump_until(lambda: len(chosen) == 2))

    def test_space_alone_decides_nothing(self):
        # Die Leertaste wirkt nur auf einen Knopf mit Fokus; den hat beim
        # Öffnen keiner, das Fenster selbst kennt sie nicht.
        window = self.open()
        self.assertEqual(window.top.focus_lastfor(), window.top)
        self.assertFalse(window.top.bind("<space>") or window.top.bind("<Key-space>"))
        self.assertTrue(window.top.winfo_exists())

    def test_enter_belongs_to_the_button_with_focus(self):
        self.root.deiconify()  # nur ein sichtbares Fenster merkt sich den Fokus
        window = self.open()
        self.root.update()
        self.button(window, "Nein").focus_force()
        self.root.update()
        self.key(window, "<Return>")
        self.assertFalse(window.answer)
        self.assertFalse(window.top.winfo_exists())

    def test_closing_the_window_means_no(self):
        window = self.open()
        self.root.tk.call(window.top.protocol("WM_DELETE_WINDOW"))
        self.assertFalse(window.answer)

    def test_f11_repeats_and_f9_switches_announcement(self):
        self.app.announcer.var.set(True)
        self.pump_until(lambda: False, timeout=0.3)
        window = self.open(question=False)
        self.assertTrue(self.pump_until(lambda: any("Mit Lektion 5 weitermachen?" in s for s in self.said)))
        self.assertTrue(any("Enter: schließen." in s for s in self.said))
        self.said.clear()
        self.app.announcer.clear_cache()  # sonst käme die Wiederholung ohne synth aus dem Speicher
        self.key(window, "<F11>")
        # Echte Synthese ohne Speicher: auf langsamen CI-Rechnern dauert sie länger als 3 s.
        self.assertTrue(self.pump_until(lambda: any("Mit Lektion 5 weitermachen?" in s for s in self.said), timeout=10))
        self.key(window, "<F9>")
        self.assertFalse(self.app.announcer.enabled())
        self.key(window, "<F9>")
        self.assertTrue(self.app.announcer.enabled())

    def test_app_asks_with_the_spoken_dialog(self):
        from morsetrainer import app as app_module
        from morsetrainer.modes import network_mode
        self.assertFalse(hasattr(app_module, "messagebox"))
        self.assertFalse(hasattr(network_mode, "messagebox"))
