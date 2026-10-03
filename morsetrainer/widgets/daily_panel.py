"""Leiste der Tagesübung über den Reitern.

Ohne laufende Tagesübung: Knopf „▶ Tagesübung“ und die Sterne von heute.
Während der Tagesübung: die drei Abschnitte, Zeitbalken mit
„6:10 von 10 Min“ und die schon verdienten Sterne – ruhig, ohne
Aufleuchten, damit nichts den Blick vom Hören wegzieht."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import daily
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import theme

FULL_STAR, EMPTY_STAR = "★", "☆"
BLOCK_LABELS = {daily.WARMUP: N_("Aufwärmen"), daily.MAIN: N_("Hauptteil"), daily.OUTRO: N_("Ausklang")}


def star_text(stars) -> str:
    return " ".join(FULL_STAR if s in stars else EMPTY_STAR for s in daily.STAR_ORDER)


def minutes_text(minutes: float) -> str:
    seconds = max(int(minutes * 60), 0)
    return f"{seconds // 60}:{seconds % 60:02d}"


class DailyBar:
    def __init__(self, parent, on_start):
        self.frame = ttk.Frame(parent, padding=(10, 6, 10, 2))
        self.frame.columnconfigure(1, weight=1)
        self.idle = ttk.Frame(self.frame)
        self.start_button = ttk.Button(
            self.idle, text=tr("▶ Tagesübung ({minutes} Min)").format(minutes=daily.TOTAL_MINUTES),
            style="Accent.TButton", command=on_start)
        self.start_button.pack(side="left")
        self.today_var = tk.StringVar(value="")
        ttk.Label(self.idle, textvariable=self.today_var).pack(side="left", padx=(10, 0))
        self.note_var = tk.StringVar(value="")
        theme.hint(self.idle, textvariable=self.note_var).pack(side="left", padx=(10, 0))

        self.active = ttk.Frame(self.frame)
        self.active.columnconfigure(1, weight=1)
        ttk.Label(self.active, text=tr("Tagesübung"), style="Score.TLabel").grid(row=0, column=0, sticky="w")
        self.phases_var = tk.StringVar(value="")
        ttk.Label(self.active, textvariable=self.phases_var).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.stars_var = tk.StringVar(value="")
        ttk.Label(self.active, textvariable=self.stars_var, style="Score.TLabel").grid(row=0, column=2, sticky="e")
        self.progress = ttk.Progressbar(self.active, maximum=daily.TOTAL_MINUTES)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 0))
        self.time_var = tk.StringVar(value="")
        theme.hint(self.active, textvariable=self.time_var).grid(row=1, column=2, sticky="e", padx=(8, 0))
        self.show_idle([])

    def pack(self, **options):
        self.frame.pack(fill="x", **options)

    def show_idle(self, stars_today, note: str = "") -> None:
        self.active.pack_forget()
        self.idle.pack(fill="x")
        self.today_var.set(tr("Heute: {stars}").format(stars=star_text(stars_today)))
        self.note_var.set(note)

    def show_active(self) -> None:
        self.idle.pack_forget()
        self.active.pack(fill="x")

    def set_enabled(self, enabled: bool) -> None:
        self.start_button.config(state="normal" if enabled else "disabled")

    def update(self, blocks, current: int, elapsed_minutes: float, stars) -> None:
        """`current`: Index des laufenden Blocks; davor ●, ab dann ○."""
        marks = []
        for index, block in enumerate(blocks):
            mark = "●" if index <= current else "○"
            marks.append(f"{mark} {tr(BLOCK_LABELS[block.kind])}")
        self.phases_var.set(" ── ".join(marks))
        elapsed = min(elapsed_minutes, daily.TOTAL_MINUTES)
        self.progress.config(value=elapsed)
        self.time_var.set(tr("{elapsed} von {total} Min").format(
            elapsed=minutes_text(elapsed), total=daily.TOTAL_MINUTES))
        self.stars_var.set(star_text(stars))
