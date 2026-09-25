"""Morsetrainer von DL4YM.

core/     Ton, Morsecode, Bandbedingungen, Texte, Statistik
modes/    ein Modul je Trainingsreiter
widgets/  wiederverwendbare Tk-Bausteine
app.py    Hauptfenster mit allen Reitern"""
import os
import sys
from pathlib import Path


def _data_dir() -> Path:
    """Ort der Nutzerdaten (stats/, window_state.json, callsigns.scp).

    Aus dem Quelltext gestartet: das Projektverzeichnis neben main.py.
    Als AppImage oder exe (PyInstaller) ist das Programmverzeichnis nicht
    beschreibbar, dann das übliche Datenverzeichnis des Benutzers."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        path = base / "Morsetrainer"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        path = base / "morsetrainer"
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = _data_dir()
