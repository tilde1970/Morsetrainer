"""Tests für Wochenstreifen, Wochenziel und Wochenrückblick (core/week.py)."""
import unittest
from datetime import date, timedelta

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import daily, week
from morsetrainer.widgets import daily_panel

MONDAY = date(2026, 10, 5)
GOAL = 600  # Tagesziel 10 Min


def day_with(stars, lesson=12, progress=()):
    return {"stars": list(stars), "blocks": [{"kind": daily.MAIN}], "minutes": 10.0,
            "progress": list(progress), "lesson": lesson}


def iso(offset):
    return (MONDAY + timedelta(days=offset)).isoformat()


class StripTest(unittest.TestCase):
    def test_days_from_monday(self):
        state = {"days": {iso(0): day_with(daily.STAR_ORDER), iso(1): day_with([daily.DABEI])}}
        practice = {iso(2): 650, iso(3): 100}
        days = week.strip(state, practice, GOAL, MONDAY + timedelta(days=3))
        self.assertEqual([d["day"] for d in days], [MONDAY + timedelta(days=i) for i in range(7)])
        self.assertEqual([d["stars"] for d in days[:2]], [3, 1])
        self.assertEqual([d["status"] for d in days[2:]],
                         [week.PRACTICED, week.NONE, week.FUTURE, week.FUTURE, week.FUTURE])
        self.assertEqual(daily_panel.week_text(days), "Mo ★★★  Di ★  Mi ✓  Do –  Fr ·  Sa ·  So ·")

    def test_without_goal_any_practice_counts(self):
        days = week.strip({"days": {}}, {iso(0): 30}, 0, MONDAY)
        self.assertEqual(days[0]["status"], week.PRACTICED)

    def test_stars_and_goal(self):
        state = {"days": {iso(i): day_with(daily.STAR_ORDER) for i in range(3)}}
        state["days"][iso(-1)] = day_with(daily.STAR_ORDER)  # Sonntag davor zählt nicht
        self.assertEqual(week.stars_in_week(state, MONDAY + timedelta(days=6)), 9)
        self.assertEqual(daily_panel.week_goal_text(9), "9 von 12 ★ diese Woche")
        self.assertEqual(daily_panel.week_goal_text(13), "Wochenziel erreicht: 13 ★")


class ReviewTest(unittest.TestCase):
    def test_last_week_until_first_daily(self):
        state = {"days": {iso(-7): day_with(daily.STAR_ORDER, lesson=12),
                          iso(-5): day_with([daily.DABEI, daily.WEITER], lesson=12, progress=[daily.LESSON_UP]),
                          iso(-3): day_with([daily.DABEI], lesson=13)}}
        practice = {iso(-2): 700}  # frei geübt
        review = week.last_week_review(state, practice, GOAL, MONDAY + timedelta(days=1))
        self.assertEqual(review, {"days": 4, "stars": 6, "lesson_from": 12, "lesson_to": 13})
        self.assertEqual(daily_panel.review_line(review), "Letzte Woche: 4 Tage, 6 ★, Lektion 12 → 13")
        state["days"][iso(1)] = day_with([])  # erste Tagesübung dieser Woche
        self.assertIsNone(week.last_week_review(state, practice, GOAL, MONDAY + timedelta(days=1)))

    def test_nothing_last_week(self):
        self.assertIsNone(week.last_week_review({"days": {}}, {}, GOAL, MONDAY))

    def test_only_free_practice(self):
        review = week.last_week_review({"days": {}}, {iso(-1): 900}, GOAL, MONDAY)
        self.assertEqual(review, {"days": 1, "stars": 0, "lesson_from": None, "lesson_to": None})
        self.assertEqual(daily_panel.review_line(review), "Letzte Woche: 1 Tag, 0 ★")

    def test_koch_completed_instead_of_lesson_number(self):
        review = {"days": 3, "stars": 5, "lesson_from": 40, "lesson_to": daily.POST_KOCH}
        self.assertEqual(daily_panel.review_line(review), "Letzte Woche: 3 Tage, 5 ★, Lektion 40 → Koch geschafft")
        review.update(lesson_from=44, lesson_to=45)  # alte Daten: Lektion 45 heißt schon nach Koch
        self.assertEqual(daily_panel.review_line(review), "Letzte Woche: 3 Tage, 5 ★")
        self.assertEqual(daily_panel.outlook_line({"lesson": 41, "missing": 3}),
                         "Noch 3 % beim ersten Versuch bis Lektion 41")
        self.assertEqual(daily_panel.outlook_line({"lesson": daily.POST_KOCH, "missing": 3}),
                         "Noch 3 % beim ersten Versuch bis zum Koch-Abschluss")
        self.assertIn("Koch geschafft", daily_panel.outlook_line({"lesson": daily.POST_KOCH, "pending": True}))


class LessonPerDayTest(unittest.TestCase):
    def test_finish_block_records_lesson(self):
        state = {"days": {}, "lesson": 17}
        daily.finish_block(state, MONDAY, daily.Block(daily.WARMUP, "single", 3), {})
        self.assertEqual(state["days"][MONDAY.isoformat()]["lesson"], 17)


if __name__ == "__main__":
    unittest.main()
