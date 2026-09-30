"""Fehlerprotokoll für unerwartete Fehler (Programmfehler).

exe und AppImage laufen ohne Konsole: Ein Fehler in einem Knopf oder
einem Hintergrund-Thread wäre sonst unsichtbar – es passiert einfach
nichts. record() hängt den Traceback an fehler.log im Datenverzeichnis
an; das Hauptfenster zeigt dann einmal, wo die Datei liegt, damit sie
einem Fehlerbericht beigelegt werden kann.

Erwartete Fehler (kein Audiogerät, Datei nicht schreibbar, kein Netz)
behandeln die Module selbst; hier landet nur, was keiner erwartet hat."""
import threading
import traceback
from datetime import datetime

from morsetrainer import DATA_DIR

LOG_FILE = DATA_DIR / "fehler.log"
# Größer wird die Datei nicht: Sie wird dann neu begonnen.
MAX_BYTES = 1 << 20

_lock = threading.Lock()
# Zahl der protokollierten Fehler, die das Hauptfenster noch nicht gemeldet hat.
unseen = 0


def record(exc_type, exc, tb, version="") -> bool:
    """Schreibt den Fehler ins Protokoll. False, wenn das nicht ging."""
    global unseen
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    stamp = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _lock:
        unseen += 1
        try:
            mode = "w" if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_BYTES else "a"
            with open(LOG_FILE, mode, encoding="utf-8") as fp:
                fp.write(f"--- {stamp} Morsetrainer {version} ---\n{text}\n")
        except OSError:
            return False
    return True


def take_unseen() -> int:
    """Zahl der neuen Fehler seit dem letzten Aufruf (und zurücksetzen)."""
    global unseen
    with _lock:
        count, unseen = unseen, 0
    return count
