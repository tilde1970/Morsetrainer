"""Probehören im Fenster Bandbedingungen: ein CQ in eigener Tonhöhe und
eigenem Tempo unter den gerade eingestellten Bedingungen, ohne in einen
Reiter zu wechseln. Änderungen im Fenster wirken sofort. Zählt für nichts
(keine Statistik, keine Übungszeit, kein Diplom)."""
import threading

import numpy as np

from morsetrainer.core import audio, band
from morsetrainer.core.morse import SAMPLE_RATE, build_text, silence

PREVIEW_SECONDS = 15
BLOCK_SECONDS = 0.05
PAUSE_SECONDS = 1.5  # zwischen zwei CQ-Rufen
FALLBACK_CALL = "DL1ABC"


def cq_text(call: str) -> str:
    call = call or FALLBACK_CALL
    return f"CQ CQ DE {call} {call} K"


class BandPreview:
    """`settings`: BandSettings; `params()` liefert (WpM, Tonhöhe,
    Rufzeichen). Läuft in einem eigenen Thread; Tk nur im GUI-Thread."""

    def __init__(self, settings, params):
        self.settings = settings
        self.params = params
        self.running = False
        self.error = None
        self.band = None
        self.freq = 600
        self.thread = None
        settings.subscribe(self._apply)

    def start(self) -> None:
        if self.running:
            return
        wpm, self.freq, call = self.params()
        conditions = band.BandConditions(1)
        band.apply_spec(conditions, self.settings.spec())
        conditions.prepare(self.freq)
        self.band = conditions
        self.error = None
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(conditions, wpm, cq_text(call)), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def _apply(self) -> None:
        """Einstellung geändert: gleich zu hören (wie im laufenden Durchgang)."""
        if self.running and self.band is not None:
            band.apply_spec(self.band, self.settings.spec())
            self.band.prepare(self.freq)

    def _run(self, conditions, wpm: int, text: str) -> None:
        try:
            self._play(conditions, wpm, text)
        except audio.ERRORS as exc:
            self.error = audio.describe(exc)
        except Exception as exc:
            self.error = audio.unexpected(exc)
            raise  # ins Fehlerprotokoll (threading.excepthook)
        finally:
            self.running = False

    def _play(self, conditions, wpm: int, text: str) -> None:
        n = int(SAMPLE_RATE * BLOCK_SECONDS)
        total = PREVIEW_SECONDS * SAMPLE_RATE
        signal, pos = np.zeros(0, dtype=np.float32), 0
        with audio.output_stream() as stream:
            for _ in range(0, total, n):
                if not self.running:
                    break
                if pos >= len(signal):
                    # Je Ruf neu gebaut: ein geänderter Chirp ist beim nächsten zu hören.
                    signal = np.concatenate([build_text(text, wpm, self.freq, chirp=conditions.chirp_for(0)),
                                             silence(PAUSE_SECONDS)]).astype(np.float32)
                    pos = 0
                block = signal[pos:pos + n]
                pos += len(block)
                stream.write(conditions.mix([(block, 0)], n))
