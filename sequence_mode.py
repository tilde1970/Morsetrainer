"""Gemeinsame Basis für Trainingsmodi, die eine ganze Zeichenkette am
Stück senden ("Gruppen", "Rufzeichen"): die komplette Sequenz wird
hintereinander abgespielt, per Entry + Enter als Ganzes eingegeben,
positionsweise verglichen, und bei einem Fehler wiederholt, bis sie
vollständig richtig eingegeben wurde. Optional mit fester Dauer: nach
Ablauf wird die laufende Sequenz noch beantwortet, dann automatisch
gestoppt.

Subklassen implementieren `_generate_sequence()` (was gesendet wird) und
können `_build_extra_settings()`, `_validate_settings()`, `_setup_pickers()`,
`_log_charset()` und `_session_group_len()` überschreiben."""
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd

import sfx
from morse import AUDIO_LATENCY, END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text, code_units
from stats import SessionStats
from stats_widget import StatsPanel


class SequenceModeFrame:
    session_mode = "group"
    intro_text = ""
    # "VVV =" vor der ersten und "+" nach der letzten Sequenz senden.
    send_prosigns = False

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
        self.waiting_for_input = False
        self.current_sequence = ""
        self.history = []
        self.session_stats = None
        self.play_start_time = 0.0
        self.repeat_pending = False
        self.deadline = None   # time.time(), ab der keine neue Sequenz mehr kommt
        self.session_id = 0    # damit ein alter Timer keine neue Sitzung anzeigt

        self._build_widgets(parent)

    # --- Überschreibbar durch Subklassen -------------------------------
    def _build_extra_settings(self, parent):
        pass

    def _validate_settings(self) -> bool:
        return True

    def _setup_pickers(self, weighted: bool):
        """Wird nach dem Anlegen von self.session_stats aufgerufen, um die
        (ggf. gewichteten) CharPicker für _generate_sequence() zu erzeugen."""
        pass

    def _generate_sequence(self) -> str:
        raise NotImplementedError

    def _log_charset(self) -> str:
        return self.charset_var.get().upper()

    def _session_group_len(self):
        return None

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        pad = {"padx": 8, "pady": 4}

        if self.intro_text:
            ttk.Label(parent, text=self.intro_text, wraplength=460, justify="left").pack(
                anchor="w", padx=8, pady=(4, 8)
            )

        self._build_extra_settings(parent)

        controls = ttk.Frame(parent)
        controls.pack(fill="x", **pad)
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.pack(side="left", **pad)
        self.repeat_button = ttk.Button(
            controls, text="Wiederholen", command=self.repeat_sequence, state="disabled"
        )
        self.repeat_button.pack(side="left", **pad)
        self.sound_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Quittungston", variable=self.sound_var).pack(side="left", **pad)

        duration = ttk.Frame(parent)
        duration.pack(fill="x", padx=8)
        ttk.Label(duration, text="Dauer:").pack(side="left", padx=(8, 4))
        self.duration_var = tk.IntVar(value=5)
        ttk.Spinbox(duration, from_=0, to=120, textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(duration, text="Min. (0 = ohne Limit)").pack(side="left", padx=(4, 0))
        self.remaining_var = tk.StringVar(value="")
        ttk.Label(duration, textvariable=self.remaining_var).pack(side="left", padx=(16, 0))

        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(parent, textvariable=self.status_var, font=("Sans", 14)).pack(pady=10)

        entry_frame = ttk.Frame(parent)
        entry_frame.pack(pady=4)
        ttk.Label(entry_frame, text="Eingabe (Enter bestätigt):").pack(side="left", padx=(0, 6))
        self.input_var = tk.StringVar(value="")
        self.entry = ttk.Entry(entry_frame, textvariable=self.input_var, width=20, state="disabled")
        self.entry.pack(side="left")
        self.entry.bind("<Return>", self.on_submit)

        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = ttk.Label(parent, textvariable=self.feedback_var, font=("Sans", 16, "bold"))
        self.feedback_label.pack(pady=10)

        self.stats_panel = StatsPanel(parent)

        ttk.Label(parent, text="Verlauf (letzte):").pack(anchor="w", padx=8)
        self.history_var = tk.StringVar(value="")
        ttk.Label(
            parent, textvariable=self.history_var, font=("Consolas", 11), wraplength=460
        ).pack(anchor="w", padx=8)

    # --- Ablauf -----------------------------------------------------------
    def toggle_running(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if not self._validate_settings():
            return
        try:
            minutes = self.duration_var.get()
        except tk.TclError:
            minutes = -1
        if minutes < 0:
            self.status_var.set("Ungültige Dauer!")
            return
        self.deadline = time.time() + minutes * 60 if minutes else None
        self.session_id += 1
        self.running = True
        self.repeat_pending = False
        self.start_button.config(text="Stop")
        self.repeat_button.config(state="normal")
        self.feedback_var.set("")
        self.session_stats = SessionStats(
            self.session_mode, self._log_charset(), self.wpm_var.get(), self.freq_var.get(),
            group_len=self._session_group_len(), farnsworth_wpm=self.farnsworth_wpm(),
        )
        self._setup_pickers(self.weighted_var.get())
        self.history = []
        self.history_var.set("")
        self.stats_panel.reset()
        self.on_start_cb()
        self._update_remaining(self.session_id)
        if self.send_prosigns:
            self._play_intro()
        else:
            self.next_sequence()

    def _play_intro(self):
        """Sendet START_TEXT plus Wortpause, danach die erste Sequenz.
        Wird nicht ausgewertet."""
        wpm, freq = self._audio_settings()
        samples = build_text(START_TEXT + " ", wpm, freq, self.farnsworth_wpm())
        self.status_var.set(f"Achtung: {START_TEXT}")
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
        dur_ms = int((len(samples) / SAMPLE_RATE + AUDIO_LATENCY) * 1000)
        self.root.after(dur_ms, self._after_intro, self.session_id)

    def _after_intro(self, session_id):
        if session_id == self.session_id:
            self.next_sequence()

    def stop(self):
        self.running = False
        self.waiting_for_input = False
        self.start_button.config(text="Start")
        self.repeat_button.config(state="disabled")
        self.entry.config(state="disabled")
        sd.stop()
        if self.send_prosigns:
            wpm, freq = self._audio_settings()
            sd.play(build_text(END_TEXT, wpm, freq), SAMPLE_RATE, latency=AUDIO_LATENCY)
        self._finalize_session()
        self.status_var.set("Gestoppt.")
        self.remaining_var.set("")
        self.on_stop_cb()

    def _time_up(self) -> bool:
        return self.deadline is not None and time.time() >= self.deadline

    def _update_remaining(self, session_id):
        if not self.running or session_id != self.session_id or self.deadline is None:
            return
        remaining = max(int(self.deadline - time.time()), 0)
        if remaining:
            self.remaining_var.set(f"Restzeit {remaining // 60}:{remaining % 60:02d}")
        else:
            self.remaining_var.set("Zeit abgelaufen – letzte Eingabe noch")
        self.root.after(1000, self._update_remaining, session_id)

    def _finalize_session(self):
        if self.session_stats is None:
            return
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path)
        self.session_stats = None

    def on_close(self):
        self._finalize_session()

    def next_sequence(self):
        if not self.running:
            return
        if self._time_up():
            self.stop()
            self.status_var.set("Zeit abgelaufen – Durchgang ausgewertet.")
            return
        self.waiting_for_input = False
        self.entry.config(state="disabled")
        if not self.repeat_pending:
            self.current_sequence = self._generate_sequence()
        was_repeat = self.repeat_pending
        self.repeat_pending = False
        self.feedback_var.set("")
        self.input_var.set("")
        self.status_var.set("Höre zu… (Wiederholung)" if was_repeat else "Höre zu…")
        self.play_current()

    def _audio_settings(self):
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
        return wpm, freq

    def play_current(self):
        wpm, freq = self._audio_settings()
        # Farnsworth streckt nur die Pausen zwischen den Zeichen; nach dem
        # letzten Zeichen bleibt die normale Pause, damit die Eingabe nicht
        # unnötig spät freigegeben wird.
        fw = self.farnsworth_wpm()
        last = len(self.current_sequence) - 1
        parts = [
            build_samples(ch, wpm, freq, fw if i < last else None)
            for i, ch in enumerate(self.current_sequence)
        ]
        samples = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        # Hörbar wird der Ton erst nach der Ausgabelatenz; ab dann zählt die
        # Reaktionszeit, und erst danach ist er zu Ende.
        self.play_start_time = time.time() + AUDIO_LATENCY
        sd.play(samples, SAMPLE_RATE, latency=AUDIO_LATENCY)
        dur_ms = int(len(samples) / SAMPLE_RATE * 1000) + 150 + int(AUDIO_LATENCY * 1000)
        self.root.after(dur_ms, self.on_playback_done)

    def on_playback_done(self):
        if not self.running:
            return
        self.waiting_for_input = True
        self.status_var.set("Deine Eingabe?")
        self.entry.config(state="normal")
        self.entry.focus_set()

    def repeat_sequence(self):
        if self.running and self.current_sequence:
            self.waiting_for_input = False
            self.entry.config(state="disabled")
            self.status_var.set("Höre zu… (Wiederholung)")
            self.play_current()

    def on_submit(self, event=None):
        if not self.waiting_for_input:
            return
        typed = "".join(ch for ch in self.input_var.get().upper() if ch in MORSE_CODE)
        self.waiting_for_input = False
        self.entry.config(state="disabled")

        sent = self.current_sequence
        elapsed = max(time.time() - self.play_start_time, 0.001)
        per_char_time = elapsed / max(len(sent), 1)

        all_correct = True
        for i, expected in enumerate(sent):
            got = typed[i] if i < len(typed) else ""
            correct = got == expected
            all_correct &= correct
            effective_wpm = code_units(expected) * 1.2 / per_char_time
            self.session_stats.record_char(expected, got, correct, per_char_time, effective_wpm)
        self.session_stats.record_group(sent, typed)
        self.repeat_pending = not all_correct

        if all_correct:
            if self.sound_var.get():
                sfx.play_ok()
            self.feedback_var.set(f"Richtig: {sent}")
            self.feedback_label.config(foreground="green")
        else:
            if self.sound_var.get():
                sfx.play_error()
            self.feedback_var.set(f"Falsch: war {sent}, du: {typed}")
            self.feedback_label.config(foreground="red")

        self.history.append(f"{sent}{'=' if all_correct else '≠'}{typed}")
        self.history = self.history[-10:]
        self.history_var.set("   ".join(self.history))

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

        self.root.after(900, self.next_sequence)

    def on_key(self, event):
        # Eingabe erfolgt über das Entry-Feld (self.entry), nicht über eine
        # globale Tastenbindung; hier gibt es nichts zu tun.
        pass