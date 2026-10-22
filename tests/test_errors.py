"""Unerwartete Fehler: Fehlerprotokoll, Meldung im Hauptfenster, und dass
Update, MP3-Export und Schließen daran nicht hängen bleiben."""
import http.client
import sys
import tempfile
import time
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

    def test_unwritable_log_is_reported_with_the_error(self):
        broken = Path(self.tmp.name) / "fehlt" / "fehler.log"  # Ordner gibt es nicht
        with mock.patch.object(errorlog, "LOG_FILE", broken):
            try:
                raise RuntimeError("kaputt")
            except RuntimeError:
                self.assertFalse(errorlog.record(*sys.exc_info(), version="9.9"))
            self.assertIn("FileNotFoundError", errorlog.unwritten)
        self.assertTrue(self._record_ok())
        self.assertIsNone(errorlog.unwritten)

    def _record_ok(self):
        try:
            raise RuntimeError("gut")
        except RuntimeError:
            return errorlog.record(*sys.exc_info(), version="9.9")

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
                mock.patch.object(app_module.dialog, "showinfo") as shown:
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
                mock.patch.object(app_module.dialog, "showwarning") as warned:
            self.app._save_state_or_warn()
        self.assertIn("schreibgeschützt", warned.call_args.args[1])

    def test_newer_database_is_announced_at_start(self):
        with mock.patch.object(app_module.db, "problem", return_value="too_new"), \
                mock.patch.object(app_module.dialog, "showwarning") as warned:
            self.app._warn_if_database_too_new()
        warned.assert_called_once()
        self.assertIn("neueren Version", warned.call_args.args[1])
        with mock.patch.object(app_module.db, "problem", return_value=None), \
                mock.patch.object(app_module.dialog, "showwarning") as warned:
            self.app._warn_if_database_too_new()
        warned.assert_not_called()

    def test_set_aside_and_failed_migration_are_announced_too(self):
        for kind, word in (("aside", "beiseitegelegt"), ("migration", "aktualisieren")):
            with mock.patch.object(app_module.db, "problem", return_value=kind), \
                    mock.patch.object(app_module.dialog, "showwarning") as warned:
                self.app._warn_if_database_too_new()
            self.assertIn(word, warned.call_args.args[1])
            self.assertTrue(warned.call_args.kwargs["always_speak"])

    def test_failed_auto_backup_is_announced_at_start(self):
        self.app.auto_backup_var.set(True)
        with mock.patch.object(app_module.db, "problem", return_value=None), \
                mock.patch.object(app_module.backup, "auto_backup_failure", return_value="Platte voll"), \
                mock.patch.object(app_module.dialog, "showwarning") as warned:
            self.app._warn_if_database_too_new()
        self.assertIn("Platte voll", warned.call_args.args[1])
        self.assertTrue(warned.call_args.kwargs["always_speak"])
        self.app.auto_backup_var.set(False)  # abgeschaltet: kein Hinweis
        with mock.patch.object(app_module.db, "problem", return_value=None), \
                mock.patch.object(app_module.backup, "auto_backup_failure", return_value="Platte voll"), \
                mock.patch.object(app_module.dialog, "showwarning") as warned:
            self.app._warn_if_database_too_new()
        warned.assert_not_called()

    def test_whats_new_and_awards_wait_for_the_start_notice(self):
        self.app.saved_state = {"seen_version": "2.0"}
        self.app.start_notice_open = True
        with mock.patch.object(app_module.dialog, "showinfo") as shown, \
                mock.patch.object(self.app, "_check_awards") as checked, \
                mock.patch.object(self.app.root, "after") as later:
            self.app.show_whats_new()
            self.app._check_awards_at_start()
        shown.assert_not_called()
        checked.assert_not_called()
        self.assertEqual(later.call_count, 2)  # beide planen sich neu
        self.app.start_notice_open = False
        with mock.patch.object(app_module.dialog, "showinfo") as shown:
            self.app.show_whats_new()
        shown.assert_called_once()

    def test_start_notices_come_one_after_the_other_in_real_windows(self):
        # Echte Fenster statt Attrappen: Der Datenbank-Hinweis ist modal und lässt
        # die Ereignisschleife weiterlaufen; „Neu in Version“ und die Diplome
        # dürfen erst nach seinem Schließen kommen, nie darüber.
        self.app.saved_state = {"seen_version": "2.0"}
        opened, closed = [], {}
        real_init = app_module.dialog.MessageDialog.__init__

        def spy(window, parent, title, *args, **kwargs):
            real_init(window, parent, title, *args, **kwargs)
            opened.append((title, time.monotonic(), window))

        def close_old():
            for title, since, window in opened:
                if title not in closed and time.monotonic() - since > 0.15:
                    closed[title] = time.monotonic()
                    window.close()
            if len(closed) < 2:
                self.app.root.after(20, close_old)

        awards_at = []
        with mock.patch.object(app_module, "UPDATE_POLL_MS", 20), \
                mock.patch.object(app_module.db, "problem", return_value="aside"), \
                mock.patch.object(app_module.dialog.MessageDialog, "__init__", spy), \
                mock.patch.object(self.app, "_check_awards", side_effect=lambda: awards_at.append(time.monotonic())), \
                mock.patch.object(self.app, "show_pending_seals"):
            root = self.app.root
            root.after(0, self.app._warn_if_database_too_new)
            root.after(0, self.app.show_whats_new)
            root.after(0, self.app._check_awards_at_start)
            root.after(20, close_old)
            end = time.monotonic() + 5
            while time.monotonic() < end and not (len(closed) == 2 and awards_at):
                root.update()
                time.sleep(0.01)
        titles = [title for title, _, _ in opened]
        self.assertEqual(len(titles), 2, titles)
        self.assertIn("beiseitegelegt", app_module.tr(app_module.DATABASE_PROBLEMS["aside"]))
        self.assertEqual(titles[0], app_module.tr(app_module.DATABASE_PROBLEM_TITLES["aside"]))
        self.assertTrue(titles[1].startswith("Neu in Version"), titles)
        self.assertLessEqual(closed[titles[0]], opened[1][1])  # erst nach dem Schließen
        self.assertTrue(awards_at, "Diplome nie geprüft")
        self.assertGreaterEqual(awards_at[0], closed[titles[0]])

    def test_wrongly_typed_saved_settings_do_not_break_the_start(self):
        # window_state.json kann beliebiges JSON enthalten (von Hand bearbeitet, andere Version).
        from morsetrainer.core import band
        bad_values = ([], {}, [1], {"a": 1}, None, 7, 1.5, True, "unbekannt")
        for mode in self.app.modes:
            if not hasattr(mode, "settings"):
                continue
            for key in mode.settings():
                for bad in bad_values:
                    try:
                        mode.restore_settings({key: bad})
                    except Exception as exc:  # noqa: BLE001
                        self.fail(f"{type(mode).__name__}: {key}={bad!r} -> {exc!r}")
        for bad in bad_values:
            band.clean_spec({"levels": bad, "qrm_offset": bad, "filter": bad, "seed": bad, "gain": bad})

    def test_error_loops_keep_running_after_an_exception(self):
        app = self.app
        with mock.patch.object(app, "_update_practice", side_effect=RuntimeError("x")), \
                mock.patch.object(app.root, "after") as later:
            with self.assertRaises(RuntimeError):
                app._practice_tick()
        later.assert_called_once()
        app.error_shown = False
        with mock.patch.object(errorlog, "take_unseen", return_value=1), \
                mock.patch.object(app_module.dialog, "showerror", side_effect=RuntimeError("x")), \
                mock.patch.object(app.root, "after") as later:
            with self.assertRaises(RuntimeError):
                app._check_errors()
        later.assert_called_once()
        app.error_shown = False

    def test_error_dialog_names_the_error_when_the_log_cannot_be_written(self):
        app = self.app
        self.addCleanup(setattr, errorlog, "unwritten", None)
        errorlog.unwritten = "PermissionError: [Errno 13] Permission denied"
        app.error_shown = False
        with mock.patch.object(errorlog, "take_unseen", return_value=1), \
                mock.patch.object(app_module.dialog, "showerror") as shown:
            app._check_errors(poll=False)
        text = shown.call_args.args[1]
        self.assertIn("PermissionError", text)
        self.assertNotIn("Einzelheiten stehen", text)

    def test_failed_mp3_export_leaves_no_partial_file(self):
        from morsetrainer.core import mp3
        listen = self.mode("Sprechen")
        path = Path(self.tmp.name) / "uebung.mp3"

        class Failing:
            def __init__(self, target):
                Path(target).write_bytes(b"halb")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def write(self, samples):
                raise OSError("Platte voll")
        opts = {"wpm": 20, "freq": 600, "fw": None, "count": 1, "source": None}
        with mock.patch.object(mp3, "Mp3Writer", Failing), \
                mock.patch.object(type(listen), "speaker", mock.PropertyMock(return_value=mock.Mock(error=None))):
            listen._export(path, opts)
        self.assertEqual(listen.export_result, "Platte voll")
        self.assertFalse(path.exists())

    def test_old_tick_of_the_continuous_mode_ends(self):
        cont = self.mode("Kontinuierlich")
        cont.running, cont.session_id = True, 2
        self.addCleanup(setattr, cont, "running", False)
        with mock.patch.object(cont.root, "after") as later:
            cont._tick(1)
        later.assert_not_called()

    def test_idle_stream_is_reopened(self):
        from morsetrainer.core import audio
        old, new = mock.Mock(active=False), mock.Mock(active=True)
        self.addCleanup(setattr, audio, "_keepalive", audio._keepalive)
        audio._keepalive = old
        with mock.patch.object(audio.sd, "OutputStream", return_value=new):
            audio.keep_awake()
        self.assertIs(audio._keepalive, new)
        old.close.assert_called_once()

    def test_callback_error_is_logged_and_shown_once(self):
        with mock.patch.object(app_module.dialog, "showerror") as shown:
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

    def test_close_writes_the_database_back_before_a_hard_exit(self):
        with mock.patch.object(app_module.db, "close") as closed, mock.patch.object(self.root, "destroy"):
            self.app.on_close()
        closed.assert_called_once()

    def test_close_makes_the_weekly_backup_only_when_wanted(self):
        for wanted, calls in ((True, 1), (False, 0)):
            self.app.auto_backup_var.set(wanted)
            with mock.patch.object(app_module.backup, "auto_backup") as made, \
                    mock.patch.object(self.root, "destroy"):
                self.app.on_close()
            self.assertEqual(made.call_count, calls)

    def test_failing_backup_does_not_stop_closing(self):
        self.app.auto_backup_var.set(True)
        with mock.patch.object(app_module.backup, "auto_backup", side_effect=OSError("Platte voll")), \
                mock.patch.object(self.root, "destroy") as destroy:
            self.app.on_close()
        destroy.assert_called_once()
        self.assertIn("Platte voll", errorlog.LOG_FILE.read_text(encoding="utf-8"))

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
