"""MP3-Export mit lameenc (LAME, als kleines Wheel für Linux und Windows).

Übungen lassen sich so unterwegs hören, im Auto oder auf dem Handy. Mono,
48 kHz wie die Tonausgabe, 96 kbit/s: für Töne und Sprache mehr als genug,
eine Stunde sind rund 43 MB."""
import numpy as np

from morsetrainer.core.morse import SAMPLE_RATE

BITRATE_KBPS = 96


class Mp3Error(Exception):
    pass


def available():
    """None, wenn MP3 geschrieben werden kann, sonst der Grund."""
    try:
        import lameenc  # noqa: F401
    except ImportError:
        return "MP3-Export nicht verfügbar: lameenc ist nicht installiert (pip install lameenc)."
    return None


class Mp3Writer:
    """Schreibt float32-Blöcke nacheinander in eine MP3-Datei, damit auch
    eine Stunde Übung nicht auf einmal im Speicher liegen muss."""

    def __init__(self, path):
        reason = available()
        if reason:
            raise Mp3Error(reason)
        import lameenc
        self.encoder = lameenc.Encoder()
        self.encoder.set_bit_rate(BITRATE_KBPS)
        self.encoder.set_in_sample_rate(SAMPLE_RATE)
        self.encoder.set_channels(1)
        self.encoder.set_quality(2)
        try:
            self.file = open(path, "wb")
        except OSError as exc:
            raise Mp3Error(f"{path} lässt sich nicht schreiben: {exc}") from exc
        self.seconds = 0.0

    def write(self, samples: np.ndarray) -> None:
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        self.file.write(self.encoder.encode(pcm))
        self.seconds += len(samples) / SAMPLE_RATE

    def close(self) -> None:
        try:
            self.file.write(self.encoder.flush())
        finally:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
