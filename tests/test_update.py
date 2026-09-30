"""Updates: Versionsvergleich, Download und Austausch des Programms,
Updateprüfung beim Start (auch ohne Internet)."""
import io
import json
import tempfile
import time
import tkinter as tk
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.net import update
from morsetrainer.widgets import updater as updater_module
from tests.test_modes import AppTestCase


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, length=None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if length is None else length)}


class VersionTest(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertEqual(update.parse_version("2.15"), (2, 15))
        self.assertEqual(update.parse_version("2.15.1"), (2, 15, 1))
        for bad in ("", "v2.15", "2", "2.x", None, 215, "2.15; rm -rf"):
            self.assertIsNone(update.parse_version(bad))
        self.assertTrue(update.is_newer("2.16", "2.15"))
        self.assertTrue(update.is_newer("2.15.1", "2.15"))
        self.assertTrue(update.is_newer("2.100", "2.99"))  # nicht als Text vergleichen
        self.assertFalse(update.is_newer("2.15", "2.15"))
        self.assertFalse(update.is_newer("2.14", "2.15"))
        self.assertFalse(update.is_newer(None, "2.15"))
        self.assertFalse(update.is_newer("2.16", None))

    def test_latest_version(self):
        answer = FakeResponse(json.dumps({"tag_name": "v2.16"}).encode())
        with mock.patch.object(update.urllib.request, "urlopen", return_value=answer) as urlopen:
            self.assertEqual(update.latest_version(), "2.16")
        self.assertIn("api.github.com/repos/tilde1970/Morsetrainer/releases/latest", urlopen.call_args[0][0].full_url)
        self.assertEqual(urlopen.call_args[1]["timeout"], update.CHECK_TIMEOUT_S)

    def test_latest_version_without_internet(self):
        for problem in (urllib.error.URLError("no route"), TimeoutError(), OSError("offline")):
            with mock.patch.object(update.urllib.request, "urlopen", side_effect=problem):
                with self.assertRaises(update.UpdateError):
                    update.latest_version()
        for body in (b"<html>", json.dumps({"tag_name": "nightly"}).encode(), b"[]"):
            with mock.patch.object(update.urllib.request, "urlopen", return_value=FakeResponse(body)):
                with self.assertRaises(update.UpdateError):
                    update.latest_version()


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.target = self.dir / "Morsetrainer.exe"
        self.target.write_bytes(b"MZ old")
        patch = mock.patch.object(update, "MIN_SIZE", 10)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def fetch(self, data, length=None, asset=update.WINDOWS_ASSET):
        with mock.patch.object(update.urllib.request, "urlopen", return_value=FakeResponse(data, length)) as urlopen:
            progress = []
            part = update.download("2.16", self.target, asset, lambda done, total: progress.append((done, total)))
        self.assertEqual(urlopen.call_args[0][0].full_url,
                         f"https://github.com/tilde1970/Morsetrainer/releases/download/v2.16/{asset}")
        self.assertEqual(progress[-1], (len(data), len(data)))
        return part

    def test_windows_renames_the_running_exe(self):
        part = self.fetch(b"MZ" + b"x" * 100)
        self.assertEqual(part.name, "Morsetrainer.exe.new")
        update.install(part, self.target, windows=True)
        self.assertTrue(self.target.read_bytes().startswith(b"MZx"))
        old = self.dir / "Morsetrainer.old.exe"
        self.assertEqual(old.read_bytes(), b"MZ old")
        with mock.patch.object(update, "installed", return_value=(self.target, update.WINDOWS_ASSET)):
            update.cleanup()  # beim nächsten Start
        self.assertFalse(old.exists())
        self.assertTrue(self.target.exists())

    def test_appimage_is_replaced_and_executable(self):
        self.target.unlink()
        self.target = self.dir / "Morsetrainer-x86_64.AppImage"
        self.target.write_bytes(b"\x7fELF old")
        part = self.fetch(b"\x7fELF" + b"x" * 100, asset=update.APPIMAGE_ASSET)
        update.install(part, self.target, windows=False)
        self.assertTrue(self.target.read_bytes().startswith(b"\x7fELFx"))
        self.assertTrue(self.target.stat().st_mode & 0o100)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), [self.target.name])

    def test_broken_downloads_leave_the_program_alone(self):
        cases = [
            (b"<html>not found</html>" * 10, None),  # keine exe
            (b"MZ" + b"x" * 100, 5000),                # abgebrochen
            (b"MZ", None),                             # zu klein
        ]
        for data, length in cases:
            with mock.patch.object(update.urllib.request, "urlopen", return_value=FakeResponse(data, length)):
                with self.assertRaises(update.UpdateError):
                    update.download("2.16", self.target, update.WINDOWS_ASSET)
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with mock.patch.object(update.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(update.UpdateError):
                update.download("2.16", self.target, update.WINDOWS_ASSET)
        with self.assertRaises(update.UpdateError):
            update.download("../evil", self.target, update.WINDOWS_ASSET)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["Morsetrainer.exe"])
        self.assertEqual(self.target.read_bytes(), b"MZ old")

    def test_relaunch_does_not_inherit_the_packed_environment(self):
        env = {"APPIMAGE": "/old.AppImage", "APPDIR": "/tmp/.mount", "LD_LIBRARY_PATH": "/tmp/.mount/lib",
               "LD_LIBRARY_PATH_ORIG": "/usr/local/lib", "HOME": "/home/x"}
        with mock.patch.dict(update.os.environ, env, clear=True), \
                mock.patch.object(update.subprocess, "Popen") as popen:
            update.relaunch(self.target, ["--join", "1234"])
        args, kwargs = popen.call_args
        self.assertEqual(args[0], [str(self.target), "--join", "1234"])
        self.assertEqual(kwargs["env"], {"HOME": "/home/x", "LD_LIBRARY_PATH": "/usr/local/lib",
                                         "PYINSTALLER_RESET_ENVIRONMENT": "1"})

    def test_nothing_to_replace_when_run_from_source(self):
        self.assertIsNone(update.installed())


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()
        self.restarts = []
        self.updater = updater_module.Updater(self.root, "2.15", self.restarts.append)
        self.shown = []

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def offer(self, version="2.16", answer=True, installable=True, **kwargs):
        target = (Path("/x/Morsetrainer.exe"), update.WINDOWS_ASSET)
        with mock.patch.object(updater_module.Updater, "can_install", return_value=installable), \
                mock.patch.object(update, "installed", return_value=target), \
                mock.patch.object(updater_module.messagebox, "askyesno", return_value=answer) as asked:
            outcome = self.updater.offer(version, "Neu.", self.shown.append, **kwargs)
        return outcome, asked.call_count

    def test_download_install_and_restart(self):
        with mock.patch.object(update, "download", return_value=Path("/x/new")) as download, \
                mock.patch.object(update, "install") as install:
            outcome, asked = self.offer(prepare=lambda: ["--join", "1234"])
            self.assertEqual((outcome, asked), (updater_module.STARTED, 1))
            self.assertTrue(self.wait(lambda: self.restarts))
        self.assertEqual(download.call_args[0][:3], ("2.16", Path("/x/Morsetrainer.exe"), update.WINDOWS_ASSET))
        install.assert_called_once_with(Path("/x/new"), Path("/x/Morsetrainer.exe"))
        self.assertEqual(self.restarts, [["--join", "1234"]])
        self.assertIn("installiert", self.shown[-1])

    def test_failed_download_says_where_to_get_it(self):
        failed = []
        with mock.patch.object(update, "download", side_effect=update.UpdateError("offline")):
            self.offer(failed=lambda: failed.append(True))
            self.assertTrue(self.wait(lambda: failed))
        self.assertEqual(self.restarts, [])
        self.assertIn("offline", self.shown[-1])
        self.assertIn("releases/tag/v2.16", self.shown[-1])
        self.assertFalse(self.updater.busy)

    def test_ask_only_once_and_only_for_newer(self):
        self.assertEqual(self.offer("2.15"), (None, 0))
        self.assertEqual(self.offer("2.14"), (None, 0))
        self.assertEqual(self.offer("2.16", answer=False), (updater_module.DECLINED, 1))
        self.assertEqual(self.offer("2.16"), (None, 0))  # nicht gleich noch einmal
        self.assertEqual(self.restarts, [])

    def test_from_source_only_a_hint(self):
        self.assertEqual(self.offer(installable=False), (updater_module.HINT, 0))
        self.assertIn("releases/tag/v2.16", self.shown[-1])

    def wait(self, condition, timeout=3.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.root.update()
            if condition():
                return True
            time.sleep(0.02)
        return False


class StartupCheckTest(AppTestCase):
    def check(self, latest, outcome=None):
        side_effect = update.UpdateError("offline") if latest is None else None
        with mock.patch.object(update, "latest_version", return_value=latest, side_effect=side_effect), \
                mock.patch.object(self.app.updater, "offer", return_value=outcome) as offer:
            self.app.update_checked = False
            self.app.check_for_update()
            end = time.monotonic() + 3
            while not self.app.update_checked and time.monotonic() < end:
                self.root.update()
                time.sleep(0.02)
        self.assertTrue(self.app.update_checked)
        return offer

    def test_offline_stays_quiet(self):
        offer = self.check(None)
        offer.assert_not_called()
        self.assertEqual(self.app.update_var.get(), "")

    def test_same_version_stays_quiet(self):
        self.check(app_module_version()).assert_not_called()

    def test_newer_release_is_offered_and_a_no_is_remembered(self):
        offer = self.check("99.0", outcome=updater_module.DECLINED)
        self.assertEqual(offer.call_args[0][0], "99.0")
        self.assertEqual(self.app.update_declined, "99.0")
        self.assertIn("99.0 verfügbar", self.app.update_var.get())
        self.app._save_state()
        self.assertEqual(self.app._load_state()["update_declined"], "99.0")
        self.check("99.0").assert_not_called()  # abgelehnt: nur der Hinweis unten

    def test_no_question_during_a_running_exercise(self):
        self.app.running_mode = True
        self.check("99.0").assert_not_called()
        self.assertIn("99.0 verfügbar", self.app.update_var.get())


    def test_join_after_restart_opens_the_network_tab(self):
        network = self.mode("Netzwerk")
        with mock.patch.object(network, "rejoin") as rejoin:
            self.app.join_network("1234")
        rejoin.assert_called_once_with("1234")
        self.assertIs(self.app._active_mode(), network)

    def test_restart_saves_first(self):
        with mock.patch.object(self.app, "on_close") as close:
            self.app.restart_for_update(("--join", "1234"))
        close.assert_called_once()
        self.assertEqual(self.app.restart_args, ["--join", "1234"])


def app_module_version():
    from morsetrainer import app
    return app.__version__


if __name__ == "__main__":
    unittest.main()
