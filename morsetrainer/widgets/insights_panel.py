"""Abschnitt „Auswertungen“ im Statistik-Reiter: Rückstand beim Mitschreiben,
Fehlerarten je Woche, Ermüdung im Durchgang, Verwechslungspaare im Verlauf und
wieder wackelige Zeichen (Zahlen aus core/insights). Jede Auswertung sagt in
Worten, was sie zeigt, und schweigt, solange die Daten nicht reichen. Alles
steht auch in `spoken()` für die Vorlese-Taste F11 und den Knopf oben, weil
Screenreader die Tk-Texte nicht lesen."""
import sys
import tkinter as tk
from tkinter import ttk

from morsetrainer import i18n
from morsetrainer.core import errorlog, insights, stats
from morsetrainer.core.morse import display_text
from morsetrainer.i18n import N_, number, tr
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.help_window import HelpWindow

CAUSE_NAMES = {stats.HEARD: N_("verwechselt"), insights.SWAPPED: N_("vertauscht"),
               insights.UNRECOGNISED: N_("nicht erkannt")}
VERDICT_WORDS = {insights.LESS: N_("seltener"), insights.MORE: N_("häufiger"), insights.SAME: N_("unverändert"),
                 insights.UNSURE: N_("kein sicherer Unterschied")}


def _pct(share: float) -> int:
    """Prozent ohne auf 100 zu runden, solange es Fehler gab (wie die Vergleichszeile)."""
    return 100 if share >= 100 else min(int(share + 0.5), 99)


def _chars(chars) -> str:
    return " ".join(display_text(ch) for ch in chars)


def lag_text(lag: dict) -> str:
    """„Rückstand am Stück (Median): letzte 14 Tage: 1,4 Zeichen, davor: 1,8 Zeichen.“ oder ""."""
    parts = []
    for key, label in (("recent", tr("letzte {days} Tage").format(days=insights.RECENT_DAYS)),
                       ("before", tr("davor"))):
        values = lag[key]
        if len(values) >= insights.MIN_LAG_CHARS:
            text = tr("{label}: {n} Zeichen").format(label=label, n=number(insights.median(values), 1))
            accuracy = lag.get("accuracy", {}).get(key)
            if accuracy is not None:
                text += ", " + tr("{pct} % richtig").format(pct=_pct(accuracy))
            parts.append(text)
    if not parts:
        return ""
    return tr("Rückstand am Stück (Median): {parts}.").format(parts=", ".join(parts))


def _week_label(day) -> str:
    return f"{day.month}/{day.day}" if i18n.LANG == "en" else f"{day.day}.{day.month}."


def _week_line(week: dict) -> str:
    counts = week["counts"]
    total = sum(counts.values())
    head = tr("Woche ab {day}").format(day=_week_label(week["first"]))
    if week["current"]:
        head += " " + tr("(läuft noch)")
    if total < insights.MIN_WEEK_ERRORS:
        return f"{head}: " + tr("{n} Fehler (zu wenige für eine Aufteilung)").format(n=total)
    shares = ", ".join(f"{tr(CAUSE_NAMES.get(cause, cause))} {_pct(count / total * 100)} %"
                       for cause, count in sorted(counts.items(), key=lambda item: -item[1]))
    rate = total / week["chars"] * 100 if week["chars"] else 0
    line = f"{head}: " + tr("{rate} Fehler je 100 Zeichen, davon {shares} ({n} Fehler)").format(
        rate=number(rate, 1), shares=shares, n=total)
    top = [ch for ch, n in week["unrecognised"].most_common(insights.WEEK_CHARS_SHOWN)
           if n >= insights.MIN_WEEK_CHAR_ERRORS]
    if top:
        line += "; " + tr("nicht erkannt vor allem: {chars}").format(chars=", ".join(display_text(ch) for ch in top))
    return line


def causes_text(weeks: list) -> str:
    """Eine Zeile je Woche: „Woche ab 12.10.: 7,5 Fehler je 100 Zeichen, davon nicht erkannt
    86 %, verwechselt 14 % (273 Fehler); nicht erkannt vor allem: 6, X“."""
    return "\n".join(_week_line(week) for week in weeks)


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


def _pair_line(row: dict, spoken: bool = False) -> str:
    spell = announcer.spell if spoken else display_text
    sent, typed = spell(row["sent"]), spell(row["typed"])
    name = tr("{sent} als {typed} getippt").format(sent=sent, typed=typed) if spoken else f"{sent} → {typed}"
    before, recent = row["before"], row["recent"]
    if row["new"]:
        return f"{name}: " + (tr("neu dabei, zuletzt {recent} %").format(recent=number(recent, 0))
                              if recent is not None else tr("neu dabei, {n}-mal verwechselt").format(n=row["count"]))
    if before is None or recent is None:
        return f"{name}: " + tr("{n}-mal verwechselt, für den Vergleich zu wenig Daten").format(n=row["count"])
    word = tr(VERDICT_WORDS[insights.pair_verdict(row)])
    return f"{name}: " + tr("davor {before} % (von {n_before}), zuletzt {recent} % (von {n_recent}): {word}").format(
        before=number(before, 0), recent=number(recent, 0), word=word,
        n_before=row["n_before"], n_recent=row["n_recent"])


def pairs_text(rows: list, spoken: bool = False) -> str:
    """Eine Zeile je Richtung, die beiden Richtungen eines Paares untereinander:
    „D → U: davor 18 % (von 40), zuletzt 9 % (von 52): seltener“."""
    return "\n".join(_pair_line(row, spoken) for row in rows)


def pair_chars(rows: list) -> str:
    """Die Zeichen der angezeigten Paare, jedes einmal."""
    chars = []
    for row in rows:
        for ch in (row["sent"], row["typed"]):
            if ch not in chars:
                chars.append(ch)
    return "".join(chars)


def wobbly_text(rows: list) -> str:
    """„6 (Fach 5 → 1), X (Fach 4 → 2)“ oder ""."""
    return ", ".join(tr("{char} (Fach {best} → {box})").format(char=display_text(ch), best=best, box=box)
                     for ch, best, box in rows)


class InsightsPanel:
    """Karte mit den Auswertungen; `refresh()` liest die Daten neu."""
    def __init__(self, parent, on_drill=None):
        """`on_drill(chars, meldung)`: Übung mit diesen Zeichen starten (die Meldung
        sagt, was fehlt, wenn es zu wenige sind)."""
        self.on_drill = on_drill
        self.locked = False
        box = theme.card(parent, tr("Auswertungen (letzte {days} Tage)").format(days=insights.INSIGHT_DAYS))
        # Oben ein Bedienelement: Der Sprung aus der Sprungzeile landet hier, im Blick, und die
        # Sprachausgabe bekommt die Texte, die Screenreader in Tk-Beschriftungen nicht lesen.
        ttk.Button(box, text=tr("Auswertungen vorlesen"), command=self.speak).pack(anchor="w")
        theme.hint(box, wrap=560, text=tr(
            "Die Auswertungen füllen sich mit dem Üben; was noch fehlt, steht jeweils dabei.")).pack(
            anchor="w", pady=(2, 0))
        self.vars = {}
        self.buttons = {}
        self.drill = {"pairs": "", "weak": ""}
        sections = (
            ("lag", tr("Rückstand beim Mitschreiben"), tr(
                "So viele Zeichen hängst du im Reiter Am Stück hinter dem Ton her. Mehr Rückstand heißt, dass du "
                "mit Abstand mitschreibst wie beim Kopf-Hören; entscheidend ist, dass die Trefferquote dabei hält. "
                "Gezählt werden nur Durchgänge, die den Rückstand aufgezeichnet haben, auch zu späte Tasten."),
             tr("Noch keine Messung: übe im Reiter Am Stück.")),
            ("causes", tr("Fehlerarten je Woche"), tr(
                "Verwechselt: ein anderes Zeichen getippt. Vertauscht: zwei Zeichen in falscher Reihenfolge. Nicht "
                "erkannt: nichts getippt, zu spät oder erst nach Wiederholung. Viel „nicht erkannt“ ist am Anfang "
                "normal; sinkt die Rate je 100 Zeichen, erkennst du mehr. Ein Tempo- oder Lektionswechsel verändert "
                "die Rate. Wenn aus Aussetzern Verwechslungen werden, hörst du die Zeichen schon, trennst sie aber "
                "noch nicht sicher."),
             tr("Noch keine Fehler in den letzten Wochen.")),
            ("fatigue", tr("Ermüdung im Durchgang"), tr(
                "Alle Durchgänge ab {n} Zeichen, jeder in drei Teile geteilt, zusammengezählt. Das erste Drittel fällt "
                "oft besser aus (Aufwärmen, bekannte Zeichen). Die Reaktion stammt nur aus Einzelzeichen. Tempo und "
                "Zeichensatz passen sich beim Üben an, der Vergleich ist ein Anhaltspunkt.").format(
                n=insights.FATIGUE_MIN_CHARS),
             tr("Noch zu wenige lange Durchgänge (ab {n} Durchgängen mit je mindestens {chars} Zeichen).").format(
                 n=insights.FATIGUE_MIN_SESSIONS, chars=insights.FATIGUE_MIN_CHARS)),
            ("pairs", tr("Verwechslungspaare im Verlauf"), tr(
                "Gesendet → getippt, in Prozent der Fälle, in denen das gesendete Zeichen kam: die letzten {days} Tage "
                "gegen die Zeit davor, dazu in Klammern, aus wie vielen Fällen. Seltener ist besser. Ein Unterschied "
                "zählt erst, wenn er sich von Zufall abhebt; sonst steht „kein sicherer Unterschied“. Ein Tempowechsel "
                "dazwischen verfälscht den Vergleich, und ein Zeichen, das gerade neu geübt wird, sieht kurz schlechter "
                "aus. Zeichen, die davor nicht vorkamen, sind „neu dabei“.").format(days=insights.RECENT_DAYS),
             tr("Noch keine Verwechslungen zum Vergleichen.")),
            ("wobbly", tr("Wieder wackelig"), tr(
                "Zeichen, die in der Lernkartei schon in einem hohen Fach lagen und zurückgestuft wurden. Sie sind keine "
                "Anfänger-Fehler, sondern Zeichen, die einmal saßen; ein paar Wiederholungen bringen sie meist zurück."),
             tr("Kein Zeichen ist aus einem hohen Fach zurückgefallen.")),
        )
        for key, heading, explanation, empty in sections:
            ttk.Label(box, text=heading, font=theme.HEADING).pack(anchor="w", pady=(6, 0))
            var = tk.StringVar(value="")
            self.vars[key] = (var, empty)
            theme.fit_wrap(ttk.Label(box, textvariable=var, justify="left"), 560).pack(anchor="w", pady=(2, 0))
            theme.hint(box, wrap=560, text=explanation).pack(anchor="w", pady=(2, 0))
            if key in ("causes", "pairs") and on_drill is not None:
                drill = "weak" if key == "causes" else "pairs"
                button = ttk.Button(box, command=lambda drill=drill: self._start_drill(drill))
                button.pack(anchor="w", pady=(4, 0))
                self.buttons[drill] = button
        self._label_buttons()
        self.card = box

    def _label_buttons(self) -> None:
        labels = {"pairs": tr("Diese Zeichen gezielt üben: {chars}"),
                  "weak": tr("Nicht erkannte Zeichen gezielt üben: {chars}")}
        for drill, button in self.buttons.items():
            chars = self.drill[drill]
            button.config(text=labels[drill].format(chars=_chars(chars)) if chars
                          else labels[drill].replace(": {chars}", ""),
                          state="disabled" if self.locked or len(chars) < 2 else "normal")

    def _start_drill(self, drill: str) -> None:
        message = (tr("Noch zu wenige Verwechslungen zum gezielten Üben.") if drill == "pairs"
                   else tr("Noch zu wenige nicht erkannte Zeichen zum gezielten Üben."))
        self.on_drill(self.drill[drill], message)

    def set_locked(self, locked: bool) -> None:
        """Während eines Durchgangs sind die Übungsknöpfe gesperrt."""
        self.locked = locked
        self._label_buttons()

    def _texts(self) -> dict:
        """Die Texte der Abschnitte; ein Abschnitt, der scheitert, bleibt leer (und steht im
        Fehlerprotokoll), die anderen laufen weiter."""
        version = getattr(HelpWindow, "version", None) or ""
        texts = {}

        def guarded(key, make):
            try:
                texts[key] = make()
            except Exception:
                errorlog.record(*sys.exc_info(), version=version)
                texts[key] = None

        try:
            data = insights.load()
        except Exception:
            errorlog.record(*sys.exc_info(), version=version)
            data = None
        if data is None:
            return {key: None for key in self.vars}
        pairs = []
        weeks = []
        guarded("lag", lambda: lag_text(insights.lag_chars(data)))
        guarded("fatigue", lambda: fatigue_text(insights.fatigue(data)))

        def make_causes():
            weeks.extend(insights.causes_by_week(data))
            return causes_text(weeks)

        def make_pairs():
            pairs.extend(insights.confusion_trend(data))
            return pairs_text(pairs)
        guarded("causes", make_causes)
        guarded("pairs", make_pairs)
        guarded("wobbly", lambda: wobbly_text(insights.wobbly()))
        texts["_pairs"], texts["_weeks"] = pairs, weeks
        try:
            texts["_weak"] = "".join(ch for ch, _n in insights.weak_chars(data))
        except Exception:
            errorlog.record(*sys.exc_info(), version=version)
            texts["_weak"] = ""
        return texts

    def refresh(self):
        texts = self._texts()
        failed = tr("Nicht auswertbar, Einzelheiten im Fehlerprotokoll.")
        for key, (var, empty) in self.vars.items():
            text = texts.get(key)
            var.set(failed if text is None else text or empty)
        self.drill["pairs"] = pair_chars(texts.get("_pairs", []))
        self.drill["weak"] = texts.get("_weak", "")
        self._label_buttons()

    def spoken_parts(self) -> list:
        """Die Auswertungen für die Stimme: Rückstand, die letzte Fehlerwoche, das Urteil zur
        Ermüdung, die Paare und die wackeligen Zeichen; nur, was Daten hat."""
        texts = self._texts()
        parts = []
        if texts.get("lag"):
            parts.append(texts["lag"])
        weeks = texts.get("_weeks") or []
        if weeks:
            parts.append(_week_line(weeks[-1]))
        if texts.get("fatigue"):
            parts.append(texts["fatigue"].split("\n")[-1])
        if texts.get("_pairs"):
            parts.extend(_pair_line(row, spoken=True) for row in texts["_pairs"])
        if texts.get("wobbly"):
            parts.append(tr("Wieder wackelig: ") + ", ".join(
                tr("{char} von Fach {best} auf {box}").format(char=announcer.spell(ch), best=best, box=box)
                for ch, best, box in insights.wobbly()))
        return parts

    def spoken(self) -> str:
        """Alle Auswertungen als Sätze; mit Titel, oder der Hinweis, dass noch nichts da ist."""
        parts = self.spoken_parts()
        return announcer.sentences([tr("Auswertungen")] + (parts or [tr("Noch keine Auswertungen.")]))

    def speak(self) -> None:
        announcer.say(self.spoken())
