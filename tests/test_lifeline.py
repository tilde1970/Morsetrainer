"""Tests für die Lebenslinie (core/lifeline.py)."""
import unittest
from datetime import date, timedelta

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import awards, daily, koch, lifeline

START = date(2026, 9, 1)


def day(offset):
    return START + timedelta(days=offset)


def session(offset, **config):
    return awards.Session(day(offset), config, {}, [], [])


def daily_state(**days):
    """daily_state(d2={...}) -> Tageseinträge relativ zu START."""
    return {"days": {day(int(k[1:])).isoformat(): v for k, v in days.items()}}


EMPTY_AWARDS = {"seals": {}, "seeded": True}


class BuildTest(unittest.TestCase):
    def test_nothing_practised(self):
        self.assertEqual(lifeline.build({}, [], EMPTY_AWARDS, {}, day(5))["days"], [])

    def test_days_from_first_practice_until_today(self):
        line = lifeline.build({}, [], EMPTY_AWARDS, {day(2).isoformat(): 300}, day(4))
        self.assertEqual(line["days"], [day(2), day(3), day(4)])
        self.assertEqual(line["stars"], [0, 0, 0])
        self.assertEqual(line["lesson"], [None, None, None])

    def test_stars_add_up(self):
        state = daily_state(d0={"stars": list(daily.STAR_ORDER)}, d2={"stars": [daily.DABEI]})
        line = lifeline.build(state, [], EMPTY_AWARDS, {}, day(3))
        self.assertEqual(line["stars"], [3, 3, 4, 4])

    def test_lesson_is_highest_practised(self):
        sessions = [session(0, charset=koch.lesson_charset(5)),       # alt: nur der Zeichensatz
                    session(1, lesson=12, charset="egal"),
                    session(2, lesson=9),                              # zurück: Linie bleibt
                    session(3, charset="ABC123")]                      # keine Lektion
        state = daily_state(d4={"lesson": 13, "stars": []})
        line = lifeline.build(state, sessions, EMPTY_AWARDS, {}, day(4))
        self.assertEqual(line["lesson"], [5, 12, 12, 12, 13])

    def test_lesson_ends_at_final_lesson(self):
        line = lifeline.build({}, [session(0, lesson=koch.MAX_LESSON)], EMPTY_AWARDS, {}, day(0))
        self.assertEqual(line["lesson"], [koch.FINAL_LESSON])
        self.assertEqual(lifeline.session_lesson({"charset": koch.FINAL_CHARSET}), koch.FINAL_LESSON)

    def test_tempo_carries_forward(self):
        state = daily_state(d0={"tempo": 12}, d1={"stars": []}, d2={"tempo": 13})
        line = lifeline.build(state, [], EMPTY_AWARDS, {}, day(3))
        self.assertEqual(line["tempo"], [12, 12, 13, 13])

    def test_seals_by_day(self):
        state = {"seals": {"koch": {"0": day(1).isoformat(), "1": day(3).isoformat()},
                           "club": {"0": day(1).isoformat()}}, "seeded": True}
        line = lifeline.build({}, [], state, {}, day(3))
        self.assertEqual(line["days"][0], day(1))
        self.assertEqual(sorted(line["seals"][day(1)]), [("club", 0), ("koch", 0)])
        self.assertEqual(line["seals"][day(3)], [("koch", 1)])

    def test_ignores_broken_entries(self):
        state = {"days": {"kaputt": {"stars": [daily.DABEI]}, day(0).isoformat(): "kein dict"}}
        line = lifeline.build(state, [], EMPTY_AWARDS, {"auch kaputt": 5, day(0).isoformat(): 60}, day(0))
        self.assertEqual(line["stars"], [0])


class DailyTempoTest(unittest.TestCase):
    def test_main_block_stores_tempo(self):
        state = {"days": {}, "lesson": 12, "tempo": {"wpm": 20, "effective": 12}}
        daily.finish_block(state, START, daily.Block(daily.MAIN, "group", 4),
                           {"first_try_correct": 10, "first_try_total": 20, "wpm": 20, "minutes": 4})
        self.assertEqual(state["days"][START.isoformat()]["tempo"], 12)



class KochDoneTest(unittest.TestCase):
    """„Koch geschafft“ erst mit bestandener Lektion 41 (Gold im Koch-
    Diplom), nicht schon mit einem Durchgang in Lektion 41."""

    def test_practising_lesson_41_is_not_done(self):
        from morsetrainer.widgets import lifeline_widget as widget
        line = lifeline.build({}, [session(0, lesson=koch.FINAL_LESSON)], EMPTY_AWARDS, {}, day(1))
        self.assertEqual(line["lesson"], [koch.FINAL_LESSON] * 2)
        self.assertIsNone(line["koch_done"])
        self.assertNotIn("Koch geschafft", widget.summary_text(line))
        self.assertIn("Lektion 41", widget.summary_text(line))

    def test_gold_seal_marks_the_day(self):
        from morsetrainer.widgets import lifeline_widget as widget
        seals = {"seals": {"koch": {str(lifeline.KOCH_DONE_LEVEL): day(2).isoformat()}}, "seeded": True}
        line = lifeline.build({}, [session(0, lesson=koch.FINAL_LESSON)], seals, {}, day(3))
        self.assertEqual(line["koch_done"], day(2))
        self.assertFalse(widget.koch_done(line, day(1)))
        self.assertTrue(widget.koch_done(line, day(2)))
        self.assertIn("Lektion 41 (Koch geschafft)", widget.summary_text(line))
        bronze = {"seals": {"koch": {"0": day(1).isoformat()}}, "seeded": True}
        self.assertIsNone(lifeline.build({}, [session(0, lesson=10)], bronze, {}, day(3))["koch_done"])

if __name__ == "__main__":
    unittest.main()
