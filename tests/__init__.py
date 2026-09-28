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