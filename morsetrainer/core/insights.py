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
MIN_LAG_SESSIONS = 5    # so viele Durchgänge je Seite, damit der Rückstand verglichen wird
MIN_LAG_VALUES = 10     # und so viele Messungen, damit ein Durchgang zählt
MIN_WEEK_ERRORS = 5     # Fehler einer Woche, ab denen ihre Aufteilung gezeigt wird
WEEK_CHARS_SHOWN = 3    # so viele nicht erkannte Zeichen nennt eine Wochenzeile
MIN_WEEK_CHAR_ERRORS = 2
FATIGUE_MIN_CHARS = 30  # kürzere Durchgänge gehen nicht in die Drittel ein
FATIGUE_MIN_SESSIONS = 10
FATIGUE_VERDICT_SESSIONS = 30  # erst ab so vielen Durchgängen ein Urteil zum Nachlassen
PAIR_MIN_SENT = 20      # so oft muss das gesendete Zeichen je Seite vorkommen
PAIRS_SHOWN = 3         # verschiedene Paare (beide Richtungen zusammen)
PAIR_CHANGE_PCT = 3     # kleinster Unterschied in Prozentpunkten, der überhaupt zählt
PAIR_NOISE_FACTOR = 2.0  # und mindestens so viele Standardfehler des Unterschieds
PAIR_MIN_EXPECTED = 5   # und so viele erwartete Fälle auf jeder Seite (sonst trägt die Näherung nicht)
SAME_MARGIN_PCT = 2.0   # „unverändert“ nur, wenn das 95-%-Intervall des Unterschieds höchstens so breit ist
CHAR_MIN_CASES = 40     # so viele Antworten je Seite, damit ein Zeichen verglichen wird
CHARS_SHOWN = 6
WEAK_CHARS_SHOWN = 5
MIN_WEAK_ERRORS = 5     # so oft nicht erkannt, damit ein Zeichen als schwach gilt
WOBBLY_MIN_BOX = 2      # früher mindestens Fach 3 (Wiederholung nach 4 Tagen) erreicht
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
    `lag_chars`): {"recent": [Mediane der Durchgänge], "before": [...]}, letzte
    RECENT_DAYS Tage gegen davor. Jeder Durchgang mit mindestens MIN_LAG_VALUES
    Messwerten zählt einmal, mit dem Median seiner Werte (aufeinanderfolgende
    Zeichen eines Laufs sind nicht unabhängig). Dazu "accuracy" und "untyped":
    Trefferquote und Anteil nicht getippter Zeichen derselben Durchgänge in
    Prozent je Seite (None ohne Durchgang). Nur Durchgänge, die den Rückstand
    aufgezeichnet haben."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    result = {"recent": [], "before": []}
    right = {"recent": [0, 0], "before": [0, 0]}
    untyped = {"recent": 0, "before": 0}
    for start, config, chars in load(now) if data is None else data:
        if config.get("mode") != "continuous":
            continue
        name = "recent" if start >= split else "before"
        values = [obj["lag_chars"] for obj in chars if _number(obj.get("lag_chars"))]
        if len(values) < MIN_LAG_VALUES:
            continue
        result[name].append(statistics.median(values))
        right[name][0] += sum(1 for obj in chars if obj.get("correct") is True)
        right[name][1] += len(chars)
        untyped[name] += sum(1 for obj in chars if obj.get("correct") is False and not _text(obj.get("typed")))
    result["accuracy"] = {name: good / total * 100 if total else None for name, (good, total) in right.items()}
    result["untyped"] = {name: untyped[name] / total * 100 if total else None for name, (_g, total) in right.items()}
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
    die Woche läuft noch, "partial": die Daten beginnen mitten in der Woche}],
    älteste Woche zuerst, Wochen ohne Fehler ausgelassen.
    Nur grobe Arten, weil die feineren Ursachen (zu langsam, erst nach
    Wiederholung) erst seit Oktober 2026 aufgezeichnet werden; früher stand dort
    nur „verpasst“."""
    now = now or datetime.now()
    monday = now.date() - timedelta(days=now.weekday())
    first = monday - timedelta(weeks=WEEKS_SHOWN - 1)
    weeks = {first + timedelta(weeks=i): {"counts": {}, "chars": 0, "unrecognised": Counter()}
             for i in range(WEEKS_SHOWN)}
    sessions = load(now, days=(now.date() - first).days + 1) if data is None else data
    earliest = min((start.date() for start, _config, _chars in sessions), default=None)
    for start, _config, chars in sessions:
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
    return [{"first": day, "current": day == monday,
             "partial": earliest is not None and day < earliest < day + timedelta(days=7), **week}
            for day, week in weeks.items() if week["counts"]]


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
    Zeichen zusammen: {"sessions", "thirds": [{"good", "wrong", "latencies"}],
    "drops": [Prozentpunkte erstes minus letztes Drittel je Durchgang]}.
    Zeichen ohne Zeitmessung zählen nicht, die Reaktion kommt wie in der
    Vergleichszeile nur aus Einzelzeichen (stats.REACTION_MODE)."""
    thirds = [{"good": 0, "wrong": 0, "latencies": []} for _ in range(3)]
    drops = []
    sessions = 0
    for _start, config, chars in load(now) if data is None else data:
        chars = [obj for obj in chars if not obj.get("untimed")]
        if len(chars) < FATIGUE_MIN_CHARS:
            continue
        sessions += 1
        right = [0, 0, 0]
        size = [0, 0, 0]
        for index, obj in enumerate(chars):
            third = index * 3 // len(chars)
            part = thirds[third]
            size[third] += 1
            right[third] += obj.get("correct") is True
            part["good" if obj.get("correct") is True else "wrong"] += 1
            latency = stats._measured(obj) if config.get("mode") == stats.REACTION_MODE else None
            if latency is not None:
                part["latencies"].append(latency)
        drops.append((right[0] / size[0] - right[2] / size[2]) * 100)
    return {"sessions": sessions, "thirds": thirds, "drops": drops}


def fatigue_drop(data: dict):
    """(Mittel, untere, obere Grenze) des Abfalls vom ersten zum letzten Drittel in
    Prozentpunkten über die Durchgänge (95-%-Intervall des Mittelwerts); None bei
    weniger als zwei Durchgängen."""
    drops = data.get("drops", [])
    if len(drops) < 2:
        return None
    mean = statistics.fmean(drops)
    error = 1.96 * statistics.stdev(drops) / math.sqrt(len(drops))
    return mean, mean - error, mean + error


def rate_verdict(before: float, recent: float, n_before: int, n_recent: int) -> str:
    """LESS, MORE, SAME oder UNSURE für eine Rate (Prozent) zuletzt gegen davor: Ein
    Unterschied zählt erst ab PAIR_CHANGE_PCT Prozentpunkten, mindestens
    PAIR_NOISE_FACTOR Standardfehlern des Unterschieds (aus den Fallzahlen) und
    PAIR_MIN_EXPECTED erwarteten Fällen je Seite. „Unverändert“ (SAME) gibt es nur,
    wenn die Daten so genau sind, dass das 95-%-Intervall des Unterschieds höchstens
    SAME_MARGIN_PCT breit ist; sonst ist nichts sicher (UNSURE)."""
    change = recent - before
    pooled = (before * n_before + recent * n_recent) / (n_before + n_recent) / 100
    noise = math.sqrt(pooled * (1 - pooled) * (1 / n_before + 1 / n_recent)) * 100
    expected = min(pooled * n_before, pooled * n_recent)
    if (expected >= PAIR_MIN_EXPECTED - 1e-9 and abs(change) >= PAIR_CHANGE_PCT
            and abs(change) >= PAIR_NOISE_FACTOR * noise):
        return LESS if change < 0 else MORE
    return SAME if 1.96 * noise <= SAME_MARGIN_PCT else UNSURE


def pair_verdict(row: dict) -> str:
    """rate_verdict() für einen Paar-Eintrag von confusion_trend()."""
    return rate_verdict(row["before"], row["recent"], row["n_before"], row["n_recent"])


def confusion_trend(data=None, now=None) -> list:
    """Die häufigsten Verwechslungspaare (klangähnlich, beide Richtungen
    zusammen gerechnet) der letzten INSIGHT_DAYS Tage, je Richtung mit ihrer Rate
    zuletzt gegen davor, in Prozent der Vorkommen des gesendeten Zeichens:
    [{"sent", "typed", "count", "before", "recent", "n_before", "n_recent",
    "k_before", "k_recent", "new"}] (k: so oft wurde `typed` getippt, n: so oft kam `sent`), die Richtungen eines Paares hintereinander, die häufigere zuerst.
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
                   "k_before": wrong["before"][(char, typed)], "k_recent": wrong["recent"][(char, typed)],
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


def reached_high_box(review_data=None) -> bool:
    """Hat schon ein Zeichen der Lernkartei Fach WOBBLY_MIN_BOX + 1 oder höher erreicht?
    Sonst kann noch keines „wieder wackelig“ sein."""
    review_data = review.load() if review_data is None else review_data
    return any(isinstance(entry, dict) and "due" in entry and review.best_box(entry) >= WOBBLY_MIN_BOX
               for entry in review_data.values())


def char_trend(data=None, now=None) -> list:
    """Fehlerquote je Zeichen, letzte RECENT_DAYS Tage gegen die Zeit davor (alle Fehlerarten, ohne
    Zeichen ohne Zeitmessung): [{"char", "before", "recent", "n_before", "n_recent", "k_before",
    "k_recent"}] (Raten in Prozent, k falsche von n Antworten), für
    Zeichen mit mindestens CHAR_MIN_CASES Antworten auf jeder Seite, die schwächsten (zuletzt) zuerst,
    höchstens CHARS_SHOWN."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    seen = {"recent": Counter(), "before": Counter()}
    wrong = {"recent": Counter(), "before": Counter()}
    for start, _config, chars in load(now) if data is None else data:
        side = "recent" if start >= split else "before"
        for obj in chars:
            if obj.get("untimed"):
                continue
            seen[side][obj["char"]] += 1
            if obj.get("correct") is False:
                wrong[side][obj["char"]] += 1
    rows = [{"char": char, "n_before": seen["before"][char], "n_recent": seen["recent"][char],
             "k_before": wrong["before"][char], "k_recent": wrong["recent"][char],
             "before": wrong["before"][char] / seen["before"][char] * 100,
             "recent": wrong["recent"][char] / seen["recent"][char] * 100}
            for char in seen["recent"]
            if seen["recent"][char] >= CHAR_MIN_CASES and seen["before"][char] >= CHAR_MIN_CASES]
    return sorted(rows, key=lambda row: (-row["recent"], row["char"]))[:CHARS_SHOWN]


def median(values):
    return statistics.median(values) if values else None
