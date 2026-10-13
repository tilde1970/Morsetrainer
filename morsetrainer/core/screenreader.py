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
                            stdin=subprocess.DEVNULL, check=False, env=_system_env())
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
            if entry.stat().st_uid == uid and (entry / "comm").read_text(errors="replace").strip() == "orca":
                return True
        except OSError:
            continue
    return False


def _system_env() -> dict:
    """Umgebung für Programme des Systems: Als AppImage/PyInstaller zeigt
    LD_LIBRARY_PATH auf die mitgelieferten Bibliotheken, mit denen z. B.
    gsettings nicht startet."""
    env = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    return env
