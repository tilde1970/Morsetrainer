"""Sprachausgabe mit Piper: neuronale Stimmen, offline, für „Hören &
Sagen“ (Lösung ansagen), den MP3-Export und die Sprachansage zur
Barrierefreiheit (widgets/announcer.py). Deutsch (Thorsten) für alles,
Englisch (Lessac) für die Ansage bei englischer Oberfläche.

Die Stimme (ONNX-Modell plus .json) liegt in voices/: in AppImage und exe
mitgeliefert (sys._MEIPASS/voices), aus dem Quelltext im Datenverzeichnis
(packaging/get_voice.sh lädt sie). Fehlen Piper oder die Stimme, meldet
available() den Grund und alles andere läuft ohne Ansage weiter.

Geladen wird die Stimme erst beim ersten Gebrauch (knapp 1 s), in einem
Hintergrund-Thread über Speaker.preload(), damit weder der Programmstart
noch die erste Ansage stockt.

Gesprochen wird buchstabiert: Buchstabennamen (A, Be, Ce … bzw. ay, bee,
see …) oder das internationale Buchstabieralphabet (Alfa, Bravo …), wie
es im Funkbetrieb üblich ist. Wortgrenzen werden zu einer kurzen Pause."""
import sys
import threading
from pathlib import Path

import numpy as np

from morsetrainer import DATA_DIR
from morsetrainer.core.morse import AMPLITUDE, PROSIGNS, SAMPLE_RATE
from morsetrainer.i18n import tr

VOICE_NAME = "de_DE-thorsten-medium"
# Stimme je Sprache der Oberfläche (packaging/get_voice.sh lädt sie).
VOICES = {"de": VOICE_NAME, "en": "en_US-lessac-medium"}

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
    "A": "Alfa", "B": "Bravo", "C": "Tschali", "D": "Delta", "E": "Ekko", "F": "Foxtrott", "G": "Golf",
    "H": "Hotell", "I": "India", "J": "Dschulijätt", "K": "Kilo", "L": "Lima", "M": "Maik",
    "N": "November", "O": "Oskar", "P": "Papa", "Q": "Que-beck", "R": "Romeo", "S": "Siärra",
    "T": "Tango", "U": "Juni-form", "V": "Viktor", "W": "Wiski", "X": "Ex-Rehj", "Y": "Jäng-ki",
    "Z": "Suhlu",
}
# „Zwo“ wie im Funk üblich: klar von „drei“ zu unterscheiden.
DIGITS = {"0": "Null", "1": "Eins", "2": "Zwo", "3": "Drei", "4": "Vier", "5": "Fünf", "6": "Sechs",
          "7": "Sieben", "8": "Acht", "9": "Neun"}
# „Strich“ hieße im Morsetrainer ein Dah, daher „Schrägstrich“.
SIGNS = {".": "Punkt", ",": "Komma", "?": "Fragezeichen", "/": "Schrägstrich"}
# Betriebszeichen, im gewählten Alphabet buchstabiert (<KN> = Ka Enn bzw. Kilo November).
PROSIGN_NAMES = {"=": "BT", "+": "AR", **PROSIGNS}

ALPHABETS = {"de": GERMAN, "nato": NATO}

# Englische Stimme: Buchstabennamen so geschrieben, dass sie nicht als Wort
# gelesen werden („A“ wäre der Artikel), das Funkalphabet in der üblichen
# Schreibweise.
ENGLISH = {
    "A": "ay", "B": "bee", "C": "see", "D": "dee", "E": "ee", "F": "eff", "G": "gee", "H": "aitch",
    "I": "eye", "J": "jay", "K": "kay", "L": "el", "M": "em", "N": "en", "O": "oh", "P": "pee",
    "Q": "cue", "R": "ar", "S": "ess", "T": "tee", "U": "you", "V": "vee", "W": "double you", "X": "ex",
    "Y": "why", "Z": "zed",
}
NATO_EN = {
    "A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo", "F": "Foxtrot", "G": "Golf",
    "H": "Hotel", "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November",
    "O": "Oscar", "P": "Papa", "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango", "U": "Uniform",
    "V": "Victor", "W": "Whiskey", "X": "X-ray", "Y": "Yankee", "Z": "Zulu",
}
DIGITS_EN = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
             "7": "seven", "8": "eight", "9": "nine"}
SIGNS_EN = {".": "period", ",": "comma", "?": "question mark", "/": "slash"}
# Je Sprache: (Alphabete, Ziffern, Satzzeichen).
TABLES = {
    "de": ({"de": GERMAN, "nato": NATO}, DIGITS, SIGNS),
    "en": ({"de": ENGLISH, "nato": NATO_EN}, DIGITS_EN, SIGNS_EN),
}


def _tables(alphabet: str, lang: str):
    alphabets, digits, signs = TABLES.get(lang, TABLES["de"])
    return alphabets.get(alphabet, alphabets["de"]), digits, signs


def _name(ch: str, letters: dict, digits: dict = DIGITS, signs: dict = SIGNS) -> str:
    if ch in PROSIGN_NAMES:
        return " ".join(letters[c] for c in PROSIGN_NAMES[ch])
    return letters.get(ch) or digits.get(ch) or signs.get(ch) or ""


def spoken(text: str, alphabet: str = "de", lang: str = "de") -> str:
    """Text buchstabiert, so wie die Stimme ihn sprechen soll. `alphabet`:
    "de" Buchstabennamen, "nato" Funkalphabet; `lang`: Sprache der Stimme."""
    letters, digits, signs = _tables(alphabet, lang)
    words = []
    for word in text.upper().split():
        words.append(", ".join(name for name in (_name(ch, letters, digits, signs) for ch in word) if name))
    return ". ".join(w for w in words if w)


def spoken_words(text: str, alphabet: str = "de", lang: str = "de") -> str:
    """Wörter als Ganzes sprechen (klein geschrieben, damit die Stimme sie
    nicht buchstabiert); Zahlen, Satz- und Betriebszeichen einzeln."""
    letters, digits, signs = _tables(alphabet, lang)
    out = []
    for word in text.upper().split():
        if word.isalpha():
            out.append(word.lower())
        else:
            out.append(", ".join(name for name in (_name(ch, letters, digits, signs) for ch in word) if name))
    return ". ".join(w for w in out if w)


def voice_dirs() -> list:
    """Ordner, in denen die Stimmen gesucht werden: im gepackten Programm
    zuerst der mitgelieferte, dann voices/ im Datenordner."""
    dirs = [DATA_DIR / "voices"]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        dirs.insert(0, Path(base) / "voices")
    return dirs


def voice_path(lang: str = "de"):
    """Pfad zur Stimme für `lang` (.onnx, dazu muss die .onnx.json daneben
    liegen), oder None, wenn sie fehlt."""
    name = VOICES.get(lang, VOICE_NAME)
    for directory in voice_dirs():
        path = directory / f"{name}.onnx"
        if path.exists() and path.with_suffix(".onnx.json").exists():
            return path
    return None


def resample(samples: np.ndarray, rate: int, target: int = SAMPLE_RATE) -> np.ndarray:
    """`samples` von `rate` auf `target` Hz umrechnen (lineare Interpolation,
    für Sprache genau genug)."""
    if rate == target or not len(samples):
        return samples.astype(np.float32)
    n = int(round(len(samples) * target / rate))
    positions = np.linspace(0, len(samples) - 1, n)
    return np.interp(positions, np.arange(len(samples)), samples).astype(np.float32)


class Speaker:
    """Lädt die Stimme einmal und erzeugt Sprache als float32 bei
    SAMPLE_RATE, etwa so laut wie die Morsezeichen."""

    def __init__(self, lang: str = "de"):
        self.lang = lang if lang in VOICES else "de"
        self.voice = None
        self.error = None
        self._lock = threading.Lock()

    def available(self):
        """None, wenn Sprachausgabe möglich ist, sonst der Grund."""
        try:
            import piper  # noqa: F401
        except ImportError:
            return tr("Sprachausgabe nicht verfügbar: Piper ist nicht installiert (pip install piper-tts).")
        if voice_path(self.lang) is None:
            return tr("Sprachausgabe nicht verfügbar: Stimme {voice} fehlt "
                      "(packaging/get_voice.sh lädt sie nach {folder}).").format(
                voice=VOICES[self.lang], folder=DATA_DIR / "voices")
        return self.error

    def load(self) -> bool:
        """Lädt die Stimme, falls noch nicht geschehen (dauert knapp eine Sekunde).
        False, wenn das nicht geht; der Grund steht dann in available()."""
        with self._lock:
            if self.voice is not None:
                return True
            if self.available() is not None:
                return False
            try:
                from piper import PiperVoice
                self.voice = PiperVoice.load(str(voice_path(self.lang)))
            except Exception as exc:  # kaputtes Modell, fehlende Laufzeit …
                self.error = tr("Sprachausgabe nicht verfügbar: {error}").format(error=exc)
                return False
            return True

    def preload(self) -> None:
        """Lädt die Stimme im Hintergrund, damit die erste Ansage nicht warten muss."""
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


# Die deutsche Stimme für Sprechen und MP3; für die Ansage speaker_for().
speaker = Speaker()
_speakers = {"de": speaker}


def speaker_for(lang: str) -> Speaker:
    """Stimme für die Sprache `lang` (einmal geladen); unbekannt: Deutsch."""
    if lang not in VOICES:
        lang = "de"
    if lang not in _speakers:
        _speakers[lang] = Speaker(lang)
    return _speakers[lang]
