"""Versteckter Reiter „FSRS-Auswertung“ (Strg+Umschalt+F, auf dem Mac Cmd+Umschalt+F).

Zeigt, ob die Vorhersage des FSRS-Schattenmodells (core/fsrs_shadow.py) den
Anteil flüssiger Treffer besser trifft als das Fach der Lernkartei. Nur für
die Entwicklung: nicht in der Anleitung der Anwender, nicht übersetzt,
beim Start immer zu."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import fsrs_shadow, review
from morsetrainer.widgets import theme
from morsetrainer.widgets.ui_widgets import ScrollableFrame

TAB_NAME = "FSRS-Auswertung"

VERDICTS = {
    "few": "Zu früh für ein Urteil: Es fehlen Entscheidungen mit Vorhersage (mindestens {min}).",
    "fsrs": "FSRS trifft besser als das Fach. Eine Umstellung der Fälligkeit wäre einen Entwurf wert.",
    "box": "Das Fach trifft besser als FSRS. Die Lernkartei bleibt, wie sie ist.",
    "equal": "Kein klarer Unterschied. Die Lernkartei bleibt, wie sie ist.",
}


def report_text(report: dict) -> str:
    """Die Auswertung als Text (feste Schrift, Spalten untereinander)."""
    lines = [f"Entscheidungen im Protokoll: {report['entries']}, davon mit Vorhersage: {report['predicted']}"]
    if report["first"]:
        lines.append(f"Zeitraum: {report['first']} bis {report['last']}")
    lines += ["", VERDICTS[report["verdict"]].format(min=fsrs_shadow.MIN_REPORT)]
    brier = report["brier"]
    if brier:
        lines += ["", "Abweichung der Vorhersage vom Anteil flüssiger Treffer (Brier-Wert, kleiner ist besser):",
                  f"  FSRS-Vorhersage     {brier['fsrs']:.4f}",
                  f"  Fach (je Fach Mittel) {brier['box']:.4f}  (aus denselben Daten, günstig für das Fach)",
                  f"  Gesamtmittel        {brier['mean']:.4f}"]
        lines += ["", "Vorhersage gegen Wirklichkeit, nach vorhergesagter Behaltenswahrscheinlichkeit:",
                  "  Bereich        Anzahl  vorhergesagt  tatsächlich"]
        lines += [f"  {b['low']:.1f} bis {b['high']:.1f}   {b['n']:6d}  {b['p']:12.2f}  {b['actual']:11.2f}"
                  for b in report["bins"]]
        lines += ["", "Nach Fach vor der Entscheidung (Fach 1 bis 6):",
                  "  Fach   Anzahl  vorhergesagt  tatsächlich"]
        lines += [f"  {b['box'] + 1:4d}   {b['n']:6d}  {b['p']:12.2f}  {b['actual']:11.2f}" for b in report["boxes"]]
    return "\n".join(lines)


class FsrsPanel:
    """Inhalt des Reiters; `refresh()` liest das Protokoll neu."""

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        box = theme.card(ScrollableFrame(self.frame).inner, "FSRS-Schattenmodell gegen Lernkartei")
        self.text_var = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.text_var, font=theme.MONO, justify="left").pack(anchor="w", pady=4)
        theme.hint(box, wrap=560, text="Das Schattenmodell schreibt nur mit, es ändert nichts an den Fächern. "
                                       "Dieser Reiter ist versteckt: Strg+Umschalt+F blendet ihn ein und aus."
                   ).pack(anchor="w", pady=(0, 6))
        self.refresh_button = ttk.Button(box, text="Aktualisieren", command=self.refresh)
        self.refresh_button.pack(anchor="w")
        self.refresh()

    def refresh(self) -> None:
        self.text_var.set(report_text(fsrs_shadow.report(review.load_log())))
