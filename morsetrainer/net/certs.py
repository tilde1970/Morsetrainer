"""Zertifikate für HTTPS in den gepackten Programmen.

Mac-App und AppImage bringen eine eigene OpenSSL mit, die die Zertifikate
an dem Ort sucht, wo sie auf dem Build-Rechner lagen (python.org-Python
bzw. /usr/lib/ssl unter Debian). Auf dem Mac der Nutzer und unter Fedora,
Arch, openSUSE … gibt es den Ort nicht: Jeder HTTPS-Abruf (Rufzeichenliste,
Update-Prüfung) scheiterte dann mit CERTIFICATE_VERIFY_FAILED. Findet
OpenSSL nichts, zeigt SSL_CERT_FILE auf die Zertifikate des Systems.
Windows nutzt ohnehin den Zertifikatsspeicher des Systems."""
import os
import ssl
import sys

# Übliche Orte der Zertifikate: macOS, Arch und Alpine; Debian und Ubuntu;
# Fedora und RHEL; openSUSE.
SYSTEM_CA_FILES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
                   "/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/ca-bundle.pem")


def _usable(paths) -> bool:
    """Ob OpenSSL von sich aus Zertifikate findet (Datei, oder Ordner mit Inhalt)."""
    if paths.cafile:
        return True
    try:
        return bool(paths.capath and os.listdir(paths.capath))
    except OSError:
        return False


def use_system_certificates(candidates=SYSTEM_CA_FILES) -> str | None:
    """Beim Start: SSL_CERT_FILE auf die Zertifikate des Systems setzen, falls
    OpenSSL keine findet und niemand etwas vorgegeben hat. Gibt die gewählte
    Datei zurück (sonst None)."""
    if sys.platform == "win32" or os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
        return None
    if _usable(ssl.get_default_verify_paths()):
        return None
    for path in candidates:
        if os.path.isfile(path):
            os.environ["SSL_CERT_FILE"] = path
            return path
    return None
