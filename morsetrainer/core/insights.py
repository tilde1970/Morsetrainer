"""Auswertungen über mehrere Durchgänge hinweg, aus den Zeichen-Zeilen der
letzten INSIGHT_DAYS Tage: Rückstand beim Mitschreiben, Fehlerarten je Woche,
Ermüdung im Durchgang und Verwechslungspaare im Verlauf. Nur lesend; die
Texte dazu stehen in widgets/insights_panel.py."""
import statistics
from datetime import datetime, timedelta

from morsetrainer.core import db
from morsetrainer.core import stats
from morsetrainer.core import tempo

INSIGHT_DAYS = 90
RECENT_DAYS = 14        # „zuletzt“ gegen „davor“ (Rückstand, Verwechslungspaare)
WEEKS_SHOWN = 6         # Fehlerarten je Woche
MIN_LAG_CHARS = 30      # so viele Messungen je Seite, damit der Rückstand verglichen wird
MIN_WEEK_ERRORS = 5     # Fehler einer Woche, ab denen ihre Aufteilung gezeigt wird
FATIGUE_MIN_CHARS = 30  # kürzere Durchgänge gehen nicht in die Drittel ein
FATIGUE_MIN_SESSIONS = 10
FATIGUE_GAP_PCT = 3     # so viel schlechter am Ende gilt als Nachlassen
PAIR_MIN_SENT = 20      # so oft muss das gesendete Zeichen je Seite vorkommen
PAIRS_SHOWN = 3
UNRECOGNISED = "unrecognised"  # nichts getippt, zu spät oder erst nach Wiederholung
CHARS_PER_WPM_SECOND = 5 / 60  # ein WPM sind fünf Zeichen je Minute


def _sessions(now: datetime, days: int = INSIGHT_DAYS):
    """(Startzeit, Konfiguration, Zeichen-Zeilen ohne Wiederholungsabfragen)
    der abgeschlossenen Durchgänge der letzten `days` Tage seit dem Zurücksetzen,
    ohne selbst bewertete (wie stats._char_events)."""
    since = stats._after_reset(now - timedelta(days=days))
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
                 if obj.get("type") == "char" and "char" in obj and not obj.get("retry")]
        if chars:
            yield start, config, chars


def _effective_wpm(config: dict):
    try:
        fw = config.get("farnsworth_wpm")
        return tempo.effective(int(config["wpm"]), int(fw) if fw else None)
    except (KeyError, TypeError, ValueError):
        return None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 and value == value


def lag_chars(now=None) -> dict:
    """Rückstand beim Mitschreiben am Stück in Zeichen: Zeit vom Tonende des
    Zeichens bis zur Taste, mal Zeichen je Sekunde bei dem effektiven Tempo des
    Durchgangs (so sind Tempi vergleichbar). {"recent": [Werte], "before":
    [Werte]}; nur Durchgänge, die den Rückstand aufgezeichnet haben."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    result = {"recent": [], "before": []}
    for start, config, chars in _sessions(now):
        wpm = _effective_wpm(config)
        if config.get("mode") != "continuous" or wpm is None:
            continue
        side = result["recent" if start >= split else "before"]
        side.extend(obj["lag_s"] * wpm * CHARS_PER_WPM_SECOND for obj in chars if _number(obj.get("lag_s")))
    return result


def causes_by_week(now=None) -> list:
    """Fehler der letzten WEEKS_SHOWN Wochen nach Art (stats.HEARD oder
    UNRECOGNISED): [{"first": Montag, "counts": {Art: Anzahl}, "chars": Zeichen
    der Woche}], älteste Woche zuerst, Wochen ohne Fehler ausgelassen. Nur zwei Arten, weil die
    feineren Ursachen (zu langsam, erst nach Wiederholung) erst seit Oktober 2026
    aufgezeichnet werden; früher stand dort nur „verpasst“."""
    now = now or datetime.now()
    monday = now.date() - timedelta(days=now.weekday())
    first = monday - timedelta(weeks=WEEKS_SHOWN - 1)
    weeks = {first + timedelta(weeks=i): {} for i in range(WEEKS_SHOWN)}
    chars_per_week = dict.fromkeys(weeks, 0)
    for start, _config, chars in _sessions(now, days=(now.date() - first).days + 1):
        week = start.date() - timedelta(days=start.weekday())
        if week not in weeks:
            continue
        for obj in chars:
            if not obj.get("untimed"):
                chars_per_week[week] += 1
            if obj.get("correct") is False and not obj.get("untimed"):
                cause = obj.get("cause") or (stats.HEARD if obj.get("typed") else "missed")
                kind = stats.HEARD if cause in (stats.HEARD, "swap") else UNRECOGNISED
                weeks[week][kind] = weeks[week].get(kind, 0) + 1
    return [{"first": day, "counts": counts, "chars": chars_per_week[day]} for day, counts in weeks.items() if counts]


def fatigue(now=None) -> dict:
    """Erstes, mittleres und letztes Drittel der Durchgänge ab FATIGUE_MIN_CHARS
    Zeichen zusammen: {"sessions", "thirds": [{"good", "wrong", "latencies"}]}."""
    thirds = [{"good": 0, "wrong": 0, "latencies": []} for _ in range(3)]
    sessions = 0
    for _start, _config, chars in _sessions(now or datetime.now()):
        if len(chars) < FATIGUE_MIN_CHARS:
            continue
        sessions += 1
        for index, obj in enumerate(chars):
            part = thirds[index * 3 // len(chars)]
            part["good" if obj.get("correct") is True else "wrong"] += 1
            latency = stats._measured(obj)
            if latency is not None:
                part["latencies"].append(latency)
    return {"sessions": sessions, "thirds": thirds}


def confusion_trend(now=None) -> list:
    """Die häufigsten Verwechslungspaare (gesendet → getippt, klangähnlich) der
    letzten INSIGHT_DAYS Tage mit ihrer Rate zuletzt gegen davor, in Prozent
    der Vorkommen des gesendeten Zeichens: [{"sent", "typed", "count", "before",
    "recent", "n_before", "n_recent", "new"}] (n_*: Vorkommen des gesendeten
    Zeichens je Seite), Rate None bei weniger als PAIR_MIN_SENT Vorkommen; "new":
    eines der beiden Zeichen kam davor nie vor (gerade erst gelernt)."""
    now = now or datetime.now()
    split = now - timedelta(days=RECENT_DAYS)
    sent = {"recent": {}, "before": {}}
    wrong = {"recent": {}, "before": {}}
    for start, _config, chars in _sessions(now):
        side = "recent" if start >= split else "before"
        for obj in chars:
            if obj.get("untimed"):
                continue
            char = obj["char"]
            sent[side][char] = sent[side].get(char, 0) + 1
            # Die Ursache wird erst seit Oktober 2026 gespeichert; davor galt ein getipptes Zeichen als Verwechslung.
            if obj.get("correct") is False and obj.get("typed") and obj.get("cause", stats.HEARD) == stats.HEARD:
                pair = (char, obj["typed"])
                wrong[side][pair] = wrong[side].get(pair, 0) + 1
    totals = {}
    for side in wrong:
        for pair, count in wrong[side].items():
            if stats.sounds_similar(*pair):
                totals[pair] = totals.get(pair, 0) + count
    rows = []
    for (char, typed), count in sorted(totals.items(), key=lambda item: -item[1])[:PAIRS_SHOWN]:
        row = {"sent": char, "typed": typed, "count": count,
               "n_before": sent["before"].get(char, 0), "n_recent": sent["recent"].get(char, 0),
               "new": not sent["before"].get(char) or not sent["before"].get(typed)}
        for side in ("before", "recent"):
            seen = sent[side].get(char, 0)
            row[side] = wrong[side].get((char, typed), 0) / seen * 100 if seen >= PAIR_MIN_SENT else None
        rows.append(row)
    return rows


def median(values):
    return statistics.median(values) if values else None
