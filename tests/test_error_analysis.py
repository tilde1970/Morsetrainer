"""Tests für die Fehleranalyse: Ursache je Fehler, erneute Abfragen, klangliche
Ähnlichkeit, Gewichtung nach Verwechslungen und letzten Antworten."""
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import align, awards, morse, review, stats
from morsetrainer.core.awards import Session
from morsetrainer.core.weighting import CharPicker
from morsetrainer.modes.single_mode import RETRY_AFTER, RetryQueue


class SoundsSimilarTest(unittest.TestCase):
    def test_typical_confusions_are_similar(self):
        for pair in ("B6", "SH", "DU", "AN", "5H", "87"):
            self.assertTrue(morse.sounds_similar(*pair), pair)

    def test_distant_patterns_are_not(self):
        for pair in ("E7", "T0", "6N", "E5"):
            self.assertFalse(morse.sounds_similar(*pair), pair)

    def test_unknown_characters_are_not_similar(self):
        self.assertIsNone(morse.code_distance("B", "Ä"))
        self.assertFalse(morse.sounds_similar("B", "Ä"))

    def test_distance_is_symmetric(self):
        for a, b in (("B", "6"), ("K", "R"), ("0", "O")):
            self.assertEqual(morse.code_distance(a, b), morse.code_distance(b, a))


class SwapTest(unittest.TestCase):
    def test_neighbours_typed_the_other_way_round(self):
        self.assertEqual(align.swapped_results("ABCD", "ABDC"), {2, 3})
        self.assertEqual(align.swapped_results("KMUR", "KMRU"), {2, 3})

    def test_ordinary_substitution_is_not_a_swap(self):
        self.assertEqual(align.swapped_results("ABCD", "ABXD"), set())
        self.assertEqual(align.swapped_results("ABCD", "ABCD"), set())


class CauseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(stats, "STATS_DIR", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def _session(self):
        return stats.SessionStats("single", "BD6U", 20, 600)

    def test_only_a_heard_character_is_a_confusion(self):
        session = self._session()
        session.record_char("B", "6", False, 0.5, 20.0)                   # gehört
        session.record_char("B", "", False, 0.5, 20.0, cause="late")      # zu langsam
        session.record_char("B", "", False, 0.5, 20.0, cause="replay")    # erst nach Wiederholung
        session.record_char("B", "", False, 0.5, 20.0)                    # nichts getippt: verpasst
        session.record_char("D", "U", False, 0.5, 20.0, cause="swap")     # mit dem Nachbarn vertauscht
        self.assertEqual(session.per_char["B"]["confusions"], {"6": 1, "": 3})
        self.assertEqual(session.per_char["B"]["causes"], {"heard": 1, "late": 1, "replay": 1, "missed": 1})
        self.assertEqual(session.per_char["D"]["confusions"], {"": 1})
        self.assertEqual(session.per_char["D"]["causes"], {"swap": 1})

    def test_events_carry_the_cause_and_correct_ones_do_not(self):
        session = self._session()
        session.record_char("B", "B", True, 0.5, 20.0)
        session.record_char("B", "", False, 0.5, 20.0, cause="late")
        self.assertNotIn("cause", session.rounds[0])
        self.assertEqual(session.rounds[1]["cause"], "late")

    def test_causes_are_listed_next_to_the_confusions(self):
        text = stats.format_confusions({"6": 2, "": 4}, {"heard": 2, "late": 3, "swap": 1})
        self.assertEqual(text, "6 (2); zu langsam 3×, vertauscht 1×")
        # Ältere Daten ohne Ursache: der Rest heißt „ohne Eingabe“.
        self.assertEqual(stats.format_confusions({"": 2}), "ohne Eingabe 2×")
        self.assertEqual(stats.format_confusions({}), "")

    def test_causes_survive_merge_and_reload(self):
        session = self._session()
        session.record_char("B", "", False, 0.5, 20.0, cause="late")
        session.record_char("B", "6", False, 0.5, 20.0)
        session.finalize()
        again = self._session()
        again.record_char("B", "", False, 0.5, 20.0, cause="late")
        again.finalize()
        data = stats.load_all_time()
        self.assertEqual(data["B"]["causes"], {"late": 2, "heard": 1})
        self.assertEqual(data["B"]["confusions"], {"": 2, "6": 1})
        row = stats.all_time_char_rows(data)[0]
        self.assertEqual(row[6], "6 (1); zu langsam 2×")

    def test_broken_causes_are_cleaned(self):
        cleaned = stats._clean_all_time({"B": {"good": 1, "wrong": 0, "attempts": 1, "causes": [1]}})
        self.assertNotIn("causes", cleaned["B"])

    def test_recent_data_follows_the_stored_cause(self):
        session = self._session()
        session.record_char("B", "6", False, 0.5, 20.0)
        session.record_char("B", "", False, 0.5, 20.0, cause="late")
        session.record_char("D", "U", False, 0.5, 20.0, cause="swap")
        session.finalize()
        recent = stats.recent_char_data()
        self.assertEqual(recent["B"]["confusions"], {"6": 1, "": 1})
        self.assertEqual(recent["D"]["confusions"], {"": 1})
        self.assertEqual(recent["D"]["causes"], {"swap": 1})

    def test_old_lines_without_a_cause_count_as_before(self):
        tests.write_session([
            {"type": "config", "mode": "single", "start_time": datetime.now().isoformat(timespec="seconds")},
            {"type": "char", "char": "B", "typed": "6", "correct": False},
            {"type": "char", "char": "B", "typed": "", "correct": False},
        ])
        recent = stats.recent_char_data()
        self.assertEqual(recent["B"]["confusions"], {"6": 1, "": 1})


class RetryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(stats, "STATS_DIR", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_retry_counts_in_the_session_but_not_in_the_long_term_data(self):
        session = stats.SessionStats("single", "KMURE", 20, 600, review_promote=True)
        session.record_char("K", "M", False, 0.5, 20.0, latency=0.5)
        for _ in range(9):
            session.record_char("K", "K", True, 0.5, 20.0, latency=0.5, retry=True)
        self.assertEqual(session.summary()["total"], 10)           # Durchgang und Koch-Aufstieg wie bisher
        self.assertEqual(session.per_char["K"]["good"], 9)         # Anzeige
        self.assertEqual(session.kept_char["K"]["good"], 0)        # Gesamtstatistik und Lernkartei
        self.assertEqual(session.kept_char["K"]["wrong"], 1)
        session.finalize()
        self.assertEqual(stats.load_all_time()["K"]["good"], 0)
        self.assertEqual(stats.load_all_time()["K"]["wrong"], 1)

    def test_retry_does_not_lift_a_character_in_the_review_box(self):
        session = stats.SessionStats("single", "KMURESNAP", 20, 600, review_promote=True)
        for _ in range(10):
            session.record_char("K", "K", True, 0.5, 20.0, latency=0.5, retry=True)
        session.finalize()
        self.assertNotIn("K", review.load())

    def test_retry_events_are_marked_and_skipped_for_recent_data(self):
        session = stats.SessionStats("single", "KM", 20, 600)
        session.record_char("K", "K", True, 0.5, 20.0, latency=0.5, retry=True)
        session.record_char("K", "M", False, 0.5, 20.0)
        session.finalize()
        self.assertTrue(session.rounds[0]["retry"])
        self.assertEqual(stats.recent_char_data()["K"]["good"], 0)

    def test_queue_remembers_which_came_after_an_error(self):
        rng = random.Random(1)
        queue = RetryQueue(rng)
        queue.add("K")
        queue.add("M", error=False)
        seen = {}
        for _ in range(RETRY_AFTER[1] + 2):
            due = queue.next_due()
            if due:
                seen[due] = queue.last_after_error
            elif not queue.waiting:
                break
        self.assertEqual(seen, {"K": True, "M": False})
        self.assertGreaterEqual(RETRY_AFTER[0], 4)  # nicht gleich nach dem Fehler

    def test_next_due_resets_the_flag(self):
        queue = RetryQueue(random.Random(1))
        queue.add("K")
        for _ in range(RETRY_AFTER[1] + 1):
            queue.next_due()
        self.assertFalse(queue.last_after_error and queue.next_due() is None)


class WeightingErrorsTest(unittest.TestCase):
    def picker(self, charset, all_time, recent):
        with mock.patch.object(stats, "load_all_time", return_value=all_time), \
                mock.patch.object(stats, "recent_char_data", return_value=recent), \
                mock.patch.object(review, "due_chars", return_value=[]):
            return CharPicker(charset, weighted=True)

    def test_a_character_that_slips_now_stands_out_despite_many_old_hits(self):
        old = {"K": {"good": 400, "wrong": 4}, "M": {"good": 400, "wrong": 4}}
        recent = {"K": {"good": 5, "wrong": 5}, "M": {"good": 10, "wrong": 0}}
        picker = self.picker("KM", old, recent)
        self.assertGreater(picker._error_rate("K"), 0.4)
        self.assertLess(picker._error_rate("M"), 0.1)

    def test_few_recent_answers_do_not_decide(self):
        old = {"K": {"good": 400, "wrong": 4}}
        picker = self.picker("K", old, {"K": {"good": 1, "wrong": 2}})
        self.assertLess(picker._error_rate("K"), 0.1)

    def test_the_partner_of_a_confused_character_comes_more_often(self):
        recent = {"B": {"good": 10, "wrong": 6, "confusions": {"6": 5, "": 1}},
                  "6": {"good": 16, "wrong": 0, "confusions": {}},
                  "E": {"good": 16, "wrong": 0, "confusions": {}}}
        picker = self.picker("B6E", {}, recent)
        weights = dict(zip("B6E", picker.weights()))
        self.assertGreater(weights["6"], weights["E"])

    def test_a_single_confusion_gives_no_bonus(self):
        recent = {"B": {"good": 10, "wrong": 1, "confusions": {"6": 1}}, "6": {"good": 16, "wrong": 0},
                  "E": {"good": 16, "wrong": 0}}
        picker = self.picker("B6E", {}, recent)
        weights = dict(zip("B6E", picker.weights()))
        self.assertAlmostEqual(weights["6"], weights["E"])

    def test_latency_follows_the_last_days(self):
        old = {"K": {"total_latency_s": 200.0, "latency_count": 100}}  # früher im Schnitt 2 s
        recent = {"K": {"good": 10, "wrong": 0, "latencies": [0.4, 0.5, 0.5, 0.6, 0.5], "assumed_latencies": []}}
        picker = self.picker("K", old, recent)
        self.assertAlmostEqual(picker._mean_latency("K"), 0.5)

    def test_latency_falls_back_to_the_total_without_recent_data(self):
        old = {"K": {"total_latency_s": 200.0, "latency_count": 100}}
        picker = self.picker("K", old, {})
        self.assertAlmostEqual(picker._mean_latency("K"), 2.0)

    def test_assumed_latencies_do_not_count_as_measured(self):
        recent = {"K": {"good": 6, "wrong": 0, "latencies": [0.5, 0.5, 0.5, 2.0, 2.0],
                        "assumed_latencies": [2.0, 2.0]}}
        picker = self.picker("K", {}, recent)
        self.assertAlmostEqual(picker._mean_latency("K"), 0.5)
        self.assertAlmostEqual(picker._mean_latency("K", measured_only=True), 0.5)


class ConfusionListTest(unittest.TestCase):
    DATA = {
        "B": {"good": 20, "wrong": 5, "confusions": {"6": 4, "E": 1}},
        "D": {"good": 20, "wrong": 3, "confusions": {"U": 3}},
        "E": {"good": 20, "wrong": 3, "confusions": {"7": 3}},
    }

    def test_minimum_count_hides_single_events(self):
        pairs = stats.top_confusions(self.DATA, min_count=stats.MIN_CONFUSION_COUNT)
        self.assertEqual([p[:2] for p in pairs], [("B", "6"), ("D", "U"), ("E", "7")])

    def test_similar_only_drops_typos(self):
        pairs = stats.top_confusions(self.DATA, min_count=3, similar_only=True)
        self.assertEqual([p[:2] for p in pairs], [("B", "6"), ("D", "U")])

    def test_weakest_chars_use_the_rate_not_the_count(self):
        all_time = {"A": {"good": 950, "wrong": 50}, "R": {"good": 4, "wrong": 6}, "T": {"good": 2, "wrong": 1}}
        ranked = stats.weakest_chars({}, all_time)
        self.assertEqual([c for c, _ in ranked], ["R", "A"])  # T: zu wenige Antworten

    def test_recent_answers_override_the_old_rate(self):
        all_time = {"R": {"good": 4, "wrong": 6}, "A": {"good": 100, "wrong": 5}}
        recent = {"R": {"good": 10, "wrong": 0}, "A": {"good": 5, "wrong": 5}}
        self.assertEqual([c for c, _ in stats.weakest_chars(recent, all_time)], ["A"])

    def test_table_orders_by_error_rate(self):
        all_time = {"A": {"good": 950, "wrong": 50, "attempts": 1000}, "R": {"good": 4, "wrong": 6, "attempts": 10}}
        rows = stats.all_time_char_rows(stats._clean_all_time(all_time))
        self.assertEqual([r[0] for r in rows], ["R", "A"])


class AwardDigestTest(unittest.TestCase):
    def test_only_heard_errors_are_confusions(self):
        digest = awards.digest_of([("B", "6", False, "heard"), ("D", "U", False, "swap"),
                                   ("K", "M", False)], [])
        self.assertEqual({tuple(sorted(pair)) for pair, _ in digest.confusions}, {("6", "B"), ("K", "M")})

    def test_events_with_a_cause_are_read(self):
        digest = awards._events_digest([
            {"type": "char", "char": "B", "typed": "6", "correct": False, "cause": "swap"},
            {"type": "char", "char": "K", "typed": "M", "correct": False, "cause": "heard"},
            {"type": "char", "char": "S", "typed": "H", "correct": False}])
        self.assertEqual({tuple(sorted(pair)) for pair, _ in digest.confusions}, {("K", "M"), ("H", "S")})

    def test_pair_practised_apart_is_not_overcome(self):
        import datetime as dt
        start = dt.date(2026, 1, 1)

        def make(offset, chars):
            return Session(start + dt.timedelta(days=offset), {"mode": "single"}, {"total": len(chars)}, chars=chars)

        bad = [("B", "D", False)] * 6 + [("B", "B", True)] * 50 + [("D", "D", True)] * 50
        apart = [make(0, bad)]
        for i in range(1, 29):  # B und D getrennt geübt: nie zusammen
            apart.append(make(i, [("B", "B", True)] * 2))
            apart.append(make(i, [("D", "D", True)] * 2))
        together = [make(0, bad)] + [make(i, [("B", "B", True)] * 2 + [("D", "D", True)] * 2) for i in range(1, 29)]

        def overcome(sessions):
            data = awards.Data(sessions, [], {}, {})
            return awards._confusion_state(data)[0]
        self.assertEqual(len(overcome(together)), 1)
        self.assertEqual(overcome(apart), [])


class ErrorReviewTest(unittest.TestCase):
    @staticmethod
    def review(causes, pair=None, answers=100):
        total = sum(causes.values())
        return {"total": total, "answers": answers, "causes": causes, "pair": pair}

    def test_data_from_a_session(self):
        session = stats.SessionStats("single", "B6DU", 20, 600)
        for _ in range(3):
            session.record_char("B", "6", False, 0.5, 20.0)
        session.record_char("B", "", False, 0.5, 20.0, cause="late")
        session.record_char("D", "U", False, 0.5, 20.0, cause="swap")
        for _ in range(10):
            session.record_char("6", "6", True, 0.5, 20.0)
        review = stats.error_review(session.kept_char)
        self.assertEqual((review["total"], review["answers"]), (5, 15))
        self.assertEqual(review["causes"], {"heard": 3, "late": 1, "swap": 1})
        self.assertEqual(review["pair"], ("B", "6", 3))

    def test_a_single_confusion_is_no_pair(self):
        session = stats.SessionStats("single", "B6", 20, 600)
        session.record_char("B", "6", False, 0.5, 20.0)
        self.assertIsNone(stats.error_review(session.kept_char)["pair"])

    def test_line_names_the_causes_with_the_pair(self):
        line = stats.error_review_line(self.review({"heard": 5, "late": 3, "missed": 1}, ("B", "6", 3)))
        self.assertEqual(line, "Woran es lag: Von 9 Fehlern waren 5 Verwechslungen (B für 6 dreimal), "
                               "3 zu langsam, 1 verpasst.")

    def test_at_most_three_causes_and_the_rest_as_others(self):
        line = stats.error_review_line(self.review({"heard": 4, "late": 3, "missed": 2, "swap": 1, "replay": 1}))
        self.assertTrue(line.endswith("4 Verwechslungen, 3 zu langsam, 2 verpasst, 2 andere."))

    def test_nothing_with_few_errors(self):
        self.assertEqual(stats.error_review_line(self.review({"heard": 3})), "")
        self.assertEqual(stats.error_review_line(self.review({"heard": 4}, answers=200)), "")  # unter 5 %
        self.assertNotEqual(stats.error_review_line(self.review({"heard": 4}, answers=80)), "")

    def test_tip_only_for_a_dominant_cause(self):
        heard = self.review({"heard": 5, "late": 2})
        self.assertIn("Statistik", stats.error_review_tip(heard))
        late = self.review({"late": 5, "heard": 1})
        self.assertIn("entspannte Tagesübung", stats.error_review_tip(late))
        self.assertEqual(stats.error_review_tip(late, relaxed_hint=False), "")
        self.assertIn("langsameres Tempo", stats.error_review_tip(self.review({"missed": 4}, answers=60)))
        self.assertEqual(stats.error_review_tip(self.review({"heard": 2, "late": 2, "missed": 1, "swap": 1})), "")
        self.assertEqual(stats.error_review_tip(self.review({"heard": 3})), "")  # zu wenige Fehler

    def test_text_is_neutral(self):
        line = stats.error_review_line(self.review({"heard": 5, "late": 3, "missed": 1}, ("B", "6", 3)))
        for word in ("nur", "leider", "schlecht"):
            self.assertNotIn(word, line)


if __name__ == "__main__":
    unittest.main()
