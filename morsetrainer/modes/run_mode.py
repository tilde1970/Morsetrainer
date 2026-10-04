"""Contest-Modus (aktiv), angelehnt an Morse Runner: Du bist die Run-Station.
Du rufst CQ, Anrufer antworten (mehrere gleichzeitig, jeder mit eigener
Tonhöhe, Tempo und Lautstärke), du nimmst ein Rufzeichen auf, gibst den
Austausch und loggst das QSO. Am Ende wird das Log mit dem verglichen, was
die Stationen tatsächlich gesendet haben.

Tasten (wie in Morse Runner):
  F1 CQ · F2 Austausch (Call + 5NN + eigener Austausch) · F3 TU und loggen ·
  F4 eigenes Rufzeichen · F5 sein Rufzeichen · F7 „?“ · F8 „AGN“
  Enter: ESM (sendet jeweils die passende nächste Nachricht) ·
  Esc: Senden abbrechen · Leertaste im Call-Feld: zum Austausch-Feld

Verhalten der Anrufer:
- Nach CQ bzw. TU rufen die wartenden Stationen (und ggf. neue) mit etwas
  Verzögerung ihr Rufzeichen.
- Gibst du einen Austausch an ein Rufzeichen, antwortet genau diese Station
  mit ihrem Austausch; die anderen warten. Ist das Rufzeichen nur ähnlich
  (oder mit „?“ gefragt), wiederholt die passende Station ihr Rufzeichen.
- „?“ bzw. „AGN“ lässt die gearbeitete Station den Austausch wiederholen,
  sonst rufen alle nochmal.
- Wer zu lange nicht drankommt, ruft nach einer Pause erneut und gibt
  irgendwann auf.

Technik: Ein Audio-Thread (Mixer) spielt durchgehend alle Signale plus
Bandbedingungen ab. Die Spiellogik läuft im GUI-Thread und plant Ereignisse
in Samples der Mixer-Uhr."""
import random
import re
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import numpy as np

from morsetrainer.core import align, audio
from morsetrainer.core import qso_text
from morsetrainer.core import stats
from morsetrainer.core.band import BandConditions
from morsetrainer.core.morse import MORSE_CODE, SAMPLE_RATE, build_text
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.qso_quiz import is_correct
from morsetrainer.widgets import theme
from morsetrainer.widgets.ui_widgets import BandSettingsPanel, ChoiceBox, ScrollableFrame

TICK_MS = 30
MIX_CHUNK_SECONDS = 0.02
# Stationen je Sitzung (Stimmen für Chirp/QSB werden reihum vergeben).
MAX_STATIONS = 64

# Anrufer: Streuung von Tempo und Tonhöhe um deine (Standard, einstellbar),
# Lautstärke.
CALLER_WPM_SPREAD = 4
CALLER_WPM_SPREAD_RANGE = (0, 10)
CALLER_FREQ_OFFSET_HZ = 300
CALLER_FREQ_SPREAD_RANGE = (50, 500)
CALLER_STRENGTH = (0.35, 1.0)
# Reaktionszeit der Anrufer nach deinem Durchgang und Wahrscheinlichkeit,
# dass ein wartender Anrufer nach CQ/TU überhaupt (sofort) wieder ruft.
REPLY_DELAY = (0.15, 0.9)
CALL_AGAIN_PROBABILITY = 0.85
# Wie lange Anrufer ohne Reaktion warten, bevor sie erneut rufen, und nach
# wie vielen Versuchen sie aufgeben.
RETRY_WAIT = (1.5, 3.0)
WAITING_RETRY_WAIT = (4.0, 6.0)
PATIENCE = (3, 6)
# Wie oft nach CQ niemand antwortet.
NOBODY_PROBABILITY = 0.12
# Busted Call: Gibst du den Austausch an ein fast richtiges Rufzeichen (ein
# Zeichen daneben), antwortet der Anrufer mit dieser Wahrscheinlichkeit
# trotzdem – wie im echten Contest. Mal korrigiert er dabei sein Rufzeichen
# („DL1ABC 5NN 14“), mal nicht; den Hörfehler musst du selbst bemerken.
BUSTED_ANSWER_PROBABILITY = 0.4
BUSTED_CORRECTS_PROBABILITY = 0.6

MESSAGES = {  # Taste -> (Nachrichtentyp, Beschriftung)
    "F1": ("cq", "CQ"), "F2": ("exchange", N_("Austausch")), "F3": ("tu", "TU/Log"),
    "F4": ("mycall", N_("Mein Call")), "F5": ("hiscall", N_("Sein Call")), "F7": ("query", "?"), "F8": ("agn", "AGN"),
}


@dataclass
class Caller:
    call: str
    exchange: str
    exchange_kind: str
    station: int
    wpm: int
    freq: float
    strength: float
    patience: int
    state: str = "calling"   # calling | waiting | worked | done
    busy_until: int = 0      # Sample, bis zu dem die Station sendet
    last_end: int = 0
    retry_token: int = 0     # nur die Wiederholungs-Prüfung zum letzten Ruf zählt
    asked: bool = False      # Call auf Rückfrage oder Korrektur wiederholt (zählt nicht fürs WPX-Diplom)


class Mixer:
    """Audio-Thread: mischt geplante Signale [(Samples, Start-Sample,
    Station)] und die Bandbedingungen zu einem durchgehenden Strom. `clock`
    zählt die geschriebenen Samples und dient der Spiellogik als Uhr."""

    def __init__(self, band: BandConditions):
        self.band = band
        self.lock = threading.Lock()
        self.sources = []
        self.clock = 0
        self.running = False
        self.thread = None
        self.error = None  # Fehlermeldung, falls die Tonausgabe scheitert

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2)
            self.thread = None

    def add(self, samples: np.ndarray, station, start: int) -> int:
        """Plant `samples` ab Sample `start` ein; gibt das Ende zurück."""
        with self.lock:
            self.sources.append([samples, start, station])
        return start + len(samples)

    def cancel(self, station) -> None:
        with self.lock:
            self.sources = [s for s in self.sources if s[2] != station]

    def _run(self):
        try:
            self._mix()
        except audio.ERRORS as exc:
            self.error = audio.describe(exc)  # RunModeFrame._tick beendet den Contest
        except Exception as exc:
            self.error = audio.unexpected(exc)
            raise  # ins Fehlerprotokoll (threading.excepthook)

    def _mix(self):
        n = int(SAMPLE_RATE * MIX_CHUNK_SECONDS)
        with audio.output_stream() as stream:
            while self.running:
                begin, end = self.clock, self.clock + n
                parts = []
                with self.lock:
                    for samples, start, station in self.sources:
                        if start >= end or start + len(samples) <= begin:
                            continue
                        part = np.zeros(n, dtype=np.float32)
                        a = max(start, begin)
                        b = min(start + len(samples), end)
                        part[a - begin:b - begin] = samples[a - start:b - start]
                        parts.append((part, station))
                    self.sources = [s for s in self.sources if s[1] + len(s[0]) > end]
                stream.write(self.band.mix(parts, n))
                self.clock = end


def _distance(a: str, b: str) -> int:
    return sum(op.kind != align.OpKind.MATCH for op in align.align(a, b))


def call_matches(sent: str, call: str) -> str:
    """"exact", "similar" (ähnlich bzw. passt zur „?“-Anfrage) oder ""."""
    if sent == call:
        return "exact"
    if "?" in sent:
        # „?“ steht für ein einzelnes Zeichen: DL1? und DL?ABC passen zu DL1ABC.
        if len(sent.replace("?", "")) < 2:
            return ""
        pattern = ".".join(re.escape(part) for part in sent.split("?"))
        return "similar" if re.search(pattern, call) else ""
    if len(sent) >= 3 and (_distance(sent, call) <= 2 or sent in call):
        return "similar"
    return ""


class RunModeFrame:
    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop):
        self.root = parent.winfo_toplevel()
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.mixer = None
        self.band = None
        self.callers = []
        self.events = []          # [(Sample, Callback, Argumente)]
        self.msg_id = 0           # damit ein abgebrochener Durchgang keine Reaktion auslöst
        self.my_tx_start = self.my_tx_end = 0
        self.next_station = 0
        self.log = []
        self.my_serial = 1
        self.exchange_sent_to = ""  # Rufzeichen, an das zuletzt der Austausch ging
        self.deadline = None
        self.started_at = 0.0
        self.session_id = 0
        self.my_exchanges = {}    # Contest -> eigener Austausch (für gespeicherte Einstellungen)

        self._build_widgets(ScrollableFrame(parent).inner)

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        theme.hint(
            parent, wrap=560,
            text=tr("Du bist die Run-Station: F1 ruft CQ, nimm ein Rufzeichen auf, gib mit Enter den "
                    "Austausch, trag seinen Austausch ein und logge mit Enter (TU). "
                    "Am Ende wird dein Log mit dem verglichen, was wirklich gesendet wurde."),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        box = theme.card(parent, "Contest")
        box.columnconfigure(1, weight=1)
        row_pad = {"padx": (0, 8), "pady": 2}
        ttk.Label(box, text=tr("Contest:")).grid(row=0, column=0, sticky="w", **row_pad)
        self.kind_var = tk.StringVar(value=qso_text.CONTEST_NAMES["cqww"])
        self.kind_combo = ChoiceBox(
            box, self.kind_var, list(qso_text.CONTEST_NAMES.values()),
            width=26,
        )
        self.kind_combo.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)

        ttk.Label(box, text=tr("Mein Rufzeichen:")).grid(row=1, column=0, sticky="w", **row_pad)
        self.my_call_var = tk.StringVar(value="")  # Vorgabe: Rufzeichen aus den Einstellungen
        call_row = ttk.Frame(box)
        call_row.grid(row=1, column=1, columnspan=2, sticky="w", pady=2)
        self.my_call_entry = ttk.Entry(call_row, textvariable=self.my_call_var, width=12)
        self.my_call_entry.pack(side="left")
        # Nicht jeder, der übt, hat schon ein Rufzeichen; vorgegeben wird
        # keins, weil ein erfundenes jemandem gehören könnte.
        self.call_hint_var = tk.StringVar(value="")
        theme.hint(call_row, textvariable=self.call_hint_var).pack(side="left", padx=6)

        ttk.Label(box, text=tr("Mein Austausch:")).grid(row=2, column=0, sticky="w", **row_pad)
        exchange_row = ttk.Frame(box)
        exchange_row.grid(row=2, column=1, columnspan=2, sticky="w", pady=2)
        self.my_exchange_var = tk.StringVar(value="")
        self.my_exchange_entry = ttk.Entry(exchange_row, textvariable=self.my_exchange_var, width=12)
        self.my_exchange_entry.pack(side="left")
        self.exchange_hint_var = tk.StringVar(value="")
        theme.hint(exchange_row, textvariable=self.exchange_hint_var).pack(side="left", padx=6)

        ttk.Label(box, text=tr("Aktivität:")).grid(row=3, column=0, sticky="w", **row_pad)
        activity_row = ttk.Frame(box)
        activity_row.grid(row=3, column=1, columnspan=2, sticky="w", pady=2)
        self.activity_var = tk.IntVar(value=2)
        self.activity_spin = ttk.Spinbox(activity_row, from_=1, to=5, textvariable=self.activity_var, width=4)
        self.activity_spin.pack(side="left")
        theme.hint(activity_row, text=tr("Anrufer gleichzeitig (ca.)")).pack(side="left", padx=6)

        ttk.Label(box, text=tr("Dauer:")).grid(row=4, column=0, sticky="w", **row_pad)
        duration_row = ttk.Frame(box)
        duration_row.grid(row=4, column=1, columnspan=2, sticky="w", pady=2)
        self.duration_var = tk.IntVar(value=10)
        self.duration_spin = ttk.Spinbox(duration_row, from_=0, to=240, textvariable=self.duration_var, width=4)
        self.duration_spin.pack(side="left")
        ttk.Label(duration_row, text=tr("Min.")).pack(side="left", padx=(4, 0))
        theme.hint(duration_row, text=tr("(0 = ohne Limit)")).pack(side="left", padx=(4, 0))

        ttk.Label(box, text=tr("Anrufer:")).grid(row=5, column=0, sticky="w", **row_pad)
        spread_row = ttk.Frame(box)
        spread_row.grid(row=5, column=1, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Label(spread_row, text=tr("Tempo ±")).pack(side="left")
        self.wpm_spread_var = tk.IntVar(value=CALLER_WPM_SPREAD)
        self.wpm_spread_spin = ttk.Spinbox(spread_row, from_=CALLER_WPM_SPREAD_RANGE[0], to=CALLER_WPM_SPREAD_RANGE[1],
                                           textvariable=self.wpm_spread_var, width=3)
        self.wpm_spread_spin.pack(side="left", padx=(4, 4))
        ttk.Label(spread_row, text=tr("WPM, Tonhöhe ±")).pack(side="left")
        self.freq_spread_var = tk.IntVar(value=CALLER_FREQ_OFFSET_HZ)
        self.freq_spread_spin = ttk.Spinbox(spread_row, from_=CALLER_FREQ_SPREAD_RANGE[0],
                                            to=CALLER_FREQ_SPREAD_RANGE[1], increment=50,
                                            textvariable=self.freq_spread_var, width=4)
        self.freq_spread_spin.pack(side="left", padx=(4, 4))
        ttk.Label(spread_row, text="Hz").pack(side="left")
        theme.hint(box, text=tr("Wenig Tonhöhen-Streuung = dichtes Pile-up nahe deiner Frequenz. "
                                "F10 startet und beendet den Contest."), wrap=520).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(2, 6))

        self.kind_var.trace_add("write", lambda *_: self._on_setup_change())
        self.my_call_var.trace_add("write", lambda *_: self._on_setup_change())

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Start"), style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")
        self.status_var = tk.StringVar(value=tr("Bereit. Drücke Start."))
        ttk.Label(controls, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=12)

        self.score_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.score_var, style="Score.TLabel").pack(anchor="w", padx=10, pady=(6, 0))

        entry_box = theme.card(parent, tr("Eingabe"))
        fields = ttk.Frame(entry_box)
        fields.pack(anchor="w", pady=(0, 6))
        theme.hint(fields, text="Call").grid(row=0, column=0, sticky="w")
        theme.hint(fields, text=tr("Austausch")).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.call_var = tk.StringVar()
        self.exch_var = tk.StringVar()
        self.call_entry = ttk.Entry(fields, textvariable=self.call_var, width=12, font=theme.MONO_ENTRY)
        self.call_entry.grid(row=1, column=0)
        self.exch_entry = ttk.Entry(fields, textvariable=self.exch_var, width=8, font=theme.MONO_ENTRY)
        self.exch_entry.grid(row=1, column=1, padx=(12, 0))
        for var in (self.call_var, self.exch_var):
            var.trace_add("write", lambda *_, v=var: self._uppercase(v))
        for entry in (self.call_entry, self.exch_entry):
            entry.bind("<Return>", self._on_enter)
            entry.bind("<KP_Enter>", self._on_enter)
            entry.bind("<Escape>", lambda e: self._abort_sending())
        self.call_entry.bind("<space>", self._to_exchange)
        self.exch_entry.bind("<space>", lambda e: (self.call_entry.focus_set(), "break")[1])

        keys = ttk.Frame(entry_box)
        keys.pack(fill="x", pady=(0, 6))
        for i, (key, (_, label)) in enumerate(MESSAGES.items()):
            ttk.Button(keys, text=f"{key} {tr(label)}", command=lambda k=key: self.on_function_key(k)).grid(
                row=i // 4, column=i % 4, padx=(0, 4), pady=2, sticky="we")
        for col in range(4):
            keys.columnconfigure(col, weight=1, uniform="keys")
        theme.hint(entry_box, wrap=540,
                   text=tr("Enter sendet die passende nächste Nachricht (leer: CQ, mit Call: Austausch, mit "
                           "Austausch: TU + loggen). Call nach dem Austausch korrigiert: Enter sendet „Call TU“ "
                           "und loggt. Call mit „?“ (z. B. DL1? oder DL?ABC) fragt nur nach. "
                           "Achtung: Anrufer antworten manchmal auch auf ein fast richtiges Call. "
                           "Esc bricht ab, Leertaste wechselt das Feld.")).pack(
            anchor="w")

        log_box = theme.card(parent, "Log")
        columns = ("nr", "call", "exch", "result")
        self.log_tree = ttk.Treeview(log_box, columns=columns, show="headings", height=8)
        for col, heading, width, anchor in (("nr", tr("Nr"), 40, "center"), ("call", "Call", 100, "w"),
                                            ("exch", tr("Austausch"), 90, "w"), ("result", tr("Ergebnis"), 200, "w")):
            self.log_tree.heading(col, text=heading)
            self.log_tree.column(col, width=width, anchor=anchor)
        self.log_tree.tag_configure("wrong", foreground=theme.ERROR)
        self.log_tree.tag_configure("ok", foreground=theme.OK)
        self.log_tree.pack(fill="x")

        # Unten, damit Eingabe und Log im laufenden Contest ohne Scrollen sichtbar sind.
        self.band_panel = BandSettingsPanel(parent, on_change=self._apply_band_settings)

        self._on_setup_change()

    @staticmethod
    def _uppercase(var):
        value = var.get()
        if value != value.upper():
            var.set(value.upper())

    def _kind(self) -> str:
        return next((k for k, v in qso_text.CONTEST_NAMES.items() if v == self.kind_var.get()), "cqww")

    def _my_call(self) -> str:
        return self.my_call_var.get().strip().upper()

    def _on_setup_change(self):
        """Neuer Contest oder neues Rufzeichen: eigenen Austausch vorschlagen."""
        kind, call = self._kind(), self._my_call()
        self.call_hint_var.set("" if call else tr("ohne eigenes Rufzeichen: ein ausgedachtes eintragen"))
        if qso_text.uses_serial(kind, call):
            self.my_exchange_entry.config(state="disabled")
            self.exchange_hint_var.set(tr("laufende Nummer (automatisch)"))
            return
        self.my_exchange_entry.config(state="normal")
        hints = {"cqww": N_("CQ-Zone"), "iaru": N_("ITU-Zone oder Verband"), "wag": N_("dein DOK"),
                 "arrldx": N_("Bundesstaat") if call[:1] in "KNW" else N_("Leistung (z. B. 100, KW)")}
        self.exchange_hint_var.set(tr(hints[kind]) if kind in hints else "")
        saved = self.my_exchanges.get(kind)
        self.my_exchange_var.set(saved if saved else qso_text.default_my_exchange(kind, call))

    def _apply_band_settings(self):
        if self.band is not None:
            self.band_panel.apply_to(self.band)
            self.band.prepare(self.freq)

    # --- Ablauf -----------------------------------------------------------
    def toggle_running(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        kind, my_call = self._kind(), self._my_call()
        if not my_call or not all(ch in MORSE_CODE for ch in my_call):
            self.status_var.set(tr("Bitte ein gültiges eigenes Rufzeichen eintragen."))
            return
        my_exchange = self.my_exchange_var.get().strip().upper()
        if not qso_text.uses_serial(kind, my_call):
            if not my_exchange or not all(ch in MORSE_CODE for ch in my_exchange):
                self.status_var.set(tr("Bitte deinen Austausch eintragen."))
                return
            self.my_exchanges[kind] = my_exchange
        try:
            self.wpm, self.freq = self.wpm_var.get(), self.freq_var.get()
            activity, minutes = self.activity_var.get(), self.duration_var.get()
            wpm_spread, freq_spread = self.wpm_spread_var.get(), self.freq_spread_var.get()
        except tk.TclError:
            self.status_var.set(tr("Ungültige Einstellung (WPM, Tonhöhe, Aktivität, Dauer oder Anrufer)."))
            return
        self.wpm_spread = min(max(wpm_spread, CALLER_WPM_SPREAD_RANGE[0]), CALLER_WPM_SPREAD_RANGE[1])
        self.freq_spread = min(max(freq_spread, CALLER_FREQ_SPREAD_RANGE[0]), CALLER_FREQ_SPREAD_RANGE[1])

        self.kind, self.my_call_str, self.my_exchange = kind, my_call, my_exchange
        self.activity = min(max(activity, 1), 5)
        self.deadline = time.time() + minutes * 60 if minutes > 0 else None
        self.started_at = time.time()
        self.callers, self.events, self.log = [], [], []
        self.my_serial = 1
        self.exchange_sent_to = ""
        self.next_station = 0
        self.msg_id += 1
        self.session_id += 1
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        self.band = BandConditions(MAX_STATIONS)
        self._apply_band_settings()
        self.mixer = Mixer(self.band)
        self.mixer.start()
        self.my_tx_start = self.my_tx_end = 0

        self.running = True
        self.start_button.config(text=tr("Stop"))
        for widget in (self.kind_combo, self.my_call_entry, self.my_exchange_entry, self.activity_spin,
                       self.duration_spin, self.wpm_spread_spin, self.freq_spread_spin):
            widget.config(state="disabled")
        self.status_var.set(tr("Läuft – F1 oder Enter ruft CQ."))
        self._update_score()
        self.on_start_cb()
        self.call_entry.focus_set()
        self.root.after(TICK_MS, self._tick, self.session_id)

    def stop(self):
        self.running = False
        if self.mixer is not None:
            self.mixer.stop()
            self.mixer = None
        self.start_button.config(text=tr("Start"))
        for widget in (self.my_call_entry, self.activity_spin, self.duration_spin, self.wpm_spread_spin,
                       self.freq_spread_spin):
            widget.config(state="normal")
        self.kind_combo.config(state="readonly")
        self._on_setup_change()
        total = len(self.log)
        correct = sum(entry["ok"] for entry in self.log)
        if total:
            minutes = (time.time() - self.started_at) / 60
            counts = {kind: sum(entry["category"] == kind for entry in self.log) for kind in ("busted", "nil", "exchange")}
            stats.log_result("contest", correct, total, self.wpm, contest=self.kind, activity=self.activity,
                             minutes=round(minutes, 1), **counts,
                             # WPX-Diplom: richtig geloggt, ohne Rückfrage nach dem Call
                             calls=[entry["call"] for entry in self.log if entry["ok"] and entry["first"]])
            details = [f"{n} {label}" for n, label in ((counts["busted"], "Busted"), (counts["nil"], "NIL"),
                                                       (counts["exchange"], tr("Austausch falsch"))) if n]
            self.status_var.set(tr("Beendet: {correct} von {total} QSOs richtig geloggt").format(
                correct=correct, total=total) + (f" · {', '.join(details)}." if details else "."))
        else:
            self.status_var.set(tr("Beendet."))
        self.on_stop_cb()

    def _tick(self, session_id):
        if not self.running or session_id != self.session_id:
            return
        if self.mixer.error:
            error = self.mixer.error
            self.stop()
            self.status_var.set(f"{error} – {self.status_var.get()}")
            return
        now = self.mixer.clock
        due = [e for e in self.events if e[0] <= now]
        self.events = [e for e in self.events if e[0] > now]
        for _, callback, args in sorted(due, key=lambda e: e[0]):
            callback(*args)
        if self.deadline is not None and time.time() >= self.deadline:
            self.stop()
            self.status_var.set(tr("Zeit abgelaufen. ") + self.status_var.get())
            return
        self._update_score()
        self.root.after(TICK_MS, self._tick, session_id)

    def _schedule(self, sample: int, callback, *args):
        self.events.append((sample, callback, args))

    def _update_score(self):
        total = len(self.log)
        correct = sum(entry["ok"] for entry in self.log)
        # Laufzeit nach Audio-Uhr (gespielte Samples), sonst nach Wanduhr.
        seconds = self.mixer.clock / SAMPLE_RATE if self.mixer is not None else time.time() - self.started_at
        hours = max(seconds, 60) / 3600
        text = tr("QSOs: {total} · richtig: {correct} · Rate: {rate:.0f}/h").format(
            total=total, correct=correct, rate=correct / hours)
        if self.deadline is not None and self.running:
            remaining = max(int(self.deadline - time.time()), 0)
            text += tr(" · Rest {time}").format(time=f"{remaining // 60}:{remaining % 60:02d}")
        self.score_var.set(text)

    # --- Eigene Durchgänge ----------------------------------------------------
    def _my_exchange_text(self) -> str:
        if qso_text.uses_serial(self.kind, self.my_call_str):
            return qso_text.cut_number(self.my_serial)
        return self.my_exchange

    def _send(self, kind: str):
        """Sendet eine eigene Nachricht; die Anrufer reagieren, wenn sie zu
        Ende ist."""
        if not self.running:
            return
        call = self.call_var.get().strip()
        test = qso_text.contest_test_word(self.kind)
        if kind in ("exchange", "hiscall") and not call:
            self.status_var.set(tr("Erst ein Rufzeichen ins Call-Feld eintragen."))
            return
        text = {
            "cq": f"CQ {test} {self.my_call_str}",
            "exchange": f"{call} 5NN {self._my_exchange_text()}",
            "tu": f"TU {self.my_call_str}",
            "correct_tu": f"{call} TU {self.my_call_str}",
            "mycall": self.my_call_str,
            "hiscall": call,
            "query": "?",
            "agn": "AGN",
        }[kind]
        unlogged = None
        if kind in ("tu", "correct_tu"):
            # Geloggt wird nur ein vollständiges QSO; ein versehentliches F3
            # soll keinen Fehleintrag erzeugen.
            if call and self.exch_var.get().strip():
                self._log_qso()
            else:
                unlogged = tr("Rufzeichen") if not call else tr("Austausch")
        elif kind == "exchange":
            self.exchange_sent_to = call

        self.mixer.cancel(None)
        self.msg_id += 1
        samples = build_text(text, self.wpm, self.freq)
        start = self.mixer.clock + int(0.05 * SAMPLE_RATE)
        self.my_tx_start = start
        self.my_tx_end = self.mixer.add(samples, None, start)
        self._schedule(self.my_tx_end, self._react, "tu" if kind == "correct_tu" else kind, call, self.msg_id)
        if unlogged:
            self.status_var.set(tr("Sende: {text} – nicht geloggt ({missing} fehlt)").format(text=text, missing=unlogged))
        else:
            self.status_var.set(tr("Sende: {text}").format(text=text))

    def _abort_sending(self):
        if self.running and self.mixer is not None:
            self.mixer.cancel(None)
            self.msg_id += 1
            self.my_tx_end = self.mixer.clock
            self.status_var.set(tr("Abgebrochen."))
        return "break"

    def _on_enter(self, event=None):
        """ESM: leeres Call-Feld -> CQ; Call noch ohne Austausch -> Austausch;
        Austausch eingetragen -> TU + loggen; sonst Rückfrage."""
        call = self.call_var.get().strip()
        if not call:
            self._send("cq")
        elif "?" in call:
            # Nur Teil aufgenommen: nur das Teil-Call mit „?“ senden.
            self._send("hiscall")
        elif (call != self.exchange_sent_to and self.exchange_sent_to and self.exch_var.get().strip()
              and _distance(call, self.exchange_sent_to) <= 2):
            # Call nach dem Austausch korrigiert: „<Call> TU“ bestätigt die
            # Korrektur und loggt, statt den Austausch zu wiederholen. Ein
            # ganz anderes Call ist die nächste Station, keine Korrektur.
            self._send("correct_tu")
        elif call != self.exchange_sent_to:
            self._send("exchange")
            self.exch_entry.focus_set()
        elif self.exch_var.get().strip():
            self._send("tu")
        else:
            self._send("agn")
        return "break"

    def _to_exchange(self, event=None):
        self.exch_entry.focus_set()
        self.exch_entry.icursor("end")
        return "break"

    def _log_qso(self):
        call = self.call_var.get().strip()
        exch = self.exch_var.get().strip()
        worked = next((c for c in self.callers if c.state == "worked"), None)
        if worked is None:
            ok, category = False, "nil"
            result = tr("NIL – keine Station hat dir einen Austausch gegeben")
            # Nur Stationen, die noch rufen: eine längst geloggte oder
            # abgewanderte zu nennen, schickte dich auf die Suche nach einem
            # Hörfehler, den es nicht gab.
            near = min(self._active(), key=lambda c: _distance(call, c.call), default=None)
            if near is not None and _distance(call, near.call) <= 3:
                result += tr(" (ähnlich ruft: {call})").format(call=near.call)
        elif call != worked.call:
            ok, category, result = False, "busted", tr("Busted – richtig: {call}").format(call=worked.call)
        elif not is_correct(exch, worked.exchange, worked.exchange_kind):
            ok, category, result = False, "exchange", tr("Austausch falsch – richtig: {exchange}").format(
                exchange=worked.exchange)
        else:
            ok, category, result = True, "ok", "✓"
        if worked is not None:
            worked.state = "done"
        self.log.append({"call": call, "exch": exch, "ok": ok, "category": category,
                         "first": worked is not None and not worked.asked})
        self.log_tree.insert("", 0, values=(len(self.log), call, exch, result), tags=("ok" if ok else "wrong",))
        self.my_serial += 1
        self.call_var.set("")
        self.exch_var.set("")
        self.exchange_sent_to = ""
        self.call_entry.focus_set()

    # --- Anrufer ----------------------------------------------------------------
    def _active(self):
        return [c for c in self.callers if c.state != "done"]

    def _new_caller(self) -> Caller:
        call, exchange, exchange_kind = qso_text.contest_caller(
            self.kind, self.my_call_str, {c.call for c in self.callers}
        )
        freq = self.freq + random.uniform(-self.freq_spread, self.freq_spread)
        caller = Caller(
            call=call, exchange=exchange, exchange_kind=exchange_kind, station=self.next_station % MAX_STATIONS,
            wpm=max(self.wpm + random.randint(-self.wpm_spread, self.wpm_spread), 8), freq=min(max(freq, 300), 1000),
            strength=random.uniform(*CALLER_STRENGTH), patience=random.randint(*PATIENCE),
        )
        self.next_station += 1
        self.callers.append(caller)
        return caller

    def _arrivals(self):
        """Nach CQ/TU kommen neue Anrufer dazu, bis grob die eingestellte
        Aktivität erreicht ist."""
        if random.random() < NOBODY_PROBABILITY and not self._active():
            return
        target = random.randint(max(self.activity - 1, 1), self.activity + 1)
        for _ in range(max(target - len(self._active()), 0)):
            self._new_caller()

    def _caller_send(self, caller: Caller, text: str, delay: float):
        start = max(self.mixer.clock, caller.busy_until) + int(delay * SAMPLE_RATE)
        chirp = self.band.chirp_for(caller.station)
        samples = build_text(text, caller.wpm, caller.freq, chirp=chirp) * caller.strength
        caller.busy_until = self.mixer.add(samples.astype(np.float32), caller.station, start)
        caller.last_end = caller.busy_until
        caller.retry_token += 1
        if caller.state in ("calling", "waiting"):
            wait = RETRY_WAIT if caller.state == "calling" else WAITING_RETRY_WAIT
            self._schedule(caller.busy_until + int(random.uniform(*wait) * SAMPLE_RATE), self._retry, caller,
                           caller.retry_token)

    def _call(self, caller: Caller, twice: bool = False, delay=None):
        caller.state = "calling"
        text = f"{caller.call} {caller.call}" if twice or random.random() < 0.25 else caller.call
        self._caller_send(caller, text, random.uniform(*REPLY_DELAY) if delay is None else delay)

    def _send_exchange(self, caller: Caller, repeat: bool = False, correct_call: bool = False):
        caller.state = "worked"
        if repeat:
            text = f"{caller.exchange} {caller.exchange}"
        elif correct_call:
            text = f"{caller.call} 5NN {caller.exchange}"
        else:
            text = random.choice(["TU 5NN", "5NN", "R 5NN"]) + f" {caller.exchange}"
        self._caller_send(caller, text, random.uniform(*REPLY_DELAY))

    def _retry(self, caller: Caller, token: int):
        """Keine Reaktion der Run-Station seit dem letzten Ruf: nochmal rufen
        oder aufgeben."""
        now = self.mixer.clock
        if token != caller.retry_token or caller.state not in ("calling", "waiting") or now < caller.busy_until:
            return
        if self.my_tx_end > now or self.my_tx_start > caller.last_end:
            return  # du sendest bzw. hast inzwischen gesendet; die Reaktion darauf zählt
        caller.patience -= 1
        if caller.patience <= 0:
            caller.state = "done"
            return
        self._call(caller, delay=random.uniform(0.0, 0.4))

    def _react(self, kind: str, sent_call: str, msg_id: int):
        """Dein Durchgang ist zu Ende: die Anrufer reagieren darauf."""
        if msg_id != self.msg_id:
            return  # abgebrochen oder schon durch eine neue Nachricht ersetzt
        active = self._active()
        worked = next((c for c in active if c.state == "worked"), None)

        if kind in ("cq", "mycall", "tu"):
            if kind != "mycall":
                self._arrivals()
            for caller in self._active():
                if caller.state != "worked" and random.random() < CALL_AGAIN_PROBABILITY:
                    self._call(caller)
                elif caller.state != "worked":
                    # Ruft erst später, falls die Run-Station sich nicht meldet.
                    caller.state = "waiting"
                    caller.retry_token += 1
                    caller.last_end = self.mixer.clock
                    self._schedule(self.mixer.clock + int(random.uniform(*WAITING_RETRY_WAIT) * SAMPLE_RATE),
                                   self._retry, caller, caller.retry_token)
            return

        if kind in ("exchange", "hiscall"):
            matches = {c.call: call_matches(sent_call, c.call) for c in active}
            exact = next((c for c in active if matches[c.call] == "exact"), None)
            if exact is None and kind == "exchange" and "?" not in sent_call:
                near = [c for c in active if _distance(sent_call, c.call) == 1]
                if near and random.random() < BUSTED_ANSWER_PROBABILITY:
                    busted = random.choice(near)
                    busted.asked = True
                    for caller in active:
                        if caller is not busted and caller.state in ("calling", "worked"):
                            caller.state = "waiting"
                    self._send_exchange(busted, correct_call=random.random() < BUSTED_CORRECTS_PROBABILITY)
                    return
            for caller in active:
                if caller is exact:
                    continue
                if caller.state == "worked":
                    caller.state = "waiting"  # du arbeitest jetzt jemand anderen
                if exact is None and matches[caller.call] == "similar":
                    caller.asked = True
                    self._call(caller, twice=True)  # korrigiert sein Rufzeichen
                elif caller.state == "calling":
                    caller.state = "waiting"
            if exact is not None:
                if kind == "exchange":
                    self._send_exchange(exact)
                elif exact.state == "worked":
                    self._send_exchange(exact, repeat=True)  # Call bestätigt: Austausch nochmal
                else:
                    exact.asked = True
                    self._call(exact)
            return

        if kind in ("query", "agn"):
            if worked is not None:
                self._send_exchange(worked, repeat=True)
            else:
                for caller in active:
                    caller.asked = True
                    self._call(caller)

    # --- Schnittstelle zur App ------------------------------------------------
    def on_function_key(self, key: str):
        if key == "F10":
            self.toggle_running()
            return
        if key in MESSAGES and self.running:
            self._send(MESSAGES[key][0])
            if key == "F2":
                self.exch_entry.focus_set()

    def on_key(self, event):
        pass  # Eingabe über die Felder und Funktionstasten

    def settings(self) -> dict:
        exchange = self.my_exchange_var.get().strip().upper()
        if exchange and not qso_text.uses_serial(self._kind(), self._my_call()):
            self.my_exchanges[self._kind()] = exchange
        try:
            activity, duration = self.activity_var.get(), self.duration_var.get()
        except tk.TclError:
            activity, duration = 2, 10
        return {
            "kind": self._kind(),
            "my_call": self._my_call(),
            "my_exchanges": self.my_exchanges,
            "activity": activity,
            "duration": duration,
            "wpm_spread": self._int_or(self.wpm_spread_var, CALLER_WPM_SPREAD),
            "freq_spread": self._int_or(self.freq_spread_var, CALLER_FREQ_OFFSET_HZ),
            "band": self.band_panel.settings(),
        }

    @staticmethod
    def _int_or(var, default):
        try:
            return var.get()
        except tk.TclError:
            return default

    def restore_settings(self, data: dict) -> None:
        exchanges = data.get("my_exchanges")
        if isinstance(exchanges, dict):
            self.my_exchanges = {k: v for k, v in exchanges.items() if isinstance(v, str)}
        call = data.get("my_call")
        if isinstance(call, str) and call and all(ch in MORSE_CODE for ch in call):
            self.my_call_var.set(call)
        if data.get("kind") in qso_text.CONTEST_NAMES:
            self.kind_var.set(qso_text.CONTEST_NAMES[data["kind"]])
        for key, var, limits in (("activity", self.activity_var, (1, 5)), ("duration", self.duration_var, (0, 240)),
                                 ("wpm_spread", self.wpm_spread_var, CALLER_WPM_SPREAD_RANGE),
                                 ("freq_spread", self.freq_spread_var, CALLER_FREQ_SPREAD_RANGE)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)
        self.band_panel.restore(data.get("band"))
        self._on_setup_change()

    def on_close(self):
        if self.mixer is not None:
            self.mixer.stop()
