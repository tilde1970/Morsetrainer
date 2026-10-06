"""Tonausgabe mit Fehlerbehandlung. Ohne Audiogerät, bei abgezogenem
Headset oder einem exklusiv belegten Gerät wirft sounddevice einen Fehler;
der soll den laufenden Modus sauber beenden und angezeigt werden, statt
unsichtbar in der Konsole zu landen und die Reiter gesperrt zu lassen.

- play(): für Töne, ohne die ein Durchgang nicht weitergeht; wirft
  AudioError mit einer lesbaren Meldung.
- play_quietly() und stop(): Nebensächliches (Quittungston, Schlusszeichen
  nach dem Stop); Fehler werden ignoriert.
- output_stream(): für die Modi mit eigenem Audio-Thread. Deren Fehler
  fängt der Thread mit ERRORS ab und übergibt describe(exc) an die
  Oberfläche; jeden anderen Fehler meldet er mit unexpected(exc) und gibt
  ihn weiter ans Fehlerprotokoll, damit die Übung nicht auf „läuft“
  stehen bleibt.
- keep_awake() / release(): ein stiller Ausgabestrom, solange das Programm
  läuft. PipeWire und PulseAudio legen ein Ausgabegerät nach wenigen
  Sekunden Stille schlafen; das Aufwecken dauert (bei Bluetooth-Kopfhörern
  spürbar), und der Anfang des nächsten Tons fehlt dann – meist das erste
  Zeichen nach Start, Blockwechsel oder Pause."""
import sounddevice as sd

from morsetrainer.core.morse import AUDIO_LATENCY, SAMPLE_RATE
from morsetrainer.i18n import tr

ERRORS = (getattr(sd, "PortAudioError", OSError), OSError, ValueError)


class AudioError(Exception):
    """Tonausgabe gescheitert; die Meldung ist schon für die Anzeige formuliert."""


def describe(exc: Exception) -> str:
    """Lesbare Meldung für einen Fehler der Tonausgabe (`exc` aus ERRORS)."""
    return tr("Keine Tonausgabe möglich: {error}").format(error=exc)


def unexpected(exc: Exception) -> str:
    """Lesbare Meldung für einen unerwarteten Fehler im Audio-Thread."""
    return tr("Durchgang abgebrochen, unerwarteter Fehler: {error}").format(error=str(exc) or type(exc).__name__)


def play(samples) -> None:
    """Spielt `samples` ab, ohne zu warten. Wirft AudioError, wenn es keine
    Tonausgabe gibt."""
    try:
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS as exc:
        raise AudioError(describe(exc)) from exc


def play_quietly(samples) -> None:
    """Wie play(), aber Fehler werden still übergangen (für Nebensächliches
    wie den Quittungston)."""
    try:
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS:
        pass


def stop() -> None:
    """Bricht eine laufende Wiedergabe von play()/play_quietly() ab."""
    try:
        sd.stop()
    except ERRORS:
        pass


def output_stream():
    """Neuer Ausgabestrom (mono, float32) für Modi mit eigenem Audio-Thread;
    als Kontextmanager verwenden."""
    return sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=AUDIO_LATENCY)


_keepalive = None


def _silence(outdata, frames, time_info, status) -> None:
    outdata.fill(0)


def keep_awake() -> None:
    """Stillen Strom öffnen (einmal); ohne Audiogerät ohne Wirkung."""
    global _keepalive
    if _keepalive is not None:
        return
    try:
        stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency="high",
                                 callback=_silence)
        stream.start()
    except (*ERRORS, TypeError, AttributeError):
        return
    _keepalive = stream


def release() -> None:
    """Schließt den stillen Strom von keep_awake() (beim Programmende)."""
    global _keepalive
    if _keepalive is None:
        return
    try:
        _keepalive.close()
    except ERRORS:
        pass
    _keepalive = None
