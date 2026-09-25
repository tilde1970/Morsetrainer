"""Kontinuierlicher Modus: Audio läuft in einem Hintergrund-Thread ohne
Pause weiter, unabhängig davon ob/wie schnell du tippst (wie beim Mithören
von echtem CW-Verkehr). Du tippst fortlaufend mit; ein Levenshtein-Alignment
zwischen gesendeter und getippter Zeichenkette (analog zu morse_trainer_cont.py
in WZab/morse_trainer, hier direkt auf Strings statt mit eigenem Audio-Queue-
Player reimplementiert) ordnet am Ende jedem gesendeten Zeichen zu, ob es
richtig, falsch oder gar nicht getippt wurde – auch wenn zwischendurch
Zeichen übersprungen wurden.

Vereinfachung gegenüber dem Original: die Live-Anzeige während der Session
ist nur eine grobe, alle 1s neu berechnete Vorschau; die für die Statistik
verwendete, endgültige Zuordnung passiert erst beim Stop in einem einzigen
Alignment-Durchlauf über die komplette Session."""
import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd

from morsetrainer.core import align
from morsetrainer.core.morse import (
    AUDIO_LATENCY, END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text,
    char_gap_seconds, code_units, silence, word_gap_extra_seconds,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.core.weighting import CharPicker

# Der Audio-Thread schreibt die Zeichen in so großen Häppchen in den Stream,
# damit ein Stop nicht erst das ganze (evtl. lange Farnsworth-)Zeichen
# abwarten muss.
WRITE_CHUNK_SECONDS = 0.02

# Nach Ablauf der eingestellten Dauer wird nichts Neues mehr gesendet; so
# lange bleibt noch Zeit, die zuletzt gehörten Zeichen einzutippen.
FINISH_GRACE_SECONDS = 3


class ContinuousModeFrame:
    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop):
        self.root = parent.winfo_toplevel()
        self.charset_var = charset_var
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.weighted_var = weighted_var
        self.farnsworth_wpm = farnsworth_wpm  # callable -> effektive WPM oder None
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.charset = ""
        self.picker = None
        self.wpm = 15
        self.freq = 600
        self.sent_log = []    # [{"char": str, "end_time": float}]
        self.typed_log = []   # [{"char": str, "time": float}]
        self.play_thread = None
        self.session_stats = None
        self.deadline = None      # time.time(), ab der nichts Neues mehr gesendet wird
        self.finishing = False    # Zeit abgelaufen, Auto-Stop ist eingeplant
        self.end_sent = False     # Schlusszeichen schon gesendet
        self.session_id = 0       # damit ein alter Auto-Stop keine neue Sitzung beendet

        self._build_widgets(parent)

    def _build_widgets(self, parent):
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            parent,
            text="Der Ton läuft durch, ohne auf dich zu warten. Tippe mit, was du erkennst "
                 "– auch wenn du mal hinterherhinkst. Auswertung erfolgt beim Stoppen.",
            wraplength=440, justify="left",
        ).pack(anchor="w", padx=8, pady=(4, 8))

        controls = ttk.Frame(parent)
        controls.pack(fill="x", **pad)
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.pack(side="left", **pad)
        ttk.Label(controls, text="Dauer:").pack(side="left", padx=(8, 4))
        self.duration_var = tk.IntVar(value=5)
        ttk.Spinbox(controls, from_=0, to=120, textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(controls, text="Min. (0 = ohne Limit)").pack(side="left", padx=(4, 0))

        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(parent, textvariable=self.status_var, font=("Sans", 14)).pack(pady=10)

        self.live_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.live_var, font=("Sans", 11)).pack(anchor="w", padx=8)

        ttk.Label(parent, text="Deine Eingabe (letzte Zeichen):").pack(anchor="w", padx=8, pady=(8, 0))
        self.typed_preview_var = tk.StringVar(value="")
        ttk.Label(
            parent, textvariable=self.typed_preview_var, font=("Consolas", 12), wraplength=440
        ).pack(anchor="w", padx=8)

        self.stats_panel = StatsPanel(parent)

    def toggle_running(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set("Kein gültiges Zeichen im Zeichensatz!")
            return
        try:
            minutes = self.duration_var.get()
        except tk.TclError:
            minutes = -1
        if minutes < 0:
            self.status_var.set("Ungültige Dauer!")
            return
        self.deadline = time.time() + minutes * 60 if minutes else None
        self.finishing = False
        self.end_sent = False
        self.session_id += 1
        self.charset = charset
        self.wpm = self.wpm_var.get()
        self.freq = self.freq_var.get()
        self.fw = self.farnsworth_wpm()
        self.sent_log = []
        self.typed_log = []
        self.session_stats = SessionStats("continuous", charset, self.wpm, self.freq, farnsworth_wpm=self.fw)
        # Ohne Session: die Zuordnung gesendet/getippt steht erst beim Stop
        # fest, während der Sitzung zählt daher nur die Gesamtstatistik.
        self.picker = CharPicker(charset, self.weighted_var.get())
        self.stats_panel.reset()
        self.live_var.set("Gesendet: 0 Zeichen")
        self.typed_preview_var.set("")

        self.running = True
        self.start_button.config(text="Stop")
        self.status_var.set("Läuft – höre zu und tippe mit…")
        self.on_start_cb()

        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        self.root.after(1000, self._tick)

    def _play_loop(self):
        # Ein durchgehender Stream für die ganze Sitzung: Zeichen werden
        # lückenlos hintergeschrieben. Ein eigener Stream pro Zeichen
        # (sd.play + sd.wait) knackt beim Öffnen/Schließen und reißt Lücken.
        with sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=AUDIO_LATENCY
        ) as stream:
            # Einleitung, wird nicht ausgewertet (landet nicht in sent_log).
            if not self._write(stream, build_text(START_TEXT + " ", self.wpm, self.freq, self.fw)):
                return
            while self.running and not self._time_up():
                char = self.picker.pick()
                samples = build_samples(char, self.wpm, self.freq, self.fw)
                if not self._write(stream, samples):
                    break
                # write() kehrt zurück, sobald die Samples im Puffer sind; zu
                # hören ist ihr Ende erst nach stream.latency. Die Reaktionszeit
                # zählt ab dem Ende des Tons, also vor der Pause dahinter.
                tone_end = time.time() + stream.latency - char_gap_seconds(self.wpm, self.fw)
                self.sent_log.append({"char": char, "end_time": tone_end})
            if self.running:
                # Zeit abgelaufen: Wortpause und Schlusszeichen direkt hinterher.
                ending = np.concatenate([
                    silence(word_gap_extra_seconds(self.wpm, self.fw)),
                    build_text(END_TEXT, self.wpm, self.freq),
                ])
                self.end_sent = self._write(stream, ending)

    def _time_up(self) -> bool:
        return self.deadline is not None and time.time() >= self.deadline

    def _auto_stop(self, session_id):
        if self.running and session_id == self.session_id:
            self.stop()
            self.status_var.set("Zeit abgelaufen – Durchgang ausgewertet.")

    def _write(self, stream, samples) -> bool:
        """Schreibt `samples` häppchenweise; False, wenn zwischendurch
        gestoppt wurde."""
        chunk = int(SAMPLE_RATE * WRITE_CHUNK_SECONDS)
        for start in range(0, len(samples), chunk):
            if not self.running:
                return False
            stream.write(samples[start:start + chunk])
        return True

    def _tick(self):
        if not self.running:
            return
        sent_str = "".join(e["char"] for e in self.sent_log)
        typed_str = "".join(e["char"] for e in self.typed_log)
        live = f"Gesendet: {len(self.sent_log)} Zeichen"
        if sent_str:
            ops = align.align(sent_str, typed_str)
            matches = sum(1 for op in ops if op.kind == align.OpKind.MATCH)
            expected_total = sum(
                1 for op in ops if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE, align.OpKind.DELETE)
            )
            pct = (matches / expected_total * 100) if expected_total else 0.0
            live += f" · vorläufige Trefferquote: {pct:.0f}%"
        if self.deadline is not None:
            remaining = max(int(self.deadline - time.time()), 0)
            live += f" · Restzeit {remaining // 60}:{remaining % 60:02d}"
        self.live_var.set(live)
        # Erst wenn auch das letzte Zeichen fertig gesendet ist (der Audio-Thread
        # hat sich beendet), läuft die Frist fürs Nachtippen.
        if self._time_up() and not self.play_thread.is_alive() and not self.finishing:
            self.finishing = True
            self.status_var.set("Zeit abgelaufen – tippe die letzten Zeichen noch ein…")
            self.root.after(FINISH_GRACE_SECONDS * 1000, self._auto_stop, self.session_id)
        self.typed_preview_var.set(typed_str[-60:])
        self.root.after(1000, self._tick)

    def stop(self):
        self.running = False
        if self.play_thread is not None:
            self.play_thread.join(timeout=2)
            self.play_thread = None
        if not self.end_sent:
            # Manueller Stop: Schlusszeichen nachschieben (eigener Stream,
            # der Sitzungs-Stream ist schon zu).
            self.end_sent = True
            sd.play(build_text(END_TEXT, self.wpm, self.freq), SAMPLE_RATE, latency=AUDIO_LATENCY)
        self.start_button.config(text="Start")
        self.status_var.set("Werte aus…")
        self._finalize_session()
        self.status_var.set("Gestoppt.")
        self.on_stop_cb()

    def _finalize_session(self):
        if self.session_stats is None:
            return
        sent_str = "".join(e["char"] for e in self.sent_log)
        typed_str = "".join(e["char"] for e in self.typed_log)
        ops = align.align(sent_str, typed_str)
        for op in ops:
            if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE):
                expected_char = op.expected_char
                typed_char = op.received_char
                correct = op.kind == align.OpKind.MATCH
                play_end = self.sent_log[op.expected_index]["end_time"]
                typed_time = self.typed_log[op.received_index]["time"]
                reaction_time = max(typed_time - play_end, 0.001)
                effective_wpm = code_units(expected_char) * 1.2 / reaction_time
                self.session_stats.record_char(
                    expected_char, typed_char, correct, reaction_time, effective_wpm, latency=reaction_time
                )
            elif op.kind == align.OpKind.DELETE:
                self.session_stats.record_char(op.expected_char, "", False, 0.0, 0.0)
            # INSERT (stray keystroke with no corresponding sent character) is not
            # attributable to any Morse character and is skipped for the stats.

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path)
        self.session_stats = None

    def on_close(self):
        if self.running:
            self.running = False
            if self.play_thread is not None:
                self.play_thread.join(timeout=2)
        self._finalize_session()

    def on_key(self, event):
        if not self.running:
            return
        typed = event.char.upper()
        if not typed or typed not in MORSE_CODE:
            return
        self.typed_log.append({"char": typed, "time": time.time()})