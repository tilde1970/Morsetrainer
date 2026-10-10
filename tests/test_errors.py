"""Unerwartete Fehler: Fehlerprotokoll, Meldung im Hauptfenster, und dass
Update, MP3-Export und Schließen daran nicht hängen bleiben."""
import http.client
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

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

    def test_no_window_is_reported_on_the_console(self):
        import io
        console = io.StringIO()
        with mock.patch.object(app_module.tk, "Tk", side_effect=app_module.tk.TclError("no display name")), \
                mock.patch.object(app_module.update, "cleanup"), mock.patch.object(app_module.migration, "run"), \
                mock.patch.object(sys, "__stderr__", console), mock.patch.object(sys, "excepthook"):
            with self.assertRaises(SystemExit):
                app_module.main()
        self.assertIn("kein Fenster öffnen: no display name", console.getvalue())
        self.assertIn(str(self.log), console.getvalue())
        self.assertIn("TclError", self.log.read_text(encoding="utf-8"))


class AppErrorTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.log_patch = mock.patch.object(errorlog, "LOG_FILE", Path(self.tmp.name) / "fehler.log")
        self.log_patch.start()
        errorlog.take_unseen()

    def tearDown(self):
        self.log_patch.stop()
        super().tearDown()

    def test_whats_new_once_after_an_update(self):
        with mock.patch.object(app_module, "WHATS_NEW", {"2.10": "alt", "9.0": "Zukunft", "2.39": "Reiter neu"}), \
                mock.patch.object(app_module, "__version__", "2.39"), \
                mock.patch.object(app_module.messagebox, "showinfo") as shown:
            self.app.saved_state = {"seen_version": "2.20"}
            self.app.show_whats_new()
            self.assertEqual(shown.call_args.args[1], "Reiter neu")  # nur Neues bis zur eigenen Version
            shown.reset_mock()
            self.app.saved_state = {"seen_version": "2.39"}  # schon gesehen
            self.app.show_whats_new()
            self.app.saved_state = {}  # frische Installation
            self.app.show_whats_new()
            shown.assert_not_called()

    def test_settings_that_cannot_be_saved_are_reported(self):
        with mock.patch.object(app_module.storage, "write_json_atomic", side_effect=PermissionError("schreibgeschützt")), \
                mock.patch.object(app_module.messagebox, "showwarning") as warned:
            self.app._save_state_or_warn()
        self.assertIn("schreibgeschützt", warned.call_args.args[1])

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

    def test_export_after_shutdown_writes_nothing(self):
        listen = self.mode("Sprechen")
        path = Path(self.tmp.name) / "x.mp3"
        self.addCleanup(setattr, speech, "_closing", False)
        self.assertTrue(speech.shut_down(0))
        listen._export_worker(path, {})
        self.assertFalse(path.exists())
        self.assertIn("abgebrochen", listen.export_result)


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
            with mock.patch.object(stats, "STATS_DIR", blocker):
                practice.add(60)  # kein Fehler

    def test_item_with_text_that_is_no_string_is_ignored(self):
        for text in (5, None, ["KMR"], {"a": 1}):
            self.assertIsNone(NetworkModeFrame._on_item(object(), {"type": "item", "n": 1, "text": text, "wpm": 20}))



class SpeechShutdownTest(unittest.TestCase):
    """Das Programmende wartet auf laufende Sprachsynthese; ein Python-Ende
    mitten in onnxruntime bricht den Prozess sonst hart ab."""

    def setUp(self):
        self.addCleanup(setattr, speech, "_closing", False)

    def test_waits_for_running_synthesis_and_refuses_new(self):
        started, release = threading.Event(), threading.Event()

        class Voice:
            config = SimpleNamespace(sample_rate=speech.SAMPLE_RATE)

            def synthesize(self, text):
                started.set()
                release.wait(5)
                return [SimpleNamespace(audio_float_array=np.ones(10, dtype=np.float32))]

        speaker = speech.Speaker()
        speaker.voice = Voice()
        thread = threading.Thread(target=speaker.synth, args=("A",), daemon=True)
        thread.start()
        self.assertTrue(started.wait(5))
        self.assertFalse(speech.shut_down(0.1))  # rechnet noch
        self.assertEqual(len(speaker.synth("B")), 0)  # nichts Neues mehr
        release.set()
        thread.join(5)
        self.assertTrue(speech.shut_down(0.1))

    def test_no_voice_is_loaded_after_shutdown(self):
        speaker = speech.Speaker()
        speech.shut_down(0)
        with mock.patch.object(speaker, "available", return_value=None):
            self.assertFalse(speaker.load())
        self.assertIsNone(speaker.voice)
        self.assertIsNone(speaker.error)


class AudioLockTest(unittest.TestCase):
    """Öffnen und Schließen von Strömen nur unter der gemeinsamen Sperre
    (PortAudio ist dabei nicht threadsicher)."""

    def test_stream_opens_and_closes_under_the_lock(self):
        from morsetrainer.core import audio
        seen = []

        class Stream:
            def __init__(self, **kwargs):
                seen.append(("open", audio._lock._is_owned()))

            def start(self):
                pass

            def stop(self):
                seen.append(("stop", audio._lock._is_owned()))

            def close(self):
                seen.append(("close", audio._lock._is_owned()))

            def write(self, block):
                seen.append(("write", audio._lock._is_owned()))

        with mock.patch.object(audio.sd, "OutputStream", Stream, create=True):
            with audio.output_stream() as stream:
                stream.write(b"")
        self.assertEqual(seen, [("open", True), ("write", False), ("stop", False), ("close", True)])

    def test_known_errors_say_what_to_do(self):
        from morsetrainer.core import audio
        busy = audio.describe(OSError("Error opening OutputStream: Device unavailable [PaErrorCode -9985]"))
        self.assertIn("belegt", busy)
        self.assertIn("PaErrorCode -9985", busy)  # roher Text für Fehlerberichte
        self.assertIn("kein Gerät", audio.describe(OSError("kein Gerät")))
        self.assertIn("Kein Audiogerät gefunden", audio.describe(OSError("No Default Output Device", -9996)))

    def test_lost_device_is_retried_with_fresh_devices(self):
        from morsetrainer.core import audio
        calls = []

        def play(*args, **kwargs):
            calls.append("play")
            if len(calls) == 1:
                raise OSError("Device unavailable", -9986)
        with mock.patch.object(audio.sd, "play", play), \
                mock.patch.object(audio.sd, "_terminate", lambda: calls.append("terminate"), create=True), \
                mock.patch.object(audio.sd, "_initialize", lambda: calls.append("initialize"), create=True):
            audio.play([0.0])
        self.assertEqual(calls, ["play", "terminate", "initialize", "play"])
        with mock.patch.object(audio.sd, "play", side_effect=OSError("busy", -9985)), \
                mock.patch.object(audio.sd, "_terminate", create=True) as terminate:
            with self.assertRaises(audio.AudioError):
                audio.play([0.0])
        terminate.assert_not_called()  # belegt: kein Neustart, das hilft nicht

    def test_play_and_stop_use_the_lock(self):
        from morsetrainer.core import audio
        owned = []
        with mock.patch.object(audio.sd, "play", lambda *a, **k: owned.append(audio._lock._is_owned())), \
                mock.patch.object(audio.sd, "stop", lambda *a, **k: owned.append(audio._lock._is_owned())):
            audio.play_quietly([0.0])
            audio.stop()
        self.assertEqual(owned, [True, True])


if __name__ == "__main__":
    unittest.main()
