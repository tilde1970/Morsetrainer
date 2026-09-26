"""Einzelzeichen-Modus: spielt ein Morsezeichen ab, wartet auf Tastatureingabe,
prüft die Antwort und spielt danach das nächste Zeichen. Bei einer falschen
Antwort wird dasselbe Zeichen sofort wiederholt (statt zufällig weiterzumachen),
bis es richtig erkannt wird.

Zeitlimit (Instant Character Recognition): Wer nach dem Ton nicht innerhalb
des Limits tippt, hat das Zeichen verpasst. So bleibt keine Zeit, Punkte
und Striche zu zählen; das Zeichen muss als Reflex kommen. Das Limit passt
sich an: jede schnelle richtige Antwort macht es etwas kürzer, jeder Fehler
und jedes Verpassen etwas länger (nur beim ersten Hören eines Zeichens)."""
import time
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import audio, sfx
from morsetrainer.core.morse import (
    AUDIO_LATENCY, MORSE_CODE, SAMPLE_RATE, build_samples, code_units, duration_seconds, vary_voice,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.core.weighting import CharPicker

# Zeitlimit in Sekunden ab Tonende: Start, Grenzen und Faktoren pro Antwort.
ICR_START = 2.0
ICR_RANGE = (0.4, 3.0)
ICR_FASTER = 0.93
ICR_SLOWER = 1.15


def next_limit(limit: float, in_time_and_correct: bool) -> float:
    factor = ICR_FASTER if in_time_and_correct else ICR_SLOWER
    return round(min(max(limit * factor, ICR_RANGE[0]), ICR_RANGE[1]), 2)


class SingleModeFrame:
    uses_vary = True

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 vary_var=None):
        self.root = parent.winfo_toplevel()
        self.vary_var = vary_var
        self.voice = (15, 600)      # (WPM, Hz) des aktuellen Zeichens
        self.limit = ICR_START      # aktuelles Zeitlimit
        self.timeout_token = 0      # macht einen geplanten Timeout ungültig
        self.first_hearing = True   # Zeichen zum ersten Mal gehört (nicht wiederholt)
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
            controls, text="Wiederholen (Leertaste)", command=self.repeat_char, state="disabled"
        )
        self.repeat_button.pack(side="left", **pad)
        self.sound_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Quittungston", variable=self.sound_var).pack(side="left", **pad)

        icr = ttk.Frame(parent)
        icr.pack(fill="x", padx=8)
        self.icr_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            icr, text="Zeitlimit (wird kürzer, solange du sicher bist)", variable=self.icr_var,
            command=self._show_limit,
        ).pack(side="left", padx=(8, 0))
        self.limit_var = tk.StringVar(value="")
        ttk.Label(icr, textvariable=self.limit_var, foreground="gray40").pack(side="left", padx=(8, 0))
        ttk.Button(icr, text="zurücksetzen", command=self._reset_limit).pack(side="left", padx=(8, 0))
        self._show_limit()

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

    def _show_limit(self):
        self.limit_var.set(f"{self.limit:.2f} s".replace(".", ",") if self.icr_var.get() else "")

    def _reset_limit(self):
        self.limit = ICR_START
        self._show_limit()

    def settings(self) -> dict:
        return {"icr": self.icr_var.get(), "icr_limit": self.limit}

    def restore_settings(self, data: dict) -> None:
        if isinstance(data.get("icr"), bool):
            self.icr_var.set(data["icr"])
        limit = data.get("icr_limit")
        if isinstance(limit, (int, float)) and not isinstance(limit, bool) and ICR_RANGE[0] <= limit <= ICR_RANGE[1]:
            self.limit = float(limit)
        self._show_limit()

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
        self.timeout_token += 1
        self.start_button.config(text="Start")
        self.repeat_button.config(state="disabled")
        audio.stop()
        self._finalize_session()
        self.status_var.set("Gestoppt.")
        self.on_stop_cb()

    def _finalize_session(self):
        if self.session_stats is None:
            return
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None

    def on_close(self):
        self._finalize_session()

    def next_char(self):
        if not self.running:
            return
        self.waiting_for_input = False
        if not self.repeat_pending:
            self.current_char = self.picker.pick()
            self.voice = self._pick_voice()
        was_repeat = self.repeat_pending
        self.first_hearing = not was_repeat
        self.repeat_pending = False
        self.feedback_var.set("")
        self.status_var.set("Höre zu… (Wiederholung)" if was_repeat else "Höre zu…")
        self.play_current()

    def _pick_voice(self):
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
        if self.vary_var is not None and self.vary_var.get():
            wpm, freq = vary_voice(wpm, freq)
        return wpm, freq

    def play_current(self):
        self.timeout_token += 1
        wpm, freq = self.voice
        samples = build_samples(self.current_char, wpm, freq)
        # Hörbar wird der Ton erst nach der Ausgabelatenz; ab dann zählt die
        # Reaktionszeit, und erst danach ist er zu Ende.
        self.play_start_time = time.time() + AUDIO_LATENCY
        try:
            audio.play(samples)
        except audio.AudioError as exc:
            self.stop()
            self.status_var.set(str(exc))
            return
        dur_ms = int(duration_seconds(self.current_char, wpm) * 1000) + 150 + int(AUDIO_LATENCY * 1000)
        self.root.after(dur_ms, self.on_playback_done)

    def on_playback_done(self):
        if not self.running:
            return
        self.waiting_for_input = True
        self.status_var.set("Deine Eingabe?")
        if self.icr_var.get():
            # Das Limit zählt ab dem gleichen Zeitpunkt wie die Latenz.
            deadline = self.play_start_time + duration_seconds(self.current_char, self.voice[0]) + self.limit
            token = self.timeout_token
            self.root.after(max(int((deadline - time.time()) * 1000), 50), self._on_timeout, token)

    def _on_timeout(self, token):
        if not self.running or not self.waiting_for_input or token != self.timeout_token:
            return
        self.waiting_for_input = False
        wpm = self.voice[0]
        reaction_time = duration_seconds(self.current_char, wpm) + self.limit
        self.session_stats.record_char(
            self.current_char, "", False, reaction_time, code_units(self.current_char) * 1.2 / reaction_time
        )
        self.repeat_pending = True
        if self.first_hearing:
            self.limit = next_limit(self.limit, False)
            self._show_limit()
        if self.sound_var.get():
            sfx.play_error()
        self.feedback_var.set(f"Zu langsam: war {self.current_char}")
        self.feedback_label.config(foreground="red")
        self._add_history(False)
        self.root.after(700, self.next_char)

    def _add_history(self, correct: bool):
        self.history.append(correct)
        self.history = self.history[-40:]
        self.history_var.set("".join("✓" if ok else "✗" for ok in self.history))
        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

    def repeat_char(self):
        if self.running and self.current_char:
            self.first_hearing = False
            self.waiting_for_input = False
            self.status_var.set("Höre zu… (Wiederholung)")
            self.play_current()

    def on_key(self, event):
        if event.keysym == "space":
            self.repeat_char()
            return
        if not self.waiting_for_input:
            return
        typed = event.char.upper()
        if not typed or typed not in MORSE_CODE:
            return
        self.waiting_for_input = False
        self.timeout_token += 1
        correct = typed == self.current_char

        reaction_time = max(time.time() - self.play_start_time, 0.001)
        effective_wpm = code_units(self.current_char) * 1.2 / reaction_time
        latency = reaction_time - duration_seconds(self.current_char, self.voice[0])
        self.session_stats.record_char(
            self.current_char, typed, correct, reaction_time, effective_wpm, latency=latency
        )
        self.repeat_pending = not correct
        if self.icr_var.get() and self.first_hearing:
            self.limit = next_limit(self.limit, correct)
            self._show_limit()

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

        self._add_history(correct)
        self.root.after(700, self.next_char)