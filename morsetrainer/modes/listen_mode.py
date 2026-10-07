"""Hören & Sagen: ohne Tastatur üben, wie bei Morse Code Ninja.

Ablauf je Eintrag: Morsezeichen – Denkpause, in der du laut sagst, was du
gehört hast – eine Stimme sagt die Lösung an (Piper, core/speech.py) –
wahlweise noch einmal das Morsezeichen, damit das Klangbild mit der Lösung
im Ohr bleibt. Sprechen statt Tippen: Das Zeichen wird als Klangbild
erkannt und nicht über die Finger übersetzt, und man kann dabei spazieren
gehen oder Auto fahren.

Inhalte: Zeichen, Gruppen, Wörter, Wendungen und Rufzeichen, jeweils nur
aus dem eingestellten Zeichensatz. Die Ansage buchstabiert im
Buchstabieralphabet (Alfa, Bravo …) und nennt bei Wörtern und Wendungen
auf Wunsch die Bedeutung.

Derselbe Ablauf lässt sich als MP3 speichern (core/mp3.py), zum Hören
unterwegs. Weil es keine Eingabe gibt, zählt Hören & Sagen nicht für
Statistik und Lektion, nur für die Übungszeit. F5 startet und stoppt,
Esc stoppt, die Leertaste spielt den aktuellen Eintrag noch einmal."""
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

import numpy as np

from morsetrainer.core import audio, mp3, speech, words
from morsetrainer.core.morse import (
    AUDIO_LATENCY, MORSE_CODE, SAMPLE_RATE, build_text, display_text, silence, vary_voice,
)
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.content import ItemSource
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.ui_widgets import ChoiceButtons, ScrollableFrame

CONTENTS = {N_("Zeichen"): "chars", N_("Gruppen"): "groups", N_("Wörter"): "words", N_("Wendungen"): "phrases",
            N_("Rufzeichen"): "calls"}
# Buchstabiert wird immer im Buchstabieralphabet: Es ist eindeutig (B und D,
# M und N klingen als Buchstabennamen ähnlich) und wie im Funkbetrieb.
ALPHABET = "nato"
DEFAULT_COUNT = 50
COUNT_RANGE = (5, 500)
# Knapp: Wer länger hat, zählt Punkte und Striche, statt das Klangbild zu erkennen.
DEFAULT_PAUSE = 1.0
PAUSE_RANGE = (0.5, 10.0)
GROUP_LEN_RANGE = (2, 8)
# Pause nach der Ansage bis zum nächsten Eintrag.
GAP_AFTER_S = 1.2
# Kurze Pause zwischen Ansage und nochmaligem Morsezeichen.
REPLAY_GAP_S = 0.5


class ListenModeFrame:
    """Reiter Sprechen („Hören & Sagen“): Morsezeichen, eine Denkpause zum
    lauten Nachsprechen, dann sagt eine Stimme die Lösung an und das Zeichen
    kommt noch einmal. Ohne Tastatur; auch als MP3 für unterwegs."""
    uses_vary = True

    def __init__(self, parent, charset_var, wpm_var, freq_var, weighted_var, farnsworth_wpm, on_start, on_stop,
                 vary_var=None):
        self.root = parent.winfo_toplevel()
        self.charset_var = charset_var
        self.wpm_var = wpm_var
        self.freq_var = freq_var
        self.weighted_var = weighted_var
        self.farnsworth_wpm = farnsworth_wpm
        self.vary_var = vary_var
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop

        self.running = False
        self.exporting = False
        self.session_id = 0
        self.source = None
        self.current = None      # (Text, Bedeutung, WPM, Hz) des aktuellen Eintrags
        self.done = 0
        self.total = 0
        self._build_widgets(ScrollableFrame(parent).inner)

    # --- Widgets --------------------------------------------------------
    def _build_widgets(self, parent):
        """Baut den Reiter: oben die Wahl des Inhalts (wie in Einzeln und Am
        Stück), Ansage-Optionen, Start und MP3-Knopf, Lösung, Bedeutung und
        Fortschritt."""
        content = ttk.Frame(parent, padding=(8, 6, 8, 0))
        content.pack(fill="x")
        ttk.Label(content, text=tr("Inhalt:")).pack(side="left", padx=(0, 8))
        self.content_var = tk.StringVar(value="Zeichen")
        self.content_buttons = ChoiceButtons(content, self.content_var, CONTENTS, tr("Inhalt"))
        self.content_buttons.pack(side="left")
        theme.hint(
            parent, wrap=560,
            text=tr("Ohne Tastatur üben: Du hörst das Morsezeichen und sagst in der Pause laut, was du "
                    "erkannt hast. Dann sagt eine Stimme die Lösung an. Sprechen statt tippen trainiert "
                    "das Klangbild – und geht auch beim Spazierengehen. Als MP3 gespeichert läuft die "
                    "Übung auf Handy oder im Auto. F5 startet und stoppt, Leertaste wiederholt."),
        ).pack(anchor="w", padx=8, pady=(4, 2))

        options = theme.card(parent, tr("Einstellungen"))
        row = ttk.Frame(options)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=tr("Gruppen zu")).pack(side="left", padx=(0, 4))
        self.group_len_var = tk.IntVar(value=5)
        self.group_len_box = ttk.Spinbox(row, from_=GROUP_LEN_RANGE[0], to=GROUP_LEN_RANGE[1],
                                         textvariable=self.group_len_var, width=3)
        self.group_len_box.pack(side="left")
        ttk.Label(row, text=tr("Zeichen", context="Einheit")).pack(side="left", padx=(4, 0))
        # Gruppenlänge gilt nur für den Inhalt Gruppen.
        self.content_var.trace_add("write", lambda *_: self.group_len_box.state(
            ["!disabled"] if self.content_var.get() == "Gruppen" else ["disabled"]))
        self.content_var.set(self.content_var.get())

        row = ttk.Frame(options)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=tr("Anzahl:")).pack(side="left", padx=(0, 4))
        self.count_var = tk.IntVar(value=DEFAULT_COUNT)
        ttk.Spinbox(row, from_=COUNT_RANGE[0], to=COUNT_RANGE[1], increment=5, textvariable=self.count_var,
                    width=5).pack(side="left")
        ttk.Label(row, text=tr("Denkpause:")).pack(side="left", padx=(12, 4))
        self.pause_var = tk.DoubleVar(value=DEFAULT_PAUSE)
        ttk.Spinbox(row, from_=PAUSE_RANGE[0], to=PAUSE_RANGE[1], increment=0.5, textvariable=self.pause_var,
                    width=5, format="%.1f").pack(side="left")
        ttk.Label(row, text=tr("s (+0,3 s je Zeichen)")).pack(side="left", padx=(4, 0))

        row = ttk.Frame(options)
        row.pack(fill="x", pady=1)
        self.whole_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text=tr("Wörter und Wendungen als Ganzes ansagen"), variable=self.whole_var).pack(
            side="left")
        self.meaning_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text=tr("Beim Buchstabieren mit Bedeutung"), variable=self.meaning_var).pack(
            side="left", padx=(12, 0))
        row = ttk.Frame(options)
        row.pack(fill="x", pady=1)
        self.replay_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text=tr("Danach noch einmal morsen"), variable=self.replay_var).pack(side="left")

        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=10, pady=(8, 0))
        self.start_button = ttk.Button(controls, text=tr("Start"), style="Accent.TButton", command=self.toggle_running)
        self.start_button.pack(side="left")
        self.export_button = ttk.Button(controls, text=tr("Als MP3 speichern…"), command=self.export)
        self.export_button.pack(side="left", padx=8)
        self.progress_var = tk.StringVar(value="")
        theme.hint(controls, textvariable=self.progress_var).pack(side="right")

        self.status_var = tk.StringVar(value=tr("Bereit. Drücke Start."))
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel", wraplength=560,
                  justify="center").pack(pady=(14, 6))
        self.solution_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.solution_var, style="Feedback.TLabel", wraplength=560,
                  justify="center").pack(pady=(4, 2))
        self.meaning_text = tk.StringVar(value="")
        theme.hint(parent, textvariable=self.meaning_text, wrap=560).pack()

    # --- Einstellungen --------------------------------------------------
    def settings(self) -> dict:
        """Einstellungen zum Speichern: Inhalt, Bedeutung ansagen,
        nochmal spielen, als Ganzes ansagen, Anzahl, Pause, Gruppenlänge."""
        data = {
            "content": CONTENTS.get(self.content_var.get()),
            "meaning": self.meaning_var.get(),
            "replay": self.replay_var.get(),
            "whole": self.whole_var.get(),
        }
        for key, var in (("count", self.count_var), ("pause", self.pause_var), ("group_len", self.group_len_var)):
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
        for key, var in (("meaning", self.meaning_var), ("replay", self.replay_var), ("whole", self.whole_var)):
            if isinstance(data.get(key), bool):
                var.set(data[key])
        for key, var, (low, high), kind in (("count", self.count_var, COUNT_RANGE, int),
                                            ("group_len", self.group_len_var, GROUP_LEN_RANGE, int),
                                            ("pause", self.pause_var, PAUSE_RANGE, (int, float))):
            value = data.get(key)
            if isinstance(value, kind) and not isinstance(value, bool) and low <= value <= high:
                var.set(value)

    def _options(self):
        """Gültige Einstellungen oder None (Meldung steht dann in der Statuszeile)."""
        try:
            count = min(max(self.count_var.get(), COUNT_RANGE[0]), COUNT_RANGE[1])
            pause = min(max(float(self.pause_var.get()), PAUSE_RANGE[0]), PAUSE_RANGE[1])
            group_len = min(max(self.group_len_var.get(), GROUP_LEN_RANGE[0]), GROUP_LEN_RANGE[1])
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except (tk.TclError, ValueError):
            announcer.problem(self.status_var, tr("Ungültige Anzahl, Pause, Geschwindigkeit oder Tonhöhe!"))
            return None
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        source = ItemSource(CONTENTS.get(self.content_var.get(), "chars"), charset, group_len,
                            self.weighted_var.get())
        problem = source.problem()
        if problem:
            announcer.problem(self.status_var, problem)
            return None
        reason = speech.speaker.available()
        if reason:
            self.status_var.set(reason)
            return None
        return {"count": count, "pause": pause, "wpm": wpm, "freq": freq, "fw": self.farnsworth_wpm(),
                "source": source, "alphabet": ALPHABET,
                "meaning": self.meaning_var.get(), "replay": self.replay_var.get(),
                "whole": self.whole_var.get(), "kind": source.kind,
                "vary": self.vary_var is not None and self.vary_var.get()}

    # --- Ein Eintrag als Audio ------------------------------------------
    @staticmethod
    def think_seconds(text: str, pause: float) -> float:
        """Denkpause nach einem Eintrag: die eingestellte Pause plus 0,3 s je
        Zeichen."""
        return pause + 0.3 * len(text.replace(" ", ""))

    @staticmethod
    def announcement(text: str, meaning: str, opts) -> str:
        """Zeichen, Gruppen, Rufzeichen buchstabiert. Wörter und Wendungen
        wahlweise als Ganzes – als Wort erkannt, nicht Buchstabe für
        Buchstabe: bei Kürzeln die deutsche Bedeutung („TNX“ → „danke“), bei
        gewöhnlichen Wörtern das Wort selbst."""
        german = meaning.split("–")[-1].strip()
        if opts.get("whole") and opts.get("kind") in ("words", "phrases"):
            return german or speech.spoken_words(text, opts["alphabet"])
        said = speech.spoken(text, opts["alphabet"])
        if opts["meaning"] and german:
            said += ". " + german
        return said

    def item_parts(self, text: str, meaning: str, wpm: int, freq: int, opts):
        """(Morsezeichen, Denkpause, Ansage, Rest) als Samples."""
        code = build_text(text, wpm, freq, opts["fw"])
        voice = speech.speaker.synth(self.announcement(text, meaning, opts))
        rest = [silence(REPLAY_GAP_S), code] if opts["replay"] else []
        rest.append(silence(GAP_AFTER_S))
        return code, silence(self.think_seconds(text, opts["pause"])), voice, np.concatenate(rest)

    def _voice_for(self, opts):
        wpm, freq = opts["wpm"], opts["freq"]
        return vary_voice(wpm, freq) if opts["vary"] else (wpm, freq)

    # --- Live ------------------------------------------------------------
    def toggle_running(self):
        """Starten bzw. beenden (Knopf, F5)."""
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        """Prüft die Einstellungen (sonst Grund in der Statuszeile und als Ansage)
        und beginnt mit dem ersten Eintrag."""
        if self.running or self.exporting:
            return
        opts = self._options()
        if opts is None:
            announcer.say(self.status_var.get())  # warum es nicht losgeht
            return
        self.opts = opts
        self.source = opts["source"]
        self.session_id += 1
        self.running = True
        self.done, self.total = 0, opts["count"]
        self.start_button.config(text=tr("Stop"))
        self.content_buttons.state(["disabled"])
        self.export_button.config(state="disabled")
        self.solution_var.set("")
        self.meaning_text.set("")
        self.on_start_cb()
        self.status_var.set(tr("Stimme wird geladen…"))
        speech.speaker.preload()
        self._wait_for_voice(self.session_id)

    def _wait_for_voice(self, session_id):
        if not self.running or session_id != self.session_id:
            return
        if speech.speaker.voice is None and speech.speaker.error is None:
            self.root.after(100, self._wait_for_voice, session_id)
            return
        if speech.speaker.error:
            self.stop()
            self.status_var.set(speech.speaker.error)
            announcer.say(speech.speaker.error)
            return
        self._next_item(session_id)

    def _later(self, ms, callback, *args):
        session_id = self.session_id

        def run():
            if self.running and session_id == self.session_id:
                callback(*args)
        self.root.after(ms, run)

    def _next_item(self, _session_id=None):
        if self.done >= self.total:
            self.stop()
            self.status_var.set(tr("Fertig: {n} Einträge.").format(n=self.total))
            announcer.say(self.status_var.get())
            return
        text, meaning = self.source.next()
        wpm, freq = self._voice_for(self.opts)
        self.current = (text, meaning, wpm, freq)
        self.done += 1
        self._play_current()

    def _play_current(self):
        """Spielt den aktuellen Eintrag mit Denkpause und plant die Ansage der
        Lösung (und das nochmalige Zeichen) danach ein."""
        text, meaning, wpm, freq = self.current
        code, think, voice, rest = self.item_parts(text, meaning, wpm, freq, self.opts)
        self.progress_var.set(f"{self.done}/{self.total}")
        self.solution_var.set("")
        self.meaning_text.set("")
        self.status_var.set(tr("Hör zu …"))
        if not self._play(np.concatenate([code, think])):
            return
        latency = int(AUDIO_LATENCY * 1000)
        self._later(int(len(code) / SAMPLE_RATE * 1000) + latency,
                    lambda: self.status_var.set(tr("Sag es laut …")))
        self._later(int((len(code) + len(think)) / SAMPLE_RATE * 1000) + latency, self._answer, voice, rest)

    def _answer(self, voice, rest):
        text, meaning, _, _ = self.current
        self.status_var.set(tr("Lösung:"))
        self.solution_var.set(display_text(text))
        self.meaning_text.set(words.shown_meaning(text, meaning))
        samples = np.concatenate([voice, rest])
        if self._play(samples):
            self._later(int(len(samples) / SAMPLE_RATE * 1000) + int(AUDIO_LATENCY * 1000), self._next_item)

    def _play(self, samples) -> bool:
        try:
            audio.play(samples)
        except audio.AudioError as exc:
            self.stop()
            announcer.problem(self.status_var, str(exc))
            return False
        return True

    def repeat_item(self):
        """Leertaste: den aktuellen Eintrag von vorn (erst hören, dann Lösung)."""
        if self.running and self.current is not None:
            self.session_id += 1  # laufende Timer verwerfen
            audio.stop()
            self._play_current()

    def stop(self):
        """Bricht ab, stoppt den Ton und gibt die Reiter frei."""
        if not self.running:
            return
        self.running = False
        self.session_id += 1
        audio.stop()
        self.start_button.config(text=tr("Start"))
        self.content_buttons.state(["!disabled"])
        self.export_button.config(state="normal")
        self.progress_var.set("")
        self.status_var.set(tr("Gestoppt."))
        announcer.say(self.status_var.get())  # am Ende verdrängt von „Fertig …“
        self.on_stop_cb()

    # --- MP3 -------------------------------------------------------------
    def export(self):
        """Erzeugt dieselbe Folge als MP3-Datei (Ort per Dialog) im Hintergrund,
        mit Fortschritt in der Statuszeile."""
        if self.running or self.exporting:
            return
        reason = mp3.available()
        if reason:
            announcer.problem(self.status_var, reason)
            return
        opts = self._options()
        if opts is None:
            return
        content = CONTENTS.get(self.content_var.get(), "chars")
        name = f"morsetrainer-{content}-{opts['wpm']}wpm-{datetime.now():%Y%m%d-%H%M}.mp3"
        path = filedialog.asksaveasfilename(
            parent=self.root, title=tr("Übung als MP3 speichern"), defaultextension=".mp3", initialfile=name,
            initialdir=str(Path.home()), filetypes=[("MP3", "*.mp3")],
        )
        if not path:
            return
        self.exporting = True
        self.cancel_export = False
        self.start_button.config(state="disabled")
        self.content_buttons.state(["disabled"])
        self.export_button.config(text=tr("Abbrechen"), command=self._cancel_export)
        self.export_result = None
        self.export_done = 0
        self.status_var.set(tr("MP3 wird erstellt …"))
        announcer.say(self.status_var.get())
        self.export_spoken = None
        threading.Thread(target=self._export_worker, args=(path, opts), daemon=True).start()
        self._watch_export(opts["count"])

    def _cancel_export(self):
        self.cancel_export = True

    def _export_worker(self, path, opts):
        """Im Hintergrund: Einträge erzeugen und kodieren. Das Ergebnis holt
        _watch_export im Tk-Thread ab."""
        try:
            speech.speaker.load()
            if speech.speaker.error:
                raise mp3.Mp3Error(speech.speaker.error)
            with mp3.Mp3Writer(path) as writer:
                writer.write(build_text("VVV = ", opts["wpm"], opts["freq"], opts["fw"]))
                writer.write(silence(1.0))
                for i in range(opts["count"]):
                    if self.cancel_export:
                        break
                    text, meaning = opts["source"].next()
                    wpm, freq = self._voice_for(opts)
                    for part in self.item_parts(text, meaning, wpm, freq, opts):
                        writer.write(part)
                    self.export_done = i + 1
                writer.write(build_text("+", opts["wpm"], opts["freq"]))
            if self.cancel_export:
                Path(path).unlink(missing_ok=True)
                self.export_result = tr("MP3 abgebrochen.")
            else:
                self.export_result = tr("Gespeichert: {path} ({minutes:.0f} Min.)").format(path=path, minutes=writer.seconds / 60)
                # Ansage ohne Pfad (der hilft beim Zuhören nicht).
                self.export_spoken = tr("MP3 gespeichert, {minutes:.0f} Minuten.").format(minutes=writer.seconds / 60)
        except (mp3.Mp3Error, OSError) as exc:
            self.export_result = str(exc)
        except Exception as exc:
            # Sonst bliebe „MP3 wird erstellt …“ stehen und Start gesperrt.
            self.export_result = tr("MP3 nicht erstellt: {error}").format(error=str(exc) or type(exc).__name__)
            raise  # ins Fehlerprotokoll (threading.excepthook)

    def _watch_export(self, total):
        if self.export_result is None:
            self.progress_var.set(f"{self.export_done}/{total}")
            self.root.after(200, self._watch_export, total)
            return
        self.exporting = False
        self.start_button.config(state="normal")
        self.content_buttons.state(["!disabled"])
        self.export_button.config(text=tr("Als MP3 speichern…"), command=self.export)
        self.progress_var.set("")
        self.status_var.set(self.export_result)
        announcer.say(self.export_spoken or self.export_result)

    # --- Tasten ----------------------------------------------------------
    def on_function_key(self, key: str):
        """F5 startet bzw. beendet."""
        if key == "F5":
            self.toggle_running()

    def on_key(self, event):
        """Esc beendet, Leertaste wiederholt den aktuellen Eintrag."""
        if event.keysym == "Escape":
            self.stop()
        elif event.keysym == "space":
            self.repeat_item()

    def on_close(self):
        """Programmende: MP3-Erzeugung abbrechen und stoppen."""
        self.cancel_export = True
        self.stop()
