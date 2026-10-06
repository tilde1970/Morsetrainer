"""Woche der Tagesübung: Wochenstreifen, Wochenziel, Wochenrückblick.

Ersetzt die Serie „X Tage in Folge“: Die fiel nach einem ausgelassenen Tag
auf null, und jeder kurze Tag zählte als Fehlschlag. Die Woche beginnt am
Montag; das Wochenziel (WEEK_GOAL Sterne) ist mit vier bis fünf
Übungstagen erreichbar, ein ausgelassener Tag kostet nicht die Woche.

Sterne gibt es nur aus der Tagesübung (core/daily.py). Freies Üben, das das
Tagesziel erreicht (core/practice.py), erscheint im Streifen als ✓, bringt
aber keine Sterne. Nur Daten, die Darstellung steht in
widgets/daily_panel.py."""
from datetime import date, timedelta

from morsetrainer.core import daily

WEEK_GOAL = 12

# Zustand eines Tages im Streifen.
FUTURE, NONE, PRACTICED = "future", "none", "practiced"


def monday(day: date) -> date:
    """Der Montag der Woche, in der `day` liegt."""
    return day - timedelta(days=day.weekday())


def _practiced(practice_data: dict, day: date, goal_seconds: float) -> bool:
    """Tagesziel erreicht (ohne Ziel: überhaupt geübt)."""
    return practice_data.get(day.isoformat(), 0.0) >= max(goal_seconds, 1.0)


def strip(state: dict, practice_data: dict, goal_seconds: float, today: date) -> list:
    """Sieben Tage ab Montag: [{"day", "stars": Anzahl, "status"}]; `status`
    FUTURE (nach heute), PRACTICED (ohne Sterne, aber Tagesziel erreicht),
    NONE (sonst; bei Sternen ohne Bedeutung)."""
    first = monday(today)
    days = []
    for offset in range(7):
        day = first + timedelta(days=offset)
        stars = len(daily.stars_on(state, day))
        if day > today:
            status = FUTURE
        elif not stars and _practiced(practice_data, day, goal_seconds):
            status = PRACTICED
        else:
            status = NONE
        days.append({"day": day, "stars": stars, "status": status})
    return days


def stars_in_week(state: dict, any_day: date) -> int:
    """Sterne der Tagesübung in der Woche (Montag bis Sonntag), in der
    `any_day` liegt."""
    first = monday(any_day)
    return sum(len(daily.stars_on(state, first + timedelta(days=offset))) for offset in range(7))


def _daily_days(state: dict, first: date) -> list:
    """Tageseinträge der Woche ab `first`, an denen eine Tagesübung lief."""
    entries = []
    for offset in range(7):
        entry = state.get("days", {}).get((first + timedelta(days=offset)).isoformat())
        if isinstance(entry, dict) and entry.get("blocks"):
            entries.append(entry)
    return entries


def last_week_review(state: dict, practice_data: dict, goal_seconds: float, today: date):
    """Rückblick auf die Vorwoche, solange diese Woche noch keine
    Tagesübung lief: {"days", "stars", "lesson_from", "lesson_to"} (Lektionen
    None, wenn keine bekannt), sonst None. Ohne jedes Üben in der Vorwoche
    ebenfalls None: Ein „0 Tage“ hilft niemandem."""
    this_week = monday(today)
    if _daily_days(state, this_week):
        return None
    first = this_week - timedelta(days=7)
    days = 0
    for offset in range(7):
        day = first + timedelta(days=offset)
        if daily.stars_on(state, day) or _practiced(practice_data, day, goal_seconds):
            days += 1
    if not days:
        return None
    lessons = []
    for entry in _daily_days(state, first):
        lesson = entry.get("lesson")
        if isinstance(lesson, int) and not isinstance(lesson, bool):
            # Ein Aufstieg an diesem Tag gilt ab dem nächsten, gehört aber zu dieser Woche.
            up = daily.LESSON_UP in entry.get("progress", [])
            lessons.append((lesson, lesson + 1 if up else lesson))
    lesson_from = min(a for a, _ in lessons) if lessons else None
    lesson_to = max(b for _, b in lessons) if lessons else None
    return {"days": days, "stars": stars_in_week(state, first), "lesson_from": lesson_from, "lesson_to": lesson_to}
