"""Auswertungen über mehrere Durchgänge hinweg, aus den Zeichen-Zeilen der
letzten INSIGHT_DAYS Tage: Rückstand beim Mitschreiben, Fehlerarten je Woche,
Ermüdung im Durchgang, Verwechslungspaare im Verlauf, nicht erkannte Zeichen
und wieder wackelige Zeichen der Lernkartei. Nur lesend; die Texte dazu stehen
in widgets/insights_panel.py.

`load()` liest die Durchgänge einmal; jede Auswertung nimmt sie als `data`
(ohne Angabe liest sie selbst). Zeilen mit unerwarteten Werten fallen weg,
statt eine Auswertung zu stören."""
import math
import statistics
from collections import Counter
from datetime import datetime, timedelta

from morsetrainer.core import db
from morsetrainer.core import review
from morsetrainer.core import stats

INSIGHT_DAYS = 90
RECENT_DAYS = 14        # „zuletzt“ gegen „davor“ (Rückstand, Verwechslungspaare)
WEEKS_SHOWN = 6         # Fehlerarten je Woche
MIN_LAG_CHARS = 30      # so viele Messungen je Seite, damit der Rückstand verglichen wird
MIN_WEEK_ERRORS = 5     # Fehler einer Woche, ab denen ihre Aufteilung gezeigt wird
WEEK_CHARS_SHOWN = 3    # so viele nicht erkannte Zeichen nennt eine Wochenzeile
MIN_WEEK_CHAR_ERRORS = 2
FATIGUE_MIN_CHARS = 30  # kürzere Durchgänge gehen nicht in die Drittel ein
FATIGUE_MIN_SESSIONS = 10
FATIGUE_GAP_PCT = 3     # so viel schlechter am Ende gilt als Nachlassen
PAIR_MIN_SENT = 20      # so oft muss das gesendete Zeichen je Seite vorkommen
PAIRS_SHOWN = 3         # verschiedene Paare (beide Richtungen zusammen)
PAIR_CHANGE_PCT = 3     # kleinster Unterschied in Prozentpunkten, der überhaupt zählt
PAIR_NOISE_FACTOR = 1.5  # und mindestens so viele Standardfehler des Unterschieds
WEAK_CHARS_SHOWN = 5
MIN_WEAK_ERRORS = 5     # so oft nicht erkannt, damit ein Zeichen als schwach gilt
WOBBLY_MIN_BOX = 3      # früher mindestens Fach 4 (8 Tage) erreicht
WOBBLY_DROP = 2         # und um so viele Fächer zurückgestuft
UNRECOGNISED = "unrecognised"  # nichts getippt, zu spät oder erst nach Wiederholung
SWAPPED = "swap"        # mit dem Nachbarn vertauscht (Mitschreib-Fehler, keine Klangverwechslung)

# Urteil über den Verlauf eines Paares.
LESS, MORE, SAME, UNSURE = "less", "more", "same", "unsure"


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def load(now=None, days: int = INSIGHT_DAYS) -> list:
    """[(Startzeit, Konfiguration, Zeichen-Zeilen)] der abgeschlossenen Durchgänge
    der letzten `days` Tage seit dem Zurücksetzen, ohne selbst bewertete (wie
    stats._char_events) und ohne Wiederholungsabfragen und unlesbare Zeilen."""
    now = now or datetime.now()
    since = stats._after_reset(now - timedelta(days=days))
    result = []
    for session in db.sessions(since=since.replace(microsecond=0), events=True):
        config = session.config
        if not session.summary or config.get("self_assessed") or config.get("char_stats") is False:
            continue
        try:
            start = datetime.fromisoformat(config["start_time"])
        except (KeyError, TypeError, ValueError):
            continue
        if start.tzinfo is not None:
            start = start.astimezone().replace(tzinfo=None)
        chars = [obj for obj in session.events
                 if isinstance(obj, dict) and obj.get("type") == "char" and isinstance(obj.get("char"), str)
                 and not obj.get("retry")]
        if chars:
            result.append((start, config, chars))
    return result


def lag_chars(data=None, now=None) -> dict:
    """Rückstand beim Mitschreiben am Stück in Zeichen (stats.record_char,
    `lag_chars`): {"recent": [Werte], "before": [Werte]}, letzte RECENT_DAYS Tage
    gegen davor, dazu "accuracy": {"recent", "before"} die Trefferquote derselben
    Durchgänge in Prozent (None ohne Durchgang). Nur Durchgänge, die den
    Rückstand aufgezeichnet haben."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    result = {"recent": [], "before": []}
    right = {"recent": [0, 0], "before": [0, 0]}
    for start, config, chars in load(now) if data is None else data:
        if config.get("mode") != "continuous":
            continue
        name = "recent" if start >= split else "before"
        values = [obj["lag_chars"] for obj in chars if _number(obj.get("lag_chars"))]
        if values:
            result[name].extend(values)
            right[name][0] += sum(1 for obj in chars if obj.get("correct") is True)
            right[name][1] += len(chars)
    result["accuracy"] = {name: good / total * 100 if total else None for name, (good, total) in right.items()}
    return result


def _kind(obj: dict):
    """Art eines Fehlers: stats.HEARD, SWAPPED oder UNRECOGNISED. Die Ursache wird erst
    seit Oktober 2026 gespeichert; davor galt ein getipptes Zeichen als Verwechslung."""
    cause = obj.get("cause")
    if not isinstance(cause, str):
        cause = stats.HEARD if _text(obj.get("typed")) else "missed"
    if cause == stats.HEARD:
        return stats.HEARD
    return SWAPPED if cause == SWAPPED else UNRECOGNISED


def causes_by_week(data=None, now=None) -> list:
    """Fehler der letzten WEEKS_SHOWN Wochen nach Art (stats.HEARD, SWAPPED,
    UNRECOGNISED): [{"first": Montag, "counts": {Art: Anzahl}, "chars": Zeichen
    der Woche, "unrecognised": Counter der nicht erkannten Zeichen, "current":
    die Woche läuft noch}], älteste Woche zuerst, Wochen ohne Fehler ausgelassen.
    Nur grobe Arten, weil die feineren Ursachen (zu langsam, erst nach
    Wiederholung) erst seit Oktober 2026 aufgezeichnet werden; früher stand dort
    nur „verpasst“."""
    now = now or datetime.now()
    monday = now.date() - timedelta(days=now.weekday())
    first = monday - timedelta(weeks=WEEKS_SHOWN - 1)
    weeks = {first + timedelta(weeks=i): {"counts": {}, "chars": 0, "unrecognised": Counter()}
             for i in range(WEEKS_SHOWN)}
    for start, _config, chars in load(now, days=(now.date() - first).days + 1) if data is None else data:
        week = weeks.get(start.date() - timedelta(days=start.weekday()))
        if week is None:
            continue
        for obj in chars:
            if obj.get("untimed"):
                continue
            week["chars"] += 1
            if obj.get("correct") is False:
                kind = _kind(obj)
                week["counts"][kind] = week["counts"].get(kind, 0) + 1
                if kind == UNRECOGNISED:
                    week["unrecognised"][obj["char"]] += 1
    return [{"first": day, "current": day == monday, **week} for day, week in weeks.items() if week["counts"]]


def weak_chars(data=None, now=None) -> list:
    """[(Zeichen, Anzahl)] der am häufigsten nicht erkannten Zeichen der letzten
    INSIGHT_DAYS Tage, ab MIN_WEAK_ERRORS, höchstens WEAK_CHARS_SHOWN."""
    counts = Counter()
    for _start, _config, chars in load(now) if data is None else data:
        for obj in chars:
            if obj.get("correct") is False and not obj.get("untimed") and _kind(obj) == UNRECOGNISED:
                counts[obj["char"]] += 1
    return [(char, n) for char, n in counts.most_common(WEAK_CHARS_SHOWN) if n >= MIN_WEAK_ERRORS]


def fatigue(data=None, now=None) -> dict:
    """Erstes, mittleres und letztes Drittel der Durchgänge ab FATIGUE_MIN_CHARS
    Zeichen zusammen: {"sessions", "thirds": [{"good", "wrong", "latencies"}]}.
    Zeichen ohne Zeitmessung zählen nicht, die Reaktion kommt wie in der
    Vergleichszeile nur aus Einzelzeichen (stats.REACTION_MODE)."""
    thirds = [{"good": 0, "wrong": 0, "latencies": []} for _ in range(3)]
    sessions = 0
    for _start, config, chars in load(now) if data is None else data:
        chars = [obj for obj in chars if not obj.get("untimed")]
        if len(chars) < FATIGUE_MIN_CHARS:
            continue
        sessions += 1
        for index, obj in enumerate(chars):
            part = thirds[index * 3 // len(chars)]
            part["good" if obj.get("correct") is True else "wrong"] += 1
            latency = stats._measured(obj) if config.get("mode") == stats.REACTION_MODE else None
            if latency is not None:
                part["latencies"].append(latency)
    return {"sessions": sessions, "thirds": thirds}


def pair_verdict(row: dict) -> str:
    """LESS, MORE, SAME oder UNSURE für einen Paar-Eintrag von confusion_trend():
    ein Unterschied zählt erst ab PAIR_CHANGE_PCT Prozentpunkten und mindestens
    PAIR_NOISE_FACTOR Standardfehlern des Unterschieds (aus den Fallzahlen);
    dazwischen ist er nicht sicher von Zufall zu trennen (UNSURE)."""
    before, recent = row["before"], row["recent"]
    n_before, n_recent = row["n_before"], row["n_recent"]
    change = recent - before
    if abs(change) < PAIR_CHANGE_PCT:
        return SAME
    pooled = (before * n_before + recent * n_recent) / (n_before + n_recent) / 100
    noise = math.sqrt(pooled * (1 - pooled) * (1 / n_before + 1 / n_recent)) * 100
    if abs(change) < PAIR_NOISE_FACTOR * noise:
        return UNSURE
    return LESS if change < 0 else MORE


def confusion_trend(data=None, now=None) -> list:
    """Die häufigsten Verwechslungspaare (klangähnlich, beide Richtungen
    zusammen gerechnet) der letzten INSIGHT_DAYS Tage, je Richtung mit ihrer Rate
    zuletzt gegen davor, in Prozent der Vorkommen des gesendeten Zeichens:
    [{"sent", "typed", "count", "before", "recent", "n_before", "n_recent",
    "new"}], die Richtungen eines Paares hintereinander, die häufigere zuerst.
    Rate None bei weniger als PAIR_MIN_SENT Vorkommen; "new": eines der beiden
    Zeichen kam davor nie vor (gerade erst gelernt). Richtungen ohne Fehler fehlen."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    sent = {"recent": Counter(), "before": Counter()}
    wrong = {"recent": Counter(), "before": Counter()}
    for start, _config, chars in load(now) if data is None else data:
        side = "recent" if start >= split else "before"
        for obj in chars:
            if obj.get("untimed"):
                continue
            char = obj["char"]
            sent[side][char] += 1
            typed = _text(obj.get("typed"))
            if obj.get("correct") is False and typed and _kind(obj) == stats.HEARD:
                wrong[side][(char, typed)] += 1
    totals = Counter()
    for side in wrong:
        for pair, count in wrong[side].items():
            if stats.sounds_similar(*pair):
                totals[pair] += count
    by_pair = Counter()
    for (char, typed), count in totals.items():
        by_pair[frozenset((char, typed))] += count
    rows = []
    for key, _ in by_pair.most_common(PAIRS_SHOWN):
        for char, typed in sorted(((c, t) for c, t in totals if frozenset((c, t)) == key), key=lambda p: -totals[p]):
            row = {"sent": char, "typed": typed, "count": totals[(char, typed)],
                   "n_before": sent["before"][char], "n_recent": sent["recent"][char],
                   "new": not sent["before"][char] or not sent["before"][typed]}
            for side in ("before", "recent"):
                seen = sent[side][char]
                row[side] = wrong[side][(char, typed)] / seen * 100 if seen >= PAIR_MIN_SENT else None
            rows.append(row)
    return rows


def wobbly(review_data=None) -> list:
    """[(Zeichen, bestes Fach, jetziges Fach)] (Fächer ab 1 gezählt) der Zeichen, die
    früher mindestens Fach WOBBLY_MIN_BOX + 1 erreicht hatten und seitdem um
    WOBBLY_DROP Fächer oder mehr zurückgestuft wurden, stärkster Rückfall zuerst."""
    review_data = review.load() if review_data is None else review_data
    rows = []
    for char, entry in review_data.items():
        if not isinstance(entry, dict) or "due" not in entry or not isinstance(char, str):
            continue
        best, box = review.best_box(entry), int(entry.get("box", 0))
        if best >= WOBBLY_MIN_BOX and best - box >= WOBBLY_DROP:
            rows.append((char, best + 1, box + 1))
    return sorted(rows, key=lambda row: (row[2] - row[1], row[0]))


def median(values):
    return statistics.median(values) if values else None
