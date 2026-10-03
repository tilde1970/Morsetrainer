"""Diplome: dauerhafte Erfolge wie bei DXCC oder WAC, in Stufen Bronze,
Silber, Gold und teils Platin (Konzept-Motivation.md, „Dauerhaft: Diplome“).

Ausgewertet wird immer alles, was schon gespeichert ist: Sitzungsdateien,
stats/results.jsonl, Lernkartei (höchstes je erreichtes Fach) und
Übungszeit je Tag. Vergeben wird nur aus Durchgängen ohne Selbstbewertung.
Was einmal erreicht ist, steht mit Datum in stats/awards.json und geht nie
verloren, auch nicht durch „Gesamtstatistik zurücksetzen“ (die
Sitzungsdateien bleiben dabei ohnehin stehen).

Beim ersten Mal wird still nachgetragen, was sich aus dem bisherigen Üben
ergibt (mit dem Tag, an dem es erreicht wurde); danach gilt ein neues
Siegel ab dem Tag, an dem es auffällt.

Fächer der Lernkartei heißen hier wie in der Oberfläche 1–6 (`box` 0–5)."""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from morsetrainer.i18n import N_
from morsetrainer.core import koch, practice, review, stats, storage, words

AWARDS_FILE_NAME = "awards.json"

LEVEL_NAMES = (N_("Bronze"), N_("Silber"), N_("Gold"), N_("Platin"))
SILVER = 1

# Fach 3, 4, 6 der Oberfläche als `box` der Lernkartei.
BOX_3, BOX_4, BOX_6 = 2, 3, 5

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
# Voller Koch-Zeichensatz ohne die Betriebszeichen (Lektion 40, wie lcwo.net).
FULL_CHARSET = koch.lesson_charset(40)

MIN_CHAR_WPM = koch.SLOW_CHAR_WPM  # 18: darunter lassen sich Punkte und Striche zählen
FULL_RUN_S = 180                   # „voller 3-Min.-Lauf“
DAY_GOAL_S = 600                   # Ausdauer: Tage mit ≥ 10 Min. Übung

Q_GROUPS = tuple(word for word in words.WORDS if len(word) == 3 and word.startswith("Q"))
CONTEST_KINDS = ("cqww", "wpx", "wag", "arrldx", "iaru")
RAGCHEW = "ragchew"
# Klartext im Reiter Kontinuierlich (ohne eigene Texte, siehe modes/content.py).
PLAIN_CONTENT = {"words", "phrases", "qso"}


@dataclass(frozen=True)
class Award:
    key: str
    name: str
    condition: str
    targets: tuple          # Schwelle je Stufe; ohne Stufen genau eine
    unit: str = ""          # Einheit des Fortschritts („Buchstaben“, „WPM“ …)
    from_lesson: int = None
    levels: bool = True
    two_days: bool = False  # Silber und höher erst an zwei verschiedenen Tagen
    stepped: bool = False   # Stufen aus mehreren Bedingungen: Fortschritt ist die Stufe selbst


AWARDS = (
    Award("koch", N_("Koch"), N_("Bestandener Aufstiegslauf (≥ 50 Zeichen, ≥ 90 % beim ersten Versuch, "
                                "Zeichen ≥ 18 WPM)"), (10, 25, 44), N_("Lektion"), 1),
    Award("wal", N_("Worked All Letters"), N_("Bronze: 10 Buchstaben in Fach 3, Silber: alle 26, "
                                             "Gold: alle Buchstaben in Fach 6 und alle Ziffern in Fach 4"),
          (1, 2, 3), "", 1, stepped=True),
    Award("flow", N_("Mitschreiben im Fluss"), N_("Kontinuierlich mit Klartext, voller 3-Min.-Lauf, ≥ 90 % "
                                                 "abzüglich überzähliger Tasten, Zeichen ≥ 18 WPM"),
          (10, 15, 22), N_("WPM eff."), 15, two_days=True),
    Award("qrq", N_("QRQ"), N_("Kontinuierlich mit Zufallsgruppen (≥ 5 Zeichen), voller Zeichensatz, ohne "
                               "Farnsworth, voller 3-Min.-Lauf, ≥ 90 % abzüglich überzähliger Tasten"),
          (20, 25, 30, 35), N_("WPM"), 40, two_days=True),
    Award("qrn", N_("QRN-fest"), N_("Gruppen oder Kontinuierlich, ≥ 200 Zeichen, Störlautstärke ≥ 100 %, "
                                    "Zeichen ≥ 20 WPM, effektiv ≥ 12 WPM; Bronze: Band leicht 90 %, "
                                    "Silber: mittel 90 %, Gold: stark 85 %"),
          (1, 2, 3), "", 25, two_days=True, stepped=True),
    Award("rufz", N_("Rufz"), N_("Voller Rufz-Durchgang mit 50 Rufzeichen, ohne Präfix-Filter, "
                                 "Zeichentempo beim Start ≥ 20 WPM"),
          (2000, 3500, 5500, 7500), N_("Punkte"), 27, two_days=True),
    Award("contest", N_("Contest"), N_("Durchgang ≥ 10 Min.; Bronze: ≥ 20 WPM, 10 QSOs in 10 Min., ≤ 10 % "
                                       "Fehler; Silber: ≥ 25 WPM, Aktivität ≥ 2, 20 QSOs, ≤ 5 %; "
                                       "Gold: ≥ 30 WPM, Aktivität ≥ 3, 25 QSOs, höchstens 1 Fehler"),
          (1, 2, 3), "", 44, two_days=True, stepped=True),
    Award("wpx", N_("WPX"), N_("Verschiedene WPX-Präfixe, beim ersten Versuch richtig (Rufzeichen und "
                               "Contest)"), (100, 400, 1200, 2000), N_("Präfixe"), 25),
    Award("headphones", N_("Kopfhörer"), N_("3 normale QSOs in Folge mit „Kopfhören + Fragen“, alle Fragen "
                                            "richtig, ohne „Nochmal“"), (15, 20, 25), N_("WPM eff."), 44),
    Award("confusion", N_("Verwechslung überwunden"), N_("Ein häufig verwechseltes Paar 28 Tage lang mit je "
                                                         "≥ 40 Versuchen höchstens einmal verwechselt"),
          (1, 3, 6), N_("Paare"), 5),
    Award("endurance", N_("Ausdauer"), N_("Tage mit ≥ 10 Min. Übung, nicht in Folge"),
          (10, 50, 150, 365), N_("Tage")),
    Award("heard", N_("Zeichen gehört"), N_("Richtig erkannte Zufallszeichen"),
          (5000, 25000, 100000, 250000), N_("Zeichen")),
    Award("first_qso", N_("Erstes QSO verstanden"), N_("Normales QSO mit Abfrage, alles richtig, ohne "
                                                       "„Nochmal“, ≥ 15 WPM effektiv"), (1,), levels=False),
    Award("all_contests", N_("Worked All Contests"), N_("Alle 5 Contest-Arten mit je ≥ 30 QSOs und ≤ 10 % "
                                                        "Fehlern"), (5,), N_("Contests"), levels=False),
    Award("club", N_("Clubabend"), N_("An einer Netzwerk-Übung teilgenommen"), (1,), levels=False),
    Award("q_groups", N_("Q-Gruppen-Kenner"), N_("Jede der 20 Q-Gruppen 3× beim ersten Hören richtig, an "
                                                 "mindestens 2 Tagen, Zeichen ≥ 18 WPM"),
          (len(Q_GROUPS),), N_("Q-Gruppen"), levels=False),
    Award("digits", N_("Alle Ziffern"), N_("Alle 10 Ziffern mindestens in Fach 3"), (10,), N_("Ziffern"),
          levels=False),
)
BY_KEY = {award.key: award for award in AWARDS}


# --- Daten ----------------------------------------------------------------------
@dataclass
class Session:
    day: date
    config: dict
    summary: dict
    chars: list   # [(gesendet, getippt, richtig)]
    groups: list  # [(gesendet, getippt, erster Versuch richtig oder None)]


@dataclass
class Data:
    sessions: list
    results: list   # Einträge aus results.jsonl mit "day"
    review: dict
    practice: dict


# Sitzungsdateien ändern sich nach dem Schreiben nicht mehr: einmal gelesen,
# bleiben sie im Speicher (Schlüssel: Pfad, Größe, Änderungszeit).
_session_cache = {}


def _read_session(path):
    try:
        info = path.stat()
    except OSError:
        return None
    key = (str(path), info.st_size, info.st_mtime)
    if key in _session_cache:
        return _session_cache[key]
    config = summary = None
    chars, groups = [], []
    for obj in stats._read_jsonl(path):
        kind = obj.get("type")
        if kind == "config":
            config = obj
        elif kind == "summary":
            summary = obj
        elif kind == "char":
            chars.append((obj.get("char", ""), obj.get("typed", ""), bool(obj.get("correct"))))
        elif kind == "group":
            groups.append((obj.get("sent", ""), obj.get("typed", ""), obj.get("first")))
    session = None
    if config and summary and not config.get("self_assessed"):
        try:
            day = datetime.fromisoformat(config["start_time"]).date()
            session = Session(day, config, summary, chars, groups)
        except (KeyError, TypeError, ValueError):
            pass
    _session_cache[key] = session
    return session


def load_data() -> Data:
    sessions = [s for s in (_read_session(p) for p in sorted(stats.STATS_DIR.glob("20*.jsonl"))) if s]
    sessions.sort(key=lambda s: s.config.get("start_time", ""))
    results = []
    for obj in stats._read_jsonl(stats.RESULTS_FILE):
        try:
            results.append({**obj, "day": datetime.fromisoformat(obj["time"]).date()})
        except (KeyError, TypeError, ValueError):
            continue
    results.sort(key=lambda r: r["time"])
    return Data(sessions, results, review.load(), practice.load())


# --- Hilfen ------------------------------------------------------------------------
def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_share(summary: dict) -> float:
    """Trefferquote abzüglich überzähliger Tasten (Kontinuierlich)."""
    total = _num(summary.get("total"))
    if not total:
        return 0.0
    return max(_num(summary.get("correct")) - _num(summary.get("extra_keys")), 0.0) / total


def _char_wpm(config: dict) -> float:
    return _num(config.get("wpm"))


def _farnsworth(config: dict) -> bool:
    fw = config.get("farnsworth_wpm")
    return bool(fw) and _num(fw) < _char_wpm(config)


def _effective_wpm(session: Session) -> float:
    try:
        return float(stats._session_effective_wpm(session.config, session.summary))
    except (KeyError, TypeError, ValueError):
        return 0.0


def _full_run(session: Session) -> bool:
    return bool(session.summary.get("completed")) and _num(session.summary.get("duration_s")) >= FULL_RUN_S


def _contains(charset, chars: str) -> bool:
    return isinstance(charset, str) and set(chars) <= set(charset)


def _cumulative(dated_items) -> list:
    """[(Tag, Wert)] -> [(Tag, laufende Summe)], chronologisch."""
    total, out = 0, []
    for day, value in sorted(dated_items, key=lambda item: item[0]):
        total += value
        out.append((day, total))
    return out


def level_dates(events, targets, two_days=False) -> list:
    """Tag, an dem jede Stufe erreicht wurde (None: noch nicht). `events`:
    [(Tag, Wert)]; eine Stufe gilt, sobald ein Wert ihre Schwelle erreicht,
    bei `two_days` ab Silber erst am zweiten verschiedenen Tag."""
    out = []
    for index, target in enumerate(targets):
        days = sorted({day for day, value in events if value >= target})
        need = 2 if two_days and index >= SILVER else 1
        out.append(days[need - 1] if len(days) >= need else None)
    return out


@dataclass
class Status:
    dates: list   # Tag je Stufe oder None
    value: float  # aktueller Stand (bester Wert bzw. Summe; bei `stepped` die erreichte Stufe)


def _status(award: Award, events) -> Status:
    value = max((v for _, v in events), default=0)
    return Status(level_dates(events, award.targets, award.two_days), value)


# --- Die einzelnen Diplome ---------------------------------------------------------
def _koch(data: Data) -> list:
    events = []
    for s in data.sessions:
        mode, lesson = s.config.get("mode"), s.config.get("lesson")
        if not isinstance(lesson, int) or _char_wpm(s.config) < MIN_CHAR_WPM:
            continue
        if mode == "group":
            total = _num(s.summary.get("first_try_total", s.summary.get("total")))
            correct = _num(s.summary.get("first_try_correct", s.summary.get("correct")))
        elif mode == "continuous" and s.config.get("content", "chars") == "chars":
            total = _num(s.summary.get("total"))
            correct = _clean_share(s.summary) * total
        else:
            continue
        if total and koch.passed(correct, total):
            events.append((s.day, lesson))
    return events


def _best_day(entry: dict, fallback: date) -> date:
    try:
        return date.fromisoformat(entry.get("best_day") or entry.get("day"))
    except (TypeError, ValueError):
        return fallback


def _wal(data: Data, today: date) -> list:
    reached = {ch: (review.best_box(e), _best_day(e, today)) for ch, e in data.review.items()}
    letters3 = sorted(day for ch, (box, day) in reached.items() if ch in LETTERS and box >= BOX_3)
    events = []
    if len(letters3) >= 10:
        events.append((letters3[9], 1))
    if len(letters3) == len(LETTERS):
        events.append((letters3[-1], 2))
    gold = [reached.get(ch, (0, None)) for ch in LETTERS] + [reached.get(ch, (0, None)) for ch in DIGITS]
    if all(box >= (BOX_6 if i < len(LETTERS) else BOX_4) for i, (box, _) in enumerate(gold)):
        events.append((max(day for _, day in gold), 3))
    return events


def wal_progress(data: Data) -> tuple:
    """(erreicht, nötig) für die nächste Stufe von Worked All Letters."""
    boxes = {ch: review.best_box(e) for ch, e in data.review.items()}
    letters3 = sum(boxes.get(ch, 0) >= BOX_3 for ch in LETTERS)
    if letters3 < 10:
        return letters3, 10
    if letters3 < len(LETTERS):
        return letters3, len(LETTERS)
    have = sum(boxes.get(ch, 0) >= BOX_6 for ch in LETTERS) + sum(boxes.get(ch, 0) >= BOX_4 for ch in DIGITS)
    return have, len(LETTERS) + len(DIGITS)


def _flow(data: Data) -> list:
    events = []
    for s in data.sessions:
        c = s.config
        if (c.get("mode") == "continuous" and c.get("content") in PLAIN_CONTENT and _full_run(s)
                and _char_wpm(c) >= MIN_CHAR_WPM and _clean_share(s.summary) >= 0.9):
            events.append((s.day, _effective_wpm(s)))
    return events


def _qrq(data: Data) -> list:
    events = []
    for s in data.sessions:
        c = s.config
        if (c.get("mode") == "continuous" and c.get("content", "chars") == "chars"
                and _num(c.get("group_len")) >= 5 and _contains(c.get("charset"), FULL_CHARSET)
                and not _farnsworth(c) and _full_run(s) and _clean_share(s.summary) >= 0.9):
            events.append((s.day, _char_wpm(c)))
    return events


BAND_RANK = {"light": 1, "medium": 2, "heavy": 3}


def _qrn(data: Data) -> list:
    events = []
    for s in data.sessions:
        c, summary = s.config, s.summary
        mode, rank = c.get("mode"), BAND_RANK.get(c.get("band"))
        if mode not in ("group", "continuous") or rank is None:
            continue
        # Kontinuierlich hat keinen Regler für die Störlautstärke: immer 100 %.
        gain = _num(c.get("band_gain"), 100) if mode == "group" else 100
        if (gain < 100 or _num(summary.get("total")) < 200 or _char_wpm(c) < 20 or _effective_wpm(s) < 12
                or not _contains(c.get("charset"), koch.lesson_charset(25))):
            continue
        share = _clean_share(summary) if mode == "continuous" else _num(summary.get("accuracy_pct")) / 100
        level = rank if share >= 0.9 else 3 if rank == 3 and share >= 0.85 else 0
        if level:
            events.append((s.day, level))
    return events


def _rufz(data: Data) -> list:
    events = []
    for r in data.results:
        if r.get("mode") != "rufz" or _num(r.get("total")) < 50 or r.get("prefixes"):
            continue
        if r.get("start_wpm") is not None and _num(r["start_wpm"]) < 20:
            continue  # ältere Einträge kennen das Starttempo nicht
        events.append((r["day"], _num(r.get("score"))))
    return events


def contest_errors(r: dict) -> int:
    return int(sum(_num(r.get(kind)) for kind in ("busted", "nil", "exchange")))


def _contest(data: Data) -> list:
    events = []
    for r in data.results:
        minutes = _num(r.get("minutes"))
        if r.get("mode") != "contest" or minutes < 10 or not _num(r.get("total")):
            continue
        wpm, activity = _num(r.get("wpm")), _num(r.get("activity"), 1)
        rate = _num(r.get("correct")) / minutes * 10  # richtige QSOs in 10 Minuten
        errors = contest_errors(r)
        share = errors / _num(r["total"])
        level = 0
        if wpm >= 20 and rate >= 10 and share <= 0.10:
            level = 1
        if wpm >= 25 and activity >= 2 and rate >= 20 and share <= 0.05:
            level = 2
        if wpm >= 30 and activity >= 3 and rate >= 25 and errors <= 1:
            level = 3
        if level:
            events.append((r["day"], level))
    return events


_PORTABLE = {"P", "M", "MM", "AM", "QRP", "A"}


def wpx_prefix(call: str):
    """WPX-Präfix eines Rufzeichens (CQ-WPX-Regeln, vereinfacht): alles bis
    zur letzten Ziffer des Rufzeichenteils (DL1ABC -> DL1, S51A -> S51);
    /P und /M zählen nicht; ein Gast-Präfix ohne Ziffer zählt mit 0
    (OE/DL1ABC -> OE0), eine angehängte Ziffer ersetzt die eigene
    (W1AW/4 -> W4). None, wenn sich nichts ableiten lässt."""
    parts = [p for p in call.upper().strip().split("/") if p and p not in _PORTABLE]
    if not parts:
        return None
    base = max(parts, key=len)
    others = [p for p in parts if p is not base]
    digit = next((p for p in others if p.isdigit() and len(p) == 1), None)
    guest = next((p for p in others if not p.isdigit()), None)
    if guest:
        match = re.match(r"^(.*\d)", guest)
        return match.group(1) if match else guest + "0"
    match = re.match(r"^([A-Z0-9]*?\d+)[A-Z]*$", base)
    if not match:
        return None if not base.isalpha() else base[:2] + "0"
    prefix = match.group(1)
    if digit:
        prefix = re.sub(r"\d+$", digit, prefix)
    return prefix


def _wpx(data: Data) -> list:
    first_day = {}

    def add(call, day):
        prefix = wpx_prefix(call)
        if prefix and prefix not in first_day:
            first_day[prefix] = day

    for s in data.sessions:
        if s.config.get("mode") == "callsign":
            for sent, typed, first in s.groups:
                # Ältere Dateien kennen den ersten Versuch nicht: richtig getippt zählt.
                if first or (first is None and sent == typed):
                    add(sent, s.day)
    for r in data.results:
        if r.get("mode") == "contest":
            for call in r.get("calls") or ():
                add(call, r["day"])
    return _cumulative((day, 1) for day in first_day.values())


def _headphones(data: Data) -> list:
    events, run = [], []
    for r in data.results:
        if r.get("mode") != "qso_head" or r.get("kind") != RAGCHEW:
            continue
        if _num(r.get("total")) and r.get("correct") == r.get("total") and not r.get("replays"):
            run.append(_num(r.get("wpm")))
            if len(run) >= 3:
                events.append((r["day"], min(run[-3:])))
        else:
            run = []
    return events


# Verwechslung überwunden: Paar war in einem 30-Tage-Fenster unter den
# häufigsten 10 (≥ 5 Verwechslungen, ≥ 5 % Anteil), danach 28 Tage lang
# beide Zeichen je ≥ 40 Versuche mit höchstens einer Verwechslung.
CONFUSION_WINDOW = 30
CONFUSION_TOP = 10
CONFUSION_MIN = 5
CONFUSION_SHARE = 0.05
CLEAN_DAYS = 28
CLEAN_ATTEMPTS = 40


def _random_chars(session: Session) -> bool:
    mode = session.config.get("mode")
    return mode in ("single", "group") or (
        mode == "continuous" and session.config.get("content", "chars") == "chars")


def _daily_char_counts(data: Data):
    """Je Tag: Versuche je Zeichen und Verwechslungen je Paar (aus Zufallszeichen)."""
    attempts, confusions = {}, {}
    for s in data.sessions:
        if not _random_chars(s):
            continue
        day_attempts = attempts.setdefault(s.day, {})
        day_confusions = confusions.setdefault(s.day, {})
        for sent, typed, correct in s.chars:
            day_attempts[sent] = day_attempts.get(sent, 0) + 1
            if not correct and len(typed) == 1 and typed != sent and typed.strip():
                pair = frozenset((sent, typed))
                day_confusions[pair] = day_confusions.get(pair, 0) + 1
    return attempts, confusions


def _window_sum(per_day: dict, first: date, last: date) -> dict:
    out = {}
    day = first
    while day <= last:
        for key, n in per_day.get(day, {}).items():
            out[key] = out.get(key, 0) + n
        day += timedelta(days=1)
    return out


def _confusion(data: Data) -> list:
    attempts, confusions = _daily_char_counts(data)
    if not attempts:
        return []
    days = sorted(attempts)
    # Tage, an denen ein Paar verwechselt wurde und (im Fenster bis dahin)
    # zu den häufigsten gehörte.
    problem_days = {}
    for day in days:
        start = day - timedelta(days=CONFUSION_WINDOW - 1)
        conf = _window_sum(confusions, start, day)
        if not conf:
            continue
        tries = _window_sum(attempts, start, day)
        ranked = sorted(conf.items(), key=lambda item: -item[1])[:CONFUSION_TOP]
        for pair, n in ranked:
            if not confusions.get(day, {}).get(pair):
                continue
            pair_tries = sum(tries.get(ch, 0) for ch in pair)
            if n >= CONFUSION_MIN and pair_tries and n / pair_tries >= CONFUSION_SHARE:
                problem_days.setdefault(pair, []).append(day)
    overcome = []
    for pair, marked in problem_days.items():
        last_problem = max(marked)
        # Frühestens 28 Tage nach dem letzten Tag als Problem, Fenster danach.
        for day in days:
            start = day - timedelta(days=CLEAN_DAYS - 1)
            if start <= last_problem:
                continue
            tries = _window_sum(attempts, start, day)
            conf = _window_sum(confusions, start, day).get(pair, 0)
            if all(tries.get(ch, 0) >= CLEAN_ATTEMPTS for ch in pair) and conf <= 1:
                overcome.append((day, 1))
                break
    return _cumulative(overcome)


def _endurance(data: Data) -> list:
    days = []
    for key, seconds in data.practice.items():
        try:
            if seconds >= DAY_GOAL_S:
                days.append((date.fromisoformat(key), 1))
        except ValueError:
            continue
    return _cumulative(days)


def _heard(data: Data) -> list:
    return _cumulative((s.day, sum(1 for _, _, ok in s.chars if ok)) for s in data.sessions if _random_chars(s))


def _first_qso(data: Data) -> list:
    return [(r["day"], 1) for r in data.results
            if r.get("mode") in ("qso_quiz", "qso_head") and r.get("kind") == RAGCHEW and _num(r.get("total"))
            and r.get("correct") == r.get("total") and not r.get("replays") and _num(r.get("wpm")) >= 15]


def _all_contests(data: Data) -> list:
    first_day = {}
    for r in data.results:
        total = _num(r.get("total"))
        if (r.get("mode") == "contest" and r.get("contest") in CONTEST_KINDS and total >= 30
                and contest_errors(r) / total <= 0.10):
            first_day.setdefault(r["contest"], r["day"])
    return _cumulative((day, 1) for day in first_day.values())


def _club(data: Data) -> list:
    days = [(s.day, 1) for s in data.sessions if s.config.get("mode") == "network"]
    days += [(r["day"], 1) for r in data.results if r.get("mode") == "network"]
    return days


def _q_groups(data: Data) -> list:
    hits = {}
    for s in data.sessions:
        if s.config.get("mode") != "word" or _char_wpm(s.config) < MIN_CHAR_WPM:
            continue
        for sent, _, first in s.groups:
            if sent in Q_GROUPS and first:
                hits.setdefault(sent, []).append(s.day)
    done = []
    for days in hits.values():
        days.sort()
        for index in range(2, len(days)):
            if len(set(days[:index + 1])) >= 2:
                done.append((days[index], 1))
                break
    return _cumulative(done)


def _digits(data: Data, today: date) -> list:
    reached = sorted(_best_day(e, today) for ch, e in data.review.items()
                     if ch in DIGITS and review.best_box(e) >= BOX_3)
    return [(day, n) for n, day in enumerate(reached, 1)]


def evaluate(data: Data = None, today: date = None) -> dict:
    """Stand aller Diplome aus den gespeicherten Daten: {Schlüssel: Status}."""
    data = data or load_data()
    today = today or date.today()
    events = {
        "koch": _koch(data), "wal": _wal(data, today), "flow": _flow(data), "qrq": _qrq(data),
        "qrn": _qrn(data), "rufz": _rufz(data), "contest": _contest(data), "wpx": _wpx(data),
        "headphones": _headphones(data), "confusion": _confusion(data), "endurance": _endurance(data),
        "heard": _heard(data), "first_qso": _first_qso(data), "all_contests": _all_contests(data),
        "club": _club(data), "q_groups": _q_groups(data), "digits": _digits(data, today),
    }
    return {award.key: _status(award, events[award.key]) for award in AWARDS}


# --- Protokoll ---------------------------------------------------------------------
def _path():
    return stats.STATS_DIR / AWARDS_FILE_NAME


def load() -> dict:
    data = storage.load_json(_path(), {})
    if not isinstance(data, dict):
        data = {}
    seals = data.get("seals") if isinstance(data.get("seals"), dict) else {}
    return {"seals": {k: v for k, v in seals.items() if isinstance(v, dict)}, "seeded": bool(data.get("seeded"))}


def save(state: dict) -> None:
    try:
        stats.STATS_DIR.mkdir(exist_ok=True)
        storage.write_json_atomic(_path(), state, indent=1, sort_keys=True)
    except OSError:
        pass


def seals_of(state: dict, key: str) -> dict:
    """{Stufe: Tag} der schon vergebenen Siegel eines Diploms."""
    out = {}
    for level, day in state["seals"].get(key, {}).items():
        try:
            out[int(level)] = date.fromisoformat(day)
        except (TypeError, ValueError):
            continue
    return out


def check(today: date = None, data: Data = None):
    """Neue Siegel eintragen. Rückgabe (neu, nachgetragen): `neu` ist eine
    Liste (Schlüssel, Stufe) für das Diplom-Fenster; beim allerersten Aufruf
    wird still nachgetragen und `nachgetragen` ist die Zahl der Diplome
    (sonst None)."""
    today = today or date.today()
    state = load()
    statuses = evaluate(data, today)
    first_time = not state["seeded"]
    new = []
    for award in AWARDS:
        have = seals_of(state, award.key)
        for level, day in enumerate(statuses[award.key].dates):
            if day is None or level in have:
                continue
            state["seals"].setdefault(award.key, {})[str(level)] = (day if first_time else today).isoformat()
            new.append((award.key, level))
    state["seeded"] = True
    if new or first_time:
        save(state)
    if first_time:
        return [], len({key for key, _ in new})
    return new, None


def level_name(award: Award, level: int) -> str:
    """Stufenname (deutsch, über tr() anzeigen); ohne Stufen leer."""
    return LEVEL_NAMES[level] if award.levels else ""
