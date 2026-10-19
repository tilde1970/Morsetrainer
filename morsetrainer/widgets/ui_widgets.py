"""Wiederverwendbare Tk-Bausteine: scrollbarer Bereich, übersetzte
Klappliste und Optionsfelder in einer Reihe."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.i18n import tr
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.tkcompat import is_enabled, set_enabled


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
    Ansage nennt `role` mit („Inhalt Wörter“). Passen sie bei großer Schrift
    nicht in die Breite der Zeile (`parent`), brechen sie um."""

    GAP = 10  # Abstand zwischen den Feldern (Pixel)

    def __init__(self, parent, variable, values, role: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.variable = variable
        self.keys = list(values)
        self.buttons = []
        self.role = role
        self.rows = []         # Frames je Zeile, siehe _layout
        self.layout = None     # Zahl der Felder je Zeile beim letzten Aufbau
        self.pending = None    # after-ID des nächsten Aufbaus
        for key in self.keys:
            button = ttk.Radiobutton(self, text=tr(key), value=key, variable=variable)
            announcer.name(button, f"{role} {tr(key)}")
            for arrow, step in (("Left", -1), ("Up", -1), ("Right", 1), ("Down", 1)):
                button.bind(f"<{arrow}>", lambda e, d=step: self.step(d) or "break")
            # Größere Schrift ändert die Breite der Felder.
            button.bind("<Configure>", self._reflow, add="+")
            self.buttons.append(button)
        one_tab_stop(self.buttons, variable)
        self._layout()
        parent.bind("<Configure>", self._reflow, add="+")

    def _reflow(self, event=None) -> None:
        if self.pending is None:
            self.pending = self.after_idle(self._layout)

    def _layout(self) -> None:
        """Felder der Reihe nach auf Zeilen verteilen, so viele, wie in die
        Zeile passen (mindestens eins je Zeile)."""
        self.pending = None
        try:
            available = self.master.winfo_width() - self.winfo_x()
        except tk.TclError:
            return
        if available <= 1:  # noch nicht gezeichnet: alles in eine Zeile
            available = float("inf")
        counts, used = [], 0
        for button in self.buttons:
            width = button.winfo_reqwidth() + self.GAP
            if counts and used + width > available:
                counts.append(1)
                used = width
            else:
                if not counts:
                    counts.append(0)
                counts[-1] += 1
                used += width
        if counts == self.layout:
            return
        self.layout = counts
        for button in self.buttons:
            button.pack_forget()
        for row in self.rows:
            row.destroy()
        self.rows = []
        buttons = iter(self.buttons)
        for count in counts:
            row = ttk.Frame(self)
            row.pack(anchor="w")
            self.rows.append(row)
            for _ in range(count):
                button = next(buttons)
                button.pack(in_=row, side="left", padx=(0, self.GAP))
                button.lift(row)  # sonst läge der später angelegte Zeilenrahmen darüber

    def step(self, step: int) -> None:
        """Den nächsten (1) bzw. vorigen (−1) Wert wählen, Fokus mitnehmen
        und ansagen; nicht, solange die Felder gesperrt sind."""
        if not self.buttons or not is_enabled(self.buttons[0]):
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
            set_enabled(button, "disabled" not in statespec)
        return None


def focus_keeper(root):
    """Den Tastaturfokus von jetzt merken (vor dem Öffnen eines Fensters);
    die zurückgegebene Funktion gibt ihn zurück, hilfsweise dem Hauptfenster.
    Ohne Fenstermanager (oder mit manchem) bliebe er sonst nirgends, und
    Tasten wie F11 oder Enter gingen ins Leere."""
    try:
        before = root.focus_get()
    except (KeyError, tk.TclError):  # Fokus in einem Dialog von Tk selbst
        before = None

    # focus_force: Das eben geschlossene Fenster war unseres; ohne
    # Fenstermanager käme der Fokus mit focus_set nicht zurück.
    def restore():
        try:
            if before is not None and before.winfo_exists() and before.winfo_viewable():
                before.focus_force()
            else:
                root.focus_force()
        except tk.TclError:
            pass
    return restore


# Abstand zum Rand, wenn ein Bedienelement in Sicht gerollt wird (Pixel).
FOCUS_MARGIN = 8


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
        # Fokus mit Tab (oder Vorlesen per Tastatur) unterhalb des sichtbaren
        # Teils: hinrollen, sonst arbeitet man bei großer Schrift blind. Die
        # Bindung am Fenster sieht FocusIn aller Bedienelemente darin.
        parent.winfo_toplevel().bind("<FocusIn>", self._follow_focus, add="+")
        # Ebenso die gewählte Zeile einer hohen Tabelle (bei großer Schrift).
        parent.winfo_toplevel().bind("<<TreeviewSelect>>", self._follow_row, add="+")

    def _follow_focus(self, event):
        widget = event.widget
        if not isinstance(widget, tk.Misc) or not str(widget).startswith(str(self.inner) + "."):
            return
        try:
            self.show(widget)
        except tk.TclError:
            pass

    def _follow_row(self, event):
        tree = event.widget
        if not isinstance(tree, ttk.Treeview) or not str(tree).startswith(str(self.inner) + "."):
            return
        try:
            if not tree.selection():
                return
            tree.update_idletasks()
            box = tree.bbox(tree.selection()[0])  # leer, solange die Zeile nicht zu sehen ist
            if box:
                top = tree.winfo_rooty() - self.inner.winfo_rooty() + box[1]
                self._reveal(top, top + box[3])
        except tk.TclError:
            pass

    def follow(self, variable, widget) -> None:
        """Ändert sich `variable` (etwa die Rückmeldung zu einer Antwort), zu
        `widget` hinrollen: Bei großer Schrift läge es sonst unterhalb des
        sichtbaren Teils."""
        def show():
            try:
                widget.update_idletasks()
                self.show(widget)
            except tk.TclError:
                pass
        root = widget.nametowidget(".")  # nach dem Hauptfenster geplant, das ihn auch wieder abbricht
        variable.trace_add("write", lambda *_: root.after_idle(show))

    def show(self, widget):
        """So weit rollen, dass `widget` ganz zu sehen ist (wenn es passt,
        sonst sein Anfang)."""
        top = widget.winfo_rooty() - self.inner.winfo_rooty()
        self._reveal(top, top + widget.winfo_height())

    def _reveal(self, top, bottom):
        """Den Bereich von `top` bis `bottom` (im Inhalt) ins Bild rollen."""
        total = self.inner.winfo_height()
        visible = self.canvas.winfo_height()
        if total <= visible or visible <= 1:
            return
        shown_top = self.canvas.canvasy(0)
        margin = FOCUS_MARGIN
        if top - margin < shown_top:
            target = top - margin
        elif bottom + margin > shown_top + visible:
            target = min(bottom + margin - visible, top - margin)
        else:
            return
        self.canvas.yview_moveto(max(target, 0) / total)

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
