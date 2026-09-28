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
Alignment-Durchlauf über die komplette Session.

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
from tkinter import ttk

import numpy as np

from morsetrainer.core import align, audio
from morsetrainer.core.morse import (
    END_TEXT, MORSE_CODE, SAMPLE_RATE, START_TEXT, build_samples, build_text,
    char_gap_seconds, code_units, silence, word_gap_extra_seconds,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.widgets import theme
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ScrollableFrame
from morsetrainer.modes.content import ItemSource

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
CONTENTS = {"Zufallszeichen": "chars", "Wörter": "words", "Wendungen": "phrases", "Rufzeichen": "calls",
            "QSO-Klartext": "qso"}

# Zeitliche Plausibilität einer Zuordnung Taste -> gesendetes Zeichen: so
# viel früher als das Tonende (Messungenauigkeit) bzw. höchstens so viel
# später darf die Taste kommen.
EARLY_TOLERANCE_SECONDS = 0.15
MAX_LAG_SECONDS = 5.0


# Beim Stoppen von Hand: so kurz vor dem Stopp gesendete Zeichen, die noch
# nicht getippt sind, zählen nicht als verpasst.
STOP_GRACE_SECONDS = 2.0
# So viele der letzten Zeichen zeigt die Gegenüberstellung nach dem Stopp.
DIFF_TAIL = 30


def plausible(typed_time: float, tone_end: float) -> bool:
    """Passt ein Tastendruck zeitlich zu einem Zeichen mit diesem Tonende?"""
    return tone_end - EARLY_TOLERANCE_SECONDS <= typed_time <= tone_end + MAX_LAG_SECONDS

# Die vorläufige Trefferquote während der Sitzung bezieht sich auf die
# zuletzt gesendeten Zeichen; die ganze Sitzung wird erst beim Stop
# ausgewertet. Getippte Zeichen zählen zum Fenster, wenn sie höchstens
# PREVIEW_SLACK_SECONDS vor dem Ende seines ersten Zeichens kamen.
PREVIEW_CHARS = 200
PREVIEW_SLACK_SECONDS = 1.0


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
        self.koch_result = None   # (Zeichensatz, richtig, gesamt) für den Koch-Aufstieg
        self.audio_error = None   # Fehlermeldung aus dem Audio-Thread

        self._build_widgets(ScrollableFrame(parent).inner)

    def _build_widgets(self, parent):
        theme.hint(
            parent, wrap=560,
            text="Der Ton läuft durch, ohne auf dich zu warten. Tippe mit, was du erkennst "
                 "– auch wenn du mal hinterherhinkst. Auswertung erfolgt beim Stoppen. "
                 "F5 startet und stoppt, Esc stoppt.",
        ).pack(anchor="w", padx=10, pady=(8, 2))

        options = theme.card(parent, "Einstellungen")
        duration = ttk.Frame(options)
        duration.pack(fill="x")
        ttk.Label(duration, text="Dauer:").pack(side="left", padx=(0, 4))
        self.duration_var = tk.IntVar(value=5)
        ttk.Spinbox(duration, from_=0, to=120, textvariable=self.duration_var, width=4).pack(side="left")
        ttk.Label(duration, text="Min.").pack(side="left", padx=(4, 0))
        theme.hint(duration, text="(0 = ohne Limit)").pack(side="left", padx=(4, 0))
        content = ttk.Frame(options)
        content.pack(fill="x", pady=(2, 0))
        ttk.Label(content, text="Inhalt:").pack(side="left", padx=(0, 4))
        self.content_var = tk.StringVar(value="Zufallszeichen")
        ttk.Combobox(content, textvariable=self.content_var, values=list(CONTENTS), state="readonly",
                     width=14).pack(side="left")
        theme.hint(content, text="(Klartext zählt nicht für die Lektion)").pack(side="left", padx=(6, 0))
        grouping = ttk.Frame(options)
        grouping.pack(fill="x", pady=(2, 0))
        ttk.Label(grouping, text="Gruppen zu").pack(side="left", padx=(0, 4))
        self.group_len_var = tk.IntVar(value=DEFAULT_GROUP_LEN)
        group_len_box = ttk.Spinbox(grouping, from_=GROUP_LEN_RANGE[0], to=GROUP_LEN_RANGE[1],
                                    textvariable=self.group_len_var, width=3)
        group_len_box.pack(side="left")
        # Gruppenlänge gilt nur für Zufallszeichen; Klartext hat seine Wörter.
        self.content_var.trace_add("write", lambda *_: group_len_box.state(
            ["!disabled"] if self.content_var.get() == "Zufallszeichen" else ["disabled"]))
        ttk.Label(grouping, text="Zeichen").pack(side="left", padx=(4, 0))
        theme.hint(grouping, text="(mit Wortpause dazwischen; 0 = durchgehend)").pack(side="left", padx=(4, 0))

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text="Start", style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")

        self.status_var = tk.StringVar(value="Bereit. Drücke Start.")
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel").pack(pady=(14, 6))

        self.live_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.live_var).pack(anchor="w", padx=10)

        self.diff_box = theme.card(parent, "Auswertung (letzte Zeichen)")
        self.diff_var = tk.StringVar(value="Erscheint nach dem Stoppen.")
        ttk.Label(self.diff_box, textvariable=self.diff_var, font=theme.MONO, justify="left").pack(anchor="w")

        typed = theme.card(parent, "Deine Eingabe (letzte Zeichen)")
        self.typed_preview_var = tk.StringVar(value="")
        ttk.Label(typed, textvariable=self.typed_preview_var, font=theme.MONO, wraplength=540).pack(anchor="w")

        self.stats_panel = StatsPanel(parent)

    def settings(self) -> dict:
        data = {"content": CONTENTS.get(self.content_var.get())}
        for key, var in (("duration", self.duration_var), ("group_len", self.group_len_var)):
            try:
                data[key] = var.get()
            except tk.TclError:
                pass
        return data

    def restore_settings(self, data: dict) -> None:
        for label, key in CONTENTS.items():
            if data.get("content") == key:
                self.content_var.set(label)
        for key, var, limits in (("duration", self.duration_var, (0, 120)),
                                 ("group_len", self.group_len_var, GROUP_LEN_RANGE)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                var.set(value)

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
        self.koch_result = None
        self.audio_error = None
        self.session_id += 1
        self.charset = charset
        self.wpm = self.wpm_var.get()
        self.freq = self.freq_var.get()
        self.fw = self.farnsworth_wpm()
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
                                          group_len=self.group_len or None)
        self.stats_panel.reset()
        self.live_var.set("Gesendet: 0 Zeichen")
        self.typed_preview_var.set("")
        self.diff_var.set("Erscheint nach dem Stoppen.")

        self.running = True
        self.start_button.config(text="Stop")
        self.status_var.set("Läuft – höre zu und tippe mit…")
        self.on_start_cb()

        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        self.root.after(1000, self._tick)

    def _play_loop(self):
        try:
            self._play_session()
        except audio.ERRORS as exc:
            self.audio_error = audio.describe(exc)  # _tick beendet die Sitzung

    def _play_session(self):
        # Ein durchgehender Stream für die ganze Sitzung: Zeichen werden
        # lückenlos hintergeschrieben. Ein eigener Stream pro Zeichen
        # (sd.play + sd.wait) knackt beim Öffnen/Schließen und reißt Lücken.
        with audio.output_stream() as stream:
            # Einleitung, wird nicht ausgewertet (landet nicht in sent_log).
            if not self._write(stream, build_text(START_TEXT + " ", self.wpm, self.freq, self.fw)):
                return
            word_gaps = self.content != "chars" or self.group_len
            first = True
            while self.running and not self._time_up():
                token, _ = self.source.next()
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
                        continue
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
        if self.audio_error:
            self.stop()
            self.status_var.set(self.audio_error)
            return
        sent_log, typed_log = list(self.sent_log), list(self.typed_log)  # Audio-Thread hängt weiter an
        window = sent_log[-PREVIEW_CHARS:]
        live = f"Gesendet: {len(sent_log)} Zeichen"
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
            scope = f" (letzte {PREVIEW_CHARS})" if len(sent_log) > PREVIEW_CHARS else ""
            live += f" · vorläufige Trefferquote{scope}: {pct:.0f}%"
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
        self.typed_preview_var.set("".join(e["char"] for e in typed_log[-60:]))
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
            audio.play_quietly(build_text(END_TEXT, self.wpm, self.freq))
        self.start_button.config(text="Start")
        self.status_var.set("Werte aus…")
        self._finalize_session(stopped_at=None if self.finishing else time.time())
        self.status_var.set("Gestoppt.")
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
        rows = []  # (gesendet, getippt, Markierung) für die Gegenüberstellung
        for op in ops:
            if (op.kind == align.OpKind.DELETE and stopped_at is not None
                    and self.sent_log[op.expected_index]["end_time"] > stopped_at - STOP_GRACE_SECONDS):
                continue  # beim Stoppen gerade erst gesendet
            late = (op.kind in (align.OpKind.MATCH, align.OpKind.SUBSTITUTE)
                    and not plausible(self.typed_log[op.received_index]["time"],
                                      self.sent_log[op.expected_index]["end_time"]))
            rows.append((op.expected_char or "–", op.received_char or "–",
                         " " if op.kind == align.OpKind.MATCH and not late else "^"))
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
                reaction_time = max(typed_time - play_end, 0.001)
                effective_wpm = code_units(expected_char) * 1.2 / reaction_time
                self.session_stats.record_char(
                    expected_char, typed_char, correct, reaction_time, effective_wpm, latency=reaction_time
                )
            elif op.kind == align.OpKind.DELETE:
                self.session_stats.record_char(op.expected_char, "", False, 0.0, 0.0)
            else:
                # INSERT: Taste ohne gesendetes Zeichen; keinem Zeichen
                # zuzuordnen, zählt aber für den Aufstieg als Fehler.
                extra += 1

        tail = rows[-DIFF_TAIL:]
        if tail:
            self.diff_var.set(
                "gesendet  " + " ".join(r[0] for r in tail) + "\ngetippt   " + " ".join(r[1] for r in tail)
                + "\n          " + " ".join(r[2] for r in tail).rstrip() + "\n          – fehlt/zu viel, ^ falsch oder nicht rechtzeitig"
            )
        summary = self.session_stats.summary()
        if getattr(self, "content", "chars") == "chars":  # Klartext ist vorhersagbarer
            self.koch_result = (self.charset, max(summary["correct"] - extra, 0), summary["total"])
        self.stats_panel.refresh(summary, self.session_stats.char_rows())
        path = self.session_stats.finalize()
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None

    def on_close(self):
        if self.running:
            self.running = False
            if self.play_thread is not None:
                self.play_thread.join(timeout=2)
        self._finalize_session()

    def on_function_key(self, key: str):
        if key == "F5":
            self.toggle_running()

    def on_key(self, event):
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