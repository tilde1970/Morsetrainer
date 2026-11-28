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
CLUSTER_MIN_SESSIONS = 3  # so viele Durchgänge je Seite, damit ein Urteil über ein Zeichen möglich ist
CHARS_SHOWN = 6
WEAK_CHARS_SHOWN = 5
MIN_WEAK_ERRORS = 5     # so oft nicht erkannt, damit ein Zeichen als schwach gilt
WOBBLY_MIN_BOX = 2      # früher mindestens Fach 3 (Wiederholung nach 4 Tagen) erreicht
WOBBLY_DROP = 2         # und um so viele Fächer zurückgestuft
WOBBLY_DAYS = 2         # an so vielen verschiedenen Tagen seit dem besten Fach nicht sicher (ein Tag kann Zufall sein)
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


def fatigue(data=None, now=None, mode=None) -> dict:
    """Erstes, mittleres und letztes Drittel der Durchgänge ab FATIGUE_MIN_CHARS
    Zeichen zusammen: {"sessions", "thirds": [{"good", "wrong", "latencies"}],
    "drops": [Prozentpunkte erstes minus letztes Drittel je Durchgang]}.
    Mit `mode` nur die Durchgänge dieses Modus (sonst alle). Zeichen ohne Zeitmessung
    zählen nicht, die Reaktion kommt wie in der Vergleichszeile nur aus Einzelzeichen
    (stats.REACTION_MODE)."""
    thirds = [{"good": 0, "wrong": 0, "latencies": []} for _ in range(3)]
    drops = []
    sessions = 0
    for _start, config, chars in load(now) if data is None else data:
        if mode is not None and config.get("mode") != mode:
            continue
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


def fatigue_by_mode(data=None, now=None) -> dict:
    """fatigue() je Modus, der mindestens FATIGUE_MIN_SESSIONS lange Durchgänge hat, die
    meisten zuerst: {Modus: fatigue()}. Die Modi unterscheiden sich so stark in Tempo und
    Aufgabe, dass ein gemeinsamer Schnitt nur den Modus-Mix zeigt."""
    data = load(now) if data is None else data
    modes = {config.get("mode") for _start, config, _chars in data if isinstance(config.get("mode"), str)}
    result = {mode: fatigue(data, mode=mode) for mode in modes}
    result = {mode: part for mode, part in result.items() if part["sessions"] >= FATIGUE_MIN_SESSIONS}
    return dict(sorted(result.items(), key=lambda item: (-item[1]["sessions"], item[0])))


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


def cluster_verdict(before: list, recent: list) -> str:
    """LESS, MORE, SAME oder UNSURE für eine Fehlerrate zuletzt gegen davor, wenn die Antworten
    zu Durchgängen gehören: `before` und `recent` sind Listen (falsch, Antworten) je Durchgang.
    Die Antworten eines Durchgangs hängen zusammen (Tagesform, Tempo, Zeichensatz), deshalb
    zählen die Durchgänge, nicht die Antworten, als Stichprobe: Der Fehler des Unterschieds
    kommt aus der Streuung der Durchgangsraten (Verhältnisschätzer). Ein Unterschied zählt
    ab PAIR_CHANGE_PCT Prozentpunkten und nur, wenn das 95-%-Intervall die Null nicht
    einschließt; je Seite braucht es CLUSTER_MIN_SESSIONS Durchgänge. „Unverändert“ (SAME)
    nur bei einem Intervall von höchstens SAME_MARGIN_PCT Breite, sonst UNSURE."""
    if min(len(before), len(recent)) < CLUSTER_MIN_SESSIONS:
        return UNSURE
    variance, rates = 0.0, []
    for sessions in (before, recent):
        total = sum(n for _k, n in sessions)
        if total <= 0:
            return UNSURE
        rate = sum(k for k, _n in sessions) / total
        rates.append(rate * 100)
        spread = sum((k - rate * n) ** 2 for k, n in sessions)
        variance += spread * len(sessions) / (len(sessions) - 1) / total ** 2
    change = rates[1] - rates[0]
    margin = 1.96 * math.sqrt(variance) * 100
    if abs(change) >= PAIR_CHANGE_PCT and abs(change) > margin:
        return LESS if change < 0 else MORE
    return SAME if margin <= SAME_MARGIN_PCT else UNSURE


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


def wobbly(review_data=None, log=None) -> list:
    """[(Zeichen, bestes Fach, jetziges Fach)] (Fächer ab 1 gezählt) der Zeichen, die
    früher mindestens Fach WOBBLY_MIN_BOX + 1 erreicht hatten, seitdem um
    WOBBLY_DROP Fächer oder mehr zurückgestuft wurden und an mindestens WOBBLY_DAYS
    Tagen nach dem besten Fach nicht sicher waren (Anteil flüssiger Treffer unter
    review.SURE_SHARE, laut Protokoll `log`): Auch ein sicheres Zeichen fällt an
    einem einzelnen Tag mit einigen Prozent Wahrscheinlichkeit durch. Stärkster
    Rückfall zuerst."""
    review_data = review.load() if review_data is None else review_data
    log = review.load_log() if log is None else log
    weak_days = {}  # Zeichen -> Tage mit Entscheidung unter der Sicher-Schwelle
    for entry in log:
        try:
            if entry["share"] < review.SURE_SHARE:
                weak_days.setdefault(entry["c"], set()).add(str(entry["day"]))
        except (KeyError, TypeError):
            continue
    rows = []
    for char, entry in review_data.items():
        if not isinstance(entry, dict) or "due" not in entry or not isinstance(char, str):
            continue
        best, box = review.best_box(entry), int(entry.get("box", 0))
        if best >= WOBBLY_MIN_BOX and best - box >= WOBBLY_DROP:
            since = str(entry.get("best_day", ""))
            if len([day for day in weak_days.get(char, ()) if day > since]) >= WOBBLY_DAYS:
                rows.append((char, best + 1, box + 1))
    return sorted(rows, key=lambda row: (row[2] - row[1], row[0]))


def reached_high_box(review_data=None) -> bool:
    """Hat schon ein Zeichen der Lernkartei Fach WOBBLY_MIN_BOX + 1 oder höher erreicht?
    Sonst kann noch keines „wieder wackelig“ sein."""
    review_data = review.load() if review_data is None else review_data
    return any(isinstance(entry, dict) and "due" in entry and review.best_box(entry) >= WOBBLY_MIN_BOX
               for entry in review_data.values())


def char_trend(data=None, now=None) -> list:
    """Fehlerquote je Zeichen und Modus, letzte RECENT_DAYS Tage gegen die Zeit davor (alle
    Fehlerarten, ohne Zeichen ohne Zeitmessung): [{"char", "mode", "before", "recent",
    "n_before", "n_recent", "k_before", "k_recent", "sessions_before", "sessions_recent",
    "verdict"}] (Raten in Prozent, k falsche von n Antworten), für Zeichen mit mindestens
    CHAR_MIN_CASES Antworten auf jeder Seite, die schwächsten (zuletzt) zuerst, höchstens
    CHARS_SHOWN. Je Modus gerechnet: Dasselbe Zeichen ist einzeln, in Gruppen oder am Stück
    verschieden schwer, und ein Modus-Wechsel würde sonst als Fortschritt oder Rückfall
    erscheinen. Das Urteil zählt Durchgänge (cluster_verdict)."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    cells = {}  # (Zeichen, Modus, Seite) -> [[falsch, Antworten] je Durchgang]
    for start, config, chars in load(now) if data is None else data:
        mode = config.get("mode")
        mode = mode if isinstance(mode, str) else ""
        side = "recent" if start >= split else "before"
        per_char = {}
        for obj in chars:
            if obj.get("untimed"):
                continue
            counts = per_char.setdefault(obj["char"], [0, 0])
            counts[1] += 1
            counts[0] += obj.get("correct") is False
        for char, counts in per_char.items():
            cells.setdefault((char, mode, side), []).append(counts)
    rows = []
    for (char, mode, side), recent in cells.items():
        if side != "recent":
            continue
        before = cells.get((char, mode, "before"), [])
        n_recent, n_before = sum(n for _k, n in recent), sum(n for _k, n in before)
        if n_recent < CHAR_MIN_CASES or n_before < CHAR_MIN_CASES:
            continue
        k_recent, k_before = sum(k for k, _n in recent), sum(k for k, _n in before)
        rows.append({"char": char, "mode": mode, "n_before": n_before, "n_recent": n_recent,
                     "k_before": k_before, "k_recent": k_recent,
                     "before": k_before / n_before * 100, "recent": k_recent / n_recent * 100,
                     "sessions_before": len(before), "sessions_recent": len(recent),
                     "verdict": cluster_verdict(before, recent)})
    return sorted(rows, key=lambda row: (-row["recent"], row["char"], row["mode"]))[:CHARS_SHOWN]


def median(values):
    return statistics.median(values) if values else None
