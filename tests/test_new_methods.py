"""Tests für Hören & Sagen (Sprache, MP3), Klartext/Wendungen und die
Lernkartei. Laufen ohne Stimme und Soundkarte: die Sprachausgabe wird
durch Stille ersetzt."""
import json
import random
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import koch, mp3, review, speech, stats, words
from morsetrainer.core.morse import MORSE_CODE, SAMPLE_RATE
from morsetrainer.modes.content import ItemSource
from tests.test_modes import AppTestCase


def fake_synth(text):
    return np.zeros(int(0.1 * SAMPLE_RATE), dtype=np.float32)


class SpeechTextTest(unittest.TestCase):
    def test_spelling(self):
        self.assertEqual(speech.spoken("DL4YM/P"), "De, Ell, Vier, Üpsilon, Emm, Schrägstrich, Pe")
        self.assertEqual(speech.spoken("(", "nato"), "Kilo November")
        self.assertEqual(speech.spoken_words("TNX FER 599"), "tnx. fer. Fünf, Neun, Neun")
        self.assertEqual(speech.spoken("TU 73", "nato"), "Tango, Juni-form. Sieben, Drei")
        self.assertEqual(speech.spoken("*"), "Ess Ka")  # <SK>
        for ch in MORSE_CODE:
            self.assertTrue(speech.spoken(ch), ch)  # jedes Zeichen hat eine Ansage

    def test_resample_keeps_duration(self):
        out = speech.resample(np.ones(22050, dtype=np.float32), 22050)
        self.assertEqual(len(out), SAMPLE_RATE)

    def test_missing_voice_is_reported(self):
        with mock.patch.object(speech, "voice_path", lambda: None):
            reason = speech.Speaker().available()
        if reason is not None:  # ohne Piper steht dort das
            self.assertIn("nicht verfügbar", reason)


class PhraseTest(unittest.TestCase):
    def test_phrases_use_morse_chars_and_charset(self):
        for phrase in words.PHRASES:
            self.assertTrue(all(ch == " " or ch in MORSE_CODE for ch in phrase), phrase)
        found = words.phrases_for_charset(koch.lesson_charset(30))
        self.assertTrue(found)
        allowed = set(koch.lesson_charset(30)) | {" "}
        self.assertTrue(all(set(p) <= allowed for p in found))


class ItemSourceTest(unittest.TestCase):
    def test_kinds_stay_in_charset(self):
        random.seed(1)
        charset = koch.lesson_charset(40)
        for kind in ("chars", "groups", "words", "phrases", "qso"):
            source = ItemSource(kind, charset, group_len=4)
            self.assertIsNone(source.problem(), kind)
            for _ in range(30):
                text, _ = source.next()
                self.assertTrue(set(text.replace(" ", "")) <= set(charset), (kind, text))

    def test_problems_are_explained(self):
        self.assertIn("Wendungen", ItemSource("phrases", "KM").problem())
        self.assertIn("Ziffer", ItemSource("calls", "KMURES").problem())
        self.assertIn("fehlen noch", ItemSource("qso", koch.lesson_charset(20)).problem())

    def test_random_chars_may_repeat(self):
        random.seed(2)
        source = ItemSource("chars", "KM")
        picks = [source.next()[0] for _ in range(200)]
        self.assertTrue(any(a == b for a, b in zip(picks, picks[1:])))  # kein starres K M K M

    def test_words_do_not_repeat_directly(self):
        random.seed(3)
        source = ItemSource("words", koch.lesson_charset(30))
        picks = [source.next()[0] for _ in range(100)]
        self.assertFalse(any(a == b for a, b in zip(picks, picks[1:])))


class Mp3Test(unittest.TestCase):
    def test_writes_mp3(self):
        if mp3.available():
            self.skipTest(mp3.available())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.mp3"
            with mp3.Mp3Writer(path) as writer:
                writer.write(np.zeros(SAMPLE_RATE, dtype=np.float32))
            data = path.read_bytes()
            self.assertGreater(len(data), 1000)
            self.assertTrue(data[:3] == b"ID3" or data[0] == 0xFF)
            self.assertAlmostEqual(writer.seconds, 1.0)


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(stats, "STATS_DIR", Path(self.tmp.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    @staticmethod
    def _chars(**results):
        """Zeichen=(richtig, falsch[, angenommen[, langsam]]) -> per_char wie
        SessionStats (Latenzen: flüssig 0,6 s, langsam 3 s, angenommen 2 s)."""
        out = {}
        for ch, (good, wrong, *rest) in results.items():
            assumed, slow = (rest + [0, 0])[:2]
            fast = good - assumed - slow
            out[ch] = {"good": good, "wrong": wrong, "assumed_latencies": [2.0] * assumed,
                       "latencies": [0.6] * fast + [3.0] * slow + [2.0] * assumed}
        return out

    def test_leitner_boxes(self):
        today = date(2026, 9, 27)
        tomorrow = today + timedelta(days=1)
        data = review.update(self._chars(K=(10, 0), M=(6, 4), U=(2, 0)), promote=True, today=today)
        self.assertEqual((data["K"]["box"], data["K"]["due"]), (0, "2026-09-28"))
        self.assertEqual(data["M"]["due"], "2026-09-28")
        self.assertNotIn("due", data["U"])  # erst 2 Versuche heute
        data = review.update(self._chars(U=(3, 0)), promote=True, today=today)
        self.assertEqual(data["U"]["due"], "2026-09-28")  # Versuche des Tages zusammen
        # Fällig und sicher, aber nur aus Klartext/Wörtern: kein Hochstufen
        data = review.update(self._chars(K=(10, 0)), promote=False, today=tomorrow)
        self.assertEqual(data["K"]["box"], 0)
        # Aus Zufallszeichen: ein Fach weiter (2 Tage), nur einmal am Tag
        data = review.update(self._chars(K=(10, 0)), promote=True, today=tomorrow)
        self.assertEqual((data["K"]["box"], data["K"]["due"]), (1, (tomorrow + timedelta(days=2)).isoformat()))
        data = review.update(self._chars(K=(10, 0)), promote=True, today=tomorrow)
        self.assertEqual(data["K"]["box"], 1)

    def test_slow_or_assumed_is_not_fluent(self):
        day = date(2026, 9, 27)
        data = review.update(self._chars(K=(10, 0, 0, 5), M=(10, 0, 3)), promote=True, today=day)
        self.assertEqual(data["K"]["fluent"], 5)
        self.assertEqual(data["M"]["fluent"], 7)
        review._save({"R": {"box": 3, "due": day.isoformat()}})
        data = review.update(self._chars(R=(10, 0, 0, 2)), promote=True, today=day)  # 80 %: ein Fach zurück
        self.assertEqual(data["R"]["box"], 2)

    def test_small_charset_cannot_promote(self):
        self.assertFalse(review.can_promote("KMUR"))
        self.assertTrue(review.can_promote(koch.lesson_charset(8)))

    def test_due_chars_and_weight(self):
        from morsetrainer.core.weighting import CharPicker
        today = date.today()
        storage_data = {"K": {"box": 2, "due": today.isoformat()}, "M": {"box": 0, "due": "2000-01-01"},
                        "R": {"box": 1, "due": (today + timedelta(days=3)).isoformat()}}
        review._save(storage_data)
        self.assertEqual(review.due_chars(), "MK")  # unteres Fach zuerst
        self.assertEqual(review.next_due()[1], "R")
        self.assertEqual(sorted(review.boxed_chars({**storage_data, "+": {"day": "2026-10-03", "n": 2}})),
                         ["K", "M", "R"])  # noch ohne Fach: nicht gelernt
        with mock.patch.object(stats, "ALL_TIME_FILE", Path(self.tmp.name) / "all_time.json"):
            weights = dict(zip("KMR", CharPicker("KMR", weighted=True).weights()))
        self.assertAlmostEqual(weights["K"], weights["R"] * review.DUE_FACTOR)

    def test_session_updates_review_and_reset_clears_it(self):
        with mock.patch.object(stats, "ALL_TIME_FILE", Path(self.tmp.name) / "all_time.json"), \
                mock.patch.object(stats, "RESET_FILE", Path(self.tmp.name) / "reset.json"):
            session = stats.SessionStats("group", "KM", 20, 600)
            for _ in range(6):
                session.record_char("K", "K", True, 0.5, 20.0)
            session.finalize()
            self.assertIn("K", review.load())
            stats.reset_all_time()
            self.assertEqual(review.load(), {})

    def test_best_box_and_promotion_events(self):
        day = date(2026, 9, 27)
        review._save({"K": {"box": 2, "due": day.isoformat()}, "M": {"box": 3, "due": day.isoformat()}})
        events = []
        data = review.update(self._chars(K=(10, 0), M=(10, 0, 0, 2)), promote=True, today=day, events=events)
        # K steigt erstmals in Fach 3 (box 3); M fällt zurück, behält aber sein bestes Fach.
        self.assertEqual(events, [{"char": "K", "box": 3, "first": True}])
        self.assertEqual((data["K"]["best_box"], data["K"]["best_day"]), (3, day.isoformat()))
        self.assertEqual((data["M"]["box"], data["M"]["best_box"]), (2, 3))
        self.assertEqual(review.best_box(data["M"]), 3)
        # Wieder hochgestuft auf ein schon erreichtes Fach: kein „erstmals“.
        later = date.fromisoformat(data["M"]["due"])
        events = []
        data = review.update(self._chars(M=(10, 0)), promote=True, today=later, events=events)
        self.assertEqual(events, [{"char": "M", "box": 3, "first": False}])
        self.assertNotIn("best_day", data["M"])

    def test_award_box_only_from_fast_sessions(self):
        day = date(2026, 9, 27)
        review._save({"K": {"box": 2, "best_box": 2, "best_day": "2026-09-01", "due": day.isoformat()},
                      "M": {"box": 2, "due": day.isoformat()}})
        data = review.update(self._chars(K=(10, 0), M=(10, 0)), promote=True, today=day, fast=False)
        # Langsam: das Fach steigt, für die Diplome bleibt das bisherige (alter Eintrag: best_box).
        self.assertEqual((data["K"]["box"], review.award_box(data["K"]), data["K"]["award_day"]),
                         (3, 2, "2026-09-01"))
        later = date.fromisoformat(data["M"]["due"])
        data = review.update(self._chars(M=(10, 0)), promote=True, today=later)
        self.assertEqual((review.award_box(data["M"]), data["M"]["award_day"]), (4, later.isoformat()))

    def test_old_entries_without_best_box(self):
        self.assertEqual(review.best_box({"box": 4}), 4)
        self.assertEqual(review.best_box({}), 0)

    def test_session_log_has_conditions_duration_and_events(self):
        with mock.patch.object(stats, "ALL_TIME_FILE", Path(self.tmp.name) / "all_time.json"):
            charset = koch.lesson_charset(8)
            session = stats.SessionStats("group", charset, 20, 600, review_promote=True,
                                         config_extra={"lesson": 8, "band": "light"})
            for _ in range(6):
                session.record_char("K", "K", True, 0.5, 20.0, latency=0.5)
            path = session.finalize({"first_try_correct": 5, "first_try_total": 6})
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual((lines[0]["lesson"], lines[0]["band"]), (8, "light"))
            self.assertEqual(lines[-1]["first_try_correct"], 5)
            self.assertIn("duration_s", lines[-1])
            self.assertEqual(session.review_events, [])  # neues Zeichen: erst morgen hochstufbar

    def test_damaged_entries_are_usable(self):
        review._save({
            "K": {"box": "drei", "best_box": None, "due": "2026-10-01", "day": "2026-10-03", "n": "x",
                  "fluent": 1, "pn": 0, "pfluent": 0, "decided": False},
            "M": {"box": 2, "day": "2026-10-03", "n": 3, "fluent": 3, "pn": 0, "pfluent": 0},  # ohne "decided"
            "R": "kaputt",
        })
        data = review.load()
        self.assertEqual(sorted(data), ["K", "M"])
        self.assertEqual((data["K"]["box"], review.best_box(data["K"])), (0, 0))
        self.assertNotIn("day", data["K"])  # Tageszähler beginnen neu
        self.assertNotIn("day", data["M"])
        per_char = {"K": {"good": 1, "wrong": 0, "latencies": [0.3]}, "M": {"good": 1, "wrong": 0, "latencies": [0.3]}}
        review.update(per_char, today=date(2026, 10, 3))  # kein Fehler


class ListenModeTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.listen = self.mode("Sprechen")
        self.app.charset_var.set(koch.lesson_charset(40))
        self.patches += [mock.patch.object(speech.speaker, "synth", fake_synth),
                         mock.patch.object(speech.speaker, "available", lambda: None),
                         mock.patch.object(speech.speaker, "voice", object())]
        for patch in self.patches[-3:]:
            patch.start()

    def test_item_flow_hides_solution_until_answer(self):
        from morsetrainer.modes import listen_mode
        m = self.listen
        m.content_var.set("Rufzeichen")
        m.count_var.set(2)
        with mock.patch.object(listen_mode.audio, "play") as play:
            m.start()
            self.assertTrue(m.running)
            self.assertIn("Hör zu", m.status_var.get())
            self.assertEqual(m.solution_var.get(), "")
            text = m.current[0]
            m._answer(np.zeros(10, dtype=np.float32), np.zeros(10, dtype=np.float32))
            self.assertEqual(m.solution_var.get(), text)
            self.assertEqual(play.call_count, 2)
            m.stop()
        self.assertFalse(m.running)

    def test_problem_blocks_start(self):
        m = self.listen
        self.app.charset_var.set("KM")
        m.content_var.set("Wendungen")
        m.start()
        self.assertFalse(m.running)
        self.assertIn("Wendungen", m.status_var.get())

    def test_announcement_with_meaning(self):
        m = self.listen
        opts = {"alphabet": "de", "meaning": True, "whole": False, "kind": "words"}
        self.assertEqual(m.announcement("TNX", "thanks – danke", opts), "Te, Enn, Ix. danke")
        opts["meaning"] = False
        self.assertEqual(m.announcement("TNX", "thanks – danke", opts), "Te, Enn, Ix")
        opts["whole"] = True  # als Ganzes: Bedeutung bzw. das Wort selbst
        self.assertEqual(m.announcement("TNX", "thanks – danke", opts), "danke")
        self.assertEqual(m.announcement("NAME", "", opts), "name")
        opts["kind"] = "calls"  # Rufzeichen immer buchstabiert
        self.assertEqual(m.announcement("DL1A", "", opts), "De, Ell, Eins, A")

    def test_export_writes_mp3(self):
        if mp3.available():
            self.skipTest(mp3.available())
        m = self.listen
        m.content_var.set("Wörter")
        m.count_var.set(5)
        opts = m._options()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "uebung.mp3"
            m.cancel_export, m.export_result = False, None
            with mock.patch.object(speech.speaker, "load", lambda: True):
                m._export_worker(path, opts)
            self.assertIn("Gespeichert", m.export_result)
            self.assertGreater(path.stat().st_size, 10000)

    def test_settings_roundtrip(self):
        m = self.listen
        m.content_var.set("Wendungen")
        m.alphabet_var.set("Buchstabieralphabet (Alfa, Bravo)")
        m.pause_var.set(3.5)
        data = m.settings()
        m.content_var.set("Zeichen")
        m.restore_settings(data)
        self.assertEqual(m.content_var.get(), "Wendungen")
        self.assertEqual(data["alphabet"], "nato")
        self.assertEqual(m.pause_var.get(), 3.5)


class ContinuousContentTest(AppTestCase):
    def test_words_come_with_word_gaps_and_no_lesson(self):
        import contextlib
        from morsetrainer.modes import continuous_mode

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        c = self.mode("Kontinuierlich")
        self.app.charset_var.set(koch.lesson_charset(30))
        c.content = "words"
        c.source = ItemSource("words", koch.lesson_charset(30))
        c.wpm, c.freq, c.fw, c.group_len = 20, 600, None, 5
        c.sent_log, c.running, c.deadline = [], True, None
        gaps = []
        real_silence = continuous_mode.silence

        def counting_silence(seconds):
            gaps.append(seconds)
            if len(gaps) == 3:
                c.running = False
            return real_silence(seconds)

        with mock.patch.object(continuous_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())), \
                mock.patch.object(continuous_mode, "silence", counting_silence):
            c._play_session()
        sent = "".join(e["char"] for e in c.sent_log)
        self.assertTrue(sent and set(sent) <= set(koch.lesson_charset(30)))


class ContinuousPhraseGapTest(AppTestCase):
    def test_phrase_has_word_gaps_inside(self):
        import contextlib
        from morsetrainer.modes import continuous_mode

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        class OnePhrase:
            def next(self):
                return "TNX FER CALL", ""

        c = self.mode("Kontinuierlich")
        c.content, c.source = "phrases", OnePhrase()
        c.wpm, c.freq, c.fw, c.group_len = 20, 600, None, 5
        c.sent_log, c.running, c.deadline = [], True, None
        word_gap = continuous_mode.word_gap_extra_seconds(20, None)
        gaps = []
        real_silence = continuous_mode.silence

        def counting_silence(seconds):
            if abs(seconds - word_gap) < 1e-9:
                gaps.append(seconds)
                if len(gaps) == 3:  # 2 in der ersten Wendung, 1 vor der zweiten
                    c.running = False
            return real_silence(seconds)

        with mock.patch.object(continuous_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())), \
                mock.patch.object(continuous_mode, "silence", counting_silence):
            c._play_session()
        self.assertEqual("".join(e["char"] for e in c.sent_log), "TNXFERCALL")  # Leerzeichen nur als Pause


class StatsTabReviewTest(AppTestCase):
    def test_review_text(self):
        today = date(2026, 9, 27)
        text = self.app._review_text({"K": {"box": 0, "due": "2026-09-27"}}, today)
        self.assertIn("Heute fällig (1): K", text)
        text = self.app._review_text({"K": {"box": 0, "due": "2026-09-28"}}, today)
        self.assertIn("morgen", text)
        self.assertIn("Lernkartei", self.app._review_text({}, today))
