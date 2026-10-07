"""Diplome: dauerhafte Erfolge wie bei DXCC oder WAC, in Stufen Bronze,
Silber, Gold und teils Platin (Konzept-Motivation.md, „Dauerhaft: Diplome“).

Ausgewertet wird immer alles, was schon gespeichert ist: Durchgänge,
Ergebnisse (stats.log_result), Lernkartei (höchstes je erreichtes Fach) und
Übungszeit je Tag. Vergeben wird nur aus Durchgängen ohne Selbstbewertung.
Was einmal erreicht ist, steht mit Datum in der Datenbank ("awards") und geht nie
verloren, auch nicht durch „Gesamtstatistik zurücksetzen“ (die
Durchgänge bleiben dabei ohnehin stehen).

Beim ersten Mal wird still nachgetragen, was sich aus dem bisherigen Üben
ergibt (mit dem Tag, an dem es erreicht wurde); danach gilt ein neues
Siegel ab dem Tag, an dem es auffällt.

Fächer der Lernkartei heißen hier wie in der Oberfläche 1–6 (`box` 0–5)."""
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from morsetrainer.i18n import N_
from morsetrainer.core import db, errorlog, koch, practice, review, stats, words

STATE_KEY = "awards"

LEVEL_NAMES = (N_("Bronze"), N_("Silber"), N_("Gold"), N_("Platin"))
SILVER = 1

# Fach 3, 4, 6 der Oberfläche als `box` der Lernkartei.
BOX_3, BOX_4, BOX_6 = 2, 3, 5

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
# Voller Koch-Zeichensatz ohne die Betriebszeichen (wie lcwo.net).
FULL_CHARSET = koch.LCWO_ORDER

MIN_CHAR_WPM = koch.SLOW_CHAR_WPM  # 18: darunter lassen sich Punkte und Striche zählen
FULL_RUN_S = 180                   # „voller 3-Min.-Lauf“
DAY_GOAL_S = 600                   # Ausdauer: Tage mit ≥ 10 Min. Übung
CLUB_MIN_S = 600                   # Clubabend: ≥ 10 Min. Netzwerk-Übung an einem Tag

Q_GROUPS = tuple(word for word in words.WORDS if len(word) == 3 and word.startswith("Q"))
CONTEST_KINDS = ("cqww", "wpx", "wag", "arrldx", "iaru")
RAGCHEW = "ragchew"
# Klartext im Reiter Kontinuierlich (ohne eigene Texte, siehe modes/content.py).
PLAIN_CONTENT = {"words", "phrases", "qso"}
FLOW_WORDS_MAX = 21.9  # mit Wörtern höchstens Silber (Gold: 22 WPM)


@dataclass(frozen=True)
class Award:
    """Beschreibung eines Diploms: Schlüssel, Name, Bedingung als Text, Schwellen
    je Stufe und wie der Fortschritt angezeigt wird (Felder siehe unten)."""
    key: str
    name: str
    condition: str
    targets: tuple          # Schwelle je Stufe; ohne Stufen genau eine
    unit: str = ""          # Einheit des Fortschritts („Buchstaben“, „WPM“ …)
    from_lesson: int = None
    levels: bool = True
    two_days: bool = False  # Silber und höher erst an zwei verschiedenen Tagen
    stepped: bool = False   # Stufen aus mehreren Bedingungen: Fortschritt ist die Stufe selbst
    steps: tuple = ()       # bei `stepped`: Bedingung je Stufe, zusätzlich zu `condition`
    together: bool = False  # nur gemeinsam mit anderen erreichbar: ohne Siegel am Ende der Übersicht
    unit_one: str = ""      # Einzahl der Einheit, wo eine Schwelle 1 ist („ab 1 Abend“)
    unit_dative: str = ""   # Dativ Mehrzahl, wo er abweicht („ab 5 Abenden“)

    def unit_for(self, amount, dative=False) -> str:
        """Einheit passend zur Menge, mit `dative` für „ab …“; noch
        unübersetzt (für tr())."""
        if amount == 1 and self.unit_one:
            return self.unit_one
        return self.unit_dative if dative and self.unit_dative else self.unit


AWARDS = (
    Award("koch", N_("Koch"), N_("Bestandener Aufstiegslauf (≥ 50 Zeichen, ≥ 90 % beim ersten Versuch, "
                                "Zeichen ≥ 18 WPM)"), (10, 25, koch.FINAL_LESSON), N_("Lektionen"), 1,
          two_days=True),
    Award("wal", N_("Worked All Letters"), N_("Fächer der Lernkartei, erreicht mit Zeichen ≥ 18 WPM"),
          (1, 2, 3), N_("Zeichen"), 1, stepped=True,
          steps=(N_("10 Buchstaben in Fach 3"), N_("alle 26 Buchstaben in Fach 3"),
                 N_("alle Buchstaben in Fach 6 und alle Ziffern in Fach 4"))),
    Award("flow", N_("Mitschreiben im Fluss"), N_("Am Stück mit Klartext ohne eigene Wörter, Zeichensatz "
                                                 "mindestens Lektion 15, voller 3-Min.-Lauf, ≥ 90 % abzüglich "
                                                 "überzähliger Tasten, Zeichen ≥ 18 WPM; Gold nur mit Wendungen "
                                                 "oder QSO"),
          (10, 15, 22), N_("WPM eff."), 15, two_days=True),
    Award("qrq", N_("QRQ"), N_("Am Stück mit Zufallsgruppen (≥ 5 Zeichen), voller Zeichensatz, ohne "
                               "Farnsworth, voller 3-Min.-Lauf, ≥ 90 % abzüglich überzähliger Tasten"),
          (20, 25, 30, 35), N_("WPM"), 40, two_days=True),
    Award("qrn", N_("QRN-fest"), N_("Gruppen oder Am Stück mit Zufallszeichen, ≥ 200 Zeichen, "
                                    "Bandbedingungen den ganzen Lauf an und nicht leichter gestellt, "
                                    "Störlautstärke ≥ 100 %, Zeichen ≥ 20 WPM, effektiv ≥ 12 WPM, bei Gruppen "
                                    "der rechtzeitige erste Versuch"),
          (1, 2, 3), "", 25, two_days=True, stepped=True,
          steps=(N_("Band leicht, ≥ 90 %"), N_("Band mittel, ≥ 90 %"), N_("Band stark, ≥ 85 %"))),
    Award("rufz", N_("Rufz"), N_("Voller Rufz-Durchgang mit 50 Rufzeichen, ohne Präfix-Filter, "
                                 "Zeichentempo beim Start ≥ 20 WPM"),
          (2000, 3500, 5500, 7500), N_("Punkte"), 27, unit_dative=N_("Punkten"), two_days=True),
    Award("contest", N_("Contest"), N_("Contest-Durchgang ≥ 10 Min."),
          (1, 2, 3), "", koch.FINAL_LESSON, two_days=True, stepped=True,
          steps=(N_("≥ 20 WPM, 10 QSOs in 10 Min., ≤ 10 % Fehler"),
                 N_("≥ 25 WPM, Aktivität ≥ 2, 20 QSOs in 10 Min., ≤ 5 % Fehler"),
                 N_("≥ 30 WPM, Aktivität ≥ 3, 25 QSOs in 10 Min., höchstens 1 Fehler"))),
    Award("wpx", N_("WPX"), N_("Verschiedene WPX-Präfixe, beim ersten Versuch richtig (Rufzeichen und "
                               "Contest, dort ohne Rückfrage nach dem Call), Zeichen ≥ 18 WPM"),
          (100, 400, 1200, 2000), N_("Präfixe"), 25, unit_dative=N_("Präfixen")),
    Award("headphones", N_("Kopfhörer"), N_("3 normale QSOs in Folge mit „Kopfhören + Fragen“, alle Fragen "
                                            "richtig, ohne „Nochmal“, Zeichen ≥ 18 WPM; Silber und Gold mit "
                                            "der Länge Normal oder Lang"), (15, 20, 25), N_("WPM eff."), koch.FINAL_LESSON),
    Award("confusion", N_("Verwechslung überwunden"), N_("Ein häufig verwechseltes Paar 28 Tage lang mit je "
                                                         "≥ 40 Versuchen höchstens einmal verwechselt"),
          (1, 3, 6), N_("Paare"), 5, unit_one=N_("Paar"), unit_dative=N_("Paaren")),
    Award("endurance", N_("Ausdauer"), N_("Tage mit ≥ 10 Min. Übung, nicht in Folge"),
          (10, 50, 150, 365), N_("Tage"), unit_dative=N_("Tagen")),
    Award("heard", N_("Zeichen gehört"), N_("Richtig erkannte Zufallszeichen, Zeichen ≥ 18 WPM"),
          (5000, 25000, 100000, 250000), N_("Zeichen")),
    Award("first_qso", N_("Erstes QSO verstanden"), N_("Normales QSO mit Abfrage, alles richtig, ohne "
                                                       "„Nochmal“, ≥ 15 WPM effektiv, Zeichen ≥ 18 WPM"), (1,),
          from_lesson=40, levels=False),
    Award("all_contests", N_("Worked All Contests"), N_("Alle 5 Contest-Arten mit je ≥ 30 QSOs und ≤ 10 % "
                                                        "Fehlern"), (5,), N_("Contests"), koch.FINAL_LESSON,
          levels=False),
    Award("club", N_("Clubabend"), N_("Tage mit zusammen ≥ 10 Min. Netzwerk-Übung, mitgemacht oder als "
                                      "Trainer geleitet"), (1, 5, 15, 40), N_("Abende"),
          unit_one=N_("Abend"), unit_dative=N_("Abenden"), together=True),
    Award("q_groups", N_("Q-Gruppen-Kenner"), N_("Jede der 20 Q-Gruppen 3× beim ersten Hören richtig, an "
                                                 "mindestens 2 Tagen, Zeichen ≥ 18 WPM"),
          (len(Q_GROUPS),), N_("Q-Gruppen"), 40, levels=False),
    Award("digits", N_("Alle Ziffern"), N_("Alle 10 Ziffern mindestens in Fach 3, erreicht mit Zeichen "
                                           "≥ 18 WPM"), (10,), N_("Ziffern"), 39, levels=False),
)
BY_KEY = {award.key: award for award in AWARDS}


# --- Daten ----------------------------------------------------------------------
@dataclass
class Session:
    """Ein gespeicherter Durchgang, aufbereitet für die Diplome: Tag, config und
    summary sowie die Ergebnisse je Zeichen und je Gruppe."""
    day: date
    config: dict
    summary: dict
    chars: list   # [(gesendet, getippt, richtig)]
    groups: list  # [(gesendet, getippt, erster Versuch richtig oder None)]


@dataclass
class Data:
    """Alles, was die Diplome auswerten: Durchgänge, Ergebnisse der Modi ohne
    Zeichenprotokoll (QSO, Contest, Rufz …), Lernkartei und Übungszeit."""
    sessions: list
    results: list   # Ergebnisse (stats.log_result) mit "day"
    review: dict
    practice: dict


# Abgeschlossene Durchgänge ändern sich nicht mehr: einmal gelesen, bleiben
# sie im Speicher (Schlüssel: db.generation und id des Durchgangs).
_session_cache = {}


def _make_session(config: dict, summary: dict, events: list):
    """Session aus config, summary und den Zeilen eines Durchgangs; None, wenn
    die Startzeit fehlt oder ungültig ist."""
    chars, groups = [], []
    for obj in events:
        kind = obj.get("type")
        if kind == "char":
            chars.append((_text(obj.get("char")), _text(obj.get("typed")), bool(obj.get("correct"))))
        elif kind == "group":
            first = obj.get("first")
            groups.append((_text(obj.get("sent")), _text(obj.get("typed")), first if isinstance(first, bool) else None))
    try:
        day = datetime.fromisoformat(config["start_time"]).date()
    except (KeyError, TypeError, ValueError):
        return None
    return Session(day, config, summary, chars, groups)


def _load_sessions() -> list:
    """Abgeschlossene Durchgänge ohne Selbstbewertung, nach Startzeit; die
    Zeilen werden nur für noch nicht gelesene Durchgänge geholt."""
    wanted = [s for s in db.sessions() if s.summary is not None and not s.config.get("self_assessed")]
    generation = db.generation
    missing = [s.id for s in wanted if (generation, s.id) not in _session_cache]
    events = db.events_by_session(missing) if missing else {}
    for s in wanted:
        if s.id in events:
            _session_cache[(generation, s.id)] = _make_session(s.config, s.summary, events[s.id])
    return [session for session in (_session_cache[(generation, s.id)] for s in wanted) if session]


def load_data() -> Data:
    """Liest alle Daten für die Diplome aus der Datenbank; Ergebnisse ohne
    gültige Zeit fallen weg, die übrigen sind nach Zeit sortiert."""
    sessions = _load_sessions()
    results = []
    for obj in db.results():
        try:
            results.append({**obj, "day": datetime.fromisoformat(obj["time"]).date()})
        except (KeyError, TypeError, ValueError):
            continue
    results.sort(key=lambda r: r["time"])
    return Data(sessions, results, review.load(), practice.load())


# --- Hilfen ------------------------------------------------------------------------
def _text(value) -> str:
    """Text aus einer Protokollzeile; alles andere (von Hand verändert,
    beschädigt) zählt als leer."""
    return value if isinstance(value, str) else ""


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
    """Stand eines Diploms: an welchem Tag welche Stufe erreicht wurde und wie
    nah die nächste ist."""
    dates: list           # Tag je Stufe oder None
    value: float          # aktueller Stand (bester Wert bzw. Summe; bei `stepped` die erreichte Stufe)
    progress: tuple = None  # (erreicht, nötig) zur nächsten Stufe, wenn sich das zählen lässt
    second_day: bool = False  # Schwelle der nächsten Stufe erreicht, fehlt nur der zweite Tag
    hint: tuple = None      # (Text mit Platzhaltern, Werte): wie nah man der nächsten Stufe ist

    @property
    def next_level(self):
        """Nächste offene Stufe oder None, wenn alles erreicht ist."""
        return next((level for level, day in enumerate(self.dates) if day is None), None)


def _status(award: Award, dates: list, value: float) -> Status:
    status = Status(dates, value)
    level = status.next_level
    if level is not None:
        target = award.targets[level]
        status.second_day = value >= target
        # Stufen aus mehreren Bedingungen und Diplome mit nur einem Schritt
        # haben keinen zählbaren Fortschritt.
        if not award.stepped and target > 1:
            status.progress = (min(value, target), target)
    return status


# --- Die einzelnen Diplome ---------------------------------------------------------
def _koch(data: Data) -> list:
    """Koch-Diplom: [(Tag, Lektion)] je bestandenem Aufstiegslauf (Gruppen oder
    Kontinuierlich mit Zufallszeichen, Zeichen ≥ MIN_CHAR_WPM)."""
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
    """Tag, an dem das für die Diplome zählende Fach erreicht wurde."""
    try:
        return date.fromisoformat(entry.get("award_day") or entry.get("best_day") or entry.get("day"))
    except (TypeError, ValueError):
        return fallback


def _wal(data: Data, today: date) -> list:
    reached = {ch: (review.award_box(e), _best_day(e, today)) for ch, e in data.review.items()}
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
    boxes = {ch: review.award_box(e) for ch, e in data.review.items()}
    letters3 = sum(boxes.get(ch, 0) >= BOX_3 for ch in LETTERS)
    if letters3 < 10:
        return letters3, 10
    if letters3 < len(LETTERS):
        return letters3, len(LETTERS)
    have = sum(boxes.get(ch, 0) >= BOX_6 for ch in LETTERS) + sum(boxes.get(ch, 0) >= BOX_4 for ch in DIGITS)
    return have, len(LETTERS) + len(DIGITS)


def _flow(data: Data) -> list:
    """Mitschreiben im Fluss: [(Tag, effektives WPM)] je voller Klartext-Lauf in
    Kontinuierlich mit mindestens 90 % sauber; mit Wörtern höchstens Silber."""
    events = []
    for s in data.sessions:
        c = s.config
        if (c.get("mode") == "continuous" and c.get("content") in PLAIN_CONTENT and _full_run(s)
                and not c.get("user_words") and _contains(c.get("charset"), koch.lesson_charset(15))
                and _char_wpm(c) >= MIN_CHAR_WPM and _clean_share(s.summary) >= 0.9):
            wpm = _effective_wpm(s)
            # Gold nur mit Wendungen oder QSO-Text: Die eingebauten Wörter sind
            # wenige und werden bei hohem Tempo eher wiedererkannt.
            if c.get("content") == "words":
                wpm = min(wpm, FLOW_WORDS_MAX)
            events.append((s.day, wpm))
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


def _qrn_runs(data: Data) -> list:
    """[(Tag, Band-Rang, Anteil)] der Läufe, die alle übrigen Bedingungen erfüllen."""
    runs = []
    for s in data.sessions:
        c, summary = s.config, s.summary
        mode, rank = c.get("mode"), BAND_RANK.get(_text(c.get("band")))
        if "band_min" in summary:
            # Die Bandbedingungen lassen sich mitten im Durchgang ändern: Es
            # zählt die schwächste Stufe darin (None: zwischendurch aus).
            rank = min(rank or 0, BAND_RANK.get(_text(summary.get("band_min")), 0)) or None
        if mode not in ("group", "continuous") or rank is None:
            continue
        if mode == "continuous" and c.get("content", "chars") != "chars":
            continue  # Klartext ist im Störnebel viel leichter (Zusammenhang); wie bei QRQ
        # Lautstärke der Störungen: der kleinste Wert im Durchgang. Fehlt er
        # (ältere Daten), gilt der beim Start, fehlt auch der, 100 %.
        gain = min(_num(c.get("band_gain"), 100), _num(summary.get("band_gain_min"), 100))
        if (gain < 100 or _num(summary.get("total")) < 200 or _char_wpm(c) < 20 or _effective_wpm(s) < 12
                or not _contains(c.get("charset"), koch.lesson_charset(25))):
            continue
        if mode == "continuous":
            share = _clean_share(summary)
        elif "first_try_total" in summary:
            # Wie beim Koch-Aufstieg nur der flüssige erste Versuch: kein
            # langes Überlegen, kein Wiederholen.
            share = _num(summary.get("first_try_correct")) / max(_num(summary.get("first_try_total")), 1)
        else:
            share = _num(summary.get("accuracy_pct")) / 100
        runs.append((s.day, rank, share))
    return runs


def _qrn_need(rank: int) -> float:
    return 0.85 if rank == 3 else 0.9


def _qrn(runs: list) -> list:
    return [(day, rank) for day, rank, share in runs if share >= _qrn_need(rank)]


BAND_NAMES = {1: N_("leicht"), 2: N_("mittel"), 3: N_("stark")}


def _qrn_hint(runs: list, level: int):
    rank = level + 1
    best = max(((share, r) for _, r, share in runs if r >= rank), default=None)
    if best is None:
        return (N_("Noch kein Lauf ab Band {band}, der die übrigen Bedingungen erfüllt"), {"band": BAND_NAMES[rank]})
    return (N_("Bester Lauf ab Band {band}: {share} % (nötig {need} %)"),
            {"band": BAND_NAMES[rank], "share": int(best[0] * 100), "need": round(_qrn_need(rank) * 100)})


def _rufz(data: Data) -> list:
    events = []
    for r in data.results:
        if r.get("mode") != "rufz" or _num(r.get("total")) < 50 or r.get("prefixes"):
            continue
        if r.get("start_wpm") is not None and _num(r["start_wpm"]) < 20:
            continue  # Einträge ohne Starttempo (ältere Daten) zählen
        events.append((r["day"], _num(r.get("score"))))
    return events


def contest_errors(r: dict) -> int:
    """Fehler eines Contest-Ergebnisses: falsche Rufzeichen (busted), nicht im
    Log der Gegenstation (nil) und falscher Austausch zusammen."""
    return int(sum(_num(r.get(kind)) for kind in ("busted", "nil", "exchange")))


CONTEST_LEVELS = ((20, 1, 10), (25, 2, 20), (30, 3, 25))  # (WPM, Aktivität, QSOs in 10 Min.) je Stufe


def _contest_runs(data: Data) -> list:
    """[(Tag, WPM, Aktivität, QSOs in 10 Min., Fehler, Fehleranteil)] der Durchgänge ≥ 10 Min."""
    runs = []
    for r in data.results:
        minutes = _num(r.get("minutes"))
        if r.get("mode") != "contest" or minutes < 10 or not _num(r.get("total")):
            continue
        wpm, activity = _num(r.get("wpm")), _num(r.get("activity"), 1)
        rate = _num(r.get("correct")) / minutes * 10  # richtige QSOs in 10 Minuten
        errors = contest_errors(r)
        runs.append((r["day"], wpm, activity, rate, errors, errors / _num(r["total"])))
    return runs


def _contest_ok(level: int, errors: int, share: float) -> bool:
    return (share <= 0.10, share <= 0.05, errors <= 1)[level]


def _contest(runs: list) -> list:
    events = []
    for day, wpm, activity, rate, errors, share in runs:
        level = 0
        for i, (min_wpm, min_activity, min_rate) in enumerate(CONTEST_LEVELS):
            if wpm >= min_wpm and activity >= min_activity and rate >= min_rate and _contest_ok(i, errors, share):
                level = i + 1
        if level:
            events.append((day, level))
    return events


def _contest_hint(runs: list, level: int):
    min_wpm, min_activity, min_rate = CONTEST_LEVELS[level]
    fitting = [run for run in runs if run[1] >= min_wpm and run[2] >= min_activity]
    if not fitting:
        return (N_("Noch kein Durchgang mit ≥ {wpm} WPM und Aktivität ≥ {activity}"),
                {"wpm": min_wpm, "activity": min_activity})
    # Am nächsten: erst ohne zu viele Fehler, dann die höchste Rate.
    _, _, _, rate, errors, share = max(fitting, key=lambda run: (_contest_ok(level, run[4], run[5]), run[3]))
    return (N_("Bester Durchgang mit ≥ {wpm} WPM: {rate} QSOs in 10 Min. (nötig {need}), {errors} Fehler "
               "({share} %)"),
            {"wpm": min_wpm, "rate": int(rate), "need": min_rate, "errors": errors, "share": round(share * 100)})


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
    """WPX: laufende Zahl verschiedener Präfixe [(Tag, Anzahl)], aus Rufzeichen
    beim ersten Versuch richtig und Contest-Calls ohne Rückfrage."""
    first_day = {}

    def add(call, day):
        prefix = wpx_prefix(call)
        if prefix and prefix not in first_day:
            first_day[prefix] = day

    for s in data.sessions:
        if s.config.get("mode") == "callsign" and _char_wpm(s.config) >= MIN_CHAR_WPM:
            for sent, typed, first in s.groups:
                # Ohne Angabe zum ersten Versuch (ältere Daten) zählt richtig getippt.
                if first or (first is None and sent == typed):
                    add(sent, s.day)
    for r in data.results:
        if r.get("mode") == "contest" and _num(r.get("wpm")) >= MIN_CHAR_WPM:
            # Nur Calls ohne Rückfrage (ältere Daten kennen den Unterschied nicht).
            for call in r.get("calls") or ():
                add(call, r["day"])
    return _cumulative((day, 1) for day in first_day.values())


def _qso_understood(r: dict) -> bool:
    """Alles richtig, ohne „Nochmal“ und mit Zeichen ≥ 18 WPM; Ergebnisse
    ohne gespeichertes Zeichentempo (ältere Daten) zählen ohne diese
    Bedingung."""
    if r.get("char_wpm") is not None and _num(r["char_wpm"]) < MIN_CHAR_WPM:
        return False
    return bool(_num(r.get("total"))) and r.get("correct") == r.get("total") and not r.get("replays")


def _headphones(data: Data) -> list:
    """Kopfhörer: [(Tag, WPM)] nach je drei verstandenen normalen QSOs in Folge
    (Kopfhören mit Fragen); das langsamste der drei zählt, mit kurzen QSOs
    höchstens Bronze."""
    events, run = [], []
    for r in data.results:
        if r.get("mode") != "qso_head" or r.get("kind") != RAGCHEW:
            continue
        if _qso_understood(r):
            run.append((_num(r.get("wpm")), r.get("length") == "Kurz"))
            if len(run) >= 3:
                wpm = min(w for w, _ in run[-3:])
                # Silber und Gold nur mit normaler oder langer Länge: Ein kurzes
                # QSO ist eher Merken als Kopfhören über längere Zeit.
                if any(short for _, short in run[-3:]):
                    wpm = min(wpm, BY_KEY["headphones"].targets[0])
                events.append((r["day"], wpm))
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


def _confusion_state(data: Data):
    """(überwunden [(Tag, 1)], offene Paare {Paar: letzter Problemtag},
    Versuche je Tag, Verwechslungen je Tag)."""
    attempts, confusions = _daily_char_counts(data)
    if not attempts:
        return [], {}, attempts, confusions
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
    overcome, open_pairs = [], {}
    for pair, marked in problem_days.items():
        last_problem = max(marked)
        open_pairs[pair] = last_problem
        # Frühestens 28 Tage nach dem letzten Tag als Problem, Fenster danach.
        for day in days:
            start = day - timedelta(days=CLEAN_DAYS - 1)
            if start <= last_problem:
                continue
            tries = _window_sum(attempts, start, day)
            conf = _window_sum(confusions, start, day).get(pair, 0)
            if all(tries.get(ch, 0) >= CLEAN_ATTEMPTS for ch in pair) and conf <= 1:
                overcome.append((day, 1))
                del open_pairs[pair]
                break
    return overcome, open_pairs, attempts, confusions


def _confusion_hint(state, today: date):
    """Hinweis für „Verwechslung überwunden“: das offene Paar, das dem Ziel am
    nächsten ist, als (Text mit Platzhaltern, Werte)."""
    _, open_pairs, attempts, confusions = state
    if not open_pairs:
        return (N_("Noch kein Paar unter deinen häufigsten Verwechslungen"), {})
    best = None
    for pair, last_problem in open_pairs.items():
        start = max(last_problem + timedelta(days=1), today - timedelta(days=CLEAN_DAYS - 1))
        tries = _window_sum(attempts, start, today)
        days_left = max(0, (last_problem + timedelta(days=CLEAN_DAYS) - today).days)
        fewest = min(tries.get(ch, 0) for ch in pair)
        candidate = (days_left, -min(fewest, CLEAN_ATTEMPTS), pair, fewest)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    days_left, _, pair, fewest = best
    return (N_("Nächstes Paar {pair}: noch {days} Tage ohne Verwechslung, {tries} / {need} Versuche je Zeichen"),
            {"pair": "/".join(sorted(pair)), "days": days_left, "tries": fewest, "need": CLEAN_ATTEMPTS})


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
    return _cumulative((s.day, sum(1 for _, _, ok in s.chars if ok)) for s in data.sessions
                       if _random_chars(s) and _char_wpm(s.config) >= MIN_CHAR_WPM)


def _first_qso(data: Data) -> list:
    return [(r["day"], 1) for r in data.results
            if r.get("mode") in ("qso_quiz", "qso_head") and r.get("kind") == RAGCHEW and _qso_understood(r)
            and _num(r.get("wpm")) >= 15]


def _all_contests(data: Data) -> list:
    first_day = {}
    for r in data.results:
        total = _num(r.get("total"))
        if (r.get("mode") == "contest" and r.get("contest") in CONTEST_KINDS and total >= 30
                and contest_errors(r) / total <= 0.10):
            first_day.setdefault(r["contest"], r["day"])
    return _cumulative((day, 1) for day in first_day.values())


def _club(data: Data) -> list:
    """Tage mit zusammen ≥ 10 Min. Netzwerk-Übung, mitgemacht oder geleitet.
    Protokolle ohne Dauer (ältere Daten): Der Tag zählt schon durch die
    Teilnahme."""
    seconds = {}
    for s in data.sessions:
        if s.config.get("mode") == "network":
            duration = s.summary.get("duration_s")
            seconds[s.day] = seconds.get(s.day, 0) + (_num(duration) if duration is not None else CLUB_MIN_S)
    for r in data.results:
        if r.get("mode") == "network":
            seconds[r["day"]] = seconds.get(r["day"], 0) + _num(r.get("duration_s"))
    return _cumulative((day, 1) for day, total in seconds.items() if total >= CLUB_MIN_S)


def _q_groups(data: Data) -> list:
    """Q-Gruppen-Kenner: laufende Zahl der Q-Gruppen [(Tag, Anzahl)], die je
    dreimal beim ersten Hören richtig waren, an mindestens zwei Tagen."""
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
                     if ch in DIGITS and review.award_box(e) >= BOX_3)
    return [(day, n) for n, day in enumerate(reached, 1)]


def evaluate(data: Data = None, today: date = None) -> dict:
    """Stand aller Diplome aus den gespeicherten Daten: {Schlüssel: Status}."""
    data = data or load_data()
    today = today or date.today()
    qrn_runs = _guarded("qrn", lambda: _qrn_runs(data), [])
    contest_runs = _guarded("contest", lambda: _contest_runs(data), [])
    confusion = _guarded("confusion", lambda: _confusion_state(data), None)
    checks = {
        "koch": lambda: _koch(data), "wal": lambda: _wal(data, today), "flow": lambda: _flow(data),
        "qrq": lambda: _qrq(data), "qrn": lambda: _qrn(qrn_runs), "rufz": lambda: _rufz(data),
        "contest": lambda: _contest(contest_runs), "wpx": lambda: _wpx(data),
        "headphones": lambda: _headphones(data),
        "confusion": lambda: _cumulative(confusion[0]) if confusion else [],
        "endurance": lambda: _endurance(data), "heard": lambda: _heard(data),
        "first_qso": lambda: _first_qso(data), "all_contests": lambda: _all_contests(data),
        "club": lambda: _club(data), "q_groups": lambda: _q_groups(data), "digits": lambda: _digits(data, today),
    }
    statuses = {}
    for award in AWARDS:
        found = _guarded(award.key, checks[award.key], [])
        value = max((v for _, v in found), default=0)
        statuses[award.key] = _status(award, level_dates(found, award.targets, award.two_days), value)
    if statuses["wal"].next_level is not None:
        statuses["wal"].progress = _guarded("wal", lambda: wal_progress(data), None)
    hints = {"qrn": lambda level: _qrn_hint(qrn_runs, level),
             "contest": lambda level: _contest_hint(contest_runs, level),
             "confusion": lambda level: _confusion_hint(confusion, today) if confusion else None}
    for key, hint in hints.items():
        status = statuses[key]
        if status.next_level is not None and not status.second_day:
            status.hint = _guarded(key, lambda: hint(status.next_level), None)
    return statuses


# Diplome, deren Auswertung schon einmal gescheitert ist (nur einmal ins
# Fehlerprotokoll je Programmlauf).
_failed = set()


def _guarded(key: str, compute, default):
    """`compute()`, oder `default`, wenn es an unerwarteten Daten scheitert
    (von Hand veränderte oder beschädigte Dateien): Dann fehlt nur dieses
    eine Diplom, die anderen und der Rest nach der Übung laufen weiter.
    Der Fehler kommt ins Fehlerprotokoll, damit er sich finden lässt."""
    try:
        return compute()
    except (TypeError, ValueError, KeyError, AttributeError, IndexError):
        if key not in _failed:
            _failed.add(key)
            errorlog.record(*sys.exc_info())
        return default


# --- Protokoll ---------------------------------------------------------------------
def load() -> dict:
    """Gespeicherter Stand der Siegel: {"seals": {Diplom: {Stufe: Tag}},
    "seeded": schon einmal nachgetragen}; Ungültiges fällt weg."""
    data = db.load_state(STATE_KEY, {})
    seals = data.get("seals") if isinstance(data.get("seals"), dict) else {}
    return {"seals": {k: v for k, v in seals.items() if isinstance(v, dict)}, "seeded": bool(data.get("seeded"))}


def save(state: dict) -> None:
    """Speichert den Stand der Siegel; scheitert das, bleibt es beim alten Stand
    ohne Fehlermeldung."""
    try:
        db.save_state(STATE_KEY, state)
    except (db.Error, OSError):
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


def overview(state: dict = None, statuses: dict = None) -> list:
    """[(Diplom, Status)] für die Übersicht. Die Tage der Siegel kommen aus
    dem Protokoll, wo es sie schon gibt; was noch nicht eingetragen ist,
    zeigt den Tag aus der Auswertung. Diplome, die nur gemeinsam mit
    anderen gehen (Clubabend), stehen ohne Siegel am Ende: Wer allein übt,
    hat sonst mitten in der Liste ein Ziel, das er allein nie erreicht."""
    state = state if state is not None else load()
    statuses = statuses if statuses is not None else evaluate()
    out = []
    for award in AWARDS:
        status = statuses[award.key]
        have = seals_of(state, award.key)
        merged = [have.get(level, day) for level, day in enumerate(status.dates)]
        if merged == status.dates:
            out.append((award, status))
            continue
        shown = _status(award, merged, status.value)
        if shown.next_level == status.next_level:
            shown.hint = status.hint
            if award.key == "wal":
                shown.progress = status.progress
        out.append((award, shown))
    return sorted(out, key=lambda row: row[0].together and not any(row[1].dates))


def level_name(award: Award, level: int) -> str:
    """Stufenname (deutsch, über tr() anzeigen); ohne Stufen leer."""
    return LEVEL_NAMES[level] if award.levels else ""
