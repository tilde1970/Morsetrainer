"""Welche Morsetrainer-Fenster arbeiten gerade mit dem Datenordner?

Jedes Programmfenster legt in "<Datenordner>/.fenster/" eine Datei mit seiner
Prozessnummer an und entfernt sie beim Beenden. Wer die Daten ersetzen will
(Sicherung einlesen), fragt vorher mit others() nach anderen Fenstern: Sie
schrieben sonst in die ersetzte Datenbank oder hielten sie offen. Dateien
abgestürzter Fenster erkennt others() an der toten Prozessnummer."""
import atexit
import os
import sys
from pathlib import Path

DIR_NAME = ".fenster"


def _alive(pid: int) -> bool:
    """Läuft ein Prozess mit dieser Nummer? Im Zweifel ja (lieber eine Warnung
    zu viel als eine Sicherung eingelesen, während noch ein Fenster schreibt)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        process = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not process:
            return ctypes.GetLastError() == 5  # Zugriff verweigert: gibt es also
        kernel32.CloseHandle(ctypes.c_void_p(process))
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # PermissionError: gehört einem anderen Nutzer, läuft aber
    return True


def register(data_dir: Path) -> None:
    """Meldet dieses Fenster an und räumt beim Beenden auf. Scheitert das
    Anlegen (schreibgeschützter Ordner), geht es ohne Meldung weiter."""
    folder = Path(data_dir) / DIR_NAME
    mine = folder / str(os.getpid())
    try:
        folder.mkdir(parents=True, exist_ok=True)
        mine.touch()
    except OSError:
        return
    atexit.register(mine.unlink, missing_ok=True)


def others(data_dir: Path) -> int:
    """Zahl der anderen laufenden Fenster, die den Datenordner nutzen. Dateien
    nicht mehr laufender Prozesse werden dabei entfernt."""
    folder = Path(data_dir) / DIR_NAME
    count = 0
    try:
        entries = list(folder.iterdir())
    except OSError:
        return 0
    for entry in entries:
        try:
            pid = int(entry.name)
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        if _alive(pid):
            count += 1
        else:
            entry.unlink(missing_ok=True)
    return count
