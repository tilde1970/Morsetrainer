"""QSO-Modus: Hörtraining mit kompletten, realistischen CW-QSOs (Text aus
qso_text.py) – entweder ein normales QSO zwischen zwei Stationen oder ein
Contest-Run, in dem eine Run-Station mehrere Anrufer abarbeitet. Jede
Station sendet mit eigener Tonhöhe und etwas anderem Tempo, damit man die
Durchgänge wie in echt auseinanderhalten kann.

Drei Arten der Auswertung:
- Mitschreiben + Abfrage: frei mitnotieren, danach das Wichtigste
  eintragen (normales QSO: Rufzeichen, Name, QTH, Rapport beider Stationen;
  Contest: Rufzeichen und Austausch jedes QSOs, also das Log) und prüfen
  lassen.
- Fortlaufend mittippen: wie im Kontinuierlich-Modus jedes Zeichen
  mittippen; am Ende Levenshtein-Abgleich mit dem gesendeten Text, die
  Zeichen fließen in die Statistik ein.
- Nur hören: keine Bewertung, der Klartext lässt sich jederzeit aufdecken.

Zuschaltbar sind Kurzwellen-Bandbedingungen (Rauschen mit Knackstörungen,
QSB, Chirp, SSB-Gebrabbel und CW-QRM auf der Nachbarfrequenz), siehe band.py.

Unabhängig vom oben eingestellten Zeichensatz."""
import random
import threading
import time
import tkinter as tk
from tkinter import ttk

import sounddevice as sd

import align
import qso_text
from band import BandConditions
from qso_quiz import QuizPanel
from ui_widgets import BandSettingsPanel, ScrollableFrame
from morse import (
    AUDIO_LATENCY, MORSE_CODE, PROSIGNS, SAMPLE_RATE, build_samples, char_gap_seconds, code_units, silence,
    word_gap_extra_seconds,
)
from stats import SessionStats
from stats_widget import StatsPanel

EVAL_QUIZ, EVAL_TYPING, EVAL_LISTEN = "quiz", "typing", "listen"
EVAL_LABELS = {
    EVAL_QUIZ: "Mitschreiben + Abfrage",
    EVAL_TYPING: "Fortlaufend mittippen",
    EVAL_LISTEN: "Nur hören",
}
LENGTH_LABELS = ["Kurz", "Normal", "Lang"]  # Index = qso_text.LENGTH_*

# Pause zwischen zwei Durchgängen (Umschalten auf Empfang, Gegenstation
# setzt ein); im Contest geht es deutlich zackiger.
TX_GAP_SECONDS = 1.2
CONTEST_TX_GAP_SECONDS = 0.5
LEAD_IN_SECONDS = 0.3
# Mit Rauschen/QRM: erst etwas zum Einhören, am Ende kurz ausklingen.
NOISE_LEAD_IN_SECONDS = 1.5
NOISE_TAIL_SECONDS = 1.0
# Versatz der anderen Stationen gegenüber Station 1 in Hz (zufälliges
# Vorzeichen) und in WPM. Contest-Anrufer liegen mal fast auf der Frequenz,
# mal weiter daneben.
FREQ_OFFSET_RANGE = (80, 150)
CONTEST_FREQ_OFFSET_RANGE = (40, 250)
WPM_OFFSETS = (-2, -1, 0, 1, 2)
CONTEST_WPM_OFFSETS = (-3, -2, -1, 0, 1, 2, 3)
WRITE_CHUNK_SECONDS = 0.02
FINISH_GRACE_SECONDS = 3
TICK_MS = 250

# Station 1 bzw. Run-Station, dann abwechselnd für die Gegenstationen.
STATION_COLORS = ("#1f5fbf", "#b35900", "#2e8b57")


def _voice(wpm: int, freq: int, offset_range, wpm_offsets):
    offset = random.choice((-1, 1)) * random.randint(*offset_range)
    if not 300 <= freq + offset <= 1000:
        offset = -offset
    return max(wpm + random.choice(wpm_offsets), 5), freq + offset


class QsoModeFrame:
    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop):
        self.root = parent.winfo_toplevel()
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.farnsworth_wpm = farnsworth_wpm  # callable -> effektive WPM oder None
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.tracking = False      # aktueller Durchlauf wird mitgetippt und ausgewertet
        self.qso = None
        self.voices = ()           # (wpm, freq) je Stationsindex
        self.band = None           # BandConditions des aktuellen QSOs
        self.fw = None
        self.current_tx = 0
        self.sent_log = []         # [{"char": str, "end_time": float}]
        self.typed_log = []        # [{"char": str, "time": float}]
        self.char_marks = None     # (Anzahl gesendeter Zeichen, Indizes falscher/verpasster)
        self.play_thread = None
        self.session_stats = None
        self.session_id = 0
        self.finishing = False
        self.revealed = False
        self.quiz_ready = False    # QSO einmal komplett gelaufen, Abfrage verfügbar
        self.quiz_checked = False

        self._build_widgets(ScrollableFrame(parent).inner)
        self._update_layout()

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            parent,
            text="Hör einem kompletten CW-QSO oder einem Contest-Run zu. Jede Station hat eine "
                 "eigene Tonhöhe. "
                 "„=“ ist BT (Trennung), „+“ ist AR (Ende des Durchgangs); <SK>, <KN> und <BK> "
                 "werden zusammengezogen gesendet und beim Mittippen nicht gezählt. "
                 "Der Zeichensatz oben gilt hier nicht.",
            wraplength=460, justify="left",
        ).pack(anchor="w", padx=8, pady=(4, 8))

        self._build_qso_settings(parent)
        self.band_panel = BandSettingsPanel(parent, on_change=self._apply_band_settings)

        self.eval_var.trace_add("write", lambda *_: self._on_eval_change())
        self.kind_var.trace_add("write", lambda *_: self._on_kind_change())
        self.length_var.trace_add("write", lambda *_: self._update_length_hint())

        controls = ttk.Frame(parent)
        controls.pack(fill="x", **pad)
        self.start_button = ttk.Button(controls, text="Neues QSO", command=self.toggle_running)
        self.start_button.pack(side="left", **pad)
        self.replay_button = ttk.Button(controls, text="Nochmal hören", command=self.replay, state="disabled")
        self.replay_button.pack(side="left", **pad)
        self.reveal_button = ttk.Button(controls, text="Text zeigen", command=self.toggle_reveal, state="disabled")
        self.reveal_button.pack(side="left", **pad)

        self.status_var = tk.StringVar(value="Bereit. Drücke „Neues QSO“.")
        ttk.Label(parent, textvariable=self.status_var, font=("Sans", 14)).pack(pady=8)

        # Ein- und ausblendbare Bereiche; _update_layout() packt die jeweils
        # sichtbaren in fester Reihenfolge.
        self.notes_box = ttk.LabelFrame(parent, text="Notizen (frei, werden nicht ausgewertet)")
        self.notes = tk.Text(self.notes_box, height=4, wrap="word", font=("Consolas", 11))
        self.notes.pack(fill="x", padx=4, pady=4)

        self.typed_box = ttk.Frame(parent)
        ttk.Label(self.typed_box, text="Deine Eingabe (letzte Zeichen):").pack(anchor="w")
        self.typed_preview_var = tk.StringVar(value="")
        ttk.Label(self.typed_box, textvariable=self.typed_preview_var, font=("Consolas", 12), wraplength=440).pack(
            anchor="w"
        )

        self.quiz = QuizPanel(parent, on_checked=self._on_quiz_checked)
        self.quiz_box = self.quiz.box

        self.reveal_box = ttk.LabelFrame(parent, text="QSO-Text")
        self.reveal_text = tk.Text(self.reveal_box, height=8, wrap="word", font=("Consolas", 11))
        scroll = ttk.Scrollbar(self.reveal_box, orient="vertical", command=self.reveal_text.yview)
        self.reveal_text.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.reveal_text.pack(fill="x", padx=4, pady=4)
        for i, color in enumerate(STATION_COLORS):
            self.reveal_text.tag_config(f"st{i}", foreground=color)
        self.reveal_text.tag_config("miss", foreground="white", background="#d9534f")
        self.reveal_text.tag_config("unsent", foreground="#999999")
        self.reveal_text.config(state="disabled")

        self.stats_box = ttk.Frame(parent)
        self.stats_panel = StatsPanel(self.stats_box, tree_height=5)

    def _build_qso_settings(self, parent):
        box = ttk.LabelFrame(parent, text="QSO")
        box.pack(fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        row_pad = {"padx": (8, 4), "pady": 2}

        ttk.Label(box, text="Art:").grid(row=0, column=0, sticky="w", **row_pad)
        self.kind_var = tk.StringVar(value=qso_text.QSO_TYPES[qso_text.RAGCHEW])
        self.kind_combo = ttk.Combobox(
            box, textvariable=self.kind_var, values=list(qso_text.QSO_TYPES.values()), state="readonly", width=32,
        )
        self.kind_combo.grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Auswertung:").grid(row=1, column=0, sticky="w", **row_pad)
        self.eval_var = tk.StringVar(value=EVAL_LABELS[EVAL_QUIZ])
        self.eval_combo = ttk.Combobox(
            box, textvariable=self.eval_var, values=list(EVAL_LABELS.values()), state="readonly", width=32
        )
        self.eval_combo.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Länge:").grid(row=2, column=0, sticky="w", **row_pad)
        length_row = ttk.Frame(box)
        length_row.grid(row=2, column=1, sticky="w", pady=(2, 6))
        self.length_var = tk.StringVar(value=LENGTH_LABELS[qso_text.LENGTH_NORMAL])
        self.length_combo = ttk.Combobox(
            length_row, textvariable=self.length_var, values=LENGTH_LABELS, state="readonly", width=10
        )
        self.length_combo.pack(side="left")
        self.length_hint_var = tk.StringVar(value="")
        ttk.Label(length_row, textvariable=self.length_hint_var).pack(side="left", padx=(8, 0))

    def _kind(self) -> str:
        for key, label in qso_text.QSO_TYPES.items():
            if label == self.kind_var.get():
                return key
        return qso_text.RAGCHEW

    def _apply_band_settings(self):
        """Auch während der Wiedergabe: der Audio-Thread liest nur die
        einfachen Attribute von self.band."""
        if self.band is not None:
            self.band_panel.apply_to(self.band)
            self.band.prepare(self.voices[0][1])

    def _on_kind_change(self):
        self._update_length_hint()
        if self.qso is None:
            self._update_layout()

    def _update_length_hint(self):
        if self._kind() == qso_text.RAGCHEW:
            self.length_hint_var.set("")
        else:
            count = qso_text.CONTEST_QSO_COUNTS[LENGTH_LABELS.index(self.length_var.get())]
            self.length_hint_var.set(f"{count} QSOs")

    def _eval_mode(self) -> str:
        for key, label in EVAL_LABELS.items():
            if label == self.eval_var.get():
                return key
        return EVAL_QUIZ

    def _on_eval_change(self):
        self._update_layout()
        self._update_reveal_button()

    def _update_layout(self):
        mode = self._eval_mode()
        # Im Contest wird direkt ins Log geschrieben, schon während des Hörens.
        contest = self.qso.is_contest if self.qso is not None else self._kind() != qso_text.RAGCHEW
        live_log = contest and mode == EVAL_QUIZ and self.qso is not None
        boxes = [
            (self.notes_box, mode == EVAL_LISTEN or (mode == EVAL_QUIZ and not contest and not self.quiz_checked)),
            (self.typed_box, mode == EVAL_TYPING),
            (self.quiz_box, mode == EVAL_QUIZ and (self.quiz_ready or live_log)),
            (self.reveal_box, self.revealed),
            (self.stats_box, mode == EVAL_TYPING),
        ]
        for box, _ in boxes:
            box.pack_forget()
        for box, visible in boxes:
            if visible:
                box.pack(fill="x", padx=8, pady=4)

    def _update_reveal_button(self):
        # Während des ersten Durchlaufs nur im reinen Hörmodus aufdeckbar,
        # sonst wäre die Abfrage bzw. das Mittippen witzlos.
        allowed = self.qso is not None and not self.tracking and (
            not self.running or self.quiz_ready or self._eval_mode() == EVAL_LISTEN
        )
        self.reveal_button.config(
            state="normal" if allowed else "disabled",
            text="Text verbergen" if self.revealed else "Text zeigen",
        )

    # --- Ablauf -----------------------------------------------------------
    def toggle_running(self):
        if self.running:
            self._finish(stopped=True)
        else:
            self.start_new()

    def start_new(self):
        try:
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except tk.TclError:
            self.status_var.set("Ungültige Geschwindigkeit oder Tonhöhe!")
            return
        self.qso = qso_text.generate_qso(self._kind(), LENGTH_LABELS.index(self.length_var.get()))
        if self.qso.is_contest:
            offsets, wpm_offsets = CONTEST_FREQ_OFFSET_RANGE, CONTEST_WPM_OFFSETS
        else:
            offsets, wpm_offsets = FREQ_OFFSET_RANGE, WPM_OFFSETS
        self.voices = ((wpm, freq),) + tuple(
            _voice(wpm, freq, offsets, wpm_offsets) for _ in self.qso.calls[1:]
        )
        self.band = BandConditions(len(self.qso.calls))
        self._apply_band_settings()
        self.fw = self.farnsworth_wpm()
        self.revealed = False
        self.quiz_ready = False
        self.quiz_checked = False
        self.char_marks = None
        self.quiz.reset(self.qso)
        self.notes.delete("1.0", "end")
        self._play(tracking=self._eval_mode() == EVAL_TYPING)

    def replay(self):
        """Spielt das letzte QSO noch einmal ab, ohne Auswertung."""
        if self.qso is not None and not self.running:
            self._play(tracking=False)

    def _play(self, tracking: bool):
        self.tracking = tracking
        self.sent_log = []
        self.typed_log = []
        self.current_tx = 0
        self.finishing = False
        self.session_id += 1
        self.band.rewind()
        if tracking:
            wpm, freq = self.voices[0]
            self.session_stats = SessionStats(
                "qso", "QSO-Text", wpm, freq, farnsworth_wpm=self.fw,
                group_len={"kind": self.qso.kind, "length": self.length_var.get(), "calls": list(self.qso.calls),
                           "voices": [list(v) for v in self.voices]},
            )
            self.stats_panel.reset()
            self.typed_preview_var.set("")

        self.running = True
        self.start_button.config(text="Stop")
        self.replay_button.config(state="disabled")
        for combo in (self.kind_combo, self.eval_combo, self.length_combo):
            combo.config(state="disabled")
        if not self.quiz_ready:
            self.quiz.set_check_enabled(False)
        self._update_reveal_button()
        self._update_layout()
        self.on_start_cb()

        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        self.root.after(TICK_MS, self._tick, self.session_id)

    def _play_loop(self):
        with sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=AUDIO_LATENCY
        ) as stream:
            lead_in = NOISE_LEAD_IN_SECONDS if self.band.has_background else LEAD_IN_SECONDS
            if not self._write(stream, silence(lead_in)):
                return
            gap = CONTEST_TX_GAP_SECONDS if self.qso.is_contest else TX_GAP_SECONDS
            for tx_index, (station, text) in enumerate(self.qso.transmissions):
                self.current_tx = tx_index
                wpm, freq = self.voices[station]
                if tx_index and not self._write(stream, silence(gap)):
                    return
                for ch in text:
                    if ch == " ":
                        if not self._write(stream, silence(word_gap_extra_seconds(wpm, self.fw))):
                            return
                        continue
                    if not self._write(stream, build_samples(ch, wpm, freq, self.fw, self.band.chirp_for(station)), station):
                        return
                    if self.tracking and ch not in PROSIGNS:
                        # Wie im Kontinuierlich-Modus: hörbar endet der Ton erst
                        # nach stream.latency, die Zeichenpause zählt nicht mit.
                        tone_end = time.time() + stream.latency - char_gap_seconds(wpm, self.fw)
                        self.sent_log.append({"char": ch, "end_time": tone_end})
            if self.band.has_background:
                self._write(stream, silence(NOISE_TAIL_SECONDS))

    def _write(self, stream, samples, station: int = 0) -> bool:
        """Schreibt `samples` (von Station `station`) häppchenweise, ggf. mit
        Rauschen/QSB; False, wenn zwischendurch gestoppt wurde."""
        chunk = int(SAMPLE_RATE * WRITE_CHUNK_SECONDS)
        for start in range(0, len(samples), chunk):
            if not self.running:
                return False
            block = samples[start:start + chunk]
            if self.band.active:
                block = self.band.process(block, station)
            stream.write(block)
        return True

    def _tick(self, session_id):
        if not self.running or session_id != self.session_id:
            return
        if self.tracking:
            self.typed_preview_var.set("".join(e["char"] for e in self.typed_log)[-60:])
        if self.play_thread.is_alive():
            label = "Wiederholung – " if not self.tracking and self.quiz_ready else ""
            self.status_var.set(f"{label}Durchgang {self.current_tx + 1} von {len(self.qso.transmissions)}")
        elif not self.tracking:
            self._finish()
            return
        elif not self.finishing:
            self.finishing = True
            self.status_var.set("QSO zu Ende – tippe die letzten Zeichen noch ein…")
            self.root.after(FINISH_GRACE_SECONDS * 1000, self._auto_finish, session_id)
        self.root.after(TICK_MS, self._tick, session_id)

    def _auto_finish(self, session_id):
        if self.running and session_id == self.session_id:
            self._finish()

    def _finish(self, stopped: bool = False):
        self.running = False
        if self.play_thread is not None:
            self.play_thread.join(timeout=2)
            self.play_thread = None
        self.start_button.config(text="Neues QSO")
        self.replay_button.config(state="normal")
        for combo in (self.kind_combo, self.eval_combo, self.length_combo):
            combo.config(state="readonly")

        mode = self._eval_mode()
        if self.tracking:
            self._finalize_session()
            self.revealed = True
            self.tracking = False
            self.status_var.set("Ausgewertet – rot markiert: falsch oder verpasst.")
        elif mode == EVAL_QUIZ and not self.quiz_checked:
            what = "Ergänze dein Log" if self.qso.is_contest else "Trag ein, was du gehört hast,"
            self.status_var.set(f"{what} und drück „Prüfen“.")
        else:
            self.status_var.set("QSO beendet.")
        if stopped:
            self.status_var.set("Gestoppt. " + self.status_var.get())
        self.quiz_ready = True
        self.quiz.set_check_enabled(True)

        self._update_layout()
        self._update_reveal_button()
        self._render_reveal()
        self.on_stop_cb()

    def _finalize_session(self):
        if self.session_stats is None:
            return
        sent_str = "".join(e["char"] for e in self.sent_log)
        typed_str = "".join(e["char"] for e in self.typed_log)
        missed = set()
        for op in align.align(sent_str, typed_str):
            if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE):
                correct = op.kind == align.OpKind.MATCH
                play_end = self.sent_log[op.expected_index]["end_time"]
                typed_time = self.typed_log[op.received_index]["time"]
                reaction_time = max(typed_time - play_end, 0.001)
                effective_wpm = code_units(op.expected_char) * 1.2 / reaction_time
                self.session_stats.record_char(
                    op.expected_char, op.received_char, correct, reaction_time, effective_wpm,
                    latency=reaction_time,
                )
                if not correct:
                    missed.add(op.expected_index)
            elif op.kind == align.OpKind.DELETE:
                self.session_stats.record_char(op.expected_char, "", False, 0.0, 0.0)
                missed.add(op.expected_index)
            # INSERT (Tippen ohne gesendetes Zeichen) zählt für kein Zeichen.
        self.char_marks = (len(sent_str), missed)
        self.session_stats.record_group(self.qso.text(), typed_str)

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path)
        self.session_stats = None

    # --- Klartext -----------------------------------------------------------
    def toggle_reveal(self):
        if self.qso is None:
            return
        self.revealed = not self.revealed
        self._render_reveal()
        self._update_layout()
        self._update_reveal_button()

    def _render_reveal(self):
        if not self.revealed or self.qso is None:
            return
        text = self.reveal_text
        text.config(state="normal")
        text.delete("1.0", "end")
        index = 0  # Position im gesendeten Text ohne Leerzeichen und Betriebszeichen (wie sent_log)
        for n, (station, tx) in enumerate(self.qso.transmissions):
            if n:
                text.insert("end", "\n\n")
            for ch in tx:
                tags = [f"st{0 if station == 0 else 1 + (station - 1) % 2}"]
                if ch in PROSIGNS:
                    text.insert("end", f"<{PROSIGNS[ch]}>", tuple(tags))
                    continue
                if ch != " ":
                    if self.char_marks is not None:
                        sent_count, missed = self.char_marks
                        if index >= sent_count:
                            tags.append("unsent")
                        elif index in missed:
                            tags.append("miss")
                    index += 1
                text.insert("end", ch, tuple(tags))
        text.config(state="disabled")

    # --- Abfrage ------------------------------------------------------------
    def _on_quiz_checked(self, correct: int, total: int):
        self.quiz_checked = True
        self.revealed = True
        self.status_var.set("Abfrage ausgewertet.")
        self._render_reveal()
        self._update_layout()
        self._update_reveal_button()

    # --- Schnittstelle zur App ------------------------------------------------
    def settings(self) -> dict:
        """Einstellungen zum Speichern in window_state.json (Schlüssel statt
        Beschriftungen, damit Umbenennungen alte Dateien nicht entwerten)."""
        return {
            "kind": self._kind(),
            "eval": self._eval_mode(),
            "length": LENGTH_LABELS.index(self.length_var.get()),
            "band": self.band_panel.settings(),
        }

    def restore_settings(self, data: dict) -> None:
        """Gegenstück zu settings(); unbekannte oder kaputte Werte werden
        ignoriert."""
        if data.get("kind") in qso_text.QSO_TYPES:
            self.kind_var.set(qso_text.QSO_TYPES[data["kind"]])
        if data.get("eval") in EVAL_LABELS:
            self.eval_var.set(EVAL_LABELS[data["eval"]])
        length = data.get("length")
        if isinstance(length, int) and 0 <= length < len(LENGTH_LABELS):
            self.length_var.set(LENGTH_LABELS[length])
        self.band_panel.restore(data.get("band"))

    def on_close(self):
        if self.running:
            self.running = False
            if self.play_thread is not None:
                self.play_thread.join(timeout=2)
        self._finalize_session()

    def on_key(self, event):
        if not (self.running and self.tracking):
            return
        typed = event.char.upper()
        if typed and typed in MORSE_CODE:
            self.typed_log.append({"char": typed, "time": time.time()})
