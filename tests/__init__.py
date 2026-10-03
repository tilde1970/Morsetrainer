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
_stats.RESULTS_FILE = _stats.STATS_DIR / "results.jsonl"
atexit.register(shutil.rmtree, _guard_dir, True)