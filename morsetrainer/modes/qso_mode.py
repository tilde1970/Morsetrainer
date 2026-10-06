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
- Kopfhören + Fragen: ohne Notizen zuhören, danach einige zufällige
  Inhaltsfragen (Name, QTH, Rig, Wetter … bzw. Austausch, Anzahl QSOs).
- Nur hören: keine Bewertung, der Klartext lässt sich jederzeit aufdecken.

Wie oft ein QSO vor dem Prüfen mit „Nochmal“ wiederholt wurde, wird
mitprotokolliert; dann passt die Tempo-Automatik das Tempo nicht an.
Pile-ups (gleichzeitige Anrufer im Contest) sind einstellbar, Standard aus.

Zuschaltbar sind Kurzwellen-Bandbedingungen (Rauschen mit Knackstörungen,
QSB, Chirp, SSB-QRM und CW-QRM auf der Nachbarfrequenz), siehe band.py.

Unabhängig vom oben eingestellten Zeichensatz."""
import dataclasses
import random
import threading
import time
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import align, audio
from morsetrainer.core import qso_text, tempo
import numpy as np

from morsetrainer.core.band import BandConditions, apply_spec, soft_limit
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.continuous_mode import plausible
from morsetrainer.modes.qso_quiz import QuizPanel
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.band_settings import BandSettings, BandToggle, toggle_value
from morsetrainer.widgets.ui_widgets import ChoiceBox, ScrollableFrame
from morsetrainer.core.morse import (
    MORSE_CODE, PROSIGNS, SAMPLE_RATE, build_samples, char_gap_seconds, code_units, duration_seconds, silence,
    word_gap_extra_seconds,
)
from morsetrainer.core import stats
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets.stats_widget import StatsPanel

EVAL_QUIZ, EVAL_TYPING, EVAL_HEAD, EVAL_LISTEN = "quiz", "typing", "head", "listen"
EVAL_LABELS = {
    EVAL_QUIZ: N_("Mitschreiben + Abfrage"),
    EVAL_TYPING: N_("Fortlaufend mittippen"),
    EVAL_HEAD: N_("Kopfhören + Fragen"),
    EVAL_LISTEN: N_("Nur hören"),
}
# Auswertungen mit Abfrage-Tabelle (Prüfen, Text erst danach).
QUIZ_MODES = (EVAL_QUIZ, EVAL_HEAD)
# So viele Inhaltsfragen beim Kopfhören.
HEAD_QUESTIONS = 3
# Pile-ups im Contest: Beschriftung -> Anteil der Anrufe mit weiteren Rufern.
PILEUP_LEVELS = {N_("aus"): 0.0, N_("selten"): 0.2, N_("oft"): qso_text.PILEUP_PROBABILITY}
LENGTH_LABELS = [N_("Kurz"), N_("Normal"), N_("Lang")]  # Index = qso_text.LENGTH_*

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
# Pile-up-Anrufer sind unterschiedlich laut (relativ zu den anderen Stationen).
PILEUP_STRENGTH = (0.4, 0.9)
WRITE_CHUNK_SECONDS = 0.02
FINISH_GRACE_SECONDS = 3
TICK_MS = 250
# Tempo automatisch anpassen: (Mindest-Trefferquote, Änderung des effektiven
# Tempos in WPM), die erste passende Stufe gilt. Nur ±1: ein QSO hat nur
# wenige abgefragte Felder, ein Ausreißer soll nicht gleich zwei Stufen machen.
ADAPTIVE_STEPS = ((0.9, 1), (0.6, 0), (0.0, -1))


def estimate_minutes(kind: str, length: int, wpm: int, fw=None, samples: int = 3) -> float:
    """Geschätzte Dauer eines QSOs dieser Art und Länge (Mittel über einige
    zufällige QSOs, ohne Pile-ups und Hörpausen der Stationen)."""
    total = 0.0
    for _ in range(samples):
        qso = qso_text.generate_qso(kind, length)
        gap = CONTEST_TX_GAP_SECONDS if qso.is_contest else TX_GAP_SECONDS
        for _, text in qso.transmissions:
            words = text.split()
            total += sum(duration_seconds(ch, wpm, fw) for word in words for ch in word)
            total += word_gap_extra_seconds(wpm, fw) * (len(words) - 1) + gap
    return total / samples / 60


def _voice(wpm: int, freq: int, offset_range, wpm_offsets):
    offset = random.choice((-1, 1)) * random.randint(*offset_range)
    if not 300 <= freq + offset <= 1000:
        offset = -offset
    return max(wpm + random.choice(wpm_offsets), 5), freq + offset


class QsoModeFrame:
    """Reiter QSO: ein erzeugtes QSO oder ein Contest-Run hören, auf Wunsch mit
    Abfrage der Inhalte, Mittippen oder Kopfhören mit Fragen; mit mehreren
    Stationen, Pile-ups und Bandbedingungen."""
    uses_tempo_adjust = True
    uses_band = True  # zentrale Bandbedingungen (widgets/band_settings.py)

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 adjust_tempo=None, band_settings=None):
        self.root = parent.winfo_toplevel()
        self.band_settings = band_settings or BandSettings(self.root)
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.farnsworth_wpm = farnsworth_wpm  # callable -> effektive WPM oder None
        self.adjust_tempo = adjust_tempo      # callable(delta) -> (vorher, nachher) als Text
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
        self.overlays = []         # [[Samples, Position, Station]] gleichzeitig laufender Pile-up-Anrufer
        self.session_stats = None
        self.session_id = 0
        self.finishing = False
        self.revealed = False
        self.quiz_ready = False    # QSO einmal komplett gelaufen, Abfrage verfügbar
        self.quiz_checked = False
        self.qso_eval = EVAL_QUIZ  # Auswertungsart des aktuellen QSOs (beim Start festgehalten)

        self._build_widgets(ScrollableFrame(parent).inner)
        self.wpm_var.trace_add("write", lambda *_: self._update_length_hint())
        self._on_kind_change()
        self._update_layout()

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        """Baut den Reiter: Einstellungen, Knöpfe, Notizen, Mittippen, Abfrage,
        Klartext und Statistik (die Bereiche ordnet _update_layout())."""
        theme.hint(
            parent, wrap=560,
            text=tr("Hör einem kompletten CW-QSO oder einem Contest-Run zu. Jede Station hat eine "
                    "eigene Tonhöhe. "
                    "„=“ ist BT (Trennung), „+“ ist AR (Ende des Durchgangs); <SK>, <KN> und <BK> "
                    "werden zusammengezogen gesendet und beim Mittippen nicht gezählt. "
                    "Der Zeichensatz oben gilt hier nicht."),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self._build_qso_settings(parent)
        self.band_var = tk.BooleanVar(value=False)
        BandToggle(parent, self.band_settings, self.band_var, on_change=self._apply_band_settings, padx=12,
                   pady=(2, 4))

        self.eval_var.trace_add("write", lambda *_: self._on_eval_change())
        self.kind_var.trace_add("write", lambda *_: self._on_kind_change())
        self.length_var.trace_add("write", lambda *_: self._update_length_hint())

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Neues QSO (F5)"), style="Accent.TButton",
                                       command=self.toggle_running)
        self.start_button.pack(side="left")
        self.replay_button = ttk.Button(controls, text=tr("Nochmal (F6)"), command=self.replay, state="disabled")
        self.replay_button.pack(side="left", padx=8)
        self.reveal_button = ttk.Button(controls, text=tr("Text zeigen (F7)"), command=self.toggle_reveal,
                                        state="disabled")
        self.reveal_button.pack(side="left")

        self.status_var = tk.StringVar(value=tr("Bereit. Drücke „Neues QSO“."))
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel").pack(pady=(14, 6))

        # Ein- und ausblendbare Bereiche; _update_layout() packt die jeweils
        # sichtbaren in fester Reihenfolge.
        self.notes_box = ttk.LabelFrame(parent, text=tr("Notizen (frei, werden nicht ausgewertet)"), padding=(8, 4, 8, 8))
        self.notes = tk.Text(self.notes_box, height=4, wrap="word", font=theme.MONO)
        self.notes.pack(fill="x")

        self.typed_box = ttk.LabelFrame(parent, text=tr("Deine Eingabe (letzte Zeichen)"), padding=(8, 4, 8, 8))
        self.typed_preview_var = tk.StringVar(value="")
        ttk.Label(self.typed_box, textvariable=self.typed_preview_var, font=theme.MONO, wraplength=540).pack(
            anchor="w"
        )

        self.quiz = QuizPanel(parent, on_checked=self._on_quiz_checked)
        self.quiz_box = self.quiz.box

        self.reveal_box = ttk.LabelFrame(parent, text=tr("QSO-Text"), padding=(8, 4, 8, 8))
        self.reveal_text = tk.Text(self.reveal_box, height=8, wrap="word", font=theme.MONO)
        scroll = ttk.Scrollbar(self.reveal_box, orient="vertical", command=self.reveal_text.yview)
        self.reveal_text.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.reveal_text.pack(fill="x")
        for i, color in enumerate(theme.STATION_COLORS):
            self.reveal_text.tag_config(f"st{i}", foreground=color)
        self.reveal_text.tag_config("miss", foreground=theme.SURFACE, background=theme.ERROR)
        self.reveal_text.tag_config("unsent", foreground=theme.DISABLED)
        self.reveal_text.tag_config("extra", foreground=theme.DISABLED, font=theme.SMALL_ITALIC)
        self.reveal_text.config(state="disabled")

        self.stats_box = ttk.Frame(parent)
        self.stats_panel = StatsPanel(self.stats_box, tree_height=5)

    def _build_qso_settings(self, parent):
        """Einstellungen des QSOs: Art (normal oder Contest), Auswertung, Länge,
        Pile-ups, Tempo automatisch anpassen und Bandbedingungen."""
        box = theme.card(parent, "QSO")
        box.columnconfigure(1, weight=1)
        row_pad = {"padx": (0, 8), "pady": 2}

        ttk.Label(box, text=tr("Art:")).grid(row=0, column=0, sticky="w", **row_pad)
        self.kind_var = tk.StringVar(value=qso_text.QSO_TYPES[qso_text.RAGCHEW])
        self.kind_combo = ChoiceBox(box, self.kind_var, qso_text.QSO_TYPES.values(), width=32)
        self.kind_combo.grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(box, text=tr("Auswertung:")).grid(row=1, column=0, sticky="w", **row_pad)
        self.eval_var = tk.StringVar(value=EVAL_LABELS[EVAL_QUIZ])
        self.eval_combo = ChoiceBox(box, self.eval_var, EVAL_LABELS.values(), width=32)
        self.eval_combo.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(box, text=tr("Länge:")).grid(row=2, column=0, sticky="w", **row_pad)
        length_row = ttk.Frame(box)
        length_row.grid(row=2, column=1, sticky="w", pady=(2, 6))
        self.length_var = tk.StringVar(value=LENGTH_LABELS[qso_text.LENGTH_SHORT])
        self.length_combo = ChoiceBox(length_row, self.length_var, LENGTH_LABELS, width=10)
        self.length_combo.pack(side="left")
        self.length_hint_var = tk.StringVar(value="")
        theme.hint(length_row, textvariable=self.length_hint_var).pack(side="left", padx=(8, 0))

        ttk.Label(box, text="Pile-ups:").grid(row=3, column=0, sticky="w", **row_pad)
        pileup_row = ttk.Frame(box)
        pileup_row.grid(row=3, column=1, sticky="w", pady=(0, 6))
        self.pileup_var = tk.StringVar(value="aus")
        self.pileup_combo = ChoiceBox(pileup_row, self.pileup_var, PILEUP_LEVELS, width=10)
        self.pileup_combo.pack(side="left")
        theme.hint(pileup_row, text=tr("(im Contest rufen weitere Stationen gleichzeitig)")).pack(side="left", padx=(8, 0))

        self.adaptive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            box, text=tr("Tempo automatisch anpassen (nach Abfrage/Mittippen, ändert das Tempo oben)"),
            variable=self.adaptive_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w")

    def _kind(self) -> str:
        for key, label in qso_text.QSO_TYPES.items():
            if label == self.kind_var.get():
                return key
        return qso_text.RAGCHEW

    def _apply_band_settings(self):
        """Auch während der Wiedergabe: der Audio-Thread liest nur die
        einfachen Attribute von self.band."""
        if self.band is not None:
            apply_spec(self.band, self.band_settings.spec() if self.band_var.get() else None)
            self.band.prepare(self.voices[0][1])

    def _on_kind_change(self):
        self._update_length_hint()
        self.pileup_combo.config(state="disabled" if self._kind() == qso_text.RAGCHEW else "readonly")
        if self.qso is None:
            self._update_layout()

    def _update_length_hint(self):
        """Hinweis neben der Länge: Zahl der QSOs im Contest und ungefähre Dauer
        beim aktuellen Tempo."""
        length = LENGTH_LABELS.index(self.length_var.get())
        parts = []
        if self._kind() != qso_text.RAGCHEW:
            low, high = qso_text.CONTEST_QSO_RANGES[length]
            parts.append(f"{low}–{high} QSOs")
        try:
            wpm = self.wpm_var.get()
        except tk.TclError:
            wpm = None
        if wpm:
            minutes = estimate_minutes(self._kind(), length, wpm, self.farnsworth_wpm())
            parts.append(tr("ca. {minutes} Min. bei {tempo}").format(
                minutes=max(round(minutes), 1), tempo=tempo.label(wpm, self.farnsworth_wpm())))
        self.length_hint_var.set(" · ".join(parts))

    def _eval_mode(self) -> str:
        for key, label in EVAL_LABELS.items():
            if label == self.eval_var.get():
                return key
        return EVAL_QUIZ

    def _on_eval_change(self):
        self._update_layout()
        self._update_reveal_button()

    def _update_layout(self):
        """Zeigt nur die Bereiche, die zur Auswertung passen (Notizen, Mittippen,
        Abfrage, Klartext, Statistik), in fester Reihenfolge."""
        mode = self._eval_mode()
        # Im Contest wird direkt ins Log geschrieben, schon während des Hörens.
        contest = self.qso.is_contest if self.qso is not None else self._kind() != qso_text.RAGCHEW
        live_log = contest and mode == EVAL_QUIZ and self.qso is not None
        boxes = [
            (self.notes_box, mode == EVAL_LISTEN or (mode == EVAL_QUIZ and not contest and not self.quiz_checked)),
            (self.typed_box, mode == EVAL_TYPING),
            (self.quiz_box, mode in QUIZ_MODES and (self.quiz_ready or live_log)),
            (self.reveal_box, self.revealed),
            (self.stats_box, mode == EVAL_TYPING),
        ]
        for box, _ in boxes:
            box.pack_forget()
        for box, visible in boxes:
            if visible:
                # Das Statistik-Panel bringt seinen eigenen Rahmen mit.
                box.pack(fill="x", **({} if box is self.stats_box else {"padx": 10, "pady": 5}))

    def _update_reveal_button(self):
        # Während des ersten Durchlaufs nur im reinen Hörmodus aufdeckbar,
        # sonst wäre die Abfrage bzw. das Mittippen witzlos.
        """Knopf „Text zeigen“ nur freigeben, wenn das nichts verrät: bei Abfrage
        erst nach dem Prüfen, beim Mittippen erst nach dem Durchlauf."""
        if self._eval_mode() in QUIZ_MODES:
            # Bei der Abfrage erst nach „Prüfen“, sonst ließe sich abschreiben.
            allowed = self.qso is not None and self.quiz_checked
        else:
            allowed = self.qso is not None and not self.tracking and (
                not self.running or self.quiz_ready or self._eval_mode() == EVAL_LISTEN
            )
        self.reveal_button.config(
            state="normal" if allowed else "disabled",
            text=tr("Text verbergen (F7)") if self.revealed else tr("Text zeigen (F7)"),
        )

    # --- Ablauf -----------------------------------------------------------
    def toggle_running(self):
        """QSO starten bzw. beenden (Knopf, F5)."""
        if self.running:
            self._finish(stopped=True)
        else:
            self.start_new()

    def start_new(self):
        """Erzeugt ein neues QSO nach Art, Länge und Pile-up-Stufe, verteilt Tempo
        und Tonhöhe auf die Stationen und spielt es ab."""
        try:
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except tk.TclError:
            self.status_var.set(tr("Ungültige Geschwindigkeit oder Tonhöhe!"))
            return
        self._log_skipped_head()
        self.qso = qso_text.generate_qso(self._kind(), LENGTH_LABELS.index(self.length_var.get()),
                                         PILEUP_LEVELS.get(self.pileup_var.get(), 0.0))
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
        self.replays = 0  # „Nochmal“ vor dem Prüfen
        # Auswertungsart beim Start festhalten: wer mit Notizen hört und vor
        # dem Prüfen auf Kopfhören umschaltet, soll nicht als Kopfhören zählen.
        self.qso_eval = self._eval_mode()
        self.quiz.reset(self._quiz_view())
        self.notes.delete("1.0", "end")
        self._play(tracking=self._eval_mode() == EVAL_TYPING)

    def _log_skipped_head(self):
        """Ein Kopfhör-QSO, das ohne „Prüfen“ übersprungen wird, zählt als
        nicht verstanden: Sonst ließe sich die Serie fürs Diplom Kopfhörer
        aus den gelungenen QSOs zusammensuchen. Im Verlauf erscheint es nicht."""
        if (self.qso is not None and self.quiz_ready and not self.quiz_checked
                and self.qso_eval == EVAL_HEAD):
            stats.log_result("qso_head", 0, HEAD_QUESTIONS, tempo.effective(self.voices[0][0], self.fw),
                             kind=self.qso.kind, length=self.length_var.get(), replays=self.replays, skipped=True,
                             char_wpm=self.voices[0][0])

    def _quiz_view(self):
        """Was die Abfrage-Tabelle zeigt: beim Kopfhören einige zufällige
        Inhaltsfragen statt des ganzen Logs."""
        if self._eval_mode() != EVAL_HEAD or not self.qso.facts:
            return self.qso
        facts = random.sample(self.qso.facts, min(HEAD_QUESTIONS, len(self.qso.facts)))
        return dataclasses.replace(self.qso, quiz_columns=(tr("Antwort (wie gesendet)"),),
                                   quiz_rows=tuple((question, (cell,)) for question, cell in facts))

    def replay(self):
        """Spielt das letzte QSO noch einmal ab, ohne Auswertung."""
        if self.qso is not None and not self.running:
            if not self.quiz_checked:
                if self.qso_eval == EVAL_HEAD:
                    # Mit den Fragen vor Augen nochmal hören wäre gezieltes
                    # Mitschreiben statt Kopfhören.
                    self.status_var.set(tr("Erst die Fragen beantworten und prüfen – dann „Nochmal“."))
                    return
                self.replays += 1
            self._play(tracking=False)

    def _play(self, tracking: bool):
        """Startet die Wiedergabe des QSOs im Audio-Thread; mit `tracking` wird
        mitgetippt und als Durchgang aufgezeichnet."""
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
                "qso", "QSO-Text", wpm, freq, farnsworth_wpm=self.fw, char_stats=False,
                group_len={"kind": self.qso.kind, "length": self.length_var.get(), "calls": list(self.qso.calls),
                           "voices": [list(v) for v in self.voices]},
            )
            self.stats_panel.reset()
            self.typed_preview_var.set("")

        self.running = True
        self.start_button.config(text=tr("Stop (F5)"))
        self.replay_button.config(state="disabled")
        for combo in (self.kind_combo, self.eval_combo, self.length_combo):
            combo.config(state="disabled")
        if not self.quiz_ready:
            self.quiz.set_check_enabled(False)
        self._update_reveal_button()
        self._update_layout()
        self.on_start_cb()

        self.audio_error = None  # Fehlermeldung aus dem Audio-Thread
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        self.root.after(TICK_MS, self._tick, self.session_id)

    def _own_thread(self) -> bool:
        """Gehört der aufrufende Audio-Thread zum laufenden QSO? Ein alter
        Thread, der nach Stop an einem hängenden Gerät festhing, darf ein
        neues QSO weder beschreiben noch beenden."""
        return threading.current_thread() is self.play_thread

    def _play_loop(self):
        try:
            self._play_qso()
        except audio.ERRORS as exc:
            if self._own_thread():
                self.audio_error = audio.describe(exc)  # _tick beendet das QSO
        except Exception as exc:
            if self._own_thread():
                self.audio_error = audio.unexpected(exc)
            raise  # ins Fehlerprotokoll (threading.excepthook)

    def _play_qso(self):
        """Audio-Thread: spielt alle Durchgänge der Stationen in einem Strom, mit
        Pausen dazwischen, Pile-up-Anrufern und Bandbedingungen."""
        with audio.output_stream() as stream:
            lead_in = NOISE_LEAD_IN_SECONDS if self.band.has_background else LEAD_IN_SECONDS
            if not self._write(stream, silence(lead_in)):
                return
            gap = CONTEST_TX_GAP_SECONDS if self.qso.is_contest else TX_GAP_SECONDS
            pileups = dict(self.qso.pileups)
            self.overlays = []
            for tx_index, (station, text) in enumerate(self.qso.transmissions):
                self.current_tx = tx_index
                wpm, freq = self.voices[station]
                if tx_index and not self._write(stream, silence(gap)):
                    return
                for other, other_text, delay in pileups.get(tx_index, ()):
                    self._start_overlay(other, other_text, delay)
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
                # Pile-up-Anrufer, die länger rufen, noch ausklingen lassen.
                while self.overlays:
                    if not self._write(stream, silence(WRITE_CHUNK_SECONDS)):
                        return
            if self.band.has_background:
                self._write(stream, silence(NOISE_TAIL_SECONDS))

    def _start_overlay(self, station: int, text: str, delay: float):
        wpm, freq = self.voices[station]
        parts = [silence(delay)] + [
            silence(word_gap_extra_seconds(wpm, self.fw)) if ch == " "
            else build_samples(ch, wpm, freq, self.fw, self.band.chirp_for(station))
            for ch in text
        ]
        samples = np.concatenate(parts) * random.uniform(*PILEUP_STRENGTH)
        self.overlays.append([samples.astype(np.float32), 0, station])

    def _overlay_blocks(self, n: int):
        """Nächste `n` Samples aller laufenden Pile-up-Anrufer; fertige
        fallen heraus."""
        blocks = []
        for overlay in self.overlays:
            samples, pos, station = overlay
            blocks.append((samples[pos:pos + n], station))
            overlay[1] = pos + n
        self.overlays = [o for o in self.overlays if o[1] < len(o[0])]
        return blocks

    def _write(self, stream, samples, station: int = 0) -> bool:
        """Schreibt `samples` (von Station `station`) häppchenweise, ggf. mit
        Pile-up-Anrufern und Rauschen/QSB; False, wenn zwischendurch
        gestoppt wurde."""
        chunk = int(SAMPLE_RATE * WRITE_CHUNK_SECONDS)
        for start in range(0, len(samples), chunk):
            if not (self.running and self._own_thread()):
                return False
            block = samples[start:start + chunk]
            if self.overlays or self.band.active:
                sources = [(block, station)] + self._overlay_blocks(len(block))
                if self.band.active:
                    block = self.band.mix(sources, len(block))
                else:
                    mixed = np.zeros(len(block))
                    for part, _ in sources:
                        mixed[:len(part)] += part
                    block = soft_limit(mixed).astype(np.float32)
            stream.write(block)
        return True

    def _tick(self, session_id):
        """Regelmäßig während der Wiedergabe: Fehler melden, Eingabe und Stand
        („Durchgang 3 von 8“) zeigen, am Ende _finish()."""
        if not self.running or session_id != self.session_id:
            return
        if self.audio_error:
            self._finish(stopped=True)
            self.status_var.set(self.audio_error)
            return
        if self.tracking:
            self.typed_preview_var.set("".join(e["char"] for e in self.typed_log)[-60:])
        if self.play_thread.is_alive():
            label = tr("Wiederholung – ") if not self.tracking and self.quiz_ready else ""
            self.status_var.set(label + tr("Durchgang {n} von {total}").format(
                n=self.current_tx + 1, total=len(self.qso.transmissions)))
        elif not self.tracking:
            self._finish()
            return
        elif not self.finishing:
            self.finishing = True
            self.status_var.set(tr("QSO zu Ende – tippe die letzten Zeichen noch ein…"))
            self.root.after(FINISH_GRACE_SECONDS * 1000, self._auto_finish, session_id)
        self.root.after(TICK_MS, self._tick, session_id)

    def _auto_finish(self, session_id):
        if self.running and session_id == self.session_id:
            self._finish()

    def _finish(self, stopped: bool = False):
        """QSO zu Ende oder gestoppt: Knöpfe zurücksetzen, beim Mittippen auswerten,
        sonst Abfrage freigeben; sagt an, was jetzt zu tun ist."""
        self.running = False
        if self.play_thread is not None:
            self.play_thread.join(timeout=2)
            self.play_thread = None
        self.start_button.config(text=tr("Neues QSO (F5)"))
        head_unchecked = self.qso_eval == EVAL_HEAD and not self.quiz_checked
        self.replay_button.config(state="disabled" if head_unchecked else "normal")
        for combo in (self.kind_combo, self.eval_combo, self.length_combo):
            combo.config(state="readonly")

        mode = self._eval_mode()
        # Ansage (Barrierefreiheit): was jetzt zu tun ist.
        if self.tracking:
            accuracy = self._finalize_session()
            self.revealed = True
            self.tracking = False
            self.status_var.set(tr("Ausgewertet – rot markiert: falsch oder verpasst.") + self._adapt_speed(accuracy))
            spoken = (tr("Ausgewertet. {percent} Prozent der Zeichen richtig.").format(percent=round(accuracy * 100))
                      if accuracy is not None else tr("Ausgewertet."))
        elif mode == EVAL_HEAD and not self.quiz_checked:
            self.status_var.set(tr("Beantworte die Fragen und drück „Prüfen“."))
            spoken = tr("QSO zu Ende. Beantworte die Fragen; Tab springt in die Felder, F8 prüft.")
        elif mode == EVAL_QUIZ and not self.quiz_checked:
            self.status_var.set(tr("Ergänze dein Log und drück „Prüfen“.") if self.qso.is_contest
                                else tr("Trag ein, was du gehört hast, und drück „Prüfen“."))
            spoken = tr("QSO zu Ende. Trag ins Log ein, was du gehört hast; Tab springt in die Felder, F8 prüft.")
        else:
            self.status_var.set(tr("QSO beendet."))
            spoken = tr("QSO beendet.")
        if stopped:
            self.status_var.set(tr("Gestoppt. ") + self.status_var.get())
            spoken = tr("Gestoppt. ") + spoken
        announcer.say(spoken)
        self.quiz_ready = True
        self.quiz.set_check_enabled(True)

        self._update_layout()
        self._update_reveal_button()
        self._render_reveal()
        self.on_stop_cb()

    def _finalize_session(self):
        """Wertet das Mittippen aus; gibt die Trefferquote (0..1) zurück, oder
        None, wenn es nichts auszuwerten gab."""
        if self.session_stats is None:
            return None
        sent_str = "".join(e["char"] for e in self.sent_log)
        typed_str = "".join(e["char"] for e in self.typed_log)
        missed = set()
        for op in align.align(sent_str, typed_str):
            if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE):
                correct = op.kind == align.OpKind.MATCH
                play_end = self.sent_log[op.expected_index]["end_time"]
                typed_time = self.typed_log[op.received_index]["time"]
                if not plausible(typed_time, play_end):
                    # Vorausgeahnt („DE“, „599“) oder viel zu spät: verpasst.
                    self.session_stats.record_char(op.expected_char, "", False, 0.0, 0.0)
                    missed.add(op.expected_index)
                    continue
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

        summary = self.session_stats.summary()
        self.stats_panel.refresh(summary, self.session_stats.char_rows())
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None
        return summary["accuracy_pct"] / 100 if summary["total"] else None

    # --- Klartext -----------------------------------------------------------
    def toggle_reveal(self):
        """Klartext des QSOs zeigen bzw. verbergen (F7)."""
        if self.qso is None:
            return
        self.revealed = not self.revealed
        self._render_reveal()
        self._update_layout()
        self._update_reveal_button()

    def _render_reveal(self):
        """Füllt den Klartext: Durchgänge je Station farbig, Pile-up-Anrufer
        markiert, beim Mittippen die Fehler hervorgehoben."""
        if not self.revealed or self.qso is None:
            return
        pileups = dict(self.qso.pileups)
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
            if n in pileups:
                others = ", ".join(self.qso.calls[station] for station, _, _ in pileups[n])
                text.insert("end", tr("   (gleichzeitig: {calls})").format(calls=others), ("extra",))
        text.config(state="disabled")

    # --- Abfrage ------------------------------------------------------------
    def _on_quiz_checked(self, correct: int, total: int):
        """Abfrage geprüft: Ergebnis protokollieren, Klartext zeigen und, wenn
        eingeschaltet, das Tempo anpassen (nicht nach „Nochmal“ oder beim
        Kopfhören)."""
        head = self.qso_eval == EVAL_HEAD
        mode = "qso_head" if head else "qso_quiz"
        stats.log_result(mode, correct, total, tempo.effective(self.voices[0][0], self.fw), kind=self.qso.kind,
                         length=self.length_var.get(), replays=self.replays, char_wpm=self.voices[0][0])
        self.on_stop_cb()  # Statistik-Reiter (Verlauf) aktualisieren
        self.quiz_checked = True
        self.revealed = True
        self.replay_button.config(state="normal")
        if self.replays:
            # Mehrfach gehört: das Ergebnis sagt wenig über das Tempo.
            note = (tr(" (vorher einmal „Nochmal“ – Tempo bleibt)") if self.replays == 1
                    else tr(" (vorher {n}× „Nochmal“ – Tempo bleibt)").format(n=self.replays))
        elif head:
            note = ""  # drei Fragen sind zu wenig, um das Tempo anzupassen
        else:
            note = self._adapt_speed(correct / total if total else None)
        self.status_var.set(tr("Abfrage ausgewertet.") + note)
        announcer.say(self.quiz.spoken_result())
        self._render_reveal()
        self._update_layout()
        self._update_reveal_button()

    def _adapt_speed(self, accuracy) -> str:
        """Passt bei eingeschalteter Option das Tempo (gemeinsame Einstellung,
        Regel aus core/tempo.py: erst die Farnsworth-Pausen) an die
        Trefferquote an; gibt einen Hinweis für die Statuszeile zurück."""
        if accuracy is None or not self.adaptive_var.get() or self.adjust_tempo is None:
            return ""
        change = next(step for threshold, step in ADAPTIVE_STEPS if accuracy >= threshold)
        result = self.adjust_tempo(change)
        if result is None:
            return ""
        before, after = result
        if before == after:
            return tr(" Tempo bleibt bei {tempo}.").format(tempo=before)
        return tr(" Tempo: {before} → {after}.").format(before=before, after=after)

    # --- Schnittstelle zur App ------------------------------------------------
    def on_function_key(self, key: str):
        """F5 startet bzw. beendet, F6 spielt nochmal, F7 zeigt den Klartext, F8
        prüft die Abfrage."""
        if key == "F5":
            self.toggle_running()
        elif key == "F6" and str(self.replay_button["state"]) != "disabled":
            self.replay()
        elif key == "F7" and str(self.reveal_button["state"]) != "disabled":
            self.toggle_reveal()
        elif key == "F8" and self._eval_mode() in QUIZ_MODES and self.quiz_ready:
            self.quiz.check()

    def settings(self) -> dict:
        """Einstellungen zum Speichern in window_state.json (Schlüssel statt
        Beschriftungen, damit Umbenennungen alte Dateien nicht entwerten)."""
        return {
            "kind": self._kind(),
            "eval": self._eval_mode(),
            "length": LENGTH_LABELS.index(self.length_var.get()),
            "adaptive": self.adaptive_var.get(),
            "pileups": self.pileup_var.get(),
            "band": self.band_var.get(),
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
        if isinstance(data.get("adaptive"), bool):
            self.adaptive_var.set(data["adaptive"])
        if data.get("pileups") in PILEUP_LEVELS:
            self.pileup_var.set(data["pileups"])
        if "band" in data and toggle_value(data["band"]) is not None:
            self.band_var.set(toggle_value(data["band"]))

    def on_close(self):
        """Programmende: Wiedergabe beenden und den Durchgang speichern."""
        if self.running:
            self.running = False
            if self.play_thread is not None:
                self.play_thread.join(timeout=2)
        self._finalize_session()

    def on_key(self, event):
        """Beim Mittippen: jedes Morsezeichen mit Zeitpunkt mitschreiben."""
        if not (self.running and self.tracking):
            return
        typed = event.char.upper()
        if typed and typed in MORSE_CODE:
            self.typed_log.append({"char": typed, "time": time.time()})
