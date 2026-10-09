"""Updates: das passende Release von GitHub laden, die eigene exe bzw.
das AppImage austauschen und neu starten. Anlass ist ein neueres Release
beim Programmstart (latest_version) oder ein Trainer im Netzwerk-Reiter
mit neuerer Version.

Geladen wird nur aus diesem Repo und nur eine neuere Version – ein
Trainer im Netz nennt bloß die Nummer. Die Datei muss zur Prüfsumme in
SHA256SUMS.txt desselben Releases passen. Das fängt beschädigte und
falsche Downloads ab, aber keinen, der das Release selbst austauschen
kann: Der ersetzt die Prüfsumme gleich mit. Aus dem Quelltext gestartet
(python main.py) gibt es nichts auszutauschen; dann bleibt es beim
Hinweis.

Windows: Eine laufende exe lässt sich nicht überschreiben, aber
umbenennen. Die alte wird zu Morsetrainer.old.exe und beim nächsten Start
entfernt (cleanup)."""
import hashlib
import http.client
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
SUMS_ASSET = "SHA256SUMS.txt"
MAX_SUMS_BYTES = 1 << 16
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class UpdateError(Exception):
    """Update gescheitert (Download, Prüfsumme oder Ersetzen); die Meldung ist
    lesbar."""


# Netzfehler: http.client meldet einen abgerissenen Download (IncompleteRead)
# nicht als OSError.
NET_ERRORS = (OSError, ValueError, http.client.HTTPException)


def parse_version(text):
    """"2.15" -> (2, 15); None, wenn es keine Versionsnummer ist."""
    if not isinstance(text, str) or not VERSION_RE.fullmatch(text):
        return None
    return tuple(int(part) for part in text.split("."))


def is_newer(theirs, mine) -> bool:
    """Ist Version `theirs` neuer als `mine`? False, wenn eine keine
    Versionsnummer ist."""
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
    return latest_release(timeout)[0]


# Die Release-Beschreibung (.github/workflows/release.yml): deutsche
# Neuerungen, Verweis, ab „### English“ die englischen, Verweis, dann der
# Vergleichslink von GitHub. Die Verweise gehören nicht zu den Neuerungen.
_NOTES_END = re.compile(r"^\s*(Alle Änderungen:|All changes:|\*\*Full Changelog\*\*)", re.MULTILINE)
_ENGLISH = re.compile(r"^###\s+English\s*$", re.MULTILINE)
MAX_NOTES_CHARS = 6000


def release_notes(body, lang: str = "de") -> str:
    """Die Neuerungen aus der Beschreibung eines Releases (Markdown) in der
    Sprache `lang`, ohne die Verweise; ohne englischen Teil (ältere
    Releases) die deutschen. Leer, wenn es keine gibt."""
    if not isinstance(body, str):
        return ""
    english = _ENGLISH.search(body)
    if lang == "en" and english:
        body = body[english.end():]
    end = _NOTES_END.search(body)
    return (body[:end.start()] if end else body).strip()[:MAX_NOTES_CHARS]


def latest_release(timeout: float = CHECK_TIMEOUT_S, lang: str = "de"):
    """(Nummer, Neuerungen in der Sprache `lang`) des neuesten Releases auf
    GitHub. UpdateError ohne Internet oder bei unerwarteter Antwort.
    Blockiert (im Thread aufrufen)."""
    request = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                     headers={"User-Agent": "Morsetrainer",
                                              "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(MAX_API_BYTES).decode("utf-8"))
    except NET_ERRORS as exc:
        raise UpdateError(str(exc)) from exc
    tag = data.get("tag_name") if isinstance(data, dict) else None
    version = tag[1:] if isinstance(tag, str) and tag.startswith("v") else None
    if parse_version(version) is None:
        raise UpdateError(f"unerwartete Antwort: {tag!r}")
    return version, release_notes(data.get("body"), lang)


def release_url(version: str) -> str:
    """Seite des Releases `version` auf GitHub."""
    return f"https://github.com/{REPO}/releases/tag/v{version}"


def download_url(version: str, asset: str) -> str:
    """Download-Adresse der Datei `asset` im Release `version`."""
    return f"https://github.com/{REPO}/releases/download/v{version}/{asset}"


def expected_sha256(version: str, asset: str) -> str:
    """Prüfsumme von `asset` aus SHA256SUMS.txt des Releases (Zeilen
    „<sha256>  <Datei>“ wie von sha256sum). UpdateError, wenn die Datei
    fehlt oder `asset` darin nicht vorkommt."""
    request = urllib.request.Request(download_url(version, SUMS_ASSET), headers={"User-Agent": "Morsetrainer"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            text = response.read(MAX_SUMS_BYTES).decode("ascii", "replace")
    except NET_ERRORS as exc:
        raise UpdateError(f"keine Prüfsumme: {exc}") from exc
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset and SHA256_RE.fullmatch(parts[0].lower()):
            return parts[0].lower()
    raise UpdateError(f"keine Prüfsumme für {asset}")


def download(version: str, target: Path, asset: str, progress=None, cancelled=lambda: False) -> Path:
    """Lädt `asset` von Version `version` neben `target` (als .new) und
    prüft, ob es vollständig ist, zur Prüfsumme passt und nach Programm
    aussieht. `progress`: (geladen, gesamt oder 0) je Block."""
    if parse_version(version) is None:
        raise UpdateError(f"keine Versionsnummer: {version!r}")
    expected = expected_sha256(version, asset)
    part = target.with_name(target.name + ".new")
    request = urllib.request.Request(download_url(version, asset), headers={"User-Agent": "Morsetrainer"})
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(CHUNK):
                if cancelled():
                    raise UpdateError("abgebrochen")
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
        if total and done != total:
            raise UpdateError("Download unvollständig")
        with open(part, "rb") as check:
            head = check.read(4)
        if done < MIN_SIZE or not head.startswith(MAGIC.get(asset, b"")):
            raise UpdateError("Die geladene Datei ist kein Morsetrainer")
        if digest.hexdigest() != expected:
            raise UpdateError("Prüfsumme stimmt nicht (SHA256SUMS.txt)")
    except NET_ERRORS as exc:
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


def restart_command():
    """Befehl, der den Morsetrainer neu startet, als Liste: die Programmdatei
    (exe, AppImage, Mac-App) bzw. Python mit main.py; None, wenn er sich
    nicht ermitteln lässt."""
    found = installed()
    if found is not None:
        return [str(found[0])]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    main = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    return [sys.executable, str(main)] if main is not None and main.is_file() else None


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
