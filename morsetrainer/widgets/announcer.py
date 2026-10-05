"""Sprachansage für blinde und sehbehinderte Nutzer: Das Programm sagt mit
der eingebauten Stimme (core/speech.py) selbst an, was sonst nur auf dem
Bildschirm steht – Ergebnis jeder Antwort, Ende eines Durchgangs,
Reiterwechsel, Karten der Tagesübung. Das geht ohne Screenreader, den Tk
nicht bedient.

Ein- und ausgeschaltet mit F9 (oder unter „Einstellungen“); F11 liest
vor, wo man gerade ist.

Morsezeichen und Ansage teilen sich die Tonausgabe (ein neuer Ton bricht
den laufenden ab). Deshalb gibt say() den Ablauf erst frei, wenn die Ansage
zu Ende ist: Die Reiter übergeben, was danach kommt, als `then`.

Gesprochen wird in der Sprache der Oberfläche, mit der deutschen bzw.
englischen Stimme (core/speech.py, VOICES).

Erzeugt wird die Sprache in einem Hintergrund-Thread; die Oberfläche fragt
mit after() nach, ob sie fertig ist (Tk darf nur aus seinem eigenen Thread
bedient werden)."""
import re
import threading
import time
import tkinter as tk

from morsetrainer import i18n
from morsetrainer.core import audio, sfx, speech
from morsetrainer.core.morse import AUDIO_LATENCY, SAMPLE_RATE
from morsetrainer.i18n import tr

# Pause nach einer Ansage, bevor es weitergeht.
AFTER_SPEECH_MS = 250
POLL_MS = 20
CACHE_SIZE = 64
# Lange Ansagen (Statistik) satzweise: der erste Satz klingt sofort, die
# übrigen entstehen, während er läuft. Kurze bleiben ein Stück.
SPLIT_ABOVE_CHARS = 60
CHUNK_CHARS = 150

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
                           and self.speaker().voice is None and self.speaker().preload())

    def enabled(self) -> bool:
        return self.var.get()

    @staticmethod
    def speaker():
        """Die Stimme in der Sprache der Oberfläche."""
        return speech.speaker_for(i18n.LANG)

    def available(self):
        """None, wenn angesagt werden kann, sonst der Grund."""
        return self.speaker().available()

    def say(self, text: str, then=None, force: bool = False) -> None:
        """`text` ansagen, danach `then()` aufrufen. Ist die Ansage aus (und
        nicht `force`) oder keine Stimme da, kommt `then` sofort. Eine neue
        Ansage verdrängt eine noch nicht begonnene ältere; deren `then` wird
        trotzdem aufgerufen, damit kein Ablauf hängen bleibt."""
        if not text or not (force or self.enabled()) or self.available() is not None:
            if force and text and self.available() is not None:
                sfx.play_error()  # ausdrücklich verlangt (F9, F11), aber keine Stimme: hörbar melden
            if then is not None:
                then()
            return
        self.token += 1
        token = self.token
        chunks = _chunks(text)
        results = {}  # Nr. -> Samples (oder None), sobald erzeugt

        def work():
            for index, chunk in enumerate(chunks):
                if token != self.token:
                    return  # verdrängt: den Rest nicht mehr erzeugen
                results[index] = self._synth(chunk)

        threading.Thread(target=work, daemon=True).start()
        state = {"next": 0, "free_at": 0.0}  # nächstes Stück; wann das laufende zu Ende ist

        def poll():
            if token != self.token:  # verdrängt: Ablauf trotzdem freigeben
                if then is not None:
                    then()
                return
            index = state["next"]
            if index >= len(chunks):
                if then is not None:
                    wait = max(state["free_at"] - time.time(), 0.0)
                    self.root.after(int(wait * 1000) + AFTER_SPEECH_MS, then)
                return
            if index in results and time.time() >= state["free_at"]:
                samples = results[index]
                if samples is not None and len(samples):
                    audio.play_quietly(samples)
                    state["free_at"] = time.time() + len(samples) / SAMPLE_RATE + (AUDIO_LATENCY if index == 0 else 0)
                state["next"] += 1
            self.root.after(POLL_MS, poll)

        poll()

    def render(self, text: str, deliver) -> None:
        """Sprache für `text` im Hintergrund erzeugen und `deliver(samples)`
        im Tk-Thread aufrufen, ohne sie abzuspielen (für Reiter mit eigenem
        Tonstrom, z. B. den Contest-Mischer). Nichts, wenn die Ansage aus ist."""
        if not text or not self.enabled() or self.available() is not None:
            return
        result = {}
        thread = threading.Thread(target=lambda: result.update(samples=self._synth(text)), daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self.root.after(POLL_MS, poll)
            elif result.get("samples") is not None and len(result["samples"]):
                deliver(result["samples"])

        poll()

    def _synth(self, text: str):
        samples = self._cache.get(text)
        if samples is None:
            with _synth_lock:
                try:
                    samples = self.speaker().synth(text)
                except Exception:  # Stimme defekt: lieber still als abgestürzt
                    samples = None
            if samples is not None:
                if len(self._cache) >= CACHE_SIZE:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[text] = samples
        return samples


def _chunks(text: str) -> list:
    """Kurze Ansage: ein Stück. Lange: erster Satz allein, der Rest in
    Stücken bis CHUNK_CHARS, an Satzgrenzen geteilt."""
    if len(text) <= SPLIT_ABOVE_CHARS:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = [sentences[0]]
    for sentence in sentences[1:]:
        if len(chunks) > 1 and len(chunks[-1]) + 1 + len(sentence) <= CHUNK_CHARS:
            chunks[-1] += " " + sentence
        else:
            chunks.append(sentence)
    return chunks


def install(root) -> Announcer:
    """Eine Ansage für das ganze Programm (vom Hauptfenster). Tabellen lesen
    die gewählte Zeile vor, wenn man mit der Tastatur darin unterwegs ist."""
    global _instance
    _instance = Announcer(root)
    root.bind_class("Treeview", "<<TreeviewSelect>>", _read_row, add="+")
    return _instance


def _read_row(event) -> None:
    """Gewählte Tabellenzeile als „Spalte: Wert, …“ ansagen – nur mit
    Tastaturfokus in der Tabelle, nicht beim Auffrischen von selbst."""
    tree = event.widget
    try:
        if not active() or tree.focus_get() is not tree or not tree.selection():
            return
        values = tree.item(tree.selection()[0], "values")
        columns = tree["columns"]
        parts = [f"{tree.heading(column, 'text')}: {value}"
                 for column, value in zip(columns, values) if str(value).strip()]
    except tk.TclError:
        return
    _instance.say(". ".join(parts) + ".")


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


def render(text: str, deliver) -> None:
    """Sprache erzeugen und `deliver(samples)` übergeben, falls die Ansage an
    ist (für Reiter mit eigenem Tonstrom)."""
    if _instance is not None:
        _instance.render(text, deliver)


def spell(text: str) -> str:
    """Buchstabiert (Ka, Emm, U … bzw. kay, em, you …); leer wird „nichts“."""
    return speech.spoken(text, lang=i18n.LANG) or tr("nichts")


def spell_nato(text: str) -> str:
    """Buchstabiert im Funkalphabet (Delta Lima Vier …), wie Rufzeichen im
    Contest gesprochen werden."""
    return speech.spoken(text, "nato", lang=i18n.LANG) or tr("nichts")


def value(text: str) -> str:
    """Ein Wert aus dem Log: Rufzeichen, Rapport, Nummern und Kürzel (NY)
    buchstabiert, Namen und Orte (auch kurze wie Eva) als Wort."""
    text = str(text).strip()
    if not text:
        return tr("nichts")
    if any(ch.isdigit() for ch in text) or len(text) <= 2:
        return spell_nato(text)
    return text.capitalize()
