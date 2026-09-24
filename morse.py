"""Morse code table and audio generation."""
import numpy as np

MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "/": "-..-.",
    "=": "-...-", "+": ".-.-.",
}

# 48 kHz ist die native Rate von PipeWire/PulseAudio und den meisten
# Soundkarten; bei 44,1 kHz würde der Soundserver umrechnen.
SAMPLE_RATE = 48000

# Betriebstechnik am Anfang und Ende eines Übungsdurchgangs:
# "VVV =" (Achtung, Trennung) und "+" (AR, Ende der Nachricht).
START_TEXT = "VVV ="
END_TEXT = "+"

# Deutlich unter Vollaussteuerung, damit Resampling oder Mixer im
# Soundserver nicht übersteuern (Übersteuern klingt nach Knistern).
AMPLITUDE = 0.5

# Ausgabelatenz für alle Streams. Mit sounddevice' "high" (~35 ms) zwingt
# das Programm PipeWire auf einen Takt von nur 256 Samples; dann reicht kurze
# Systemlast für Aussetzer (leichte Spratzer mitten im Ton). 100 ms geben
# PipeWire 1024er-Blöcke und sind fürs Morsen unkritisch – die Verzögerung
# wird bei der Reaktionszeit herausgerechnet.
AUDIO_LATENCY = 0.1

# Feste Flankenlänge für Ein-/Ausblenden, unabhängig von der Tonlänge.
# 5 ms mit Raised-Cosine-Form ist üblicher CW-Standard: kurz genug für
# hohe Geschwindigkeiten, lang genug gegen Tastklicks.
RAMP_SECONDS = 0.005


def shaped_tone(freq: float, duration: float, amplitude: float = AMPLITUDE, harmonics=(1,), chirp=None) -> np.ndarray:
    """Sinuston mit weichen Raised-Cosine-Flanken, als float32.

    `chirp=(delta_hz, tau_s)` simuliert einen schlecht stabilisierten Sender:
    beim Tasten liegt die Frequenz um delta_hz daneben und läuft mit der
    Zeitkonstante tau_s auf `freq` zurück."""
    n = int(round(SAMPLE_RATE * duration))
    t = np.arange(n) / SAMPLE_RATE
    phase = 2 * np.pi * freq * t
    if chirp is not None:
        delta, tau = chirp
        # Integral der Momentanfrequenz freq + delta * exp(-t / tau).
        phase = phase + 2 * np.pi * delta * tau * (1 - np.exp(-t / tau))
    wave = sum(np.sin(h * phase) for h in harmonics) / len(harmonics)
    ramp_len = min(int(SAMPLE_RATE * RAMP_SECONDS), n // 2)
    if ramp_len > 0:
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(ramp_len) / ramp_len))
        wave[:ramp_len] *= ramp
        wave[n - ramp_len:] *= ramp[::-1]
    return (wave * amplitude).astype(np.float32)


def silence(duration: float) -> np.ndarray:
    return np.zeros(int(round(SAMPLE_RATE * duration)), dtype=np.float32)


def char_gap_seconds(wpm: int, farnsworth_wpm=None) -> float:
    """Pause nach einem Zeichen. Normal 3 Dits; mit Farnsworth (effektive
    Geschwindigkeit `farnsworth_wpm` < `wpm`) wird sie nach der ARRL-Formel
    gestreckt: Die Zeichen selbst bleiben bei `wpm`, die 19 Pausen-Einheiten
    im Wort "PARIS " (4 Zeichenpausen à 3 + 1 Wortpause à 7) werden so
    verlängert, dass sich insgesamt `farnsworth_wpm` ergibt."""
    if farnsworth_wpm and farnsworth_wpm < wpm:
        total_delay = (60 * wpm - 37.2 * farnsworth_wpm) / (farnsworth_wpm * wpm)
        return 3 * total_delay / 19
    return 3 * 1.2 / wpm


def build_samples(char: str, wpm: int, freq: int, farnsworth_wpm=None, chirp=None) -> np.ndarray:
    """Render a single character to a mono float32 waveform.

    Timing follows the standard Morse convention where one dit = 1.2/wpm
    seconds; inter-element gap = 1 dit, inter-character gap = 3 dits
    (appended at the end so consecutive characters sound natural), or the
    stretched Farnsworth gap when `farnsworth_wpm` is given. `chirp` is
    passed on to shaped_tone.
    """
    code = MORSE_CODE.get(char.upper())
    if code is None:
        return np.zeros(0, dtype=np.float32)

    dit = 1.2 / wpm
    dah = dit * 3
    gap = dit  # gap between elements within a character
    char_gap = char_gap_seconds(wpm, farnsworth_wpm)  # gap after the character

    tone_dit = shaped_tone(freq, dit, chirp=chirp)
    tone_dah = shaped_tone(freq, dah, chirp=chirp)
    silence_gap = silence(gap)
    silence_char = silence(char_gap)

    parts = []
    for i, symbol in enumerate(code):
        if i > 0:
            parts.append(silence_gap)
        parts.append(tone_dit if symbol == "." else tone_dah)
    parts.append(silence_char)

    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


def word_gap_extra_seconds(wpm: int, farnsworth_wpm=None) -> float:
    """Zusätzliche Pause für einen Wortabstand: 7 statt 3 Einheiten, also
    4 Einheiten über die Zeichenpause hinaus (bei Farnsworth gestreckt)."""
    return char_gap_seconds(wpm, farnsworth_wpm) * 4 / 3


def build_text(text: str, wpm: int, freq: int, farnsworth_wpm=None, chirp=None) -> np.ndarray:
    """Wie build_samples, aber für einen ganzen Text; Leerzeichen werden zu
    Wortabständen."""
    parts = [
        silence(word_gap_extra_seconds(wpm, farnsworth_wpm)) if ch == " "
        else build_samples(ch, wpm, freq, farnsworth_wpm, chirp)
        for ch in text
    ]
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


def duration_seconds(char: str, wpm: int, farnsworth_wpm=None) -> float:
    code = MORSE_CODE.get(char.upper())
    if code is None:
        return 0.0
    dit = 1.2 / wpm
    dah = dit * 3
    gap = dit
    total = char_gap_seconds(wpm, farnsworth_wpm)
    for i, symbol in enumerate(code):
        if i > 0:
            total += gap
        total += dit if symbol == "." else dah
    return total


def code_units(char: str) -> float:
    """Length of a character in dit-units (dot=1, dash=3, inter-element
    gap=1, trailing inter-character gap=3), independent of WPM.

    Used to translate a measured real-world response time back into an
    "effective WPM": effective_wpm = code_units(char) * 1.2 / elapsed_seconds.
    This mirrors the standard PARIS timing formula (dit = 1.2 / wpm) but
    applied per character instead of per standard word.
    """
    code = MORSE_CODE.get(char.upper())
    if code is None:
        return 0.0
    units = 3.0  # trailing inter-character gap
    for i, symbol in enumerate(code):
        if i > 0:
            units += 1  # inter-element gap
        units += 1 if symbol == "." else 3
    return units