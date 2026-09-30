"""Unerwartete Fehler: Fehlerprotokoll, Meldung im Hauptfenster, und dass
Update, MP3-Export und Schließen daran nicht hängen bleiben."""
import http.client
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import app as app_module
from morsetrainer.core import errorlog, practice, speech, stats
from morsetrainer.modes.network_mode import NetworkModeFrame
from morsetrainer.net import update
from tests.test_modes import AppTestCase
from tests.test_update import FakeResponse


class ErrorLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "fehler.log"
        self.patch = mock.patch.object(errorlog, "LOG_FILE", self.log)
        self.patch.start()
        errorlog.take_unseen()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_record_appends_traceback_and_counts(self):
        for _ in range(2):
            try:
                raise RuntimeError("kaputt")
            except RuntimeError:
                self.assertTrue(errorlog.record(*sys.exc_info(), version="9.9"))
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(text.count("Morsetrainer 9.9"), 2)
        self.assertIn("RuntimeError: kaputt", text)
        self.assertEqual(errorlog.take_unseen(), 2)
        self.assertEqual(errorlog.take_unseen(), 0)

    def test_big_log_starts_over(self):
        self.log.write_text("x" * (errorlog.MAX_BYTES + 1), encoding="utf-8")
        errorlog.record(ValueError, ValueError("neu"), None)
        self.assertLess(self.log.stat().st_size, 1000)

    def test_unwritable_log_does_not_raise(self):
        with mock.patch("builtins.open", side_effect=PermissionError("nein")):
            self.assertFalse(errorlog.record(ValueError, ValueError("x"), None))


class AppErrorTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.log_patch = mock.patch.object(errorlog, "LOG_FILE", Path(self.tmp.name) / "fehler.log")
        self.log_patch.start()
        errorlog.take_unseen()

    def tearDown(self):
        self.log_patch.stop()
        super().tearDown()

    def test_callback_error_is_logged_and_shown_once(self):
        with mock.patch.object(app_module.messagebox, "showerror") as shown:
            for _ in range(2):
                try:
                    raise KeyError("x")
                except KeyError:
                    self.app.report_callback_exception(*sys.exc_info())
        self.assertEqual(shown.call_count, 1)
        self.assertIn("fehler.log", shown.call_args[0][1])
        self.assertIn("KeyError", errorlog.LOG_FILE.read_text(encoding="utf-8"))

    def test_close_survives_a_failing_step(self):
        self.app.modes[0].on_close = mock.Mock(side_effect=RuntimeError("Reiter kaputt"))
        later = self.app.modes[-1].on_close = mock.Mock()
        with mock.patch.object(self.root, "destroy") as destroy:
            self.app.on_close()
        later.assert_called_once()
        destroy.assert_called_once()
        self.assertIn("Reiter kaputt", errorlog.LOG_FILE.read_text(encoding="utf-8"))

    def test_export_does_not_hang_on_unexpected_error(self):
        listen = self.mode("Sprechen")
        with mock.patch.object(speech.speaker, "load", side_effect=RuntimeError("Stimme kaputt")):
            with self.assertRaises(RuntimeError):
                listen._export_worker(Path(self.tmp.name) / "x.mp3", {})
        self.assertIn("Stimme kaputt", listen.export_result)


class UpdateNetErrorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name) / "Morsetrainer.exe"
        self.target.write_bytes(b"MZ old")

    def tearDown(self):
        self.tmp.cleanup()

    def test_broken_connection_is_an_update_error(self):
        response = FakeResponse(b"MZ")
        response.read = mock.Mock(side_effect=http.client.IncompleteRead(b"MZ"))
        with mock.patch.object(update.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(update.UpdateError):
                update.download("2.16", self.target, update.WINDOWS_ASSET)
        self.assertEqual([p.name for p in self.target.parent.iterdir()], ["Morsetrainer.exe"])
        with mock.patch.object(update.urllib.request, "urlopen", side_effect=http.client.BadStatusLine("x")):
            with self.assertRaises(update.UpdateError):
                update.latest_version()


class SmallRobustnessTest(unittest.TestCase):
    def test_practice_time_without_stats_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "stats"
            blocker.write_text("keine Mappe")  # mkdir scheitert
            with mock.patch.object(stats, "STATS_DIR", blocker), \
                    mock.patch.object(practice, "_path", lambda: blocker / "practice.json"):
                practice.add(60)  # kein Fehler

    def test_item_with_text_that_is_no_string_is_ignored(self):
        for text in (5, None, ["KMR"], {"a": 1}):
            self.assertIsNone(NetworkModeFrame._on_item(object(), {"type": "item", "n": 1, "text": text, "wpm": 20}))


if __name__ == "__main__":
    unittest.main()
