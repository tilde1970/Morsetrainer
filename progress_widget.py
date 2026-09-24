"""Fortschrittsverlauf im Statistik-Reiter: je Trainingsmodus zwei
Liniendiagramme (Trefferquote und Tempo) über die letzten Durchgänge.

Zwei getrennte Diagramme statt einer zweiten y-Achse; eine Datenreihe je
Diagramm (der Modus wird oben ausgewählt), daher keine Legende. Beim
Überfahren mit der Maus zeigen beide Diagramme synchron Fadenkreuz und
Werte; „Tabelle“ zeigt dieselben Daten als Liste."""
import tkinter as tk
from tkinter import ttk

import stats

MAX_POINTS = 100
CHART_HEIGHT = 140
MARGIN = {"left": 38, "right": 62, "top": 12, "bottom": 22}
# Punkte nur bis zu dieser Anzahl zeichnen, darüber nur die Linie.
MAX_MARKERS = 40

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES = "#2a78d6"
FONT = ("Sans", 8)


def _nice_range(values, step: int = 5):
    low = min(values) // step * step
    high = -(-max(values) // step) * step
    if high == low:
        low, high = low - step, high + step
    return max(low, 0), high, step


class _LineChart:
    """Ein Liniendiagramm auf einem Canvas; Achsen- und Hover-Logik."""

    def __init__(self, parent, title: str, unit: str, fixed_range=None, on_hover=None):
        ttk.Label(parent, text=title, font=("Sans", 10, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.canvas = tk.Canvas(parent, height=CHART_HEIGHT, background=SURFACE, highlightthickness=0)
        self.canvas.pack(fill="x", padx=8, pady=(2, 4))
        self.unit = unit
        self.fixed_range = fixed_range
        self.on_hover = on_hover
        self.points = []   # [(x, y, Wert, Eintrag)]
        self.entries, self.values = [], []
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda e: self.on_hover and self.on_hover(None))

    def set_data(self, entries, values):
        self.entries, self.values = entries, values
        self.draw()

    def _plot_box(self):
        width = self.canvas.winfo_width()
        return (MARGIN["left"], MARGIN["top"], width - MARGIN["right"], CHART_HEIGHT - MARGIN["bottom"])

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.points = []
        if not self.values:
            c.create_text(c.winfo_width() / 2, CHART_HEIGHT / 2, text="Noch keine Daten für diesen Modus.",
                          fill=TEXT_SECONDARY, font=("Sans", 9))
            return
        x0, y0, x1, y1 = self._plot_box()
        if x1 <= x0:
            return
        low, high, step = self.fixed_range or _nice_range(self.values)
        span = high - low

        def y_of(value):
            return y1 - (value - low) / span * (y1 - y0)

        # Raster und y-Beschriftung (dezent, 1 px, durchgezogen).
        tick = low
        while tick <= high + 1e-9:
            y = y_of(tick)
            c.create_line(x0, y, x1, y, fill=GRID, width=1)
            c.create_text(x0 - 6, y, text=f"{tick:g}", anchor="e", fill=TEXT_SECONDARY, font=FONT)
            tick += step

        n = len(self.values)
        for i, (entry, value) in enumerate(zip(self.entries, self.values)):
            x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
            self.points.append((x, y_of(value), value, entry))

        # x-Beschriftung: Datum des ersten, mittleren und letzten Durchgangs
        # (Uhrzeit, wenn alle am selben Tag liegen).
        same_day = self.entries[0]["time"].date() == self.entries[-1]["time"].date()
        time_format = "%H:%M" if same_day else "%d.%m."
        for i in sorted({0, n // 2, n - 1}):
            x = self.points[i][0]
            anchor = "w" if i == 0 and n > 1 else "e" if i == n - 1 and n > 1 else "center"
            c.create_text(x, y1 + 12, text=self.entries[i]["time"].strftime(time_format), anchor=anchor,
                          fill=TEXT_SECONDARY, font=FONT)

        if n > 1:
            c.create_line(*[coord for x, y, _, _ in self.points for coord in (x, y)], fill=SERIES, width=2,
                          joinstyle="round", capstyle="round")
        if n <= MAX_MARKERS:
            for x, y, _, _ in self.points:
                # 8-px-Punkt mit 2-px-Ring in Flächenfarbe.
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=SERIES, outline=SURFACE, width=2)
        # Direkte Beschriftung nur am letzten Wert, in Textfarbe.
        x, y, value, _ = self.points[-1]
        c.create_text(x + 8, y, text=f"{value:g}{self.unit}", anchor="w", fill=TEXT_PRIMARY,
                      font=("Sans", 9, "bold"))

    def _motion(self, event):
        if not self.points or self.on_hover is None:
            return
        nearest = min(range(len(self.points)), key=lambda i: abs(self.points[i][0] - event.x))
        self.on_hover(nearest)

    def show_hover(self, index):
        c = self.canvas
        c.delete("hover")
        if index is None or index >= len(self.points):
            return
        x, y, value, entry = self.points[index]
        x0, y0, x1, y1 = self._plot_box()
        c.create_line(x, y0, x, y1, fill=TEXT_SECONDARY, width=1, tags="hover")
        c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=SERIES, outline=SURFACE, width=2, tags="hover")
        label = f"{entry['time'].strftime('%d.%m. %H:%M')}  ·  {value:g}{self.unit}"
        text = c.create_text(0, 0, text=label, anchor="nw", fill=TEXT_PRIMARY, font=FONT, tags="hover")
        bx0, by0, bx1, by1 = c.bbox(text)
        w, h = bx1 - bx0 + 10, by1 - by0 + 6
        tx = x + 10 if x + 10 + w < c.winfo_width() else x - 10 - w
        ty = max(y0, min(y - h - 6, y1 - h))
        c.coords(text, tx + 5, ty + 3)
        box = c.create_rectangle(tx, ty, tx + w, ty + h, fill="white", outline=GRID, tags="hover")
        c.tag_raise(text, box)


class ProgressPanel:
    def __init__(self, parent):
        box = ttk.LabelFrame(parent, text="Fortschritt")
        box.pack(fill="x", padx=8, pady=4)

        top = ttk.Frame(box)
        top.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Label(top, text="Modus:").pack(side="left")
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(top, textvariable=self.mode_var, state="readonly", width=20)
        self.mode_combo.pack(side="left", padx=(4, 8))
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self._show())
        self.table_button = ttk.Button(top, text="Tabelle", command=self._toggle_table)
        self.table_button.pack(side="right")
        self.info_var = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.info_var, foreground=TEXT_SECONDARY, wraplength=440,
                  justify="left").pack(anchor="w", padx=8)

        self.charts = ttk.Frame(box)
        self.charts.pack(fill="x")
        self.accuracy_chart = _LineChart(self.charts, "Trefferquote (%)", " %", fixed_range=(0, 100, 25),
                                         on_hover=self._hover)
        self.wpm_chart = _LineChart(self.charts, "Tempo (WPM)", " WPM", on_hover=self._hover)

        self.table = ttk.Treeview(box, columns=("time", "accuracy", "wpm", "total"), show="headings", height=8)
        for col, heading, width in (("time", "Zeitpunkt", 130), ("accuracy", "Trefferquote", 100),
                                    ("wpm", "Tempo (WPM)", 100), ("total", "Umfang", 80)):
            self.table.heading(col, text=heading)
            self.table.column(col, width=width, anchor="center")
        self.table_visible = False
        self.history = []

    def refresh(self):
        self.history = stats.load_history()
        modes = [m for m in stats.HISTORY_MODES if any(e["mode"] == m for e in self.history)]
        labels = [stats.HISTORY_MODES[m] for m in modes]
        self.mode_combo.config(values=labels)
        if self.mode_var.get() not in labels:
            # Standard: der zuletzt trainierte Modus.
            latest = self.history[-1]["mode"] if self.history else None
            self.mode_var.set(stats.HISTORY_MODES.get(latest, labels[0] if labels else ""))
        self._show()

    def _mode_key(self):
        return next((k for k, v in stats.HISTORY_MODES.items() if v == self.mode_var.get()), None)

    def _show(self):
        entries = [e for e in self.history if e["mode"] == self._mode_key()][-MAX_POINTS:]
        self.entries = entries
        if entries:
            first = entries[0]["accuracy_pct"]
            last = entries[-1]["accuracy_pct"]
            self.info_var.set(
                f"{len(entries)} Durchgänge seit {entries[0]['time'].strftime('%d.%m.%Y')} · "
                f"Trefferquote {first:g} % → {last:g} %, Tempo {entries[0]['wpm']} → {entries[-1]['wpm']} WPM"
            )
        else:
            self.info_var.set("Noch keine abgeschlossenen Durchgänge.")
        self.accuracy_chart.set_data(entries, [e["accuracy_pct"] for e in entries])
        self.wpm_chart.set_data(entries, [e["wpm"] for e in entries])
        for item in self.table.get_children():
            self.table.delete(item)
        for e in reversed(entries):
            self.table.insert("", "end", values=(e["time"].strftime("%d.%m.%Y %H:%M"), f"{e['accuracy_pct']:g} %",
                                                 e["wpm"], e["total"]))

    def _hover(self, index):
        for chart in (self.accuracy_chart, self.wpm_chart):
            chart.show_hover(index)

    def _toggle_table(self):
        self.table_visible = not self.table_visible
        if self.table_visible:
            self.charts.pack_forget()
            self.table.pack(fill="x", padx=8, pady=4)
            self.table_button.config(text="Diagramm")
        else:
            self.table.pack_forget()
            self.charts.pack(fill="x")
            self.table_button.config(text="Tabelle")