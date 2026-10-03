"""Diplom-Übersicht im Statistik-Reiter: alle Diplome mit erreichten
Siegeln, dem nächsten Ziel und ab welcher Lektion es erreichbar ist.
Offene Diplome stehen grau; die gewählte Zeile zeigt darunter Bedingung,
Stufen und die Tage der Siegel.

Dazu das Diplom-Fenster für neue Siegel (nach einer Übung, in der
Tagesübung erst nach der Abendbilanz) mit „Drucken“: eine HTML-Seite in
Urkunden-Optik (core/diploma.py), die der Browser druckt."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import awards, diploma, stats
from morsetrainer.i18n import number, tr
from morsetrainer.modes.word_mode import open_in_editor
from morsetrainer.widgets import theme

WRAP = 520
DIPLOMA_FILE_NAME = "diplom.html"
SEAL_SIZE = 56


def _amount(value) -> str:
    return number(int(round(value)))


def seals_text(award, status) -> str:
    reached = [level for level, day in enumerate(status.dates) if day is not None]
    if not reached:
        return "–"
    if not award.levels:
        return tr("erreicht")
    return ", ".join(tr(awards.LEVEL_NAMES[level]) for level in reached)


def next_text(award, status) -> str:
    level = status.next_level
    if level is None:
        return "✓"
    progress = ""
    if status.second_day and award.two_days:
        progress = tr("an einem zweiten Tag wiederholen")
    elif status.progress:
        have, need = status.progress
        progress = tr("{have} / {need} {unit}").format(have=_amount(have), need=_amount(need),
                                                       unit=tr(award.unit)).strip()
    if not award.levels:
        return progress or "–"
    name = tr(awards.LEVEL_NAMES[level])
    return tr("{level}: {progress}").format(level=name, progress=progress) if progress else name


def detail_text(award, status) -> str:
    lines = [tr(award.condition)]
    if award.levels and not award.stepped:
        steps = " · ".join(f"{tr(awards.LEVEL_NAMES[i])} {_amount(t)}" for i, t in enumerate(award.targets))
        lines.append(tr("Stufen: {steps} {unit}").format(steps=steps, unit=tr(award.unit)).strip())
    if award.two_days:
        lines.append(tr("Silber und höher: an zwei verschiedenen Tagen."))
    reached = [(level, day) for level, day in enumerate(status.dates) if day is not None]
    if reached and award.levels:
        seals = ", ".join(tr("{level} am {date}").format(level=tr(awards.LEVEL_NAMES[level]),
                                                         date=day.strftime(tr("%d.%m.%Y")))
                          for level, day in reached)
        lines.append(tr("Erreicht: {seals}").format(seals=seals))
    elif reached:
        lines.append(tr("Erreicht am {date}").format(date=reached[0][1].strftime(tr("%d.%m.%Y"))))
    return "\n".join(lines)


def seal_name(award, level) -> str:
    """„Kopfhörer – Silber“, ohne Stufen nur der Name."""
    if not award.levels:
        return tr(award.name)
    return tr("{award} – {level}").format(award=tr(award.name), level=tr(awards.LEVEL_NAMES[level]))


def diploma_condition(award, level) -> str:
    """Bedingung, bei Stufen mit Schwelle die der erreichten Stufe."""
    text = tr(award.condition)
    if award.levels and not award.stepped:
        text += " – " + tr("{level} ab {target} {unit}").format(
            level=tr(awards.LEVEL_NAMES[level]), target=_amount(award.targets[level]), unit=tr(award.unit)).strip()
    return text


def print_diploma(award, level, day, call: str) -> str:
    """Diplom als HTML-Seite im Browser öffnen; Rückgabe: Meldung."""
    page = diploma.diploma_html(
        tr(award.name), tr(awards.LEVEL_NAMES[level]) if award.levels else "",
        diploma.seal_colors(level, award.levels), diploma_condition(award, level),
        day.strftime(tr("%d.%m.%Y")), call,
        labels={"title": tr("Diplom"), "awarded": tr("verliehen an"), "date": tr("Datum:"),
                "footer": tr("Morsetrainer · entwickelt von DL4YM")})
    path = stats.STATS_DIR / DIPLOMA_FILE_NAME
    try:
        stats.STATS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        open_in_editor(path)
    except OSError as exc:
        return tr("Nicht gespeichert: {error}").format(error=exc)
    return tr("Im Browser geöffnet, dort drucken: {path}").format(path=path)


def draw_seal(parent, award, level) -> tk.Canvas:
    """Rundes Siegel in der Farbe der Stufe."""
    fill, edge = diploma.seal_colors(level, award.levels)
    canvas = tk.Canvas(parent, width=SEAL_SIZE, height=SEAL_SIZE, background=theme.BG, highlightthickness=0)
    canvas.create_oval(3, 3, SEAL_SIZE - 3, SEAL_SIZE - 3, fill=fill, outline=edge, width=4)
    canvas.create_oval(9, 9, SEAL_SIZE - 9, SEAL_SIZE - 9, outline="#ffffff", width=1)
    canvas.create_text(SEAL_SIZE / 2, SEAL_SIZE / 2, text="★", fill=theme.TEXT, font=theme.HEADING)
    return canvas


class DiplomaWindow:
    """Neue Siegel (oder ein gewähltes aus der Übersicht) mit Rufzeichen
    und „Drucken“. `seals`: [(Schlüssel, Stufe, Tag)]."""

    def __init__(self, root, seals, call: str = "", title=None, on_close=None):
        self.seals = seals
        self.on_close = on_close
        self.window = window = tk.Toplevel(root)
        window.title(title or (tr("Neues Siegel") if len(seals) == 1 else tr("Neue Siegel")))
        window.configure(background=theme.BG)
        window.transient(root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        for key, level, day in seals:
            award = awards.BY_KEY[key]
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=(0, 10))
            draw_seal(row, award, level).pack(side="left", padx=(0, 12))
            text = ttk.Frame(row)
            text.pack(side="left", fill="x", expand=True)
            ttk.Label(text, text=seal_name(award, level), style="Status.TLabel").pack(anchor="w")
            theme.hint(text, text=diploma_condition(award, level), wrap=380).pack(anchor="w")
            theme.hint(text, text=day.strftime(tr("%d.%m.%Y"))).pack(anchor="w")
            ttk.Button(row, text=tr("Drucken"),
                       command=lambda a=award, lv=level, d=day: self._print(a, lv, d)).pack(side="right", padx=(8, 0))

        line = ttk.Frame(frame)
        line.pack(fill="x", pady=(4, 0))
        ttk.Label(line, text=tr("Rufzeichen auf dem Diplom:")).pack(side="left")
        self.call_var = tk.StringVar(value=call)
        ttk.Entry(line, textvariable=self.call_var, width=12).pack(side="left", padx=(6, 0))
        self.note_var = tk.StringVar(value="")
        theme.hint(frame, textvariable=self.note_var, wrap=480).pack(anchor="w", pady=(6, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(10, 0))
        done = ttk.Button(buttons, text=tr("Schließen"), style="Accent.TButton", command=self.close)
        done.pack(side="right")
        window.bind("<Escape>", lambda e: self.close())
        window.protocol("WM_DELETE_WINDOW", self.close)
        done.focus_set()

    def call(self) -> str:
        return self.call_var.get().strip().upper()

    def _print(self, award, level, day):
        awards.save_call(self.call())
        self.note_var.set(print_diploma(award, level, day, self.call()))

    def close(self) -> None:
        if self.window is None:
            return
        awards.save_call(self.call())
        self.window.destroy()
        self.window = None
        if self.on_close:
            self.on_close()


class AwardsPanel:
    def __init__(self, parent, on_show=None):
        box = theme.card(parent, tr("Diplome"))
        self.summary_var = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.summary_var, style="Score.TLabel").pack(anchor="w", pady=(0, 6))

        columns = ("name", "seals", "next", "lesson")
        self.tree = ttk.Treeview(box, columns=columns, show="headings", height=len(awards.AWARDS),
                                 selectmode="browse")
        headings = {"name": tr("Diplom"), "seals": tr("Siegel"), "next": tr("Nächstes Ziel"),
                    "lesson": tr("ab Lektion")}
        widths = {"name": 170, "seals": 140, "next": 190, "lesson": 75}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center" if col == "lesson" else "w")
        self.tree.tag_configure("open", foreground=theme.MUTED)
        self.tree.pack(fill="x", pady=(2, 0))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_detail())

        self.detail_var = tk.StringVar(value="")
        theme.hint(box, textvariable=self.detail_var, wrap=WRAP).pack(anchor="w", pady=(6, 0))
        self.on_show = on_show
        self.show_button = ttk.Button(box, text=tr("Diplom ansehen und drucken"), command=self._show_diploma,
                                      state="disabled")
        self.show_button.pack(anchor="w", pady=(6, 0))
        self.rows = {}

    def refresh(self, rows=None):
        """`rows`: [(Diplom, Status)] wie awards.overview(); ohne Angabe neu ausgewertet."""
        rows = awards.overview() if rows is None else rows
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        seals = with_seal = 0
        for award, status in rows:
            reached = sum(day is not None for day in status.dates)
            seals += reached
            with_seal += bool(reached)
            lesson = award.from_lesson if award.from_lesson else "–"
            self.tree.insert("", "end", iid=award.key, tags=() if reached else ("open",),
                             values=(tr(award.name), seals_text(award, status), next_text(award, status), lesson))
            self.rows[award.key] = (award, status)
        if seals:
            self.summary_var.set(tr("{seals} Siegel in {awards} von {total} Diplomen").format(
                seals=seals, awards=with_seal, total=len(rows)))
        else:
            self.summary_var.set(tr("Noch keine Siegel"))
        if selected and selected[0] in self.rows:
            self.tree.selection_set(selected[0])
        self._show_detail()

    def _selected_seal(self):
        """(Schlüssel, höchste Stufe, Tag) der gewählten Zeile oder None."""
        selected = self.tree.selection()
        if not selected or selected[0] not in self.rows:
            return None
        _, status = self.rows[selected[0]]
        reached = [(level, day) for level, day in enumerate(status.dates) if day is not None]
        return (selected[0], *reached[-1]) if reached else None

    def _show_diploma(self):
        seal = self._selected_seal()
        if seal and self.on_show:
            self.on_show(seal)

    def _show_detail(self):
        selected = self.tree.selection()
        self.show_button.config(state="normal" if self._selected_seal() else "disabled")
        if selected and selected[0] in self.rows:
            self.detail_var.set(detail_text(*self.rows[selected[0]]))
        else:
            self.detail_var.set(tr("Eine Zeile wählen, um die Bedingung zu sehen. Erreichte Siegel bleiben, "
                                   "auch wenn die Gesamtstatistik zurückgesetzt wird."))
