"""Wiederverwendbare Tk-Bausteine: scrollbarer Bereich, übersetzte
Klappliste und Optionsfelder in einer Reihe."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.i18n import tr
from morsetrainer.widgets import announcer, theme


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


def wrap_pair(container, left, right, gap: int = 16, sticky: str = "e") -> None:
    """`left` und `right` nebeneinander in `container` (`right` rechtsbündig,
    mit sticky="w" gleich anschließend); reicht die Breite nicht (große
    Schrift, schmales Fenster), rutscht `right` in eine zweite Zeile, statt
    sich zu überdecken oder abgeschnitten zu werden."""
    container.columnconfigure(1, weight=1)
    left.grid(row=0, column=0, sticky="w")
    right.grid(row=0, column=1, sticky=sticky, padx=(theme.scaled(gap) if sticky == "w" else 0, 0))

    def update(_event=None):
        fits = left.winfo_reqwidth() + right.winfo_reqwidth() + theme.scaled(gap) <= container.winfo_width()
        wrapped = int(right.grid_info().get("row", 0)) == 1
        if fits and wrapped:
            right.grid(row=0, column=1, columnspan=1, sticky=sticky, pady=0,
                       padx=(theme.scaled(gap) if sticky == "w" else 0, 0))
        elif not fits and not wrapped:
            right.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0), padx=0)

    container.bind("<Configure>", update, add="+")
    # Auch wenn sich nur der Inhalt ändert (längerer Hinweis, andere Schrift).
    for part in (left, right):
        part.bind("<Configure>", update, add="+")


def one_tab_stop(buttons, variable) -> None:
    """Optionsfelder einer Gruppe als ein Tab-Stopp: Tab erreicht nur das
    gewählte, die Pfeiltasten wählen die anderen (wie in Optionsgruppen
    üblich, spart Tastaturnutzern Tabs)."""
    def update(*_):
        values = [str(button.cget("value")) for button in buttons]
        current = variable.get()
        chosen = values.index(current) if current in values else 0
        for index, button in enumerate(buttons):
            button.configure(takefocus=index == chosen)

    variable.trace_add("write", update)
    update()


class ChoiceButtons(ttk.Frame):
    """Optionsfelder nebeneinander für deutsche Werte (wie ChoiceBox, aber
    alle Möglichkeiten auf einen Blick): `variable` hält den deutschen Wert,
    angezeigt wird die Übersetzung. Pfeiltasten wählen den Nachbarn, die
    Ansage nennt `role` mit („Inhalt Wörter“)."""

    def __init__(self, parent, variable, values, role: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.variable = variable
        self.keys = list(values)
        self.buttons = []
        self.role = role
        for key in self.keys:
            button = ttk.Radiobutton(self, text=tr(key), value=key, variable=variable)
            button.pack(side="left", padx=(0, 10))
            announcer.name(button, f"{role} {tr(key)}")
            for arrow, step in (("Left", -1), ("Up", -1), ("Right", 1), ("Down", 1)):
                button.bind(f"<{arrow}>", lambda e, d=step: self.step(d) or "break")
            self.buttons.append(button)
        one_tab_stop(self.buttons, variable)

    def step(self, step: int) -> None:
        """Den nächsten (1) bzw. vorigen (−1) Wert wählen, Fokus mitnehmen
        und ansagen; nicht, solange die Felder gesperrt sind."""
        if not self.buttons or self.buttons[0].instate(["disabled"]):
            return
        current = self.variable.get()
        index = (self.keys.index(current) + step) % len(self.keys) if current in self.keys else 0
        self.variable.set(self.keys[index])
        self.buttons[index].focus_set()
        announcer.say(f"{self.role} {tr(self.keys[index])}.")

    def state(self, statespec=None):
        """Sperren bzw. freigeben wie ein einzelnes ttk-Element."""
        if statespec is None:
            return super().state()
        for button in self.buttons:
            button.state(statespec)
        return None


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
