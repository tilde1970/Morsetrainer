"""Rufzeichenliste laden: die aktuelle MASTER.SCP direkt von
supercheckpartial.com holen und als callsigns.scp ablegen. Die Liste liegt
bewusst nicht im Repository (keine veröffentlichten Weitergabe-Bedingungen);
so lädt jede und jeder sie selbst von der Quelle.

Die Datei wird erst neben dem Ziel gespeichert (.new) und nur dann an
die Stelle der alten gesetzt, wenn sie nach einer SCP-Liste aussieht;
sonst bleibt die bisherige Liste unangetastet.

Fehler kommen als ScpError mit einer Art (OFFLINE, TIMEOUT …): Den
verständlichen, übersetzten Satz dazu sucht die Oberfläche aus; der
technische Text von urllib steht nur in `detail`."""
import http.client
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://www.supercheckpartial.com/MASTER.SCP"
TIMEOUT_S = 30
CHUNK = 1 << 16
# Die Liste hat rund 360 kB; deutlich größer ist sie nicht.
MAX_BYTES = 10_000_000
# Weniger Rufzeichen: eher eine Fehlerseite als die Liste.
MIN_CALLS = 1000
CALL_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/")
# Unter Windows hält ein Virenscanner die frische Datei manchmal kurz fest.
REPLACE_RETRY_S = 0.5

# Arten von Fehlern (ScpError.kind).
OFFLINE = "offline"          # keine Verbindung (Internet, Proxy, Name nicht auflösbar)
TIMEOUT = "timeout"          # Server antwortet nicht
CERTIFICATE = "certificate"  # sichere Verbindung nicht möglich
SERVER = "server"            # Server meldet einen HTTP-Fehler (ScpError.code)
INCOMPLETE = "incomplete"    # Übertragung abgebrochen
TOO_LARGE = "too_large"      # viel größer als eine Rufzeichenliste
NOT_A_LIST = "not_a_list"    # etwas anderes kam an (Fehlerseite, WLAN-Anmeldung)
PERMISSION = "permission"    # kein Schreibrecht, oder Datei von anderem Programm geöffnet
WRITE = "write"              # Speichern gescheitert (Datenträger voll …)


class ScpError(Exception):
    """Laden gescheitert: `kind` (siehe oben), `detail` (technischer Text),
    `code` (HTTP-Status bei SERVER)."""

    def __init__(self, kind: str, detail: str = "", code: int | None = None):
        super().__init__(detail or kind)
        self.kind, self.detail, self.code = kind, detail, code


def count_calls(data: bytes) -> int:
    """Rufzeichen-Zeilen einer SCP-Liste (ohne Kommentare und Leerzeilen)."""
    count = 0
    for line in data.decode("ascii", errors="ignore").splitlines():
        line = line.strip().upper()
        if line and line[0] not in "#!" and set(line) <= CALL_CHARS:
            count += 1
    return count


def download(target: Path, url: str = URL) -> int:
    """Lädt die Liste nach `target` und gibt die Zahl der Rufzeichen zurück."""
    data = _fetch(url)
    calls = count_calls(data)
    if calls < MIN_CALLS:
        raise ScpError(NOT_A_LIST, f"{calls} Rufzeichen")
    _store(data, target)
    return calls


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Morsetrainer"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            total = int(response.headers.get("Content-Length") or 0)
            data = bytearray()
            while chunk := response.read(CHUNK):
                data += chunk
                if len(data) > MAX_BYTES:
                    raise ScpError(TOO_LARGE, f"> {MAX_BYTES} Byte")
    except urllib.error.HTTPError as exc:
        raise ScpError(SERVER, str(exc), code=exc.code) from exc
    except urllib.error.URLError as exc:
        raise ScpError(_kind(exc.reason), str(exc)) from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise ScpError(_kind(exc), str(exc) or type(exc).__name__) from exc
    if total and len(data) != total:
        raise ScpError(INCOMPLETE, f"{len(data)} von {total} Byte")
    return bytes(data)


def _kind(reason) -> str:
    """Art eines Netzfehlers (`reason` von URLError oder die Ausnahme selbst)."""
    if isinstance(reason, ssl.SSLError):
        return CERTIFICATE
    if isinstance(reason, TimeoutError):
        return TIMEOUT
    if isinstance(reason, (http.client.HTTPException, ValueError, ConnectionResetError)):
        return INCOMPLETE
    return OFFLINE


def _store(data: bytes, target: Path) -> None:
    """Erst neben das Ziel (.new), dann an seine Stelle; scheitert das, bleibt
    die alte Liste und kein Rest."""
    part = target.with_name(target.name + ".new")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(data)
        try:
            os.replace(part, target)
        except PermissionError:
            time.sleep(REPLACE_RETRY_S)
            os.replace(part, target)
    except OSError as exc:
        _remove(part)
        raise ScpError(PERMISSION if isinstance(exc, PermissionError) else WRITE, str(exc)) from exc


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
