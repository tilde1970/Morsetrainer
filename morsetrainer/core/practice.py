"""Übungszeit pro Tag, für Tagesziel und Serie ("12 Tage in Folge").

Gezählt wird die Zeit, in der irgendein Trainingsmodus läuft (zwischen
Start und Stop), gespeichert als {"2026-09-26": Sekunden, …} in
stats/practice.json. Die Gesamtstatistik zurückzusetzen lässt sie stehen."""
from datetime import date, timedelta

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
    stats.STATS_DIR.mkdir(exist_ok=True)
    try:
        storage.write_json_atomic(_path(), data, indent=1, sort_keys=True)
    except OSError:
        pass


def seconds_on(data: dict, day: date) -> float:
    return data.get(day.isoformat(), 0.0)


def streak(data: dict, goal_seconds: float, today: date) -> int:
    """Tage in Folge mit erreichtem Ziel (ohne Ziel: mit Übung überhaupt).
    Heute zählt mit, sobald das Ziel erreicht ist; vorher bleibt die Serie
    bis gestern bestehen."""
    threshold = max(goal_seconds, 1.0)
    day = today if seconds_on(data, today) >= threshold else today - timedelta(days=1)
    count = 0
    while seconds_on(data, day) >= threshold:
        count += 1
        day -= timedelta(days=1)
    return count
