"""Non-Morse feedback sounds: a short confirmation blip for correct
answers and a low buzzer for wrong answers (inspired by sig_ok/sig_err
in WZab/morse_trainer)."""
import numpy as np

from morsetrainer.core import audio
from morsetrainer.core.morse import shaped_tone, silence


def ok_samples() -> np.ndarray:
    """Kurzer heller Quittungston für eine richtige Antwort."""
    return shaped_tone(1000, 0.08, amplitude=0.3)


def error_samples() -> np.ndarray:
    """Tiefer Doppelton für einen Fehler (oder fehlende Stimme bei der Ansage)."""
    beep = shaped_tone(150, 0.12, amplitude=0.35, harmonics=(1, 2))
    return np.concatenate([beep, silence(0.05), beep])


def play_ok() -> None:
    """Spielt den Quittungston ab; ohne Tonausgabe still."""
    audio.play_quietly(ok_samples())


def play_error() -> None:
    """Spielt den Fehlerton ab; ohne Tonausgabe still."""
    audio.play_quietly(error_samples())