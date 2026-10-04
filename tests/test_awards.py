"""Tests für die Diplome (core/awards.py)."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import awards, db, diploma, koch, stats
from morsetrainer.core.awards import Data, Session
from morsetrainer.widgets import awards_panel as panel

DAY = date(2026, 10, 1)


def day(offset=0):
    return DAY + timedelta(days=offset)


def session(mode, offset=0, chars=(), groups=(), **config_and_summary):
    config = {"mode": mode, "wpm": 20, "start_time": f"{day(offset).isoformat()}T20:00:00"}
    summary = {}
    for key, value in config_and_summary.items():
        (summary if key in ("total", "correct", "accuracy_pct", "extra_keys", "completed", "duration_s",
                            "first_try_correct", "first_try_total", "band_gain_min", "band_min") else config)[key] = value
    return Session(day(offset), config, summary, list(chars), list(groups))


def result(mode, offset=0, **fields):
    return {"mode": mode, "day": day(offset), "time": f"{day(offset).isoformat()}T20:00:00", **fields}


def data(sessions=(), results=(), review=None, practice=None):
    return Data(list(sessions), list(results), review or {}, practice or {})


def dates(key, d):
    return awards.evaluate(d, today=day(100))[key].dates


class LevelDatesTest(unittest.TestCase):
    def test_silver_needs_two_days(self):
        events = [(day(0), 30), (day(0), 31), (day(3), 26)]
        self.assertEqual(awards.level_dates(events, (20, 25, 30), two_days=True), [day(0), day(3), None])
        self.assertEqual(awards.level_dates(events, (20, 25, 30)), [day(0), day(0), day(0)])


class AwardsTest(unittest.TestCase):
    def test_koch_needs_first_tries_and_fast_chars(self):
        ok = session("group", 0, lesson=12, first_try_correct=46, first_try_total=50)
        slow = session("group", 1, lesson=30, wpm=15, first_try_correct=50, first_try_total=50)
        few = session("group", 2, lesson=30, first_try_correct=40, first_try_total=40)
        self.assertEqual(dates("koch", data([ok, slow, few])), [day(0), None, None])

    def test_koch_gold_with_final_lesson(self):
        runs = [session("group", 0, lesson=25, first_try_correct=50, first_try_total=50),
                session("group", 1, lesson=40, first_try_correct=50, first_try_total=50)]
        # Silber und höher an zwei verschiedenen Tagen: Lektion 40 zählt auch für 25.
        self.assertEqual(dates("koch", data(runs)), [day(0), day(1), None])
        final = koch.lesson_of(koch.FINAL_CHARSET)
        runs.append(session("group", 2, lesson=final, first_try_correct=50, first_try_total=50))
        self.assertEqual(dates("koch", data(runs)), [day(0), day(1), None])  # erst ein Tag mit 41
        runs.append(session("continuous", 4, lesson=final, content="chars", total=60, correct=60,
                            accuracy_pct=100.0))
        self.assertEqual(dates("koch", data(runs)), [day(0), day(1), day(4)])

    def test_koch_entry_at_final_lesson_needs_a_second_day(self):
        # Einstieg in Lektion 41: ein Glückstreffer bringt nur Bronze.
        final = koch.lesson_of(koch.FINAL_CHARSET)
        runs = [session("group", 0, lesson=final, first_try_correct=58, first_try_total=60),
                session("group", 0, lesson=final, first_try_correct=59, first_try_total=60)]
        self.assertEqual(dates("koch", data(runs)), [day(0), None, None])
        runs.append(session("group", 1, lesson=final, first_try_correct=57, first_try_total=60))
        self.assertEqual(dates("koch", data(runs)), [day(0), day(1), day(1)])

    def test_worked_all_letters_counts_best_box(self):
        review = {ch: {"box": 0, "best_box": 2, "best_day": day(i).isoformat()} for i, ch in enumerate("ABCDEFGHIJ")}
        self.assertEqual(dates("wal", data(review=review)), [day(9), None, None])
        self.assertEqual(awards.wal_progress(data(review=review)), (10, 26))

    def test_letter_boxes_count_only_when_reached_fast(self):
        # award_box: Fach aus Sitzungen ab 18 WPM; best_box allein (alte Einträge) zählt weiter.
        review = {ch: {"box": 3, "best_box": 3, "award_box": 1, "best_day": day(i).isoformat()}
                  for i, ch in enumerate("ABCDEFGHIJ")}
        self.assertEqual(dates("wal", data(review=review)), [None, None, None])
        review["A"].update(award_box=2, award_day=day(20).isoformat())
        review.update({ch: {"box": 2, "best_box": 2, "best_day": day(0).isoformat()} for ch in "KLMNOPQRS"})
        self.assertEqual(dates("wal", data(review=review))[0], day(20))

    def test_flow_and_qrq_need_full_clean_runs(self):
        flow = dict(content="words", completed=True, duration_s=180, total=100, correct=95, extra_keys=3,
                    farnsworth_wpm=15, charset=koch.lesson_charset(20))
        runs = [session("continuous", 0, **flow), session("continuous", 1, **{**flow, "extra_keys": 10}),
                session("continuous", 2, **{**flow, "completed": False})]
        self.assertEqual(dates("flow", data(runs)), [day(0), None, None])
        runs = [session("continuous", 0, **{**flow, "user_words": True}),
                session("continuous", 1, **{**flow, "charset": koch.lesson_charset(10)}),
                session("continuous", 2, wpm=25, **{**flow, "farnsworth_wpm": None}),
                session("continuous", 3, wpm=25, **{**flow, "farnsworth_wpm": None})]
        # Eigene Wörter und kleiner Zeichensatz zählen nicht; mit Wörtern höchstens Silber.
        self.assertEqual(dates("flow", data(runs)), [day(2), day(3), None])
        for run in runs[2:]:
            run.config["content"] = "phrases"  # Gold an zwei Tagen
        self.assertEqual(dates("flow", data(runs)), [day(2), day(3), day(3)])
        qrq = dict(content="chars", group_len=5, charset=koch.lesson_charset(40), completed=True,
                   duration_s=200, total=300, correct=290, extra_keys=0)
        runs = [session("continuous", 0, wpm=26, **qrq), session("continuous", 1, wpm=25, **qrq),
                session("continuous", 2, wpm=30, farnsworth_wpm=20, **qrq),
                session("continuous", 3, wpm=30, **{**qrq, "charset": "KMURES"})]
        self.assertEqual(dates("qrq", data(runs)), [day(0), day(1), None, None])

    def test_qrn_levels(self):
        base = dict(charset=koch.lesson_charset(30), total=200, correct=180, accuracy_pct=90.0,
                    farnsworth_wpm=12, band_gain=100)
        runs = [session("group", 0, band="medium", **base),
                session("group", 1, band="heavy", **{**base, "accuracy_pct": 86.0}),
                session("group", 2, band="heavy", **{**base, "band_gain": 50}),
                session("group", 3, band="light", **{**base, "charset": "KMURES"})]
        self.assertEqual(dates("qrn", data(runs)), [day(0), day(1), None])

    def test_qrn_counts_lowest_gain_and_fluent_first_tries(self):
        base = dict(charset=koch.lesson_charset(30), band="light", total=200, correct=200, accuracy_pct=100.0,
                    band_gain=100)
        runs = [session("group", 0, **base, band_gain_min=0),  # Regler im Lauf heruntergezogen
                session("group", 1, **base, first_try_correct=170, first_try_total=200),  # zu viel überlegt
                session("group", 2, **base, first_try_correct=185, first_try_total=200, band_gain_min=100)]
        self.assertEqual(dates("qrn", data(runs))[0], day(2))

    def test_qrn_counts_weakest_band_level_of_the_run(self):
        base = dict(charset=koch.lesson_charset(30), total=200, correct=200, accuracy_pct=100.0, band_gain=100,
                    band_gain_min=100, wpm=20, farnsworth_wpm=12, completed=True, extra_keys=0, duration_s=200)
        runs = [session("group", 0, band="heavy", band_min="light", **base),  # mittendrin leichter gestellt
                session("group", 1, band="heavy", band_min=None, **base),     # zwischendurch aus
                session("continuous", 2, band="medium", band_min="medium", **{**base, "band_gain_min": 80}),
                session("continuous", 3, band="medium", band_min="medium", content="chars", **base)]
        self.assertEqual([(d, rank) for d, rank, _ in awards._qrn_runs(data(runs))], [(day(0), 1), (day(3), 2)])

    def test_hints_show_how_close_the_next_level_is(self):
        base = dict(charset=koch.lesson_charset(30), total=200, correct=170, accuracy_pct=85.0, band_gain=100)
        status = awards.evaluate(data([session("group", 0, band="medium", **base)]), today=day(1))["qrn"]
        self.assertEqual(status.hint[1], {"band": "leicht", "share": 85, "need": 90})
        self.assertIn("leicht: 85 % (nötig 90 %)", panel.detail_text(awards.BY_KEY["qrn"], status))
        run = result("contest", 0, wpm=22, activity=1, minutes=10, correct=8, total=9, busted=1)
        hint = awards.evaluate(data(results=[run]), today=day(1))["contest"].hint
        self.assertEqual(hint[1], {"wpm": 20, "rate": 8, "need": 10, "errors": 1, "share": 11})
        hint = awards.evaluate(data(), today=day(1))["confusion"].hint
        self.assertIn("Noch kein Paar", hint[0])
        bad = [("B", "D", False)] * 6 + [("B", "B", True)] * 50 + [("D", "D", True)] * 50
        clean = [("B", "B", True)] * 2 + [("D", "D", True)] * 2
        sessions = [session("single", 0, chars=bad)] + [session("single", i, chars=clean) for i in range(1, 11)]
        hint = awards.evaluate(data(sessions), today=day(10))["confusion"].hint
        self.assertEqual(hint[1], {"pair": "B/D", "days": 18, "tries": 20, "need": 40})

    def test_rufz_full_runs_without_prefix_filter(self):
        runs = [result("rufz", 0, total=50, score=3600, start_wpm=20, prefixes=[]),
                result("rufz", 1, total=50, score=3700, start_wpm=20, prefixes=["DL"]),
                result("rufz", 2, total=50, score=9000, start_wpm=16, prefixes=[]),
                result("rufz", 3, total=50, score=3500)]  # alter Eintrag ohne Bedingungen
        self.assertEqual(dates("rufz", data(results=runs)), [day(0), day(3), None, None])

    def test_contest_rate_and_errors(self):
        bronze = result("contest", 0, wpm=22, activity=1, minutes=10, correct=12, total=13, busted=1)
        silver = dict(wpm=25, activity=2, minutes=10, correct=20, total=20)
        short = result("contest", 3, wpm=35, activity=3, minutes=5, correct=20, total=20)
        runs = [bronze, result("contest", 1, **silver), result("contest", 2, **silver), short]
        self.assertEqual(dates("contest", data(results=runs)), [day(0), day(2), None])

    def test_wpx_prefixes(self):
        self.assertEqual(awards.wpx_prefix("DL1ABC/P"), "DL1")
        self.assertEqual(awards.wpx_prefix("OE/DL1ABC"), "OE0")
        self.assertEqual(awards.wpx_prefix("2E0ABC"), "2E0")
        self.assertEqual(awards.wpx_prefix("W1AW/4"), "W4")
        calls = [(f"DL{i}ABC", f"DL{i}ABC", True) for i in range(10)] + [("K1ABC", "K1ABC", False)]
        groups = [(f"W{i}XX", f"W{i}XX", True) for i in range(10)] * 2  # doppelt zählt einmal
        contest = result("contest", 1, wpm=22, calls=[f"{p}{i}A" for p in ("F", "G", "I", "N", "R", "S", "VE", "JA")
                                                       for i in range(10)])
        slow = [session("callsign", 2, wpm=15, groups=[(f"SP{i}X", f"SP{i}X", True) for i in range(10)]),
                result("contest", 2, wpm=16, calls=["OK1A", "HA1A"])]  # unter 18 WPM zählt nicht
        d = data([session("callsign", 0, groups=calls + groups), slow[0]], [contest, slow[1]])
        status = awards.evaluate(d, today=day(5))["wpx"]
        self.assertEqual((status.value, status.dates[0]), (100, day(1)))

    def test_headphones_needs_three_in_a_row(self):
        good = dict(kind="ragchew", correct=3, total=3, replays=0)
        runs = [result("qso_head", 0, wpm=21, **good), result("qso_head", 0, wpm=16, **good),
                result("qso_head", 1, wpm=22, **{**good, "replays": 1}),
                result("qso_head", 2, wpm=21, **good), result("qso_head", 2, wpm=20, **good),
                result("qso_head", 3, wpm=25, **good)]
        self.assertEqual(dates("headphones", data(results=runs)), [day(3), day(3), None])

    def test_headphones_silver_needs_normal_length(self):
        good = dict(kind="ragchew", correct=3, total=3, replays=0, wpm=26)
        short = [result("qso_head", 0, length="Kurz", **good)] * 3
        self.assertEqual(dates("headphones", data(results=short)), [day(0), None, None])
        long = [result("qso_head", 1, length="Normal", **good)] * 3
        self.assertEqual(dates("headphones", data(results=short + long)), [day(0), day(1), day(1)])

    def test_qso_awards_need_fast_chars_where_known(self):
        good = dict(kind="ragchew", correct=3, total=3, replays=0, wpm=16)
        slow = [result("qso_head", 0, char_wpm=16, **good)] * 3
        self.assertEqual(dates("headphones", data(results=slow))[0], None)
        self.assertEqual(dates("first_qso", data(results=slow)), [None])
        fast = [result("qso_head", 1, char_wpm=20, **good)] * 3
        self.assertEqual(dates("headphones", data(results=slow + fast))[0], day(1))
        self.assertEqual(dates("first_qso", data(results=[result("qso_quiz", 2, **good)])), [day(2)])  # vor 2.26

    def test_skipped_head_copy_breaks_the_run(self):
        good = dict(kind="ragchew", correct=3, total=3, replays=0, wpm=16)
        runs = [result("qso_head", 0, **good)] * 2 + [result("qso_head", 0, kind="ragchew", correct=0, total=3,
                                                              wpm=16, skipped=True)] + [result("qso_head", 0, **good)]
        self.assertEqual(dates("headphones", data(results=runs))[0], None)

    def test_confusion_overcome_after_28_clean_days(self):
        bad = [("B", "D", False)] * 6 + [("B", "B", True)] * 50 + [("D", "D", True)] * 50
        clean = [("B", "B", True)] * 2 + [("D", "D", True)] * 2
        sessions = [session("single", 0, chars=bad)] + [session("single", i, chars=clean) for i in range(1, 29)]
        self.assertEqual(dates("confusion", data(sessions))[0], day(28))
        self.assertIsNone(dates("confusion", data(sessions[:-1]))[0])

    def test_endurance_and_heard(self):
        practice = {day(i).isoformat(): 600 for i in range(0, 20, 2)}
        practice[day(1).isoformat()] = 300
        self.assertEqual(dates("endurance", data(practice=practice))[0], day(18))
        chars = [("K", "K", True)] * 2500
        sessions = [session("single", 0, chars=chars), session("word", 1, chars=chars),
                    session("group", 2, wpm=15, chars=chars), session("group", 3, chars=chars)]
        self.assertEqual(dates("heard", data(sessions))[0], day(3))  # Wörter und 15 WPM zählen nicht

    def test_unlevelled_awards(self):
        quiz = result("qso_quiz", 0, kind="ragchew", correct=5, total=5, replays=0, wpm=15)
        self.assertEqual(dates("first_qso", data(results=[quiz])), [day(0)])
        contests = [result("contest", i, contest=kind, total=30, correct=28, nil=2)
                    for i, kind in enumerate(awards.CONTEST_KINDS)]
        self.assertEqual(dates("all_contests", data(results=contests)), [day(4)])
        self.assertEqual(dates("club", data([session("network", 2, duration_s=600)]))[0], day(2))
        led = result("network", 1, role="trainer", duration_s=240)
        self.assertIsNone(dates("club", data([session("network", 1, duration_s=300)], [led]))[0])  # 9 Min.
        evening = [session("network", 3, duration_s=300), session("network", 3, duration_s=300)]
        self.assertEqual(dates("club", data(evening))[0], day(3))  # Durchgänge eines Abends zählen zusammen
        led_long = result("network", 4, role="trainer", duration_s=660)
        self.assertEqual(dates("club", data(results=[led_long]))[0], day(4))
        old_log = session("network", 5)  # Protokoll ohne Dauer (vor 2.22): Teilnahme genügt
        self.assertEqual(dates("club", data([old_log]))[0], day(5))

    def test_club_levels_count_evenings(self):
        evenings = [session("network", i, duration_s=600) for i in range(40)]
        self.assertEqual(dates("club", data(evenings)), [day(0), day(4), day(14), day(39)])
        same_day = [session("network", 0, duration_s=600)] * 5
        self.assertEqual(dates("club", data(same_day)), [day(0), None, None, None])  # ein Abend
        groups = [(q, q, True) for q in awards.Q_GROUPS]
        q = [session("word", 0, groups=groups * 2), session("word", 1, groups=groups)]
        self.assertEqual(dates("q_groups", data(q)), [day(1)])
        review = {d: {"box": 2, "day": day(int(d)).isoformat()} for d in awards.DIGITS}
        self.assertEqual(dates("digits", data(review=review)), [day(9)])


class OverviewTest(unittest.TestCase):
    def test_progress_and_second_day(self):
        koch_runs = [session("group", 0, lesson=18, first_try_correct=50, first_try_total=50)]
        status = awards.evaluate(data(koch_runs), today=day(5))["koch"]
        self.assertEqual((status.next_level, status.progress), (1, (18, 25)))
        self.assertEqual(panel.next_text(awards.BY_KEY["koch"], status), "Silber: 18 / 25 Lektionen")
        qrq = dict(content="chars", group_len=5, charset=koch.lesson_charset(40), completed=True,
                   duration_s=200, total=300, correct=290, extra_keys=0)
        status = awards.evaluate(data([session("continuous", 0, wpm=26, **qrq)]), today=day(5))["qrq"]
        self.assertTrue(status.second_day)
        self.assertEqual(panel.next_text(awards.BY_KEY["qrq"], status), "Silber: an einem zweiten Tag wiederholen")
        status = awards.evaluate(data(), today=day(5))["first_qso"]
        self.assertEqual((panel.seals_text(awards.BY_KEY["first_qso"], status),
                          panel.next_text(awards.BY_KEY["first_qso"], status)), ("–", "–"))

    def test_club_without_seal_comes_last(self):
        rows = awards.overview({"seals": {}, "seeded": True}, awards.evaluate(data(), today=day(5)))
        award, status = rows[-1]
        self.assertEqual(award.key, "club")
        self.assertEqual(panel.next_text(award, status), "gemeinsam im Netzwerk")
        statuses = awards.evaluate(data([session("network", 0, duration_s=600)]), today=day(5))
        keys = [a.key for a, _ in awards.overview({"seals": {}, "seeded": True}, statuses)]
        self.assertEqual(keys, [a.key for a in awards.AWARDS])

    def test_diploma_shows_only_the_reached_step(self):
        text = panel.diploma_condition(awards.BY_KEY["contest"], 2)
        self.assertIn("Gold: ≥ 30 WPM", text)
        self.assertNotIn("Bronze", text)
        self.assertIn("Bronze: ", panel.detail_text(awards.BY_KEY["qrn"], awards.evaluate(data())["qrn"]))

    def test_protocol_dates_win_and_stay(self):
        state = {"seals": {"club": {"0": day(-3).isoformat()}, "endurance": {"0": day(-9).isoformat()}},
                 "seeded": True}
        rows = dict(awards.overview(state, awards.evaluate(data([session("network", 0)]), today=day(5))))
        self.assertEqual(rows[awards.BY_KEY["club"]].dates, [day(-3), None, None, None])  # altes Siegel = Bronze
        endurance = rows[awards.BY_KEY["endurance"]]
        self.assertEqual((endurance.dates[0], endurance.next_level, endurance.progress), (day(-9), 1, (0, 50)))
        self.assertIn("Bronze am", panel.detail_text(awards.BY_KEY["endurance"], endurance))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patch = mock.patch.object(stats, "STATS_DIR", directory)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_first_check_seeds_silently_then_reports_new(self):
        club = data([session("network", 0, duration_s=600)])
        self.assertEqual(awards.check(today=day(5), data=club), ([], 1))
        self.assertEqual(awards.seals_of(awards.load(), "club"), {0: day(0)})  # Tag des Erreichens
        quiz = result("qso_quiz", 6, kind="ragchew", correct=5, total=5, replays=0, wpm=15)
        more = data([session("network", 0, duration_s=600)], [quiz])
        self.assertEqual(awards.check(today=day(7), data=more), ([("first_qso", 0)], None))
        self.assertEqual(awards.seals_of(awards.load(), "first_qso"), {0: day(7)})
        self.assertEqual(awards.check(today=day(8), data=data()), ([], None))  # nichts geht verloren
        self.assertIn("club", awards.load()["seals"])


class DamagedDataTest(unittest.TestCase):
    """Von Hand veränderte oder beschädigte Dateien dürfen die Prüfung nach
    der Übung nicht jedes Mal scheitern lassen."""

    def test_session_lines_with_wrong_types(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(stats, "STATS_DIR", Path(tmp)):
            session_id = tests.write_session([
                {"type": "config", "mode": "single", "start_time": "2026-10-01T20:00:00"},
                {"type": "char", "char": "K", "typed": None, "correct": False},
                {"type": "char", "char": ["K"], "typed": "K", "correct": True},
                {"type": "group", "sent": "KM", "typed": 5, "first": "ja"},
                {"type": "summary", "total": 2},
            ])
            db._write("INSERT INTO events (session_id, type, data) VALUES (?, '', '[1, 2]')", (session_id,))
            [loaded] = awards._load_sessions()
        self.assertEqual(loaded.chars, [("K", "", False), ("", "K", True)])
        self.assertEqual(loaded.groups, [("KM", "", None)])

    def test_failing_award_leaves_the_others(self):
        club = data([session("network", 0, duration_s=600)])
        awards._failed.clear()
        with mock.patch.object(awards, "_koch", side_effect=TypeError("kaputt")), \
                mock.patch.object(awards.errorlog, "record") as record:
            statuses = awards.evaluate(club, today=day(1))
            awards.evaluate(club, today=day(1))
        self.assertEqual(statuses["koch"].dates, [None] * len(awards.BY_KEY["koch"].targets))
        self.assertEqual(statuses["club"].dates[0], day(0))
        record.assert_called_once()  # je Diplom und Programmlauf einmal ins Fehlerprotokoll
        awards._failed.clear()

    def test_band_of_wrong_type(self):
        broken = session("group", 0, band=["heavy"], lesson=20, total=50, correct=50)
        self.assertEqual(awards._qrn_runs(data([broken])), [])


class DiplomaTest(unittest.TestCase):
    def test_page_shows_award_level_call_and_date(self):
        award = awards.BY_KEY["koch"]
        page = diploma.diploma_html("Koch", "Silber", diploma.seal_colors(1), panel.diploma_condition(award, 1),
                                    "03.10.2026", "DL0ABC", "Erika",
                                    labels={"title": "Diplom", "awarded": "verliehen an"})
        for text in ("Koch", "Silber", "DL0ABC", "Erika", "03.10.2026", "Silber ab 25 Lektionen", "landscape"):
            self.assertIn(text, page)
        club = awards.BY_KEY["club"]
        self.assertTrue(panel.diploma_condition(club, 0).endswith("Bronze ab 1 Abend"))
        self.assertTrue(panel.diploma_condition(club, 1).endswith("Silber ab 5 Abenden"))
        self.assertTrue(panel.diploma_condition(awards.BY_KEY["confusion"], 0).endswith("Bronze ab 1 Paar"))
        plain = diploma.diploma_html("Clubabend", "", diploma.seal_colors(0, levels=False), "<b>", "1.1.", "")
        self.assertNotIn("verliehen", plain)
        self.assertIn("&lt;b&gt;", plain)

    def test_award_name_in_morse(self):
        self.assertEqual(diploma.morse_of("Koch"), [["-.-", "---", "-.-.", "...."]])
        self.assertEqual(diploma.morse_of("Hör-Test!")[0][:3], ["....", "---", "."])  # Ö als OE
        self.assertEqual(diploma.morse_svg("", "#000"), "")
        self.assertEqual(diploma.morse_svg("E", "#000").count("<rect"), 1)


class DiplomaNumberTest(unittest.TestCase):
    DAY = date(2026, 10, 4)

    def test_number_is_readable(self):
        self.assertEqual(diploma.diploma_number("dl1abc ", "koch", 2, self.DAY), "DL1ABC-KOCH-G-20261004")
        self.assertEqual(diploma.diploma_number("DL1ABC", "qrq", 3, self.DAY), "DL1ABC-QRQ-P-20261004")
        self.assertEqual(diploma.diploma_number("DL1ABC", "first_qso", None, self.DAY), "DL1ABC-FIRSTQSO-20261004")
        self.assertEqual(diploma.diploma_number("  ", "koch", 0, self.DAY), "")

    def test_diploma_shows_number(self):
        award = awards.BY_KEY["koch"]
        page = panel.diploma_page(award, 2, self.DAY, "DL1ABC", "Max")
        for text in ("Nr. DL1ABC-KOCH-G-20261004", "Max", "Gold", "04.10.2026", "landscape"):
            self.assertIn(text, page)
        self.assertNotIn("Nr.", panel.diploma_page(award, 2, self.DAY, "", "Max"))
        plain = panel.diploma_page(awards.BY_KEY["first_qso"], 0, self.DAY, "DL1ABC", "")
        self.assertIn("DL1ABC-FIRSTQSO-20261004", plain)


class DiplomaMotifTest(unittest.TestCase):
    DAY = date(2026, 10, 4)

    def test_every_award_has_a_motif_and_the_club_house_exists(self):
        for key in list(awards.BY_KEY) + [diploma.CLUB_MOTIF]:
            svg = diploma.motif_svg(key, "left")
            self.assertTrue(svg.startswith('<svg class="motif left" viewBox="'), key)
            self.assertIn("currentColor", svg)
            self.assertIn("var(--paper", svg)

    def test_diploma_shows_award_motif_left_and_club_house_right(self):
        page = panel.diploma_page(awards.BY_KEY["koch"], 2, self.DAY, "DL1ABC", "Max")
        self.assertEqual(page.count('class="motif left"'), 1)
        self.assertEqual(page.count('class="motif right"'), 1)

    def test_preview_has_stamp_but_no_date_or_number(self):
        page = panel.diploma_page(awards.BY_KEY["headphones"], 1, None, "DL1ABC", "Max")
        for text in ("VORSCHAU", "Silber", "DL1ABC", "Datum: –", 'class="motif left"'):
            self.assertIn(text, page)
        self.assertNotIn("Nr.", page)
        self.assertNotIn("VORSCHAU", panel.diploma_page(awards.BY_KEY["headphones"], 1, self.DAY, "DL1ABC", "Max"))

    def test_missing_motif_is_left_out(self):
        self.assertEqual(diploma.motif_svg("gibt-es-nicht", "left"), "")
        with mock.patch.object(diploma, "MOTIF_DIR", Path("/nirgends")):
            page = panel.diploma_page(awards.BY_KEY["koch"], 0, self.DAY, "DL1ABC", "")
        self.assertNotIn('class="motif', page)
        self.assertIn("DL1ABC", page)


class DiplomaWindowTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()
        self.tk = tk

    def tearDown(self):
        self.root.destroy()

    def test_print_uses_call_and_name_from_the_window(self):
        tk = self.tk
        call, name = tk.StringVar(value="dl1abc"), tk.StringVar(value="Max")
        window = panel.DiplomaWindow(self.root, [("koch", 2, date(2026, 10, 4))], call, name)
        with mock.patch.object(panel, "print_diploma", return_value="ok") as printed:
            window._print(awards.BY_KEY["koch"], 2, date(2026, 10, 4))
        printed.assert_called_once_with(awards.BY_KEY["koch"], 2, date(2026, 10, 4), "DL1ABC", "Max")
        window.close()


    def test_preview_button_shows_the_next_open_level(self):
        box = self.tk.Frame(self.root)
        awards_box = panel.AwardsPanel(box, station=lambda: ("DL1ABC", "Max"))
        koch, club = awards.BY_KEY["koch"], awards.BY_KEY["club"]
        done = awards.Status([date(2026, 10, 4)] * 4, 40)
        awards_box.refresh([(koch, awards.Status([date(2026, 10, 1), None, None], 12)), (club, done)])
        awards_box.tree.selection_set("koch")
        awards_box._show_detail()
        self.assertEqual(str(awards_box.preview_button["state"]), "normal")
        with mock.patch.object(panel, "preview_diploma", return_value="ok") as preview:
            awards_box._preview()
        preview.assert_called_once_with(koch, 1, "DL1ABC", "Max")
        self.assertEqual(awards_box.note_var.get(), "ok")
        awards_box.tree.selection_set("club")  # alle Stufen erreicht: keine Vorschau
        awards_box._show_detail()
        self.assertEqual(str(awards_box.preview_button["state"]), "disabled")
        self.assertEqual(awards_box.note_var.get(), "")

if __name__ == "__main__":
    unittest.main()
