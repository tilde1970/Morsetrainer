"""Kontinuierlicher Modus: Audio läuft in einem Hintergrund-Thread ohne
Pause weiter, unabhängig davon ob/wie schnell du tippst (wie beim Mithören
von echtem CW-Verkehr). Du tippst fortlaufend mit; ein Levenshtein-Alignment
zwischen gesendeter und getippter Zeichenkette (analog zu morse_trainer_cont.py
in WZab/morse_trainer, hier direkt auf Strings statt mit eigenem Audio-Queue-
Player reimplementiert) ordnet am Ende jedem gesendeten Zeichen zu, ob es
richtig, falsch oder gar nicht getippt wurde – auch wenn zwischendurch
Zeichen übersprungen wurden.

Die Live-Anzeige während der Session ist nur eine grobe, jede Sekunde neu
berechnete Vorschau. Die endgültige Zuordnung für die Statistik passiert erst
beim Stop in einem einzigen Alignment-Durchlauf über die ganze Session.

Die Zeichen kommen in Gruppen (Standard 5) mit Wortpause dazwischen, wie
bei Koch-Kursen und im Funkbetrieb; das gibt dem Ohr Wortgrenzen, und mit
Farnsworth stimmt das effektive Tempo (die ARRL-Formel rechnet mit
Wortpausen). Gruppenlänge 0 = ununterbrochener Strom.

Ehrliche Wertung: Eine Taste zählt nur dann für ein gesendetes Zeichen,
wenn sie zeitlich dazu passt – nicht vor dessen Ende (Vorausraten) und
höchstens MAX_LAG_SECONDS danach; sonst gilt das Zeichen als verpasst und
die Taste als überzählig. Überzählige Tasten werden für den Koch-Aufstieg
abgezogen, sonst brächte Drauflostippen volle Punktzahl. Beim Stoppen
von Hand zählen Zeichen der letzten STOP_GRACE_SECONDS nicht als verpasst
(man war gerade dabei, sie zu tippen). Nach dem Stoppen zeigt eine
Gegenüberstellung die letzten Zeichen gesendet/getippt. F5 startet und
stoppt, Esc stoppt."""
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import numpy as np

from morsetrainer.core import align, audio, band, koch
from morsetrainer.core.latency import char_latency
from morsetrainer.core.morse import (
    END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text,
    char_gap_seconds, effective_wpm, silence, tone_seconds, word_gap_extra_seconds,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import theme
from morsetrainer.widgets.band_settings import BandSettings, BandToggle, toggle_value
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ChoiceBox, ScrollableFrame
from morsetrainer.modes.content import PLAIN_TEXT, ItemSource
from morsetrainer.modes.daily_support import DailyModeMixin
from morsetrainer.modes.sequence_mode import BAND_ORDER, band_config

# Der Audio-Thread schreibt die Zeichen in so großen Häppchen in den Stream,
# damit ein Stop nicht erst das ganze (evtl. lange Farnsworth-)Zeichen
# abwarten muss.
WRITE_CHUNK_SECONDS = 0.02

# Nach Ablauf der eingestellten Dauer wird nichts Neues mehr gesendet; so
# lange bleibt noch Zeit, die zuletzt gehörten Zeichen einzutippen.
FINISH_GRACE_SECONDS = 3

DEFAULT_GROUP_LEN = 5
GROUP_LEN_RANGE = (0, 10)

# Inhalt: Zufallszeichen in Gruppen (zählt für die Koch-Lektion) oder
# Klartext aus Wörtern, Wendungen, Rufzeichen, QSOs (siehe modes/content.py).
CONTENTS = {N_("Zufallszeichen"): "chars", N_("Wörter"): "words", N_("Wendungen"): "phrases",
            N_("Rufzeichen"): "calls", N_("QSO-Klartext"): "qso"}

# Zeitliche Plausibilität einer Zuordnung Taste -> gesendetes Zeichen: so
# viel früher als das Tonende (Messungenauigkeit) bzw. höchstens so viel
# später darf die Taste kommen.
EARLY_TOLERANCE_SECONDS = 0.15
MAX_LAG_SECONDS = 5.0


# Beim Stoppen von Hand: so kurz vor dem Stopp gesendete Zeichen, die noch
# nicht getippt sind, zählen nicht als verpasst.
STOP_GRACE_SECONDS = 2.0
# So viele der letzten Zeichen zeigt die Gegenüberstellung nach dem Stopp,
# in Zeilen zu DIFF_LINE (gesendet, getippt, Markierung untereinander).
DIFF_TAIL = 90
DIFF_LINE = 30
# So viele der zuletzt getippten Zeichen zeigt „Deine Eingabe“.
TYPED_TAIL = 120
# Die ganze Auswertung (eigenes Fenster) ist nach den gesendeten Gruppen
# bzw. Wörtern gegliedert; ohne Gruppen (durchgehend) in Blöcken zu 5.
FULL_GROUP_LEN = 5
GROUP_GAP = "  "
# Schriftgröße im Fenster (Standard, kleinste, größte, Schritt).
FULL_FONT = (18, 10, 60, 2)


def grouped_lines(rows, width: int):
    """Gegenüberstellung der ganzen Sitzung, nach Gruppen gegliedert und
    auf `width` Spalten umbrochen (eine Gruppe wird nicht zerteilt):
    [(Nr. der ersten Gruppe, gesendet, getippt, Markierungen)]. `rows`:
    [(gesendet, getippt, Markierung, Gruppe)] je Zeichen, "–" = Lücke."""
    groups = []
    for sent, typed, mark, group in rows:
        if not groups or groups[-1][0] != group:
            groups.append((group, []))
        groups[-1][1].append((sent, typed, mark))
    lines, current, used = [], [], 0

    def flush():
        cells = [[cell[i] for cell in group] for group in current for i in range(3)]
        rows_out = [GROUP_GAP.join("".join(cells[g * 3 + i]) for g in range(len(current))) for i in range(3)]
        lines.append((first, rows_out[0], rows_out[1], rows_out[2].rstrip()))

    first = 1
    for number, (_, cells) in enumerate(groups, start=1):
        extra = len(cells) + (len(GROUP_GAP) if current else 0)
        if current and used + extra > width:
            flush()
            current, used, first = [], 0, number
            extra = len(cells)
        current.append(cells)
        used += extra
    if current:
        flush()
    return lines


def plausible(typed_time: float, tone_end: float) -> bool:
    """Passt ein Tastendruck zeitlich zu einem Zeichen mit diesem Tonende?"""
    return tone_end - EARLY_TOLERANCE_SECONDS <= typed_time <= tone_end + MAX_LAG_SECONDS


# Die vorläufige Trefferquote während der Sitzung bezieht sich auf die
# zuletzt gesendeten Zeichen; die ganze Sitzung wird erst beim Stop
# ausgewertet. Getippte Zeichen zählen zum Fenster, wenn sie höchstens
# PREVIEW_SLACK_SECONDS vor dem Ende seines ersten Zeichens kamen.
PREVIEW_CHARS = 200
PREVIEW_SLACK_SECONDS = 1.0


class ContinuousModeFrame(DailyModeMixin):
    """Reiter Kontinuierlich: der Ton läuft ohne Warten durch, du tippst mit wie
    beim Mithören. Ausgewertet wird erst nach dem Stoppen, mit Gegenüberstellung
    und auf Wunsch der ganzen Sitzung im eigenen Fenster."""
    daily_keys = ("content", "group_len", "band")
    uses_band = True  # zentrale Bandbedingungen (widgets/band_settings.py)

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 band_settings=None):
        self.root = parent.winfo_toplevel()
        self.band_settings = band_settings or BandSettings(self.root)
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
        self.koch_result = None   # (Zeichensatz, richtig, gesamt) für den Koch-Aufstieg
        self.audio_error = None   # Fehlermeldung aus dem Audio-Thread
        self.band = None          # BandConditions des laufenden Durchgangs, None = ohne Störungen
        self.band_tracked = False  # Durchgang begann mit Bandbedingungen
        self.full_rows = []       # Gegenüberstellung der ganzen letzten Sitzung
        self.full_window = None
        self.full_width = None    # Spalten beim letzten Aufbau des Fensters

        self._build_widgets(ScrollableFrame(parent).inner)

    def _build_widgets(self, parent):
        """Baut den Reiter: Einstellungen, Start, Statuszeile, Live-Anzeige,
        Auswertung, eigene Eingabe und Statistik."""
        theme.hint(
            parent, wrap=560,
            text=tr("Der Ton läuft durch, ohne auf dich zu warten. Tippe mit, was du erkennst "
                    "– auch wenn du mal hinterherhinkst. Auswertung erfolgt beim Stoppen. "
                    "F5 startet und stoppt, Esc stoppt."),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        options = self.options_card = theme.card(parent, tr("Einstellungen"))
        duration = ttk.Frame(options)
        duration.pack(fill="x")
        ttk.Label(duration, text=tr("Dauer:")).pack(side="left", padx=(0, 4))
        self.duration_var = tk.IntVar(value=5)
        ttk.Spinbox(duration, from_=0, to=120, textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(duration, text=tr("Min.")).pack(side="left", padx=(4, 0))
        theme.hint(duration, text=tr("(0 = ohne Limit)")).pack(side="left", padx=(4, 0))
        content = ttk.Frame(options)
        content.pack(fill="x", pady=(2, 0))
        ttk.Label(content, text=tr("Inhalt:")).pack(side="left", padx=(0, 4))
        self.content_var = tk.StringVar(value="Zufallszeichen")
        ChoiceBox(content, self.content_var, CONTENTS, width=17).pack(side="left")
        theme.hint(content, text=tr("(Klartext zählt nicht für die Lektion)")).pack(side="left", padx=(6, 0))
        grouping = ttk.Frame(options)
        grouping.pack(fill="x", pady=(2, 0))
        ttk.Label(grouping, text=tr("Gruppen zu")).pack(side="left", padx=(0, 4))
        self.group_len_var = tk.IntVar(value=DEFAULT_GROUP_LEN)
        group_len_box = ttk.Spinbox(grouping, from_=GROUP_LEN_RANGE[0], to=GROUP_LEN_RANGE[1],
                                    textvariable=self.group_len_var, width=3)
        group_len_box.pack(side="left")
        # Gruppenlänge gilt nur für Zufallszeichen; Klartext hat seine Wörter.
        self.content_var.trace_add("write", lambda *_: group_len_box.state(
            ["!disabled"] if self.content_var.get() == "Zufallszeichen" else ["disabled"]))
        ttk.Label(grouping, text=tr("Zeichen", context="Einheit")).pack(side="left", padx=(4, 0))
        theme.hint(grouping, text=tr("(mit Wortpause dazwischen; 0 = durchgehend)")).pack(side="left", padx=(4, 0))
        self.band_var = tk.BooleanVar(value=False)
        self.band_toggle = BandToggle(options, self.band_settings, self.band_var, on_change=self._update_band,
                                      pady=(2, 0))

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Start"), style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")

        self.status_var = tk.StringVar(value=tr("Bereit. Drücke Start."))
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel").pack(pady=(14, 6))

        self.live_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.live_var).pack(anchor="w", padx=10)

        self.diff_box = theme.card(parent, tr("Auswertung (letzte {n} Zeichen)").format(n=DIFF_TAIL))
        self.diff_var = tk.StringVar(value=tr("Erscheint nach dem Stoppen."))
        ttk.Label(self.diff_box, textvariable=self.diff_var, font=theme.MONO, justify="left").pack(anchor="w")
        self.full_button = ttk.Button(self.diff_box, text=tr("Alles in eigenem Fenster"), command=self.show_full,
                                      state="disabled")
        self.full_button.pack(anchor="w", pady=(6, 0))

        typed = theme.card(parent, tr("Deine Eingabe (letzte {n} Zeichen)").format(n=TYPED_TAIL))
        self.typed_preview_var = tk.StringVar(value="")
        ttk.Label(typed, textvariable=self.typed_preview_var, font=theme.MONO, wraplength=540).pack(anchor="w")

        self.stats_panel = StatsPanel(parent)

    def settings(self) -> dict:
        """Einstellungen zum Speichern: Inhalt, Bandbedingungen an/aus, Dauer und
        Gruppenlänge (ungültige Felder fehlen)."""
        data = {"content": CONTENTS.get(self.content_var.get()), "band": self.band_var.get()}
        for key, var in (("duration", self.duration_var), ("group_len", self.group_len_var)):
            try:
                data[key] = var.get()
            except tk.TclError:
                pass
        return data

    def restore_settings(self, data: dict) -> None:
        """Gegenstück zu settings(); ungültige Werte werden übergangen."""
        for label, key in CONTENTS.items():
            if data.get("content") == key:
                self.content_var.set(label)
        if "band" in data and toggle_value(data["band"]) is not None:
            self.band_var.set(toggle_value(data["band"]))
        for key, var, limits in (("duration", self.duration_var, (0, 120)),
                                 ("group_len", self.group_len_var, GROUP_LEN_RANGE)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)

    def _update_band(self):
        """Schalter und zentrale Einstellung wirken auch im laufenden
        Durchgang; das Schwächste davon zählt für das Diplom."""
        if not self.running:
            return
        spec = self.band_settings.spec() if self.band_var.get() else None
        if spec is None:
            self.band = None
        elif self.band is None:
            self.band = band.conditions(spec, self.freq)
        else:
            band.apply_spec(self.band, spec)
            self.band.prepare(self.freq)
        if self.band_tracked:
            self.band_gain_min = min(self.band_gain_min, round(spec["gain"] * 100) if spec else 0)
            self.band_rank_min = min(self.band_rank_min, band.preset_rank(spec), key=BAND_ORDER.index)

    def toggle_running(self):
        """Durchgang starten bzw. beenden (Knopf, F5)."""
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        """Prüft Zeichensatz, Dauer und Inhalt und startet den Audio-Thread, der
        nach „VVV =“ ohne Pause sendet, bis die Dauer um ist (0 = bis Stop)."""
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set(tr("Kein gültiges Zeichen im Zeichensatz!"))
            return
        try:
            minutes = self.duration_var.get()
        except tk.TclError:
            minutes = -1
        if minutes < 0:
            self.status_var.set(tr("Ungültige Dauer!"))
            return
        self.deadline = time.time() + minutes * 60 if minutes else None
        if self.daily_minutes:
            self.deadline = self._daily_deadline()
        self.finishing = False
        self.end_sent = False
        self.koch_result = None
        self.audio_error = None
        self.session_id += 1
        self.charset = charset
        self.wpm = self.wpm_var.get()
        self.freq = self.freq_var.get()
        self.fw = self.farnsworth_wpm()
        # Bandbedingungen laufen durchgehend unter dem ganzen Durchgang mit
        # (Rauschen und QSB reißen nicht zwischen den Zeichen ab).
        spec = self.band_settings.spec() if self.band_var.get() else None
        self.band = band.conditions(spec, self.freq) if spec else None
        self.band_tracked = spec is not None
        self.band_gain_min = round(spec["gain"] * 100) if spec else 0
        self.band_rank_min = band.preset_rank(spec)
        self.sent_log = []
        self.typed_log = []
        try:
            self.group_len = min(max(self.group_len_var.get(), GROUP_LEN_RANGE[0]), GROUP_LEN_RANGE[1])
        except tk.TclError:
            self.group_len = DEFAULT_GROUP_LEN
        self.content = CONTENTS.get(self.content_var.get(), "chars")
        if self.content == "chars":
            # Gruppenlänge 0: ein Zeichen je Eintrag, ohne Wortpausen.
            self.source = ItemSource("groups", charset, self.group_len or 1, self.weighted_var.get())
        else:
            self.source = ItemSource(self.content, charset, weighted=self.weighted_var.get())
        problem = self.source.problem()
        if problem:
            self.status_var.set(problem)
            return
        self.session_stats = SessionStats("continuous", charset, self.wpm, self.freq, farnsworth_wpm=self.fw,
                                          review_promote=self.content == "chars",
                                          # Im Störnebel verlorene Zeichen zählen nicht für die
                                          # Zeichenstatistik (wie in sequence_mode).
                                          char_stats=self.content not in PLAIN_TEXT and spec is None,
                                          group_len=self.group_len or None,
                                          config_extra={"lesson": koch.lesson_of(charset),
                                                        **band_config(spec),
                                                        "content": self.content,
                                                        "user_words": self.source.has_user_words(),
                                                        **self._daily_config()})
        self.stats_panel.reset()
        self.live_var.set(tr("Gesendet: {n} Zeichen").format(n=0))
        self.typed_preview_var.set("")
        self.diff_var.set(tr("Erscheint nach dem Stoppen."))

        self.running = True
        self.band_toggle.set_locked(True)
        self.start_button.config(text=tr("Stop"))
        self.status_var.set(tr("Läuft – höre zu und tippe mit…"))
        self.on_start_cb()

        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        self.root.after(1000, self._tick)

    def _own_thread(self) -> bool:
        """Gehört der aufrufende Audio-Thread zur laufenden Sitzung? Ein
        alter Thread, der nach Stop an einem hängenden Gerät festhing, darf
        eine neue Sitzung weder beschreiben noch beenden."""
        return threading.current_thread() is self.play_thread

    def _live(self) -> bool:
        return self.running and self._own_thread()

    def _play_loop(self):
        try:
            self._play_session()
        except audio.ERRORS as exc:
            if self._own_thread():
                self.audio_error = audio.describe(exc)  # _tick beendet die Sitzung
        except Exception as exc:
            if self._own_thread():
                self.audio_error = audio.unexpected(exc)
            raise  # ins Fehlerprotokoll (threading.excepthook)

    def _play_session(self):
        # Ein durchgehender Stream für die ganze Sitzung: Zeichen werden
        # lückenlos hintergeschrieben. Ein eigener Stream pro Zeichen
        # (sd.play + sd.wait) knackt beim Öffnen/Schließen und reißt Lücken.
        """Audio-Thread: sendet „VVV =“, dann ohne Pause Zeichen bzw. Wörter aus
        der Quelle in einem durchgehenden Strom und protokolliert das hörbare
        Ende jedes Zeichens; ist die Zeit um, folgt das Schlusszeichen."""
        with audio.output_stream() as stream:
            # Einleitung, wird nicht ausgewertet (landet nicht in sent_log).
            if not self._write(stream, build_text(START_TEXT + " ", self.wpm, self.freq, self.fw)):
                return
            word_gaps = self.content != "chars" or self.group_len
            first = True
            group = -1  # für die ganze Auswertung: gesendete Gruppe bzw. Wort
            while self._live() and not self._time_up():
                token, _ = self.source.next()
                if word_gaps or len(self.sent_log) % FULL_GROUP_LEN == 0:
                    group += 1
                if word_gaps and not first:
                    # Wortpause zwischen Gruppen bzw. Wörtern (zusätzlich zur Zeichenpause).
                    if not self._write(stream, silence(word_gap_extra_seconds(self.wpm, self.fw))):
                        break
                first = False
                for char in token:
                    if char == " ":
                        # Wortabstand innerhalb einer Wendung („TNX FER CALL“).
                        if not self._write(stream, silence(word_gap_extra_seconds(self.wpm, self.fw))):
                            break
                        group += 1
                        continue
                    conditions = self.band
                    chirp = conditions.chirp_for(0) if conditions is not None else None
                    samples = build_samples(char, self.wpm, self.freq, self.fw, chirp)
                    if not self._write(stream, samples):
                        break
                    # write() kehrt zurück, sobald die Samples im Puffer sind; zu
                    # hören ist ihr Ende erst nach stream.latency. Die Reaktionszeit
                    # zählt ab dem Ende des Tons, also vor der Pause dahinter.
                    tone_end = time.time() + stream.latency - char_gap_seconds(self.wpm, self.fw)
                    self.sent_log.append({"char": char, "end_time": tone_end, "group": group})
            if self._live():
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
            self.status_var.set(tr("Zeit abgelaufen – Durchgang ausgewertet."))

    def _write(self, stream, samples) -> bool:
        """Schreibt `samples` häppchenweise; False, wenn zwischendurch
        gestoppt wurde."""
        chunk = int(SAMPLE_RATE * WRITE_CHUNK_SECONDS)
        for start in range(0, len(samples), chunk):
            if not self._live():
                return False
            block = samples[start:start + chunk]
            conditions = self.band  # kann der GUI-Thread jederzeit tauschen (_update_band)
            stream.write(block if conditions is None else conditions.process(block, 0))
        return True

    def _tick(self):
        """Jede Sekunde: Fehler aus dem Audio-Thread melden, die vorläufige
        Trefferquote über die letzten PREVIEW_CHARS Zeichen und die eigene
        Eingabe zeigen."""
        if not self.running:
            return
        if self.audio_error:
            self.stop()
            self.status_var.set(self.audio_error)
            return
        sent_log, typed_log = list(self.sent_log), list(self.typed_log)  # Audio-Thread hängt weiter an
        window = sent_log[-PREVIEW_CHARS:]
        live = tr("Gesendet: {n} Zeichen").format(n=len(sent_log))
        if window:
            since = window[0]["end_time"] - PREVIEW_SLACK_SECONDS
            sent_str = "".join(e["char"] for e in window)
            typed_str = "".join(e["char"] for e in typed_log if e["time"] >= since)
            ops = align.align(sent_str, typed_str)
            matches = sum(1 for op in ops if op.kind == align.OpKind.MATCH)
            expected_total = sum(
                1 for op in ops if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE, align.OpKind.DELETE)
            )
            pct = (matches / expected_total * 100) if expected_total else 0.0
            if len(sent_log) > PREVIEW_CHARS:
                live += tr(" · vorläufige Trefferquote (letzte {n}): {pct:.0f}%").format(n=PREVIEW_CHARS, pct=pct)
            else:
                live += tr(" · vorläufige Trefferquote: {pct:.0f}%").format(pct=pct)
        if self.deadline is not None:
            remaining = max(int(self.deadline - time.time()), 0)
            live += " · " + tr("Restzeit {time}").format(time=f"{remaining // 60}:{remaining % 60:02d}")
        self.live_var.set(live)
        # Erst wenn auch das letzte Zeichen fertig gesendet ist (der Audio-Thread
        # hat sich beendet), läuft die Frist fürs Nachtippen.
        if self._time_up() and not self.play_thread.is_alive() and not self.finishing:
            self.finishing = True
            self.status_var.set(tr("Zeit abgelaufen – tippe die letzten Zeichen noch ein…"))
            self.root.after(FINISH_GRACE_SECONDS * 1000, self._auto_stop, self.session_id)
        self.typed_preview_var.set("".join(e["char"] for e in typed_log[-TYPED_TAIL:]))
        self.root.after(1000, self._tick)

    def stop(self):
        """Beendet die Wiedergabe (bei Stop von Hand mit Schlusszeichen) und wertet
        den ganzen Durchgang aus."""
        self.running = False
        self.band_toggle.set_locked(False)
        if self.play_thread is not None:
            self.play_thread.join(timeout=2)
            self.play_thread = None
        if not self.end_sent:
            # Manueller Stop: Schlusszeichen nachschieben (eigener Stream,
            # der Sitzungs-Stream ist schon zu).
            self.end_sent = True
            audio.play_quietly(build_text(END_TEXT, self.wpm, self.freq))
        self.start_button.config(text=tr("Start"))
        self.status_var.set(tr("Werte aus…"))
        self._finalize_session(stopped_at=None if self.finishing else time.time())
        self.status_var.set(tr("Gestoppt."))
        self.on_stop_cb()

    def _finalize_session(self, stopped_at=None):
        """Wertet aus. `stopped_at`: Zeitpunkt eines Stopps von Hand; dann
        zählen gerade erst gesendete, noch nicht getippte Zeichen nicht."""
        if self.session_stats is None:
            return
        sent_str = "".join(e["char"] for e in self.sent_log)
        typed_str = "".join(e["char"] for e in self.typed_log)
        ops = align.align(sent_str, typed_str)
        extra = 0  # Tasten ohne passendes gesendetes Zeichen
        rows = []  # (gesendet, getippt, Markierung, Gruppe) für die Gegenüberstellung
        group = 0  # überzählige Tasten gehören zur Gruppe davor
        for op in ops:
            if (op.kind == align.OpKind.DELETE and stopped_at is not None
                    and self.sent_log[op.expected_index]["end_time"] > stopped_at - STOP_GRACE_SECONDS):
                continue  # beim Stoppen gerade erst gesendet
            late = (op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE)
                    and not plausible(self.typed_log[op.received_index]["time"],
                                      self.sent_log[op.expected_index]["end_time"]))
            if op.expected_index is not None:
                group = self.sent_log[op.expected_index].get("group", op.expected_index // FULL_GROUP_LEN)
            rows.append((op.expected_char or "–", op.received_char or "–",
                         " " if op.kind == align.OpKind.MATCH and not late else "^", group))
            if op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE):
                expected_char = op.expected_char
                typed_char = op.received_char
                correct = op.kind == align.OpKind.MATCH
                play_end = self.sent_log[op.expected_index]["end_time"]
                typed_time = self.typed_log[op.received_index]["time"]
                if not plausible(typed_time, play_end):
                    # Vorausgeraten oder viel zu spät: verpasst plus überzählig.
                    self.session_stats.record_char(expected_char, "", False, 0.0, 0.0)
                    extra += 1
                    continue
                previous_key = self.typed_log[op.received_index - 1]["time"] if op.received_index else None
                latency = char_latency(typed_time, play_end, previous_key)
                since_start = tone_seconds(expected_char, self.wpm) + (latency or 0.0)
                self.session_stats.record_char(
                    expected_char, typed_char, correct, since_start,
                    effective_wpm(expected_char, since_start, self.wpm), latency=latency
                )
            elif op.kind == align.OpKind.DELETE:
                self.session_stats.record_char(op.expected_char, "", False, 0.0, 0.0)
            else:
                # INSERT: Taste ohne gesendetes Zeichen; keinem Zeichen
                # zuzuordnen, zählt aber für den Aufstieg als Fehler.
                extra += 1

        self.full_rows = rows
        self.full_button.config(state="normal" if rows else "disabled")
        self._render_full()
        tail = rows[-DIFF_TAIL:]
        if tail:
            blocks = []
            for start in range(0, len(tail), DIFF_LINE):
                line = tail[start:start + DIFF_LINE]
                blocks.append(
                    f"{tr('gesendet'):<10}" + " ".join(r[0] for r in line)
                    + f"\n{tr('getippt'):<10}" + " ".join(r[1] for r in line)
                    + "\n" + (" " * 10 + " ".join(r[2] for r in line)).rstrip())
            self.diff_var.set("\n\n".join(blocks)
                              + "\n" + " " * 10 + tr("– fehlt/zu viel, ^ falsch oder nicht rechtzeitig"))
        summary = self.session_stats.summary()
        if getattr(self, "content", "chars") == "chars":  # Klartext ist vorhersagbarer
            self.koch_result = (self.charset, max(summary["correct"] - extra, 0), summary["total"])
        self.stats_panel.refresh(summary, self.session_stats.char_rows())
        # Überzählige Tasten zählen für Lektion und Diplome als Fehler;
        # „completed“: bis zum Ende der eingestellten Dauer, nicht von Hand gestoppt.
        result = {"extra_keys": extra, "completed": self.finishing}
        if self.band_tracked:
            result.update(band_gain_min=self.band_gain_min, band_min=self.band_rank_min)
        path = self.session_stats.finalize(result)
        self._remember_result(self.session_stats, summary, extra_keys=extra, completed=self.finishing)
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None

    def show_full(self):
        """Die ganze letzte Sitzung in einem eigenen Fenster (auch für den
        Beamer): gesendet, getippt und Fehler, nach Gruppen gegliedert;
        wahlweise nur der gesendete Text zum Vergleichen mit dem Zettel."""
        if self.full_window is not None:
            self.full_window.lift()
            return
        window = tk.Toplevel(self.root)
        window.title(tr("Am Stück – ganze Auswertung"))
        window.geometry(theme.scaled_geometry(window, 900, 600))
        window.configure(background=theme.BG)
        family = tkfont.nametofont("TkFixedFont", root=window).actual("family")
        size, low, high, _ = FULL_FONT
        self.full_font = tkfont.Font(root=window, family=family, size=theme.scaled_size(size, low, high))
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="A−", width=3, command=lambda: self.zoom_full(-1)).pack(side="left")
        ttk.Button(bar, text="A+", width=3, command=lambda: self.zoom_full(1)).pack(side="left", padx=(4, 0))
        ttk.Button(bar, text=tr("Kopieren"), command=self.copy_full).pack(side="left", padx=(12, 0))
        self.sent_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text=tr("Nur gesendeter Text"), variable=self.sent_only_var,
                        command=self._render_full).pack(side="left", padx=(12, 0))
        self.full_note_var = tk.StringVar(value="")
        theme.hint(bar, textvariable=self.full_note_var).pack(side="left", padx=(12, 0))
        text = tk.Text(frame, font=self.full_font, wrap="none", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.tag_configure("error", foreground=theme.ERROR)
        text.tag_configure("number", foreground=theme.DISABLED)
        # Umbruch nach der Fensterbreite: bei geänderter Breite neu aufbauen.
        text.bind("<Configure>", lambda e: self._render_full(only_if_resized=True))
        window.bind("<Key>", self._on_full_key)
        window.protocol("WM_DELETE_WINDOW", self.close_full)
        self.full_text = text
        self.full_window = window
        self.full_width = None
        self._render_full()

    def close_full(self):
        """Schließt das Fenster mit der ganzen Auswertung."""
        if self.full_window is not None:
            self.full_window.destroy()
        self.full_window = None

    def _full_columns(self) -> int:
        """So viele Zeichen passen neben die Gruppennummer in eine Zeile."""
        width = self.full_text.winfo_width()
        if width <= 1:  # noch nicht angezeigt
            width = 880
        return max((width - 40) // max(self.full_font.measure("0"), 1) - 6, 10)

    def _render_full(self, only_if_resized=False):
        """Füllt das Auswertungsfenster neu (nach Gruppen gegliedert, auf die
        Fensterbreite umbrochen, Fehler markiert); mit `only_if_resized` nur, wenn
        sich die Breite geändert hat."""
        if self.full_window is None:
            return
        columns = self._full_columns()
        if only_if_resized and columns == self.full_width:
            return
        self.full_width = columns
        text = self.full_text
        text.config(state="normal")
        text.delete("1.0", "end")
        sent_only = self.sent_only_var.get()
        rows = [row for row in self.full_rows if row[0] != "–"] if sent_only else self.full_rows
        for number, sent, typed, marks in grouped_lines(rows, columns):
            prefix = f"{number:>4}  "
            text.insert("end", prefix, ("number",))
            text.insert("end", sent + "\n")
            if sent_only:
                continue
            line = int(text.index("end-1c").split(".")[0])
            text.insert("end", " " * len(prefix) + typed + "\n")
            text.insert("end", " " * len(prefix) + marks + "\n\n")
            for column, mark in enumerate(marks):
                if mark == "^":
                    for row in (line, line + 1):
                        text.tag_add("error", f"{row}.{len(prefix) + column}")
        if not self.full_rows:
            text.insert("end", tr("Erscheint nach dem Stoppen."))
        text.config(state="disabled")
        self.full_note_var.set("" if sent_only or not self.full_rows
                               else tr("– fehlt/zu viel, ^ falsch oder nicht rechtzeitig"))

    def _on_full_key(self, event):
        if event.keysym in ("plus", "KP_Add"):
            self.zoom_full(1)
        elif event.keysym in ("minus", "KP_Subtract"):
            self.zoom_full(-1)

    def zoom_full(self, direction: int):
        """Schrift im Auswertungsfenster eine Stufe größer (1) oder kleiner (−1)."""
        size, low, high, step = FULL_FONT
        self.full_font.configure(size=min(max(self.full_font.cget("size") + direction * step, low), high))
        self._render_full()

    def copy_full(self):
        """Kopiert den Inhalt des Auswertungsfensters in die Zwischenablage."""
        if not self.full_rows:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.full_text.get("1.0", "end").rstrip() + "\n")
        self.full_note_var.set(tr("In die Zwischenablage kopiert."))

    def on_close(self):
        """Programmende: Wiedergabe beenden und den Durchgang speichern."""
        if self.running:
            self.running = False
            if self.play_thread is not None:
                self.play_thread.join(timeout=2)
        self._finalize_session()

    def on_function_key(self, key: str):
        """F5 startet bzw. beendet den Durchgang."""
        if key == "F5":
            self.toggle_running()

    def on_key(self, event):
        """Esc beendet den Durchgang; jedes andere Morsezeichen wird mit Zeitpunkt
        für die spätere Zuordnung mitgeschrieben."""
        if event.keysym == "Escape":
            if self.running:
                self.stop()
            return
        if not self.running:
            return
        typed = event.char.upper()
        if not typed or typed not in MORSE_CODE:
            return
        self.typed_log.append({"char": typed, "time": time.time()})