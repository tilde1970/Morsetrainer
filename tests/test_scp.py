"""Rufzeichenliste laden: Prüfung der geladenen Datei, alte Liste bleibt bei
Fehlern, Knopf im Rufzeichen-Modus."""
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.modes import callsign_mode
from morsetrainer.net import scp
from tests.test_modes import AppTestCase
from tests.test_update import FakeResponse

LIST = ("# Super Check Partial\n"
        + "".join(f"DL{n}ABC\n" for n in range(scp.MIN_CALLS + 5))).encode("ascii")


def answer(data: bytes, length=None):
    return mock.patch.object(scp.urllib.request, "urlopen",
                             lambda request, timeout=None: FakeResponse(data, length))


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "callsigns.scp"
        self.target.write_text("ALT\n")

    def assert_old_list_kept(self):
        self.assertEqual(self.target.read_text(), "ALT\n")
        self.assertEqual([p.name for p in self.target.parent.iterdir()], ["callsigns.scp"])

    def test_count_skips_comments_and_garbage(self):
        self.assertEqual(scp.count_calls(b"# x\n!y\n\nDL4YM\nk1ar/p\n<html>\n"), 2)

    def test_download_replaces_list(self):
        with answer(LIST):
            self.assertEqual(scp.download(self.target), scp.MIN_CALLS + 5)
        self.assertEqual(self.target.read_bytes(), LIST)
        self.assertFalse(self.target.with_name("callsigns.scp.new").exists())

    def test_error_page_keeps_old_list(self):
        with answer(b"<html><body>Not here</body></html>"), self.assertRaises(scp.ScpError):
            scp.download(self.target)
        self.assert_old_list_kept()

    def test_incomplete_download_keeps_old_list(self):
        with answer(LIST, len(LIST) + 100), self.assertRaises(scp.ScpError):
            scp.download(self.target)
        self.assert_old_list_kept()

    def test_too_large_keeps_old_list(self):
        with mock.patch.object(scp, "MAX_BYTES", 1000), answer(LIST), \
                self.assertRaises(scp.ScpError):
            scp.download(self.target)
        self.assert_old_list_kept()

    def test_network_error_becomes_scp_error(self):
        def fail(request, timeout=None):
            raise urllib.error.URLError("Name or service not known")
        with mock.patch.object(scp.urllib.request, "urlopen", fail), \
                self.assertRaisesRegex(scp.ScpError, "Name or service"):
            scp.download(self.target)
        self.assert_old_list_kept()

    def test_missing_folder_is_created(self):
        target = Path(self.tmp.name) / "neu" / "callsigns.scp"
        with answer(LIST):
            scp.download(target)
        self.assertEqual(target.read_bytes(), LIST)


class ButtonTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.file = Path(self.tmp.name) / "callsigns.scp"
        patch = mock.patch.object(callsign_mode, "CALLSIGN_FILE", self.file)
        patch.start()
        self.addCleanup(patch.stop)
        self.mode = next(m for m in self.app.modes if isinstance(m, callsign_mode.CallsignModeFrame))

    def wait_for_download(self):
        deadline = time.monotonic() + 5
        while self.mode.scp_status is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertIsNone(self.mode.scp_status)

    def test_load_reads_new_list(self):
        def download(target):
            target.write_text("DL4YM\nDK1AB\nDJ2CD\n")
            return 3
        with mock.patch.object(scp, "download", download):
            self.mode._download_list()
            self.assertIn("disabled", self.mode.scp_button.state())
            self.wait_for_download()
        self.assertEqual(sorted(self.mode.all_calls), ["DJ2CD", "DK1AB", "DL4YM"])
        self.assertNotIn("disabled", self.mode.scp_button.state())
        self.assertEqual(self.mode.scp_button.cget("text"), "Rufzeichenliste aktualisieren")
        self.assertIn("geladen: 3", self.mode.status_var.get())

    def test_error_is_reported_and_button_comes_back(self):
        old = list(self.mode.all_calls)

        def download(target):
            raise scp.ScpError("Download unvollständig")
        with mock.patch.object(scp, "download", download):
            self.mode._download_list()
            self.wait_for_download()
        self.assertEqual(self.mode.all_calls, old)
        self.assertNotIn("disabled", self.mode.scp_button.state())
        self.assertIn("Download unvollständig", self.mode.status_var.get())

    def test_not_during_exercise(self):
        self.mode.running = True
        try:
            with mock.patch.object(scp, "download") as download:
                self.mode._download_list()
        finally:
            self.mode.running = False
        download.assert_not_called()
        self.assertIsNone(self.mode.scp_status)
        self.assertIn("nach der Übung", self.mode.status_var.get())


if __name__ == "__main__":
    unittest.main()
