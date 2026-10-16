"""Klassische Tk-Widgets, wie Tk 9.1 sie bei laufendem Screenreader statt
der ttk-Widgets baut: Sperren, Zustand und Ansage gehen weiter."""
import tkinter as tk
import unittest
from tkinter import ttk

import tests  # Pfad und sounddevice-Attrappe
from morsetrainer.widgets import announcer, tkcompat


class TkCompatTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()

    def tearDown(self):
        tests.release_root(self.root, owner=self)

    def pairs(self):
        # Gemerkt: Eine eingesammelte Variable löscht ihren Tcl-Wert.
        on = self.on = tk.BooleanVar(self.root, value=True)
        choice = self.choice = tk.StringVar(self.root, value="b")
        return [
            (tk.Checkbutton(self.root, text="Hoher Kontrast", variable=on),
             ttk.Checkbutton(self.root, text="Hoher Kontrast", variable=on), True),
            (tk.Radiobutton(self.root, text="A", value="a", variable=choice),
             ttk.Radiobutton(self.root, text="A", value="a", variable=choice), False),
            (tk.Radiobutton(self.root, text="B", value="b", variable=choice),
             ttk.Radiobutton(self.root, text="B", value="b", variable=choice), True),
            (tk.Spinbox(self.root, from_=0, to=9), ttk.Spinbox(self.root, from_=0, to=9), None),
            (tk.Scale(self.root, from_=0, to=100), ttk.Scale(self.root, from_=0, to=100), None),
        ]

    def test_classic_widgets_behave_like_ttk(self):
        for classic, themed, selected in self.pairs():
            self.root.update_idletasks()  # ttk-Schalter übernehmen den Wert der Variablen
            with self.subTest(classic.winfo_class()):
                self.assertTrue(tkcompat.is_classic(classic))
                self.assertFalse(tkcompat.is_classic(themed))
                self.assertEqual(tkcompat.widget_class(classic), themed.winfo_class())
                for widget in (classic, themed):
                    self.assertTrue(tkcompat.is_enabled(widget))
                    tkcompat.set_enabled(widget, False)
                    self.assertFalse(tkcompat.is_enabled(widget))
                    tkcompat.set_enabled(widget, True)
                    self.assertTrue(tkcompat.is_enabled(widget))
                    if selected is not None:
                        self.assertEqual(tkcompat.is_selected(widget), selected)

    def test_announcer_describes_classic_widgets(self):
        on = tk.BooleanVar(self.root, value=False)
        check = tk.Checkbutton(self.root, text="Hoher Kontrast", variable=on)
        self.assertEqual(announcer.describe(check), "Hoher Kontrast, Schalter, aus.")
        on.set(True)
        tkcompat.set_enabled(check, False)
        self.assertEqual(announcer.describe(check), "Hoher Kontrast, Schalter, an, nicht verfügbar.")


    def test_classic_widgets_take_the_palette(self):
        # Hoher Kontrast: ohne die Farben stünden sie grau auf Schwarz.
        from morsetrainer.widgets import theme
        self.addCleanup(theme.set_palette, theme.PALETTE)
        theme.set_palette("contrast")
        theme.apply(self.root)
        check = tk.Checkbutton(self.root, text="Hoher Kontrast")
        self.assertEqual((str(check.cget("background")), str(check.cget("foreground"))), ("#000000", "#ffffff"))
        self.assertEqual(str(check.cget("highlightcolor")), theme.FOCUS)
        self.assertGreaterEqual(int(check.cget("highlightthickness")), 2)  # Fokus sichtbar
        self.assertEqual(str(tk.Radiobutton(self.root).cget("selectcolor")), theme.SURFACE)
        self.assertEqual(str(tk.Spinbox(self.root).cget("background")), theme.SURFACE)
        self.assertEqual(str(tk.Scale(self.root).cget("troughcolor")), theme.TROUGH)

    def test_field_next_to_a_classic_switch_is_named(self):
        on = self.on = tk.BooleanVar(self.root, value=True)
        row = ttk.Frame(self.root)
        tk.Checkbutton(row, text="Farnsworth, effektiv", variable=on).pack(side="left")
        spin = ttk.Spinbox(row, from_=3, to=39)
        spin.pack(side="left")
        self.assertTrue(announcer.describe(spin).startswith("Farnsworth, effektiv, Zahlenfeld"))


if __name__ == "__main__":
    unittest.main()
