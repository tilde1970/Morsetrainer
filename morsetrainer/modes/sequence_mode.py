"""Gemeinsame Basis für Trainingsmodi, die eine ganze Zeichenkette am
Stück senden ("Gruppen", "Wörter", "Rufzeichen"): die komplette Sequenz
wird hintereinander abgespielt und als Ganzes beantwortet.

Drei Eingabearten:
- Mitschreiben (Standard): das Eingabefeld ist schon offen, während der Ton
  läuft, so wie man es vom Einzelzeichen gewohnt ist. Die Latenz jedes
  Zeichens (Tonende bis Tastendruck) wird einzeln gemessen.
- Erst merken: getippt wird erst nach dem Ton.
- Kopfhören: nichts tippen, nur im Kopf mitlesen, dann auflösen (Enter)
  und selbst bewerten (J = gewusst, N = nicht gewusst).

Ausgewertet wird per Alignment (core/align.py): ein ausgelassenes Zeichen
ist genau ein Fehler und verschiebt nicht alle folgenden. Die falschen
Stellen werden markiert. Bei einem Fehler kommt dieselbe Sequenz noch
einmal, nach der eingestellten Zahl an Fehlversuchen wird die Lösung
gezeigt und noch einmal vorgespielt, dann geht es weiter.

Wahlweise wächst das Tempo mit (wie bei RufzXP: richtig beim ersten
Versuch +1 WPM, jeder Fehlversuch −1 WPM), und es lassen sich
Bandbedingungen in drei Stufen unterlegen. Mit „Tonhöhe und Tempo
variieren“ (gemeinsame Einstellung) klingt jede Sequenz etwas anders.

Optional mit fester Dauer: nach Ablauf wird die laufende Sequenz noch
beantwortet, dann automatisch gestoppt.

Subklassen implementieren `_generate_sequence()` (was gesendet wird) und
können `_build_extra_settings()`, `_validate_settings()`, `_setup_pickers()`,
`_log_charset()`, `_session_group_len()`, `_after_result()`, `_explain()`,
`settings()` und `restore_settings()` überschreiben."""
import time
import tkinter as tk
from tkinter import ttk

import numpy as np

from morsetrainer.core import align, audio, band, sfx
from morsetrainer.core.morse import (
    AUDIO_LATENCY, END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text, char_gap_seconds,
    code_units, vary_voice,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets.stats_widget import StatsPanel

DEFAULT_GIVE_UP = 3

COPY, MEMORIZE, HEAD = "copy", "memorize", "head"
INPUT_STYLES = ((COPY, "Mitschreiben"), (MEMORIZE, "Erst merken"), (HEAD, "Kopfhören"))

# Mitwachsendes Tempo: Schritt und Grenzen in WPM.
TEMPO_STEP = 1
TEMPO_RANGE = (5, 60)

# Bandbedingungen: Beschriftung -> Stufe aus band.PRESETS (None = aus).
BAND_LABELS = {"aus": None, "leicht": "light", "mittel": "medium", "stark": "heavy"}


def clean_input(text: str) -> str:
    return "".join(ch for ch in text.upper() if ch in MORSE_CODE)


class SequenceModeFrame:
    session_mode = "group"
    intro_text = ""
    # "VVV =" vor der ersten und "+" nach der letzten Sequenz senden.
    send_prosigns = False
    # Ergebnis zählt für den Aufstieg in die nächste Koch-Lektion.
    koch_progress = False
    # Bekommt die gemeinsame Einstellung "Tonhöhe und Tempo variieren".
    uses_vary = True

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 vary_var=None):
        self.root = parent.winfo_toplevel()
        self.charset_var = charset_var
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.weighted_var = weighted_var
        self.farnsworth_wpm = farnsworth_wpm  # callable -> effektive WPM oder None
        self.vary_var = vary_var
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.style = COPY
        self.waiting_for_input = False  # Antwort wird angenommen
        self.input_open = False         # Eingabefeld nimmt Tasten an
        self.submit_pending = False     # Enter kam, während der Ton noch lief
        self.revealed = False           # Kopfhören: Lösung aufgedeckt, Bewertung steht aus
        self.current_sequence = ""
        self.voice = (15, 600)          # (WPM, Hz) der aktuellen Sequenz
        self.history = []
        self.session_stats = None
        self.play_start_time = 0.0
        self.tone_starts = []  # hörbarer Beginn jedes Zeichens (time.time())
        self.tone_ends = []    # hörbares Ende jedes Zeichens
        self.key_times = []    # Zeitpunkt jedes Zeichens im Eingabefeld
        self.typed_so_far = ""
        self.replayed = False  # Sequenz in diesem Versuch mehrfach gehört
        self.attempts = 0      # Versuche für die aktuelle Sequenz
        self.first_try_correct = 0
        self.first_try_total = 0
        self.koch_result = None  # (Zeichensatz, richtig, gesamt) des letzten Durchgangs
        self.tempo = None        # mitwachsendes Tempo, None = aus
        self.tempo_best = None   # höchstes Tempo mit einer beim ersten Versuch richtigen Sequenz
        self.band = None         # BandConditions, None = ohne Störungen
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

    def _after_result(self, correct: bool, attempts: int):
        """Nach jeder Auswertung; `attempts` zählt die Versuche für diese
        Sequenz einschließlich des aktuellen."""
        pass

    def _explain(self, sequence: str) -> str:
        """Zusatz zur Rückmeldung, z. B. die Bedeutung einer Abkürzung."""
        return ""

    def settings(self) -> dict:
        """Einstellungen zum Speichern in window_state.json."""
        data = {
            "input_style": self.style_var.get(),
            "adaptive_tempo": self.tempo_var.get(),
            "band": BAND_LABELS.get(self.band_var.get()),
        }
        for key, var in (("duration", self.duration_var), ("give_up", self.give_up_var)):
            try:
                data[key] = var.get()
            except tk.TclError:
                pass
        return data

    def restore_settings(self, data: dict) -> None:
        """Gegenstück zu settings(); unbekannte oder kaputte Werte werden
        ignoriert."""
        if data.get("input_style") in dict(INPUT_STYLES):
            self.style_var.set(data["input_style"])
        if isinstance(data.get("adaptive_tempo"), bool):
            self.tempo_var.set(data["adaptive_tempo"])
        for label, preset in BAND_LABELS.items():
            if data.get("band") == preset:
                self.band_var.set(label)
        for key, var, limits in (("duration", self.duration_var, (0, 120)), ("give_up", self.give_up_var, (0, 9))):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        pad = {"padx": 8, "pady": 4}

        if self.intro_text:
            ttk.Label(parent, text=self.intro_text, wraplength=460, justify="left").pack(
                anchor="w", padx=8, pady=(4, 8)
            )

        self._build_extra_settings(parent)

        style = ttk.Frame(parent)
        style.pack(fill="x", padx=8)
        ttk.Label(style, text="Eingabe:").pack(side="left", padx=(8, 4))
        self.style_var = tk.StringVar(value=COPY)
        for value, label in INPUT_STYLES:
            ttk.Radiobutton(style, text=label, value=value, variable=self.style_var).pack(side="left", padx=(0, 8))

        give_up = ttk.Frame(parent)
        give_up.pack(fill="x", padx=8)
        ttk.Label(give_up, text="Lösung zeigen nach").pack(side="left", padx=(8, 4))
        self.give_up_var = tk.IntVar(value=DEFAULT_GIVE_UP)
        ttk.Spinbox(give_up, from_=0, to=9, textvariable=self.give_up_var, width=3).pack(side="left")
        ttk.Label(give_up, text="Fehlversuchen (0 = nie)").pack(side="left", padx=(4, 0))

        tempo = ttk.Frame(parent)
        tempo.pack(fill="x", padx=8)
        self.tempo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            tempo, text=f"Tempo wächst mit (richtig +{TEMPO_STEP}, falsch −{TEMPO_STEP} WPM)",
            variable=self.tempo_var,
        ).pack(side="left", padx=(8, 0))
        self.tempo_info_var = tk.StringVar(value="")
        ttk.Label(tempo, textvariable=self.tempo_info_var, foreground="gray40").pack(side="left", padx=(8, 0))

        band_row = ttk.Frame(parent)
        band_row.pack(fill="x", padx=8)
        ttk.Label(band_row, text="Bandbedingungen:").pack(side="left", padx=(8, 4))
        self.band_var = tk.StringVar(value="aus")
        ttk.Combobox(band_row, textvariable=self.band_var, values=list(BAND_LABELS), state="readonly",
                     width=8).pack(side="left")
        ttk.Label(band_row, text="(Rauschen, QSB, Knacken, QRM)", foreground="gray40").pack(side="left", padx=(6, 0))

        controls = ttk.Frame(parent)
        controls.pack(fill="x", **pad)
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.pack(side="left", **pad)
        self.repeat_button = ttk.Button(
            controls, text="Wiederholen (Leertaste)", command=self.repeat_sequence, state="disabled"
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

        # Eingabezeile; beim Kopfhören stattdessen die Knöpfe zum Auflösen
        # und Bewerten (siehe _show_answer_row).
        self.answer_area = ttk.Frame(parent)
        self.answer_area.pack(pady=4)
        self.entry_frame = ttk.Frame(self.answer_area)
        self.entry_frame.pack()
        ttk.Label(self.entry_frame, text="Eingabe (Enter bestätigt):").pack(side="left", padx=(0, 6))
        self.input_var = tk.StringVar(value="")
        self.input_var.trace_add("write", self._on_input_change)
        self.entry = ttk.Entry(self.entry_frame, textvariable=self.input_var, width=20, state="disabled")
        self.entry.pack(side="left")
        self.entry.bind("<Return>", self.on_submit)
        # Ein Leerzeichen gehört nie zur Antwort, die Leertaste wiederholt.
        self.entry.bind("<space>", lambda e: (self.repeat_sequence(), "break")[1])

        self.head_frame = ttk.Frame(self.answer_area)
        self.reveal_button = ttk.Button(self.head_frame, text="Auflösen (Enter)", command=self.reveal,
                                        state="disabled")
        self.reveal_button.pack(side="left", padx=4)
        self.known_button = ttk.Button(self.head_frame, text="Gewusst (J)", command=lambda: self.assess(True),
                                       state="disabled")
        self.known_button.pack(side="left", padx=4)
        self.unknown_button = ttk.Button(self.head_frame, text="Nicht gewusst (N)",
                                         command=lambda: self.assess(False), state="disabled")
        self.unknown_button.pack(side="left", padx=4)

        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = ttk.Label(
            parent, textvariable=self.feedback_var, font=("Sans", 16, "bold"), wraplength=460, justify="center"
        )
        self.feedback_label.pack(pady=(10, 2))
        # Gesendet / getippt / Markierung untereinander, daher Festbreitenschrift.
        self.diff_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.diff_var, font=("Consolas", 13), justify="left").pack(pady=(0, 8))

        self.stats_panel = StatsPanel(parent)

        ttk.Label(parent, text="Verlauf (letzte):").pack(anchor="w", padx=8)
        self.history_var = tk.StringVar(value="")
        ttk.Label(
            parent, textvariable=self.history_var, font=("Consolas", 11), wraplength=460
        ).pack(anchor="w", padx=8)

    def _show_answer_row(self):
        if self.style == HEAD:
            self.entry_frame.pack_forget()
            self.head_frame.pack()
        else:
            self.head_frame.pack_forget()
            self.entry_frame.pack()

    def _set_head_buttons(self, reveal=False, assess=False):
        self.reveal_button.config(state="normal" if reveal else "disabled")
        for button in (self.known_button, self.unknown_button):
            button.config(state="normal" if assess else "disabled")

    # --- Ablauf -----------------------------------------------------------
    def _later(self, ms: int, callback, *args):
        """root.after, das nach Stop oder Neustart nicht mehr feuert."""
        session_id = self.session_id

        def run():
            if self.running and session_id == self.session_id:
                callback(*args)
        self.root.after(ms, run)

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
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except tk.TclError:
            self.status_var.set("Ungültige Dauer, Geschwindigkeit oder Tonhöhe!")
            return
        if minutes < 0:
            self.status_var.set("Ungültige Dauer!")
            return
        self.deadline = time.time() + minutes * 60 if minutes else None
        self.session_id += 1
        self.running = True
        self.style = self.style_var.get()
        self._show_answer_row()
        self.repeat_pending = False
        self.revealed = False
        self.first_try_correct = self.first_try_total = 0
        self.koch_result = None
        self.tempo = wpm if self.tempo_var.get() else None
        self.tempo_best = None
        self._show_tempo()
        preset = BAND_LABELS.get(self.band_var.get())
        self.band = band.preset_conditions(preset, freq) if preset else None
        self.start_button.config(text="Stop")
        self.repeat_button.config(state="normal")
        self.feedback_var.set("")
        self.diff_var.set("")
        self.session_stats = SessionStats(
            self.session_mode, self._log_charset(), wpm, freq,
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
        if not self._play(samples):
            return
        dur_ms = int((len(samples) / SAMPLE_RATE + AUDIO_LATENCY) * 1000)
        self._later(dur_ms, self.next_sequence)

    def stop(self):
        self.running = False
        self.waiting_for_input = False
        self.submit_pending = False
        self.start_button.config(text="Start")
        self.repeat_button.config(state="disabled")
        self._set_input_open(False)
        self._set_head_buttons()
        audio.stop()
        if self.send_prosigns:
            wpm, freq = self._audio_settings()
            audio.play_quietly(build_text(END_TEXT, wpm, freq))
        self._finalize_session()
        self.status_var.set("Gestoppt.")
        self.remaining_var.set("")
        if self.tempo is not None:
            best = f"{self.tempo_best} WPM" if self.tempo_best else "–"
            self.tempo_info_var.set(f"Bestwert {best}, zuletzt {self.tempo} WPM")
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
        if self.koch_progress and self.first_try_total:
            self.koch_result = (getattr(self, "charset", ""), self.first_try_correct, self.first_try_total)
        extra = {}
        if self.tempo is not None:
            extra = {"wpm_reached": self.tempo_best, "wpm_end": self.tempo}
        path = self.session_stats.finalize(extra)
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None

    def on_close(self):
        self._finalize_session()

    def _set_input_open(self, is_open: bool):
        self.input_open = is_open
        self.entry.config(state="normal" if is_open else "disabled")
        if is_open:
            self.entry.focus_set()

    def _on_input_change(self, *_):
        """Merkt sich, wann jedes Zeichen im Eingabefeld dazukam. Bei
        Korrekturen behalten die unveränderten Zeichen davor ihre Zeit."""
        typed = clean_input(self.input_var.get())
        keep = 0
        while keep < min(len(typed), len(self.typed_so_far)) and typed[keep] == self.typed_so_far[keep]:
            keep += 1
        now = time.time()
        self.key_times = self.key_times[:keep] + [now] * (len(typed) - keep)
        self.typed_so_far = typed

    def next_sequence(self):
        if not self.running:
            return
        if self._time_up():
            self.stop()
            self.status_var.set("Zeit abgelaufen – Durchgang ausgewertet.")
            return
        self.waiting_for_input = False
        self.submit_pending = False
        self.revealed = False
        was_repeat = self.repeat_pending
        if not was_repeat:
            self.current_sequence = self._generate_sequence()
            self.attempts = 0
            self.voice = self._pick_voice()
            # Bei einer Wiederholung bleibt die Markierung der Fehler stehen.
            self.feedback_var.set("")
            self.diff_var.set("")
        self.repeat_pending = False
        self.replayed = False
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

    def _pick_voice(self):
        """Tempo und Tonhöhe für eine neue Sequenz; Wiederholungen behalten sie."""
        wpm, freq = self._audio_settings()
        if self.tempo is not None:
            wpm = self.tempo
        if self.vary_var is not None and self.vary_var.get():
            wpm, freq = vary_voice(wpm, freq)
        return wpm, freq

    def _show_tempo(self):
        self.tempo_info_var.set(f"aktuell {self.tempo} WPM" if self.tempo is not None else "")

    def _update_tempo(self, correct: bool, attempts: int):
        if self.tempo is None:
            return
        if correct and attempts == 1:
            self.tempo_best = max(self.tempo_best or 0, self.tempo)
            self.tempo = min(self.tempo + TEMPO_STEP, TEMPO_RANGE[1])
        elif not correct:
            self.tempo = max(self.tempo - TEMPO_STEP, TEMPO_RANGE[0])
        self._show_tempo()

    def play_current(self, listen_only=False, on_done=None):
        """Spielt die aktuelle Sequenz. Beim Mitschreiben ist die Eingabe
        dabei schon offen, außer bei `listen_only` (Lösung vorspielen)."""
        wpm, freq = self.voice
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
        lead = 0.0
        if self.band is not None:
            samples, lead = band.apply_preset(self.band, samples)
        # Hörbar wird der Ton erst nach der Ausgabelatenz; ab dann zählt die
        # Reaktionszeit, und erst danach ist er zu Ende.
        self.play_start_time = time.time() + AUDIO_LATENCY
        self.tone_starts, self.tone_ends = [], []
        offset = self.play_start_time + lead
        for i, part in enumerate(parts):
            self.tone_starts.append(offset)
            offset += len(part) / SAMPLE_RATE
            self.tone_ends.append(offset - char_gap_seconds(wpm, fw if i < last else None))
        if not self._play(samples):
            return
        self._set_input_open(self.style == COPY and not listen_only)
        if self.style == HEAD:
            # Tasten (Enter, J, N) sollen beim Fenster ankommen, nicht im Eingabefeld.
            self.root.focus_set()
            self._set_head_buttons()
        dur_ms = int(len(samples) / SAMPLE_RATE * 1000) + 150 + int(AUDIO_LATENCY * 1000)
        self._later(dur_ms, on_done or self.on_playback_done)

    def _play(self, samples) -> bool:
        """Spielt `samples`; scheitert die Tonausgabe, endet der Durchgang
        mit der Fehlermeldung."""
        try:
            audio.play(samples)
        except audio.AudioError as exc:
            self.stop()
            self.status_var.set(str(exc))
            return False
        return True

    def on_playback_done(self):
        self.waiting_for_input = True
        if self.style == HEAD:
            # Nach dem Auflösen noch einmal gehört: weiter mit der Bewertung.
            self._set_head_buttons(reveal=not self.revealed, assess=self.revealed)
            self.status_var.set("Gewusst? J oder N" if self.revealed else "Erkannt? Enter löst auf.")
            return
        self._set_input_open(True)
        if self.submit_pending:
            self.submit_pending = False
            self.on_submit()
        else:
            self.status_var.set("Deine Eingabe?")

    def repeat_sequence(self):
        # Während die Lösung vorgespielt wird oder die Rückmeldung steht, ist
        # die Eingabe zu; dann gibt es auch nichts zu wiederholen.
        if self.running and self.current_sequence and (self.input_open or self.waiting_for_input):
            self.waiting_for_input = False
            self.submit_pending = False
            self.replayed = True
            self.status_var.set("Höre zu… (Wiederholung)")
            self.play_current()

    def _char_timing(self, index: int, typed_index):
        """(Reaktionszeit, Latenz oder None) für das gesendete Zeichen an
        `index`. Die Latenz ist nur beim Mitschreiben ohne Wiederholung
        eindeutig; sonst wird die Gesamtzeit gleichmäßig verteilt."""
        if (
            typed_index is not None and self.style == COPY and not self.replayed
            and typed_index < len(self.key_times)
        ):
            key_time = self.key_times[typed_index]
            latency = key_time - self.tone_ends[index]
            if latency >= 0:
                return key_time - self.tone_starts[index], latency
        elapsed = max(time.time() - self.play_start_time, 0.001)
        return elapsed / max(len(self.current_sequence), 1), None

    def on_submit(self, event=None):
        if not self.running or self.style == HEAD:
            return
        if not self.waiting_for_input:
            if self.input_open:
                # Beim Mitschreiben vorzeitig Enter gedrückt: nach dem Ton werten.
                self.submit_pending = True
                self.status_var.set("Wird nach dem Ton ausgewertet…")
            return
        typed = clean_input(self.input_var.get())
        self.waiting_for_input = False
        self._set_input_open(False)

        sent = self.current_sequence
        results = align.char_results(sent, typed)
        for index, (expected, got, typed_index) in enumerate(results):
            reaction_time, latency = self._char_timing(index, typed_index)
            effective_wpm = code_units(expected) * 1.2 / max(reaction_time, 0.001)
            self.session_stats.record_char(
                expected, got, got == expected, reaction_time, effective_wpm, latency=latency
            )
        correct_chars = sum(1 for expected, got, _ in results if got == expected)
        self._finish_attempt(typed, typed == sent, correct_chars)

    def reveal(self):
        """Kopfhören: Lösung aufdecken, danach bewerten."""
        if not self.running or self.style != HEAD or not self.waiting_for_input or self.revealed:
            return
        self.revealed = True
        explanation = self._explain(self.current_sequence)
        self.feedback_var.set(self.current_sequence + (f"\n{explanation}" if explanation else ""))
        self.feedback_label.config(foreground="")
        self.status_var.set("Gewusst? J oder N")
        self._set_head_buttons(assess=True)

    def assess(self, known: bool):
        """Kopfhören: eigene Bewertung. Nicht gewusst zählt jedes Zeichen als
        verpasst (es gibt keine Eingabe, die zeigen würde, welches)."""
        if not self.running or not self.revealed:
            return
        self.revealed = False
        self.waiting_for_input = False
        self._set_head_buttons()
        sent = self.current_sequence
        reaction_time = max(time.time() - self.play_start_time, 0.001) / max(len(sent), 1)
        for ch in sent:
            self.session_stats.record_char(
                ch, ch if known else "", known, reaction_time, code_units(ch) * 1.2 / reaction_time
            )
        self._finish_attempt(sent if known else "", known, len(sent) if known else 0, head=True)

    def _finish_attempt(self, typed: str, all_correct: bool, correct_chars: int, head=False):
        """Gemeinsamer Abschluss eines Versuchs: Statistik, Anpassungen,
        Rückmeldung und was als Nächstes kommt."""
        sent = self.current_sequence
        self.session_stats.record_group(sent, typed, wpm=self.voice[0] if self.tempo is not None else None)
        self.attempts += 1
        if self.attempts == 1:
            self.first_try_total += len(sent)
            self.first_try_correct += correct_chars
        try:
            give_up_after = self.give_up_var.get()
        except tk.TclError:
            give_up_after = DEFAULT_GIVE_UP
        # Beim Kopfhören gibt es keinen zweiten Versuch: die Lösung ist schon zu sehen.
        give_up = not all_correct and (head or 0 < give_up_after <= self.attempts)
        self.repeat_pending = not all_correct and not give_up
        self._after_result(all_correct, self.attempts)
        self._update_tempo(all_correct, self.attempts)

        explanation = self._explain(sent)
        if all_correct:
            if self.sound_var.get():
                sfx.play_ok()
            self.feedback_var.set(f"Richtig: {sent}" + (f"\n{explanation}" if explanation else ""))
            self.feedback_label.config(foreground="green")
            self.diff_var.set("")
        else:
            if self.sound_var.get():
                sfx.play_error()
            if give_up:
                text = f"Lösung: {sent}" + (f"\n{explanation}" if explanation else "")
            else:
                text = "Leider falsch – hör noch einmal hin."
            self.feedback_var.set(text)
            self.feedback_label.config(foreground="red")
            if not head:
                sent_row, typed_row, marks = align.diff_rows(sent, typed)
                self.diff_var.set(f"gesendet  {sent_row}\ngetippt   {typed_row}\n          {marks}")

        self.history.append(f"{sent}{'=' if all_correct else '≠'}{typed}")
        self.history = self.history[-10:]
        self.history_var.set("   ".join(self.history))

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

        if give_up:
            # Lösung sehen und dabei noch einmal hören, dann weiter.
            self.status_var.set("Hör dir die Lösung noch einmal an…")
            self._later(900, self.play_current, True, lambda: self._later(900, self.next_sequence))
        else:
            self._later(900 if all_correct else 1500, self.next_sequence)

    def on_key(self, event):
        # Eingabe erfolgt über das Entry-Feld (self.entry), nicht über eine
        # globale Tastenbindung; nur die Leertaste wirkt auch außerhalb, beim
        # Kopfhören außerdem Enter, J und N.
        if event.keysym == "space":
            self.repeat_sequence()
        elif self.style == HEAD and self.running:
            key = event.keysym.lower()
            if key in ("return", "kp_enter"):
                self.reveal()
            elif key == "j":
                self.assess(True)
            elif key == "n":
                self.assess(False)
