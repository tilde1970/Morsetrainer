"""Einzelzeichen-Modus: spielt ein Morsezeichen ab, wartet auf Tastatureingabe,
prüft die Antwort und spielt danach das nächste Zeichen.

Nach einem Fehler (falsch oder zu langsam) wird das Zeichen noch einmal
vorgespielt, während die Lösung dasteht, damit Klang und Buchstabe
zusammenkommen. Abgefragt wird es erst wieder nach ein paar anderen
Zeichen und ohne Ankündigung: Käme es sofort, wüsste man die Antwort
schon, bevor man hinhört. Bei kleinen Zeichensätzen (unter RETRY_EXCLUDE_MIN
Zeichen) wird das vorgemerkte Zeichen dazwischen nicht ausgeschlossen,
sonst stünde die Folge fest (bei K und M käme bis dahin sicher nur M).

Die Rückmeldung nennt die Zeit bis zum Tastendruck in Sekunden, gezählt
wie das Zeitlimit ab dem Ende des Zeichens samt folgender Zeichenpause,
und daneben das aktuelle Limit (eine WPM-Angabe hinge von der
Zeichenlänge ab). War die Antwort ein anderes Zeichen, klingt beim
Korrekturton richtig – getippt – richtig: „So klingt K – und so M“.

Die Leertaste wiederholt das Zeichen, verlängert aber die Frist nicht, und
ein erst nach der Wiederholung erkanntes Zeichen gilt als nicht erkannt.

Zeitlimit (Instant Character Recognition): Wer nach dem Ton nicht innerhalb
des Limits tippt, hat das Zeichen verpasst. So bleibt keine Zeit, Punkte
und Striche zu zählen; das Zeichen muss als Reflex kommen. Das Limit passt
sich an: jede schnelle richtige Antwort macht es etwas kürzer, jedes
Verpassen deutlich länger (nur beim ersten Hören eines Zeichens). Eine
falsche Antwort in der Zeit lässt es, wie es ist: Wer verwechselt, braucht
den Korrekturton, nicht mehr Zeit – sonst wüchse das Limit bei vielen
Verwechslungen, bis wieder Zeit zum Zählen bleibt. Die Faktoren sind so
gewählt, dass sich das Limit dort einpendelt, wo von den nicht
verwechselten Zeichen knapp neun von zehn rechtzeitig kommen (ICR_FASTER, ICR_SLOWER); bei gleich
großen Schritten wäre jedes dritte Zeichen „zu langsam“, egal wie gut man
ist. In der Tagesübung wächst es höchstens bis review.FLUENT_LATENCY_S:
Langsamer zählt in der Lernkartei ohnehin nicht als flüssig. Unter ICR_RANGE[0] sinkt es nie: Schon die einfache
Reaktion auf einen Ton braucht etwa 0,15–0,2 s, dazu kommen das Erkennen
unter mehreren Zeichen und der Griff zur Taste. Darunter würde
Reaktionsschnelle geübt, nicht das Erkennen.
Das Limit ist standardmäßig an; ohne kann man Punkte und Striche zählen,
und genau diese Gewohnheit bremst später."""
import random
import time
import tkinter as tk
from tkinter import ttk

import numpy as np

from morsetrainer.core import audio, koch, review, sfx
from morsetrainer.core.morse import (
    AUDIO_LATENCY, MORSE_CODE, display_text, SAMPLE_RATE, build_samples, effective_wpm, silence, tone_seconds,
    vary_voice,
)
from morsetrainer.core.stats import SessionStats
from morsetrainer.modes.daily_support import DailyModeMixin
from morsetrainer.i18n import number, tr
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ScrollableFrame
from morsetrainer.core.weighting import CharPicker

# Zeitlimit in Sekunden ab Tonende: Start, Grenzen und Faktoren pro Antwort.
ICR_START = 2.0
ICR_RANGE = (0.5, 3.0)
# Gleichgewicht bei p · ln(FASTER) + (1 − p) · ln(SLOWER) = 0, also
# p ≈ 0,88 rechtzeitig richtig unter den richtigen und verpassten Zeichen
# (Verwechslungen ändern das Limit nicht).
ICR_FASTER = 0.97
ICR_SLOWER = 1.25
# Ein falsch erkanntes Zeichen kommt nach so vielen anderen wieder.
RETRY_AFTER = (2, 4)
# Pause nach der Rückmeldung bzw. nach dem Korrekturton, in ms.
FEEDBACK_MS = 700
AFTER_CORRECTION_MS = 600
# Ab so vielen verschiedenen Zeichen werden vorgemerkte Zeichen bis zu ihrer
# erneuten Abfrage aus der Zufallsauswahl genommen.
RETRY_EXCLUDE_MIN = 5
# Pause zwischen richtigem und getipptem Zeichen beim Korrekturton.
COMPARE_GAP_SECONDS = 0.6
# Hinweis auf die Gruppen nur, wenn das Zeitlimit am Ende höchstens so lang ist.
GROUPS_HINT_MAX_LIMIT = 1.5
# So viele Antworten zeigt „Verlauf“ (✓/✗).
HISTORY_LEN = 40


def next_limit(limit: float, in_time_and_correct: bool, upper: float = ICR_RANGE[1]) -> float:
    """Nach einer richtigen Antwort in der Zeit (True) bzw. einem verpassten
    Zeichen (False)."""
    factor = ICR_FASTER if in_time_and_correct else ICR_SLOWER
    return round(min(max(limit * factor, ICR_RANGE[0]), max(upper, ICR_RANGE[0])), 2)


class RetryQueue:
    """Falsch erkannte Zeichen, die nach einigen anderen Zeichen erneut
    abgefragt werden. next_due() wird einmal je neuem Zeichen aufgerufen."""

    def __init__(self, rng=random):
        self.rng = rng
        self.waiting = {}  # Zeichen -> Anzahl anderer Zeichen, die noch davor kommen

    def add(self, ch: str) -> None:
        """Merkt `ch` zur erneuten Abfrage nach zufällig RETRY_AFTER anderen Zeichen
        vor."""
        self.waiting[ch] = self.rng.randint(*RETRY_AFTER)

    def next_due(self):
        """Das fällige Zeichen (und aus der Liste nehmen) oder None; dann
        rückt die Wartezeit aller anderen um eins vor."""
        for ch, remaining in self.waiting.items():
            if remaining <= 0:
                del self.waiting[ch]
                return ch
        for ch in self.waiting:
            self.waiting[ch] -= 1
        return None

    def discard(self, ch: str) -> None:
        """Nimmt `ch` aus der Warteliste (etwa weil es zufällig schon wieder dran
        war)."""
        self.waiting.pop(ch, None)


class SingleModeFrame(DailyModeMixin):
    """Reiter Einzelzeichen: ein Zeichen hören, sofort die Taste drücken. Mit
    Zeitlimit (ICR) wird das Limit nach jeder Antwort enger oder weiter;
    falsche Zeichen kommen bald wieder und werden mit dem Getippten zum
    Vergleich vorgespielt."""
    uses_vary = True
    # Das Limit gehört dazu: die Tagesübung beginnt mit eigenem Startwert
    # (daily_runner.py), danach gilt wieder das Limit des Reiters.
    daily_keys = ("icr", "icr_limit")

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
        self.retries = RetryQueue()
        self.correcting = False     # Korrekturton läuft, keine Eingabe erwartet
        # (Zeichensatz, richtig, gesamt) eines Durchgangs mit Zeitlimit; die
        # App bietet danach ggf. den Wechsel zu den Gruppen an.
        self.groups_result = None
        self.icr_whole_session = False  # Zeitlimit den ganzen Durchgang an
        self.deadline = None        # Frist für das aktuelle Zeichen (time.time()), ab erstem Hören
        self.replayed = False       # aktuelles Zeichen mit der Leertaste wiederholt
        self.last_typed = None      # falsche Antwort, zum Vergleich mit vorgespielt
        self.block_end = None       # Ende eines Tagesübungs-Blocks (time.time())

        self._build_widgets(ScrollableFrame(parent).inner)

    def _build_widgets(self, parent):
        """Baut den Reiter: Erklärung, Zeitlimit, Start und Wiederholen, Anzeige von
        Zeichen und Rückmeldung, Verlauf und Statistik."""
        options = self.options_card = theme.card(parent, tr("Einstellungen"))
        icr = ttk.Frame(options)
        icr.pack(fill="x")
        self.icr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            icr, text=tr("Zeitlimit (wird kürzer, solange du sicher bist)"), variable=self.icr_var,
            command=self._on_icr_toggle,
        ).pack(side="left")
        self.limit_var = tk.StringVar(value="")
        theme.hint(icr, textvariable=self.limit_var).pack(side="left", padx=(8, 0))
        ttk.Button(icr, text=tr("zurücksetzen"), command=self._reset_limit).pack(side="right")
        self.sound_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text=tr("Quittungston"), variable=self.sound_var).pack(anchor="w")
        self._show_limit()

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Start"), style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")
        self.repeat_button = ttk.Button(
            controls, text=tr("Wiederholen (Leertaste)"), command=self.repeat_char, state="disabled"
        )
        self.repeat_button.pack(side="left", padx=8)

        self.status_var = tk.StringVar(value=tr("Bereit. Drücke Start."))
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel").pack(pady=(14, 4))

        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = ttk.Label(parent, textvariable=self.feedback_var, style="Feedback.TLabel")
        self.feedback_label.pack(pady=(4, 10))

        self.stats_panel = StatsPanel(parent)

        history = theme.card(parent, tr("Verlauf (letzte {n})").format(n=HISTORY_LEN))
        self.history_var = tk.StringVar(value="")
        ttk.Label(history, textvariable=self.history_var, font=theme.MONO, wraplength=520).pack(anchor="w")

    def _on_icr_toggle(self):
        if self.running:
            # Mitten im Durchgang umgeschaltet: der Durchgang zählt nicht als
            # durchgehend mit Zeitlimit (Gruppen-Hinweis).
            self.icr_whole_session = False
        self._show_limit()

    def _show_limit(self):
        self.limit_var.set(f"{number(self.limit, 2)} s" if self.icr_var.get() else "")

    def _limit_max(self) -> float:
        return review.FLUENT_LATENCY_S if self.daily_minutes else ICR_RANGE[1]

    def _reset_limit(self):
        self.limit = ICR_START
        self._show_limit()

    def settings(self) -> dict:
        """Einstellungen zum Speichern: Zeitlimit an/aus und sein aktueller Wert."""
        return {"icr": self.icr_var.get(), "icr_limit": self.limit}

    def restore_settings(self, data: dict) -> None:
        """Gegenstück zu settings(); das Limit wird auf ICR_RANGE begrenzt."""
        if isinstance(data.get("icr"), bool):
            self.icr_var.set(data["icr"])
        limit = data.get("icr_limit")
        if isinstance(limit, (int, float)) and not isinstance(limit, bool) and limit > 0:
            # Gespeicherte Werte können außerhalb von ICR_RANGE liegen: begrenzen.
            self.limit = min(max(float(limit), ICR_RANGE[0]), ICR_RANGE[1])
        self._show_limit()

    def on_function_key(self, key: str):
        """F5 startet bzw. beendet den Durchgang, wie der Knopf (nicht, wenn
        er gerade gesperrt ist, etwa in der Tagesübung)."""
        if key == "F5" and not self.start_button.instate(["disabled"]):
            self.toggle_running()

    def toggle_running(self):
        """Durchgang starten bzw. beenden (Start/Stop-Knopf)."""
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        """Beginnt einen Durchgang mit dem Zeichensatz der Kopfleiste (nur gültige
        Zeichen) und spielt das erste Zeichen."""
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set(tr("Kein gültiges Zeichen im Zeichensatz!"))
            return
        self.charset = charset
        self.running = True
        self.retries = RetryQueue()
        self.correcting = False
        self.icr_whole_session = self.icr_var.get()
        self.block_end = self._daily_deadline()
        self.start_button.config(text=tr("Stop"))
        self.repeat_button.config(state="normal")
        self.feedback_var.set("")
        self.session_stats = SessionStats("single", charset, self.wpm_var.get(), self.freq_var.get(),
                                          review_promote=True,
                                          config_extra={"lesson": koch.lesson_of(charset), **self._daily_config()})
        self.picker = CharPicker(charset, self.weighted_var.get(), self.session_stats)
        self.history = []
        self.history_var.set("")
        self._count_streak()
        self.stats_panel.reset()
        self.on_start_cb()
        self.next_char()

    def stop(self):
        """Beendet den Durchgang, speichert die Statistik und gibt die Reiter frei."""
        self.running = False
        self.waiting_for_input = False
        self.timeout_token += 1
        self.start_button.config(text=tr("Start"))
        self.repeat_button.config(state="disabled")
        audio.stop()
        self._finalize_session()
        self.status_var.set(tr("Gestoppt."))
        self.on_stop_cb()

    def _finalize_session(self):
        if self.session_stats is None:
            return
        summary = self.session_stats.summary()
        if self.icr_whole_session and self.limit <= GROUPS_HINT_MAX_LIMIT:
            self.groups_result = (self.charset, summary["correct"], summary["total"])
        path = self.session_stats.finalize()
        self._remember_result(self.session_stats, summary)
        self.stats_panel.show_saved(path, self.session_stats.log_error)
        self.session_stats = None

    def on_close(self):
        """Programmende: laufenden Durchgang abschließen und speichern."""
        self._finalize_session()

    def next_char(self):
        """Wählt das nächste Zeichen (vorgemerkte Fehler zuerst, sonst gewichtet
        zufällig) und spielt es; endet ein Block der Tagesübung, ist hier Schluss."""
        if not self.running:
            return
        if self.block_end is not None and time.time() >= self.block_end:
            # Tagesübung: der Block endet zwischen zwei Zeichen, nie mitten in einer Antwort.
            self.stop()
            return
        self.waiting_for_input = False
        self.correcting = False
        self.replayed = False
        self.deadline = None
        due = self.retries.next_due()
        if due is not None:
            self.current_char = due
        elif len(set(self.charset)) >= RETRY_EXCLUDE_MIN:
            # Vorgemerkte Zeichen nicht vorzeitig ziehen (sie sind nach dem
            # Fehler gerade die mit dem höchsten Gewicht).
            self.current_char = self.picker.pick(exclude="".join(self.retries.waiting))
        else:
            # Wenige Zeichen: Ausschließen machte die Folge vorhersagbar. Kommt
            # das vorgemerkte Zeichen zufällig dran, ist die Abfrage erledigt.
            self.current_char = self.picker.pick()
            self.retries.discard(self.current_char)
        self.voice = self._pick_voice()
        # Eine erneute Abfrage zählt wie ein erstes Hören (auch fürs Zeitlimit):
        # dazwischen lagen andere Zeichen.
        self.first_hearing = True
        self.feedback_var.set("")
        self.status_var.set(tr("Höre zu…"))
        self.play_current()

    def _after_error(self, play_correction=True):
        """Falsches oder verpasstes Zeichen: später erneut abfragen und es
        jetzt, mit der Lösung vor Augen, noch einmal vorspielen (entfällt,
        wenn es nach der Wiederholung richtig war)."""
        self.retries.add(self.current_char)
        self.correcting = True
        self.timeout_token += 1
        token = self.timeout_token
        if play_correction:
            self.root.after(FEEDBACK_MS, self._play_correction, token)
        else:
            self.root.after(FEEDBACK_MS, self._after_correction, token)

    def _play_correction(self, token):
        """Nach einem Fehler: das richtige Zeichen vorspielen, bei einer
        Verwechslung zum Vergleich auch das getippte und zum Schluss noch einmal
        das richtige."""
        if not self.running or token != self.timeout_token:
            return
        wpm, freq = self.voice
        samples = build_samples(self.current_char, wpm, freq)
        typed = self.last_typed
        if typed and typed != self.current_char:
            # Richtig und Getipptes direkt nacheinander: so hört man den Unterschied.
            self.status_var.set(tr("So klingt {char} – und so {typed} (dein Tipp):").format(
                char=display_text(self.current_char), typed=display_text(typed)))
            # Zum Schluss nochmal das richtige, damit dieses Klangbild bleibt.
            samples = np.concatenate([samples, silence(COMPARE_GAP_SECONDS), build_samples(typed, wpm, freq),
                                      silence(COMPARE_GAP_SECONDS), samples])
        else:
            self.status_var.set(tr("So klingt {char}:").format(char=display_text(self.current_char)))
        try:
            audio.play(samples)
        except audio.AudioError as exc:
            self.stop()
            announcer.problem(self.status_var, str(exc))
            return
        dur_ms = int(len(samples) / SAMPLE_RATE * 1000) + int(AUDIO_LATENCY * 1000)
        self.root.after(dur_ms + AFTER_CORRECTION_MS, self._after_correction, token)

    def _after_correction(self, token):
        if self.running and token == self.timeout_token:
            self.next_char()

    def _pick_voice(self):
        # Falls das WPM-/Tonhöhe-Feld gerade mitten im Bearbeiten ist (z. B.
        # Feld geleert, um eine neue Zahl einzutippen), ist der Wert kurzzeitig
        # ungültig; dann den zuletzt bekannten Wert weiterverwenden statt
        # abzustürzen.
        """(WpM, Tonhöhe) für das nächste Zeichen: aus der Kopfleiste (bei
        ungültigem Feld der letzte Wert), mit „variieren“ leicht gestreut."""
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
        """Spielt das aktuelle Zeichen und merkt den hörbaren Beginn für die
        Reaktionszeit; ohne Tonausgabe endet der Durchgang mit Meldung."""
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
            announcer.problem(self.status_var, str(exc))
            return
        # Die Eingabe öffnet mit dem hörbaren Ende des letzten Elements: die
        # Reflexantwort, um die es beim Zeitlimit geht, darf nicht verfallen.
        dur_ms = int((tone_seconds(self.current_char, wpm) + AUDIO_LATENCY) * 1000)
        self.root.after(dur_ms, self.on_playback_done)

    def on_playback_done(self):
        """Ton zu Ende: Eingabe freigeben und, mit Zeitlimit, die Frist ab dem
        ersten Hören setzen."""
        if not self.running:
            return
        self.waiting_for_input = True
        self.status_var.set(tr("Deine Eingabe?"))
        if self.icr_var.get():
            # Das Limit zählt ab dem gleichen Zeitpunkt wie die Latenz, und
            # zwar ab dem ersten Hören: Wiederholen verschafft keine Zeit.
            if self.deadline is None:
                self.deadline = self.play_start_time + tone_seconds(self.current_char, self.voice[0]) + self.limit
            token = self.timeout_token
            self.root.after(max(int((self.deadline - time.time()) * 1000), 50), self._on_timeout, token)

    def _on_timeout(self, token):
        """Zeitlimit abgelaufen: als verpasst werten, das Limit lockern (nur beim
        ersten Hören), Fehlerton und Korrektur."""
        if not self.running or not self.waiting_for_input or token != self.timeout_token:
            return
        self.waiting_for_input = False
        wpm = self.voice[0]
        reaction_time = tone_seconds(self.current_char, wpm) + self.limit
        self.session_stats.record_char(
            self.current_char, "", False, reaction_time, effective_wpm(self.current_char, reaction_time, wpm)
        )
        if self.first_hearing:
            self.limit = next_limit(self.limit, False, self._limit_max())
            self._show_limit()
        if self.sound_var.get() and not announcer.active():
            sfx.play_error()
        self.last_typed = None
        text = tr("Zu langsam: war {char}").format(char=display_text(self.current_char))
        if self.first_hearing and not self.daily_minutes:
            text += "  " + tr("(Limit jetzt {limit} s)").format(limit=number(self.limit, 2))
        self.feedback_var.set(text)
        self.feedback_label.config(foreground=theme.ERROR)
        self._add_history(False)
        announcer.say(tr("Zu langsam. Es war {char}.").format(char=announcer.spell(self.current_char)),
                      then=self._after_error)

    def _add_history(self, correct: bool):
        self._count_streak(correct)
        self.history.append(correct)
        self.history = self.history[-HISTORY_LEN:]
        self.history_var.set("".join("✓" if ok else "✗" for ok in self.history))
        self.stats_panel.refresh(self.session_stats.summary(), self.session_stats.char_rows())

    def repeat_char(self):
        # Nur solange eine Antwort erwartet wird; in der Pause nach einer
        # Antwort würde sonst dasselbe Zeichen ein zweites Mal gewertet.
        """Leertaste: das aktuelle Zeichen noch einmal (zählt danach als nicht auf
        Anhieb erkannt)."""
        if self.running and self.current_char and self.waiting_for_input and not self.correcting:
            self.first_hearing = False
            self.replayed = True
            self.waiting_for_input = False
            self.status_var.set(tr("Höre zu… (Wiederholung)"))
            self.play_current()

    def on_key(self, event):
        """Taste im Reiter: Leertaste wiederholt, ein Zeichen ist die Antwort
        (gewertet nach richtig, Zeit und Wiederholung)."""
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
        # Erst nach dem Wiederholen erkannt zählt als nicht erkannt.
        helped = correct and self.replayed
        self.last_typed = typed

        reaction_time = max(time.time() - self.play_start_time, 0.001)
        measured_wpm = effective_wpm(self.current_char, reaction_time, self.voice[0])
        latency = max(reaction_time - tone_seconds(self.current_char, self.voice[0]), 0.0)
        if helped:
            self.session_stats.record_char(self.current_char, "", False, reaction_time, measured_wpm)
        else:
            self.session_stats.record_char(
                self.current_char, typed, correct, reaction_time, measured_wpm, latency=latency
            )
        if self.icr_var.get() and self.first_hearing and correct:
            self.limit = next_limit(self.limit, True, self._limit_max())
            self._show_limit()

        if helped:
            self.feedback_var.set(tr("{char} – erst nach Wiederholung, kommt gleich noch mal").format(
                char=display_text(self.current_char)))
            self.feedback_label.config(foreground=theme.MUTED)
        elif correct:
            # Mit Ansage nur der kurze Ton: ein Wort nach jedem Zeichen hielte auf.
            if self.sound_var.get() or announcer.active():
                sfx.play_ok()
            text = tr("Richtig: {text}").format(text=display_text(self.current_char))
            if not self.daily_minutes:
                # In der Tagesübung ohne Zahlen: bis zum nächsten Zeichen
                # bleibt keine Zeit zum Lesen.
                shown = f"{number(max(latency, 0), 2)} s"
                if self.icr_var.get():
                    shown += tr(", Limit {limit} s").format(limit=number(self.limit, 2))
                text += f"  ({shown})"
            self.feedback_var.set(text)
            self.feedback_label.config(foreground=theme.OK)
        else:
            if self.sound_var.get() and not announcer.active():
                sfx.play_error()
            self.feedback_var.set(tr("Falsch: war {char}, du: {typed}").format(
                char=display_text(self.current_char), typed=display_text(typed)))
            self.feedback_label.config(foreground=theme.ERROR)

        self._add_history(correct and not helped)
        if helped:
            announcer.say(tr("Erst nach Wiederholung: {char}.").format(char=announcer.spell(self.current_char)),
                          then=lambda: self._after_error(play_correction=False))
        elif correct:
            token = self.timeout_token
            self.root.after(FEEDBACK_MS, self._after_correction, token)
        else:
            announcer.say(tr("Falsch. {char}, nicht {typed}.").format(char=announcer.spell(self.current_char),
                                                                       typed=announcer.spell(typed)),
                          then=self._after_error)