"""Lebenslinie: der lange Weg auf einen Blick, Tag für Tag vom ersten
Üben bis heute (Konzept-Motivation.md, „Dauerhaft: Diplome“).

Drei Linien, die nur steigen oder stehen bleiben – Rückschritte zeigen
schon der Fortschritt im Statistik-Reiter und der Wochenrückblick:
- Sterne gesamt aus der Tagesübung (core/daily.py), aufsummiert.
- Koch-Lektion: die höchste bis dahin geübte (nicht bestandene: wer mit
  Lektion 40 einsteigt, soll nicht monatelang bei null stehen), aus den
  gespeicherten Durchgängen und der Tagesübung. Die Betriebszeichen-Lektionen 42–45
  sind freiwillig; die Linie endet bei der Abschlusslektion 41. „Koch
  geschafft“ heißt dagegen bestanden: der Tag des Gold-Siegels im
  Koch-Diplom ("koch_done"), nicht schon ein Durchgang in Lektion 41.
- Tagestempo (effektiv) der Tagesübung; gilt bis zum nächsten Wechsel
  weiter, auch an Tagen ohne Tagesübung.
Dazu die Siegel der Diplome an ihrem Tag.

Alle Quellen bleiben beim Zurücksetzen der Gesamtstatistik stehen."""
from datetime import date, timedelta

from morsetrainer.core import awards, daily, koch, practice

# Stufe des Koch-Diploms für die Abschlusslektion (Gold: Lektion 41 bestanden).
KOCH_DONE_LEVEL = next(a for a in awards.AWARDS if a.key == "koch").targets.index(koch.FINAL_LESSON)


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _day(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def session_lesson(config: dict):
    """Koch-Lektion einer Sitzung; ältere Sitzungen ohne „lesson“ am
    Zeichensatz erkannt. None, wenn die Zeichen keiner Lektion entsprechen."""
    lesson = _int(config.get("lesson"))
    if lesson is None and isinstance(config.get("charset"), str):
        lesson = koch.lesson_of(config["charset"])
    if lesson is None or lesson < 1:
        return None
    return min(lesson, koch.FINAL_LESSON)


def build(state: dict, sessions: list, awards_state: dict, practice_data: dict, today: date) -> dict:
    """{"days": [Tag …], "stars": [Summe …], "lesson": [Lektion oder None …],
    "tempo": [WPM oder None …], "seals": {Tag: [(Schlüssel, Stufe)]},
    "koch_done": Tag des bestandenen Laufs in Lektion 41 oder None};
    leer ({"days": []}), solange noch nichts geübt wurde."""
    daily_days = {}
    for key, entry in (state.get("days") or {}).items():
        day = _day(key)
        if day and isinstance(entry, dict):
            daily_days[day] = entry
    seals = {}
    for award in awards.AWARDS:
        for level, day in sorted(awards.seals_of(awards_state, award.key).items()):
            seals.setdefault(day, []).append((award.key, level))
    lessons = {}
    for session in sessions:
        lesson = session_lesson(session.config)
        if lesson:
            lessons[session.day] = max(lessons.get(session.day, 0), lesson)
    for day, entry in daily_days.items():
        lesson = _int(entry.get("lesson"))
        if lesson and lesson >= 1:
            lessons[day] = max(lessons.get(day, 0), min(lesson, koch.FINAL_LESSON))

    known = [d for d in (*daily_days, *seals, *lessons, *filter(None, map(_day, practice_data))) if d <= today]
    if not known:
        return {"days": [], "stars": [], "lesson": [], "tempo": [], "seals": {}, "koch_done": None}
    koch_done = awards.seals_of(awards_state, "koch").get(KOCH_DONE_LEVEL)
    out = {"days": [], "stars": [], "lesson": [], "tempo": [], "seals": seals, "koch_done": koch_done}
    stars, lesson, tempo = 0, None, None
    day = min(known)
    while day <= today:
        entry = daily_days.get(day, {})
        stars += len(daily.stars_on(state, day))
        if day in lessons:
            lesson = max(lesson or 0, lessons[day])
        tempo = _int(entry.get("tempo")) or tempo
        out["days"].append(day)
        out["stars"].append(stars)
        out["lesson"].append(lesson)
        out["tempo"].append(tempo)
        day += timedelta(days=1)
    return out


def load(today: date = None) -> dict:
    """Lebenslinie aus allen gespeicherten Daten bis `today` (Standard: heute),
    fertig für die Anzeige; siehe build()."""
    return build(daily.load(), awards.load_data().sessions, awards.load(), practice.load(), today or date.today())
