"""Abschnitt „Auswertungen“ im Statistik-Reiter: Rückstand beim Mitschreiben,
Fehlerarten je Woche, Ermüdung im Durchgang und Verwechslungspaare im Verlauf
(Zahlen aus core/insights). Jede Auswertung sagt in Worten, was sie zeigt, und
schweigt, solange die Daten nicht reichen."""
from tkinter import ttk
import tkinter as tk

from morsetrainer import i18n
from morsetrainer.core import insights, stats
from morsetrainer.core.morse import display_text
from morsetrainer.i18n import N_, number, tr
from morsetrainer.widgets import theme

# Unterschied, ab dem eine Verwechslungsrate als seltener oder häufiger gilt (Prozentpunkte).
PAIR_CHANGE_PCT = 3

CAUSE_NAMES = {stats.HEARD: N_("verwechselt"), insights.UNRECOGNISED: N_("nicht erkannt")}


def _pct(share: float) -> int:
    """Prozent ohne auf 100 zu runden, solange es Fehler gab (wie die Vergleichszeile)."""
    return 100 if share >= 100 else min(int(share + 0.5), 99)


def lag_text(lag: dict) -> str:
    """„Rückstand am Stück (Median): zuletzt 1,4 Zeichen, davor 1,8 Zeichen.“ oder ""."""
    parts = []
    for key, label in (("recent", tr("letzte {days} Tage").format(days=insights.RECENT_DAYS)),
                       ("before", tr("davor"))):
        values = lag[key]
        if len(values) >= insights.MIN_LAG_CHARS:
            parts.append(tr("{label}: {n} Zeichen").format(label=label, n=number(insights.median(values), 1)))
    if not parts:
        return ""
    return tr("Rückstand am Stück (Median): {parts}.").format(parts=", ".join(parts))


def _week_label(day) -> str:
    return f"{day.month}/{day.day}" if i18n.LANG == "en" else f"{day.day}.{day.month}."


def causes_text(weeks: list) -> str:
    """Eine Zeile je Woche: „ab 12.10.: 18 Fehler: verwechselt 50 %, verpasst 33 %, …“."""
    lines = []
    for week in weeks:
        counts = week["counts"]
        total = sum(counts.values())
        head = tr("Woche ab {day}").format(day=_week_label(week["first"]))
        if total < insights.MIN_WEEK_ERRORS:
            lines.append(f"{head}: " + tr("{n} Fehler (zu wenige für eine Aufteilung)").format(n=total))
            continue
        shares = ", ".join(f"{tr(CAUSE_NAMES.get(cause, cause))} {_pct(count / total * 100)} %"
                           for cause, count in sorted(counts.items(), key=lambda item: -item[1]))
        lines.append(f"{head}: " + tr("{n} Fehler: {shares}").format(n=total, shares=shares))
    return "\n".join(lines)


def fatigue_text(data: dict) -> str:
    """Erstes, mittleres und letztes Drittel samt Urteil; "" bei zu wenigen Durchgängen."""
    if data["sessions"] < insights.FATIGUE_MIN_SESSIONS:
        return ""
    names = (tr("Erstes Drittel"), tr("Mittleres Drittel"), tr("Letztes Drittel"))
    shares, lines = [], []
    for name, part in zip(names, data["thirds"]):
        total = part["good"] + part["wrong"]
        if not total:
            return ""
        share = part["good"] / total * 100
        shares.append(share)
        latency = insights.median(part["latencies"])
        reaction = "" if latency is None else ", " + tr("Reaktion {s} s").format(s=number(latency, 2))
        lines.append(f"{name}: " + tr("{pct} % richtig").format(pct=_pct(share)) + reaction)
    if shares[0] - shares[2] >= insights.FATIGUE_GAP_PCT:
        verdict = tr("Zum Ende lässt es nach: kürzere Durchgänge oder eine Pause in der Mitte könnten sich lohnen.")
    else:
        verdict = tr("Kaum Nachlassen zum Ende des Durchgangs.")
    return "\n".join(lines + [verdict])


def pairs_text(rows: list) -> str:
    """Eine Zeile je Paar: „D → U: davor 18 %, zuletzt 9 % (seltener)“."""
    lines = []
    for row in rows:
        name = f"{display_text(row['sent'])} → {display_text(row['typed'])}"
        before, recent = row["before"], row["recent"]
        if row["new"]:
            lines.append(f"{name}: " + (tr("neu dabei, zuletzt {recent} %").format(recent=number(recent, 0))
                                        if recent is not None else tr("neu dabei, {n}-mal verwechselt").format(n=row["count"])))
            continue
        if before is None or recent is None:
            lines.append(f"{name}: " + tr("{n}-mal verwechselt, für den Vergleich zu wenig Daten").format(n=row["count"]))
            continue
        change = recent - before
        word = (tr("seltener") if change <= -PAIR_CHANGE_PCT
                else tr("häufiger") if change >= PAIR_CHANGE_PCT else tr("unverändert"))
        lines.append(f"{name}: " + tr("davor {before} %, zuletzt {recent} % ({word})").format(
            before=number(before, 0), recent=number(recent, 0), word=word))
    return "\n".join(lines)


class InsightsPanel:
    """Karte mit den vier Auswertungen; `refresh()` liest die Daten neu."""
    def __init__(self, parent):
        box = theme.card(parent, tr("Auswertungen (letzte {days} Tage)").format(days=insights.INSIGHT_DAYS))
        self.vars = {}
        sections = (
            ("lag", tr("Rückstand beim Mitschreiben"), tr(
                "So viele Zeichen hängst du im Reiter Am Stück hinter dem Ton her. Mehr Rückstand heißt, dass du "
                "mit Abstand mitschreibst wie beim Kopf-Hören; entscheidend ist, dass die Trefferquote dabei hält. "
                "Gezählt werden nur Durchgänge, die den Rückstand schon aufgezeichnet haben."), tr("Noch keine Messung: übe im Reiter Am Stück.")),
            ("causes", tr("Fehlerarten je Woche"), tr(
                "Verwechselt: ein anderes Zeichen getippt oder zwei vertauscht. Nicht erkannt: nichts getippt, zu spät "
                "oder erst nach Wiederholung. Wenn aus Aussetzern Verwechslungen werden, hörst du die Zeichen schon, "
                "trennst sie aber noch nicht sicher."),
             tr("Noch keine Fehler in den letzten Wochen.")),
            ("fatigue", tr("Ermüdung im Durchgang"), tr(
                "Alle Durchgänge ab {n} Zeichen, jeder in drei Teile geteilt, zusammengezählt. Tempo und Zeichensatz "
                "passen sich beim Üben an, der Vergleich ist ein Anhaltspunkt.").format(n=insights.FATIGUE_MIN_CHARS),
             tr("Noch zu wenige lange Durchgänge (ab {n}).").format(n=insights.FATIGUE_MIN_SESSIONS)),
            ("pairs", tr("Verwechslungspaare im Verlauf"), tr(
                "Gesendet → getippt, in Prozent der Fälle, in denen das gesendete Zeichen kam: die letzten {days} Tage "
                "gegen die Zeit davor. Seltener ist besser. Zeichen, die davor nicht vorkamen, sind „neu dabei“.").format(days=insights.RECENT_DAYS),
             tr("Noch keine Verwechslungen zum Vergleichen.")),
        )
        for key, heading, explanation, empty in sections:
            ttk.Label(box, text=heading, font=theme.HEADING).pack(anchor="w", pady=(6, 0))
            var = tk.StringVar(value="")
            self.vars[key] = (var, empty)
            theme.fit_wrap(ttk.Label(box, textvariable=var, justify="left"), 560).pack(anchor="w", pady=(2, 0))
            theme.hint(box, wrap=560, text=explanation).pack(anchor="w", pady=(2, 0))
        self.card = box

    def refresh(self):
        texts = {
            "lag": lag_text(insights.lag_chars()),
            "causes": causes_text(insights.causes_by_week()),
            "fatigue": fatigue_text(insights.fatigue()),
            "pairs": pairs_text(insights.confusion_trend()),
        }
        for key, (var, empty) in self.vars.items():
            var.set(texts[key] or empty)
