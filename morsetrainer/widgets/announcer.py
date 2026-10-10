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
from morsetrainer.core.morse import AUDIO_LATENCY, PROSIGN_KEYS, SAMPLE_RATE
from morsetrainer.i18n import N_, number, tr

# Pause nach einer Ansage, bevor es weitergeht.
AFTER_SPEECH_MS = 250
POLL_MS = 20
# Verdrängte Ansage: ihr Ablauf wartet, bis die neue zu Ende ist – höchstens
# so lange, damit nichts hängen bleibt, falls immer neue kommen.
SUPERSEDED_MAX_WAIT_S = 30
CACHE_SIZE = 64
# Zusätzlich nach Größe begrenzt (etwa anderthalb Minuten Sprache): Ansagen
# mit Zahlen (F11, Statistik) kommen kaum je gleich wieder, sind aber lang.
CACHE_BYTES = 16 * 1024 * 1024
# Lange Ansagen (Statistik) satzweise: der erste Satz klingt sofort, die
# übrigen entstehen, während er läuft. Kurze bleiben ein Stück.
SPLIT_ABOVE_CHARS = 60
CHUNK_CHARS = 150
# Ein neues Fenster sagt seinen Namen an. Was kurz davor oder danach
# angesagt wird, gehört zum Fenster und bekommt den Namen vorangestellt,
# statt ihn zu verdrängen. Davor: Fenster wie Diplom und Tagesübung sprechen
# schon beim Aufbau, Augenblicke bevor sie erscheinen; eng gefasst, damit
# etwa die Ansage eines eben gewechselten Reiters nicht dazukommt.
WINDOW_JOIN_BEFORE_S = 0.25
WINDOW_JOIN_AFTER_S = 0.4
# Die Stimme erst so lange nach dem Zeichnen laden: Ihr Laden hält alle
# Python-Threads knapp 1 s an, auch die Oberfläche (core/speech.py); so
# steht das Fenster schon, statt erst danach zu erscheinen.
PRELOAD_AFTER_MS = 300
# Nach dem Schließen eines Fensters so lange warten, bis der Fokus
# zurückgegeben ist, dann sagen, wo man gelandet ist.
WINDOW_BACK_MS = 120

_instance = None
_synth_lock = threading.Lock()  # Piper nicht aus zwei Threads zugleich
# Den Zwischenspeicher teilen sich mehrere Synthese-Threads (verdrängte
# Ansagen rechnen noch, render() im Contest, Tipp-Echo).
_cache_lock = threading.Lock()


class Announcer:
    """Die Sprachansage des Programms: an/aus (var, F9), sagt Texte mit der
    Stimme der Oberfläche, eine nach der anderen; erzeugte Sprache wird
    zwischengespeichert."""
    def __init__(self, root):
        self.root = root
        self.var = tk.BooleanVar(value=False)
        self.token = 0
        self.speaking_until = 0.0  # time.time(), zu der die laufende Ansage endet
        self.done_token = 0  # token der zuletzt ganz abgespielten Ansage
        self.recent = None  # (Text, time.time(), token) der letzten Ansage
        self.window_intro = None  # (Fenstername als Satz, time.time(), token)
        self.last_window = None  # (Fenster, time.time()): nicht doppelt ansagen
        self.main_place = None  # Funktion: Ort im Hauptfenster („Reiter Gruppen.“), set_main_place()
        self.last_closed = None  # (Fenster, time.time()): nicht doppelt ansagen
        self.window_token = 0  # token der letzten Fensteransage (wird nicht mit angehängt)
        self._cache = {}
        self._cache_size = 0  # Bytes im Zwischenspeicher
        # Stimme schon laden, sobald die Ansage an ist (knapp 1 s).
        self.var.trace_add("write", lambda *_: self._preload_soon())

    def _preload_soon(self) -> None:
        """Ansage an: die Stimme laden, sobald das Fenster gezeichnet ist."""
        if self.var.get() and self.available() is None and self.speaker().voice is None:
            try:
                self.root.after_idle(self._after, PRELOAD_AFTER_MS, self._preload_now)
            except tk.TclError:
                pass

    def _preload_now(self) -> None:
        if self.var.get() and self.speaker().voice is None:
            self.speaker().preload()

    def _after(self, ms: int, callback, *args) -> None:
        """root.after; ist das Fenster schon zu (Programmende), still nichts."""
        try:
            self.root.after(ms, callback, *args)
        except tk.TclError:
            pass

    def enabled(self) -> bool:
        """Ist die Ansage eingeschaltet?"""
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
        intro = self.window_intro
        if (intro is not None and intro[2] == self.token and time.time() - intro[1] < WINDOW_JOIN_AFTER_S
                and not text.startswith(intro[0])):
            text = f"{intro[0]} {text}"
        self.window_intro = None
        self.token += 1
        token = self.token
        self.recent = (text, time.time(), token)
        chunks = _chunks(text)
        results = {}  # Nr. -> Samples (oder None), sobald erzeugt

        def work():
            for index, chunk in enumerate(chunks):
                if token != self.token:
                    return  # verdrängt: den Rest nicht mehr erzeugen
                try:
                    results[index] = self._synth(chunk)
                except BaseException:
                    # Ohne die übrigen Stücke wartete poll() endlos und der
                    # Ablauf (then) stünde still; der Fehler geht ins Protokoll.
                    for rest in range(index, len(chunks)):
                        results.setdefault(rest, None)
                    raise

        thread = threading.Thread(target=work, daemon=True)
        if self.speaker().voice is None:
            # Erste Ansage (etwa der Reiter beim Start): Sie lädt die Stimme,
            # und das hält die Oberfläche an – erst, wenn das Fenster steht.
            try:
                self.root.after_idle(self._after, PRELOAD_AFTER_MS, thread.start)
            except tk.TclError:
                thread.start()
        else:
            thread.start()
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

    def window_shown(self, window) -> None:
        """Ein Fenster ist erschienen: seinen Namen ansagen („Fenster
        Bandbedingungen.“). Kam gerade eben schon eine Ansage (etwa die des
        Fensters selbst), wird sie mit dem Namen davor wiederholt."""
        if not self.enabled() or self.available() is not None:
            return
        now = time.time()
        if self.last_window is not None and self.last_window[0] == str(window) and now - self.last_window[1] < 1.0:
            return
        self.last_window = (str(window), now)
        try:
            title = window.title()
        except tk.TclError:
            return
        intro = speakable(tr("Fenster {title}.").format(title=title) if title else tr("Neues Fenster."))
        text = intro
        if self._recent_content(now):
            text = f"{intro} {self.recent[0]}"
        self.window_intro = None  # Fensteransagen bekommen nichts vorangestellt
        self.say(text)
        self.window_token = self.token
        self.window_intro = (intro, time.time(), self.token)

    def _recent_content(self, now: float) -> bool:
        """Kam gerade eben eine Ansage, die keine Fensteransage war (etwa die
        eines Fensters beim Aufbau)? Dann gehört sie zu diesem Fenster."""
        recent = self.recent
        return (recent is not None and recent[2] == self.token and recent[2] != self.window_token
                and now - recent[1] < WINDOW_JOIN_BEFORE_S)

    def window_closed(self, window) -> None:
        """Ein Fenster ist zu oder versteckt: kurz danach sagen, wo der Fokus
        jetzt ist („Zurück im Hauptfenster, Reiter Gruppen.“ bzw. „Zurück im
        Fenster Einstellungen.“)."""
        if not self.enabled() or self.available() is not None:
            return
        now = time.time()
        # Zerstören meldet oft Unmap und Destroy: nur einmal.
        if self.last_closed is not None and self.last_closed[0] == str(window) and now - self.last_closed[1] < 1.0:
            return
        self.last_closed = (str(window), now)
        self._after(WINDOW_BACK_MS, self._say_back)

    def _say_back(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            focus = self.root.focus_get()
            top = focus.winfo_toplevel() if focus is not None else self.root
            if top is not self.root and top.winfo_viewable():
                text = tr("Zurück im Fenster {title}.").format(title=top.title())
            else:
                place = self.main_place() if self.main_place is not None else ""
                text = f"{tr('Zurück im Hauptfenster.')} {place}".strip()
        except (tk.TclError, KeyError, AttributeError):
            return
        if self._recent_content(time.time()):
            text = f"{self.recent[0]} {text}"  # was das Schließen selbst ansagte, nicht abschneiden
        self.window_intro = None
        self.say(text)
        self.window_token = self.token

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
        """Sprache für `text` (zwischengespeichert, höchstens CACHE_SIZE Einträge
        und CACHE_BYTES; zuerst fällt, was am längsten nicht gebraucht wurde);
        None, wenn die Stimme versagt."""
        with _cache_lock:
            samples = self._take_cached(text)
        if samples is None:
            with _synth_lock:
                try:
                    samples = self.speaker().synth(text)
                except Exception:  # Stimme defekt: lieber still als abgestürzt
                    samples = None
        if samples is not None:
            with _cache_lock:
                self._take_cached(text)  # inzwischen von einem anderen Thread erzeugt
                size = getattr(samples, "nbytes", 0)
                while self._cache and (len(self._cache) >= CACHE_SIZE or self._cache_size + size > CACHE_BYTES):
                    self._take_cached(next(iter(self._cache)))
                if size <= CACHE_BYTES:
                    self._cache[text] = samples
                    self._cache_size += size
        return samples

    def clear_cache(self) -> None:
        """Zwischenspeicher leeren."""
        with _cache_lock:
            self._cache.clear()
            self._cache_size = 0

    def _take_cached(self, text: str):
        """Eintrag aus dem Zwischenspeicher nehmen (unter _cache_lock)."""
        samples = self._cache.pop(text, None)
        if samples is not None:
            self._cache_size -= getattr(samples, "nbytes", 0)
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
_echo_widgets = set()  # str(Widget): Eingabefelder, in denen das Tippen angesagt wird (echo())
_echo_last = {}  # str(Widget) -> Inhalt beim letzten Blick (Fokus oder Taste)
_nato_widgets = set()  # str(Widget): Rufzeichen im Funkalphabet buchstabieren (nato())
# Tasten, deren Wirkung ein Zahlenfeld schon selbst ansagt (<<Increment>>).
_ECHO_SKIP_KEYS = {"Up", "Down", "Prior", "Next", "Tab", "ISO_Left_Tab"}


def name(widget, text: str, value=None) -> None:
    """Festen Namen für die Ansage vergeben, wo die Beschriftung daneben nicht
    reicht; `value`: Funktion für den angesagten Wert (sonst der Inhalt)."""
    _names[str(widget)] = text
    if value is not None:
        _values[str(widget)] = value


def value_of(widget, value) -> None:
    """Funktion für den angesagten Wert vergeben, ohne den Namen zu ändern
    (z. B. Reiter samt gewähltem Inhalt)."""
    _values[str(widget)] = value


_iconified = set()  # str(Toplevel): nur minimiert, nicht geschlossen


def _minimized(widget) -> bool:
    """Ist das Fenster (oder das Hauptfenster, mit dem es verschwindet) bloß
    minimiert?"""
    try:
        return widget.wm_state() == "iconic" or _instance.root.wm_state() == "iconic"
    except tk.TclError:
        return False


def _window_shown(widget) -> None:
    if _instance is not None and isinstance(widget, tk.Toplevel):
        if str(widget) in _iconified:  # wiederhergestellt, nicht neu geöffnet
            _iconified.discard(str(widget))
            return
        _instance.window_shown(widget)


def _window_closed(widget) -> None:
    if _instance is not None and isinstance(widget, tk.Toplevel):
        if _minimized(widget):  # Minimieren oder Arbeitsfläche gewechselt: nichts ansagen
            _iconified.add(str(widget))
            return
        _iconified.discard(str(widget))
        _instance.window_closed(widget)


def set_main_place(place) -> None:
    """`place()` sagt, wo man im Hauptfenster ist (z. B. „Reiter Gruppen.“),
    für die Ansage nach dem Schließen eines Fensters."""
    if _instance is not None:
        _instance.main_place = place


def echo(widget) -> None:
    """Tippen in diesem Eingabefeld ansagen, wie ein Screenreader: jedes
    neue Zeichen buchstabiert, Gelöschtes mit „gelöscht“. Für Felder der
    Einstellungen (Zahlenfelder immer); nicht für Antwortfelder, dort bräche
    die Ansage den laufenden Morseton ab."""
    _echo_widgets.add(str(widget))


def nato(widget) -> None:
    """In diesem Feld bzw. dieser Tabelle Rufzeichen im Funkalphabet
    buchstabieren (Delta, Lima, Eins …), wie im Contest üblich – beim
    Hineinspringen, beim Tippen und beim Vorlesen einer Zeile."""
    _nato_widgets.add(str(widget))


def _alphabet(widget) -> str:
    return "nato" if str(widget) in _nato_widgets else "de"


def _echoes(widget) -> bool:
    return widget.winfo_class() == "TSpinbox" or str(widget) in _echo_widgets


def _echo_start(widget) -> None:
    try:
        if _echoes(widget):
            _echo_last[str(widget)] = widget.get()
    except tk.TclError:
        pass


def _echo_key(event) -> None:
    widget = event.widget
    try:
        if not _echoes(widget):
            return
        after = widget.get()
    except tk.TclError:
        return
    before = _echo_last.get(str(widget))
    _echo_last[str(widget)] = after
    if before is None or before == after or event.keysym in _ECHO_SKIP_KEYS or not active():
        return
    _instance.say(change_text(before, after, _alphabet(widget)))


def spell_chars(text: str, alphabet: str = "de") -> str:
    """Jedes Zeichen einzeln gesprochen, auch Leerzeichen und Satzzeichen;
    `alphabet` "nato" für das Funkalphabet."""
    names = []
    for ch in text:
        if ch.isspace():
            names.append(tr("Leerzeichen"))
        else:
            names.append(speech.spoken(ch, alphabet, lang=i18n.LANG) or ch)
    return ", ".join(names)


def change_text(before: str, after: str, alphabet: str = "de") -> str:
    """Was sich in einem Feld geändert hat, zum Ansagen: Neues buchstabiert,
    Gelöschtes mit „gelöscht“ (bei einer ersetzten Auswahl das Neue)."""
    start = 0
    while start < min(len(before), len(after)) and before[start] == after[start]:
        start += 1
    end = 0
    while end < min(len(before), len(after)) - start and before[-1 - end] == after[-1 - end]:
        end += 1
    removed, added = before[start:len(before) - end], after[start:len(after) - end]
    if removed and not added:
        return tr("{chars} gelöscht").format(chars=spell_chars(removed, alphabet))
    return spell_chars(added, alphabet)


def _forget(widget) -> None:
    """Ein zerstörtes Bedienelement aus allen Merklisten streichen. Sonst
    hielten sie es (über die Wert-Funktionen samt Fenster) fest, und jeder
    neu geöffnete Dialog (fortlaufende Namen .!toplevel2 …) käme dazu."""
    key = str(widget)
    for registry in (_names, _values, _echo_last):
        registry.pop(key, None)
    for registry in (_echo_widgets, _nato_widgets, _iconified):
        registry.discard(key)


def _install_focus(root) -> None:
    # Nach den Klassenbindungen (Fenster geschlossen), die die Namen noch brauchen.
    root.bind_all("<Destroy>", lambda e: _forget(e.widget), add="+")
    root.bind_class("Toplevel", "<Map>", lambda e: _window_shown(e.widget), add="+")
    for sequence in ("<Unmap>", "<Destroy>"):
        root.bind_class("Toplevel", sequence, lambda e: _window_closed(e.widget), add="+")
    for cls in ("TEntry", "TSpinbox"):
        root.bind_class(cls, "<FocusIn>", lambda e: _echo_start(e.widget), add="+")
        root.bind_class(cls, "<KeyRelease>", _echo_key, add="+")
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
    """Was ein Bedienelement gerade zeigt, als gesprochener Text: fester Wert
    aus name(), sonst je nach Art (Schalter an/aus, gewählter Reiter, Inhalt
    eines Feldes, Wert eines Reglers …)."""
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
        unit = _unit_after(widget)
        if unit:
            if text == "1":
                # „1 Fehlversuchen“ läse die Stimme „eins Fehlversuchen“.
                for plural, singular in _ONE_UNITS:
                    if unit == tr(plural, context="Einheit" if plural == "Zeichen" else ""):
                        return tr(singular)
            return f"{text} {unit}"
        if str(widget) in _nato_widgets:
            return spell_nato(text)
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


# Längere Texte hinter einem Zahlenfeld sind Erklärungen, keine Einheit.
UNIT_MAX_CHARS = 25


# Einheiten hinter Zahlenfeldern, die bei 1 eine eigene Form brauchen
# (Minuten und Sekunden erledigt speakable).
_ONE_UNITS = ((N_("Fehlversuchen"), N_("einem Fehlversuch")), (N_("Zeichen"), N_("ein Zeichen")))


def _unit_after(widget) -> str:
    """Einheit gleich hinter einem Zahlenfeld („3 Fehlversuchen“, „10
    Minuten“): das nächste schlichte Label in derselben Zeile. Erklärtexte
    und Beschriftungen des nächsten Feldes (mit Doppelpunkt oder direkt vor
    einem weiteren Feld, wie „von [3] bis [5]“) zählen nicht."""
    parent = widget.master
    if parent is None or widget.winfo_class() != "TSpinbox":
        return ""
    siblings = parent.winfo_children()
    manager = widget.winfo_manager()
    if manager == "grid":
        info = widget.grid_info()
        row, column = int(info["row"]), int(info["column"])
        following = [s for s in siblings if s.winfo_manager() == "grid"
                     and (int(s.grid_info()["row"]), int(s.grid_info()["column"])) == (row, column + 1)]
    elif manager == "pack" and widget.pack_info().get("side") == "left" and widget in siblings:
        packed = [s for s in siblings[siblings.index(widget) + 1:] if s.winfo_manager() == "pack"]
        if len(packed) > 1 and packed[1].winfo_class() in ("TSpinbox", "TEntry", "TCombobox"):
            return ""
        following = packed[:1]
    else:
        return ""
    for sibling in following:
        if sibling.winfo_class() != "TLabel" or str(sibling.cget("style")) in ("Hint.TLabel", "Status.TLabel"):
            continue
        raw = str(sibling.cget("text")).strip()
        if raw and not raw.endswith(":") and len(raw) <= UNIT_MAX_CHARS:
            return raw
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
        nato_calls = str(tree) in _nato_widgets
        parts = [f"{tree.heading(column, 'text')}: {_cell_spoken(str(value), nato_calls)}"
                 for column, value in zip(columns, values) if str(value).strip()]
    except tk.TclError:
        return
    _instance.say(". ".join(parts) + ".")


def times(count: int) -> str:
    """„einmal“, „9 mal“ zum Sprechen (nicht „1 mal“)."""
    return tr("einmal") if count == 1 else tr("{count} mal").format(count=count)


def _cell_spoken(value: str, nato_calls: bool = False) -> str:
    """Eine Tabellenzelle zum Vorlesen: ein einzelnes Zeichen buchstabiert
    („Fragezeichen“, sonst spräche die Stimme „?“ gar nicht), Verwechslungen
    „B (9), N (1)“ als „Be gleich 9 mal, Enn gleich einmal“, Rufzeichen
    (`nato_calls`) im Funkalphabet."""
    value = value.strip()
    if value == "–":  # keine Messung
        return tr("keine")
    if len(value) == 1:
        return spell_chars(value)
    if _CONFUSIONS.match(value):
        return ", ".join(tr("{char} gleich {times}").format(char=spell_chars(char), times=times(int(count)))
                         for char, count in _CONFUSION.findall(value))
    if nato_calls and _CALLSIGN.match(value):
        return spell_nato(value)
    return value


def get():
    """Die Ansage des Hauptfensters (install()), oder None vor dem Start."""
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


def problem(variable, text: str) -> None:
    """Fehler in die Statuszeile `variable` schreiben und ansagen: Wer nicht
    hinsieht, merkt sonst nur, dass nichts passiert (ungültige Eingabe, zu
    wenige Zeichen für den Inhalt, keine Tonausgabe)."""
    variable.set(text)
    say(text)


def render(text: str, deliver) -> None:
    """Sprache erzeugen und `deliver(samples)` übergeben, falls die Ansage an
    ist (für Reiter mit eigenem Tonstrom)."""
    if _instance is not None:
        _instance.render(text, deliver)


# Zeichen, die auf dem Bildschirm etwas bedeuten, die Stimme aber nicht
# (oder falsch) liest.
_SYMBOLS = (("→", N_(" auf ")), ("↔", N_(" und ")), ("≈", N_("etwa ")), ("±", N_(" plus minus ")),
            ("✓", N_("richtig")), ("✗", N_("falsch")), ("★", N_(" Stern ")), ("☆", ""), ("…", ""),
            ("%", N_(" Prozent")), ("≥", N_("mindestens")), ("≤", N_("höchstens")), ("–", ","), ("·", ","))
# Betriebszeichen, wie sie angezeigt werden („<SK>“), mit ihrem Namen
# („Ende der Verbindung“); die Taste dazu („Taste *“) mit dem Namen der Taste.
_PROSIGN_SHOWN = re.compile(r"<(" + "|".join(PROSIGN_KEYS.values()) + r")>")
_PROSIGN_CHAR = {name: ch for ch, name in PROSIGN_KEYS.items()}
_KEY = re.compile(r"\b(Taste|key) ([*(#+=])")
_KEY_NAMES = {"*": N_("Stern"), "(": N_("Klammer auf"), "#": N_("Raute"), "+": N_("Plus"),
              "=": N_("Gleichheitszeichen")}
# Einheiten, die die Stimme sonst buchstabiert („HaZet“); nur als ganzes Wort.
_UNITS = ((re.compile(r"\bkHz\b"), N_("Kilohertz")), (re.compile(r"\bHz\b"), N_("Hertz")),
          (re.compile(r"/h\b"), N_(" pro Stunde")))
# Englische Lehnwörter, die die deutsche Stimme deutsch ausspricht
# („Fäding“): so geschrieben, wie sie klingen sollen (auch im Wortinnern,
# etwa „Flatterfading“).
_PRONOUNCE_DE = ((re.compile(r"Fading"), "Fehding"), (re.compile(r"fading"), "fehding"),
                 (re.compile(r"\bpile-?up(s?)\b", re.IGNORECASE), r"Peil-app\1"))
# Abkürzungen der Contest-Arten (qso_text.QSO_TYPES): buchstabiert mit den
# Buchstabennamen wie bei Rufzeichen („We, A, Ge“ bzw. „double you, ay,
# gee“); sonst liest die Stimme „WAG“ oder „ARRL“ als Wort. Ein Bindestrich dahinter („CQ-Zone“) wird
# zur Pause.
_ACRONYMS_DE = ("CQ", "WW", "WPX", "WAG", "DOK", "ARRL", "DX", "IARU", "HF", "ITU", "HQ", "IP")
_ACRONYM_PATTERN = re.compile(r"\b(" + "|".join(_ACRONYMS_DE) + r")\b(-(?=\w))?")
# Klammern und Schrägstrich hinter einem Wort liest die Stimme mit („in
# Klammern“); gesprochen wird stattdessen eine Pause bzw. „oder“
# („Staat/Leistung“, „Zone/HQ“; nicht „TU/Log“, das heißt „und“).
_BRACKETS = re.compile(r"\s*\(([^()]*)\)")
# Spaltenköpfe: „Zeit (s)“ heißt „Zeit in Sekunden“, „Ø Zeit“ „Durchschnittszeit“.
_SECONDS_IN_BRACKETS = re.compile(r"\s*\(s\)")
_AVERAGE = re.compile(r"Ø\s*(\S+)")
# IP-Adresse (mit Port) Zahl für Zahl mit „Punkt“, sonst liest die Stimme
# eine große Dezimalzahl; ein „Adresse“ davor geht im „IP-Adresse“ auf.
_IP_ADDRESS = re.compile(r"(?:\b(?:Adresse|Address)\s+)?\b(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{2,5}))?\b")
# PIN Ziffer für Ziffer („Vier, Sieben, Eins, Eins“ statt einer Zahl).
_PIN = re.compile(r"\bPIN:?\s+(\d+)\b")
# Verwechslungen in der Statistik („B (9), 5 (2)“, stats.format_confusions).
_CONFUSION = re.compile(r"(\S+) \((\d+)\)")
_CONFUSIONS = re.compile(r"^\S+ \(\d+\)(, \S+ \(\d+\))*$")
# Rufzeichen in einer Tabellenzelle (Buchstaben und Ziffern, ggf. mit /).
_CALLSIGN = re.compile(r"^(?=.*\d)(?=.*[A-Z])[A-Z0-9/]{3,}$")
_WORD_SLASH = re.compile(r"(?<=[a-zäöüß]{2})/(?=[^\W\d_]{2})")
# Zeiteinheiten nur direkt hinter einer Zahl (sonst ist „s“ ein Buchstabe);
# (Muster, Einzahl, Mehrzahl).
# Bei 1 das Zahlwort samt Einheit („eine Minute“): Die Stimme läse die
# einzelne Ziffer sonst als „eins“.
_NUMBER_UNITS = (
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*[Mm]in\.?(?!\w)"), N_("eine Minute"), N_("Minuten")),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s+s(?!\w)"), N_("eine Sekunde"), N_("Sekunden")),
)


def speakable(text: str) -> str:
    """Text für die Stimme: Symbole und Einheiten als Wort, doppelte
    Leerzeichen weg."""
    if not text:
        return ""
    text = _PROSIGN_SHOWN.sub(lambda m: speech.spoken(_PROSIGN_CHAR[m.group(1)], lang=i18n.LANG), text)
    text = _KEY.sub(lambda m: f"{m.group(1)} {tr(_KEY_NAMES[m.group(2)])}", text)
    for symbol, word in _SYMBOLS:
        if symbol in text:
            text = text.replace(symbol, tr(word) if word else "")
    text = _SECONDS_IN_BRACKETS.sub(" " + tr("in Sekunden"), text)
    text = _AVERAGE.sub(_average, text)
    text = _BRACKETS.sub(r", \1,", text)
    text = _IP_ADDRESS.sub(lambda m: f"{tr('IP-Adresse')} " + f" {tr('Punkt')} ".join(m.group(1).split("."))
                           + (f", {tr('Port')} {m.group(2)}" if m.group(2) else ""), text)
    text = _PIN.sub(lambda m: f"{tr('PIN-Nummer')} {spell_chars(m.group(1))}", text)
    text = _WORD_SLASH.sub(" " + tr("oder") + " ", text)
    for pattern, word in _UNITS:
        text = pattern.sub(tr(word), text)
    if i18n.LANG == "de":
        for pattern, sounds in _PRONOUNCE_DE:
            text = pattern.sub(sounds, text)
    # Abkürzungen in beiden Sprachen, mit den Buchstabennamen der Stimme.
    text = _ACRONYM_PATTERN.sub(lambda m: speech.spoken(m.group(1), lang=i18n.LANG) + (" " if m.group(2) else ""),
                                text)
    for pattern, one, many in _NUMBER_UNITS:
        text = pattern.sub(lambda m, one=one, many=many: tr(one) if m.group(1) == "1" else f"{m.group(1)} {tr(many)}",
                           text)
    text = re.sub(r" +([,.])", r"\1", text)
    text = re.sub(r",(\s*,)+", ",", text)  # Pausen nicht doppelt
    text = re.sub(r",\s*([.!?:])", r"\1", text)
    return re.sub(r" {2,}", " ", text).strip().rstrip(",").strip()


def _average(match) -> str:
    """„Ø Zeit“ → „Durchschnittszeit“, „Ø effektive …“ → „durchschnittliche
    effektive …“, „Ø WPM“ → „Durchschnitts-WPM“; englisch „average …“."""
    word = match.group(1)
    if i18n.LANG != "de":
        return f"average {word}"
    if word[:1].islower():
        return f"durchschnittliche {word}"
    if word.isupper():
        return f"Durchschnitts-{word}"
    return f"Durchschnitts{word[:1].lower()}{word[1:]}"


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
