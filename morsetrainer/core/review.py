"""Wiederholung über Tage (Lernkartei nach Leitner).

Jedes Zeichen liegt in einem Fach; das Fach bestimmt, nach wie vielen
Tagen es wieder dran ist (INTERVALS). Wer ein fälliges Zeichen sicher
erkennt, schiebt es ein Fach weiter; wer es unsicher erkennt, schiebt es
zurück (deutlich unsicher: ins erste Fach, morgen wieder). So kommt ein
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
Gespeichert in stats/review.json: {Zeichen: {"box", "due", "day", Zähler,
"best_box", "best_day"}}. "best_box" ist das höchste je erreichte Fach (für
Fortschritt und Diplome: ein späteres Zurückstufen nimmt es nicht weg);
ältere Einträge ohne das Feld gelten mit ihrem aktuellen Fach."""
from datetime import date, timedelta

from morsetrainer.core import stats, storage
from morsetrainer.core.morse import MORSE_CODE

INTERVALS = (1, 2, 4, 8, 16, 32)  # Tage bis zur nächsten Wiederholung je Fach
MIN_ATTEMPTS = 5
SURE_SHARE = 0.9    # ab diesem Anteil flüssiger Treffer: sicher
SHAKY_SHARE = 0.75  # darunter: zurück ins erste Fach, sonst ein Fach zurück
FLUENT_LATENCY_S = 1.5
PROMOTE_MIN_CHARSET = 8
DUE_FACTOR = 2.0
FOCUS_FACTOR = 4.0

# Beim gezielten Üben („Fällige gezielt üben“) die fälligen Zeichen; die
# App leert die Menge, wenn der Durchgang endet.
focus = set()


def _path():
    return stats.STATS_DIR / "review.json"


def load() -> dict:
    data = storage.load_json(_path(), {})
    if not isinstance(data, dict):
        return {}
    return {ch: e for ch, e in data.items() if isinstance(e, dict)}


def _save(data: dict) -> None:
    try:
        stats.STATS_DIR.mkdir(exist_ok=True)
        storage.write_json_atomic(_path(), data, indent=1)
    except OSError:
        pass


def _due_date(entry) -> date:
    try:
        return date.fromisoformat(entry["due"])
    except (KeyError, TypeError, ValueError):
        return date.min  # kaputter Eintrag: gleich wieder fällig


def is_due(entry, today=None) -> bool:
    return _due_date(entry) <= (today or date.today())


def fluent_count(e: dict) -> int:
    """Flüssige Treffer eines Zeichens aus SessionStats.per_char."""
    latencies = e.get("latencies", [])
    assumed = e.get("assumed_latencies", [])
    slow = sum(1 for lat in latencies if lat > FLUENT_LATENCY_S)
    slow += sum(1 for lat in assumed if lat <= FLUENT_LATENCY_S)  # angenommen ist nie flüssig
    return max(e["good"] - slow, 0)


def can_promote(charset: str) -> bool:
    return len({ch for ch in charset.upper() if ch in MORSE_CODE}) >= PROMOTE_MIN_CHARSET


def best_box(entry: dict) -> int:
    """Höchstes je erreichtes Fach eines Eintrags (0 = erstes Fach)."""
    return max(int(entry.get("best_box", 0)), int(entry.get("box", 0)))


def update(per_char: dict, promote: bool = False, today=None, events=None) -> dict:
    """Übernimmt die Ergebnisse einer Sitzung (SessionStats.per_char).
    `promote`: Die Sitzung darf Zeichen hochstufen (siehe Modultext).
    `events`: Liste, an die jede Hochstufung als {"char", "box", "first"}
    angehängt wird; "first": das Fach ist für dieses Zeichen neu."""
    today = today or date.today()
    day = today.isoformat()
    data = load()
    for char, e in per_char.items():
        attempts = e["good"] + e["wrong"]
        if not attempts:
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
        _decide(char, entry, today, events)
    _save(data)
    return data


def _decide(char: str, entry: dict, today: date, events=None) -> None:
    """Höchstens eine Entscheidung je Zeichen und Tag."""
    if entry["decided"] or entry["n"] < MIN_ATTEMPTS:
        return
    share = entry["fluent"] / entry["n"]
    old_box = box = int(entry.get("box", 0))
    old_best = best_box(entry)
    if share < SURE_SHARE:
        box = 0 if share < SHAKY_SHARE else max(box - 1, 0)
    elif "due" not in entry:
        box = 0  # neu und gleich sicher: morgen die erste Wiederholung
    elif is_due(entry, today) and entry["pn"] >= MIN_ATTEMPTS and entry["pfluent"] / entry["pn"] >= SURE_SHARE:
        box = min(box + 1, len(INTERVALS) - 1)
    else:
        return  # sicher, aber nicht fällig oder nur aus Klartext: Termin bleibt, später am Tag noch möglich
    entry.update(box=box, due=(today + timedelta(days=INTERVALS[box])).isoformat(), decided=True)
    if box > old_best:
        entry.update(best_box=box, best_day=today.isoformat())
    elif "best_box" not in entry:
        entry["best_box"] = old_best
    if box > old_box and events is not None:
        events.append({"char": char, "box": box, "first": box > old_best})


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
    try:
        _path().unlink(missing_ok=True)
    except OSError:
        pass
