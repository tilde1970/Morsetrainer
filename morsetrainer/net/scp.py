"""Rufzeichenliste laden: die aktuelle MASTER.SCP direkt von
supercheckpartial.com holen und als callsigns.scp ablegen. Die Liste liegt
bewusst nicht im Repository (keine veröffentlichten Weitergabe-Bedingungen);
so lädt jede und jeder sie selbst von der Quelle.

Die Datei wird erst neben dem Ziel gespeichert (.new) und nur dann an
die Stelle der alten gesetzt, wenn sie nach einer SCP-Liste aussieht;
sonst bleibt die bisherige Liste unangetastet."""
import http.client
import os
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
NET_ERRORS = (OSError, ValueError, http.client.HTTPException)


class ScpError(Exception):
    """Laden gescheitert; die Meldung ist lesbar."""


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
    part = target.with_name(target.name + ".new")
    request = urllib.request.Request(url, headers={"User-Agent": "Morsetrainer"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            total = int(response.headers.get("Content-Length") or 0)
            data = bytearray()
            while chunk := response.read(CHUNK):
                data += chunk
                if len(data) > MAX_BYTES:
                    raise ScpError("Datei zu groß")
        if total and len(data) != total:
            raise ScpError("Download unvollständig")
        calls = count_calls(bytes(data))
        if calls < MIN_CALLS:
            raise ScpError("Die geladene Datei ist keine Rufzeichenliste")
        target.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(data)
        os.replace(part, target)
    except NET_ERRORS as exc:
        _remove(part)
        raise ScpError(str(exc) or type(exc).__name__) from exc
    except ScpError:
        _remove(part)
        raise
    return calls


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
