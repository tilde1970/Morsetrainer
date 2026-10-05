"""Abfrage im QSO-Modus: Tabelle zum Eintragen (normales QSO: Rufzeichen,
Name, QTH, Rapport beider Stationen; Contest: das Log) und der Vergleich
mit dem, was tatsächlich gesendet wurde."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import qso_text
from morsetrainer.i18n import tr
from morsetrainer.widgets import theme



def normalize(text: str, kind: str = qso_text.TEXT) -> str:
    """Vergleichsform einer Eingabe bzw. eines erwarteten Werts. Groß-/
    Kleinschreibung, Leerzeichen und Umlaut-Schreibweise zählen nicht; bei
    Zahlen sind Kurzzahlen (5NN, TT7, KW) und ein mitgeloggter Rapport
    erlaubt."""
    text = text.upper().replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
    text = "".join(ch for ch in text if ch.isalnum() or ch == "/")
    if kind == qso_text.DOK:
        # Führende Null der Nummer zählt nicht: A5 = A05.
        letters = text.rstrip("0123456789")
        return letters + (text[len(letters):].lstrip("0") or "0")
    if kind == qso_text.POWER:
        # „100“, „100W“ und „100 WATT“ sind dasselbe.
        return text.removesuffix("WATT").removesuffix("W")
    if kind == qso_text.NUMBER:
        text = text.replace("KW", "1000")
    if kind in (qso_text.RST, qso_text.NUMBER):
        # Kurzzahlen zulassen: 5NN = 599, TT7 = 007.
        text = text.replace("N", "9").replace("T", "0")
    if kind == qso_text.NUMBER:
        # Mitgeloggter Rapport vor dem Austausch ("599 14") und führende
        # Nullen zählen nicht.
        if len(text) > 3 and text.startswith("599"):
            text = text[3:]
        text = text.lstrip("0") or "0"
    return text


def is_correct(entered: str, expected: str, kind: str) -> bool:
    return normalize(entered, kind) == normalize(expected, kind)


class QuizPanel:
    """Die Tabelle wird pro QSO in reset() neu aufgebaut; `on_checked(correct,
    total)` wird nach „Prüfen“ aufgerufen."""

    def __init__(self, parent, on_checked):
        self.on_checked = on_checked
        self.qso = None
        self.checked = False
        self.box = ttk.LabelFrame(parent, text=tr("Abfrage – was hast du mitbekommen?"), padding=(8, 4, 8, 8))
        self.grid = ttk.Frame(self.box)
        self.grid.pack(fill="x", pady=(0, 6))
        self.vars, self.entries, self.marks = {}, {}, {}

        bottom = ttk.Frame(self.box)
        bottom.pack(fill="x")
        self.check_button = ttk.Button(bottom, text=tr("Prüfen (F8)"), command=self.check)
        self.check_button.pack(side="left")
        self.score_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.score_var, style="Score.TLabel").pack(side="left", padx=12)
        self.fix_var = tk.StringVar(value="")
        ttk.Label(self.box, textvariable=self.fix_var, foreground=theme.ERROR, wraplength=540,
                  justify="left").pack(anchor="w", pady=(4, 0))

    def reset(self, qso) -> None:
        self.qso = qso
        for child in self.grid.winfo_children():
            child.destroy()
        self.vars, self.entries, self.marks = {}, {}, {}
        for col, header in enumerate(qso.quiz_columns):
            ttk.Label(self.grid, text=header, style="Hint.TLabel").grid(row=0, column=1 + 2 * col, columnspan=2, sticky="w")
        for row, (label, cells) in enumerate(qso.quiz_rows, start=1):
            ttk.Label(self.grid, text=label + ":").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
            for col, cell in enumerate(cells):
                if cell is None:
                    continue
                var = tk.StringVar()
                # tk.Entry statt ttk.Entry, damit sich der Hintergrund einfärben lässt.
                entry = tk.Entry(self.grid, textvariable=var, width=13, font=theme.MONO, relief="flat",
                                 highlightthickness=1, highlightbackground=theme.BORDER,
                                 highlightcolor=theme.FOCUS, background=theme.SURFACE)
                entry.grid(row=row, column=1 + 2 * col, sticky="w", pady=1)
                mark = ttk.Label(self.grid, text="", width=2)
                mark.grid(row=row, column=2 + 2 * col, sticky="w", padx=(2, 6))
                self.vars[row - 1, col] = var
                self.entries[row - 1, col] = entry
                self.marks[row - 1, col] = mark
        self.score_var.set("")
        self.fix_var.set("")
        self.checked = False
        self.set_check_enabled(True)

    def set_check_enabled(self, enabled: bool) -> None:
        self.check_button.config(state="normal" if enabled and not self.checked else "disabled")

    def check(self) -> None:
        if self.qso is None or self.checked or str(self.check_button["state"]) == "disabled":
            return
        correct, fixes = 0, []
        for (row, col), var in self.vars.items():
            label, cells = self.qso.quiz_rows[row]
            expected, kind = cells[col]
            ok = is_correct(var.get(), expected, kind)
            correct += ok
            bg = theme.OK_BG if ok else theme.ERROR_BG
            self.entries[row, col].config(background=bg, readonlybackground=bg, state="readonly")
            self.marks[row, col].config(text="✓" if ok else "✗", foreground=theme.OK if ok else theme.ERROR)
            if not ok:
                fixes.append(f"{label} ({self.qso.quiz_columns[col]}): {expected}")
        total = len(self.vars)
        self.score_var.set(tr("{correct} / {total} richtig").format(correct=correct, total=total))
        self.fix_var.set(tr("Richtig wäre: ") + ", ".join(fixes) if fixes else "")
        self.checked = True
        self.set_check_enabled(False)
        self.on_checked(correct, total)