"""Übungszeit pro Tag, für das Tagesziel in der Fußzeile und frei geübte
Tage im Wochenstreifen (core/week.py).

Gezählt wird die Zeit, in der irgendein Trainingsmodus läuft (zwischen
Start und Stop), gespeichert als {"2026-09-26": Sekunden, …} in
stats/practice.json. Die Gesamtstatistik zurückzusetzen lässt sie stehen."""
from datetime import date

from morsetrainer.core import stats, storage

PRACTICE_FILE_NAME = "practice.json"


def _path():
    return stats.STATS_DIR / PRACTICE_FILE_NAME


def load() -> dict:
    data = storage.load_json(_path(), {})
    return {k: float(v) for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def add(seconds: float, day: date = None) -> None:
    if seconds <= 0:
        return
    data = load()
    key = (day or date.today()).isoformat()
    data[key] = round(data.get(key, 0.0) + seconds, 1)
    try:
        stats.STATS_DIR.mkdir(exist_ok=True)
        storage.write_json_atomic(_path(), data, indent=1, sort_keys=True)
    except OSError:
        pass


def seconds_on(data: dict, day: date) -> float:
    return data.get(day.isoformat(), 0.0)

