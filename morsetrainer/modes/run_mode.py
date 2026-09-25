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
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import numpy as np
import sounddevice as sd

from morsetrainer.core import align
from morsetrainer.core import qso_text
from morsetrainer.core import stats
from morsetrainer.core.band import BandConditions
from morsetrainer.core.morse import AUDIO_LATENCY, MORSE_CODE, SAMPLE_RATE, build_text
from morsetrainer.modes.qso_quiz import is_correct
from morsetrainer.widgets.ui_widgets import BandSettingsPanel, ScrollableFrame

DEFAULT_CALL = "DL4YM"
TICK_MS = 30
MIX_CHUNK_SECONDS = 0.02
# Stationen je Sitzung (Stimmen für Chirp/QSB werden reihum vergeben).
MAX_STATIONS = 64

# Anrufer: Tempo relativ zu deinem, Abstand zu deiner Tonhöhe, Lautstärke.
CALLER_WPM_OFFSET = (-4, 4)
CALLER_FREQ_OFFSET_HZ = 300
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

MESSAGES = {  # Taste -> (Nachrichtentyp, Beschriftung)
    "F1": ("cq", "CQ"), "F2": ("exchange", "Austausch"), "F3": ("tu", "TU/Log"),
    "F4": ("mycall", "Mein Call"), "F5": ("hiscall", "Sein Call"), "F7": ("query", "?"), "F8": ("agn", "AGN"),
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
        n = int(SAMPLE_RATE * MIX_CHUNK_SECONDS)
        with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=AUDIO_LATENCY) as stream:
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
        part = sent.replace("?", "")
        return "similar" if len(part) >= 2 and part in call else ""
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
        ttk.Label(
            parent, wraplength=460, justify="left",
            text="Du bist die Run-Station: F1 ruft CQ, nimm ein Rufzeichen auf, gib mit Enter den "
                 "Austausch, trag seinen Austausch ein und logge mit Enter (TU). "
                 "Am Ende wird dein Log mit dem verglichen, was wirklich gesendet wurde.",
        ).pack(anchor="w", padx=8, pady=(4, 8))

        box = ttk.LabelFrame(parent, text="Contest")
        box.pack(fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        row_pad = {"padx": (8, 4), "pady": 2}
        ttk.Label(box, text="Contest:").grid(row=0, column=0, sticky="w", **row_pad)
        self.kind_var = tk.StringVar(value=qso_text.QSO_TYPES["cqww"])
        self.kind_combo = ttk.Combobox(
            box, textvariable=self.kind_var, state="readonly", width=32,
            values=[label for key, label in qso_text.QSO_TYPES.items() if key != qso_text.RAGCHEW],
        )
        self.kind_combo.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)

        ttk.Label(box, text="Mein Rufzeichen:").grid(row=1, column=0, sticky="w", **row_pad)
        self.my_call_var = tk.StringVar(value=DEFAULT_CALL)
        self.my_call_entry = ttk.Entry(box, textvariable=self.my_call_var, width=12)
        self.my_call_entry.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Mein Austausch:").grid(row=2, column=0, sticky="w", **row_pad)
        exchange_row = ttk.Frame(box)
        exchange_row.grid(row=2, column=1, columnspan=2, sticky="w", pady=2)
        self.my_exchange_var = tk.StringVar(value="")
        self.my_exchange_entry = ttk.Entry(exchange_row, textvariable=self.my_exchange_var, width=12)
        self.my_exchange_entry.pack(side="left")
        self.exchange_hint_var = tk.StringVar(value="")
        ttk.Label(exchange_row, textvariable=self.exchange_hint_var, foreground="gray40").pack(side="left", padx=6)

        ttk.Label(box, text="Aktivität:").grid(row=3, column=0, sticky="w", **row_pad)
        activity_row = ttk.Frame(box)
        activity_row.grid(row=3, column=1, columnspan=2, sticky="w", pady=2)
        self.activity_var = tk.IntVar(value=2)
        self.activity_spin = ttk.Spinbox(activity_row, from_=1, to=5, textvariable=self.activity_var, width=4)
        self.activity_spin.pack(side="left")
        ttk.Label(activity_row, text="Anrufer gleichzeitig (ca.)").pack(side="left", padx=6)

        ttk.Label(box, text="Dauer:").grid(row=4, column=0, sticky="w", **row_pad)
        duration_row = ttk.Frame(box)
        duration_row.grid(row=4, column=1, columnspan=2, sticky="w", pady=(2, 6))
        self.duration_var = tk.IntVar(value=10)
        self.duration_spin = ttk.Spinbox(duration_row, from_=0, to=240, textvariable=self.duration_var, width=4)
        self.duration_spin.pack(side="left")
        ttk.Label(duration_row, text="Min. (0 = ohne Limit)").pack(side="left", padx=6)

        self.kind_var.trace_add("write", lambda *_: self._on_setup_change())
        self.my_call_var.trace_add("write", lambda *_: self._on_setup_change())

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=8, pady=4)
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.pack(side="left", padx=8, pady=4)
        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(controls, textvariable=self.status_var, font=("Sans", 11)).pack(side="left", padx=8)

        self.score_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.score_var, font=("Sans", 12, "bold")).pack(anchor="w", padx=16)

        entry_box = ttk.LabelFrame(parent, text="Eingabe")
        entry_box.pack(fill="x", padx=8, pady=4)
        fields = ttk.Frame(entry_box)
        fields.pack(anchor="w", padx=8, pady=4)
        ttk.Label(fields, text="Call").grid(row=0, column=0, sticky="w")
        ttk.Label(fields, text="Austausch").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.call_var = tk.StringVar()
        self.exch_var = tk.StringVar()
        self.call_entry = ttk.Entry(fields, textvariable=self.call_var, width=12, font=("Consolas", 16))
        self.call_entry.grid(row=1, column=0)
        self.exch_entry = ttk.Entry(fields, textvariable=self.exch_var, width=8, font=("Consolas", 16))
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
        keys.pack(fill="x", padx=4, pady=(0, 6))
        for i, (key, (_, label)) in enumerate(MESSAGES.items()):
            ttk.Button(keys, text=f"{key} {label}", width=11,
                       command=lambda k=key: self.on_function_key(k)).grid(row=i // 4, column=i % 4, padx=2, pady=1)
        ttk.Label(entry_box, foreground="gray40", wraplength=440, justify="left",
                  text="Enter sendet die passende nächste Nachricht (leer: CQ, mit Call: Austausch, mit "
                       "Austausch: TU + loggen). Esc bricht ab, Leertaste wechselt das Feld.").pack(
            anchor="w", padx=8, pady=(0, 6))

        log_box = ttk.LabelFrame(parent, text="Log")
        log_box.pack(fill="x", padx=8, pady=4)
        columns = ("nr", "call", "exch", "result")
        self.log_tree = ttk.Treeview(log_box, columns=columns, show="headings", height=8)
        for col, heading, width, anchor in (("nr", "Nr", 40, "center"), ("call", "Call", 100, "w"),
                                            ("exch", "Austausch", 90, "w"), ("result", "Ergebnis", 200, "w")):
            self.log_tree.heading(col, text=heading)
            self.log_tree.column(col, width=width, anchor=anchor)
        self.log_tree.tag_configure("wrong", foreground="#c0392b")
        self.log_tree.tag_configure("ok", foreground="#1e7e34")
        self.log_tree.pack(fill="x", padx=4, pady=4)

        # Unten, damit Eingabe und Log im laufenden Contest ohne Scrollen sichtbar sind.
        self.band_panel = BandSettingsPanel(parent, on_change=self._apply_band_settings)

        self._on_setup_change()

    @staticmethod
    def _uppercase(var):
        value = var.get()
        if value != value.upper():
            var.set(value.upper())

    def _kind(self) -> str:
        return next((k for k, v in qso_text.QSO_TYPES.items() if v == self.kind_var.get()), "cqww")

    def _my_call(self) -> str:
        return self.my_call_var.get().strip().upper()

    def _on_setup_change(self):
        """Neuer Contest oder neues Rufzeichen: eigenen Austausch vorschlagen."""
        kind, call = self._kind(), self._my_call()
        if qso_text.uses_serial(kind, call):
            self.my_exchange_entry.config(state="disabled")
            self.exchange_hint_var.set("laufende Nummer (automatisch)")
            return
        self.my_exchange_entry.config(state="normal")
        hints = {"cqww": "CQ-Zone", "iaru": "ITU-Zone oder Verband", "wag": "dein DOK",
                 "arrldx": "Bundesstaat" if call[:1] in "KNW" else "Leistung (z. B. 100, KW)"}
        self.exchange_hint_var.set(hints.get(kind, ""))
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
            self.status_var.set("Bitte ein gültiges eigenes Rufzeichen eintragen.")
            return
        my_exchange = self.my_exchange_var.get().strip().upper()
        if not qso_text.uses_serial(kind, my_call):
            if not my_exchange or not all(ch in MORSE_CODE for ch in my_exchange):
                self.status_var.set("Bitte deinen Austausch eintragen.")
                return
            self.my_exchanges[kind] = my_exchange
        try:
            self.wpm, self.freq = self.wpm_var.get(), self.freq_var.get()
            activity, minutes = self.activity_var.get(), self.duration_var.get()
        except tk.TclError:
            self.status_var.set("Ungültige Einstellung (WPM, Tonhöhe, Aktivität oder Dauer).")
            return

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
        self.start_button.config(text="Stop")
        for widget in (self.kind_combo, self.my_call_entry, self.my_exchange_entry, self.activity_spin,
                       self.duration_spin):
            widget.config(state="disabled")
        self.status_var.set("Läuft – F1 oder Enter ruft CQ.")
        self._update_score()
        self.on_start_cb()
        self.call_entry.focus_set()
        self.root.after(TICK_MS, self._tick, self.session_id)

    def stop(self):
        self.running = False
        if self.mixer is not None:
            self.mixer.stop()
            self.mixer = None
        self.start_button.config(text="Start")
        for widget in (self.my_call_entry, self.activity_spin, self.duration_spin):
            widget.config(state="normal")
        self.kind_combo.config(state="readonly")
        self._on_setup_change()
        total = len(self.log)
        correct = sum(entry["ok"] for entry in self.log)
        if total:
            minutes = (time.time() - self.started_at) / 60
            stats.log_result("contest", correct, total, self.wpm, contest=self.kind, activity=self.activity,
                             minutes=round(minutes, 1))
            self.status_var.set(f"Beendet: {correct} von {total} QSOs richtig geloggt.")
        else:
            self.status_var.set("Beendet.")
        self.on_stop_cb()

    def _tick(self, session_id):
        if not self.running or session_id != self.session_id:
            return
        now = self.mixer.clock
        due = [e for e in self.events if e[0] <= now]
        self.events = [e for e in self.events if e[0] > now]
        for _, callback, args in sorted(due, key=lambda e: e[0]):
            callback(*args)
        if self.deadline is not None and time.time() >= self.deadline:
            self.stop()
            self.status_var.set("Zeit abgelaufen. " + self.status_var.get())
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
        text = f"QSOs: {total} · richtig: {correct} · Rate: {correct / hours:.0f}/h"
        if self.deadline is not None and self.running:
            remaining = max(int(self.deadline - time.time()), 0)
            text += f" · Rest {remaining // 60}:{remaining % 60:02d}"
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
            self.status_var.set("Erst ein Rufzeichen ins Call-Feld eintragen.")
            return
        text = {
            "cq": f"CQ {test} {self.my_call_str}",
            "exchange": f"{call} 5NN {self._my_exchange_text()}",
            "tu": f"TU {self.my_call_str}",
            "mycall": self.my_call_str,
            "hiscall": call,
            "query": "?",
            "agn": "AGN",
        }[kind]
        if kind == "tu":
            self._log_qso()
        elif kind == "exchange":
            self.exchange_sent_to = call

        self.mixer.cancel(None)
        self.msg_id += 1
        samples = build_text(text, self.wpm, self.freq)
        start = self.mixer.clock + int(0.05 * SAMPLE_RATE)
        self.my_tx_start = start
        self.my_tx_end = self.mixer.add(samples, None, start)
        self._schedule(self.my_tx_end, self._react, kind, call, self.msg_id)
        self.status_var.set(f"Sende: {text}")

    def _abort_sending(self):
        if self.running and self.mixer is not None:
            self.mixer.cancel(None)
            self.msg_id += 1
            self.my_tx_end = self.mixer.clock
            self.status_var.set("Abgebrochen.")
        return "break"

    def _on_enter(self, event=None):
        """ESM: leeres Call-Feld -> CQ; Call noch ohne Austausch -> Austausch;
        Austausch eingetragen -> TU + loggen; sonst Rückfrage."""
        call = self.call_var.get().strip()
        if not call:
            self._send("cq")
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
            ok, result = False, "NIL – keine Station hat dir einen Austausch gegeben"
        elif call != worked.call:
            ok, result = False, f"Call falsch – richtig: {worked.call}"
        elif not is_correct(exch, worked.exchange, worked.exchange_kind):
            ok, result = False, f"Austausch falsch – richtig: {worked.exchange}"
        else:
            ok, result = True, "✓"
        if worked is not None:
            worked.state = "done"
        self.log.append({"call": call, "exch": exch, "ok": ok})
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
        freq = self.freq + random.uniform(-CALLER_FREQ_OFFSET_HZ, CALLER_FREQ_OFFSET_HZ)
        caller = Caller(
            call=call, exchange=exchange, exchange_kind=exchange_kind, station=self.next_station % MAX_STATIONS,
            wpm=max(self.wpm + random.randint(*CALLER_WPM_OFFSET), 8), freq=min(max(freq, 300), 1000),
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

    def _send_exchange(self, caller: Caller, repeat: bool = False):
        caller.state = "worked"
        if repeat:
            text = f"{caller.exchange} {caller.exchange}"
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
            for caller in active:
                if caller is exact:
                    continue
                if caller.state == "worked":
                    caller.state = "waiting"  # du arbeitest jetzt jemand anderen
                if exact is None and matches[caller.call] == "similar":
                    self._call(caller, twice=True)  # korrigiert sein Rufzeichen
                elif caller.state == "calling":
                    caller.state = "waiting"
            if exact is not None:
                if kind == "exchange":
                    self._send_exchange(exact)
                elif exact.state == "worked":
                    self._send_exchange(exact, repeat=True)  # Call bestätigt: Austausch nochmal
                else:
                    self._call(exact)
            return

        if kind in ("query", "agn"):
            if worked is not None:
                self._send_exchange(worked, repeat=True)
            else:
                for caller in active:
                    self._call(caller)

    # --- Schnittstelle zur App ------------------------------------------------
    def on_function_key(self, key: str):
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
            "band": self.band_panel.settings(),
        }

    def restore_settings(self, data: dict) -> None:
        exchanges = data.get("my_exchanges")
        if isinstance(exchanges, dict):
            self.my_exchanges = {k: v for k, v in exchanges.items() if isinstance(v, str)}
        call = data.get("my_call")
        if isinstance(call, str) and call and all(ch in MORSE_CODE for ch in call):
            self.my_call_var.set(call)
        if data.get("kind") in qso_text.QSO_TYPES and data["kind"] != qso_text.RAGCHEW:
            self.kind_var.set(qso_text.QSO_TYPES[data["kind"]])
        for key, var, limits in (("activity", self.activity_var, (1, 5)), ("duration", self.duration_var, (0, 240))):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)
        self.band_panel.restore(data.get("band"))
        self._on_setup_change()

    def on_close(self):
        if self.mixer is not None:
            self.mixer.stop()
