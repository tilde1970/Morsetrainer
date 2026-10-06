"""Wiederverwendbare Tk-Bausteine: scrollbarer Bereich und übersetzte
Klappliste."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.i18n import tr
from morsetrainer.widgets import theme


class ChoiceBox(ttk.Combobox):
    """Klappliste (nur Auswahl) für deutsche Werte, die gespeichert und im
    Code verglichen werden: `variable` hält den deutschen Wert, angezeigt
    wird die Übersetzung (siehe i18n.py)."""

    def __init__(self, parent, variable, values, **kwargs):
        self._shown = tk.StringVar()
        kwargs.setdefault("state", "readonly")
        super().__init__(parent, textvariable=self._shown, **kwargs)
        self.variable = variable
        self.keys = []
        self.set_values(values)
        variable.trace_add("write", lambda *_: self._show_variable())
        self._shown.trace_add("write", lambda *_: self._take_shown())

    def set_values(self, values) -> None:
        """Neue Auswahl (`values`: deutsche Schlüssel, angezeigt übersetzt)."""
        self.keys = list(values)
        self.configure(values=[tr(key) for key in self.keys])
        self._show_variable()

    def _show_variable(self) -> None:
        shown = tr(self.variable.get())
        if self._shown.get() != shown:
            self._shown.set(shown)

    def _take_shown(self) -> None:
        labels = [tr(key) for key in self.keys]
        shown = self._shown.get()
        if shown in labels and self.variable.get() != self.keys[labels.index(shown)]:
            self.variable.set(self.keys[labels.index(shown)])


class ScrollableFrame:
    """Frame mit senkrechter Scrollleiste, falls der Inhalt (z. B. ein
    langes Contest-Log samt Klartext) nicht ins Fenster passt."""

    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0, background=theme.BG)
        self.scroll = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _on_scroll(self, first, last):
        """Scrollleiste nur zeigen, wenn der Inhalt nicht ganz hineinpasst."""
        self.scroll.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scroll.pack_forget()
        elif not self.scroll.winfo_ismapped():
            self.scroll.pack(side="right", fill="y", before=self.canvas)

    def _bind_wheel(self, active: bool):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if active:
                self.canvas.bind_all(sequence, self._on_wheel)
            else:
                self.canvas.unbind_all(sequence)

    def _on_wheel(self, event):
        # Textfelder und Tabellen scrollen selbst.
        if isinstance(event.widget, (tk.Text, ttk.Treeview)):
            return
        if self.canvas.yview() == (0.0, 1.0):
            return
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")
