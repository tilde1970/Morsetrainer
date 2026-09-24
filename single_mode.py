"""Einzelzeichen-Modus: spielt ein Morsezeichen ab, wartet auf Tastatureingabe,
prüft die Antwort und spielt danach das nächste Zeichen. Bei einer falschen
Antwort wird dasselbe Zeichen sofort wiederholt (statt zufällig weiterzumachen),
bis es richtig erkannt wird."""
import time
import tkinter as tk
from tkinter import ttk

import sounddevice as sd

import sfx
from morse import AUDIO_LATENCY, MORSE_CODE, SAMPLE_RATE, build_samples, code_units, duration_seconds
from stats import SessionStats
from stats_widget import StatsPanel
from weighting import CharPicker


class SingleModeFrame:
    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop):
        self.root = parent.winfo_toplevel()
        self.charset_var = charset_var
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.weighted_var = weighted_var
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.waiting_for_input = False
        self.current_char = None
        self.charset = ""
        self.picker = None
        self.history = []
        self.session_stats = None
        self.play_start_time = 0.0
        self.repeat_pending = False

        self._build_widgets(parent)

    def _build_widgets(self, parent):
        pad = {"padx": 8, "pady": 4}

        controls = ttk.Frame(parent)
        controls.pack(fill="x", **pad)
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.pack(side="left", **pad)
        self.repeat_button = ttk.Button(
            controls, text="Wiederholen", command=self.repeat_char, state="disabled"
        )
        self.repeat_button.pack(side="left", **pad)
        self.sound_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Quittungston", variable=self.sound_var).pack(side="left", **pad)

        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(parent, textvariable=self.status_var, font=("Sans", 14)).pack(pady=10)

        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = ttk.Label(parent, textvariable=self.feedback_var, font=("Sans", 20, "bold"))
        self.feedback_label.pack(pady=10)

        self.stats_panel = StatsPanel(parent)

        ttk.Label(parent, text="Verlauf (letzte 40):").pack(anchor="w", padx=8)
        self.history_var = tk.StringVar(value="")
        ttk.Label(
            parent, textvariable=self.history_var, font=("Consolas", 12), wraplength=440
        ).pack(anchor="w", padx=8)

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
        self.charset = charset
        self.running = True
        self.repeat_pending = False
        self.start_button.config(text="Stop")
        self.repeat_button.config(state="normal")
        self.feedback_var.set("")
        self.session_stats = SessionStats("single", charset, self.wpm_var.get(), self.freq_var.get())
        self.picker = CharPicker(charset, self.weighted_var.get(), self.session_stats)
        self.history = []
        self.history_var.set("")
        self.stats_panel.reset()
        self.on_start_cb()
        self.next_char()

    def stop(self):
        self.running = False
        self.waiting_for_input = False
        self.start_button.config(text="Start")
        self.repeat_button.config(state="disabled")
        sd.stop()
        self._finalize_session()
        self.status_var.set("Gestoppt.")
        self.on_stop_cb()

    def _finalize_session(self):
        if self.session_stats is None:
            return
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path)
        self.session_stats = None

    def on_close(self):
        self._finalize_session()

    def next_char(self):
        if not self.running:
            return
        self.waiting_for_input = False
        if not self.repeat_pending:
            self.current_char = self.picker.pick()
        was_repeat = self.repeat_pending
        self.repeat_pending = False
        self.feedback_var.set("")
        self.status_var.set("Höre zu… (Wiederholung)" if was_repeat else "Höre zu…")
        self.play_current()

    def play_current(self):
        # Falls das WPM-/Tonhöhe-Feld gerade mitten im Bearbeiten ist (z. B.
        # Feld geleert, um eine neue Zahl einzutippen), ist der Wert kurzzeitig
        # ungültig; dann den zuletzt bekannten Wert weiterverwenden statt
        # abzustürzen.
        try:
            wpm = self.wpm_var.get()
        except tk.TclError:
            wpm = getattr(self, "_last_wpm", 15)
        try:
            freq = self.freq_var.get()
        except tk.TclError:
            freq = getattr(self, "_last_freq", 600)
        self._last_wpm, self._last_freq = wpm, freq
        samples = build_samples(self.current_char, wpm, freq)
        # Hörbar wird der Ton erst nach der Ausgabelatenz; ab dann zählt die
        # Reaktionszeit, und erst danach ist er zu Ende.
        self.play_start_time = time.time() + AUDIO_LATENCY
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
        dur_ms = int(duration_seconds(self.current_char, wpm) * 1000) + 150 + int(AUDIO_LATENCY * 1000)
        self.root.after(dur_ms, self.on_playback_done)

    def on_playback_done(self):
        if not self.running:
            return
        self.waiting_for_input = True
        self.status_var.set("Deine Eingabe?")

    def repeat_char(self):
        if self.running and self.current_char:
            self.waiting_for_input = False
            self.status_var.set("Höre zu… (Wiederholung)")
            self.play_current()

    def on_key(self, event):
        if not self.waiting_for_input:
            return
        typed = event.char.upper()
        if not typed or typed not in MORSE_CODE:
            return
        self.waiting_for_input = False
        correct = typed == self.current_char

        reaction_time = max(time.time() - self.play_start_time, 0.001)
        effective_wpm = code_units(self.current_char) * 1.2 / reaction_time
        latency = reaction_time - duration_seconds(self.current_char, self._last_wpm)
        self.session_stats.record_char(
            self.current_char, typed, correct, reaction_time, effective_wpm, latency=latency
        )
        self.repeat_pending = not correct

        if correct:
            if self.sound_var.get():
                sfx.play_ok()
            self.feedback_var.set(f"Richtig: {self.current_char}  ({effective_wpm:.0f} WPM)")
            self.feedback_label.config(foreground="green")
        else:
            if self.sound_var.get():
                sfx.play_error()
            self.feedback_var.set(f"Falsch: war {self.current_char}, du: {typed}")
            self.feedback_label.config(foreground="red")

        self.history.append(correct)
        self.history = self.history[-40:]
        self.history_var.set("".join("✓" if ok else "✗" for ok in self.history))

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

        self.root.after(700, self.next_char)