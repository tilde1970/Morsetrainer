"""Bandgeräusch in der Antwortpause der Abfragemodi: Nach jeder Sequenz
läuft das Band leiser weiter (Rauschen, QRN, QRM …), bis die nächste
Sequenz kommt, statt abrupt zu verstummen. Am Ende der Sequenz wird
übergeblendet, vor der nächsten wieder ausgeblendet.

Ein eigener Ausgabestrom in einem eigenen Thread, neben audio.play() für
die Sequenzen. Er mischt aus einer Kopie der BandConditions
(BandConditions.fork), damit der GUI-Thread derweil die nächste Sequenz
aus dem Original berechnen kann. Fehler der Tonausgabe übergeht er still:
Ohne Pausengeräusch geht die Übung trotzdem weiter."""
import threading
import time

import numpy as np

from morsetrainer.core import audio
from morsetrainer.core.morse import SAMPLE_RATE

# So viel leiser als während der Sequenz (das Ohr soll sich beim Tippen
# erholen, das Band aber nicht verschwinden).
PAUSE_GAIN_DB = -6.0
PAUSE_GAIN = 10 ** (PAUSE_GAIN_DB / 20)
BLOCK_SECONDS = 0.02
# Über- und Ausblenden; so lang wie das Ausblenden am Ende der Sequenz
# (band.PRESET_FADE_SECONDS), damit beide zusammen eine Überblendung ergeben.
FADE_SECONDS = 0.04


class PauseNoise:
    """start(band, delay) nach dem Abspielen einer Sequenz, fade_out() mit
    der nächsten, close() am Ende des Durchgangs."""

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        # Stoppsignal des laufenden Threads; jeder Thread hat sein eigenes,
        # damit ein close() mit gleich folgendem start() den alten sicher
        # beendet und kein zweiter Strom mitläuft.
        self.stop_event = None
        self.source = None  # BandConditions-Kopie, die gerade klingt
        self.pending = None  # (Kopie, time.time(), ab der sie klingen soll)
        self.gain = 0.0
        self.target = 0.0

    def start(self, conditions, delay: float) -> None:
        """Ab `delay` Sekunden von jetzt das Band leiser weiterlaufen lassen,
        von dem Stand aus, den `conditions` gerade hat (Ende der eben
        berechneten Sequenz)."""
        twin = conditions.fork()
        with self.lock:
            self.pending = (twin, time.time() + max(delay, 0.0))
            if self.stop_event is not None:
                return
            self.stop_event = threading.Event()
            self.thread = threading.Thread(target=self._run, args=(self.stop_event,), daemon=True)
        self.thread.start()

    @property
    def running(self) -> bool:
        """Läuft gerade ein Strom (oder wird gleich geöffnet)?"""
        return self.stop_event is not None

    def fade_out(self) -> None:
        """Die nächste Sequenz beginnt: ausblenden, nichts Neues mehr starten."""
        with self.lock:
            self.pending = None
            self.target = 0.0

    def close(self) -> None:
        """Durchgang zu Ende: Strom schließen (nach dem laufenden Block)."""
        with self.lock:
            self.pending = None
            self.target = 0.0
            stop_event, self.stop_event = self.stop_event, None
        if stop_event is not None:
            stop_event.set()

    def _run(self, stop_event) -> None:
        try:
            with audio.output_stream() as stream:
                n = int(SAMPLE_RATE * BLOCK_SECONDS)
                while not stop_event.is_set():
                    stream.write(self.block(n))
        except audio.ERRORS:
            pass
        finally:
            with self.lock:
                # Ohne Tonausgabe beendet: der nächste start() versucht es neu.
                if self.stop_event is stop_event:
                    self.stop_event = None

    def block(self, n: int) -> np.ndarray:
        """Die nächsten `n` Samples (still, solange nichts klingen soll)."""
        with self.lock:
            # Eine neue Kopie übernimmt erst, wenn die alte ganz ausgeblendet
            # ist; sonst gäbe es einen Sprung im Rauschen.
            if self.pending is not None and time.time() >= self.pending[1] and self.gain == 0.0:
                self.source, _ = self.pending
                self.pending = None
                self.target = PAUSE_GAIN
            source, target, before = self.source, self.target, self.gain
        if source is None or (before == 0.0 and target == 0.0):
            return np.zeros(n, dtype=np.float32)
        step = PAUSE_GAIN * n / (FADE_SECONDS * SAMPLE_RATE)
        after = min(before + step, target) if target > before else max(before - step, target)
        out = source.mix([], n) * np.linspace(before, after, n, dtype=np.float32)
        with self.lock:
            self.gain = after
            if after == 0.0 and self.target == 0.0:
                self.source = None
        return out.astype(np.float32)
