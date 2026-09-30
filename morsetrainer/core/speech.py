"""Sprachausgabe mit Piper: eine neuronale Stimme, offline, für „Hören &
Sagen“ (Lösung ansagen) und den MP3-Export.

Die Stimme (ONNX-Modell plus .json) liegt in voices/: in AppImage und exe
mitgeliefert (sys._MEIPASS/voices), aus dem Quelltext im Datenverzeichnis
(packaging/get_voice.sh lädt sie). Fehlen Piper oder die Stimme, meldet
available() den Grund und alles andere läuft ohne Ansage weiter.

Geladen wird die Stimme erst beim ersten Gebrauch (knapp 1 s), in einem
Hintergrund-Thread über Speaker.preload(), damit weder der Programmstart
noch die erste Ansage stockt.

Gesprochen wird buchstabiert: deutsche Buchstabennamen (A, Be, Ce …) oder
das internationale Buchstabieralphabet (Alfa, Bravo …), wie es im
Funkbetrieb üblich ist. Wortgrenzen werden zu einer kurzen Pause."""
import sys
import threading
from pathlib import Path

import numpy as np

from morsetrainer import DATA_DIR
from morsetrainer.core.morse import AMPLITUDE, PROSIGNS, SAMPLE_RATE
from morsetrainer.i18n import tr

VOICE_NAME = "de_DE-thorsten-medium"

GERMAN = {
    "A": "A", "B": "Be", "C": "Ze", "D": "De", "E": "E", "F": "Eff", "G": "Ge", "H": "Ha", "I": "I",
    "J": "Jott", "K": "Ka", "L": "Ell", "M": "Emm", "N": "Enn", "O": "O", "P": "Pe", "Q": "Ku",
    "R": "Err", "S": "Ess", "T": "Te", "U": "U", "V": "Fau", "W": "We", "X": "Ix", "Y": "Üpsilon",
    "Z": "Zett",
}
# Die Stimme ist deutsch und spräche „Mike“ als „Micke“ aus: Die
# Buchstabierwörter stehen daher so da, wie sie deutsch gelesen richtig
# klingen (Charlie → Tschali, Juliett → Dschulijätt, Zulu → Suhlu …).
NATO = {
    "A": "Alfa", "B": "Bravo", "C": "Tschali", "D": "Delta", "E": "Echo", "F": "Foxtrott", "G": "Golf",
    "H": "Hotell", "I": "India", "J": "Dschulijätt", "K": "Kilo", "L": "Lima", "M": "Maik",
    "N": "November", "O": "Oskar", "P": "Papa", "Q": "Que-beck", "R": "Romeo", "S": "Siärra",
    "T": "Tango", "U": "Juni-form", "V": "Viktor", "W": "Wiski", "X": "Ex-Rehj", "Y": "Jäng-ki",
    "Z": "Suhlu",
}
DIGITS = {"0": "Null", "1": "Eins", "2": "Zwei", "3": "Drei", "4": "Vier", "5": "Fünf", "6": "Sechs",
          "7": "Sieben", "8": "Acht", "9": "Neun"}
# „Strich“ hieße im Morsetrainer ein Dah, daher „Schrägstrich“.
SIGNS = {".": "Punkt", ",": "Komma", "?": "Fragezeichen", "/": "Schrägstrich"}
# Betriebszeichen, im gewählten Alphabet buchstabiert (<KN> = Ka Enn bzw. Kilo November).
PROSIGN_NAMES = {"=": "BT", "+": "AR", **PROSIGNS}

ALPHABETS = {"de": GERMAN, "nato": NATO}


def _name(ch: str, letters: dict) -> str:
    if ch in PROSIGN_NAMES:
        return " ".join(letters[c] for c in PROSIGN_NAMES[ch])
    return letters.get(ch) or DIGITS.get(ch) or SIGNS.get(ch) or ""


def spoken(text: str, alphabet: str = "de") -> str:
    """Text buchstabiert, so wie die Stimme ihn sprechen soll."""
    letters = ALPHABETS.get(alphabet, GERMAN)
    words = []
    for word in text.upper().split():
        words.append(", ".join(name for name in (_name(ch, letters) for ch in word) if name))
    return ". ".join(w for w in words if w)


def spoken_words(text: str, alphabet: str = "de") -> str:
    """Wörter als Ganzes sprechen (klein geschrieben, damit die Stimme sie
    nicht buchstabiert); Zahlen, Satz- und Betriebszeichen einzeln."""
    letters = ALPHABETS.get(alphabet, GERMAN)
    out = []
    for word in text.upper().split():
        if word.isalpha():
            out.append(word.lower())
        else:
            out.append(", ".join(name for name in (_name(ch, letters) for ch in word) if name))
    return ". ".join(w for w in out if w)


def voice_dirs() -> list:
    dirs = [DATA_DIR / "voices"]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        dirs.insert(0, Path(base) / "voices")
    return dirs


def voice_path():
    for directory in voice_dirs():
        path = directory / f"{VOICE_NAME}.onnx"
        if path.exists() and path.with_suffix(".onnx.json").exists():
            return path
    return None


def resample(samples: np.ndarray, rate: int, target: int = SAMPLE_RATE) -> np.ndarray:
    if rate == target or not len(samples):
        return samples.astype(np.float32)
    n = int(round(len(samples) * target / rate))
    positions = np.linspace(0, len(samples) - 1, n)
    return np.interp(positions, np.arange(len(samples)), samples).astype(np.float32)


class Speaker:
    """Lädt die Stimme einmal und erzeugt Sprache als float32 bei
    SAMPLE_RATE, etwa so laut wie die Morsezeichen."""

    def __init__(self):
        self.voice = None
        self.error = None
        self._lock = threading.Lock()

    def available(self):
        """None, wenn Sprachausgabe möglich ist, sonst der Grund."""
        try:
            import piper  # noqa: F401
        except ImportError:
            return tr("Sprachausgabe nicht verfügbar: Piper ist nicht installiert (pip install piper-tts).")
        if voice_path() is None:
            return tr("Sprachausgabe nicht verfügbar: Stimme {voice} fehlt "
                      "(packaging/get_voice.sh lädt sie nach {folder}).").format(
                voice=VOICE_NAME, folder=DATA_DIR / "voices")
        return self.error

    def load(self) -> bool:
        with self._lock:
            if self.voice is not None:
                return True
            if self.available() is not None:
                return False
            try:
                from piper import PiperVoice
                self.voice = PiperVoice.load(str(voice_path()))
            except Exception as exc:  # kaputtes Modell, fehlende Laufzeit …
                self.error = tr("Sprachausgabe nicht verfügbar: {error}").format(error=exc)
                return False
            return True

    def preload(self) -> None:
        threading.Thread(target=self.load, daemon=True).start()

    def synth(self, text: str) -> np.ndarray:
        """Sprache für `text`; leer, wenn keine Sprachausgabe möglich ist."""
        if not text or not self.load():
            return np.zeros(0, dtype=np.float32)
        chunks = [chunk.audio_float_array for chunk in self.voice.synthesize(text)]
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        samples = resample(np.concatenate(chunks), self.voice.config.sample_rate)
        peak = float(np.max(np.abs(samples))) or 1.0
        return (samples * (AMPLITUDE * 0.9 / peak)).astype(np.float32)


# Eine Stimme für das ganze Programm.
speaker = Speaker()
