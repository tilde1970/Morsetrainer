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
from morsetrainer.i18n import N_, number, tr

# Pause nach einer Ansage, bevor es weitergeht.
AFTER_SPEECH_MS = 250
POLL_MS = 20
# Verdrängte Ansage: ihr Ablauf wartet, bis die neue zu Ende ist – höchstens
# so lange, damit nichts hängen bleibt, falls immer neue kommen.
SUPERSEDED_MAX_WAIT_S = 30
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
        self.speaking_until = 0.0  # time.time(), zu der die laufende Ansage endet
        self.done_token = 0  # token der zuletzt ganz abgespielten Ansage
        self._cache = {}
        # Stimme schon laden, sobald die Ansage an ist (knapp 1 s).
        self.var.trace_add("write", lambda *_: self.var.get() and self.available() is None
                           and self.speaker().voice is None and self.speaker().preload())

    def _after(self, ms: int, callback, *args) -> None:
        """root.after; ist das Fenster schon zu (Programmende), still nichts."""
        try:
            self.root.after(ms, callback, *args)
        except tk.TclError:
            pass

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
        Ansage verdrängt die ältere, auch eine schon sprechende; deren `then`
        kommt trotzdem, aber erst wenn die neue zu Ende ist – sonst schnitte
        etwa der nächste Morseton die neue Ansage ab."""
        text = speakable(text)
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
            if token != self.token:  # verdrängt: Ablauf nach der neuen Ansage freigeben
                if then is not None:
                    self._when_idle(then, time.time() + SUPERSEDED_MAX_WAIT_S)
                return
            index = state["next"]
            if index >= len(chunks):
                self.done_token = token
                if then is not None:
                    wait = max(state["free_at"] - time.time(), 0.0)
                    self._after(int(wait * 1000) + AFTER_SPEECH_MS, then)
                return
            if index in results and time.time() >= state["free_at"]:
                samples = results[index]
                if samples is not None and len(samples):
                    audio.play_quietly(samples)
                    state["free_at"] = time.time() + len(samples) / SAMPLE_RATE + (AUDIO_LATENCY if index == 0 else 0)
                    self.speaking_until = state["free_at"]
                state["next"] += 1
            self._after(POLL_MS, poll)

        poll()

    def _when_idle(self, then, deadline: float) -> None:
        """`then()`, sobald keine Ansage mehr läuft (die neueste ganz
        abgespielt und verklungen), spätestens zu `deadline`."""
        now = time.time()
        idle = self.done_token == self.token and now >= self.speaking_until
        if idle or now >= deadline:
            self._after(AFTER_SPEECH_MS if idle else 0, then)
        else:
            self._after(POLL_MS, self._when_idle, then, deadline)

    def render(self, text: str, deliver) -> None:
        """Sprache für `text` im Hintergrund erzeugen und `deliver(samples)`
        im Tk-Thread aufrufen, ohne sie abzuspielen (für Reiter mit eigenem
        Tonstrom, z. B. den Contest-Mischer). Nichts, wenn die Ansage aus ist."""
        text = speakable(text)
        if not text or not self.enabled() or self.available() is not None:
            return
        result = {}
        thread = threading.Thread(target=lambda: result.update(samples=self._synth(text)), daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self._after(POLL_MS, poll)
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
    _install_focus(root)
    return _instance


# --- Fokus-Ansage: ein kleiner eingebauter Screenreader ---------------------
# Springt man mit Tab in ein Bedienelement (Tk meldet das als <<TraverseIn>>,
# nicht wenn ein Reiter selbst den Fokus setzt), sagt es, was es ist und wie
# es steht; Änderungen per Tastatur werden ebenfalls angesagt.
ROLES = {
    "TButton": N_("Knopf"), "TCheckbutton": N_("Schalter"), "TRadiobutton": N_("Optionsfeld"),
    "TCombobox": N_("Auswahl"), "TSpinbox": N_("Zahlenfeld"), "TEntry": N_("Eingabefeld"),
    "TScale": N_("Regler"), "Text": N_("Textfeld"), "Treeview": N_("Tabelle"), "TNotebook": N_("Reiter"),
}
_names = {}  # str(Widget) -> fester Name (name())
_values = {}  # str(Widget) -> Funktion, die den angezeigten Wert liefert (z. B. S/N statt Zahl)


def name(widget, text: str, value=None) -> None:
    """Festen Namen für die Ansage vergeben, wo die Beschriftung daneben nicht
    reicht; `value`: Funktion für den angesagten Wert (sonst der Inhalt)."""
    _names[str(widget)] = text
    if value is not None:
        _values[str(widget)] = value


def _install_focus(root) -> None:
    for cls in ROLES:
        root.bind_class(cls, "<<TraverseIn>>", lambda e: _say_focus(e.widget), add="+")
    root.bind_class("TCheckbutton", "<KeyRelease-space>", lambda e: _later_state(e.widget), add="+")
    root.bind_class("TRadiobutton", "<KeyRelease-space>", lambda e: _later_state(e.widget), add="+")
    root.bind_class("TCombobox", "<<ComboboxSelected>>", lambda e: _say_value(e.widget), add="+")
    for sequence in ("<<Increment>>", "<<Decrement>>"):
        root.bind_class("TSpinbox", sequence, lambda e: e.widget.after_idle(_say_value, e.widget), add="+")
    for key in ("Left", "Right", "Up", "Down", "Home", "End"):
        root.bind_class("TScale", f"<KeyRelease-{key}>", lambda e: _say_value(e.widget), add="+")


def _later_state(widget) -> None:
    # ttk schaltet erst kurz nach dem Loslassen der Leertaste um.
    widget.after(150, _say_value, widget)


def _say_focus(widget) -> None:
    if active():
        try:
            _instance.say(describe(widget))
        except tk.TclError:
            pass


def _say_value(widget) -> None:
    try:
        if active() and widget.focus_get() is widget:
            _instance.say(_value(widget) + ".")
    except tk.TclError:
        pass


def describe(widget) -> str:
    """„Beschriftung, Rolle, Wert“, z. B. „Hoher Kontrast, Schalter, aus.“"""
    cls = widget.winfo_class()
    parts = [_label(widget), tr(ROLES.get(cls, ""))]
    value = _value(widget)
    if value:
        parts.append(value)
    try:
        if widget.instate(["disabled"]):
            parts.append(tr("nicht verfügbar"))
    except (AttributeError, tk.TclError):
        pass
    return ", ".join(part for part in parts if part) + "."


def _value(widget) -> str:
    key = str(widget)
    if key in _values:
        return str(_values[key]())
    cls = widget.winfo_class()
    if cls in ("TCheckbutton", "TRadiobutton"):
        selected = widget.instate(["selected"])
        if cls == "TCheckbutton":
            return tr("an") if selected else tr("aus")
        return tr("ausgewählt") if selected else tr("nicht ausgewählt")
    if cls == "TNotebook":
        return widget.tab("current", "text")
    if cls == "TScale":
        return number(float(widget.get()), 0)
    if cls in ("TEntry", "TCombobox", "TSpinbox"):
        text = widget.get().strip()
        if not text:
            return tr("leer")
        # Zeichensätze und Rufzeichen buchstabieren, Zahlen und Wörter nicht.
        if cls == "TEntry" and len(text) <= 12 and text.isalnum() and text.upper() == text and not text.isdigit():
            return spell(text)
        return text
    if cls == "Treeview":
        return tr("Pfeiltasten wählen eine Zeile")
    return ""


def _text_of(widget) -> str:
    """Beschriftung eines Labels oder Schalters (ohne Doppelpunkt), sonst leer."""
    if widget.winfo_class() not in ("TLabel", "TCheckbutton", "TRadiobutton", "TButton"):
        return ""
    try:
        return str(widget.cget("text")).strip().rstrip(":").strip()
    except tk.TclError:
        return ""


def _nearby(widget, depth: int = 0) -> str:
    """Beschriftung links davor: im Raster aus derselben Zeile, sonst das
    letzte Label (oder der Schalter) davor. Steht im eigenen Rahmen nichts
    davor, die Beschriftung des Rahmens (Zeile „Aktivität: [4] …“)."""
    parent = widget.master
    if parent is None:
        return ""
    siblings = parent.winfo_children()
    if widget.winfo_manager() == "grid":
        info = widget.grid_info()
        row, column = int(info["row"]), int(info["column"])
        left = []
        for sibling in siblings:
            if sibling is widget or sibling.winfo_manager() != "grid":
                continue
            other = sibling.grid_info()
            if int(other["row"]) == row and int(other["column"]) < column:
                left.append((int(other["column"]), sibling))
        for _, sibling in sorted(left, key=lambda item: item[0], reverse=True):
            text = _text_of(sibling)
            if text:
                return text
    else:
        before = siblings[:siblings.index(widget)] if widget in siblings else []
        for sibling in reversed(before):
            # Erklär- und Statuszeilen sind keine Beschriftung.
            if (sibling.winfo_class() in ("TLabel", "TCheckbutton")
                    and str(sibling.cget("style")) not in ("Hint.TLabel", "Status.TLabel")):
                text = _text_of(sibling)
                if text:
                    return text
    if depth < 2 and parent.winfo_class() == "TFrame":
        return _nearby(parent, depth + 1)
    return ""


def _label(widget) -> str:
    """Name aus name(), dem eigenen Text, der Beschriftung davor oder dem
    Titel der umgebenden Gruppe."""
    key = str(widget)
    if key in _names:
        return _names[key]
    if widget.winfo_class() in ("TButton", "TCheckbutton", "TRadiobutton"):
        own = str(widget.cget("text")).strip()
        if own:
            return own.rstrip(" …").strip("▸▾▶ ")
    text = _nearby(widget)
    if text:
        return text
    parent = widget.master
    while parent is not None:
        if parent.winfo_class() == "TLabelframe":
            return str(parent.cget("text")).strip()
        parent = parent.master
    return ""


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


# Zeichen, die auf dem Bildschirm etwas bedeuten, die Stimme aber nicht
# (oder falsch) liest.
_SYMBOLS = (("→", N_(" auf ")), ("↔", N_(" und ")), ("≈", N_("etwa ")), ("±", N_(" plus minus ")),
            ("✓", N_("richtig")), ("✗", N_("falsch")), ("★", N_(" Stern ")), ("☆", ""), ("…", ""),
            ("%", N_(" Prozent")), ("≥", N_("mindestens")), ("≤", N_("höchstens")), ("–", ","))


def speakable(text: str) -> str:
    """Text für die Stimme: Symbole als Wort, doppelte Leerzeichen weg."""
    if not text:
        return ""
    for symbol, word in _SYMBOLS:
        if symbol in text:
            text = text.replace(symbol, tr(word) if word else "")
    return re.sub(r" {2,}", " ", re.sub(r" +([,.])", r"\1", text)).strip()


def remaining() -> float:
    """Sekunden, bis die laufende Ansage zu Ende ist (0, wenn keine läuft);
    etwa um Nachgespieltes danach zu beginnen."""
    if _instance is None:
        return 0.0
    return max(_instance.speaking_until - time.time(), 0.0)


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
