"""Updates: das passende Release von GitHub laden, die eigene exe bzw.
das AppImage austauschen und neu starten. Anlass ist ein neueres Release
beim Programmstart (latest_version) oder ein Trainer im Netzwerk-Reiter
mit neuerer Version.

Geladen wird nur aus diesem Repo und nur eine neuere Version – ein
Trainer im Netz nennt bloß die Nummer. Aus dem Quelltext gestartet
(python main.py) gibt es nichts auszutauschen; dann bleibt es beim
Hinweis.

Windows: Eine laufende exe lässt sich nicht überschreiben, aber
umbenennen. Die alte wird zu Morsetrainer.old.exe und beim nächsten Start
entfernt (cleanup)."""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = "tilde1970/Morsetrainer"
WINDOWS_ASSET = "Morsetrainer.exe"
APPIMAGE_ASSET = "Morsetrainer-x86_64.AppImage"
VERSION_RE = re.compile(r"\d{1,3}(\.\d{1,3}){1,2}")
TIMEOUT_S = 30
# Die Prüfung beim Start soll ohne Internet nicht lange hängen.
CHECK_TIMEOUT_S = 5
MAX_API_BYTES = 1 << 20
CHUNK = 1 << 16
# Kleiner ist kein Morsetrainer, sondern z. B. eine Fehlerseite.
MIN_SIZE = 5_000_000
MAGIC = {WINDOWS_ASSET: b"MZ", APPIMAGE_ASSET: b"\x7fELF"}


class UpdateError(Exception):
    pass


def parse_version(text):
    """"2.15" -> (2, 15); None, wenn es keine Versionsnummer ist."""
    if not isinstance(text, str) or not VERSION_RE.fullmatch(text):
        return None
    return tuple(int(part) for part in text.split("."))


def is_newer(theirs, mine) -> bool:
    a, b = parse_version(theirs), parse_version(mine)
    return a is not None and b is not None and a > b


def installed():
    """(Programmdatei, Name im Release) oder None, wenn nichts auszutauschen
    ist (aus dem Quelltext gestartet)."""
    if not getattr(sys, "frozen", False):
        return None
    if sys.platform == "win32":
        return Path(sys.executable), WINDOWS_ASSET
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return Path(appimage), APPIMAGE_ASSET
    return None


def latest_version(timeout: float = CHECK_TIMEOUT_S):
    """Nummer des neuesten Releases auf GitHub ("2.16"). UpdateError ohne
    Internet oder bei unerwarteter Antwort. Blockiert (im Thread aufrufen)."""
    request = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                     headers={"User-Agent": "Morsetrainer",
                                              "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(MAX_API_BYTES).decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise UpdateError(str(exc)) from exc
    tag = data.get("tag_name") if isinstance(data, dict) else None
    version = tag[1:] if isinstance(tag, str) and tag.startswith("v") else None
    if parse_version(version) is None:
        raise UpdateError(f"unerwartete Antwort: {tag!r}")
    return version


def release_url(version: str) -> str:
    return f"https://github.com/{REPO}/releases/tag/v{version}"


def download_url(version: str, asset: str) -> str:
    return f"https://github.com/{REPO}/releases/download/v{version}/{asset}"


def download(version: str, target: Path, asset: str, progress=None, cancelled=lambda: False) -> Path:
    """Lädt `asset` von Version `version` neben `target` (als .new) und
    prüft, ob es vollständig ist und nach Programm aussieht. `progress`:
    (geladen, gesamt oder 0) je Block."""
    if parse_version(version) is None:
        raise UpdateError(f"keine Versionsnummer: {version!r}")
    part = target.with_name(target.name + ".new")
    request = urllib.request.Request(download_url(version, asset), headers={"User-Agent": "Morsetrainer"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(CHUNK):
                if cancelled():
                    raise UpdateError("abgebrochen")
                out.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
        if total and done != total:
            raise UpdateError("Download unvollständig")
        with open(part, "rb") as check:
            head = check.read(4)
        if done < MIN_SIZE or not head.startswith(MAGIC.get(asset, b"")):
            raise UpdateError("Die geladene Datei ist kein Morsetrainer")
    except (OSError, ValueError) as exc:
        _remove(part)
        raise UpdateError(str(exc)) from exc
    except UpdateError:
        _remove(part)
        raise
    return part


def install(part: Path, target: Path, windows: bool = sys.platform == "win32") -> None:
    """Setzt die geladene Datei an die Stelle von `target`."""
    try:
        if windows:
            old = _old_path(target)
            _remove(old)
            os.replace(target, old)
            try:
                os.replace(part, target)
            except OSError:
                os.replace(old, target)
                raise
        else:
            os.chmod(part, 0o755)
            os.replace(part, target)
    except OSError as exc:
        _remove(part)
        raise UpdateError(str(exc)) from exc


def relaunch(target: Path, args) -> None:
    """Startet das (neue) Programm als eigenen Prozess. Die Umgebung des
    laufenden gepackten Programms (PyInstaller, AppImage) darf es nicht
    erben, sonst sucht es seine Dateien im Verzeichnis des alten."""
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    for key in ("APPDIR", "APPIMAGE", "ARGV0", "OWD"):
        env.pop(key, None)
    options = {"start_new_session": True} if sys.platform != "win32" else {}
    subprocess.Popen([str(target), *args], env=env, close_fds=True, **options)


def cleanup() -> None:
    """Reste eines Updates entfernen (alte exe, abgebrochener Download)."""
    found = installed()
    if found is None:
        return
    target, _ = found
    _remove(_old_path(target))
    _remove(target.with_name(target.name + ".new"))


def _old_path(target: Path) -> Path:
    return target.with_name(target.stem + ".old" + target.suffix)


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
