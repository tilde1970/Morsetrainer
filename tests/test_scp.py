"""Rufzeichenliste laden: Prüfung der geladenen Datei, alte Liste bleibt bei
Fehlern, Knopf im Rufzeichen-Modus."""
import os
import socket
import ssl
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.modes import callsign_mode
from morsetrainer.net import certs, scp
from tests.test_modes import AppTestCase
from tests.test_update import FakeResponse

def scp_list(calls: int) -> bytes:
    return ("# Super Check Partial\n" + "".join(f"DL{n}ABC\n" for n in range(calls))).encode("ascii")


LIST = scp_list(scp.MIN_CALLS + 5)


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

    def assert_fails(self, kind, code=None):
        with self.assertRaises(scp.ScpError) as caught:
            scp.download(self.target)
        self.assertEqual((caught.exception.kind, caught.exception.code), (kind, code))
        self.assert_old_list_kept()
        return caught.exception

    def test_error_page_keeps_old_list(self):
        with answer(b"<html><body>Not here</body></html>"):
            self.assert_fails(scp.NOT_A_LIST)

    def test_min_calls_is_the_limit(self):
        with answer(scp_list(scp.MIN_CALLS - 1)):
            self.assert_fails(scp.NOT_A_LIST)
        with answer(scp_list(scp.MIN_CALLS)):
            self.assertEqual(scp.download(self.target), scp.MIN_CALLS)

    def test_incomplete_download_keeps_old_list(self):
        with answer(LIST, len(LIST) + 100):
            self.assert_fails(scp.INCOMPLETE)

    def test_too_large_keeps_old_list(self):
        with mock.patch.object(scp, "MAX_BYTES", len(LIST) - 1), answer(LIST):
            self.assert_fails(scp.TOO_LARGE)

    def test_network_errors_get_a_kind(self):
        cases = [
            (urllib.error.URLError(socket.gaierror(-3, "Temporary failure in name resolution")), scp.OFFLINE, None),
            (urllib.error.URLError(OSError("Tunnel connection failed: 407 Proxy Authentication Required")),
             scp.OFFLINE, None),
            (urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed")),
             scp.CERTIFICATE, None),
            (urllib.error.URLError(TimeoutError("timed out")), scp.TIMEOUT, None),
            (TimeoutError("timed out"), scp.TIMEOUT, None),
            (urllib.error.HTTPError(scp.URL, 503, "Service Unavailable", {}, None), scp.SERVER, 503),
        ]
        for error, kind, code in cases:
            def fail(request, timeout=None, error=error):
                raise error
            with self.subTest(kind=kind), mock.patch.object(scp.urllib.request, "urlopen", fail):
                exc = self.assert_fails(kind, code)
                self.assertTrue(exc.detail)  # technischer Text bleibt für die Anzeige

    def test_failed_write_leaves_no_rest(self):
        real_write = Path.write_bytes

        def full(path, data):
            real_write(path, data[:10])  # Teildatei liegt schon da
            raise OSError(28, "No space left on device")
        with answer(LIST), mock.patch.object(Path, "write_bytes", full):
            self.assert_fails(scp.WRITE)

    def test_locked_target_is_tried_twice(self):
        calls = []
        real_replace = os.replace

        def locked_once(src, dst):
            calls.append(dst)
            if len(calls) == 1:
                raise PermissionError(13, "in use")
            real_replace(src, dst)
        with answer(LIST), mock.patch.object(scp.os, "replace", locked_once), \
                mock.patch.object(scp, "REPLACE_RETRY_S", 0):
            scp.download(self.target)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.target.read_bytes(), LIST)

    def test_locked_target_keeps_old_list(self):
        def locked(src, dst):
            raise PermissionError(13, "in use")
        with answer(LIST), mock.patch.object(scp.os, "replace", locked), \
                mock.patch.object(scp, "REPLACE_RETRY_S", 0):
            self.assert_fails(scp.PERMISSION)

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
        self.assertEqual(self.mode.scp_button.cget("text"), "aktualisieren")  # flach, kurz
        self.assertEqual(str(self.mode.scp_button.cget("style")), "Flat.TButton")
        from morsetrainer.widgets import announcer
        self.assertTrue(announcer.describe(self.mode.scp_button).startswith("Rufzeichenliste aktualisieren"))
        self.assertIn("geladen: 3", self.mode.status_var.get())

    def test_list_waits_for_the_end_of_a_running_exercise(self):
        old = list(self.mode.all_calls)

        def download(target):
            target.write_text("DL4YM\nDK1AB\nDJ2CD\n")
            return 3
        with mock.patch.object(scp, "download", download):
            self.mode._download_list()
            self.mode.running = True  # mit F5 gestartet, während die Liste lädt
            try:
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    self.root.update()
                    time.sleep(0.01)
                self.assertEqual(self.mode.all_calls, old)
            finally:
                self.mode.running = False
            self.wait_for_download()
        self.assertEqual(sorted(self.mode.all_calls), ["DJ2CD", "DK1AB", "DL4YM"])

    def test_error_is_reported_and_button_comes_back(self):
        old = list(self.mode.all_calls)

        def download(target):
            raise scp.ScpError(scp.OFFLINE, "<urlopen error [Errno -3] Temporary failure in name resolution>")
        with mock.patch.object(scp, "download", download), \
                mock.patch.object(callsign_mode.announcer, "say") as say:
            self.mode._download_list()
            self.wait_for_download()
        self.assertEqual(self.mode.all_calls, old)
        self.assertNotIn("disabled", self.mode.scp_button.state())
        shown = self.mode.status_var.get()
        self.assertIn("Keine Verbindung zu supercheckpartial.com", shown)
        self.assertIn("Die bisherige Liste bleibt.", shown)
        self.assertIn(str(self.file.parent), shown)
        self.assertIn("Errno -3", shown)  # technisch nur sichtbar …
        spoken = say.call_args[0][0]
        self.assertIn("Keine Verbindung", spoken)
        self.assertNotIn("Errno", spoken)  # … nicht gesprochen
        self.assertNotIn("<", spoken)
        self.assertIn("Keine Verbindung", self.mode.list_info_var.get())  # auch über dem Knopf

    def test_error_text_in_english(self):
        from morsetrainer import i18n
        from morsetrainer.i18n_en import EN
        with mock.patch.object(i18n, "_TABLE", EN):
            self.mode._report_scp_error(scp.ScpError(scp.SERVER, "HTTP Error 503", code=503))
        self.assertIn("supercheckpartial.com reports error 503.", self.mode.status_var.get())

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


class CertificatesTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ, {}, clear=False)
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
            os.environ.pop(name, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / "cert.pem"
        self.bundle.write_text("x")

    def paths(self, cafile=None, capath=None):
        return mock.patch.object(certs.ssl, "get_default_verify_paths",
                                 return_value=mock.Mock(cafile=cafile, capath=capath))

    def test_system_file_is_used_when_openssl_finds_none(self):
        with self.paths(), mock.patch.object(certs.sys, "platform", "darwin"):
            self.assertEqual(certs.use_system_certificates(["/gibt/es/nicht", str(self.bundle)]), str(self.bundle))
        self.assertEqual(os.environ["SSL_CERT_FILE"], str(self.bundle))

    def test_nothing_changes_when_openssl_has_certificates(self):
        with self.paths(cafile="/usr/lib/ssl/cert.pem"), mock.patch.object(certs.sys, "platform", "linux"):
            self.assertIsNone(certs.use_system_certificates([str(self.bundle)]))
        self.assertNotIn("SSL_CERT_FILE", os.environ)

    def test_empty_certificate_folder_does_not_count(self):
        empty = Path(self.tmp.name) / "certs"
        empty.mkdir()
        with self.paths(capath=str(empty)), mock.patch.object(certs.sys, "platform", "linux"):
            self.assertEqual(certs.use_system_certificates([str(self.bundle)]), str(self.bundle))

    def test_own_setting_and_windows_are_left_alone(self):
        os.environ["SSL_CERT_FILE"] = "/eigene.pem"
        with self.paths(), mock.patch.object(certs.sys, "platform", "linux"):
            self.assertIsNone(certs.use_system_certificates([str(self.bundle)]))
        self.assertEqual(os.environ["SSL_CERT_FILE"], "/eigene.pem")
        del os.environ["SSL_CERT_FILE"]
        with self.paths(), mock.patch.object(certs.sys, "platform", "win32"):
            self.assertIsNone(certs.use_system_certificates([str(self.bundle)]))


if __name__ == "__main__":
    unittest.main()
