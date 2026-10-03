"""Tests für den Morsetrainer. Laufen ohne Soundkarte und ohne Fenster:
sounddevice wird durch eine Attrappe ersetzt, bevor Module es importieren.

Aufruf aus dem Projektverzeichnis: python -m unittest discover tests"""
import os
import sys
import types
from pathlib import Path

# Die Tests prüfen deutsche Texte, unabhängig von der Spracheinstellung.
os.environ["MORSETRAINER_LANG"] = "de"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "sounddevice" not in sys.modules:
    _sd = types.ModuleType("sounddevice")
    _sd.OutputStream = None
    _sd.play = _sd.stop = _sd.wait = lambda *args, **kwargs: None
    sys.modules["sounddevice"] = _sd

# Kein Test darf die echten Übungsdaten anfassen: Wer STATS_DIR nicht selbst
# auf einen eigenen Ordner setzt, landet in diesem (samt Datenbank).
import atexit  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

from morsetrainer.core import stats as _stats  # noqa: E402

_guard_dir = Path(tempfile.mkdtemp(prefix="morsetrainer-tests-"))
_stats.STATS_DIR = _guard_dir / "stats"
atexit.register(shutil.rmtree, _guard_dir, True)


def session_lines(session_id: int) -> list:
    """Ein Durchgang aus der Datenbank als Zeilen wie früher in der
    Sitzungsdatei: config, die Zeilen dazwischen, summary (falls vorhanden)."""
    from morsetrainer.core import db
    [session] = [s for s in db.sessions() if s.id == session_id]
    return [session.config, *db.session_events(session_id), *([session.summary] if session.summary else [])]


def write_session(lines) -> int:
    """Legt einen Durchgang aus Zeilen wie in einer Sitzungsdatei an
    (erste Zeile config mit "start_time" und "mode", eine Zeile "summary"
    schließt ihn ab) und gibt seine id zurück."""
    from morsetrainer.core import db
    config, *rest = lines
    with db.transaction():
        session_id = db.start_session(config)
        for line in rest:
            if line.get("type") == "summary":
                db.finish_session(session_id, line)
            else:
                db.add_event(session_id, line)
    return session_id
