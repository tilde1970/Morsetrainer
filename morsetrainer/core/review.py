"""Wiederholung über Tage (Lernkartei nach Leitner).

Jedes Zeichen liegt in einem Fach; das Fach bestimmt, nach wie vielen
Tagen es wieder dran ist (INTERVALS). Wer ein fälliges Zeichen sicher
erkennt, schiebt es ein Fach weiter; wer es unsicher erkennt, schiebt es
zurück (deutlich unsicher: ins erste Fach, morgen wieder). Knapp unter
der Schwelle (NEUTRAL_SHARE bis SURE_SHARE) bleibt es, wo es ist. So kommt ein
Zeichen kurz vor dem Vergessen wieder – öfter, solange es wackelt,
seltener, sobald es sitzt.

Ehrliche Grundlage:
- Die Versuche eines Tages werden je Zeichen gesammelt; entschieden wird
  einmal am Tag, sobald MIN_ATTEMPTS Versuche beisammen sind.
- Flüssig ist ein Treffer nur ohne Wiederholen und rechtzeitig: nicht
  angenommen (siehe stats.record_char) und, wo gemessen, mit höchstens
  FLUENT_LATENCY_S Latenz.
- Hochstufen nur aus Zufallszeichen (Einzelzeichen, Gruppen, Kontinuierlich
  mit Zufallszeichen) mit mindestens PROMOTE_MIN_CHARSET Zeichen im Satz:
  In Wörtern, Klartext oder QSOs verrät der Zusammenhang viele Zeichen, und
  unter wenigen Zeichen ist Raten leicht. Solche Sitzungen können Zeichen
  nur zurückstufen.

Fällige Zeichen bekommen in der Gewichtung den Faktor DUE_FACTOR, beim
gezielten Üben FOCUS_FACTOR (core/weighting.py).
Gespeichert in der Datenbank unter "review": {Zeichen: {"box", "due", "day", Zähler,
"best_box", "best_day"}}. "best_box" ist das höchste je erreichte Fach (für
Fortschritt und Diplome: ein späteres Zurückstufen nimmt es nicht weg);
Einträge ohne das Feld (ältere Daten) gelten mit ihrem aktuellen Fach.
"award_box" und "award_day" ebenso, aber nur aus Sitzungen mit
Zeichentempo ab koch.SLOW_CHAR_WPM: Diese Fächer zählen für die Diplome,
weil sich langsamere Zeichen mitzählen lassen. Einträge ohne diese Felder
übernehmen beim ersten Entscheiden ihr "best_box".
"s", "d" und "last" sind das Schattenmodell (core/fsrs_shadow.py): Stabilität,
Schwierigkeit und Tag der letzten Entscheidung. Sie werden nur mitgeschrieben
und haben keine Wirkung. Jede Entscheidung steht außerdem im Protokoll
LOG_KEY (Zeichen, Tag, Bewertung, Anteil, Versuche, Tage seit der letzten
Entscheidung, vorhergesagte Behaltenswahrscheinlichkeit "p", Fach davor
und danach), höchstens LOG_MAX Einträge; zum späteren Vergleich von
Vorhersage und Fach."""
from datetime import date, timedelta

from morsetrainer.core import db, fsrs_shadow
from morsetrainer.core.morse import MORSE_CODE

INTERVALS = (1, 2, 4, 8, 16, 32)  # Tage bis zur nächsten Wiederholung je Fach
MIN_ATTEMPTS = 8    # unter so vielen Versuchen am Tag entscheidet die Lernkartei nicht
SURE_SHARE = 0.9    # ab diesem Anteil flüssiger Treffer: sicher
NEUTRAL_SHARE = 0.8  # zwischen hier und SURE_SHARE bleibt ein Zeichen, wo es ist
SHAKY_SHARE = 0.75  # darunter: zurück ins erste Fach, sonst ein Fach zurück
FLUENT_LATENCY_S = 1.5
PROMOTE_MIN_CHARSET = 8
DUE_FACTOR = 2.0
FOCUS_FACTOR = 4.0

# Beim gezielten Üben („Fällige gezielt üben“) die fälligen Zeichen; die
# App leert die Menge, wenn der Durchgang endet.
focus = set()


STATE_KEY = "review"
LOG_KEY = "review_log"
LOG_MAX = 20000  # älteste Einträge fallen heraus
MAX_ELAPSED_DAYS = 3650  # längere Pausen (oder kaputte Daten) zählt das Schattenmodell als zehn Jahre


# Zahlenfelder eines Eintrags: Fächer und die Zähler des Tages ("day").
BOX_FIELDS = ("box", "best_box", "award_box")
DAY_FIELDS = ("n", "fluent", "pn", "pfluent")
SHADOW_FIELDS = ("s", "d", "last")


def load() -> dict:
    """Lernkartei aus der Datenbank: {Zeichen: Eintrag}, jeder Eintrag bereinigt
    (fehlende oder ungültige Zähler auf null)."""
    data = db.load_state(STATE_KEY, {})
    return {ch: _clean(e) for ch, e in data.items() if isinstance(e, dict)}


def _clean(entry: dict) -> dict:
    """Eintrag mit falsch typisierten Feldern (von Hand verändert,
    beschädigt) brauchbar machen: ein unlesbares Fach gilt als erstes Fach,
    unlesbare Tageszähler beginnen neu."""
    for key in BOX_FIELDS:
        if key in entry and not _is_int(entry[key]):
            entry[key] = 0
    shadow = [entry.get(key) for key in SHADOW_FIELDS]
    if any(key in entry for key in SHADOW_FIELDS) and not _shadow_ok(*shadow):
        for key in SHADOW_FIELDS:
            entry.pop(key, None)
    if "day" in entry and not (all(_is_int(entry.get(key)) for key in DAY_FIELDS)
                               and isinstance(entry.get("decided"), bool)):
        del entry["day"]
    return entry


def _shadow_ok(stability, difficulty, last) -> bool:
    """Sind die Felder des Schattenmodells alle da und brauchbar?"""
    try:
        date.fromisoformat(last)
    except (TypeError, ValueError):
        return False
    return all(isinstance(v, float) and 0 < v < 1e6 for v in (stability, difficulty))


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _save(data: dict) -> bool:
    """Speichert die Lernkartei; False, wenn das nicht ging."""
    try:
        db.save_state(STATE_KEY, data)
    except (db.Error, OSError):
        return False
    return True


def _due_date(entry) -> date:
    try:
        return date.fromisoformat(entry["due"])
    except (KeyError, TypeError, ValueError):
        return date.min  # kaputter Eintrag: gleich wieder fällig


def is_due(entry, today=None) -> bool:
    """Ist das Zeichen mit `entry` an `today` (Standard: heute) zur Wiederholung
    fällig?"""
    return _due_date(entry) <= (today or date.today())


def fluent_count(e: dict) -> int:
    """Flüssige Treffer eines Zeichens aus SessionStats.per_char."""
    latencies = e.get("latencies", [])
    assumed = e.get("assumed_latencies", [])
    slow = sum(1 for lat in latencies if lat > FLUENT_LATENCY_S)
    slow += sum(1 for lat in assumed if lat <= FLUENT_LATENCY_S)  # angenommen ist nie flüssig
    # Richtige ohne Zeit (F11-Ansage ohne Zeitlimit) sind weder flüssig noch langsam.
    return max(e["good"] - e.get("untimed", 0) - slow, 0)


def can_promote(charset: str) -> bool:
    """Darf ein Durchgang mit `charset` Zeichen hochstufen? Erst ab
    PROMOTE_MIN_CHARSET verschiedenen Zeichen, darunter ist die Antwort zu oft
    zu erraten."""
    return len({ch for ch in charset.upper() if ch in MORSE_CODE}) >= PROMOTE_MIN_CHARSET


def best_box(entry: dict) -> int:
    """Höchstes je erreichtes Fach eines Eintrags (0 = erstes Fach)."""
    return max(int(entry.get("best_box", 0)), int(entry.get("box", 0)))


def award_box(entry: dict) -> int:
    """Höchstes Fach, das für die Diplome zählt (siehe Modultext)."""
    return int(entry["award_box"]) if "award_box" in entry else best_box(entry)


def load_log() -> list:
    """Protokoll der Entscheidungen (siehe Modultext), leer bei Fehlern."""
    try:
        data = db.load_state(LOG_KEY, [])
    except (db.Error, OSError):
        return []
    return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []


def _save_log(new: list) -> None:
    """Hängt `new` an das Protokoll an."""
    if not new:
        return
    try:
        db.save_state(LOG_KEY, (load_log() + new)[-LOG_MAX:])
    except (db.Error, OSError):
        pass


def update(per_char: dict, promote: bool = False, today=None, events=None, fast: bool = True) -> dict:
    """Übernimmt die Ergebnisse einer Sitzung (SessionStats.per_char).
    `promote`: Die Sitzung darf Zeichen hochstufen (siehe Modultext).
    `fast`: Zeichentempo ab koch.SLOW_CHAR_WPM; nur dann zählt ein neues
    Fach auch für die Diplome ("award_box").
    `events`: Liste, an die jede Hochstufung als {"char", "box", "first"}
    angehängt wird; "first": das Fach ist für dieses Zeichen neu."""
    today = today or date.today()
    day = today.isoformat()
    data = load()
    log = []
    for char, e in per_char.items():
        attempts = e["good"] + e["wrong"] - e.get("untimed", 0)  # ohne Zeit: zählt hier nicht
        if attempts <= 0:
            continue
        entry = data.setdefault(char, {})
        if entry.get("day") != day:
            entry.update(day=day, n=0, fluent=0, pn=0, pfluent=0, decided=False)
        fluent = fluent_count(e)
        entry["n"] += attempts
        entry["fluent"] += fluent
        if promote:
            entry["pn"] += attempts
            entry["pfluent"] += fluent
        _decide(char, entry, today, events, fast, log)
    if _save(data):  # sonst stünde die Entscheidung im Protokoll, aber nicht in der Lernkartei
        _save_log(log)
    return data


def _decide(char: str, entry: dict, today: date, events=None, fast: bool = True, log=None) -> None:
    """Höchstens eine Entscheidung je Zeichen und Tag; `log`: Liste für das Protokoll."""
    if entry["decided"] or entry["n"] < MIN_ATTEMPTS:
        return
    share = entry["fluent"] / entry["n"]
    old_box = box = int(entry.get("box", 0))
    old_best = best_box(entry)
    if "award_box" not in entry:
        entry["award_box"] = old_best
        if "best_day" in entry:
            entry["award_day"] = entry["best_day"]
    if share < SURE_SHARE:
        # Das Zeitlimit der Übung pendelt sich bei rund 88 % rechtzeitiger Antworten ein: Knapp
        # unter der Schwelle ist kein Grund zurückzustufen, mehr Versuche entscheiden später.
        if share >= NEUTRAL_SHARE and "due" in entry:
            return
        box = 0 if share < SHAKY_SHARE else max(box - 1, 0)
    elif "due" not in entry:
        box = 0  # neu und gleich sicher: morgen die erste Wiederholung
    elif is_due(entry, today) and entry["pn"] >= MIN_ATTEMPTS and entry["pfluent"] / entry["pn"] >= SURE_SHARE:
        box = min(box + 1, len(INTERVALS) - 1)
    else:
        return  # sicher, aber nicht fällig oder nur aus Klartext: Termin bleibt, später am Tag noch möglich
    shadow = _shadow(entry, share, old_box, today)
    if log is not None and shadow is not None:
        log.append({"c": char, "day": today.isoformat(), "r": shadow["rating"], "share": round(share, 3),
                    "n": entry["n"], "t": shadow["elapsed"], "p": shadow["p"], "from": old_box, "to": box})
    entry.update(box=box, due=(today + timedelta(days=INTERVALS[box])).isoformat(), decided=True)
    if box > old_best:
        entry.update(best_box=box, best_day=today.isoformat())
    elif "best_box" not in entry:
        entry["best_box"] = old_best
    if fast and box > entry["award_box"]:
        entry.update(award_box=box, award_day=today.isoformat())
    if box > old_box and events is not None:
        events.append({"char": char, "box": box, "first": box > old_best})


def _shadow(entry: dict, share: float, old_box: int, today: date):
    """Schattenmodell fortschreiben (siehe Modultext); vor dem Setzen des neuen
    Fachs und Termins aufrufen, `old_box` ist das Fach davor. Gibt Bewertung,
    Tage seit der letzten Entscheidung und vorhergesagte Behaltenswahrscheinlichkeit
    zurück ({"rating", "elapsed", "p"}; die beiden letzten None bei einem neuen
    Zeichen), bei Fehlern None."""
    rating = (fsrs_shadow.AGAIN if share < SHAKY_SHARE
              else fsrs_shadow.HARD if share < SURE_SHARE else fsrs_shadow.GOOD)
    try:
        elapsed = predicted = None
        if "due" not in entry:  # neues Zeichen
            stability, difficulty = fsrs_shadow.first(rating)
        else:
            if _shadow_ok(*(entry.get(key) for key in SHADOW_FIELDS)):
                stability, difficulty = entry["s"], entry["d"]
                elapsed = (today - date.fromisoformat(entry["last"])).days
            else:  # Eintrag aus der Zeit vor dem Schattenmodell: aus dem Fach schätzen
                stability, difficulty = float(INTERVALS[old_box]), 5.0
                try:
                    late = (today - date.fromisoformat(entry["due"])).days
                except (KeyError, TypeError, ValueError):
                    late = 0  # kaputter Termin: nicht als uralt zählen
                elapsed = INTERVALS[old_box] + late
            elapsed = min(max(elapsed, 1), MAX_ELAPSED_DAYS)
            predicted = round(fsrs_shadow.retrievability(elapsed, stability), 4)
            stability, difficulty = fsrs_shadow.review(stability, difficulty, elapsed, rating)
    except (ArithmeticError, ValueError, TypeError, KeyError, IndexError):
        for key in SHADOW_FIELDS:
            entry.pop(key, None)
        return None
    entry.update(s=float(stability), d=float(difficulty), last=today.isoformat())
    return {"rating": rating, "elapsed": elapsed, "p": predicted}


def boxed_chars(data=None) -> str:
    """Zeichen, die schon in einem Fach liegen (also wiederholt werden)."""
    data = load() if data is None else data
    return "".join(ch for ch, e in data.items() if "due" in e)


def by_box(data=None) -> list:
    """Zeichen je Fach (Index wie "box", 0 = Fach 1), in jedem Fach erst die
    Buchstaben, dann Ziffern, dann die übrigen, jeweils sortiert."""
    data = load() if data is None else data
    boxes = [[] for _ in INTERVALS]
    for ch, e in data.items():
        if "due" in e:
            boxes[min(max(e.get("box", 0), 0), len(INTERVALS) - 1)].append(ch)
    return ["".join(sorted(chars, key=lambda ch: (not ch.isalpha(), not ch.isdigit(), ch))) for chars in boxes]


def due_chars(data=None, today=None, known=None) -> str:
    """Heute fällige Zeichen, zuerst die aus den unteren Fächern.
    `known`: nur diese Zeichen (z. B. der aktuelle Zeichensatz)."""
    data = load() if data is None else data
    due = [(int(e.get("box", 0)), ch) for ch, e in data.items()
           if "due" in e and is_due(e, today) and (known is None or ch in known)]
    return "".join(ch for _, ch in sorted(due))


def next_due(data=None, today=None):
    """(Datum, Zeichen) der nächsten Fälligkeit nach heute, oder None."""
    data = load() if data is None else data
    today = today or date.today()
    upcoming = sorted((_due_date(e), ch) for ch, e in data.items() if "due" in e and _due_date(e) > today)
    if not upcoming:
        return None
    first = upcoming[0][0]
    return first, "".join(ch for day, ch in upcoming if day == first)


def reset() -> None:
    """Lernkartei löschen (alle Zeichen wieder neu); Fehler beim Löschen werden
    übergangen."""
    try:
        db.delete_state(STATE_KEY)
        db.delete_state(LOG_KEY)
    except (db.Error, OSError):
        pass
