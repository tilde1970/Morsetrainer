"""Lebenslinie im Statistik-Reiter (core/lifeline.py): Sterne gesamt,
Koch-Lektion und Tagestempo übereinander auf einer gemeinsamen
Zeitachse, darunter die Siegel der Diplome als Rauten in ihrer Farbe.
Mit Tab erreichbar: Pfeil links/rechts, Bild auf/ab (eine Woche), Pos1
und Ende gehen durch die Tage und sagen deren Werte an.

Wie beim Fortschritt drei getrennte Diagramme statt mehrerer y-Achsen.
Alle drei sind Stufenlinien: Der Wert gilt, bis er sich ändert. Beim
Überfahren mit der Maus zeigt ein Fadenkreuz über alle drei den Tag mit
seinen Werten und Siegeln."""
import math
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import awards, diploma, koch, lifeline
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.progress_widget import MARGIN, _nice_range

PANEL_TITLE = 24   # Titelzeile plus Luft über der obersten Achsenzahl
PANEL_PLOT = 66
PANEL_GAP = 8
SEAL_ROW = 20
AXIS_ROW = 18
# Bis zu so vielen Tagen stehen Tage an der x-Achse, darüber Monatsanfänge
# mit mindestens MONTH_LABEL_PX Abstand.
DAY_LABELS_MAX = 62
MONTH_LABEL_PX = 70
MONTHS = (N_("Jan"), N_("Feb"), N_("Mär"), N_("Apr"), N_("Mai"), N_("Jun"), N_("Jul"), N_("Aug"), N_("Sep"),
          N_("Okt"), N_("Nov"), N_("Dez"))
SEAL_RADIUS = 5
LESSON_TICKS = (1, 20, koch.FINAL_LESSON)

STARS, LESSON, TEMPO = "stars", "lesson", "tempo"
PANELS = ((STARS, N_("Sterne gesamt")), (LESSON, N_("Koch-Lektion")), (TEMPO, N_("Tagestempo effektiv (WPM)")))
EMPTY_TEXT = {
    STARS: N_("Sterne gibt es in der Tagesübung."),
    LESSON: N_("Noch keine Koch-Lektion geübt."),
    TEMPO: N_("Das Tagestempo kommt mit der ersten Tagesübung."),
}
HEIGHT = len(PANELS) * (PANEL_TITLE + PANEL_PLOT + PANEL_GAP) + SEAL_ROW + AXIS_ROW


def _ticks(key, values):
    if key == LESSON:
        return LESSON_TICKS[0], LESSON_TICKS[-1], LESSON_TICKS
    low, high, step = _nice_range(values, step=max(5, math.ceil(max(values) / 20) * 5))
    low = 0  # Summen und Tempo von null aus: Wachstum nicht übertreiben
    return low, high, [low + i * step for i in range(int((high - low) / step) + 1)]


def value_text(key, value, koch_done=False) -> str:
    """Wert einer Linie als Text: Sterne, Lektion (mit „Koch geschafft“) oder
    Tempo; „–“ ohne Wert."""
    if value is None:
        return "–"
    if key == STARS:
        return f"{value} ★"
    if key == LESSON:
        text = tr("Lektion {n}").format(n=value)
        return text + " (" + tr("Koch geschafft") + ")" if koch_done else text
    return f"{value} WPM"


def seal_text(key, level) -> str:
    """Name eines Siegels: Diplom und Stufe („Koch Gold“)."""
    award = awards.BY_KEY[key]
    name = awards.level_name(award, level)
    return f"{tr(award.name)} {tr(name)}".strip()


def koch_done(line, day) -> bool:
    """An `day` schon die Abschlusslektion bestanden (Gold im Koch-Diplom)?"""
    done = line.get("koch_done")
    return done is not None and done <= day


def summary_text(line) -> str:
    """Kurzfassung über der Lebenslinie: seit wann, und der heutige Stand von
    Sternen, Lektion, Tempo und Siegeln."""
    if not line["days"]:
        return tr("Die Lebenslinie beginnt mit dem ersten Üben.")
    seals = sum(len(v) for d, v in line["seals"].items() if d <= line["days"][-1])
    parts = [value_text(STARS, line["stars"][-1])]
    if line["lesson"][-1] is not None:
        parts.append(value_text(LESSON, line["lesson"][-1], koch_done(line, line["days"][-1])))
    if line["tempo"][-1] is not None:
        parts.append(value_text(TEMPO, line["tempo"][-1]))
    parts.append(tr("1 Siegel") if seals == 1 else tr("{n} Siegel").format(n=seals))
    return tr("Seit {date}: {parts}").format(date=line["days"][0].strftime(tr("%d.%m.%Y")),
                                             parts=" · ".join(parts))


class LifelinePanel:
    """Lebenslinie im Reiter Statistik: drei Linien (Sterne, Lektion, Tempo)
    und die Siegel über alle Tage seit dem ersten Üben; beim Überfahren mit
    der Maus die Werte des Tages."""
    def __init__(self, parent):
        box = theme.card(parent, tr("Lebenslinie"))
        self.info_var = tk.StringVar(value="")
        theme.hint(box, textvariable=self.info_var, wrap=520).pack(anchor="w")
        self.canvas = tk.Canvas(box, height=HEIGHT, background=theme.SURFACE, takefocus=1,
                                highlightthickness=theme.BORDER_WIDTH + 1, highlightcolor=theme.FOCUS,
                                highlightbackground=theme.SURFACE)
        self.canvas.pack(fill="x", pady=(4, 0))
        self.line = {"days": []}
        self.xs = []
        self.day_index = None  # mit der Tastatur gewählter Tag
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda e: self.canvas.delete("hover"))
        announcer.name(self.canvas, tr("Lebenslinie"), value=lambda: self.info_var.get() + ". " + tr(
            "Pfeil links und rechts gehen durch die Tage."))
        for key, step in (("Left", -1), ("Right", 1), ("Prior", -7), ("Next", 7), ("Home", None), ("End", None)):
            self.canvas.bind(f"<{key}>", lambda e, k=key, s=step: self._step(k, s) or "break")

    def refresh(self):
        """Daten neu laden und neu zeichnen."""
        self.line = lifeline.load()
        self.info_var.set(summary_text(self.line))
        self.draw()

    def _x_range(self):
        return MARGIN["left"], self.canvas.winfo_width() - MARGIN["right"]

    def _panel_box(self, index):
        top = index * (PANEL_TITLE + PANEL_PLOT + PANEL_GAP) + PANEL_TITLE
        x0, x1 = self._x_range()
        return x0, top, x1, top + PANEL_PLOT

    def draw(self):
        """Zeichnet alle Linien, die Siegel und die Datumsachse auf die
        aktuelle Breite."""
        c = self.canvas
        c.delete("all")
        days = self.line["days"]
        x0, x1 = self._x_range()
        if not days or x1 <= x0:
            self.xs = []
            return
        n = len(days)
        self.xs = [x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
        for index, (key, title) in enumerate(PANELS):
            self._draw_panel(index, key, tr(title))
        self._draw_seals()
        self._draw_axis()

    def _draw_panel(self, index, key, title):
        """Zeichnet eine Linie (`key`) mit Titel, Achse und Stufen; ohne Werte
        stattdessen einen Hinweis."""
        c = self.canvas
        x0, y0, x1, y1 = self._panel_box(index)
        c.create_text(x0 - MARGIN["left"] + 2, y0 - PANEL_TITLE, text=title, anchor="nw", fill=theme.TEXT,
                      font=theme.SMALL)
        values = self.line[key]
        known = [v for v in values if v is not None]
        if not known or (key == STARS and not any(known)):
            c.create_line(x0, y1, x1, y1, fill=theme.GRID)
            c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=tr(EMPTY_TEXT[key]), fill=theme.MUTED,
                          font=theme.SMALL)
            return
        low, high, ticks = _ticks(key, known)

        def y_of(value):
            return y1 - (value - low) / (high - low) * (y1 - y0)

        for tick in ticks:
            c.create_line(x0, y_of(tick), x1, y_of(tick), fill=theme.GRID)
            c.create_text(x0 - 6, y_of(tick), text=f"{tick:g}", anchor="e", fill=theme.MUTED, font=theme.SMALL)
        # Stufenlinie; vor dem ersten Wert (None) nichts.
        coords = []
        for x, value in zip(self.xs, values):
            if value is None:
                continue
            if coords:
                coords += [x, coords[-1]]
            coords += [x, y_of(value)]
        if len(coords) == 2:
            c.create_oval(coords[0] - 4, coords[1] - 4, coords[0] + 4, coords[1] + 4, fill=theme.ACCENT,
                          outline=theme.SURFACE, width=2)
        else:
            c.create_line(*coords, fill=theme.ACCENT, width=2, joinstyle="round", capstyle="round")
        c.create_text(x1 + 8, coords[-1], text=f"{known[-1]:g}", anchor="w", fill=theme.TEXT, font=theme.HEADING)

    def _seal_y(self):
        return len(PANELS) * (PANEL_TITLE + PANEL_PLOT + PANEL_GAP) + SEAL_ROW / 2

    def _draw_seals(self):
        """Zeichnet die Siegel in ihrer Zeile am Tag, an dem sie erreicht wurden."""
        c = self.canvas
        y = self._seal_y()
        x0, x1 = self._x_range()
        c.create_text(x0 - MARGIN["left"] + 2, y, text=tr("Siegel"), anchor="w", fill=theme.TEXT, font=theme.SMALL)
        index_of = {day: i for i, day in enumerate(self.line["days"])}
        for day, seals in self.line["seals"].items():
            if day not in index_of:
                continue
            x = self.xs[index_of[day]]
            # Mehrere Siegel am selben Tag leicht versetzt, das höchste vorn.
            for k, (key, level) in enumerate(sorted(seals, key=lambda s: s[1])):
                fill, edge = diploma.seal_colors(level, awards.BY_KEY[key].levels)
                dx = (k - (len(seals) - 1) / 2) * 4
                r = SEAL_RADIUS
                c.create_polygon(x + dx, y - r, x + dx + r, y, x + dx, y + r, x + dx - r, y, fill=fill, outline=edge)

    def _draw_axis(self):
        """Datumsachse: bei wenigen Tagen erster, mittlerer und letzter Tag, sonst
        Monatsanfänge mit genug Abstand."""
        c = self.canvas
        days = self.line["days"]
        y = HEIGHT - AXIS_ROW / 2
        n = len(days)
        if n <= DAY_LABELS_MAX:
            for i in sorted({0, n // 2, n - 1}):
                anchor = "w" if i == 0 and n > 1 else "e" if i == n - 1 and n > 1 else "center"
                c.create_text(self.xs[i], y, text=days[i].strftime(tr("%d.%m.")), anchor=anchor, fill=theme.MUTED,
                              font=theme.SMALL)
            return
        months = [i for i, day in enumerate(days) if day.day == 1]
        month_px = (self.xs[-1] - self.xs[0]) / n * 30.4
        step = max(1, math.ceil(MONTH_LABEL_PX / month_px)) if month_px else 1
        for k, i in enumerate(months[::step]):
            day = days[i]
            label = tr(MONTHS[day.month - 1])
            if k == 0 or day.month <= step:  # Jahr beim ersten und beim Jahreswechsel
                label += f" {day.year}"
            c.create_text(self.xs[i], y, text=label, anchor="center", fill=theme.MUTED, font=theme.SMALL)

    def _motion(self, event):
        """Maus über der Lebenslinie: Markierung und Werte des nächstgelegenen Tags
        (mit Siegeln) anzeigen."""
        if not self.xs:
            return
        i = min(range(len(self.xs)), key=lambda k: abs(self.xs[k] - event.x))
        self._show_day(i, event.y)

    def _step(self, key, step):
        """Tastatur: anderen Tag wählen, zeigen und ansagen."""
        if not self.xs:
            announcer.say(self.info_var.get())
            return
        last = len(self.xs) - 1
        if key == "Home":
            index = 0
        elif key == "End" or self.day_index is None:
            index = last
        else:
            index = min(max(self.day_index + step, 0), last)
        self.day_index = index
        self._show_day(index, HEIGHT // 2)
        announcer.say(", ".join(line.replace("◆ ", tr("Siegel") + " ") for line in self.day_lines(index)))

    def day_lines(self, i) -> list:
        """Tag `i` mit seinen Werten und den Siegeln, die an ihm kamen."""
        day = self.line["days"][i]
        lines = [day.strftime(tr("%d.%m.%Y")) + "  ·  " + "  ·  ".join(
            value_text(key, self.line[key][i], koch_done(self.line, day)) for key, _ in PANELS)]
        return lines + ["◆ " + seal_text(key, level) for key, level in self.line["seals"].get(day, [])]

    def _show_day(self, i, y):
        c = self.canvas
        c.delete("hover")
        x = self.xs[i]
        c.create_line(x, 0, x, HEIGHT - AXIS_ROW, fill=theme.MUTED, tags="hover")
        lines = self.day_lines(i)
        text = c.create_text(0, 0, text="\n".join(lines), anchor="nw", fill=theme.TEXT, font=theme.SMALL,
                             tags="hover")
        bx0, by0, bx1, by1 = c.bbox(text)
        w, h = bx1 - bx0 + 10, by1 - by0 + 6
        tx = x + 10 if x + 10 + w < c.winfo_width() else x - 10 - w
        ty = max(2, min(y - h - 10, HEIGHT - AXIS_ROW - h))
        c.coords(text, tx + 5, ty + 3)
        box = c.create_rectangle(tx, ty, tx + w, ty + h, fill=theme.SURFACE, outline=theme.GRID, tags="hover")
        c.tag_raise(text, box)
