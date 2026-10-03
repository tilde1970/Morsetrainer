"""Leiste der Tagesübung über den Reitern.

Ohne laufende Tagesübung: Knopf „▶ Tagesübung“, der Wochenstreifen mit
den Sternen je Tag und dem Stand zum Wochenziel (core/week.py), daneben ein
Hinweis (Wochenrückblick oder wie die letzte Tagesübung ausging).
Während der Tagesübung: die drei Abschnitte, Zeitbalken mit
„6:10 von 10 Min“ und die schon verdienten Sterne – ruhig, ohne
Aufleuchten, damit nichts den Blick vom Hören wegzieht."""
import time
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import daily, stats, week
from morsetrainer.i18n import N_, number, tr
from morsetrainer.widgets import theme

FULL_STAR, EMPTY_STAR = "★", "☆"
BLOCK_LABELS = {daily.WARMUP: N_("Aufwärmen"), daily.MAIN: N_("Hauptteil"), daily.OUTRO: N_("Ausklang"),
                daily.EXTRA: N_("Zugabe")}
STAR_NAMES = {daily.DABEI: N_("Dabei"), daily.SAUBER: N_("Sauber"), daily.WEITER: N_("Weiter")}
WEEKDAYS = (N_("Mo"), N_("Di"), N_("Mi"), N_("Do"), N_("Fr"), N_("Sa"), N_("So"))
# Eine Serie wird erst ab dieser Länge erwähnt.
STREAK_SHOWN_FROM = 5


def star_text(stars) -> str:
    return " ".join(FULL_STAR if s in stars else EMPTY_STAR for s in daily.STAR_ORDER)


def week_text(days: list) -> str:
    """Wochenstreifen: „Mo ★★★  Di ★★  Mi ✓  Do –  Fr ·“ (✓ frei geübt,
    – nicht geübt, · noch nicht dran)."""
    parts = []
    for item in days:
        if item["stars"]:
            mark = FULL_STAR * item["stars"]
        else:
            mark = {week.FUTURE: "·", week.PRACTICED: "✓"}.get(item["status"], "–")
        parts.append(f"{tr(WEEKDAYS[item['day'].weekday()])} {mark}")
    return "  ".join(parts)


def week_goal_text(stars: int) -> str:
    if stars >= week.WEEK_GOAL:
        return tr("Wochenziel erreicht: {stars} {star}").format(stars=stars, star=FULL_STAR)
    return tr("{stars} von {goal} {star} diese Woche").format(stars=stars, goal=week.WEEK_GOAL, star=FULL_STAR)


def review_line(review: dict) -> str:
    """Wochenrückblick in einem Satz."""
    days = tr("1 Tag") if review["days"] == 1 else tr("{n} Tage").format(n=review["days"])
    text = tr("Letzte Woche: {days}, {stars} {star}").format(days=days, stars=review["stars"], star=FULL_STAR)
    a, b = review["lesson_from"], review["lesson_to"]
    if a is not None and b > a and a < daily.POST_KOCH:
        if b >= daily.POST_KOCH:
            text += ", " + tr("Lektion {a} → Koch geschafft").format(a=a)
        else:
            text += ", " + tr("Lektion {a} → {b}").format(a=a, b=b)
    return text


def minutes_text(minutes: float) -> str:
    seconds = max(int(minutes * 60), 0)
    return f"{seconds // 60}:{seconds % 60:02d}"


def stars_named(stars) -> str:
    return ", ".join(f"{FULL_STAR} {tr(STAR_NAMES[s])}" for s in daily.STAR_ORDER if s in stars)


def tempo_text(tempo: dict) -> str:
    if tempo["effective"] < tempo["wpm"]:
        return f"{tempo['wpm']}/{tempo['effective']} WPM"
    return f"{tempo['wpm']} WPM"


def _share(correct: int, total: int) -> str:
    return number(round(correct / total * 100)) if total else "0"


def block_lines(summary: dict) -> list:
    """Ergebnis eines Blocks in ein bis zwei Sätzen."""
    lines = []
    correct, total = summary["correct"], summary["total"]
    if summary.get("due_practiced"):
        lines.append(tr("{n} fällige Zeichen geübt, {sure} davon heute sicher").format(
            n=summary["due_practiced"], sure=summary["due_sure"]))
    elif summary["kind"] == daily.MAIN:
        lines.append(tr("{mode}: {correct} von {total} Zeichen beim ersten Versuch ({share} %)").format(
            mode=tr(stats.HISTORY_MODES[summary["mode"]]), correct=correct, total=total,
            share=_share(correct, total)))
    elif total:
        lines.append(tr("{correct} von {total} Zeichen richtig ({share} %)").format(
            correct=correct, total=total, share=_share(correct, total)))
    streak = summary.get("streak", 0)
    if streak >= STREAK_SHOWN_FROM:
        text = (tr("Beste Serie: {n} Zeichen in Folge beim ersten Hören") if summary["mode"] == "single"
                else tr("Beste Serie: {n} in Folge fehlerfrei"))
        lines.append(text.format(n=streak))
    return lines


def moment_line(moment: dict) -> str:
    return tr("{char} sitzt jetzt: {now} s (letzte Woche {before} s)").format(
        char=moment["char"], now=number(moment["now"], 2), before=number(moment["before"], 2))


def preview_line(block, lesson: int, tempo: dict) -> str:
    what = (tr("alle Zeichen") if lesson >= daily.POST_KOCH
            else tr("Lektion {lesson}").format(lesson=lesson))
    return tr("Jetzt: {mode}, {what}, {tempo}").format(
        mode=tr(stats.HISTORY_MODES[block.mode]), what=what, tempo=tempo_text(tempo))


def better_line(item: dict) -> str:
    if item["kind"] == "groups":
        return tr("Gruppen bei {wpm} WPM: {before} % → {now} % beim ersten Versuch").format(
            wpm=item["wpm"], before=number(round(item["before"] * 100)), now=number(round(item["now"] * 100)))
    return tr("{char} kommt schneller: {before} s → {now} s").format(
        char=item["char"], before=number(item["before"], 2), now=number(item["now"], 2))


def outlook_line(outlook) -> str:
    if not outlook:
        return ""
    done = outlook["lesson"] >= daily.POST_KOCH  # nach der Abschlusslektion: Koch geschafft
    if outlook.get("pending"):
        if done:
            return tr("Koch geschafft – ab morgen übst du mit allen Zeichen weiter!")
        return tr("Ab morgen Lektion {lesson} – geschafft!").format(lesson=outlook["lesson"])
    if done:
        return tr("Noch {missing} % beim ersten Versuch bis zum Koch-Abschluss").format(missing=outlook["missing"])
    return tr("Noch {missing} % beim ersten Versuch bis Lektion {lesson}").format(
        missing=outlook["missing"], lesson=outlook["lesson"])


def extra_label(offer) -> str:
    kind, chars = offer
    if kind == daily.CONFUSIONS:
        what = tr("Verwechslungen {chars}").format(chars=" ".join(chars))
    elif kind == daily.RUFZ:
        what = tr(stats.HISTORY_MODES["rufz"])
    else:
        what = tr(stats.HISTORY_MODES["word"])
    return tr("Noch {minutes} Min: {what}").format(minutes=daily.EXTRA_MINUTES, what=what)


class DailyBar:
    def __init__(self, parent, on_start, on_continue):
        self.frame = ttk.Frame(parent, padding=(10, 6, 10, 2))
        self.frame.columnconfigure(1, weight=1)
        self.idle = ttk.Frame(self.frame)
        self.start_button = ttk.Button(
            self.idle, text=tr("▶ Tagesübung ({minutes} Min)").format(minutes=daily.TOTAL_MINUTES),
            style="Accent.TButton", command=on_start)
        self.start_button.pack(side="left")
        self.week_var = tk.StringVar(value="")
        ttk.Label(self.idle, textvariable=self.week_var).pack(side="left", padx=(12, 0))
        self.goal_var = tk.StringVar(value="")
        ttk.Label(self.idle, textvariable=self.goal_var, style="Score.TLabel").pack(side="left", padx=(12, 0))
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

        self.card = ttk.LabelFrame(self.frame, padding=(10, 4, 10, 8))
        self.card_lines = ttk.Frame(self.card)
        self.card_lines.pack(fill="x")
        footer = ttk.Frame(self.card)
        footer.pack(fill="x", pady=(6, 0))
        ttk.Button(footer, text=tr("Weiter ▶"), style="Accent.TButton", command=on_continue).pack(side="left")
        theme.hint(footer, text=tr("Enter geht weiter, Esc beendet die Tagesübung")).pack(side="left", padx=(10, 0))
        self.show_idle()

    def pack(self, **options):
        self.frame.pack(fill="x", **options)

    def show_idle(self, note: str = "") -> None:
        self.hide_card()
        self.active.pack_forget()
        self.idle.pack(fill="x")
        self.note_var.set(note)

    def show_week(self, days: list, stars: int) -> None:
        self.week_var.set(week_text(days))
        self.goal_var.set(week_goal_text(stars))

    def show_active(self) -> None:
        self.idle.pack_forget()
        self.active.pack(fill="x")

    def show_card(self, title: str, lines, strong=()) -> None:
        """Zwischenkarte unter der Leiste; `strong`: Zeilen, die betont
        werden (neue Sterne)."""
        for child in self.card_lines.winfo_children():
            child.destroy()
        self.card.config(text=title)
        for line in lines:
            style = "Score.TLabel" if line in strong else "TLabel"
            ttk.Label(self.card_lines, text=line, style=style, wraplength=640, justify="left").pack(anchor="w")
        self.card.pack(fill="x", pady=(6, 0))

    def hide_card(self) -> None:
        self.card.pack_forget()

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


# Enter direkt nach dem Erscheinen von Zwischenkarte oder Abendbilanz
# gehört noch zur letzten Antwort und soll sie nicht gleich wegklicken.
ENTER_GRACE_S = 0.8


class EveningSummary:
    """Abendbilanz: Sterne, was besser geworden ist, was fast geschafft ist,
    heute erreichte Siegel und auf Wunsch einmal „Noch 5 Min“. Enter und
    Esc schließen; danach `on_close` (zeigt die neuen Siegel)."""

    def __init__(self, root, stars, comparison: dict, outlook=None, offer=None, on_extra=None,
                 completed: bool = True, week_stars: int = None, seals=(), on_close=None):
        self.on_extra = on_extra
        self.on_close = on_close
        self.offer = offer
        self.window = window = tk.Toplevel(root)
        window.title(tr("Tagesübung"))
        window.configure(background=theme.BG)
        window.transient(root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        title = tr("Tagesübung geschafft.") if completed else tr("Tagesübung abgebrochen – deine Sterne bleiben.")
        ttk.Label(frame, text=title, style="Status.TLabel").pack(anchor="w")
        ttk.Label(frame, text=star_text(stars), style="Score.TLabel").pack(anchor="w", pady=(8, 0))
        if stars:
            ttk.Label(frame, text=stars_named(stars)).pack(anchor="w")
        if week_stars is not None:
            ttk.Label(frame, text=week_goal_text(week_stars)).pack(anchor="w", pady=(4, 0))

        box = theme.card(frame, tr("Besser geworden (gegenüber der Vorwoche)"), padx=0, pady=(12, 0))
        lines = [better_line(item) for item in comparison.get("better", [])]
        if not lines:
            lines = [tr("Stand gehalten.") if comparison.get("status") == daily.HELD
                     else tr("Für einen Vergleich mit der Vorwoche fehlen noch Daten.")]
        for line in lines:
            ttk.Label(box, text=line).pack(anchor="w")
        if outlook:
            box = theme.card(frame, tr("Fast geschafft"), padx=0, pady=(8, 0))
            ttk.Label(box, text=outlook_line(outlook)).pack(anchor="w")
        if seals:
            box = theme.card(frame, tr("Neues Siegel") if len(seals) == 1 else tr("Neue Siegel"), padx=0, pady=(8, 0))
            for line in seals:
                ttk.Label(box, text=line).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))
        self.done_button = ttk.Button(buttons, text=tr("Fertig"), style="Accent.TButton", command=self.close)
        self.done_button.pack(side="right")
        self.extra_button = None
        if offer and on_extra:
            self.extra_button = ttk.Button(buttons, text=extra_label(offer), command=self._extra)
            self.extra_button.pack(side="right", padx=(0, 8))
        # Enter gleich nach dem Erscheinen gehört noch zur letzten Antwort.
        self.opened = time.time()
        window.bind("<Return>", lambda e: self.close() if time.time() - self.opened >= ENTER_GRACE_S else None)
        window.bind("<Escape>", lambda e: self.close())
        window.protocol("WM_DELETE_WINDOW", self.close)
        self.done_button.focus_set()

    def _extra(self) -> None:
        self.close(follow=False)  # neue Siegel erst nach der Zugabe zeigen
        self.on_extra(self.offer)

    def close(self, follow: bool = True) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None
            if follow and self.on_close:
                self.on_close()
