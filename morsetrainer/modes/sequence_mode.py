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
Stellen werden markiert, die gesendete Sequenz aber erst beim Aufgeben
gezeigt: Bei einem Fehler kommt dieselbe Sequenz noch einmal, und dann
soll sie gehört, nicht abgeschrieben werden. Nach der eingestellten Zahl
an Fehlversuchen wird die Lösung gezeigt und noch einmal vorgespielt.

Ehrliche Messwerte: In die Zeichenstatistik (und damit Gewichtung und
Gesamtstatistik) geht nur der erste Versuch ein. Für den Koch-Aufstieg
zählt ein erster Versuch nur, wenn die Sequenz nicht wiederholt wurde
(Leertaste) und die Antwort innerhalb des Zeitfensters kam (answer_limit);
zu viel Getipptes zählt als Fehler. Kopfhören beruht auf Selbstbewertung
und zählt weder für den Aufstieg noch für die Gesamtstatistik.

Wahlweise wächst das Tempo mit (wie bei RufzXP): richtig beim ersten
Versuch +1 WPM, falsch beim ersten Versuch −1 WPM, angewandt auf das
effektive Tempo nach der gemeinsamen Regel in core/tempo.py (erst die
Pausen, die Zeichen bleiben schnell). Es
lassen sich Bandbedingungen in drei Stufen unterlegen. Mit „Tonhöhe und Tempo
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

from morsetrainer.core import align, audio, band, sfx, tempo
from morsetrainer.core.morse import (
    AUDIO_LATENCY, END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text, char_gap_seconds,
    code_units, display_text, vary_voice,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets import theme
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ScrollableFrame

DEFAULT_GIVE_UP = 3

COPY, MEMORIZE, HEAD = "copy", "memorize", "head"
INPUT_STYLES = ((COPY, "Mitschreiben"), (MEMORIZE, "Erst merken"), (HEAD, "Kopfhören"))

# Mitwachsendes Tempo: Schritt in WPM (Regel siehe core/tempo.py).
TEMPO_STEP = 1

# Zeitfenster für eine Antwort, die für den Koch-Aufstieg zählt: ab dem
# Ende des Tons so viele Sekunden plus je Zeichen der Sequenz.
ANSWER_BASE_S = 1.5
ANSWER_PER_CHAR_S = 0.6


def answer_limit(length: int) -> float:
    """Sekunden nach Tonende, in denen eine Antwort als flüssig gilt."""
    return ANSWER_BASE_S + ANSWER_PER_CHAR_S * length

# Bandbedingungen: Beschriftung -> Stufe aus band.PRESETS (None = aus).
BAND_LABELS = {"aus": None, "leicht": "light", "mittel": "medium", "stark": "heavy"}
# Lautstärke der Störgeräusche gegenüber den Zeichen, in Prozent.
BAND_GAIN_RANGE = (10, 150)


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
        self.enter_time = None  # Enter schon während des Tons gedrückt (time.time())
        self.tempo_fw = None     # effektives Tempo beim mitwachsenden Tempo (Farnsworth), None = aus
        self.attempts = 0      # Versuche für die aktuelle Sequenz
        self.first_try_correct = 0
        self.first_try_total = 0
        self.koch_result = None  # (Zeichensatz, richtig, gesamt) des letzten Durchgangs
        self.tempo = None        # mitwachsendes Zeichentempo, None = aus
        self.tempo_best = None   # höchstes effektives Tempo mit einer beim ersten Versuch richtigen Sequenz
        self.band = None         # BandConditions, None = ohne Störungen
        self.repeat_pending = False
        self.deadline = None   # time.time(), ab der keine neue Sequenz mehr kommt
        self.session_id = 0    # damit ein alter Timer keine neue Sitzung anzeigt

        self._build_widgets(ScrollableFrame(parent).inner)

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

    def _fixed_run(self) -> bool:
        """True für einen festen Durchgang (z. B. Rufz): ein Versuch je
        Sequenz, kein Wiederholen, Tempo wächst immer mit, keine Dauer,
        Lösung nur anzeigen statt nochmal vorspielen."""
        return False

    def _run_complete(self) -> bool:
        """Fester Durchgang zu Ende (vor der nächsten Sequenz geprüft)."""
        return False

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
            "band_gain": round(self.band_gain_var.get()),
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
        for key, var, limits in (("duration", self.duration_var, (0, 120)), ("give_up", self.give_up_var, (0, 9)),
                                 ("band_gain", self.band_gain_var, BAND_GAIN_RANGE)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)
        self._show_band_gain()

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        if self.intro_text:
            theme.hint(parent, text=self.intro_text, wrap=560).pack(anchor="w", padx=10, pady=(8, 2))

        options = theme.card(parent, "Einstellungen")
        self._build_extra_settings(options)

        style = ttk.Frame(options)
        style.pack(fill="x", pady=1)
        ttk.Label(style, text="Eingabe:").pack(side="left", padx=(0, 6))
        self.style_var = tk.StringVar(value=COPY)
        for value, label in INPUT_STYLES:
            ttk.Radiobutton(style, text=label, value=value, variable=self.style_var).pack(side="left", padx=(0, 10))

        give_up = ttk.Frame(options)
        give_up.pack(fill="x", pady=1)
        ttk.Label(give_up, text="Lösung zeigen nach").pack(side="left", padx=(0, 4))
        self.give_up_var = tk.IntVar(value=DEFAULT_GIVE_UP)
        ttk.Spinbox(give_up, from_=0, to=9, textvariable=self.give_up_var, width=3).pack(side="left")
        ttk.Label(give_up, text="Fehlversuchen").pack(side="left", padx=(4, 0))
        theme.hint(give_up, text="(0 = nie)").pack(side="left", padx=(4, 0))

        tempo_row = ttk.Frame(options)
        tempo_row.pack(fill="x", pady=1)
        self.tempo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            tempo_row, text=f"Tempo wächst mit (richtig +{TEMPO_STEP}, falsch −{TEMPO_STEP} WPM)",
            variable=self.tempo_var,
        ).pack(side="left")
        self.tempo_info_var = tk.StringVar(value="")
        theme.hint(tempo_row, textvariable=self.tempo_info_var).pack(side="left", padx=(8, 0))

        band_row = ttk.Frame(options)
        band_row.pack(fill="x", pady=1)
        ttk.Label(band_row, text="Bandbedingungen:").pack(side="left", padx=(0, 4))
        self.band_var = tk.StringVar(value="aus")
        ttk.Combobox(band_row, textvariable=self.band_var, values=list(BAND_LABELS), state="readonly",
                     width=8).pack(side="left")
        theme.hint(band_row, text="(Rauschen, QSB, Knacken, QRM)").pack(side="left", padx=(6, 0))

        gain_row = ttk.Frame(options)
        gain_row.pack(fill="x", pady=1)
        ttk.Label(gain_row, text="Störgeräusche:").pack(side="left", padx=(0, 4))
        theme.hint(gain_row, text="leiser").pack(side="left")
        self.band_gain_var = tk.DoubleVar(value=100)
        self.band_gain_scale = ttk.Scale(
            gain_row, from_=BAND_GAIN_RANGE[0], to=BAND_GAIN_RANGE[1], variable=self.band_gain_var, length=180,
            command=lambda _: self._show_band_gain(),
        )
        self.band_gain_scale.pack(side="left", padx=6)
        theme.hint(gain_row, text="lauter").pack(side="left")
        self.band_gain_text = tk.StringVar(value="")
        self.band_gain_label = ttk.Label(gain_row, textvariable=self.band_gain_text, width=6, anchor="e")
        self.band_gain_label.pack(side="left", padx=(6, 0))
        self.band_var.trace_add("write", lambda *_: self._show_band_gain())
        self._show_band_gain()

        duration = ttk.Frame(options)
        duration.pack(fill="x", pady=1)
        ttk.Label(duration, text="Dauer:").pack(side="left", padx=(0, 4))
        self.duration_var = tk.IntVar(value=5)
        ttk.Spinbox(duration, from_=0, to=120, textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(duration, text="Min.").pack(side="left", padx=(4, 0))
        theme.hint(duration, text="(0 = ohne Limit)").pack(side="left", padx=(4, 0))
        self.sound_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(duration, text="Quittungston", variable=self.sound_var).pack(side="right")

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text="Start", style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")
        self.repeat_button = ttk.Button(
            controls, text="Wiederholen (Leertaste)", command=self.repeat_sequence, state="disabled"
        )
        self.repeat_button.pack(side="left", padx=8)
        self.remaining_var = tk.StringVar(value="")
        theme.hint(controls, textvariable=self.remaining_var).pack(side="right")

        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel", wraplength=560,
                  justify="center").pack(pady=(14, 6))

        # Eingabezeile; beim Kopfhören stattdessen die Knöpfe zum Auflösen
        # und Bewerten (siehe _show_answer_row).
        self.answer_area = ttk.Frame(parent)
        self.answer_area.pack(pady=4)
        self.entry_frame = ttk.Frame(self.answer_area)
        self.entry_frame.pack()
        self.input_var = tk.StringVar(value="")
        self.input_var.trace_add("write", self._on_input_change)
        self.entry = ttk.Entry(self.entry_frame, textvariable=self.input_var, width=18, state="disabled",
                               font=theme.MONO_LARGE, justify="center")
        self.entry.pack()
        self.entry.bind("<Return>", self.on_submit)
        # Ein Leerzeichen gehört nie zur Antwort, die Leertaste wiederholt.
        self.entry.bind("<space>", lambda e: (self.repeat_sequence(), "break")[1])
        theme.hint(self.entry_frame, text="Enter bestätigt").pack(pady=(2, 0))

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
            parent, textvariable=self.feedback_var, style="Feedback.TLabel", wraplength=560, justify="center"
        )
        self.feedback_label.pack(pady=(10, 2))
        # Gesendet / getippt / Markierung untereinander, daher Festbreitenschrift.
        self.diff_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.diff_var, font=theme.MONO_LARGE, justify="left").pack(pady=(0, 8))

        self.stats_panel = StatsPanel(parent)

        history = theme.card(parent, "Verlauf")
        self.history_var = tk.StringVar(value="")
        ttk.Label(history, textvariable=self.history_var, font=theme.MONO, wraplength=540).pack(anchor="w")

    def _show_band_gain(self):
        """Prozentanzeige; ohne Bandbedingungen ist der Regler gesperrt."""
        self.band_gain_text.set(f"{round(self.band_gain_var.get())} %")
        active = BAND_LABELS.get(self.band_var.get()) is not None
        self.band_gain_scale.state(["!disabled"] if active else ["disabled"])
        self.band_gain_label.config(foreground="" if active else theme.DISABLED)

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
        self.deadline = time.time() + minutes * 60 if minutes and not self._fixed_run() else None
        self.session_id += 1
        self.running = True
        self.style = self.style_var.get()
        self._show_answer_row()
        self.repeat_pending = False
        self.revealed = False
        self.first_try_correct = self.first_try_total = 0
        self.koch_result = None
        self.tempo, self.tempo_fw = None, None
        if self.tempo_var.get() or self._fixed_run():
            self.tempo, self.tempo_fw = wpm, self.farnsworth_wpm()
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
            self_assessed=self.style == HEAD, in_history=not self._fixed_run(),
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
            best = f"{self.tempo_best} WPM effektiv" if self.tempo_best else "–"
            self.tempo_info_var.set(f"Bestwert {best}, zuletzt {tempo.label(self.tempo, self.tempo_fw)}")
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
        if self.koch_progress and self.first_try_total and not self.session_stats.self_assessed:
            self.koch_result = (getattr(self, "charset", ""), self.first_try_correct, self.first_try_total)
        extra = {}
        if self.tempo is not None:
            extra = {"wpm_effective_reached": self.tempo_best,
                     "wpm_effective_end": tempo.effective(self.tempo, self.tempo_fw)}
        path = self.session_stats.finalize(extra)
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        if self.session_stats.self_assessed and path is not None:
            self.stats_panel.save_var.set(
                self.stats_panel.save_var.get() + " – selbst bewertet, zählt nicht für Gesamtstatistik und Lektion"
            )
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
        if self._run_complete():
            self.stop()
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
        self.enter_time = None
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
        if self.tempo is None:
            self.tempo_info_var.set("")
        else:
            self.tempo_info_var.set(f"aktuell {tempo.label(self.tempo, self.tempo_fw)}")

    def _update_tempo(self, correct: bool, attempts: int):
        """Nur der erste Versuch zählt: ein Fehler bei der Wiederholung
        derselben Sequenz bremst nicht noch einmal."""
        if self.tempo is None or attempts != 1:
            return
        if correct:
            self.tempo_best = max(self.tempo_best or 0, tempo.effective(self.tempo, self.tempo_fw))
        self.tempo, self.tempo_fw = tempo.step(self.tempo, self.tempo_fw, TEMPO_STEP if correct else -TEMPO_STEP)
        self._show_tempo()

    def _farnsworth(self):
        """Effektives Tempo für die Pausen: beim mitwachsenden Tempo dessen
        eigenes (solange langsamer als die Zeichen), sonst die gemeinsame
        Einstellung."""
        if self.tempo is not None:
            fw = self.tempo_fw
            return fw if fw is not None and fw < self.voice[0] else None
        return self.farnsworth_wpm()

    def play_current(self, listen_only=False, on_done=None):
        """Spielt die aktuelle Sequenz. Beim Mitschreiben ist die Eingabe
        dabei schon offen, außer bei `listen_only` (Lösung vorspielen)."""
        wpm, freq = self.voice
        # Farnsworth streckt nur die Pausen zwischen den Zeichen; nach dem
        # letzten Zeichen bleibt die normale Pause, damit die Eingabe nicht
        # unnötig spät freigegeben wird.
        fw = self._farnsworth()
        last = len(self.current_sequence) - 1
        parts = [
            build_samples(ch, wpm, freq, fw if i < last else None)
            for i, ch in enumerate(self.current_sequence)
        ]
        samples = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        lead = 0.0
        if self.band is not None:
            # Der Regler gilt auch mitten im Durchgang ab der nächsten Sequenz.
            self.band.background_gain = self.band_gain_var.get() / 100
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
        elif self.koch_progress and self.attempts == 0 and not self.replayed:
            # Für die Lektion zählt nur eine zügige Antwort; das soll man wissen.
            limit = f"{answer_limit(len(self.current_sequence)):.1f}".replace(".", ",")
            self.status_var.set(f"Deine Eingabe? (für die Lektion zügig: {limit} s)")
        else:
            self.status_var.set("Deine Eingabe?")

    def repeat_sequence(self):
        # Während die Lösung vorgespielt wird oder die Rückmeldung steht, ist
        # die Eingabe zu; dann gibt es auch nichts zu wiederholen. Im festen
        # Durchgang gibt es wie im Contest kein „nochmal“.
        if self._fixed_run():
            return
        if self.running and self.current_sequence and (self.input_open or self.waiting_for_input):
            self.waiting_for_input = False
            self.submit_pending = False
            self.enter_time = None
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
                self.enter_time = time.time()
                self.status_var.set("Wird nach dem Ton ausgewertet…")
            return
        answer_time = self.enter_time or time.time()
        typed = clean_input(self.input_var.get())
        self.waiting_for_input = False
        self._set_input_open(False)

        sent = self.current_sequence
        results = align.char_results(sent, typed)
        # Nur der erste Versuch geht in die Zeichenstatistik; bei der
        # Wiederholung ist die Sequenz schon bekannt.
        if self.attempts == 0:
            for index, (expected, got, typed_index) in enumerate(results):
                reaction_time, latency = self._char_timing(index, typed_index)
                effective_wpm = code_units(expected) * 1.2 / max(reaction_time, 0.001)
                self.session_stats.record_char(
                    expected, got, got == expected, reaction_time, effective_wpm, latency=latency
                )
        hits = sum(1 for expected, got, _ in results if got == expected)
        correct_chars = max(hits - align.extra_count(sent, typed), 0)
        slow = answer_time - self.tone_ends[-1] > answer_limit(len(sent)) if self.tone_ends else False
        self._finish_attempt(typed, typed == sent, correct_chars, slow=slow)

    def reveal(self):
        """Kopfhören: Lösung aufdecken, danach bewerten."""
        if not self.running or self.style != HEAD or not self.waiting_for_input or self.revealed:
            return
        self.revealed = True
        explanation = self._explain(self.current_sequence)
        self.feedback_var.set(display_text(self.current_sequence) + (f"\n{explanation}" if explanation else ""))
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

    def _finish_attempt(self, typed: str, all_correct: bool, correct_chars: int, head=False, slow=False):
        """Gemeinsamer Abschluss eines Versuchs: Statistik, Anpassungen,
        Rückmeldung und was als Nächstes kommt."""
        sent = self.current_sequence
        self.session_stats.record_group(
            sent, typed, wpm=self.tempo if self.tempo is None else tempo.effective(self.tempo, self.tempo_fw)
        )
        self.attempts += 1
        # Für den Koch-Aufstieg zählt nur ein flüssiger erster Versuch: ohne
        # Wiederholen, im Zeitfenster; Kopfhören (Selbstbewertung) gar nicht.
        clean = self.attempts == 1 and not self.replayed and not slow
        if self.attempts == 1 and not head:
            self.first_try_total += len(sent)
            if clean:
                self.first_try_correct += correct_chars
        try:
            give_up_after = self.give_up_var.get()
        except tk.TclError:
            give_up_after = DEFAULT_GIVE_UP
        # Beim Kopfhören gibt es keinen zweiten Versuch: die Lösung ist schon zu sehen.
        give_up = not all_correct and (head or self._fixed_run() or 0 < give_up_after <= self.attempts)
        self.repeat_pending = not all_correct and not give_up
        # Richtig, aber nur mit Wiederholen oder zu langsam, zählt für Länge und
        # Tempo wie richtig erst im zweiten Versuch (kein Aufstieg).
        rated_attempts = self.attempts if clean or not all_correct else max(self.attempts, 2)
        self._after_result(all_correct, rated_attempts)
        self._update_tempo(all_correct, rated_attempts)

        explanation = self._explain(sent)
        if all_correct:
            if self.sound_var.get():
                sfx.play_ok()
            note = ""
            if self._fixed_run():
                if slow:
                    note = "\n(zu langsam – keine Punkte)"
            elif not self.koch_progress:
                pass  # Modus zählt ohnehin nicht für die Lektion
            elif slow and self.attempts == 1:
                note = "\n(zu langsam – zählt nicht für die Lektion)"
            elif self.replayed and self.attempts == 1:
                note = "\n(mit Wiederholen – zählt nicht für die Lektion)"
            self.feedback_var.set(
                f"Richtig: {display_text(sent)}" + (f"\n{explanation}" if explanation else "") + note
            )
            self.feedback_label.config(foreground=theme.OK)
            self.diff_var.set("")
        else:
            if self.sound_var.get():
                sfx.play_error()
            if give_up:
                text = f"Lösung: {display_text(sent)}" + (f"\n{explanation}" if explanation else "")
            else:
                text = "Leider falsch – hör noch einmal hin."
            self.feedback_var.set(text)
            self.feedback_label.config(foreground=theme.ERROR)
            if not head:
                sent_row, typed_row, marks = align.diff_rows(sent, typed)
                legend = "\n          – fehlt/zu viel, ^ falsch"
                if give_up:
                    self.diff_var.set(f"gesendet  {sent_row}\ngetippt   {typed_row}\n          {marks}{legend}")
                else:
                    # Nur markieren, wo es hakt; die gesendete Sequenz zu
                    # zeigen hieße, beim nächsten Versuch abzuschreiben.
                    self.diff_var.set(f"getippt   {typed_row}\n          {marks}{legend}")

        self.history.append(f"{sent}{'=' if all_correct else '≠'}{typed}")
        self.history = self.history[-10:]
        self.history_var.set("   ".join(self.history))

        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

        if give_up and self._fixed_run():
            self._later(1500, self.next_sequence)  # Lösung lesen, weiter im Takt
        elif give_up:
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
