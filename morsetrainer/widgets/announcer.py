"""Sprachansage für blinde und sehbehinderte Nutzer: Das Programm sagt mit
der eingebauten Stimme (core/speech.py) selbst an, was sonst nur auf dem
Bildschirm steht – Ergebnis jeder Antwort, Ende eines Durchgangs,
Reiterwechsel, Karten der Tagesübung. Das geht ohne Screenreader, den Tk
nicht bedient.

Ein- und ausgeschaltet mit F9 (oder unter „Weitere Optionen“); F11 liest
vor, wo man gerade ist.

Morsezeichen und Ansage teilen sich die Tonausgabe (ein neuer Ton bricht
den laufenden ab). Deshalb gibt say() den Ablauf erst frei, wenn die Ansage
zu Ende ist: Die Reiter übergeben, was danach kommt, als `then`.

Die Stimme ist deutsch, daher sind die Ansagen immer deutsch, auch bei
englischer Oberfläche.

Erzeugt wird die Sprache in einem Hintergrund-Thread; die Oberfläche fragt
mit after() nach, ob sie fertig ist (Tk darf nur aus seinem eigenen Thread
bedient werden)."""
import threading
import tkinter as tk

from morsetrainer.core import audio, speech
from morsetrainer.core.morse import AUDIO_LATENCY, SAMPLE_RATE

# Pause nach einer Ansage, bevor es weitergeht.
AFTER_SPEECH_MS = 250
POLL_MS = 20
CACHE_SIZE = 64

_instance = None
_synth_lock = threading.Lock()  # Piper nicht aus zwei Threads zugleich


class Announcer:
    def __init__(self, root):
        self.root = root
        self.var = tk.BooleanVar(value=False)
        self.token = 0
        self._cache = {}
        # Stimme schon laden, sobald die Ansage an ist (knapp 1 s).
        self.var.trace_add("write", lambda *_: self.var.get() and self.available() is None
                           and speech.speaker.voice is None and speech.speaker.preload())

    def enabled(self) -> bool:
        return self.var.get()

    def available(self):
        """None, wenn angesagt werden kann, sonst der Grund."""
        return speech.speaker.available()

    def say(self, text: str, then=None, force: bool = False) -> None:
        """`text` ansagen, danach `then()` aufrufen. Ist die Ansage aus (und
        nicht `force`) oder keine Stimme da, kommt `then` sofort. Eine neue
        Ansage verdrängt eine noch nicht begonnene ältere; deren `then` wird
        trotzdem aufgerufen, damit kein Ablauf hängen bleibt."""
        if not text or not (force or self.enabled()) or self.available() is not None:
            if then is not None:
                then()
            return
        self.token += 1
        token = self.token
        result = {}

        def work():
            result["samples"] = self._synth(text)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self.root.after(POLL_MS, poll)
                return
            samples = result.get("samples")
            delay = 0
            if token == self.token and samples is not None and len(samples):
                audio.play_quietly(samples)
                delay = int((len(samples) / SAMPLE_RATE + AUDIO_LATENCY) * 1000) + AFTER_SPEECH_MS
            if then is not None:
                self.root.after(delay, then)

        poll()

    def _synth(self, text: str):
        samples = self._cache.get(text)
        if samples is None:
            with _synth_lock:
                try:
                    samples = speech.speaker.synth(text)
                except Exception:  # Stimme defekt: lieber still als abgestürzt
                    samples = None
            if samples is not None:
                if len(self._cache) >= CACHE_SIZE:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[text] = samples
        return samples


def install(root) -> Announcer:
    """Eine Ansage für das ganze Programm (vom Hauptfenster)."""
    global _instance
    _instance = Announcer(root)
    return _instance


def get():
    return _instance


def active() -> bool:
    """Ist die Ansage eingeschaltet (und eine Stimme vorhanden)?"""
    return _instance is not None and _instance.enabled() and _instance.available() is None


def say(text: str, then=None) -> None:
    """Ansagen, falls eingeschaltet; `then` kommt in jedem Fall."""
    if _instance is None:
        if then is not None:
            then()
        return
    _instance.say(text, then)


def spell(text: str) -> str:
    """Buchstabiert (Ka, Emm, U …); leer wird „nichts“."""
    return speech.spoken(text) or "nichts"
