"""Tonausgabe direkt über PulseAudio (libpulse-simple), ohne PortAudio und
die ALSA-Schicht dazwischen. Unter Linux bedient pipewire-pulse dieselbe
Schnittstelle. Nur ctypes, keine zusätzliche Abhängigkeit; fehlt die
Bibliothek, ist available() False und audio.py bleibt bei sounddevice.

- PulseStream: wie ein sounddevice-OutputStream (write, latency, stop, close),
  schreibt blockierend.
- Player: ein dauerhaft offener Strom mit eigenem Thread für Einzeltöne
  (play() kehrt sofort zurück). Im Leerlauf schreibt er Stille; das hält das
  Ausgabegerät wach, sonst fehlt der Anfang des nächsten Tons."""
import ctypes
import ctypes.util
import queue
import threading

import numpy as np

_FLOAT32LE = 5
_PLAYBACK = 1
_UNSET = 0xFFFFFFFF
_IDLE_CHUNK_SECONDS = 0.02

_lib = None
_loaded = False


class _SampleSpec(ctypes.Structure):
    _fields_ = [("format", ctypes.c_int), ("rate", ctypes.c_uint32), ("channels", ctypes.c_uint8)]


class _BufferAttr(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ("maxlength", "tlength", "prebuf", "minreq", "fragsize")]


class PulseError(OSError):
    """Fehler von libpulse-simple; erscheint in audio.ERRORS."""


def _load():
    global _lib, _loaded
    if _loaded:
        return _lib
    _loaded = True
    path = ctypes.util.find_library("pulse-simple")
    try:
        lib = ctypes.CDLL(path or "libpulse-simple.so.0")
        pulse = ctypes.CDLL(ctypes.util.find_library("pulse") or "libpulse.so.0")
    except OSError:
        return None
    vp, ip, c_int = ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int
    lib.pa_simple_new.restype = vp
    lib.pa_simple_new.argtypes = [ctypes.c_char_p, ctypes.c_char_p, c_int, ctypes.c_char_p, ctypes.c_char_p,
                                  ctypes.POINTER(_SampleSpec), vp, ctypes.POINTER(_BufferAttr), ip]
    lib.pa_simple_write.argtypes = [vp, ctypes.c_char_p, ctypes.c_size_t, ip]
    lib.pa_simple_drain.argtypes = [vp, ip]
    lib.pa_simple_flush.argtypes = [vp, ip]
    lib.pa_simple_free.argtypes = [vp]
    lib.pa_simple_free.restype = None
    pulse.pa_strerror.restype = ctypes.c_char_p
    pulse.pa_strerror.argtypes = [c_int]
    lib.strerror = pulse.pa_strerror
    _lib = lib
    return lib


def available() -> bool:
    return _load() is not None


def _fail(what: str, code: int) -> PulseError:
    text = _lib.strerror(code)
    return PulseError(f"PulseAudio: {what}: {text.decode(errors='replace') if text else code}")


class PulseStream:
    """Mono-float32-Ausgabestrom. `latency` ist die eingestellte Pufferzeit."""

    def __init__(self, samplerate: int, latency: float, name: str = "Morsetrainer"):
        lib = _load()
        if lib is None:
            raise PulseError("PulseAudio: libpulse-simple nicht gefunden")
        self.latency = latency
        self._lock = threading.Lock()
        spec = _SampleSpec(_FLOAT32LE, samplerate, 1)
        attr = _BufferAttr(_UNSET, int(latency * samplerate) * 4, _UNSET, _UNSET, _UNSET)
        error = ctypes.c_int(0)
        self._handle = lib.pa_simple_new(None, name.encode(), _PLAYBACK, None, b"Morse", ctypes.byref(spec), None,
                                         ctypes.byref(attr), ctypes.byref(error))
        if not self._handle:
            raise _fail("Verbindung", error.value)

    @property
    def active(self) -> bool:
        return self._handle is not None

    def start(self) -> None:
        """Der Strom läuft ab dem Öffnen; nur für die Schnittstelle."""

    def write(self, samples) -> bool:
        """Schreibt `samples` und wartet, bis sie im Puffer Platz haben.
        Rückgabe wie bei sounddevice (Underflow): hier immer False."""
        data = np.ascontiguousarray(samples, dtype=np.float32).tobytes()
        error = ctypes.c_int(0)
        with self._lock:
            if self._handle is None:
                raise PulseError("PulseAudio: Strom geschlossen")
            if _lib.pa_simple_write(self._handle, data, len(data), ctypes.byref(error)) < 0:
                raise _fail("Schreiben", error.value)
        return False

    def flush(self) -> None:
        """Verwirft, was noch im Puffer liegt (Abbruch)."""
        error = ctypes.c_int(0)
        with self._lock:
            if self._handle is not None:
                _lib.pa_simple_flush(self._handle, ctypes.byref(error))

    def stop(self) -> None:
        """Wartet, bis der Puffer ausgespielt ist."""
        error = ctypes.c_int(0)
        with self._lock:
            if self._handle is not None:
                _lib.pa_simple_drain(self._handle, ctypes.byref(error))

    def close(self) -> None:
        with self._lock:
            handle, self._handle = self._handle, None
            if handle:
                _lib.pa_simple_free(handle)


class Player:
    """Dauerhaft offener Strom für Einzeltöne: play() stellt den Ton in die
    Warteschlange und kehrt sofort zurück, cancel() bricht ab."""

    def __init__(self, samplerate: int, latency: float):
        self.samplerate = samplerate
        self.stream = PulseStream(samplerate, latency, "Morsetrainer")
        self._queue = queue.Queue()
        self._generation = 0
        self._closed = False
        self.error = None
        self._thread = threading.Thread(target=self._run, name="pulse-player", daemon=True)
        self._thread.start()

    @property
    def alive(self) -> bool:
        return not self._closed and self.error is None and self._thread.is_alive()

    def play(self, samples) -> None:
        if not self.alive:
            raise self.error or PulseError("PulseAudio: Wiedergabe beendet")
        self._generation += 1
        self.stream.flush()
        self._queue.put((self._generation, np.ascontiguousarray(samples, dtype=np.float32)))

    def cancel(self) -> None:
        self._generation += 1
        self.stream.flush()

    def close(self) -> None:
        self._closed = True
        self._generation += 1
        self._queue.put(None)
        self._thread.join(timeout=1.0)
        self.stream.close()

    def _run(self) -> None:
        chunk = int(self.samplerate * _IDLE_CHUNK_SECONDS)
        silence = np.zeros(chunk, dtype=np.float32)
        try:
            while not self._closed:
                try:
                    job = self._queue.get_nowait()
                except queue.Empty:
                    self.stream.write(silence)  # blockiert im Takt des Geräts
                    continue
                if job is None:
                    return
                generation, samples = job
                for start in range(0, len(samples), chunk):
                    if generation != self._generation:
                        break
                    self.stream.write(samples[start:start + chunk])
        except OSError as exc:
            self.error = exc
