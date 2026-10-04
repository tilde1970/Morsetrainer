"""Netzwerk-Reiter: ein Trainer gibt im lokalen Netz vor, mehrere
Teilnehmer hören und tippen mit (siehe morsetrainer/net/).

Trainer: öffnet eine Sitzung (Name, PIN), wählt Inhalt (Einzelzeichen,
Gruppen, Wörter, Rufzeichen oder eigenen Text, eine Zeile je Sequenz),
Anzahl, Antwortzeit und Bandbedingungen; Tempo und Zeichensatz kommen aus
der Kopfleiste. Alle bekommen dieselbe Sequenz zur selben Zeit. Die
nächste kommt, sobald alle geantwortet haben oder die Antwortzeit um ist
(oder auf Knopfdruck). Die Tabelle zeigt live, wer was getippt hat; am
Ende gibt es die Auswertung der Gruppe und einen CSV-Export.

Im festen Takt (für Teilnehmer, die auf Papier mitschreiben) kommt die
nächste Sequenz nach Ton plus Schreibpause, egal wer geantwortet hat, und
bis zum Ende steht nirgends eine Lösung – der Trainerbildschirm hängt
womöglich am Beamer. Die Auflösung (eigenes Fenster) zeigt währenddessen
nur die laufende Nummer, danach alle Lösungen zum Vergleichen und
Anhören. Wer auf Papier schreibt, tippt die Mitschrift danach ab, am
eigenen Rechner oder der Trainer für ihn („Papierbogen eintragen“); diese
Antworten zählen ohne Zeit, also nicht für „flüssig“ und die
Tempo-Empfehlung. Einen Antwortbogen zum Ausdrucken gibt es auch
(core/answer_sheet.py).

Teilnehmer: sucht den Trainer im Netz (oder gibt die Adresse ein),
meldet sich mit Name/Rufzeichen und PIN an. Der Ton entsteht auf dem
eigenen Rechner mit der eigenen Tonhöhe; Tempo, Pausen und Störungen gibt
der Trainer vor. Eingegeben wird wie beim Mitschreiben schon während des
Tons, ein Versuch je Sequenz; danach steht die Lösung da (im festen Takt
erst am Ende, als Liste zum Anhören). Die Ergebnisse landen in der eigenen
Statistik wie ein normaler Durchgang. Hat der Trainer eine neuere
Programmversion, bietet der Reiter an, sie zu laden und neu zu starten
(net/update.py); danach verbindet er sich wieder."""
import random
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import messagebox, ttk

from morsetrainer.core import align, answer_sheet, audio, band, stats, tempo
import numpy as np

from morsetrainer.core.morse import (
    AUDIO_LATENCY, END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text, char_gap_seconds,
    code_units, display_text, silence, word_gap_extra_seconds,
)
from morsetrainer.core.stats import LATENCY_CAP_S, SessionStats
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import N_, number, tr
from morsetrainer.modes.content import PLAIN_TEXT, ItemSource, qso_sections
from morsetrainer.modes.sequence_mode import BAND_LABELS, HISTORY_LEN, answer_limit
from morsetrainer.modes.word_mode import open_in_editor
from morsetrainer.net import client as net_client
from morsetrainer.net import protocol
from morsetrainer.net import stream as net_stream
from morsetrainer.net.scoreboard import (
    Scoreboard, evaluate, format_confusions, format_weak, normalize, solution_cells, solution_columns, solution_rows,
    solution_text,
)
from morsetrainer.net.server import TrainerServer
from morsetrainer.widgets import theme
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ChoiceBox, ScrollableFrame

TRAINER, TRAINEE = "trainer", "trainee"
# Ablauf: warten, bis alle geantwortet haben, fester Takt (Papier) oder
# kontinuierlich (Gruppen ohne Pause für eine feste Dauer, net/stream.py).
WAIT, PACED, CONTINUOUS = "wait", "paced", "continuous"
# Inhalt: Beschriftung -> Art für content.ItemSource ("custom" = eigener Text).
CONTENTS = {
    N_("Einzelzeichen"): "chars",
    N_("Gruppen"): "groups",
    N_("Wörter"): "words",
    N_("Rufzeichen"): "calls",
    N_("Wendungen"): "phrases",
    N_("QSO-Klartext"): "qso",
    N_("Eigener Text"): "custom",
}
REJECTED = {
    "proto": N_("Abgelehnt: Der Trainer nutzt eine andere Programmversion."),
    "pin": N_("Abgelehnt: PIN falsch."),
    "name": N_("Abgelehnt: Name fehlt oder ist schon vergeben."),
}
# Eingänge aus dem Netz so oft abholen.
POLL_MS = 100
# Nach dem Schließen einer Sequenz bis zur nächsten (Lösung lesen).
NEXT_DELAY_MS = 2500
ANSWER_RANGE = (2, 60)
# Schreibpause im festen Takt, fest je Sequenz. Vorgabe je Inhalt: Ein
# Zeichen ist schnell notiert, längere Pausen laden zum Grübeln ein.
PAUSE_RANGE = (1, 30)
PAUSE_DEFAULTS = {"chars": 2, "groups": 4, "words": 3, "calls": 4, "phrases": 5, "qso": 5, "custom": 4}
# Auflösungsfenster: Schriftgröße der Lösungen (Standard, kleinste, größte,
# Schritt); die laufende Nummer ist dreimal so groß.
SOLUTION_FONT = (28, 12, 96, 4)
COUNT_RANGE = (0, 200)
# Vorgabe der Anzahl: Sequenzen, bei QSO-Klartext ganze QSOs (je ≈ 35 Abschnitte).
DEFAULT_COUNT, DEFAULT_QSO_COUNT = 20, 1
GROUP_LEN_RANGE = (1, 10)
DEFAULT_ANSWER_S = 8
# Zeilen der Teilnehmertabelle im Reiter: mindestens, höchstens (dann Scrollbalken).
TABLE_ROWS = (6, 12)
# Antwortbogen: so viele Zeilen, wenn die Anzahl nicht feststeht (bis Stop, QSOs).
SHEET_DEFAULT_ROWS = 25


def make_pin() -> str:
    return f"{random.randint(0, 9999):04d}"


def sequence_seconds(text: str, wpm: int, fw, band_preset) -> float:
    """So lange läuft der Ton einer Sequenz beim Teilnehmer (ohne Latenz)."""
    seconds = len(build_text(text, wpm, 600, fw)) / SAMPLE_RATE
    if band_preset:
        seconds += sum(band.PRESET_LEAD_SECONDS)
    return seconds


class PaperSheet:
    """Eingabe einer Papier-Mitschrift: je Nummer ein Feld, spaltenweise
    von oben nach unten wie in der Auflösung. Enter springt weiter."""

    def __init__(self, parent, numbers):
        self.frame = ttk.Frame(parent)
        self.entries = {}
        height = -(-len(numbers) // solution_columns(len(numbers))) if numbers else 1
        order = []
        for i, n in enumerate(numbers):
            column, row = divmod(i, height)
            ttk.Label(self.frame, text=f"{n}.", font=theme.MONO).grid(
                row=row, column=2 * column, sticky="e", padx=(12 if column else 0, 2))
            entry = ttk.Entry(self.frame, width=12, font=theme.MONO)
            entry.grid(row=row, column=2 * column + 1, sticky="w", pady=1)
            entry.bind("<Return>", lambda e, i=i: self.focus(i + 1) or "break")
            self.entries[n] = entry
            order.append(entry)
        self.order = order

    def focus(self, index: int = 0):
        if 0 <= index < len(self.order):
            self.order[index].focus_set()

    def values(self) -> dict:
        return {n: entry.get() for n, entry in self.entries.items()}

    def clear(self):
        for entry in self.order:
            entry.delete(0, "end")


class NetworkModeFrame:
    session_mode = "network"

    # Bekommt vom Hauptfenster practice_start und practice_stop
    # sowie adjust_tempo (für die Tempo-Empfehlung).
    uses_network_hooks = True
    uses_tempo_adjust = True

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 practice_start=None, practice_stop=None, adjust_tempo=None, version=None,
                 updater=None, session_closed=None):
        """Übungszeit zählt beim Teilnehmer nur, solange ein Durchgang läuft
        (practice_start/practice_stop), nicht beim Warten auf den Trainer;
        die Reiter bleiben gesperrt, solange er verbunden ist.

        `version`: eigene Programmversion; `updater` (widgets.updater)
        bietet an, auf die des Trainers zu aktualisieren.
        `session_closed`: Der Trainer hat seine Sitzung geschlossen (dann
        die Diplome prüfen: Clubabend gilt auch fürs Leiten)."""
        self.root = parent.winfo_toplevel()
        self.version = version
        self.updater = updater
        self.adjust_tempo = adjust_tempo
        self.practice_start = practice_start or (lambda: None)
        self.practice_stop = practice_stop or (lambda: None)
        self.session_closed = session_closed or (lambda: None)
        self.charset_var = charset_var
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.farnsworth_wpm = farnsworth_wpm
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop
        self.running = False  # Tabs gesperrt: Teilnehmer verbunden
        self.poll_id = None   # geplante Abfrage (after), None = keine
        self.after_ids = set()  # übrige geplante Aufrufe, beim Schließen abgebrochen
        self.found = None     # Ergebnis der Suche aus dem Such-Thread

        # Trainer
        self.server = None
        self.board = None
        self.run_active = False
        self.run_token = 0
        self.run_started = 0.0
        self.source = None
        self.custom_items = []
        self.planned = 0
        self.item_n = 0
        self.item = None       # aktuelle Sequenz, wie verschickt
        self.item_open = False
        self.deadline = None
        self.run_paced = False  # Durchgang im festen Takt
        self.run_continuous = False  # kontinuierlicher Durchgang
        self.stream_player = None    # Wiedergabe des kontinuierlichen Texts hier
        self.stream_timing = None    # (Zeitachse, Beginn) beim Trainer, zum Kürzen beim Abbruch
        self.stream_end = None       # Ende des Tons beim Trainer (time.time())
        self.run_speaker = False  # Ton nur über den Lautsprecher des Trainers
        self.pause_s = PAUSE_DEFAULTS["groups"]
        self.solution_window = None
        self.solution_selected = None  # markierte Nr. in der Auflösung
        self.paper_window = None       # Papierbogen eintragen

        # Teilnehmer
        self.client = None
        self.connected = False
        self.current = None     # empfangene Sequenz
        self.answered = False
        self.replayed = False
        self.play_token = 0
        self.play_start = 0.0
        self.tone_end = 0.0
        self.playing = False
        self.submit_pending = False
        self.enter_time = None
        self.tone_starts = []   # hörbarer Beginn jedes Zeichens (time.time())
        self.tone_ends = []     # hörbares Ende jedes Zeichens
        self.key_times = []     # Zeitpunkt jedes Zeichens im Eingabefeld
        self.typed_so_far = ""
        self.last_result = None
        self.unsure_latency = LATENCY_CAP_S
        self.session_stats = None
        self.run_correct = self.run_total = 0
        self.history = []
        self.paced_results = []  # fester Takt: (Sequenz, Result, wiederholt), gezeigt erst am Ende
        self.stream = None       # laufender kontinuierlicher Text beim Teilnehmer
        self.paper_items = []    # auf Papier mitgeschriebene Sequenzen, abgetippt am Ende
        self.paper_run = None    # (Zeichensatz, Tempo, Farnsworth) des Durchgangs, für die Statistik
        self.trainee_sheet = None
        self.stream_token = 0
        self._band_cache = {}

        self._build_widgets(ScrollableFrame(parent).inner)
        self._show_role()

    # --- Widgets ------------------------------------------------------------------
    def _build_widgets(self, parent):
        theme.hint(parent, wrap=560, text=tr(
            "Üben in der Gruppe im lokalen Netz (Kursraum, Clubheim): Der Trainer gibt vor, alle hören "
            "dieselbe Sequenz über den eigenen Kopfhörer und tippen mit. Übertragen wird nur Text, der "
            "Ton entsteht auf jedem Rechner selbst.")).pack(anchor="w", padx=10, pady=(8, 2))

        role = ttk.Frame(parent)
        role.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Label(role, text=tr("Ich bin:")).pack(side="left", padx=(0, 6))
        self.role_var = tk.StringVar(value=TRAINEE)
        self.role_buttons = [
            ttk.Radiobutton(role, text=tr("Teilnehmer"), value=TRAINEE, variable=self.role_var,
                            command=self._show_role),
            ttk.Radiobutton(role, text=tr("Trainer"), value=TRAINER, variable=self.role_var,
                            command=self._show_role),
        ]
        for button in self.role_buttons:
            button.pack(side="left", padx=(0, 10))

        self.trainer_frame = ttk.Frame(parent)
        self.trainee_frame = ttk.Frame(parent)
        self._build_trainer(self.trainer_frame)
        self._build_trainee(self.trainee_frame)

    def _build_trainer(self, parent):
        box = theme.card(parent, tr("Sitzung"))
        row = ttk.Frame(box)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=tr("Name der Sitzung:")).pack(side="left", padx=(0, 4))
        self.session_var = tk.StringVar(value=tr("Morsekurs"))
        self.session_entry = ttk.Entry(row, textvariable=self.session_var, width=20)
        self.session_entry.pack(side="left")
        ttk.Label(row, text=tr("Port:")).pack(side="left", padx=(12, 4))
        self.port_var = tk.IntVar(value=protocol.DEFAULT_PORT)
        self.port_spin = ttk.Spinbox(row, from_=1024, to=65535, textvariable=self.port_var, width=6)
        self.port_spin.pack(side="left")
        self.open_button = ttk.Button(row, text=tr("Sitzung öffnen"), command=self.toggle_session)
        self.open_button.pack(side="right")
        hint = theme.hint(box, wrap=540, text=tr(
            "Die Teilnehmer finden die Sitzung über „Suchen“ oder geben die Adresse ein. Beim ersten "
            "Öffnen fragt unter Windows eventuell die Firewall – für private Netzwerke zulassen."))
        hint.pack(anchor="w", pady=(2, 0))
        # Adresse und PIN, darunter gesperrte PIN-Versuche und entfernte
        # Teilnehmer (bleibt bis zum nächsten Hinweis); leer ohne Zeile.
        self.session_info_var = tk.StringVar(value="")
        self.notice_var = tk.StringVar(value="")
        for var, options, pad in ((self.session_info_var, {"style": "Score.TLabel"}, (4, 0)),
                                  (self.notice_var, {"foreground": theme.ERROR}, 0)):
            label = ttk.Label(box, textvariable=var, **options)
            var.trace_add("write", lambda *_, v=var, l=label, p=pad: (
                l.pack(anchor="w", pady=p, before=hint) if v.get() else l.pack_forget()))

        options = theme.card(parent, tr("Übung"))
        content = ttk.Frame(options)
        content.pack(fill="x", pady=1)
        ttk.Label(content, text=tr("Inhalt:")).pack(side="left", padx=(0, 4))
        self.content_var = tk.StringVar(value="Gruppen")
        self.count_kind = CONTENTS[self.content_var.get()]
        ChoiceBox(content, self.content_var, CONTENTS, width=14).pack(side="left")
        self.group_len_label = ttk.Label(content, text=tr("Länge:"))
        self.group_len_var = tk.IntVar(value=5)
        self.group_len_spin = ttk.Spinbox(content, from_=GROUP_LEN_RANGE[0], to=GROUP_LEN_RANGE[1],
                                          textvariable=self.group_len_var, width=3)

        count = ttk.Frame(options)
        count.pack(fill="x", pady=1)
        self.count_label = ttk.Label(count, text=tr("Anzahl Sequenzen:"))
        self.count_label.pack(side="left", padx=(0, 4))
        self.count_var = tk.IntVar(value=DEFAULT_COUNT)
        self.count_spin = ttk.Spinbox(count, from_=COUNT_RANGE[0], to=COUNT_RANGE[1], textvariable=self.count_var,
                                      width=4)
        self.count_spin.pack(side="left")
        theme.hint(count, text=tr("(0 = bis Stop)")).pack(side="left", padx=(4, 16))
        ttk.Label(count, text=tr("Antwortzeit:")).pack(side="left", padx=(0, 4))
        self.answer_var = tk.IntVar(value=DEFAULT_ANSWER_S)
        self.answer_spin = ttk.Spinbox(count, from_=ANSWER_RANGE[0], to=ANSWER_RANGE[1],
                                       textvariable=self.answer_var, width=4)
        self.answer_spin.pack(side="left")
        ttk.Label(count, text=tr("s nach dem Ton")).pack(side="left", padx=(4, 0))
        theme.hint(options, wrap=540, text=tr(
            "Die Antwortzeit ist die harte Grenze. Als flüssig zählt eine richtige Antwort nur beim ersten "
            "Hören und innerhalb von 1,5 s plus 0,6 s je Zeichen nach dem Ton – wer länger braucht, zählt "
            "vermutlich mit.")).pack(anchor="w", pady=(0, 2))

        band_row = ttk.Frame(options)
        band_row.pack(fill="x", pady=1)
        ttk.Label(band_row, text=tr("Bandbedingungen:")).pack(side="left", padx=(0, 4))
        self.band_var = tk.StringVar(value="aus")
        self.band_box = ChoiceBox(band_row, self.band_var, BAND_LABELS, width=8)
        self.band_box.pack(side="left")
        self.signs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text=tr("Anfangs- und Schlusszeichen senden (VVV = und +)"),
                        variable=self.signs_var).pack(anchor="w", pady=1)

        self.flow_row = ttk.Frame(options)
        self.flow_row.pack(fill="x", pady=1)
        ttk.Label(self.flow_row, text=tr("Ablauf:")).grid(row=0, column=0, sticky="nw", padx=(0, 4))
        self.flow_var = tk.StringVar(value=WAIT)
        for row, (value, label) in enumerate(((WAIT, tr("Warten auf Antworten")),
                                              (PACED, tr("Fester Takt (Mitschreiben auf Papier)")),
                                              (CONTINUOUS, tr("Kontinuierlich (ohne Pause, feste Dauer)")))):
            ttk.Radiobutton(self.flow_row, text=label, value=value, variable=self.flow_var,
                            command=self._on_flow_change).grid(row=row, column=1, sticky="w")
        self.duration_frame = ttk.Frame(options)
        duration = ttk.Frame(self.duration_frame)
        duration.pack(fill="x")
        ttk.Label(duration, text=tr("Dauer:")).pack(side="left", padx=(0, 4))
        self.duration_var = tk.IntVar(value=net_stream.DEFAULT_DURATION)
        ttk.Spinbox(duration, from_=net_stream.DURATION_RANGE[0], to=net_stream.DURATION_RANGE[1],
                    textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(duration, text=tr("Min.")).pack(side="left", padx=(4, 0))
        theme.hint(self.duration_frame, wrap=540, text=tr(
            "Die Gruppen kommen ohne Pause wie im Reiter „Kontinuierlich“, alle tippen fortlaufend mit, ohne "
            "Enter. Ausgewertet wird am Ende; eine Taste zählt nur, wenn sie zeitlich zum Zeichen passt. Die "
            "Lösungen stehen danach nummeriert unter „Auflösung“.")).pack(
            anchor="w", pady=(0, 2))
        self.pause_frame = ttk.Frame(options)
        pause = ttk.Frame(self.pause_frame)
        pause.pack(fill="x")
        ttk.Label(pause, text=tr("Schreibpause:")).pack(side="left", padx=(0, 4))
        self.pause_var = tk.IntVar(value=PAUSE_DEFAULTS["groups"])
        ttk.Spinbox(pause, from_=PAUSE_RANGE[0], to=PAUSE_RANGE[1], textvariable=self.pause_var, width=4).pack(
            side="left")
        ttk.Label(pause, text=tr("s nach dem Ton, gleich für jede Sequenz")).pack(side="left", padx=(4, 0))
        theme.hint(self.pause_frame, wrap=540, text=tr(
            "Die nächste Sequenz kommt nach Ton und Schreibpause, egal wer geantwortet hat. Lösungen gibt es "
            "erst am Ende unter „Auflösung“ – dort lassen sie sich auch anhören. Besser Blöcke von 20–25 "
            "Sequenzen mit Auflösung dazwischen als „bis Stop“. Wer ohne Rechner mitschreibt, hört den Ton "
            "über die Lautsprecher dieses Rechners. Die Mitschrift lässt sich danach abtippen: am eigenen "
            "Rechner oder hier unter „Papierbogen eintragen“ – gewertet ohne Zeit.")).pack(anchor="w", pady=(0, 2))
        sheet = ttk.Frame(self.pause_frame)
        sheet.pack(fill="x", pady=(0, 2))
        ttk.Button(sheet, text=tr("Antwortbogen drucken"), command=self.print_answer_sheet).pack(side="left")
        self.sheet_var = tk.StringVar(value="")
        theme.hint(sheet, textvariable=self.sheet_var, wrap=400).pack(side="left", padx=(8, 0))

        self.auto_var = tk.BooleanVar(value=True)
        self.auto_check = ttk.Checkbutton(
            options, text=tr("Automatisch weiter, sobald alle geantwortet haben oder die Zeit um ist"),
            variable=self.auto_var)
        self.auto_check.pack(anchor="w", pady=1)
        self.solution_var = tk.BooleanVar(value=True)
        self.solution_check = ttk.Checkbutton(options, text=tr("Lösung vorspielen, wenn sie nicht flüssig richtig war"),
                                              variable=self.solution_var)
        self.solution_check.pack(anchor="w", pady=1)
        self.listen_var = tk.BooleanVar(value=False)
        self.listen_check = ttk.Checkbutton(options, text=tr("Auch an diesem Rechner abspielen"),
                                            variable=self.listen_var)
        self.listen_check.pack(anchor="w", pady=1)
        self.speaker_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text=tr("Ton für alle nur über diesen Rechner (Lautsprecher)"),
                        variable=self.speaker_var, command=self._show_speaker_options).pack(anchor="w", pady=1)
        theme.hint(options, wrap=540, text=tr(
            "Alle hören denselben Lautsprecher, die Teilnehmer-Rechner bleiben stumm und dienen nur zum "
            "Eintippen – ohne Kopfhörer und ohne Versatz zwischen den Rechnern. Die Lösung kommt dann einmal "
            "für alle, wenn jemand sie nicht flüssig hatte.")).pack(anchor="w", pady=(0, 2))

        self.custom_frame = ttk.Frame(options)
        theme.hint(self.custom_frame, wrap=540, text=tr(
            "Eine Zeile je Sequenz, in dieser Reihenfolge; Leerzeichen werden als Wortabstand gesendet, "
            "aber nicht gewertet. Betriebszeichen: + für AR, ( für KN, * für SK, # für BK – "
            "so tippen es auch die Teilnehmer.")).pack(anchor="w", pady=(4, 2))
        self.custom_text = tk.Text(self.custom_frame, height=5, width=50, font=theme.MONO, wrap="none")
        self.custom_text.pack(fill="x")
        self.content_var.trace_add("write", lambda *_: self._on_content_change())
        self._on_content_change()
        self._show_flow_options()
        self._show_speaker_options()

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Start"), style="Accent.TButton", command=self.toggle_run,
                                       state="disabled")
        self.start_button.pack(side="left")
        self.next_button = ttk.Button(controls, text=tr("Weiter (F7)"), command=self.advance, state="disabled")
        self.next_button.pack(side="left", padx=(8, 0))
        self.replay_button = ttk.Button(controls, text=tr("Für alle wiederholen (F6)"), command=self.replay_for_all,
                                        state="disabled")
        self.replay_button.pack(side="left", padx=(8, 0))

        self.trainer_status_var = tk.StringVar(value=tr("Öffne eine Sitzung, damit sich Teilnehmer anmelden können."))
        ttk.Label(parent, textvariable=self.trainer_status_var, style="Status.TLabel", wraplength=560,
                  justify="center").pack(pady=(12, 6))

        table = theme.card(parent, tr("Teilnehmer", context="Mehrzahl"))
        head = self.table_head = ttk.Frame(table)
        head.pack(fill="x", pady=(0, 4))
        self.detach_button = ttk.Button(head, text=tr("In eigenem Fenster"), style="Flat.TButton",
                                        command=self.detach_table)
        self.detach_button.pack(side="right")
        # Gemeinsame Texte beider Ansichten (im Reiter oder im eigenen Fenster).
        self.group_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")
        self.advice_var = tk.StringVar(value="")
        self.advice_step = 0
        self.table_holder = ttk.Frame(table)
        self.table_holder.pack(fill="x")
        self.detached_note = ttk.Frame(table)
        theme.hint(self.detached_note, text=tr("Die Tabelle ist in einem eigenen Fenster.")).pack(side="left")
        ttk.Button(self.detached_note, text=tr("Zurückholen"), command=self.attach_table).pack(side="left", padx=8)
        self.table_window = None
        self._build_table_view(self.table_holder, detached=False)
        export = ttk.Frame(table)
        export.pack(fill="x", pady=(4, 0))
        self.export_button = ttk.Button(export, text=tr("Als CSV speichern"), command=self.export_csv,
                                        state="disabled")
        self.export_button.pack(side="left")
        self.solution_button = ttk.Button(export, text=tr("Auflösung"), command=self.show_solution,
                                          state="disabled")
        self.solution_button.pack(side="left", padx=(8, 0))
        self.paper_button = ttk.Button(export, text=tr("Papierbogen eintragen"), command=self.enter_paper,
                                       state="disabled")
        self.paper_button.pack(side="left", padx=(8, 0))
        self.export_var = tk.StringVar(value="")
        theme.hint(export, textvariable=self.export_var).pack(side="left", padx=(8, 0))

    def _build_table_view(self, parent, detached: bool):
        """Teilnehmertabelle mit Gruppenauswertung, Detailzeile und Tempo-
        Empfehlung. Tk kann Widgets nicht in ein anderes Fenster umhängen,
        daher wird die Ansicht dort neu gebaut; self.tree und
        self.advice_button zeigen immer auf die sichtbare."""
        columns = ("name", "state", "last", "share", "fluent", "latency")
        # Die Texte zuerst von unten: Wird das Fenster knapp, schrumpft die
        # Tabelle (sie scrollt), nicht die Auswertung darunter.
        wrap = 680 if detached else 540
        advice = ttk.Frame(parent)
        advice.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Label(advice, textvariable=self.advice_var, justify="left", wraplength=wrap - 120).pack(side="left")
        theme.hint(parent, textvariable=self.detail_var, wrap=wrap).pack(side="bottom", anchor="w", pady=(4, 0))
        ttk.Label(parent, textvariable=self.group_var, justify="left", wraplength=wrap).pack(
            side="bottom", anchor="w", pady=(6, 0))
        actions = ttk.Frame(parent)
        actions.pack(side="bottom", fill="x", pady=(4, 0))
        self.kick_button = ttk.Button(actions, text=tr("Entfernen"), command=self.kick_selected, state="disabled")
        self.kick_button.pack(side="right")
        rows = ttk.Frame(parent)
        rows.pack(fill="both", expand=detached)
        tree = ttk.Treeview(rows, columns=columns, show="headings", height=12 if detached else TABLE_ROWS[0])
        scrollbar = ttk.Scrollbar(rows, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        headings = {"name": tr("Name"), "state": tr("Status"), "last": tr("Aktuelle Antwort"),
                    "share": tr("Richtig"), "fluent": tr("Flüssig"), "latency": tr("Zeit (s)")}
        widths = {"name": 100, "state": 80, "last": 150, "share": 90, "fluent": 60, "latency": 60}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w" if col in ("name", "last") else "center")
        tree.tag_configure("ok", foreground=theme.OK)
        tree.tag_configure("error", foreground=theme.ERROR)
        tree.tag_configure("gone", foreground=theme.DISABLED)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        tree.bind("<<TreeviewSelect>>", lambda e: (self._show_details(), self._show_kick()))
        self.tree = tree
        self.advice_button = ttk.Button(advice, command=self.apply_advice)

    def detach_table(self):
        """Tabelle in ein eigenes Fenster (viele Teilnehmer, Beamer)."""
        if self.table_window is not None:
            self.table_window.lift()
            return
        selected = self._selected_name()
        window = tk.Toplevel(self.root)
        window.title(tr("Teilnehmer – {session}").format(session=self.session_var.get()))
        window.geometry("720x600")
        window.configure(background=theme.BG)
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        for child in self.table_holder.winfo_children():
            child.destroy()
        self.table_holder.pack_forget()
        self.detached_note.pack(fill="x", pady=2, after=self.table_head)
        self.detach_button.config(state="disabled")
        self._build_table_view(frame, detached=True)
        # Auch im eigenen Fenster steuern (z. B. am Beamer): F5–F7.
        window.bind("<Key>", lambda e: self.on_function_key(e.keysym))
        window.protocol("WM_DELETE_WINDOW", self.attach_table)
        self.table_window = window
        self._refresh_table(selected)

    def attach_table(self):
        """Tabelle zurück in den Reiter; schließt das eigene Fenster."""
        if self.table_window is None:
            return
        selected = self._selected_name()
        self.table_window.destroy()
        self.table_window = None
        self.detached_note.pack_forget()
        self.table_holder.pack(fill="x", after=self.table_head)
        self.detach_button.config(state="normal")
        self._build_table_view(self.table_holder, detached=False)
        self._refresh_table(selected)

    def _build_trainee(self, parent):
        box = theme.card(parent, tr("Verbinden"))
        row = ttk.Frame(box)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=tr("Name/Rufzeichen:")).pack(side="left", padx=(0, 4))
        self.name_var = tk.StringVar(value="")
        self.name_entry = ttk.Entry(row, textvariable=self.name_var, width=14)
        self.name_entry.pack(side="left")
        ttk.Label(row, text=tr("PIN:")).pack(side="left", padx=(12, 4))
        self.pin_var = tk.StringVar(value="")
        self.pin_entry = ttk.Entry(row, textvariable=self.pin_var, width=6)
        self.pin_entry.pack(side="left")

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(4, 1))
        ttk.Label(row, text=tr("Trainer:")).pack(side="left", padx=(0, 4))
        self.address_var = tk.StringVar(value="")
        self.address_box = ttk.Combobox(row, textvariable=self.address_var, width=28)
        self.address_box.pack(side="left")
        self.search_button = ttk.Button(row, text=tr("Suchen"), command=self.search)
        self.search_button.pack(side="left", padx=(6, 0))
        self.connect_button = ttk.Button(row, text=tr("Verbinden"), style="Accent.TButton",
                                         command=self.toggle_connection)
        self.connect_button.pack(side="right")
        theme.hint(box, wrap=540, text=tr(
            "Adresse wie beim Trainer angezeigt, z. B. 192.168.1.20 (anderer Port: 192.168.1.20:7400).")).pack(
            anchor="w", pady=(2, 0))
        self.paper_var = tk.BooleanVar(value=False)
        self.paper_check = ttk.Checkbutton(
            box, text=tr("Im festen Takt auf Papier mitschreiben und am Ende abtippen"), variable=self.paper_var)
        self.paper_check.pack(anchor="w", pady=(4, 0))

        self.trainee_status_var = tk.StringVar(value=tr("Suche den Trainer oder gib seine Adresse ein."))
        ttk.Label(parent, textvariable=self.trainee_status_var, style="Status.TLabel", wraplength=560,
                  justify="center").pack(pady=(14, 6))

        entry_frame = ttk.Frame(parent)
        entry_frame.pack(pady=4)
        self.input_var = tk.StringVar(value="")
        self.input_var.trace_add("write", self._on_input_change)
        self.entry = ttk.Entry(entry_frame, textvariable=self.input_var, width=18, state="disabled",
                               font=theme.MONO_LARGE, justify="center")
        self.entry.pack()
        self.entry.bind("<Return>", self.on_submit)
        theme.hint(entry_frame, text=tr("Nach dem letzten Zeichen automatisch fertig, sonst Enter")).pack(pady=(2, 0))

        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = ttk.Label(parent, textvariable=self.feedback_var, style="Feedback.TLabel",
                                        wraplength=560, justify="center")
        self.feedback_label.pack(pady=(10, 2))
        self.diff_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.diff_var, font=theme.MONO_LARGE, justify="left").pack(pady=(0, 8))

        # Fester Takt: alle Sequenzen mit Lösung erst am Ende, zum Anhören.
        self.results_holder = ttk.Frame(parent)
        self.results_holder.pack(fill="x")
        self.results_card = theme.card(self.results_holder, tr("Auflösung"))
        self.results_card.pack_forget()
        columns = ("n", "sent", "typed", "mark")
        self.results_tree = ttk.Treeview(self.results_card, columns=columns, show="headings", height=8)
        for col, heading, width in (("n", tr("Nr."), 40), ("sent", tr("gesendet"), 170),
                                    ("typed", tr("getippt"), 170), ("mark", "", 60)):
            self.results_tree.heading(col, text=heading)
            self.results_tree.column(col, width=width, anchor="w" if col in ("sent", "typed") else "center")
        self.results_tree.tag_configure("ok", foreground=theme.OK)
        self.results_tree.tag_configure("error", foreground=theme.ERROR)
        self.results_tree.pack(fill="x")
        for sequence in ("<Double-Button-1>", "<Return>", "<space>"):
            self.results_tree.bind(sequence, lambda e: self.play_result() or "break")
        theme.hint(self.results_card, text=tr("Doppelklick oder Leertaste: noch einmal anhören")).pack(
            anchor="w", pady=(2, 0))
        # Papier: Mitschrift nach dem Durchgang abtippen.
        self.paper_card = theme.card(self.results_holder, tr("Mitschrift abtippen"))
        self.paper_card.pack_forget()
        theme.hint(self.paper_card, wrap=540, text=tr(
            "Je Nummer die Zeile vom Zettel, leer = verpasst. Enter springt zur nächsten Nummer. Gewertet wird "
            "ohne Zeit, also nicht als flüssig.")).pack(anchor="w", pady=(0, 4))
        self.trainee_sheet_holder = ttk.Frame(self.paper_card)
        self.trainee_sheet_holder.pack(anchor="w")
        ttk.Button(self.paper_card, text=tr("Auswerten"), style="Accent.TButton", command=self.submit_paper).pack(
            anchor="w", pady=(6, 0))

        self.stats_panel = StatsPanel(parent)
        history = theme.card(parent, tr("Verlauf (letzte {n})").format(n=HISTORY_LEN))
        self.history_var = tk.StringVar(value="")
        ttk.Label(history, textvariable=self.history_var, font=theme.MONO, wraplength=540).pack(anchor="w")

    def _show_role(self):
        if self.role_var.get() == TRAINER:
            self.trainee_frame.pack_forget()
            self.trainer_frame.pack(fill="x")
        else:
            self.trainer_frame.pack_forget()
            self.trainee_frame.pack(fill="x")

    def _lock_role(self):
        busy = self.server is not None or self.client is not None
        for button in self.role_buttons:
            button.config(state="disabled" if busy else "normal")

    def _on_content_change(self):
        kind = CONTENTS.get(self.content_var.get())
        self.pause_var.set(PAUSE_DEFAULTS.get(kind, PAUSE_DEFAULTS["groups"]))
        # Zwischen Sequenzen und QSOs passt die Anzahl nicht: Vorgabe setzen.
        if (kind == "qso") != (self.count_kind == "qso"):
            self.count_var.set(DEFAULT_QSO_COUNT if kind == "qso" else DEFAULT_COUNT)
        self.count_kind = kind
        self._show_content_options()

    def _on_flow_change(self):
        """Wer auf Papier schreibt, hat keinen eigenen Rechner und hört den
        Ton nur über den Lautsprecher des Trainers: beim Umschalten auf den
        festen Takt daher gleich mit abspielen (abwählbar)."""
        if self.flow_var.get() == PACED:
            self.listen_var.set(True)
        self._show_flow_options()

    def _show_speaker_options(self):
        """Ton nur über den Lautsprecher: dann spielt dieser Rechner immer."""
        if self.speaker_var.get():
            self.listen_var.set(True)
        self.listen_check.config(state="disabled" if self.speaker_var.get() else "normal")

    def _show_flow_options(self):
        """Im festen Takt gelten Schreibpause statt Antwortzeit, und es gibt
        zwischendurch keine Lösung (also auch kein Vorspielen)."""
        paced = self.flow_var.get() == PACED
        continuous = self.flow_var.get() == CONTINUOUS
        if paced:
            self.pause_frame.pack(fill="x", after=self.flow_row)
        else:
            self.pause_frame.pack_forget()
        if continuous:
            self.duration_frame.pack(fill="x", after=self.flow_row)
        else:
            self.duration_frame.pack_forget()
        for widget in (self.answer_spin, self.auto_check, self.solution_check):
            widget.config(state="disabled" if paced or continuous else "normal")
        self.count_spin.config(state="disabled" if continuous else "normal")

    @property
    def hiding(self) -> bool:
        """Durchgang im festen Takt oder kontinuierlich: nichts zeigen, was
        Lösungen verrät."""
        return self.run_active and (self.run_paced or self.run_continuous)

    def _show_content_options(self):
        kind = CONTENTS.get(self.content_var.get())
        # QSO-Klartext kommt in Abschnitten; gezählt werden ganze QSOs.
        self.count_label.config(text=tr("Anzahl QSOs:") if kind == "qso" else tr("Anzahl Sequenzen:"))
        if kind == "groups":
            self.group_len_label.pack(side="left", padx=(12, 4))
            self.group_len_spin.pack(side="left")
        else:
            self.group_len_label.pack_forget()
            self.group_len_spin.pack_forget()
        if kind == "custom" and not self.hiding:
            self.custom_frame.pack(fill="x", pady=(2, 0))
        else:
            self.custom_frame.pack_forget()

    # --- Eingänge aus dem Netz -------------------------------------------------------
    def _after(self, ms: int, callback):
        """root.after, das beim Schließen des Fensters abgebrochen wird."""
        def run():
            self.after_ids.discard(after_id)
            callback()
        after_id = self.root.after(ms, run)
        self.after_ids.add(after_id)

    def _ensure_polling(self):
        if self.poll_id is None:
            self.poll_id = self.root.after(POLL_MS, self._poll)

    def _poll(self):
        self.poll_id = None
        if self.found is not None:
            found, self.found = self.found, None
            self._show_found(found)
        if self.server is not None:
            events = self.server.poll()
            for event in events:
                self._handle_server_event(event)
            if events:
                # Einmal je Abruf, nicht je Nachricht: Eine Flut von Antworten
                # soll die Oberfläche nicht lahmlegen.
                self._after_server_events()
            if self.run_active and self.run_continuous and self.item is not None:
                self._show_progress()
            if self.item_open and self.deadline is not None and time.time() >= self.deadline:
                self.close_item()
                if self.run_paced:
                    self.next_item()
        if self.client is not None:
            for event in self.client.poll():
                self._on_client_event(event)
        if self.server is not None or self.client is not None or self.searching:
            self.poll_id = self.root.after(POLL_MS, self._poll)

    @property
    def searching(self):
        return str(self.search_button.cget("state")) == "disabled"

    # --- Trainer ------------------------------------------------------------------
    def toggle_session(self):
        if self.server is None:
            self.open_session()
        else:
            self.close_session()

    def open_session(self):
        try:
            port = self.port_var.get()
        except tk.TclError:
            port = -1
        if not 1024 <= port <= 65535:
            self.trainer_status_var.set(tr("Ungültiger Port (1024–65535)."))
            return
        name = protocol.clean_name(self.session_var.get()) or tr("Morsekurs")
        server = TrainerServer(name, make_pin(), self.version)
        try:
            server.start(port)
        except OSError as exc:
            self.trainer_status_var.set(tr("Port {port} lässt sich nicht öffnen: {error}").format(port=port, error=exc))
            return
        self.server = server
        self.board = Scoreboard()
        address = protocol.local_address()
        if port != protocol.DEFAULT_PORT:
            address += f":{port}"
        self.session_info_var.set(tr("Adresse {address} · PIN {pin}").format(address=address, pin=server.pin))
        self.open_button.config(text=tr("Sitzung schließen"))
        self.start_button.config(state="normal")
        self.solution_button.config(state="normal")
        for widget in (self.session_entry, self.port_spin):
            widget.config(state="disabled")
        self.trainer_status_var.set(tr("Warte auf Teilnehmer…"))
        self.export_var.set("")
        self._lock_role()
        self._refresh_table()
        self._ensure_polling()

    def close_session(self):
        if self.run_active:
            self.stop_run()
        if self.server is not None:
            self.server.stop()
        self.server = None
        self.session_info_var.set("")
        self.notice_var.set("")
        self.open_button.config(text=tr("Sitzung öffnen"))
        for widget in (self.start_button, self.next_button, self.replay_button):
            widget.config(state="disabled")
        for widget in (self.session_entry, self.port_spin):
            widget.config(state="normal")
        self.trainer_status_var.set(tr("Sitzung geschlossen."))
        self._lock_role()
        self._refresh_table()
        self.session_closed()

    def _on_server_event(self, event):
        self._handle_server_event(event)
        self._after_server_events()

    def _handle_server_event(self, event):
        kind, name = event[0], event[1]
        if kind == "locked":
            self.notice_var.set(tr("Zu oft falsche PIN von {host} – 1 Minute gesperrt.").format(host=name))
        elif kind == "join":
            self.board.add_participant(name)
        elif kind == "answer" and self.board is not None:
            message = event[2]
            self.board.record(name, message.get("n"), message.get("typed"), message.get("latency"))
        elif kind == "paper" and self.board is not None and not self.run_active:
            # Nach dem Durchgang abgetippt; währenddessen gehört es nicht hierher.
            self.board.record_paper(name, event[2].get("n"), event[2].get("typed"))

    def _after_server_events(self):
        if self.item_open and not self.run_paced and self._all_answered():
            self.close_item()
        self._refresh_table()
        self._show_progress()

    def _all_answered(self) -> bool:
        """Alle, die beim Senden dabei und noch verbunden sind, haben
        geantwortet. Ohne Teilnehmer läuft die Antwortzeit ab (Probelauf)."""
        n = self.item["n"]
        return bool(self.board.expected[n] & set(self.server.names())) and not self._waiting_for()

    def _waiting_for(self):
        """Namen, die zur offenen Sequenz noch antworten können (verbunden
        und beim Senden dabei, noch keine Antwort)."""
        n = self.item["n"]
        return (self.board.expected[n] & set(self.server.names())) - self.board.answered(n)

    def _someone_not_fluent(self) -> bool:
        """Mindestens einer, der beim Senden dabei war, hatte die offene
        Sequenz nicht flüssig richtig (oder gar nicht beantwortet)."""
        n = self.item["n"]
        return any(result is None or not result.fluent
                   for result in (self.board.answers.get(name, {}).get(n) for name in self.board.expected[n]))

    def toggle_run(self):
        if self.run_active:
            self.stop_run()
        else:
            self.start_run()

    def start_run(self):
        if self.server is None:
            return
        kind = CONTENTS.get(self.content_var.get(), "groups")
        try:
            count, self.answer_s = self.count_var.get(), self.answer_var.get()
            group_len, pause_s = self.group_len_var.get(), self.pause_var.get()
            self.wpm_var.get()
            duration = self.duration_var.get()
        except tk.TclError:
            self.trainer_status_var.set(tr("Ungültige Anzahl, Antwortzeit, Schreibpause oder Gruppenlänge!"))
            return
        if not (COUNT_RANGE[0] <= count <= COUNT_RANGE[1] and ANSWER_RANGE[0] <= self.answer_s <= ANSWER_RANGE[1]
                and GROUP_LEN_RANGE[0] <= group_len <= GROUP_LEN_RANGE[1]
                and PAUSE_RANGE[0] <= pause_s <= PAUSE_RANGE[1]
                and net_stream.DURATION_RANGE[0] <= duration <= net_stream.DURATION_RANGE[1]):
            self.trainer_status_var.set(tr("Ungültige Anzahl, Antwortzeit, Schreibpause oder Gruppenlänge!"))
            return
        charset = normalize(self.charset_var.get())
        continuous = self.flow_var.get() == CONTINUOUS
        if continuous and kind == "custom":
            self.trainer_status_var.set(tr("Kontinuierlich geht nicht mit eigenem Text – Gruppen wählen."))
            return
        if kind == "custom":
            lines = [" ".join(line.upper().split()) for line in self.custom_text.get("1.0", "end").splitlines()]
            self.custom_items = [line[:protocol.TEXT_MAX] for line in lines if normalize(line)]
            if not self.custom_items:
                self.trainer_status_var.set(tr("Kein eigener Text – eine Zeile je Sequenz eintragen."))
                return
            self.source = None
            self.planned = len(self.custom_items)
            charset = "".join(sorted(set(normalize("".join(self.custom_items)))))
        else:
            self.source = ItemSource(kind, charset, group_len)
            problem = self.source.problem()
            if problem:
                self.trainer_status_var.set(problem)
                return
            self.custom_items = []
            self.planned = count
            if kind == "qso" and not continuous:
                self.custom_items = [text for _ in range(count) for text in qso_sections(charset)]
                self.planned = len(self.custom_items)
        self.board = Scoreboard()
        for name in self.server.names():
            self.board.add_participant(name)
        self.run_active = True
        self.run_paced = self.flow_var.get() == PACED
        self.run_continuous = continuous
        self.duration_s = duration * 60
        self.run_speaker = self.speaker_var.get()
        self.run_signs = self.signs_var.get()
        self.pause_s = pause_s
        self.run_token += 1
        self.run_started = time.monotonic()
        self.item_n = 0
        self.item = None
        self.solution_selected = None
        self._show_content_options()
        self.start_button.config(text=tr("Stop"))
        self.next_button.config(state="disabled" if continuous else "normal")
        self.export_button.config(state="disabled")
        self.paper_button.config(state="disabled")
        self.close_paper()
        self.export_var.set("")
        wpm, fw, preset = self.wpm_var.get(), self.farnsworth_wpm(), BAND_LABELS.get(self.band_var.get())
        self.server.broadcast({"type": "start", "kind": kind, "charset": charset, "wpm": wpm, "fw": fw,
                               "signs": self.run_signs, "band": preset, "silent": self.run_speaker})
        if not self.run_signs:
            self.next_item()
            return
        # Erst VVV = bei allen, dann die erste Sequenz.
        if self.listen_var.get() or self.run_speaker:
            self._play_signs(START_TEXT + " ", wpm, fw, preset)
        self.trainer_status_var.set(tr("Achtung: {text}").format(text=START_TEXT))
        token = self.run_token
        delay = AUDIO_LATENCY + sequence_seconds(START_TEXT + " ", wpm, fw, preset)
        self._after(int(delay * 1000), lambda: self.run_active and token == self.run_token and self.item is None
                    and self.next_item())

    def next_item(self):
        if not self.run_active:
            return
        if self.run_continuous:
            if self.item is None:
                self._start_stream()
            return
        if self.planned and self.item_n >= self.planned:
            self.stop_run()
            return
        if not self.custom_items and self.source is not None and self.source.kind == "qso":
            self.custom_items = qso_sections(self.source.charset)  # bis Stop: nächstes QSO
        if self.custom_items:
            text = self.custom_items.pop(0)
        else:
            text = self.source.next()[0]
        try:
            wpm = self.wpm_var.get()
        except tk.TclError:
            wpm = self.item["wpm"] if self.item else 20
        self.item_n += 1
        self.item = {"type": "item", "n": self.item_n, "text": text, "wpm": wpm, "fw": self.farnsworth_wpm(),
                     "band": BAND_LABELS.get(self.band_var.get()), "paced": self.run_paced,
                     "silent": self.run_speaker}
        self.board.add_item(self.item_n, text, self.server.names(), wpm, self.item["fw"])
        self.server.broadcast(self.item)
        self._open_item(self.item)
        if self.listen_var.get() or self.run_speaker:
            self._play_here(self.item)

    def _start_stream(self):
        """Kontinuierlich: alle Gruppen auf einmal an alle, hier abspielen,
        wenn gewünscht; nach Ton und Nachtippzeit ist der Durchgang zu Ende."""
        wpm, fw = self.wpm_var.get(), self.farnsworth_wpm()
        groups = [group[:protocol.TEXT_MAX]
                  for group in net_stream.make_groups(self.source, self.duration_s, wpm, fw)]
        names = self.server.names()
        for n, group in enumerate(groups, start=1):
            self.board.add_item(n, group, names, wpm, fw)
        self.item_n = len(groups)
        self.planned = len(groups)
        self.item = {"type": "stream", "n": len(groups), "text": groups[-1], "wpm": wpm, "fw": fw, "band": None}
        preset = BAND_LABELS.get(self.band_var.get())
        conditions = self._band(preset, self._freq()) if preset else None  # vor dem Senden, dauert etwas
        self.server.broadcast({"type": "stream", "groups": groups, "wpm": wpm, "fw": fw, "band": preset,
                               "silent": self.run_speaker})
        entries, seconds = net_stream.timeline(groups, wpm, fw)
        start = time.time() + AUDIO_LATENCY + net_stream.lead_seconds(preset)
        if self.listen_var.get() or self.run_speaker:
            self.stream_player = net_stream.Player(groups, wpm, self._freq(), fw, conditions)
            start = self.stream_player.start
        self.stream_timing = (entries, start)
        self.stream_end = start + seconds
        token = self.run_token
        rest = seconds + net_stream.lead_seconds(preset) + net_stream.tail_seconds(preset)
        self._after(int((AUDIO_LATENCY + rest + net_stream.FINISH_GRACE_SECONDS) * 1000),
                    lambda: self.run_active and token == self.run_token and self.stop_run())
        self._refresh_table()
        self._show_progress()
        self._refresh_solution()

    def _stop_stream(self):
        """Wiedergabe beenden; bei vorzeitigem Stop die Gruppen, die noch
        nicht angefangen hatten, aus der Wertung nehmen (wie die Teilnehmer)."""
        if self.stream_player is not None:
            self.stream_player.stop()
            if self.stream_player.error:
                self.trainer_status_var.set(self.stream_player.error)
            self.stream_player = None
        if self.stream_timing is not None and self.board is not None:
            entries, start = self.stream_timing
            if time.time() < self.stream_end:
                kept = net_stream.kept_groups(entries, start, time.time())
                self.board.drop_items([n for n in list(self.board.items) if n - 1 not in kept])
                self.item_n = len(self.board.items)
        self.stream_timing = None
        self.stream_end = None

    def _open_item(self, item):
        self.item_open = True
        self.replay_button.config(state="normal")
        seconds = sequence_seconds(item["text"], item["wpm"], item["fw"], item["band"])
        self.deadline = time.time() + AUDIO_LATENCY + seconds + (self.pause_s if self.run_paced else self.answer_s)
        self._refresh_table()
        self._show_progress()
        self._refresh_solution()

    def _play_here(self, item, solution=False):
        freq = self._freq()
        samples = build_text(item["text"], item["wpm"], freq, item["fw"])
        if item["band"]:
            samples, _ = band.apply_preset(self._band(item["band"], freq), samples)
        try:
            audio.play(samples)
        except audio.AudioError as exc:
            if not solution and not self.run_speaker:
                self.listen_var.set(False)
            self.trainer_status_var.set(str(exc))

    def close_item(self):
        if not self.item_open:
            return
        self.item_open = False
        self.deadline = None
        self.replay_button.config(state="disabled")
        # Im festen Takt keine Lösung bis zum Ende, und weiter geht es sofort.
        reveal = not self.run_paced
        solution = reveal and self.solution_var.get()
        self.server.broadcast({"type": "close", "n": self.item["n"], "solution": solution, "reveal": reveal})
        if solution and self.run_speaker and self._someone_not_fluent():
            # Über den Lautsprecher geht es nicht einzeln: einmal für alle.
            self._play_here(dict(self.item, band=None), solution=True)
        self._refresh_table()
        self._show_progress()
        if reveal and self.auto_var.get():
            token = self.run_token
            delay = NEXT_DELAY_MS
            if solution:
                # Zeit, die Lösung beim Teilnehmer noch einmal zu hören.
                delay += int((sequence_seconds(self.item["text"], self.item["wpm"], self.item["fw"], None)
                              + AUDIO_LATENCY) * 1000)
            self._after(delay, lambda: self.run_active and token == self.run_token and not self.item_open
                            and self.next_item())

    def advance(self):
        """Knopf „Weiter“: offene Sequenz schließen und gleich die nächste."""
        if not self.run_active or self.run_continuous:
            return
        self.run_token += 1  # eine schon geplante nächste Sequenz verfällt
        self.close_item()
        self.run_token += 1
        self.next_item()

    def replay_for_all(self):
        if not self.item_open:
            return
        # Schon eingegangene Antworten zählen noch zum ersten Hören.
        for event in self.server.poll():
            self._on_server_event(event)
        if not self.item_open:
            return  # damit haben alle geantwortet
        self.board.mark_replayed(self.item["n"])
        self.server.broadcast({"type": "replay", "n": self.item["n"]})
        self.deadline += sequence_seconds(self.item["text"], self.item["wpm"], self.item["fw"], self.item["band"])
        if self.listen_var.get() or self.run_speaker:
            self._play_here(self.item)

    def stop_run(self):
        self.close_item()
        if self.run_continuous:
            self._stop_stream()
        self.run_active = False
        self.run_token += 1
        if self.server is not None:
            wpm = self.item["wpm"] if self.item else self.wpm_var.get()
            preset = BAND_LABELS.get(self.band_var.get())
            self.server.broadcast({"type": "end", "signs": self.run_signs, "wpm": wpm, "band": preset,
                                   "silent": self.run_speaker})
            if self.run_signs and (self.listen_var.get() or self.run_speaker):
                self._play_signs(END_TEXT, wpm, None, preset)
            self._log_led_run(wpm)
        self.start_button.config(text=tr("Start"))
        self.next_button.config(state="disabled")
        self.export_button.config(state="normal" if self.board is not None and self.board.items else "disabled")
        self.paper_button.config(state=self.export_button.cget("state"))
        status = tr("Durchgang beendet: {n} Sequenzen.").format(n=self.item_n)
        if (self.run_paced or self.run_continuous) and self.item_n:
            status += " " + tr("Die Lösungen stehen unter „Auflösung“.")
        self.trainer_status_var.set(status)
        self._show_content_options()
        self._refresh_table()
        self._refresh_solution()

    def _log_led_run(self, wpm):
        """Geleiteten Durchgang vermerken, wenn jemand mitgemacht hat – nur
        für das Diplom Clubabend (zählt ab 10 Min. am Tag). Der Trainer tippt
        nicht mit: keine Statistik, keine Übungszeit, nicht im Verlauf."""
        if not self.item_n or self.board is None or not any(self.board.expected.values()):
            return
        duration_s = round(time.monotonic() - self.run_started, 1)
        stats.log_result(self.session_mode, 0, 0, wpm, role=TRAINER, participants=len(self.board.names),
                         duration_s=duration_s)

    def _show_progress(self):
        if not self.run_active or self.item is None:
            if self.server is not None and not self.run_active and self.item is None:
                count = len(self.server.names())
                self.trainer_status_var.set(
                    tr("Warte auf Teilnehmer…") if not count else
                    tr("{n} Teilnehmer verbunden. Start, wenn alle da sind.").format(n=count))
            return
        if self.run_continuous:
            remaining = max(int(self.stream_end - time.time()), 0) if self.stream_end else 0
            self.trainer_status_var.set(tr("Kontinuierlich – noch {time}").format(
                time=f"{remaining // 60}:{remaining % 60:02d}") if remaining else tr("Nachtippen…"))
            return
        n = self.item["n"]
        of = tr(" von {total}").format(total=self.planned) if self.planned else ""
        if self.run_paced:
            # Kein Text und keine Zahl der Antworten: Am Beamer liest jeder mit.
            self.trainer_status_var.set(tr("Nr. {n}{of}").format(n=n, of=of))
            return
        text = tr("Nr. {n}{of}: {text}").format(n=n, of=of, text=display_text(self.item["text"]))
        if self.item_open:
            waiting = len(self._waiting_for())
            present = len(self.board.expected[n] & set(self.server.names()))
            text += " – " + tr("{done} von {total} haben geantwortet").format(done=present - waiting, total=present)
        elif not self.auto_var.get():
            text += " – " + tr("weiter mit „Weiter“")
        self.trainer_status_var.set(text)

    def _refresh_table(self, selected=None):
        selected = selected or self._selected_name()
        for row in self.tree.get_children():
            self.tree.delete(row)
        if self.board is None:
            self.group_var.set("")
            self.detail_var.set("")
            self._show_advice()
            return
        online = set(self.server.names()) if self.server is not None else set()
        n = self.item["n"] if self.item is not None else None
        hiding = self.hiding
        for name in self.board.names:
            data = self.board.summary(name)
            state = tr("verbunden") if name in online else tr("getrennt")
            last, tag = "", "gone" if name not in online else ""
            if hiding:
                # Nur ob etwas eingegangen ist; richtig/falsch erst am Ende.
                if n is not None and name in self.board.expected.get(n, ()):
                    last = tr("eingegangen") if n in self.board.answers[name] else "…" if self.item_open else ""
            elif n is not None and name in self.board.expected.get(n, ()):
                result = self.board.answers[name].get(n)
                if result is not None:
                    last = ("✓ " if result.correct else "✗ ") + (display_text(result.typed) or "–")
                    if result.correct and result.replayed:
                        last += " " + tr("(wiederholt)")
                    elif result.correct and result.slow:
                        last += " " + tr("(langsam)")
                    tag = "ok" if result.correct else "error"
                elif self.item_open:
                    last = "…"
                else:
                    last = tr("keine Antwort")
                    tag = "error"
            share = ""
            if data["chars_total"] and not hiding:
                share = f"{data['chars_correct'] / data['chars_total']:.0%} ({data['correct_items']}/{data['items']})"
            fluent = f"{data['fluent_items']}/{data['items']}" if data["items"] and not hiding else ""
            if name in self.board.paper and not hiding:
                fluent = tr("Papier")
            latency = number(data["latency"], 1) if data["latency"] is not None and not hiding else ""
            row = self.tree.insert("", "end", values=(name, state, last, share, fluent, latency),
                                   tags=(tag,) if tag else ())
            if name == selected:
                self.tree.selection_set(row)
        if self.table_window is None:
            # Im Reiter wächst die Tabelle mit, darüber hinaus scrollt sie.
            self.tree.configure(height=min(max(len(self.board.names), TABLE_ROWS[0]), TABLE_ROWS[1]))
        self.group_var.set("" if hiding else self._group_text())
        self._show_details()
        self._show_kick()
        self._show_advice()

    def _show_kick(self):
        name = self._selected_name()
        online = self.server is not None and name in self.server.names()
        self.kick_button.config(state="normal" if online else "disabled")

    def kick_selected(self):
        """Gewählten Teilnehmer hinauswerfen; sein Rechner kann sich in
        dieser Sitzung nicht wieder anmelden."""
        name = self._selected_name()
        if self.server is None or name is None or name not in self.server.names():
            return
        if not messagebox.askyesno(
                tr("Teilnehmer entfernen"),
                tr("{name} entfernen? Dieser Rechner kann sich bis zum Schließen der Sitzung nicht wieder "
                   "anmelden.").format(name=name),
                parent=self.tree.winfo_toplevel()):
            return
        if self.server.kick(name):
            self.notice_var.set(tr("{name} entfernt.").format(name=name))
        for event in self.server.poll():
            self._handle_server_event(event)
        self._after_server_events()

    def _selected_name(self):
        selection = self.tree.selection()
        return str(self.tree.item(selection[0])["values"][0]) if selection else None

    def _show_details(self):
        """Fehler und schwache Zeichen des ausgewählten Teilnehmers – im
        Gruppenschnitt geht ein Einzelner mit S/H-Problem sonst unter."""
        name = self._selected_name()
        if self.hiding:
            self.detail_var.set(tr("Auswertung nach dem Durchgang (fester Takt)."))
            return
        if name is None or self.board is None:
            self.detail_var.set(tr("Einen Teilnehmer anklicken, um seine Fehler zu sehen.")
                                if self.board is not None and self.board.names else "")
            return
        confusions = format_confusions(self.board.confusions(name=name)) or "–"
        weak = format_weak(self.board.weak_chars(name=name)) or "–"
        self.detail_var.set(tr("{name}: Fehler {confusions} · schwächste Zeichen {weak}").format(
            name=name, confusions=confusions, weak=weak))

    def _show_advice(self):
        """Tempo-Empfehlung aus den letzten Sequenzen im aktuellen Tempo."""
        advice = self.board.tempo_advice() if self.board is not None and not self.hiding else None
        self.advice_step = 0
        self.advice_button.pack_forget()
        if advice is None:
            self.advice_var.set("")
            return
        (wpm, fw), share, step = advice
        text = tr("{tempo}: {share:.0%} der Sequenzen flüssig").format(tempo=tempo.label(wpm, fw), share=share)
        if step > 0:
            text += " – " + tr("Tempo kann steigen.")
        elif step < 0:
            text += " – " + tr("Tempo lieber senken.")
        else:
            text += " – " + tr("Tempo passt.")
        self.advice_var.set(text)
        try:
            current = (self.wpm_var.get(), self.farnsworth_wpm())
        except tk.TclError:
            current = None
        # Nur anbieten, solange die Kopfleiste noch dieses Tempo zeigt.
        if step and self.adjust_tempo is not None and current == (wpm, fw):
            self.advice_step = step
            self.advice_button.config(text=tr("+1 WPM effektiv") if step > 0 else tr("−1 WPM effektiv"))
            self.advice_button.pack(side="right")

    def apply_advice(self):
        if not self.advice_step or self.adjust_tempo is None:
            return
        change = self.adjust_tempo(self.advice_step)
        if change is not None:
            self.trainer_status_var.set(tr("Tempo {before} → {after}, ab der nächsten Sequenz.").format(
                before=change[0], after=change[1]))
        self._show_advice()

    def _group_text(self) -> str:
        accuracy = self.board.accuracy()
        if accuracy is None:
            return ""
        lines = [tr("Gruppe: {share:.0%} der Zeichen richtig, {fluent:.0%} der Sequenzen flüssig").format(
            share=accuracy, fluent=self.board.fluency() or 0)]
        confusions = self.board.confusions()
        if confusions:
            lines.append(tr("Häufigste Fehler: ") + format_confusions(confusions))
        weak = self.board.weak_chars()
        if weak:
            lines.append(tr("Schwächste Zeichen: ") + format_weak(weak))
        return "\n".join(lines)

    def show_solution(self):
        """Auflösung in einem eigenen Fenster (Beamer): während des
        Durchgangs nur die laufende Nummer, danach alle Lösungen nummeriert
        zum Vergleichen mit dem Zettel. Klick, Pfeiltasten und Leertaste
        spielen eine Lösung hier noch einmal ab (ohne Störungen)."""
        if self.solution_window is not None:
            self.solution_window.lift()
            return
        window = tk.Toplevel(self.root)
        window.title(tr("Auflösung – {session}").format(session=self.session_var.get()))
        window.geometry("900x600")
        window.configure(background=theme.BG)
        family = tkfont.nametofont("TkFixedFont", root=window).actual("family")
        self.solution_font = tkfont.Font(root=window, family=family, size=SOLUTION_FONT[0])
        self.solution_big_font = tkfont.Font(root=window, family=family, size=3 * SOLUTION_FONT[0], weight="bold")
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="A−", width=3, command=lambda: self.zoom_solution(-1)).pack(side="left")
        ttk.Button(bar, text="A+", width=3, command=lambda: self.zoom_solution(1)).pack(side="left", padx=(4, 0))
        self.copy_button = ttk.Button(bar, text=tr("Kopieren"), command=self.copy_solution)
        self.copy_button.pack(side="left", padx=(12, 0))
        self.solution_note_var = tk.StringVar(value="")
        theme.hint(bar, textvariable=self.solution_note_var).pack(side="left", padx=(12, 0))
        self.solution_number_var = tk.StringVar(value="")
        self.solution_number = ttk.Frame(frame)
        tk.Label(self.solution_number, textvariable=self.solution_number_var, font=self.solution_big_font,
                 background=theme.BG, foreground=theme.TEXT).pack(expand=True, pady=(40, 10))
        tk.Label(self.solution_number, font=self.solution_font, background=theme.BG, foreground=theme.TEXT,
                 wraplength=800, text=tr("Verpasst? Lücke lassen und bei der nächsten Nummer weiterschreiben.")).pack()
        self.solution_list = ttk.Frame(frame)
        text = tk.Text(self.solution_list, font=self.solution_font, wrap="none", cursor="arrow", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(self.solution_list, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.tag_configure("selected", background=theme.SELECT)
        self.solution_text_widget = text
        window.bind("<Key>", self._on_solution_key)
        window.protocol("WM_DELETE_WINDOW", self.close_solution)
        self.solution_window = window
        self._refresh_solution()
        window.focus_force()

    def close_solution(self):
        if self.solution_window is not None:
            self.solution_window.destroy()
        self.solution_window = None

    def _solution_cells(self):
        return solution_cells(self.board) if self.board is not None else []

    def _refresh_solution(self):
        if self.solution_window is None:
            return
        self.copy_button.config(state="disabled" if self.run_active else "normal")
        if self.run_active:
            n = self.item["n"] if self.item is not None else 0
            of = tr(" von {total}").format(total=self.planned) if self.planned else ""
            self.solution_number_var.set(tr("Nr. {n}{of}").format(n=n, of=of) if n and not self.run_continuous
                                         else "")
            self.solution_note_var.set("")
            self.solution_list.pack_forget()
            self.solution_number.pack(fill="both", expand=True)
            return
        self.solution_number.pack_forget()
        self.solution_list.pack(fill="both", expand=True)
        text = self.solution_text_widget
        text.config(state="normal")
        text.delete("1.0", "end")
        cells = self._solution_cells()
        if not cells:
            text.insert("end", tr("Noch keine Sequenzen."))
        for row in solution_rows(cells, solution_columns(len(cells))):
            for i, (n, cell) in enumerate(row):
                if i:
                    text.insert("end", "    ")
                tag = f"n{n}"
                text.insert("end", cell, (tag,))
                text.tag_bind(tag, "<Button-1>", lambda e, n=n: self.select_solution(n, play=True))
            text.insert("end", "\n")
        text.config(state="disabled")
        self.solution_note_var.set(tr("Klick oder Leertaste: anhören · ↻ = für alle wiederholt") if cells else "")
        if self.solution_selected is not None:
            self.select_solution(self.solution_selected)

    def select_solution(self, n, play=False):
        """Markiert Lösung Nr. `n`; `play`: hier noch einmal abspielen."""
        if self.solution_window is None or self.board is None or n not in self.board.items:
            return
        self.solution_selected = n
        text = self.solution_text_widget
        text.tag_remove("selected", "1.0", "end")
        ranges = text.tag_ranges(f"n{n}")
        if ranges:
            text.tag_add("selected", ranges[0], ranges[1])
            text.see(ranges[0])
        if play:
            wpm, fw = self.board.tempos.get(n, (None, None))
            self._play_here({"text": self.board.items[n], "wpm": wpm or 20, "fw": fw, "band": None}, solution=True)

    def _on_solution_key(self, event):
        key = event.keysym
        if key in ("F5", "F6", "F7"):
            self.on_function_key(key)
        elif key in ("plus", "KP_Add"):
            self.zoom_solution(1)
        elif key in ("minus", "KP_Subtract"):
            self.zoom_solution(-1)
        elif key in ("Up", "Down", "Left", "Right", "space", "Return") and not self.run_active:
            numbers = sorted(self.board.items) if self.board is not None else []
            if not numbers:
                return
            if key in ("space", "Return"):
                self.select_solution(self.solution_selected or numbers[0], play=True)
                return
            height = -(-len(numbers) // solution_columns(len(numbers)))
            step = {"Up": -1, "Down": 1, "Left": -height, "Right": height}[key]
            if self.solution_selected in numbers:
                index = min(max(numbers.index(self.solution_selected) + step, 0), len(numbers) - 1)
            else:
                index = 0
            self.select_solution(numbers[index])

    def zoom_solution(self, direction: int):
        size, low, high, step = SOLUTION_FONT
        size = min(max(self.solution_font.cget("size") + direction * step, low), high)
        self.solution_font.configure(size=size)
        self.solution_big_font.configure(size=3 * size)

    def copy_solution(self):
        cells = self._solution_cells()
        if not cells or self.run_active:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(solution_text(cells, solution_columns(len(cells))))
        self.solution_note_var.set(tr("In die Zwischenablage kopiert."))

    def enter_paper(self):
        """Papierbogen eines Teilnehmers ohne Rechner eintragen: Name und je
        Nummer die Zeile vom Zettel. Gewertet ohne Zeit (nicht flüssig,
        nicht in der Tempo-Empfehlung); derselbe Name ersetzt den Bogen."""
        if self.board is None or not self.board.items or self.run_active:
            return
        if self.paper_window is not None:
            self.paper_window.lift()
            return
        window = tk.Toplevel(self.root)
        window.title(tr("Papierbogen eintragen – {session}").format(session=self.session_var.get()))
        window.geometry("760x560")
        window.configure(background=theme.BG)
        frame = ScrollableFrame(window).inner
        top = ttk.Frame(frame, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text=tr("Name/Rufzeichen:")).pack(side="left", padx=(0, 4))
        self.paper_name_var = tk.StringVar(value="")
        name_entry = ttk.Entry(top, textvariable=self.paper_name_var, width=14)
        name_entry.pack(side="left")
        ttk.Button(top, text=tr("Übernehmen"), style="Accent.TButton", command=self.apply_paper).pack(
            side="left", padx=(12, 0))
        theme.hint(frame, wrap=560, text=tr(
            "Je Nummer die Zeile vom Zettel, leer = verpasst. Enter springt zur nächsten Nummer. Gewertet wird "
            "richtig oder falsch, ohne Zeit – nicht als flüssig und nicht für die Tempo-Empfehlung.")).pack(
            anchor="w", padx=10)
        self.paper_note_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.paper_note_var, style="Status.TLabel").pack(anchor="w", padx=10, pady=4)
        self.paper_sheet = PaperSheet(frame, sorted(self.board.items))
        self.paper_sheet.frame.pack(anchor="w", padx=10, pady=(0, 10))
        name_entry.bind("<Return>", lambda e: self.paper_sheet.focus(0) or "break")
        window.protocol("WM_DELETE_WINDOW", self.close_paper)
        self.paper_window = window
        name_entry.focus_set()

    def close_paper(self):
        if self.paper_window is not None:
            self.paper_window.destroy()
        self.paper_window = None

    def apply_paper(self):
        name = protocol.clean_name(self.paper_name_var.get())
        if not name:
            self.paper_note_var.set(tr("Bitte Name oder Rufzeichen eingeben."))
            return
        if self.board is None or not self.board.add_paper(name, self.paper_sheet.values()):
            self.paper_note_var.set(tr("„{name}“ hat schon am Rechner geantwortet – anderen Namen wählen.").format(
                name=name))
            return
        data = self.board.summary(name)
        self.paper_note_var.set(tr("Bogen von {name}: {correct} von {total} richtig. Nächster Bogen?").format(
            name=name, correct=data["correct_items"], total=data["items"]))
        self.paper_name_var.set("")
        self.paper_sheet.clear()
        self._refresh_table(name)

    def print_answer_sheet(self):
        """Antwortbogen für die eingestellte Übung als HTML-Seite im
        Browser öffnen (von dort drucken)."""
        kind = CONTENTS.get(self.content_var.get(), "groups")
        try:
            count, group_len = self.count_var.get(), self.group_len_var.get()
            wpm = self.wpm_var.get()
        except tk.TclError:
            self.sheet_var.set(tr("Ungültige Anzahl, Antwortzeit, Schreibpause oder Gruppenlänge!"))
            return
        if kind == "custom":
            count = sum(1 for line in self.custom_text.get("1.0", "end").splitlines() if normalize(line))
        elif kind == "qso" or not count:
            count = SHEET_DEFAULT_ROWS
        boxes = group_len if kind == "groups" else 1 if kind == "chars" else None
        page = answer_sheet.answer_sheet_html(
            max(count, 1), boxes, title=self.session_var.get(),
            details=f"{tr(self.content_var.get())} · {tempo.label(wpm, self.farnsworth_wpm())}",
            labels={"name": tr("Name"), "date": tr("Datum"),
                    "hint": tr("Verpasst? Lücke lassen und bei der nächsten Nummer weiterschreiben.")})
        path = stats.STATS_DIR / "antwortbogen.html"
        try:
            stats.STATS_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(page, encoding="utf-8")
            open_in_editor(path)
        except OSError as exc:
            self.sheet_var.set(tr("Nicht gespeichert: {error}").format(error=exc))
            return
        self.sheet_var.set(tr("Im Browser geöffnet, dort drucken: {path}").format(path=path))

    def export_csv(self):
        if self.board is None or not self.board.items:
            return
        headers = (tr("Name"), tr("Zeichen richtig (%)"), tr("Sequenzen richtig"), tr("Sequenzen flüssig"),
                   tr("Median Zeit (s)"), tr("Häufigste Fehler"), tr("Schwächste Zeichen"))
        path = stats.STATS_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}-netzwerk.csv"
        try:
            stats.STATS_DIR.mkdir(parents=True, exist_ok=True)
            # Mit BOM, damit Excel die Umlaute erkennt.
            path.write_text(self.board.csv_text(headers), encoding="utf-8-sig")
        except OSError as exc:
            self.export_var.set(tr("Nicht gespeichert: {error}").format(error=exc))
            return
        self.export_var.set(tr("Gespeichert: {path}").format(path=path))

    # --- Teilnehmer -----------------------------------------------------------------
    def search(self):
        """Sucht Trainer im Netz, im Hintergrund (die Suche wartet eine Sekunde)."""
        self.search_button.config(state="disabled")
        self.trainee_status_var.set(tr("Suche Trainer im Netz…"))

        def run():
            try:
                self.found = net_client.discover()
            except OSError:
                self.found = []
        threading.Thread(target=run, daemon=True).start()
        self._ensure_polling()

    def _show_found(self, found):
        self.search_button.config(state="normal")
        entries = [f"{host}" + (f":{port}" if port != protocol.DEFAULT_PORT else "") for _, host, port in found]
        self.address_box.config(values=entries)
        if not found:
            self.trainee_status_var.set(tr("Kein Trainer gefunden. Adresse von Hand eingeben?"))
            return
        if not self.address_var.get().strip() or self.address_var.get() not in entries:
            self.address_var.set(entries[0])
        names = ", ".join(f"{session} ({entry})" for (session, _, _), entry in zip(found, entries))
        self.trainee_status_var.set(tr("Gefunden: {names}").format(names=names))

    def toggle_connection(self):
        if self.client is None:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        name = protocol.clean_name(self.name_var.get())
        address = protocol.parse_address(self.address_var.get())
        if not name:
            self.trainee_status_var.set(tr("Bitte Name oder Rufzeichen eingeben."))
            return
        if address is None:
            self.trainee_status_var.set(tr("Bitte die Adresse des Trainers eingeben oder suchen."))
            return
        self.client = net_client.TraineeClient()
        self.client.connect(address[0], address[1], name, self.pin_var.get().strip(), self.version)
        self.connect_button.config(text=tr("Trennen"))
        for widget in (self.name_entry, self.pin_entry, self.address_box):
            widget.config(state="disabled")
        self.trainee_status_var.set(tr("Verbinde…"))
        self._lock_role()
        self._ensure_polling()

    def disconnect(self, status=None):
        if self.client is not None:
            self.client.close()
        self.client = None
        self._end_client_run()
        self.current = None
        self.play_token += 1
        self._set_input(False)
        self.connect_button.config(text=tr("Verbinden"))
        for widget in (self.name_entry, self.pin_entry):
            widget.config(state="normal")
        self.address_box.config(state="normal")
        self.trainee_status_var.set(status or tr("Getrennt."))
        was_connected, self.connected = self.connected, False
        self._lock_role()
        if was_connected and self.running:
            self.running = False
            self.on_stop_cb()

    def _on_client_event(self, event):
        kind = event[0]
        if kind == "welcome":
            self.connected = True
            self.running = True
            self.on_start_cb()  # sperrt die Reiter; Übungszeit erst ab dem Durchgang
            self.trainee_status_var.set(tr("Verbunden mit „{session}“. Warte auf den Trainer…").format(
                session=event[1]))
            self._check_version(event[2])
        elif kind == "reject":
            self.disconnect(tr(REJECTED.get(event[1], REJECTED["name"])))
            self._check_version(event[2])
        elif kind == "error":
            self.disconnect(tr("Keine Verbindung zum Trainer: {error}").format(error=event[1]))
        elif kind == "closed":
            self.disconnect(tr("Verbindung zum Trainer beendet."))
        elif kind == "message":
            self._on_message(event[1], event[2])

    # --- Update auf die Version des Trainers ----------------------------------------
    def _check_version(self, version):
        if self.updater is not None and version is not None:
            # Erst den Abruf aus dem Netz beenden, dann fragen (modal).
            self._after(0, lambda: self.updater.offer(
                version, tr("Der Trainer nutzt Version {theirs}, du hast {mine}.").format(
                    theirs=version, mine=self.version),
                self.trainee_status_var.set, self._prepare_update,
                lambda: self.connect_button.config(state="normal")))

    def _prepare_update(self):
        """Vor dem Laden trennen; nach dem Neustart wieder verbinden."""
        pin = self.pin_var.get().strip()
        if self.client is not None:
            self.disconnect()
        self.connect_button.config(state="disabled")
        return ["--join", pin]

    def rejoin(self, pin: str):
        """Nach dem Neustart durch ein Update: wieder als Teilnehmer mit
        demselben Trainer verbinden (Name und Adresse sind gespeichert)."""
        self.role_var.set(TRAINEE)
        self._show_role()
        self.pin_var.set(pin)
        self.connect()

    def _on_message(self, message, received=None):
        """`received`: Eingang der Nachricht; kommt der Ton vom Lautsprecher
        des Trainers, beginnt er ungefähr dann (nicht erst beim Abholen)."""
        received = received or time.time()
        kind = message["type"]
        if kind == "start":
            wpm, fw = message.get("wpm"), message.get("fw")
            self._start_client_run(str(message.get("charset", ""))[:100], wpm if isinstance(wpm, int) else 0,
                                   fw if isinstance(fw, int) else None, kind=message.get("kind"))
            if message.get("signs") is True:
                self._client_signs(START_TEXT + " ", message)
                self.trainee_status_var.set(tr("Achtung: {text}").format(text=START_TEXT))
        elif kind == "item":
            self._on_item(message, received)
        elif kind == "stream":
            self._on_stream(message, received)
        elif kind == "replay":
            if (self.current is not None and message.get("n") == self.current["n"]
                    and (not self.answered or self.current["paper"])):
                self.current["replayed"] = True
                self.replayed = True
                self.current["received"] = received
                self._play_current()
        elif kind == "close":
            if self.current is None or message.get("n") != self.current["n"]:
                return
            if not self.answered:
                self.submit(timed_out=True)
            # Die Lösung steht da; wer sie nicht flüssig hatte, hört sie dazu.
            # Im festen Takt ("reveal": false) erst am Ende.
            if (message.get("reveal", True) and message.get("solution") and self.last_result is not None
                    and not self.last_result.fluent):
                self.trainee_status_var.set(tr("Hör dir die Lösung noch einmal an…"))
                if not self.current["silent"]:  # sonst spielt sie der Lautsprecher
                    self._play_current(solution=True)
        elif kind == "end":
            self._end_client_run()
            if message.get("signs") is True:
                self._client_signs(END_TEXT, message)
            if self.paper_items:
                self._show_paper_sheet()
                return
            self._show_paced_results()
            self.trainee_status_var.set(tr("Durchgang beendet: {correct} von {total} Sequenzen richtig.").format(
                correct=self.run_correct, total=self.run_total) if self.run_total else tr("Durchgang beendet."))

    def _start_client_run(self, charset, wpm, fw, kind=None):
        """`kind`: Inhaltsart des Trainers; Klartext zählt nicht für die
        Zeichenstatistik (unbekannt, etwa beim Dazukommen: zählt)."""
        self._end_client_run()
        self.practice_start()
        self.session_stats = SessionStats(self.session_mode, charset, wpm, self._freq(), farnsworth_wpm=fw,
                                          char_stats=not (isinstance(kind, str) and kind in PLAIN_TEXT))
        # Latenz für richtig, aber unsicher (Wiederholung, zu langsam): wie in
        # sequence_mode doppelt so lang wie üblich, höchstens LATENCY_CAP_S.
        median = CharPicker(charset, weighted=True).median_latency() if charset else None
        self.unsure_latency = min(2 * median, LATENCY_CAP_S) if median else LATENCY_CAP_S
        self.run_correct = self.run_total = 0
        self.history = []
        self.history_var.set("")
        self.paced_results = []
        self.paper_items = []
        self.paper_run = (charset, wpm, fw)
        self.paper_check.config(state="disabled")
        self.results_card.pack_forget()
        self.paper_card.pack_forget()
        self.stats_panel.reset()

    def _end_client_run(self):
        if self.stream is not None:
            self._finish_stream(stopped_at=time.time())
        if self.session_stats is None:
            return
        if self.current is not None and not self.answered:
            self.submit(timed_out=True)
        if self.paced_results:
            # Im festen Takt stand die Statistik bis hierher still (sie verrät Fehler).
            self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())
        path = self.session_stats.finalize()
        if not self.paper_items:  # sonst kommt die Statistik mit dem Abtippen
            self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None
        self.paper_check.config(state="normal")
        self.practice_stop()

    def _on_item(self, item, received=None):
        text = item.get("text")
        text = normalize(text) if isinstance(text, str) else ""
        wpm, fw = item.get("wpm"), item.get("fw")
        if not text or not isinstance(item.get("n"), int) or not isinstance(wpm, int) or not 5 <= wpm <= 60:
            return
        if not (fw is None or isinstance(fw, int) and 1 <= fw < wpm):
            fw = None
        if self.current is not None and not self.answered:
            self.submit(timed_out=True)
        if self.session_stats is None:
            self._start_client_run("", wpm, fw)  # mitten im Durchgang dazugekommen
        preset = item.get("band") if item.get("band") in band.PRESETS else None
        paced = item.get("paced") is True
        self.current = {"n": item["n"], "text": str(item["text"])[:protocol.TEXT_MAX], "wpm": wpm, "fw": fw,
                        "band": preset, "paced": paced, "silent": item.get("silent") is True,
                        "paper": paced and self.paper_var.get(), "replayed": False,
                        "received": received or time.time()}
        # Papier: nichts eintippen, keine Antwort; abgetippt wird am Ende.
        self.answered = self.current["paper"]
        if self.current["paper"]:
            self.paper_items.append(self.current)
        self.replayed = False
        self.last_result = None
        self.submit_pending = False
        self.enter_time = None
        self.input_var.set("")
        self.key_times, self.typed_so_far = [], ""
        self.feedback_var.set("")
        self.diff_var.set("")
        self._play_current()

    def _on_stream(self, message, received=None):
        """Kontinuierlich: alle Gruppen ohne Pause abspielen (still, wenn
        der Lautsprecher des Trainers spielt) und fortlaufend mitschreiben."""
        groups, wpm, fw = message.get("groups"), message.get("wpm"), message.get("fw")
        if not isinstance(groups, list) or not isinstance(wpm, int) or not 5 <= wpm <= 60:
            return
        groups = [" ".join(normalize(word) for word in group.split())[:protocol.TEXT_MAX]
                  for group in groups if isinstance(group, str)]
        groups = [group for group in groups if group]
        if not groups:
            return
        if not (fw is None or isinstance(fw, int) and 1 <= fw < wpm):
            fw = None
        if self.current is not None and not self.answered:
            self.submit(timed_out=True)
        if self.stream is not None:
            self._finish_stream(stopped_at=time.time())
        if self.session_stats is None:
            self._start_client_run("", wpm, fw)
        self.current = None
        entries, seconds = net_stream.timeline(groups, wpm, fw)
        silent = message.get("silent") is True
        preset = message.get("band") if message.get("band") in band.PRESETS else None
        player = None
        if not silent:
            conditions = self._band(preset, self._freq()) if preset else None
            player = net_stream.Player(groups, wpm, self._freq(), fw, conditions)
        self.stream = {"groups": groups, "wpm": wpm, "fw": fw, "entries": entries, "player": player,
                       "start": (received or time.time()) + AUDIO_LATENCY + net_stream.lead_seconds(preset)}
        self.input_var.set("")
        self.key_times, self.typed_so_far = [], ""
        self.feedback_var.set("")
        self.diff_var.set("")
        self.results_card.pack_forget()
        self._set_input(True)
        self.trainee_status_var.set(tr("Läuft – höre zu und tippe mit, ohne Enter…")
                                    + (" " + tr("(Lautsprecher)") if silent else ""))
        self.stream_token += 1
        token = self.stream_token
        rest = seconds + net_stream.lead_seconds(preset) + net_stream.tail_seconds(preset)
        self._after(int((AUDIO_LATENCY + rest + net_stream.FINISH_GRACE_SECONDS) * 1000) + 300,
                    lambda: token == self.stream_token and self._finish_stream())

    def _finish_stream(self, stopped_at=None):
        """Wertet das Mitgeschriebene aus, schickt je Gruppe eine Antwort
        und zeigt die Auflösung wie nach dem festen Takt."""
        stream, self.stream = self.stream, None
        self.stream_token += 1
        if stream is None:
            return
        player = stream["player"]
        if player is not None:
            player.stop()
        start = player.start if player is not None else stream["start"]
        self._set_input(False)
        typed = normalize(self.input_var.get())
        chars, groups = net_stream.evaluate(stream["entries"], start, typed, self.key_times[:len(typed)],
                                            stopped_at)
        if self.session_stats is not None:
            for expected, got, correct, reaction in chars:
                if reaction is None:
                    self.session_stats.record_char(expected, "", False, 0.0, 0.0)
                else:
                    self.session_stats.record_char(expected, got, correct, reaction,
                                                   net_stream.effective_wpm(expected, reaction), latency=reaction)
        self.paced_results = []
        for index, (typed_group, latency) in sorted(groups.items()):
            item = {"n": index + 1, "text": stream["groups"][index], "wpm": stream["wpm"], "fw": stream["fw"],
                    "band": None}
            result = evaluate(item["text"], typed_group, latency)
            self.paced_results.append((item, result, False))
            self.run_total += 1
            self.run_correct += result.correct
            if self.client is not None:
                self.client.send({"type": "answer", "n": item["n"], "typed": result.typed,
                                  "latency": None if latency is None else round(latency, 3), "replayed": False})
        sent = sum(len(normalize(item["text"])) for item, _, _ in self.paced_results)
        hits = sum(result.correct_chars for _, result, _ in self.paced_results)
        if sent:
            self.feedback_var.set(tr("{correct} von {total} Gruppen richtig, {share:.0%} der Zeichen").format(
                correct=sum(r.correct for _, r, _ in self.paced_results), total=len(self.paced_results),
                share=hits / sent))
            self.feedback_label.config(foreground=theme.TEXT)
        if player is not None and player.error:
            self.trainee_status_var.set(player.error)
        else:
            self.trainee_status_var.set(tr("Warte auf den Trainer…"))
        if self.session_stats is not None:
            self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())
        self._show_paced_results()

    def _client_signs(self, text, message):
        """Anfangs- oder Schlusszeichen beim Teilnehmer, mit Tempo und
        Störungen aus `message` (start/end); still, wenn der Lautsprecher
        des Trainers spielt."""
        wpm, fw = message.get("wpm"), message.get("fw")
        if message.get("silent") is True or not isinstance(wpm, int) or not 5 <= wpm <= 60:
            return
        if not (isinstance(fw, int) and 1 <= fw < wpm):
            fw = None
        preset = message.get("band") if message.get("band") in band.PRESETS else None
        self._play_signs(text, wpm, fw, preset)

    def _play_signs(self, text, wpm, fw, preset):
        """VVV = oder +, wie in den übrigen Reitern unter den Störungen."""
        freq = self._freq()
        samples = build_text(text, wpm, freq, fw)
        if preset:
            samples = band.apply_preset(self._band(preset, freq), samples)[0]
        audio.play_quietly(samples)

    def _freq(self) -> int:
        try:
            freq = self.freq_var.get()
        except tk.TclError:
            return 600
        return freq if 300 <= freq <= 1000 else 600

    def _band(self, preset, freq):
        key = (preset, freq)
        if key not in self._band_cache:
            self._band_cache[key] = band.preset_conditions(preset, freq)
        return self._band_cache[key]

    def _play_current(self, solution=False, item=None):
        """Spielt die aktuelle Sequenz; beim Abfragen mit offener Eingabe
        (Mitschreiben). Merkt sich, wann jedes Zeichen hörbar beginnt und
        endet, für die Latenz je Zeichen. `solution`: Lösung zum Einprägen
        vorspielen, ohne Störungen und ohne Eingabe (auch eine frühere
        Sequenz `item`)."""
        item = item or self.current
        wpm, fw, freq = item["wpm"], item["fw"], self._freq()
        chars = [ch for ch in item["text"].upper() if ch == " " or ch in MORSE_CODE]
        last = max((i for i, ch in enumerate(chars) if ch != " "), default=-1)
        parts, starts, ends, offset = [], [], [], 0.0
        for i, ch in enumerate(chars):
            if ch == " ":
                part = silence(word_gap_extra_seconds(wpm, fw))
            else:
                # Nach dem letzten Zeichen keine gestreckte Pause, damit die
                # Eingabe nicht unnötig spät als beendet gilt.
                gap_fw = fw if i < last else None
                part = build_samples(ch, wpm, freq, gap_fw)
                starts.append(offset)
                ends.append(offset + len(part) / SAMPLE_RATE - char_gap_seconds(wpm, gap_fw))
            parts.append(part)
            offset += len(part) / SAMPLE_RATE
        samples = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        lead = 0.0
        silent = item.get("silent") and not solution
        self.play_token += 1
        token = self.play_token
        if silent:
            # Der Lautsprecher des Trainers spielt, seit die Nachricht kam
            # (plus dessen Latenz); hier nur mitrechnen, wann welches Zeichen klingt.
            lead = band.PRESET_LEAD_SECONDS[0] if item["band"] else 0.0
            start = item["received"] + AUDIO_LATENCY
        else:
            if item["band"] and not solution:
                samples, lead = band.apply_preset(self._band(item["band"], freq), samples)
            start = time.time() + AUDIO_LATENCY
            try:
                audio.play(samples)
            except audio.AudioError as exc:
                self.trainee_status_var.set(str(exc))
        if solution:
            return
        self.play_start = start
        self.tone_starts = [start + lead + t for t in starts]
        self.tone_ends = [start + lead + t for t in ends]
        self.tone_end = self.tone_ends[-1] if self.tone_ends else start
        self.playing = True
        self._set_input(not item["paper"])
        if item["paper"]:
            status = tr("Nr. {n} – schreib mit…").format(n=item["n"])
        else:
            status = tr("Höre zu… (Wiederholung)") if self.replayed else tr("Höre zu…")
        if silent:
            status += " " + tr("(Lautsprecher)")
        self.trainee_status_var.set(status)
        # Eigene Samples enthalten Vor- und Nachlauf der Störungen schon.
        end = start + len(samples) / SAMPLE_RATE
        if silent and item["band"]:
            end += sum(band.PRESET_LEAD_SECONDS)
        dur_ms = max(int((end - time.time()) * 1000), 0) + 150
        self._after(dur_ms, lambda: token == self.play_token and self._playback_done())

    def _playback_done(self):
        self.playing = False
        if self.current is not None and self.current["paper"]:
            self.trainee_status_var.set(tr("Nr. {n} – auf Papier").format(n=self.current["n"]))
            return
        if self.current is None or self.answered:
            return
        if self.submit_pending:
            self.submit()
        else:
            self.trainee_status_var.set(tr("Deine Eingabe?"))

    def _on_input_change(self, *_):
        """Merkt sich, wann jedes Zeichen im Eingabefeld dazukam (wie in
        sequence_mode); Korrekturen behalten die Zeiten davor."""
        typed = normalize(self.input_var.get())
        keep = 0
        while keep < min(len(typed), len(self.typed_so_far)) and typed[keep] == self.typed_so_far[keep]:
            keep += 1
        self.key_times = self.key_times[:keep] + [time.time()] * (len(typed) - keep)
        self.typed_so_far = typed
        # So viele Zeichen wie gesendet: fertig, ohne Enter (während des
        # Tons wie ein vorzeitiges Enter). Nach der Trace, nicht mittendrin.
        if (self.current is not None and not self.answered and len(typed) > keep
                and len(typed) >= len(normalize(self.current["text"]))):
            self._after(0, self.on_submit)

    def _set_input(self, is_open: bool):
        self.entry.config(state="normal" if is_open else "disabled")
        if is_open:
            self.entry.focus_set()

    def on_submit(self, event=None):
        if self.current is None or self.answered:
            return "break"
        if self.playing:
            # Vorzeitig Enter: nach dem Ton werten (wie beim Mitschreiben).
            self.submit_pending = True
            self.enter_time = time.time()
            self.trainee_status_var.set(tr("Wird nach dem Ton ausgewertet…"))
            return "break"
        self.submit()
        return "break"

    def submit(self, timed_out=False):
        """Wertet die Eingabe aus, zeigt die Lösung und schickt die Antwort.
        Bei abgelaufener Zeit zählt der letzte Tastendruck als Antwortzeit,
        nicht das Ende der Frist."""
        if self.current is None or self.answered:
            return
        self.answered = True
        self._set_input(False)
        if timed_out:
            answer_time = self.key_times[-1] if self.key_times else time.time()
        else:
            answer_time = self.enter_time or time.time()
        latency = max(answer_time - self.tone_end, 0.0)
        result = evaluate(self.current["text"], self.input_var.get(), latency, self.replayed)
        self.last_result = result
        if self.client is not None:
            self.client.send({"type": "answer", "n": self.current["n"], "typed": result.typed,
                              "latency": round(latency, 3), "replayed": self.replayed})
        self._record(result, answer_time)
        self.run_total += 1
        self.run_correct += result.correct
        if self.current["paced"]:
            # Fester Takt: keine Lösung bis zum Ende, nur die Bestätigung.
            self.paced_results.append((self.current, result, self.replayed))
            self.feedback_var.set(tr("Nr. {n} notiert").format(n=self.current["n"]))
            self.feedback_label.config(foreground=theme.TEXT)
            self.diff_var.set("")
            self.trainee_status_var.set(tr("Warte auf die nächste Sequenz…"))
            return
        sent = display_text(self.current["text"])
        if result.correct:
            note = ""
            if self.replayed:
                note = "\n" + tr("(mit Wiederholung – zählt nicht als flüssig)")
            elif result.slow:
                note = "\n" + tr("(zu langsam – zählt nicht als flüssig)")
            self.feedback_var.set(tr("Richtig: {text}").format(text=sent) + note)
            self.feedback_label.config(foreground=theme.OK)
            self.diff_var.set("")
        else:
            prefix = tr("Zeit abgelaufen. ") if timed_out and not result.typed else ""
            self.feedback_var.set(prefix + tr("Lösung: {text}").format(text=sent))
            self.feedback_label.config(foreground=theme.ERROR)
            if result.typed:
                sent_row, typed_row, marks = align.diff_rows(result.sent, result.typed)
                self.diff_var.set(f"{tr('gesendet'):<10}{sent_row}\n{tr('getippt'):<10}{typed_row}\n"
                                  + " " * 10 + marks)
            else:
                self.diff_var.set("")
        self.history.append(f"{result.sent}{'=' if result.correct else '≠'}{result.typed}")
        self.history = self.history[-HISTORY_LEN:]
        self.history_var.set("   ".join(self.history))
        self.trainee_status_var.set(tr("Warte auf den Trainer…"))

    def _show_paper_sheet(self):
        """Nach dem Durchgang: je mitgeschriebener Nummer ein Feld."""
        for child in self.trainee_sheet_holder.winfo_children():
            child.destroy()
        self.trainee_sheet = PaperSheet(self.trainee_sheet_holder, [item["n"] for item in self.paper_items])
        self.trainee_sheet.frame.pack(anchor="w")
        self.results_card.pack_forget()
        self.paper_card.pack(fill="x", padx=10, pady=5)
        self.trainee_status_var.set(tr("Durchgang beendet. Tippe jetzt deine Mitschrift ab und dann „Auswerten“."))
        self.trainee_sheet.focus(0)

    def submit_paper(self):
        """Abgetippte Mitschrift werten, dem Trainer schicken und in die
        eigene Statistik: nur richtig/falsch je Zeichen, ohne Zeit, und
        nicht für Gewichtung und Lernkartei (wie Klartext)."""
        if not self.paper_items or self.trainee_sheet is None:
            return
        values = self.trainee_sheet.values()
        charset, wpm, fw = self.paper_run or ("", self.paper_items[0]["wpm"], self.paper_items[0]["fw"])
        session = SessionStats(self.session_mode, charset, wpm, self._freq(), farnsworth_wpm=fw, char_stats=False)
        self.paced_results = []
        self.run_correct = self.run_total = 0
        for item in self.paper_items:
            typed = values.get(item["n"], "")
            result = evaluate(item["text"], typed, None, item["replayed"])
            for expected, got, _ in result.char_results:
                session.record_char(expected, got, got == expected, 0.0, 0.0)
            session.record_group(result.sent, result.typed, wpm=item["wpm"])
            self.paced_results.append((item, result, item["replayed"]))
            self.run_total += 1
            self.run_correct += result.correct
            if self.client is not None and result.typed:
                self.client.send({"type": "paper", "n": item["n"], "typed": result.typed})
        self.stats_panel.refresh(session.summary(), session.char_rows())
        path = session.finalize()
        self.stats_panel.show_saved(path, session.log_error)
        self.paper_items = []
        self.paper_card.pack_forget()
        self._show_paced_results()
        self.feedback_var.set("")
        self.trainee_status_var.set(tr("Durchgang beendet: {correct} von {total} Sequenzen richtig.").format(
            correct=self.run_correct, total=self.run_total))

    def _show_paced_results(self):
        """Nach einem Durchgang im festen Takt: alle Sequenzen mit Lösung,
        Eingabe und ✓/✗, zum Anhören; dazu der Verlauf."""
        if not self.paced_results:
            return
        tree = self.results_tree
        tree.delete(*tree.get_children())
        for item, result, replayed in self.paced_results:
            mark = ("✓" if result.correct else "✗") + (" ↻" if replayed else "")
            tree.insert("", "end", iid=str(item["n"]), tags=("ok" if result.correct else "error",),
                        values=(item["n"], display_text(item["text"]), display_text(result.typed) or "–", mark))
        tree.configure(height=min(max(len(self.paced_results), 4), 15))
        self.results_card.pack(fill="x", padx=10, pady=5)
        wrong = next((str(item["n"]) for item, result, _ in self.paced_results if not result.correct), None)
        first = wrong or tree.get_children()[0]
        tree.selection_set(first)
        tree.focus(first)
        tree.see(first)
        self.history = [f"{result.sent}{'=' if result.correct else '≠'}{result.typed}"
                        for _, result, _ in self.paced_results][-HISTORY_LEN:]
        self.history_var.set("   ".join(self.history))

    def play_result(self):
        """Markierte Sequenz aus der Auflösung noch einmal abspielen."""
        selection = self.results_tree.selection()
        if not selection:
            return
        for item, _, _ in self.paced_results:
            if str(item["n"]) == selection[0]:
                self._play_current(solution=True, item=item)
                return

    def _char_timing(self, index: int, typed_index, answer_time):
        """(Reaktionszeit, Latenz oder None) für das gesendete Zeichen an
        `index`, wie in sequence_mode: eindeutig nur ohne Wiederholung und
        wenn die Taste nach dem Tonende kam, sonst gleichmäßig verteilt."""
        if (typed_index is not None and not self.replayed and typed_index < len(self.key_times)
                and index < len(self.tone_ends)):
            key_time = self.key_times[typed_index]
            latency = key_time - self.tone_ends[index]
            if latency >= 0:
                return key_time - self.tone_starts[index], latency
        return max(answer_time - self.play_start, 0.001) / max(len(self.tone_ends), 1), None

    def _record(self, result, answer_time):
        """In die eigene Statistik. Richtig, aber nach der Wiederholung oder
        (ohne Latenz je Zeichen) zu langsam, zählt wie in sequence_mode mit
        der doppelten üblichen Latenz: richtig, aber nicht flüssig, damit
        Gewichtung und Lernkartei es nicht als sicher verbuchen."""
        if self.session_stats is None or not result.sent:
            return
        for index, (expected, got, typed_index) in enumerate(result.char_results):
            reaction_time, latency = self._char_timing(index, typed_index, answer_time)
            assumed = got == expected and (result.replayed or (latency is None and result.slow))
            if assumed:
                latency = self.unsure_latency
            self.session_stats.record_char(expected, got, got == expected, reaction_time,
                                           code_units(expected) * 1.2 / max(reaction_time, 0.001),
                                           latency=latency, assumed=assumed)
        self.session_stats.record_group(result.sent, result.typed, wpm=self.current["wpm"])
        if not self.current["paced"]:
            self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

    # --- Schnittstelle zum Hauptfenster ---------------------------------------------
    def on_key(self, event):
        pass

    def on_function_key(self, key: str):
        """Nur beim Trainer: F5 Start/Stop, F6 für alle wiederholen, F7
        weiter. Beim Teilnehmer bleibt es bei Enter."""
        if self.role_var.get() != TRAINER or self.server is None:
            return
        if key == "F5":
            self.toggle_run()
        elif key == "F6":
            self.replay_for_all()
        elif key == "F7":
            self.advance()

    def on_close(self):
        if self.server is not None:
            self.close_session()
        if self.client is not None:
            self.client.close()
            self.client = None
        self._end_client_run()
        # Zuletzt: Das Schließen der Sitzung plant womöglich noch etwas ein.
        for after_id in [self.poll_id, *self.after_ids]:
            if after_id is not None:
                self.root.after_cancel(after_id)
        self.poll_id, self.after_ids = None, set()

    def settings(self) -> dict:
        data = {
            "role": self.role_var.get(),
            "session": self.session_var.get(),
            "content": self.content_var.get(),
            "band": BAND_LABELS.get(self.band_var.get()),
            "auto": self.auto_var.get(),
            "flow": self.flow_var.get(),
            "solution": self.solution_var.get(),
            "listen": self.listen_var.get(),
            "speaker": self.speaker_var.get(),
            "signs": self.signs_var.get(),
            "paper": self.paper_var.get(),
            "name": self.name_var.get(),
            "address": self.address_var.get(),
            "custom_text": self.custom_text.get("1.0", "end").rstrip("\n"),
        }
        for key, var in (("port", self.port_var), ("count", self.count_var), ("answer_s", self.answer_var),
                         ("group_len", self.group_len_var), ("pause_s", self.pause_var),
                         ("duration", self.duration_var)):
            try:
                data[key] = var.get()
            except tk.TclError:
                pass
        return data

    def restore_settings(self, data: dict) -> None:
        if data.get("role") in (TRAINER, TRAINEE):
            self.role_var.set(data["role"])
            self._show_role()
        if data.get("content") in CONTENTS:
            self.content_var.set(data["content"])
        if data.get("flow") in (WAIT, PACED, CONTINUOUS):
            self.flow_var.set(data["flow"])
            self._show_flow_options()
        for label, preset in BAND_LABELS.items():
            if data.get("band") == preset:
                self.band_var.set(label)
        for key, var in (("auto", self.auto_var), ("solution", self.solution_var), ("listen", self.listen_var),
                         ("speaker", self.speaker_var), ("signs", self.signs_var), ("paper", self.paper_var)):
            if isinstance(data.get(key), bool):
                var.set(data[key])
        self._show_speaker_options()
        for key, var in (("session", self.session_var), ("name", self.name_var), ("address", self.address_var)):
            if isinstance(data.get(key), str):
                var.set(data[key][:60])
        if isinstance(data.get("custom_text"), str):
            self.custom_text.insert("1.0", data["custom_text"][:10000])
        for key, var, (low, high) in (("port", self.port_var, (1024, 65535)), ("count", self.count_var, COUNT_RANGE),
                                      ("answer_s", self.answer_var, ANSWER_RANGE),
                                      ("group_len", self.group_len_var, GROUP_LEN_RANGE),
                                      ("pause_s", self.pause_var, PAUSE_RANGE),
                                      ("duration", self.duration_var, net_stream.DURATION_RANGE)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
                var.set(value)
