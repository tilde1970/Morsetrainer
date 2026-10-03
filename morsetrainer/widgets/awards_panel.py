"""Diplom-Übersicht im Statistik-Reiter: alle Diplome mit erreichten
Siegeln, dem nächsten Ziel und ab welcher Lektion es erreichbar ist.
Offene Diplome stehen grau; die gewählte Zeile zeigt darunter Bedingung,
Stufen und die Tage der Siegel."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import awards
from morsetrainer.i18n import number, tr
from morsetrainer.widgets import theme

WRAP = 520


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


class AwardsPanel:
    def __init__(self, parent):
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

    def _show_detail(self):
        selected = self.tree.selection()
        if selected and selected[0] in self.rows:
            self.detail_var.set(detail_text(*self.rows[selected[0]]))
        else:
            self.detail_var.set(tr("Eine Zeile wählen, um die Bedingung zu sehen. Erreichte Siegel bleiben, "
                                   "auch wenn die Gesamtstatistik zurückgesetzt wird."))
