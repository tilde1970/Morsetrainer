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
  Oberfläche.
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
    pass


def describe(exc: Exception) -> str:
    return tr("Keine Tonausgabe möglich: {error}").format(error=exc)


def play(samples) -> None:
    try:
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS as exc:
        raise AudioError(describe(exc)) from exc


def play_quietly(samples) -> None:
    try:
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS:
        pass


def stop() -> None:
    try:
        sd.stop()
    except ERRORS:
        pass


def output_stream():
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
    global _keepalive
    if _keepalive is None:
        return
    try:
        _keepalive.close()
    except ERRORS:
        pass
    _keepalive = None
