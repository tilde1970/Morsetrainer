"""MP3-Export mit lameenc (LAME, als kleines Wheel für Linux und Windows).

Übungen lassen sich so unterwegs hören, im Auto oder auf dem Handy. Mono,
48 kHz wie die Tonausgabe, 96 kbit/s: für Töne und Sprache mehr als genug,
eine Stunde sind rund 43 MB."""
import numpy as np

from morsetrainer.core.morse import SAMPLE_RATE
from morsetrainer.i18n import tr

BITRATE_KBPS = 96


class Mp3Error(Exception):
    """MP3 lässt sich nicht schreiben; die Meldung ist schon für die Anzeige formuliert."""


def available():
    """None, wenn MP3 geschrieben werden kann, sonst der Grund."""
    try:
        import lameenc  # noqa: F401
    except ImportError:
        return tr("MP3-Export nicht verfügbar: lameenc ist nicht installiert (pip install lameenc).")
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
            raise Mp3Error(tr("{path} lässt sich nicht schreiben: {error}").format(path=path, error=exc)) from exc
        self.seconds = 0.0

    def write(self, samples: np.ndarray) -> None:
        """Hängt `samples` (float32, −1 … 1) an die MP3-Datei an."""
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        self.file.write(self.encoder.encode(pcm))
        self.seconds += len(samples) / SAMPLE_RATE

    def close(self) -> None:
        """Schreibt den Rest aus dem Encoder und schließt die Datei."""
        try:
            self.file.write(self.encoder.flush())
        finally:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
