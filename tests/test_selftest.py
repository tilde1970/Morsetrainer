"""Selbsttest der Release-Builds: die Prüfung der Zertifikate für HTTPS."""
import ssl
import unittest
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import selftest
from morsetrainer.net import certs

NO_PATHS = ssl.DefaultVerifyPaths(None, None, "SSL_CERT_FILE", "/nirgends/cert.pem", "SSL_CERT_DIR",
                                  "/nirgends/certs")


class CertificateCheckTest(unittest.TestCase):
    def test_missing_certificates_fail_with_the_searched_places(self):
        context = mock.Mock(**{"cert_store_stats.return_value": {"x509_ca": 0}})
        with mock.patch.object(certs, "use_system_certificates", return_value=None), \
                mock.patch.object(selftest.ssl, "create_default_context", return_value=context), \
                mock.patch.object(selftest.ssl, "get_default_verify_paths", return_value=NO_PATHS):
            reason = selftest._certificates()
        self.assertIn("Keine Zertifikate für HTTPS", reason)
        self.assertIn("/nirgends/cert.pem", reason)

    def test_found_certificates_pass(self):
        context = mock.Mock(**{"cert_store_stats.return_value": {"x509_ca": 120}})
        with mock.patch.object(certs, "use_system_certificates", return_value="/etc/ssl/cert.pem"), \
                mock.patch.object(selftest.ssl, "create_default_context", return_value=context), \
                mock.patch("builtins.print") as printed:
            self.assertEqual(selftest._certificates(), "")
        printed.assert_called_once_with("Zertifikate: 120 aus /etc/ssl/cert.pem")


if __name__ == "__main__":
    unittest.main()
