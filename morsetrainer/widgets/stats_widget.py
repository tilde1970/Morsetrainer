"""Shared Tk widget for displaying accuracy, effective speed, and a
per-character error table. Used both for a single session's live stats
and for the cumulative all-time stats, so the layout stays consistent
and isn't duplicated."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core.morse import display_text
from morsetrainer.i18n import tr
from morsetrainer.widgets import theme


class StatsPanel:
    def __init__(self, parent, title=None, tree_height=8, show_save_label=True):
        box = theme.card(parent, title or tr("Statistik (aktueller Durchgang)"))
        summary = ttk.Frame(box)
        summary.pack(fill="x", pady=(0, 6))
        self.stats_var = tk.StringVar(value="0 / 0 (0%)")
        ttk.Label(summary, textvariable=self.stats_var, style="Score.TLabel").pack(side="left")
        self.speed_var = tk.StringVar(value=tr("Ø effektive Geschwindigkeit: –"))
        ttk.Label(summary, textvariable=self.speed_var).pack(side="left", padx=(16, 0))

        theme.hint(box, text=tr("Zeichen, nach Fehlern sortiert")).pack(anchor="w")
        columns = ("char", "good", "wrong", "avg_rt", "avg_wpm", "confusions")
        self.char_tree = ttk.Treeview(box, columns=columns, show="headings", height=tree_height)
        headings = {
            "char": tr("Zeichen", context="Spalte"), "good": tr("Richtig"), "wrong": tr("Falsch"),
            "avg_rt": tr("Ø Zeit (s)"), "avg_wpm": tr("Ø WPM"), "confusions": tr("Verwechselt mit"),
        }
        widths = {"char": 60, "good": 60, "wrong": 55, "avg_rt": 75, "avg_wpm": 60, "confusions": 140}
        for col in columns:
            self.char_tree.heading(col, text=headings[col])
            self.char_tree.column(col, width=widths[col], anchor="w" if col == "confusions" else "center")
        self.char_tree.pack(fill="x", pady=(2, 0))

        self.save_var = tk.StringVar(value="")
        if show_save_label:
            theme.hint(box, textvariable=self.save_var).pack(anchor="w", pady=(4, 0))

    def reset(self):
        self.stats_var.set("0 / 0 (0%)")
        self.speed_var.set(tr("Ø effektive Geschwindigkeit: –"))
        self.save_var.set("")
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)

    def refresh(self, summary: dict, rows: list):
        self.stats_var.set(f"{summary['correct']} / {summary['total']} ({summary['accuracy_pct']:.0f}%)")
        speed = tr("Ø effektive Geschwindigkeit: {wpm:.1f} WPM").format(wpm=summary["avg_effective_wpm"])
        if summary.get("cpm"):
            speed += tr(" · {cpm:.0f} ZpM gemessen").format(cpm=summary["cpm"])
        self.speed_var.set(speed)
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)
        for char, good, wrong, _total, avg_rt, avg_wpm, confusions in rows:
            self.char_tree.insert("", "end", values=(display_text(char), good, wrong, f"{avg_rt:.2f}", f"{avg_wpm:.1f}", confusions))

    def show_saved(self, number, error=None):
        """`number`: Nummer des gespeicherten Durchgangs (SessionStats.finalize)."""
        if error:
            self.save_var.set(tr("Protokoll nicht gespeichert: {error}").format(error=error))
        elif number is not None:
            self.save_var.set(tr("Gespeichert (Durchgang {number})").format(number=number))