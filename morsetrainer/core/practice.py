"""Übungszeit pro Tag, für das Tagesziel in der Fußzeile und frei geübte
Tage im Wochenstreifen (core/week.py).

Gezählt wird die Zeit, in der irgendein Trainingsmodus läuft (zwischen
Start und Stop), gespeichert als {"2026-09-26": Sekunden, …} in
der Datenbank unter "practice". Die Gesamtstatistik zurückzusetzen lässt sie stehen."""
from datetime import date

from morsetrainer.core import db

STATE_KEY = "practice"


def load() -> dict:
    """Übungszeit je Tag aus der Datenbank: {"JJJJ-MM-TT": Sekunden}.
    Ungültige Einträge fallen weg."""
    data = db.load_state(STATE_KEY, {})
    return {k: float(v) for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def add(seconds: float, day: date = None) -> None:
    """Zählt `seconds` zur Übungszeit von `day` (Standard: heute) hinzu.
    Scheitert das Speichern, geht die Übung ohne Fehlermeldung weiter."""
    if seconds <= 0:
        return
    data = load()
    key = (day or date.today()).isoformat()
    data[key] = round(data.get(key, 0.0) + seconds, 1)
    try:
        db.save_state(STATE_KEY, data)
    except (db.Error, OSError):
        pass


def seconds_on(data: dict, day: date) -> float:
    """Übungszeit in Sekunden an `day` aus den Daten von load()."""
    return data.get(day.isoformat(), 0.0)

