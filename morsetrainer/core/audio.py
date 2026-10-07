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
  Zeichen nach Start, Blockwechsel oder Pause.

Öffnen und Schließen von Strömen ist in PortAudio auf keiner Plattform
threadsicher; play() und stop() öffnen bzw. schließen intern auch einen.
Alles davon läuft deshalb unter einer gemeinsamen Sperre (_lock), damit
etwa der Pausen-Thread seinen Strom nicht genau dann schließt, wenn die
Oberfläche das Schlusszeichen startet. Schreiben läuft ohne Sperre."""
import contextlib
import re
import threading

import sounddevice as sd

from morsetrainer.core.morse import AUDIO_LATENCY, SAMPLE_RATE
from morsetrainer.i18n import N_, tr

ERRORS = (getattr(sd, "PortAudioError", OSError), OSError, ValueError)
_lock = threading.RLock()


class AudioError(Exception):
    """Tonausgabe gescheitert; die Meldung ist schon für die Anzeige formuliert."""


# Häufige PortAudio-Fehler mit dem, was man dagegen tun kann.
_HINTS = {
    -9985: N_("Das Audiogerät ist belegt. Gibt ein anderes Programm (etwa SDR- oder Audio-Software im "
              "Exklusivmodus) es frei, geht es weiter."),
    -9996: N_("Kein Audiogerät gefunden. Kopfhörer oder Lautsprecher anschließen, im System als "
              "Standardausgabe wählen und noch einmal starten."),
    -9997: N_("Das Audiogerät kann die Abtastrate von 48 kHz nicht. Im System ein anderes Gerät als "
              "Standardausgabe wählen."),
    -9986: N_("Das Audiogerät ist nicht mehr verfügbar (abgezogen?). Wieder anschließen oder im System ein "
              "anderes wählen und noch einmal starten."),
}


def _error_code(exc: Exception):
    """PortAudio-Fehlercode aus `exc` (zweites Argument oder „[PaErrorCode -9985]“), sonst None."""
    if len(exc.args) > 1 and isinstance(exc.args[1], int):
        return exc.args[1]
    found = re.search(r"PaErrorCode (-?\d+)", str(exc))
    return int(found.group(1)) if found else None


def describe(exc: Exception) -> str:
    """Lesbare Meldung für einen Fehler der Tonausgabe (`exc` aus ERRORS):
    bei bekannten Fehlern mit dem nächsten Schritt, der rohe Text dahinter
    für Fehlerberichte."""
    hint = _HINTS.get(_error_code(exc))
    if hint:
        return tr("Keine Tonausgabe möglich. {hint} ({error})").format(hint=tr(hint), error=exc)
    return tr("Keine Tonausgabe möglich: {error}").format(error=exc)


def unexpected(exc: Exception) -> str:
    """Lesbare Meldung für einen unerwarteten Fehler im Audio-Thread."""
    return tr("Durchgang abgebrochen, unerwarteter Fehler: {error}").format(error=str(exc) or type(exc).__name__)


# Gerät abgezogen bzw. keins gefunden: PortAudio kennt nur die Geräte vom
# Programmstart (unter macOS folgt es einem Wechsel sonst gar nicht).
_REINIT_CODES = (-9986, -9996)


def _reinit() -> bool:
    """PortAudio neu starten, damit es die aktuellen Geräte und das neue
    Standardgerät kennt. Schließt alle offenen Ströme (auch den stillen von
    keep_awake, der danach neu geöffnet wird). False, wenn das nicht geht."""
    global _keepalive
    terminate, initialize = getattr(sd, "_terminate", None), getattr(sd, "_initialize", None)
    if terminate is None or initialize is None:
        return False
    with _lock:
        had_keepalive, _keepalive = _keepalive is not None, None
        try:
            terminate()
            initialize()
        except ERRORS:
            return False
    if had_keepalive:
        keep_awake()
    return True


def play(samples) -> None:
    """Spielt `samples` ab, ohne zu warten. Wirft AudioError, wenn es keine
    Tonausgabe gibt; ist das Gerät verschwunden, wird einmal mit neu
    eingelesenen Geräten wiederholt."""
    try:
        with _lock:
            sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
        return
    except ERRORS as exc:
        if _error_code(exc) not in _REINIT_CODES or not _reinit():
            raise AudioError(describe(exc)) from exc
    try:
        with _lock:
            sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS as exc:
        raise AudioError(describe(exc)) from exc


def play_quietly(samples) -> None:
    """Wie play(), aber Fehler werden still übergangen (für Nebensächliches
    wie den Quittungston)."""
    try:
        with _lock:
            sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
    except ERRORS:
        pass


def stop() -> None:
    """Bricht eine laufende Wiedergabe von play()/play_quietly() ab."""
    try:
        with _lock:
            sd.stop()
    except ERRORS:
        pass


def _open_stream():
    """Ausgabestrom öffnen und starten, unter der Sperre."""
    with _lock:
        stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=AUDIO_LATENCY)
        try:
            stream.start()
        except BaseException:
            stream.close()
            raise
    return stream


@contextlib.contextmanager
def output_stream():
    """Neuer Ausgabestrom (mono, float32) für Modi mit eigenem Audio-Thread,
    als Kontextmanager: geöffnet und geschlossen unter der Sperre, am Ende
    erst ausgespielt; ist das Gerät verschwunden, einmal mit neu
    eingelesenen Geräten versucht."""
    try:
        stream = _open_stream()
    except ERRORS as exc:
        if _error_code(exc) not in _REINIT_CODES or not _reinit():
            raise
        stream = _open_stream()  # mit neu eingelesenen Geräten
    try:
        yield stream
    finally:
        try:
            stream.stop()  # wartet, bis der Puffer ausgespielt ist; ohne Sperre
        finally:
            with _lock:
                stream.close()


_keepalive = None


def _silence(outdata, frames, time_info, status) -> None:
    outdata.fill(0)


def keep_awake() -> None:
    """Stillen Strom öffnen (einmal); ohne Audiogerät ohne Wirkung."""
    global _keepalive
    if _keepalive is not None:
        return
    try:
        with _lock:
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
        with _lock:
            _keepalive.close()
    except ERRORS:
        pass
    _keepalive = None
