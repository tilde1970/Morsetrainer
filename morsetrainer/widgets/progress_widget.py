"""Fortschrittsverlauf im Statistik-Reiter: je Trainingsmodus zwei
Liniendiagramme (Trefferquote und Tempo) über die letzten Durchgänge.

Zwei getrennte Diagramme statt einer zweiten y-Achse; eine Datenreihe je
Diagramm (der Modus wird oben ausgewählt), daher keine Legende. Beim
Überfahren mit der Maus zeigen beide Diagramme synchron Fadenkreuz und
Werte; „Tabelle“ zeigt dieselben Daten als Liste."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import stats
from morsetrainer.i18n import number, short_number, tr
from morsetrainer.widgets import theme

MAX_POINTS = 100
CHART_HEIGHT = 140
MARGIN = {"left": 38, "right": 62, "top": 12, "bottom": 22}
# Punkte nur bis zu dieser Anzahl zeichnen, darüber nur die Linie.
MAX_MARKERS = 40

# Farben aus theme erst beim Zeichnen lesen: die Palette (z. B. hoher
# Kontrast) steht beim Import noch nicht fest.
FONT = theme.SMALL


def _nice_range(values, step: int = 5):
    low = min(values) // step * step
    high = -(-max(values) // step) * step
    if high == low:
        low, high = low - step, high + step
    return max(low, 0), high, step


class _LineChart:
    """Ein Liniendiagramm auf einem Canvas; Achsen- und Hover-Logik."""

    def __init__(self, parent, title: str, unit: str, fixed_range=None, on_hover=None):
        ttk.Label(parent, text=title, font=theme.HEADING).pack(anchor="w", pady=(6, 2))
        self.canvas = tk.Canvas(parent, height=CHART_HEIGHT, background=theme.SURFACE, highlightthickness=0)
        self.canvas.pack(fill="x", pady=(2, 4))
        self.unit = unit
        self.fixed_range = fixed_range
        self.on_hover = on_hover
        self.points = []   # [(x, y, Wert, Eintrag)]
        self.entries, self.values = [], []
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda e: self.on_hover and self.on_hover(None))

    def set_data(self, entries, values):
        """Neue Datenreihe (`entries` mit den Werten `values`) übernehmen und neu
        zeichnen."""
        self.entries, self.values = entries, values
        self.draw()

    def _plot_box(self):
        width = self.canvas.winfo_width()
        return (MARGIN["left"], MARGIN["top"], width - MARGIN["right"], CHART_HEIGHT - MARGIN["bottom"])

    def draw(self):
        """Zeichnet Raster, Linie und Punkte auf die aktuelle Breite; ohne Werte
        einen Hinweis."""
        c = self.canvas
        c.delete("all")
        self.points = []
        if not self.values:
            c.create_text(c.winfo_width() / 2, CHART_HEIGHT / 2, text=tr("Noch keine Daten für diesen Modus."),
                          fill=theme.MUTED, font=FONT)
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
            c.create_line(x0, y, x1, y, fill=theme.GRID, width=1)
            c.create_text(x0 - 6, y, text=short_number(tick), anchor="e", fill=theme.MUTED, font=FONT)
            tick += step

        n = len(self.values)
        for i, (entry, value) in enumerate(zip(self.entries, self.values)):
            x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
            self.points.append((x, y_of(value), value, entry))

        # x-Beschriftung: Datum des ersten, mittleren und letzten Durchgangs
        # (Uhrzeit, wenn alle am selben Tag liegen).
        same_day = self.entries[0]["time"].date() == self.entries[-1]["time"].date()
        time_format = "%H:%M" if same_day else tr("%d.%m.")
        for i in sorted({0, n // 2, n - 1}):
            x = self.points[i][0]
            anchor = "w" if i == 0 and n > 1 else "e" if i == n - 1 and n > 1 else "center"
            c.create_text(x, y1 + 12, text=self.entries[i]["time"].strftime(time_format), anchor=anchor,
                          fill=theme.MUTED, font=FONT)

        if n > 1:
            c.create_line(*[coord for x, y, _, _ in self.points for coord in (x, y)], fill=theme.ACCENT, width=2,
                          joinstyle="round", capstyle="round")
        if n <= MAX_MARKERS:
            for x, y, _, _ in self.points:
                # 8-px-Punkt mit 2-px-Ring in Flächenfarbe.
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=theme.ACCENT, outline=theme.SURFACE, width=2)
        # Direkte Beschriftung nur am letzten Wert, in Textfarbe.
        x, y, value, _ = self.points[-1]
        c.create_text(x + 8, y, text=f"{short_number(value)}{self.unit}", anchor="w", fill=theme.TEXT,
                      font=theme.HEADING)

    def _motion(self, event):
        if not self.points or self.on_hover is None:
            return
        nearest = min(range(len(self.points)), key=lambda i: abs(self.points[i][0] - event.x))
        self.on_hover(nearest)

    def show_hover(self, index):
        """Markiert den Punkt Nr. `index` mit Datum und Wert (None: Markierung weg)."""
        c = self.canvas
        c.delete("hover")
        if index is None or index >= len(self.points):
            return
        x, y, value, entry = self.points[index]
        x0, y0, x1, y1 = self._plot_box()
        c.create_line(x, y0, x, y1, fill=theme.MUTED, width=1, tags="hover")
        c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=theme.ACCENT, outline=theme.SURFACE, width=2, tags="hover")
        label = f"{entry['time'].strftime(tr('%d.%m. %H:%M'))}  ·  {short_number(value)}{self.unit}"
        text = c.create_text(0, 0, text=label, anchor="nw", fill=theme.TEXT, font=FONT, tags="hover")
        bx0, by0, bx1, by1 = c.bbox(text)
        w, h = bx1 - bx0 + 10, by1 - by0 + 6
        tx = x + 10 if x + 10 + w < c.winfo_width() else x - 10 - w
        ty = max(y0, min(y - h - 6, y1 - h))
        c.coords(text, tx + 5, ty + 3)
        box = c.create_rectangle(tx, ty, tx + w, ty + h, fill=theme.SURFACE, outline=theme.GRID, tags="hover")
        c.tag_raise(text, box)


def span_text(entries) -> str:
    """Wie viele Durchgänge über welchen Zeitraum: „19 Durchgänge am
    30.09.2026“ bzw. „… vom 24.09.2026 bis 07.10.2026 an 6 Tagen“."""
    n, days = len(entries), len({e["time"].date() for e in entries})
    first, last = entries[0]["time"], entries[-1]["time"]
    if days == 1:
        text = tr("1 Durchgang am {date}") if n == 1 else tr("{n} Durchgänge am {date}")
        return text.format(n=n, date=first.strftime(tr("%d.%m.%Y")))
    return tr("{n} Durchgänge vom {first} bis {last} an {days} Tagen").format(
        n=n, first=first.strftime(tr("%d.%m.%Y")), last=last.strftime(tr("%d.%m.%Y")), days=days)


class ProgressPanel:
    """Fortschritt im Reiter Statistik: Trefferquote und Tempo der letzten
    Durchgänge eines Modus als Linien, mit Kurzfassung."""
    def __init__(self, parent):
        box = theme.card(parent, tr("Fortschritt"))

        top = ttk.Frame(box)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(top, text=tr("Modus:")).pack(side="left")
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(top, textvariable=self.mode_var, state="readonly", width=20)
        self.mode_combo.pack(side="left", padx=(4, 8))
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self._show())
        self.table_button = ttk.Button(top, text=tr("Tabelle"), command=self._toggle_table)
        self.table_button.pack(side="right")
        self.info_var = tk.StringVar(value="")
        theme.hint(box, textvariable=self.info_var, wrap=640).pack(anchor="w")

        self.charts = ttk.Frame(box)
        self.charts.pack(fill="x")
        self.accuracy_chart = _LineChart(self.charts, tr("Trefferquote (%)"), " %", fixed_range=(0, 100, 25),
                                         on_hover=self._hover)
        self.wpm_chart = _LineChart(self.charts, tr("Tempo effektiv (WPM)"), " WPM", on_hover=self._hover)

        self.table = ttk.Treeview(box, columns=("time", "accuracy", "wpm", "total"), show="headings", height=8)
        for col, heading, width in (("time", tr("Zeitpunkt"), 130), ("accuracy", tr("Trefferquote"), 100),
                                    ("wpm", tr("Tempo eff. (WPM)"), 110), ("total", tr("Umfang"), 80)):
            self.table.heading(col, text=heading)
            self.table.column(col, width=width, anchor="center")
        self.table_visible = False
        self.history = []

    def refresh(self):
        """Verlauf neu laden; Modusauswahl auf die vorhandenen Modi setzen
        (Standard: der zuletzt trainierte) und anzeigen."""
        self.history = stats.load_history(stats.MIN_HISTORY_TOTAL)
        modes = [m for m in stats.HISTORY_MODES if any(e["mode"] == m for e in self.history)]
        labels = [tr(stats.HISTORY_MODES[m]) for m in modes]
        self.mode_combo.config(values=labels)
        if self.mode_var.get() not in labels:
            # Standard: der zuletzt trainierte Modus.
            latest = self.history[-1]["mode"] if self.history else None
            self.mode_var.set(tr(stats.HISTORY_MODES[latest]) if latest in stats.HISTORY_MODES else labels[0] if labels else "")
        self._show()

    def _mode_key(self):
        return next((k for k, v in stats.HISTORY_MODES.items() if tr(v) == self.mode_var.get()), None)

    def _show(self):
        """Zeigt die letzten MAX_POINTS Durchgänge des gewählten Modus mit
        Kurzfassung (von – bis) in beiden Diagrammen."""
        entries = [e for e in self.history if e["mode"] == self._mode_key()][-MAX_POINTS:]
        self.entries = entries
        if entries:
            first = entries[0]["accuracy_pct"]
            last = entries[-1]["accuracy_pct"]
            text = span_text(entries) + tr(" · Trefferquote {first} % → {last} %, "
                                           "Tempo {wpm_first} → {wpm_last} WPM").format(
                first=short_number(first), last=short_number(last),
                wpm_first=entries[0]["wpm"], wpm_last=entries[-1]["wpm"])
            scores = [e["score"] for e in entries if "score" in e]
            if scores:
                text += tr(" · Punkte zuletzt {last}, bester {best}").format(
                    last=number(scores[-1]), best=number(max(scores)))
            self.info_var.set(text)
        else:
            self.info_var.set(tr("Noch keine abgeschlossenen Durchgänge."))
        self.accuracy_chart.set_data(entries, [e["accuracy_pct"] for e in entries])
        self.wpm_chart.set_data(entries, [e["wpm"] for e in entries])
        for item in self.table.get_children():
            self.table.delete(item)
        for e in reversed(entries):
            self.table.insert("", "end", values=(e["time"].strftime(tr("%d.%m.%Y %H:%M")), f"{short_number(e['accuracy_pct'])} %",
                                                 e["wpm"], e["total"]))

    def _hover(self, index):
        for chart in (self.accuracy_chart, self.wpm_chart):
            chart.show_hover(index)

    def _toggle_table(self):
        self.table_visible = not self.table_visible
        if self.table_visible:
            self.charts.pack_forget()
            self.table.pack(fill="x", pady=4)
            self.table_button.config(text=tr("Diagramm"))
        else:
            self.table.pack_forget()
            self.charts.pack(fill="x")
            self.table_button.config(text=tr("Tabelle"))