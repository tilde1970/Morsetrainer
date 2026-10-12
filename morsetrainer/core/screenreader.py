"""Läuft ein Screenreader? (Windows: Systemeinstellung, die NVDA, JAWS und
die Sprachausgabe setzen; macOS: VoiceOver; Linux: Orca.)

Nur eine Vermutung für den ersten Start: Wer einen Screenreader nutzt,
bekommt die eigene Ansage gleich eingeschaltet. Jeder Fehler heißt „nein“."""
import os
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 1.0


def running() -> bool:
    try:
        if sys.platform == "win32":
            return _windows()
        if sys.platform == "darwin":
            return _command(["defaults", "read", "com.apple.universalaccess", "voiceOverOnOffKey"]) == "1"
        return _orca_process() or _command(
            ["gsettings", "get", "org.gnome.desktop.a11y.applications", "screen-reader-enabled"]) == "true"
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
        return False


def _windows() -> bool:
    import ctypes
    spi_getscreenreader = 0x0046
    flag = ctypes.c_int(0)
    if not ctypes.windll.user32.SystemParametersInfoW(spi_getscreenreader, 0, ctypes.byref(flag), 0):
        return False
    return bool(flag.value)


def _command(args) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT_S,
                            stdin=subprocess.DEVNULL, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _orca_process() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    uid = os.getuid()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid == uid and (entry / "comm").read_text().strip() == "orca":
                return True
        except OSError:
            continue
    return False
