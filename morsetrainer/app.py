"""Morsetrainer von DL4YM.

Trainingsmodi über Tabs (Einzelzeichen, Gruppen, Wörter, Rufzeichen,
Kontinuierlich, QSO-Hörtraining, aktiver Contest-Betrieb, Netzwerk für
Gruppen) plus Statistik, mit
gemeinsamen Einstellungen für Zeichensatz (frei oder als Koch-Lektion),
Geschwindigkeit und Tonhöhe."""
import re
import sys
import threading
import time
from datetime import date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from morsetrainer import DATA_DIR, i18n
from morsetrainer.core import audio, awards, errorlog, koch, practice, review, stats, storage, tempo
from morsetrainer.core.morse import build_text, display_text, key_hint
from morsetrainer.daily_runner import DailyRunner
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.callsign_mode import CallsignModeFrame
from morsetrainer.modes.continuous_mode import ContinuousModeFrame
from morsetrainer.modes.group_mode import GroupModeFrame
from morsetrainer.modes.listen_mode import ListenModeFrame
from morsetrainer.modes.network_mode import NetworkModeFrame
from morsetrainer.modes.qso_mode import QsoModeFrame
from morsetrainer.modes.run_mode import RunModeFrame
from morsetrainer.modes.single_mode import SingleModeFrame
from morsetrainer.modes.word_mode import WordModeFrame
from morsetrainer.net import update
from morsetrainer.widgets.awards_panel import AwardsPanel, DiplomaWindow
from morsetrainer.widgets.daily_panel import DailyBar
from morsetrainer.widgets.help_window import HelpWindow
from morsetrainer.widgets.lifeline_widget import LifelinePanel
from morsetrainer.widgets.progress_widget import ProgressPanel
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.updater import DECLINED, Updater
from morsetrainer.widgets import theme
from morsetrainer.widgets.ui_widgets import ScrollableFrame

__author__ = "DL4YM"
__version__ = "2.22"

# Wer neu anfängt, beginnt mit Koch-Lektion 1.
DEFAULT_CHARSET = koch.lesson_charset(1)
DEFAULT_GEOMETRY = "720x900"
# Schmaler passen die Beschriftungen aller Reiter nicht nebeneinander; eine
# gespeicherte kleinere Breite (von vor dem Reiter Netzwerk) wird angehoben.
MIN_WIDTH = 720
WINDOW_STATE_FILE = DATA_DIR / "window_state.json"
# Bis 2.21 Vorgabe im Contest-Reiter; wer es dort stehen ließ, hat es nicht selbst eingetragen.
LEGACY_DEFAULT_CALL = "DL4YM"
FUNCTION_KEYS = {f"F{i}" for i in range(1, 13)}
# Startet die Tagesübung; von keinem Reiter belegt.
DAILY_KEY = "F12"
# So viele Verwechslungspaare (die häufigsten) übt "Diese Verwechslungen üben".
CONFUSION_PAIRS = 4
# Übungszeit in der Fußzeile während eines Durchgangs so oft auffrischen.
PRACTICE_TICK_MS = 15000
# Programmicon (aus packaging/morsetrainer.svg, wie im AppImage); in
# AppImage und exe per --add-data mit eingepackt.
ICON_DIR = Path(__file__).resolve().parent / "assets"
# Höchstens 128: ein 256er-Icon kommt unter X leer an (Tk 8.6).
ICON_SIZES = (128, 64, 32)
# Updateprüfung beim Start: so lange nach dem Öffnen, Abfrage alle
# UPDATE_POLL_MS (die Anfrage selbst gibt ohne Internet nach 5 s auf).
UPDATE_CHECK_DELAY_MS = 1500
# So oft wird nachgesehen, ob ein Hintergrund-Thread einen Fehler protokolliert hat.
ERROR_POLL_MS = 1000
UPDATE_POLL_MS = 500


class MorseTrainerApp:
    def __init__(self, root):
        self.root = root
        self.running_mode = False
        # „Fällige gezielt üben“: (Zeichensatz davor, erweiterter Zeichensatz);
        # nach dem Durchgang kommt der alte zurück, siehe _handle_mode_stop.
        self.drill_restore = None
        self.restart_args = None  # nach einem Update: neu starten mit diesen Argumenten
        self.groups_offered = set()  # Lektionen, für die der Gruppen-Hinweis schon kam
        self.error_shown = False  # Hinweis auf fehler.log kommt einmal je Sitzung
        root.title(tr("Morsetrainer von {author}").format(author=__author__))
        self._set_icon()
        self.saved_state = self._load_state()
        self.updater = Updater(root, __version__, self.restart_for_update)
        declined = self.saved_state.get("update_declined")
        self.update_declined = declined if isinstance(declined, str) else None  # „Nein“ zu dieser Version
        self.update_checked = False  # Updateprüfung beim Start abgeschlossen
        root.geometry(self._initial_geometry())
        root.resizable(True, True)

        theme.apply(root)
        self._build_settings()
        self._restore_shared_settings()
        self._update_more()
        self._build_footer()
        # Vor dem Notizbuch gepackt: steht über den Reitern.
        self.daily_bar = DailyBar(self.root, on_start=lambda: self.daily.start(),
                                  on_continue=lambda: self.daily.continue_now())
        self.daily_bar.pack()
        self._build_notebook()
        self._follow_station()
        self._build_all_time_tab()
        self._refresh_all_time()
        self.daily = DailyRunner(self, self.daily_bar)
        self.pending_seals = []  # neue Siegel, die noch kein Diplom-Fenster gezeigt hat
        self.diploma_window = None
        self.root.after(500, self._check_awards_at_start)
        # Ausgabegerät wach halten, damit kein Zeichenanfang verloren geht.
        audio.keep_awake()

        root.bind("<Key>", self._dispatch_key)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _set_icon(self):
        """Fenstericon, auch für das Hilfefenster (default=True). Fehlt die
        Datei, bleibt das Standardicon."""
        try:
            self.icons = [tk.PhotoImage(master=self.root, file=ICON_DIR / f"icon-{n}.png") for n in ICON_SIZES]
            self.root.iconphoto(True, *self.icons)
        except tk.TclError:
            self.icons = []

    def _load_state(self) -> dict:
        """window_state.json: Fenstergröße, gemeinsame Einstellungen und die
        Einstellungen der Reiter, die welche speichern (siehe _mode_settings)."""
        return storage.load_json(WINDOW_STATE_FILE, {})

    def _initial_geometry(self) -> str:
        geometry = self.saved_state.get("geometry")
        if isinstance(geometry, str) and self._geometry_fits_screen(geometry):
            return re.sub(r"^\d+", lambda m: str(max(int(m.group()), MIN_WIDTH)), geometry)
        return DEFAULT_GEOMETRY

    def _geometry_fits_screen(self, geometry: str) -> bool:
        match = re.match(r"(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?", geometry)
        if not match:
            return False
        width, height, x, y = match.groups()
        width, height = int(width), int(height)
        if x is None or y is None:
            return True
        x, y = int(x), int(y)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        return -width < x < screen_w and -height < y < screen_h

    def _saved_mode_settings(self, title: str) -> dict:
        modes = self.saved_state.get("modes")
        settings = modes.get(title) if isinstance(modes, dict) else None
        return settings if isinstance(settings, dict) else {}

    def _mode_settings(self) -> dict:
        """Einstellungen aller Modi mit settings()/restore_settings()."""
        return {
            title: mode.settings()
            for title, mode in zip(self.mode_titles, self.modes)
            if hasattr(mode, "settings")
        }

    def _save_state(self) -> None:
        state = {
            "geometry": self.root.geometry(),
            "shared": self._shared_settings(),
            "modes": self._mode_settings(),
            i18n.SETTING_KEY: self.language_var.get(),
            "update_declined": self.update_declined,
        }
        try:
            storage.write_json_atomic(WINDOW_STATE_FILE, state, indent=2)
        except OSError:
            pass

    def _build_settings(self):
        """Kopfleiste: Koch-Lektion, Tempo, Tonhöhe und Zeichensatz immer
        sichtbar; seltener gebrauchte Optionen klappen darunter auf."""
        header = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)

        top = ttk.Frame(header)
        top.grid(row=0, column=0, columnspan=2, sticky="we")
        self.charset_var = tk.StringVar(value=DEFAULT_CHARSET)
        self._build_koch_row(top)
        self.freq_var = tk.IntVar(value=600)
        ttk.Label(top, text="Hz").pack(side="right", padx=(4, 0))
        ttk.Spinbox(top, from_=300, to=1000, increment=50, textvariable=self.freq_var, width=5).pack(side="right")
        # Standard für Einsteiger: Koch-Tempo, Zeichen schnell, Pausen lang.
        self.wpm_var = tk.IntVar(value=koch.RECOMMENDED_WPM)
        ttk.Label(top, text="WPM").pack(side="right", padx=(4, 16))
        ttk.Spinbox(top, from_=5, to=40, textvariable=self.wpm_var, width=4).pack(side="right")

        ttk.Label(header, text=tr("Zeichen")).grid(row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 8))
        ttk.Entry(header, textvariable=self.charset_var, font=theme.MONO).grid(
            row=1, column=1, sticky="we", pady=(6, 0)
        )

        toggle_row = ttk.Frame(header)
        toggle_row.grid(row=2, column=0, columnspan=2, sticky="we", pady=(4, 0))
        self.more_var = tk.BooleanVar(value=False)
        self.more_button = ttk.Button(toggle_row, style="Flat.TButton", command=self._toggle_more)
        self.more_button.pack(side="left")
        self.extras_var = tk.StringVar(value="")
        theme.hint(toggle_row, textvariable=self.extras_var).pack(side="left", padx=(8, 0))
        # Umrechnung für alle, die in ZpM/BpM denken (DL-Kurse, RufZ, HST);
        # hier statt neben dem WPM-Feld, weil die obere Zeile voll ist.
        self.cpm_var = tk.StringVar(value="")
        theme.hint(toggle_row, textvariable=self.cpm_var).pack(side="right")

        # Hinweis bei zu langsamem Zeichentempo (koch.SLOW_CHAR_WPM), sonst
        # ausgeblendet; unter den aufklappbaren Optionen (Zeile 3).
        self.slow_hint = ttk.Frame(header)
        self.slow_hint_var = tk.StringVar(value="")
        theme.hint(self.slow_hint, textvariable=self.slow_hint_var, wrap=520).pack(side="left")
        ttk.Button(self.slow_hint, text=tr("Koch-Tempo {wpm}/{effective}").format(
            wpm=koch.RECOMMENDED_WPM, effective=koch.RECOMMENDED_EFFECTIVE_WPM),
            command=self._set_koch_tempo).pack(side="right")

        self.more_frame = ttk.Frame(header)
        farnsworth = ttk.Frame(self.more_frame)
        farnsworth.pack(fill="x", pady=2)
        self.farnsworth_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(farnsworth, text=tr("Farnsworth, effektiv"), variable=self.farnsworth_enabled_var).pack(
            side="left"
        )
        self.farnsworth_wpm_var = tk.IntVar(value=koch.RECOMMENDED_EFFECTIVE_WPM)
        ttk.Spinbox(farnsworth, from_=3, to=39, textvariable=self.farnsworth_wpm_var, width=4).pack(
            side="left", padx=4
        )
        self.farnsworth_cpm_var = tk.StringVar(value="")
        theme.hint(farnsworth, textvariable=self.farnsworth_cpm_var).pack(side="left")
        ttk.Button(
            farnsworth, text=tr("Koch-Tempo {wpm}/{effective}").format(
                wpm=koch.RECOMMENDED_WPM, effective=koch.RECOMMENDED_EFFECTIVE_WPM),
            command=self._set_koch_tempo,
        ).pack(side="right")

        self.weighted_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.more_frame, text=tr("Schwache Zeichen bevorzugen (gilt ab nächstem Start)"),
            variable=self.weighted_var,
        ).pack(anchor="w", pady=2)

        self.vary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.more_frame, text=tr("Tonhöhe und Tempo leicht variieren (gegen Gewöhnung an einen Klang)"),
            variable=self.vary_var,
        ).pack(anchor="w", pady=2)

        # Eigenes Rufzeichen und Name: für die Diplome und als Vorgabe in
        # den Reitern Contest und Netzwerk (siehe _follow_station).
        station = ttk.Frame(self.more_frame)
        station.pack(fill="x", pady=2)
        self.station_call_var = tk.StringVar(value="")
        self.station_name_var = tk.StringVar(value="")
        ttk.Label(station, text=tr("Rufzeichen", context="eigenes")).pack(side="left")
        ttk.Entry(station, textvariable=self.station_call_var, width=12).pack(side="left", padx=(6, 12))
        ttk.Label(station, text=tr("Name")).pack(side="left")
        ttk.Entry(station, textvariable=self.station_name_var, width=14).pack(side="left", padx=(6, 8))
        theme.hint(station, text=tr("falls vorhanden; für Diplome, Contest und Netzwerk")).pack(side="left")

        # Zweisprachig beschriftet, damit man auch nach versehentlichem
        # Umschalten zurückfindet; wirkt ab dem nächsten Start (i18n.py).
        language = ttk.Frame(self.more_frame)
        language.pack(fill="x", pady=2)
        ttk.Label(language, text="Sprache / Language").pack(side="left")
        self.language_var = tk.StringVar(value=i18n.LANG)
        self.language_box = ttk.Combobox(language, values=list(i18n.LANGUAGES.values()), state="readonly",
                                         width=10)
        self.language_box.set(i18n.LANGUAGES[i18n.LANG])
        self.language_box.pack(side="left", padx=(6, 8))
        self.language_box.bind("<<ComboboxSelected>>", lambda e: self._choose_language())
        self.language_hint_var = tk.StringVar(value="")
        theme.hint(language, textvariable=self.language_hint_var).pack(side="left")

        for var in (self.more_var, self.farnsworth_enabled_var, self.farnsworth_wpm_var, self.wpm_var,
                    self.weighted_var, self.vary_var):
            var.trace_add("write", lambda *_: self._update_more())
        for var in (self.wpm_var, self.farnsworth_wpm_var):
            var.trace_add("write", lambda *_: self._update_cpm())
        self._update_cpm()
        ttk.Separator(self.root).pack(fill="x", padx=10, pady=(4, 0))

        # Einstellbar im Reiter Statistik, angezeigt in der Fußzeile; so
        # lang wie die Tagesübung (core/daily.py).
        self.daily_goal_var = tk.IntVar(value=10)

    def _choose_language(self):
        """Gewählte Sprache merken (gespeichert in _save_state); sie gilt ab
        dem nächsten Start, siehe i18n.py."""
        chosen = next(k for k, v in i18n.LANGUAGES.items() if v == self.language_box.get())
        self.language_var.set(chosen)
        self.language_hint_var.set("" if chosen == i18n.LANG else tr("wirkt nach Neustart des Programms"))

    def _update_cpm(self):
        """ZpM-Hinweise zu den WPM-Feldern (PARIS-Umrechnung, core/tempo.py);
        leer bzw. ohne ZpM, solange ein Feld keine Zahl enthält."""
        try:
            wpm = self.wpm_var.get()
            self.cpm_var.set(tr("{wpm} WPM ≈ {cpm} ZpM").format(wpm=wpm, cpm=tempo.cpm(wpm)))
        except tk.TclError:
            wpm = None
            self.cpm_var.set("")
        if wpm is not None and wpm < koch.SLOW_CHAR_WPM:
            self.slow_hint_var.set(tr(
                "Zeichentempo {wpm} WPM: So langsame Zeichen lassen sich mitzählen. Besser schnelle Zeichen "
                "mit längeren Pausen (Farnsworth).").format(wpm=wpm))
            self.slow_hint.grid(row=4, column=0, columnspan=2, sticky="we", pady=(4, 0))
        else:
            self.slow_hint.grid_remove()
        try:
            fw = tr("WPM ≈ {cpm} ZpM").format(cpm=tempo.cpm(self.farnsworth_wpm_var.get()))
        except tk.TclError:
            fw = "WPM"
        self.farnsworth_cpm_var.set(tr("{wpm} (alle außer Einzelzeichen)").format(wpm=fw))

    def _toggle_more(self):
        self.more_var.set(not self.more_var.get())

    def _update_more(self):
        """Weitere Optionen ein-/ausklappen; zugeklappt steht daneben, was
        davon gerade aktiv ist."""
        expanded = self.more_var.get()
        self.more_button.config(text=tr("▾ Weitere Optionen") if expanded else tr("▸ Weitere Optionen"))
        if expanded:
            self.more_frame.grid(row=3, column=0, columnspan=2, sticky="we", pady=(2, 0))
            self.extras_var.set("")
            return
        self.more_frame.grid_remove()
        active = []
        effective = self.farnsworth_wpm()
        if effective is not None:
            active.append(tr("Farnsworth {wpm}").format(wpm=effective))
        if self.weighted_var.get():
            active.append(tr("schwache bevorzugt"))
        if self.vary_var.get():
            active.append(tr("variiert"))
        self.extras_var.set(" · ".join(active))

    def _build_koch_row(self, parent):
        """Koch-Lektion: setzt den Zeichensatz auf die ersten Zeichen der
        Koch-Reihenfolge. Das Feld "Zeichen" bleibt frei editierbar; passt
        es zu keiner Lektion, steht dort "eigene Zeichen"."""
        ttk.Label(parent, text=tr("Koch-Lektion")).pack(side="left", padx=(0, 6))
        self.lesson_var = tk.IntVar(value=1)
        spinbox = ttk.Spinbox(
            parent, from_=1, to=koch.MAX_LESSON, textvariable=self.lesson_var, width=3, command=self._apply_lesson
        )
        spinbox.pack(side="left")
        spinbox.bind("<Return>", lambda e: self._apply_lesson())
        self.lesson_info_var = tk.StringVar(value="")
        theme.hint(parent, textvariable=self.lesson_info_var).pack(side="left", padx=(8, 4))
        # Spielt das neue Zeichen vor; bei eigenem Zeichensatz (z. B. nach
        # "Verwechslungen üben") führt er zurück zur Lektion.
        self.new_char_button = ttk.Button(parent, text=tr("▶ anhören"), command=self._lesson_button)
        self.new_char_button.pack(side="left")
        self.charset_var.trace_add("write", lambda *_: self._sync_lesson())
        self._sync_lesson()

    def _apply_lesson(self):
        try:
            lesson = self.lesson_var.get()
        except tk.TclError:
            return
        self.charset_var.set(koch.lesson_charset(lesson))

    def _sync_lesson(self):
        lesson = koch.lesson_of(self.charset_var.get().strip().upper())
        if lesson is None:
            self.lesson_info_var.set(tr("(eigene Zeichen)"))
            try:
                back = self.lesson_var.get()
            except tk.TclError:
                back = 1
            self.new_char_button.config(text=tr("↩ Lektion {lesson}").format(lesson=back))
        else:
            self.lesson_var.set(lesson)
            new_char = koch.newest_char(lesson)
            if new_char:
                self.lesson_info_var.set(tr("neu: {char}").format(char=key_hint(new_char)))
            else:
                self.lesson_info_var.set(tr("alle Zeichen, keins bevorzugt"))
            self.new_char_button.config(text=tr("▶ anhören"))
            if not new_char:
                self.new_char_button.config(state="disabled")
                return
        self.new_char_button.config(state="disabled" if self.running_mode else "normal")

    def _lesson_button(self):
        if koch.lesson_of(self.charset_var.get().strip().upper()) is None:
            self._apply_lesson()
        else:
            self._play_new_char()

    def _play_new_char(self):
        """Das neueste Zeichen der Lektion dreimal vorspielen."""
        lesson = koch.lesson_of(self.charset_var.get().strip().upper())
        if lesson is None:
            return
        ch = koch.newest_char(lesson)
        if not ch:
            return
        try:
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except tk.TclError:
            wpm, freq = koch.RECOMMENDED_WPM, 600
        try:
            audio.play(build_text(f"{ch} {ch} {ch}", wpm, freq, self.farnsworth_wpm()))
        except audio.AudioError as exc:
            messagebox.showwarning(tr("Tonausgabe"), str(exc))

    def _set_koch_tempo(self):
        self.wpm_var.set(koch.RECOMMENDED_WPM)
        self.farnsworth_wpm_var.set(koch.RECOMMENDED_EFFECTIVE_WPM)
        self.farnsworth_enabled_var.set(True)

    def _offer_next_lesson(self, mode):
        """Nach einem Durchgang: bei mindestens 90 % in einer Koch-Lektion
        das nächste Zeichen anbieten."""
        result = getattr(mode, "koch_result", None)
        if result is None:
            return
        mode.koch_result = None
        charset, correct, total = result
        if not koch.can_advance(charset, correct, total):
            return
        lesson = koch.lesson_of(charset)
        new_char = koch.newest_char(lesson + 1)
        text = tr("Lektion {lesson} geschafft: {correct} von {total} Zeichen richtig ({share:.0%}).").format(
            lesson=lesson, correct=correct, total=total, share=correct / total) + "\n\n"
        if new_char:
            text += tr("Mit Lektion {next} weitermachen? Neu dazu kommt „{char}“.").format(
                next=lesson + 1, char=key_hint(new_char))
        else:
            text += tr("Du kennst jetzt alle Zeichen. Mit der Abschlusslektion {next} weitermachen? Dort ist "
                       "kein Zeichen mehr neu, alle kommen gleichmäßig (schwache weiter öfter). Die "
                       "Betriebszeichen AR, KN, SK und BK kannst du danach in den Lektionen {first}–{last} "
                       "dazunehmen.").format(next=lesson + 1, first=koch.FINAL_LESSON + 1, last=koch.MAX_LESSON)
        try:
            wpm = self.wpm_var.get()
        except tk.TclError:
            wpm = koch.RECOMMENDED_WPM
        if wpm < koch.SLOW_CHAR_WPM:
            # Geschafft mit gedehnten Zeichen heißt womöglich: mitgezählt.
            text += "\n\n" + tr(
                "Hinweis: Die Zeichen kamen mit {wpm} WPM, so langsam lassen sie sich mitzählen. Besser mit "
                "Koch-Tempo {rec}/{eff} weiterüben, damit sich das Klangbild einprägt. Für das Koch-Diplom "
                "zählen Läufe erst ab {min} WPM Zeichentempo.").format(
                wpm=wpm, rec=koch.RECOMMENDED_WPM, eff=koch.RECOMMENDED_EFFECTIVE_WPM, min=koch.SLOW_CHAR_WPM)
        if messagebox.askyesno(tr("Nächste Koch-Lektion"), text):
            self.charset_var.set(koch.lesson_charset(lesson + 1))
            self._play_new_char()

    def _offer_groups(self, mode):
        """Nach einem Einzelzeichen-Durchgang mit Zeitlimit und mindestens
        90 %: vorschlagen, im Reiter Gruppen weiterzuüben. Einzelzeichen
        allein reichen nicht, im Funkbetrieb kommen die Zeichen ohne Pause
        hintereinander. Je Lektion nur einmal pro Programmstart."""
        result = getattr(mode, "groups_result", None)
        if result is None:
            return
        mode.groups_result = None
        charset, correct, total = result
        lesson = koch.lesson_of(charset)
        if lesson is None or lesson in self.groups_offered or not koch.passed(correct, total):
            return
        self.groups_offered.add(lesson)
        if messagebox.askyesno(
            tr("Weiter mit Gruppen"),
            tr("Die Zeichen von Lektion {lesson} sitzen: {correct} von {total} richtig ({share:.0%}), "
               "mit Zeitlimit.\n\n"
               "Im Reiter Gruppen kommen sie ohne Pause hintereinander, wie im Funkbetrieb. "
               "Dort wird dir auch die nächste Lektion angeboten.\n\n"
               "Zum Reiter Gruppen wechseln?").format(lesson=lesson, correct=correct, total=total,
                                                     share=correct / total),
        ):
            self.notebook.select(self.tab_ids[self.mode_titles.index("Gruppen")])

    def _build_footer(self):
        # Vor dem Notebook gepackt, damit es bei kleinem Fenster nicht verdrängt wird.
        footer = ttk.Frame(self.root, padding=(10, 4))
        footer.pack(side="bottom", fill="x")
        self.practice_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.practice_var).pack(side="left")
        self.update_var = tk.StringVar(value="")  # Updateprüfung beim Start
        ttk.Label(footer, textvariable=self.update_var, style="Footer.TLabel", wraplength=420).pack(
            side="left", padx=(12, 0))
        ttk.Button(footer, text=tr("Hilfe"), style="Flat.TButton",
                   command=lambda: HelpWindow.show(self.root)).pack(side="right", padx=(8, 0))
        ttk.Label(
            footer, text=tr("Morsetrainer {version} · entwickelt von {author} · 73!").format(
                version=__version__, author=__author__), style="Footer.TLabel",
        ).pack(side="right")
        ttk.Separator(self.root).pack(side="bottom", fill="x", padx=10)
        self.practice_started = None  # time.time() beim Start eines Durchgangs
        self.practice_tick_id = None
        self.daily_goal_var.trace_add("write", lambda *_: self._update_practice())
        self._update_practice()

    def daily_goal_minutes(self) -> int:
        try:
            return max(self.daily_goal_var.get(), 0)
        except tk.TclError:
            return 0

    def _update_practice(self):
        """Fußzeile: heutige Übungszeit und Tagesziel; dazu der
        Wochenstreifen (frei geübte Tage). Ein laufender Durchgang zählt
        schon mit."""
        data = practice.load()
        today = date.today()
        if self.practice_started is not None:
            data[today.isoformat()] = practice.seconds_on(data, today) + time.time() - self.practice_started
        minutes = int(practice.seconds_on(data, today) // 60)
        goal = self.daily_goal_minutes()
        if goal:
            text = tr("Heute {minutes} von {goal} Min").format(minutes=minutes, goal=goal)
            if minutes >= goal:
                text += " ✓"
        else:
            text = tr("Heute {minutes} Min").format(minutes=minutes)
        self.practice_var.set(text)
        if hasattr(self, "daily"):  # beim Aufbau der Fußzeile gibt es die Leiste noch nicht
            self.daily.refresh_week(data)

    def _practice_tick(self):
        self._update_practice()
        self.practice_tick_id = self.root.after(PRACTICE_TICK_MS, self._practice_tick)

    def _record_practice(self):
        if self.practice_tick_id is not None:
            self.root.after_cancel(self.practice_tick_id)
            self.practice_tick_id = None
        if self.practice_started is not None:
            practice.add(time.time() - self.practice_started)
            self.practice_started = None

    def _shared_vars(self) -> dict:
        """Gemeinsame Einstellungen: Schlüssel -> (Variable, erlaubter Bereich
        für Zahlen oder None)."""
        return {
            "charset": (self.charset_var, None),
            "wpm": (self.wpm_var, (5, 40)),
            "freq": (self.freq_var, (300, 1000)),
            "farnsworth_enabled": (self.farnsworth_enabled_var, None),
            "farnsworth_wpm": (self.farnsworth_wpm_var, (3, 39)),
            "weighted": (self.weighted_var, None),
            "vary": (self.vary_var, None),
            "daily_goal": (self.daily_goal_var, (0, 240)),
            "more_options": (self.more_var, None),
            "station_call": (self.station_call_var, None),
            "station_name": (self.station_name_var, None),
        }

    def _shared_settings(self) -> dict:
        saved = self.saved_state.get("shared")
        settings = dict(saved) if isinstance(saved, dict) else {}
        for key, (var, _) in self._shared_vars().items():
            try:
                settings[key] = var.get()
            except tk.TclError:
                pass  # Feld gerade leer/ungültig: zuletzt gespeicherten Wert behalten
        return settings

    def _restore_shared_settings(self) -> None:
        """Unbekannte, falsch typisierte oder außerhalb des Bereichs liegende
        Werte werden ignoriert, dann bleibt der Standardwert."""
        saved = self.saved_state.get("shared")
        if not isinstance(saved, dict):
            return
        for key, (var, limits) in self._shared_vars().items():
            value = saved.get(key)
            if isinstance(var, tk.BooleanVar):
                if isinstance(value, bool):
                    var.set(value)
            elif isinstance(var, tk.IntVar):
                if isinstance(value, int) and not isinstance(value, bool) and limits[0] <= value <= limits[1]:
                    var.set(value)
            elif isinstance(value, str) and value.strip():
                var.set(value)

    def farnsworth_wpm(self):
        """Effektive Farnsworth-Geschwindigkeit, oder None wenn aus bzw.
        nicht langsamer als die Zeichengeschwindigkeit (dann normales Timing)."""
        if not self.farnsworth_enabled_var.get():
            return None
        try:
            effective, wpm = self.farnsworth_wpm_var.get(), self.wpm_var.get()
        except tk.TclError:
            return None
        return effective if 0 < effective < wpm else None

    def adjust_tempo(self, delta: int):
        """Gemeinsames Tempo um `delta` WPM effektiv ändern (core/tempo.py);
        gibt (vorher, nachher) als Text zurück oder None bei ungültigen Feldern."""
        try:
            wpm = self.wpm_var.get()
        except tk.TclError:
            return None
        fw = self.farnsworth_wpm()
        limits = self._shared_vars()["wpm"][1]
        new_wpm, new_fw = tempo.step(wpm, fw, delta, limits)
        self.wpm_var.set(new_wpm)
        if new_fw is None:
            self.farnsworth_enabled_var.set(False)
        else:
            self.farnsworth_wpm_var.set(new_fw)
            self.farnsworth_enabled_var.set(True)
        return tempo.label(wpm, fw), tempo.label(new_wpm, new_fw)

    def _build_all_time_tab(self):
        """Eigener Reiter hinter den Trainingsmodi; ist kein Modus, Tasten
        werden dort nicht ausgewertet (siehe _active_mode)."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("Statistik"))
        frame = ScrollableFrame(tab).inner
        self.all_time_panel = StatsPanel(
            frame, title=tr("Gesamtstatistik (alle Durchgänge)"), tree_height=12, show_save_label=False
        )

        goal = theme.card(frame, tr("Tagesziel"))
        row = ttk.Frame(goal)
        row.pack(fill="x")
        ttk.Spinbox(row, from_=0, to=240, increment=5, textvariable=self.daily_goal_var, width=5).pack(side="left")
        ttk.Label(row, text=tr("Min. pro Tag")).pack(side="left", padx=(4, 0))
        theme.hint(goal, text=tr("0 = ohne Ziel. Lieber täglich kurz als selten lang.")).pack(anchor="w", pady=(4, 0))
        self.awards_panel = AwardsPanel(frame, on_show=lambda seal: self._show_diplomas([seal], tr("Diplom")))
        self.lifeline_panel = LifelinePanel(frame)

        review_box = theme.card(frame, tr("Wiederholung über Tage (Lernkartei)"))
        self.review_var = tk.StringVar(value="")
        ttk.Label(review_box, textvariable=self.review_var, justify="left", wraplength=520).pack(anchor="w", pady=4)
        theme.hint(
            review_box, wrap=520,
            text=tr("Sicher und flüssig erkannte Zeichen kommen nach 1, 2, 4, 8, 16 und 32 Tagen wieder, "
                    "unsichere schon am nächsten Tag. Mit „schwache bevorzugt“ kommen fällige Zeichen öfter "
                    "dran. Hochgestuft wird nur aus Zufallszeichen (Einzelzeichen, Gruppen, Kontinuierlich), "
                    "entschieden einmal am Tag ab 5 Versuchen."),
        ).pack(anchor="w", pady=(0, 6))
        self.review_button = ttk.Button(review_box, text=tr("Fällige gezielt üben"), command=self._drill_due)
        self.review_button.pack(anchor="w")

        confusion_box = theme.card(frame, tr("Häufigste Verwechslungen (letzte {days} Tage)").format(days=stats.RECENT_DAYS))
        self.confusion_var = tk.StringVar(value="")
        ttk.Label(confusion_box, textvariable=self.confusion_var, font=theme.MONO, justify="left").pack(
            anchor="w", pady=4
        )
        theme.hint(
            confusion_box, wrap=520,
            text=tr("Gesendet → getippt. Paare, die in beide Richtungen auftauchen (↔), sind "
                    "typische Klangverwandte – am besten gezielt zusammen üben."),
        ).pack(anchor="w", pady=(0, 6))
        self.confusion_button = ttk.Button(
            confusion_box, text=tr("Die {n} häufigsten gezielt üben").format(n=CONFUSION_PAIRS), command=self._drill_confusions
        )
        self.confusion_button.pack(anchor="w")
        self.progress_panel = ProgressPanel(frame)

        ttk.Button(frame, text=tr("Gesamtstatistik zurücksetzen"), command=self._reset_all_time).pack(
            anchor="e", padx=10, pady=(4, 10)
        )

    # --- Rufzeichen und Name ---------------------------------------------------------
    def _station_name(self) -> str:
        """Vorgabe für den Netzwerk-Reiter: der Name, sonst das Rufzeichen."""
        return self.station_name_var.get().strip() or self.station_call()

    def station_call(self) -> str:
        return self.station_call_var.get().strip().upper()

    def _follow_station(self):
        """Rufzeichen im Contest und Name im Netzwerk sind eigene Felder (ein
        Contest-Rufzeichen kann anders lauten) mit den zentralen Werten als
        Vorgabe: Sie ziehen mit, solange sie leer sind oder noch den
        vorigen zentralen Wert zeigen.

        Ältere Fassungen kannten nur die beiden Felder: Beim ersten Start
        werden sie übernommen, das Rufzeichen aber nicht, wenn es noch der
        frühere Vorgabewert des Contest-Reiters ist."""
        contest = self.modes[self.mode_titles.index("Contest")].my_call_var
        network = self.modes[self.mode_titles.index("Netzwerk")].name_var
        shared = self.saved_state.get("shared")
        shared = shared if isinstance(shared, dict) else {}
        if "station_call" not in shared:
            call = contest.get().strip().upper()
            if call == LEGACY_DEFAULT_CALL:
                contest.set("")
            else:
                self.station_call_var.set(call)
        if "station_name" not in shared:
            self.station_name_var.set(network.get().strip())

        def follow(field, central):
            last = [central()]

            def update(*_):
                value = central()
                if field.get().strip().upper() in ("", last[0].upper()):
                    field.set(value)
                last[0] = value
            if not field.get().strip():
                field.set(last[0])
            return update

        contest_follow = follow(contest, self.station_call)
        network_follow = follow(network, self._station_name)
        self.station_call_var.trace_add("write", contest_follow)
        self.station_call_var.trace_add("write", network_follow)
        self.station_name_var.trace_add("write", network_follow)

    # --- Diplome ---------------------------------------------------------------------
    def _check_awards(self):
        """Neue Siegel eintragen und für das Diplom-Fenster vormerken;
        Rückgabe wie awards.check(): Zahl der nachgetragenen Diplome beim
        allerersten Mal, sonst None."""
        new, seeded = awards.check()
        today = date.today()
        self.pending_seals += [(key, level, today) for key, level in new]
        self.awards_panel.refresh()
        self.lifeline_panel.refresh()
        return seeded

    def _check_awards_at_start(self):
        """Beim allerersten Start still nachtragen, mit einem Hinweis."""
        if self.running_mode:
            return  # Prüfung folgt nach der Übung
        seeded = self._check_awards()
        if seeded:
            messagebox.showinfo(tr("Diplome"), tr(
                "Aus deinem bisherigen Üben wurden {n} Diplome nachgetragen. Du findest sie im Reiter "
                "Statistik unter „Diplome“ und kannst sie dort ansehen und drucken.").format(n=seeded))
        else:
            self.show_pending_seals()

    def show_pending_seals(self):
        if self.pending_seals and not self.running_mode:
            seals, self.pending_seals = self.pending_seals, []
            self._show_diplomas(seals)

    def _show_diplomas(self, seals, title=None):
        if self.diploma_window is not None and self.diploma_window.window is not None:
            self.diploma_window.close()
        self.diploma_window = DiplomaWindow(self.root, seals, self.station_call_var, self.station_name_var,
                                            title)

    def _refresh_all_time(self):
        data = stats.load_all_time()
        self.all_time_panel.refresh(stats.all_time_summary(data), stats.all_time_char_rows(data))
        self.confusion_var.set(self._confusion_text(stats.recent_char_data()))
        self.review_var.set(self._review_text(review.load()))
        self.progress_panel.refresh()
        self.awards_panel.refresh()
        self.lifeline_panel.refresh()

    @staticmethod
    def _review_text(data: dict, today=None) -> str:
        due = review.due_chars(data, today)
        if due:
            return tr("Heute fällig ({n}): ").format(n=len(due)) + " ".join(display_text(ch) for ch in due)
        upcoming = review.next_due(data, today)
        if upcoming is None:
            return tr("Noch nichts in der Lernkartei – sie füllt sich mit jedem Durchgang.")
        day, chars = upcoming
        if day == (today or date.today()) + timedelta(days=1):
            when = tr("morgen")
        else:
            when = tr("am {date}").format(date=day.strftime(tr("%d.%m.")))
        return tr("Heute ist nichts fällig. Als Nächstes {when}: ").format(when=when) + " ".join(display_text(ch) for ch in chars)

    def _drill_due(self):
        """Fällige Zeichen gezielt: stark gewichtet unter dem ganzen
        Zeichensatz (bei nur zwei, drei Zeichen wäre Raten zu leicht), in
        den Einzelzeichen. Die Gewichtung wird dafür eingeschaltet. Fehlende
        fällige Zeichen kommen nur für diesen Durchgang dazu; danach gilt
        wieder der Zeichensatz der Lektion."""
        due = review.due_chars()
        if not due:
            self.review_var.set(self._review_text(review.load()))
            return
        charset = self.charset_var.get()
        if self.drill_restore is not None and charset == self.drill_restore[1]:
            charset = self.drill_restore[0]  # zweimal gedrückt: vom ursprünglichen aus
        extended = charset.upper() + "".join(ch for ch in due if ch not in charset.upper())
        self.drill_restore = (charset, extended) if extended != charset else None
        self.charset_var.set(extended)
        review.focus = set(due)
        self.weighted_var.set(True)
        self.notebook.select(self.tab_ids[self.mode_titles.index("Einzelzeichen")])

    @staticmethod
    def _confusion_text(data: dict) -> str:
        pairs = stats.top_confusions(data)
        if not pairs:
            return tr("Keine Verwechslungen in den letzten {days} Tagen.").format(days=stats.RECENT_DAYS)
        seen = {(sent, typed) for sent, typed, _, _ in pairs}
        lines = []
        for sent, typed, count, share in pairs:
            arrow = "↔" if (typed, sent) in seen else "→"
            sent, typed = display_text(sent), display_text(typed)
            lines.append(tr("{sent} {arrow} {typed}   {count:>3}×   ({share:.0%} der {sent})").format(
                sent=sent, arrow=arrow, typed=typed, count=count, share=share))
        return "\n".join(lines)

    @staticmethod
    def _confusion_charset(data: dict, sent=None) -> str:
        """Zeichen der häufigsten Verwechslungspaare aus `data`, in
        Reihenfolge. Nur Paare, deren getipptes Zeichen schon einmal
        gesendet wurde (`sent`, Standard `data`): ein Vertipper wie „(“
        statt „/“ (Umschalttaste) soll nicht in den Übungs-Zeichensatz."""
        sent = data if sent is None else sent
        chars = []
        pairs = [p for p in stats.top_confusions(data, limit=None) if p[1] in sent]
        for sent, typed, _, _ in pairs[:CONFUSION_PAIRS]:
            for ch in (sent, typed):
                if ch not in chars:
                    chars.append(ch)
        return "".join(chars)

    def _drill_confusions(self):
        """Setzt den Zeichensatz auf die verwechselten Zeichen und wechselt zu
        den Einzelzeichen: ähnlich klingende Zeichen direkt gegeneinander."""
        chars = self._confusion_charset(stats.recent_char_data(), stats.load_all_time())
        if len(chars) < 2:
            self.confusion_var.set(tr("Noch zu wenige Verwechslungen zum gezielten Üben."))
            return
        self.charset_var.set(chars)
        self.notebook.select(self.tab_ids[self.mode_titles.index("Einzelzeichen")])

    def _reset_all_time(self):
        if messagebox.askyesno(
            tr("Gesamtstatistik zurücksetzen"),
            tr("Die komplette Gesamtstatistik (alle bisherigen Durchgänge) wirklich löschen?\n"
               "Das kann nicht rückgängig gemacht werden. Die einzelnen Sitzungs-Logdateien "
               "in stats/ bleiben davon unberührt."),
        ):
            stats.reset_all_time()
            self._refresh_all_time()

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        # Die deutschen Titel sind zugleich die Schlüssel der gespeicherten
        # Einstellungen (window_state.json); angezeigt wird die Übersetzung.
        mode_classes = [
            (N_("Einzelzeichen"), SingleModeFrame),
            (N_("Gruppen"), GroupModeFrame),
            (N_("Wörter"), WordModeFrame),
            (N_("Rufzeichen"), CallsignModeFrame),
            (N_("Kontinuierlich"), ContinuousModeFrame),
            (N_("Sprechen"), ListenModeFrame),
            (N_("QSO"), QsoModeFrame),
            (N_("Contest"), RunModeFrame),
            (N_("Netzwerk"), NetworkModeFrame),
        ]

        self.modes = []
        self.mode_titles = []
        self.tab_ids = []
        for title, frame_cls in mode_classes:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=tr(title))
            extra = {"vary_var": self.vary_var} if getattr(frame_cls, "uses_vary", False) else {}
            if getattr(frame_cls, "uses_tempo_adjust", False):
                extra["adjust_tempo"] = self.adjust_tempo
            if getattr(frame_cls, "uses_network_hooks", False):
                extra.update(practice_start=self._start_practice,
                             practice_stop=self._pause_practice, version=__version__,
                             updater=self.updater, session_closed=self._network_session_closed)
            mode = frame_cls(
                tab, self.charset_var, self.wpm_var, self.freq_var, self.weighted_var, self.farnsworth_wpm,
                on_start=self._lock_tabs, on_stop=self._handle_mode_stop, **extra,
            )
            if hasattr(mode, "restore_settings"):
                mode.restore_settings(self._saved_mode_settings(title))
            self.modes.append(mode)
            self.mode_titles.append(title)
            self.tab_ids.append(str(tab))

    def _lock_tabs(self):
        # Fokus aus Eingabefeldern oben (Zeichen, WPM …) nehmen, sonst
        # landen die Antworten dort; Modi mit eigenem Feld setzen ihn danach.
        self.root.focus_set()
        current = self.notebook.select()
        for tab_id in self.notebook.tabs():
            if tab_id != current:
                self.notebook.tab(tab_id, state="disabled")
        # Eigene Tonausgabe würde die des laufenden Modus abbrechen.
        self.running_mode = True
        self.new_char_button.config(state="disabled")
        self.confusion_button.config(state="disabled")
        self.review_button.config(state="disabled")
        self.daily_bar.set_enabled(False)
        # Der Netzwerk-Reiter zählt selbst nur die Durchgänge, nicht das
        # Warten auf den Trainer.
        if not getattr(self._active_mode(), "uses_network_hooks", False):
            self._start_practice()

    def _start_practice(self):
        if self.practice_started is None:
            self.practice_started = time.time()
            self.practice_tick_id = self.root.after(PRACTICE_TICK_MS, self._practice_tick)

    def _pause_practice(self):
        """Durchgang im Netzwerk zu Ende, verbunden bleibt man: Übungszeit
        und Statistik nachtragen, die Reiter bleiben gesperrt."""
        self._record_practice()
        self._update_practice()
        self._refresh_all_time()
        self._check_awards()  # angezeigt erst nach dem Trennen

    def _network_session_closed(self):
        """Trainer hat seine Sitzung geschlossen: Clubabend gilt auch fürs
        Leiten; das Diplom-Fenster erst jetzt, nicht vor der Gruppe."""
        self._check_awards()
        self.show_pending_seals()

    def _unlock_tabs(self):
        for tab_id in self.notebook.tabs():
            self.notebook.tab(tab_id, state="normal")
        self.running_mode = False
        self.confusion_button.config(state="normal")
        self.review_button.config(state="normal")
        self.daily_bar.set_enabled(True)
        self._sync_lesson()

    def _handle_mode_stop(self):
        review.focus = set()  # gezieltes Üben der Fälligen endet mit dem Durchgang
        self._restore_drill_charset()
        self._record_practice()
        self._update_practice()
        if self.daily.active:
            # Tagesübung: kein Ja/Nein-Dialog, der Ablauf geht weiter (oder endet
            # über finish_daily).
            self._refresh_all_time()
            self.daily.on_block_end(self._active_mode())
            return
        self._unlock_tabs()
        self._refresh_all_time()
        self._offer_next_lesson(self._active_mode())
        self._offer_groups(self._active_mode())
        self._check_awards()
        self.show_pending_seals()

    def finish_daily(self):
        """Tagesübung zu Ende (DailyRunner): Reiter wieder frei."""
        self.running_mode = False
        self._unlock_tabs()
        self._refresh_all_time()
        self._update_practice()
        self._check_awards()  # angezeigt nach der Abendbilanz

    def _restore_drill_charset(self):
        """Nach „Fällige gezielt üben“ wieder der Zeichensatz davor, sofern
        er zwischendurch nicht von Hand geändert wurde."""
        if self.drill_restore is not None:
            before, extended = self.drill_restore
            self.drill_restore = None
            if self.charset_var.get() == extended:
                self.charset_var.set(before)

    def _active_mode(self):
        current = self.notebook.select()
        for tab_id, mode in zip(self.tab_ids, self.modes):
            if tab_id == current:
                return mode
        return None

    def _dispatch_key(self, event):
        # Funktionstasten sind Kürzel des aktiven Reiters und gelten auch in
        # Eingabefeldern (dort haben sie sonst keine Bedeutung).
        if event.keysym == "Escape" and self.daily.active:
            self.daily.abort()
            return
        if event.keysym == "Return" and self.daily.card_open:
            self.daily.continue_now()
            return
        if event.keysym == DAILY_KEY and not self.running_mode and not self.daily.active:
            self.daily.start()
            return
        if event.keysym in FUNCTION_KEYS:
            mode = self._active_mode()
            if mode is not None and hasattr(mode, "on_function_key"):
                mode.on_function_key(event.keysym)
            return
        # Tastendrücke, die eigentlich für ein Eingabefeld gedacht sind (z. B.
        # das WPM-Feld beim Ändern der Geschwindigkeit, oder das Antwortfeld im
        # Gruppen-/Rufzeichen-Modus), sollen nicht zusätzlich als Morse-Antwort
        # gewertet werden.
        if isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        mode = self._active_mode()
        if mode is not None:
            mode.on_key(event)

    def check_for_update(self):
        """Beim Start im Hintergrund: Gibt es auf GitHub ein neueres
        Release? Ohne Internet (oder bei jedem anderen Fehler) bleibt es
        still – das Programm läuft ganz normal weiter."""
        result = {}

        def run():
            try:
                result["version"] = update.latest_version()
            except update.UpdateError:
                result["version"] = None
            except Exception:
                result["version"] = None
                raise  # ins Fehlerprotokoll (threading.excepthook)
        threading.Thread(target=run, daemon=True).start()
        self._await_update_check(result)

    def _await_update_check(self, result):
        if "version" not in result:
            self.root.after(UPDATE_POLL_MS, lambda: self._await_update_check(result))
            return
        version = result["version"]
        self.update_checked = True
        if not update.is_newer(version, __version__):
            return
        available = tr("Version {version} verfügbar").format(version=version)
        if version == self.update_declined or self.running_mode:
            # Schon abgelehnt, oder es läuft gerade eine Übung: nicht dazwischenfragen.
            self.update_var.set(available)
            return
        outcome = self.updater.offer(version, tr("Version {theirs} ist erschienen, du hast {mine}.").format(
            theirs=version, mine=__version__), self.update_var.set)
        if outcome == DECLINED:
            self.update_declined = version
            self.update_var.set(available)

    def restart_for_update(self, args):
        """Update ist installiert: wie beim Schließen alles speichern, nach
        dem Ende der Hauptschleife startet main() das neue Programm."""
        self.restart_args = list(args)
        self.on_close()

    def join_network(self, pin: str):
        """Nach dem Neustart durch ein Update (--join PIN): Reiter Netzwerk,
        wieder als Teilnehmer verbinden."""
        for tab_id, mode in zip(self.tab_ids, self.modes):
            if hasattr(mode, "rejoin"):
                self.notebook.select(tab_id)
                mode.rejoin(pin)

    def on_close(self):
        # Jeder Schritt für sich: Ein Fehler beim Speichern oder in einem
        # Reiter darf das Schließen nicht verhindern.
        # Zuerst die Tagesübung beenden: Sie stellt die gemeinsamen Einstellungen
        # zurück, bevor sie gespeichert werden.
        for step in (lambda: self.daily.abort(quiet=True), self._record_practice, self._save_state,
                     *(mode.on_close for mode in self.modes), audio.release):
            try:
                step()
            except Exception:
                errorlog.record(*sys.exc_info(), version=__version__)
        self.root.destroy()

    # --- Unerwartete Fehler -------------------------------------------------
    def report_callback_exception(self, exc_type, exc, tb):
        """Fehler in einem Tk-Callback (Knopf, Taste, after): protokollieren
        und einmal melden, statt ihn ohne Konsole zu verschlucken."""
        errorlog.record(exc_type, exc, tb, version=__version__)
        self._check_errors(poll=False)

    def thread_exception(self, args):
        """Fehler in einem Hintergrund-Thread: nur protokollieren; gemeldet
        wird im Tk-Thread (_check_errors)."""
        errorlog.record(args.exc_type, args.exc_value, args.exc_traceback, version=__version__)

    def _check_errors(self, poll=True):
        if errorlog.take_unseen() and not self.error_shown:
            self.error_shown = True
            messagebox.showerror(tr("Unerwarteter Fehler"), tr(
                "Im Programm ist ein unerwarteter Fehler aufgetreten. Einzelheiten stehen in\n{path}\n\n"
                "Bitte schick diese Datei mit, wenn du den Fehler meldest.").format(path=errorlog.LOG_FILE),
                parent=self.root)
        if poll:
            self.root.after(ERROR_POLL_MS, self._check_errors)


def main():
    # Feste Fensterklasse, passend zu StartupWMClass in der .desktop-Datei:
    # So ordnen Dock und Taskleiste das Fenster dem AppImage-Icon zu.
    sys.excepthook = lambda *exc: errorlog.record(*exc, version=__version__)
    update.cleanup()
    root = tk.Tk(className="Morsetrainer")
    app = MorseTrainerApp(root)
    root.report_callback_exception = app.report_callback_exception
    threading.excepthook = app.thread_exception
    root.after(ERROR_POLL_MS, app._check_errors)
    if len(sys.argv) == 3 and sys.argv[1] == "--join":
        root.after(300, lambda: app.join_network(sys.argv[2]))
    else:
        root.after(UPDATE_CHECK_DELAY_MS, app.check_for_update)
    root.mainloop()
    found = update.installed()
    if app.restart_args is not None and found is not None:
        update.relaunch(found[0], app.restart_args)


if __name__ == "__main__":
    main()