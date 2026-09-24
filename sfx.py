"""Non-Morse feedback sounds: a short confirmation blip for correct
answers and a low buzzer for wrong answers (inspired by sig_ok/sig_err
in WZab/morse_trainer)."""
import numpy as np
import sounddevice as sd

from morse import AUDIO_LATENCY, SAMPLE_RATE, shaped_tone, silence


def ok_samples() -> np.ndarray:
    return shaped_tone(1000, 0.08, amplitude=0.3)


def error_samples() -> np.ndarray:
    beep = shaped_tone(150, 0.12, amplitude=0.35, harmonics=(1, 2))
    return np.concatenate([beep, silence(0.05), beep])


def play_ok() -> None:
    sd.play(ok_samples(), SAMPLE_RATE, latency=AUDIO_LATENCY)


def play_error() -> None:
    sd.play(error_samples(), SAMPLE_RATE, latency=AUDIO_LATENCY)