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
import traceback
from datetime import date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from morsetrainer import DATA_DIR, i18n
from morsetrainer.core import audio, awards, backup, band, errorlog, koch, migration, practice, review, sfx, stats, storage, tempo
from morsetrainer.core.morse import build_text, display_text, key_hint
from morsetrainer.daily_runner import DailyRunner
from morsetrainer.i18n import N_, ctrl_key, tr
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
from morsetrainer.widgets.band_settings import BandSettings
from morsetrainer.widgets.daily_panel import DailyBar
from morsetrainer.widgets.help_window import HelpWindow
from morsetrainer.widgets.lifeline_widget import LifelinePanel
from morsetrainer.widgets.progress_widget import ProgressPanel
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.updater import DECLINED, HINT, STARTED, Updater
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.ui_widgets import ScrollableFrame, one_tab_stop, wrap_pair

__author__ = "DL4YM"
__version__ = "2.45"

# Wer neu anfängt, beginnt mit Koch-Lektion 1.
DEFAULT_CHARSET = koch.lesson_charset(1)
DEFAULT_GEOMETRY = "720x900"
# Mindestbreite des Hauptfensters (Kopfleiste und Reiter haben Platz, auch
# englisch); eine kleinere gespeicherte Breite wird angehoben.
MIN_WIDTH = 720
WINDOW_STATE_FILE = DATA_DIR / "window_state.json"
# Platzhalter-Rufzeichen, das in alten Einstellungsdateien im Contest-Reiter
# stehen kann. Beim Übernehmen in die zentralen Einstellungen gilt es nicht
# als eigenes Rufzeichen und wird verworfen (siehe _follow_station).
OLD_CONTEST_PLACEHOLDER_CALL = "DL4YM"
FUNCTION_KEYS = {f"F{i}" for i in range(1, 13)}
# Startet die Tagesübung; von keinem Reiter belegt.
DAILY_KEY = "F12"
# Esc bzw. F5 beenden die Tagesübung erst, wenn sie innerhalb dieser Zeit
# zweimal gedrückt werden.
DAILY_END_CONFIRM_S = 3.0
# Bedienelemente, die Leertaste, Enter und Pfeile selbst auswerten, wenn sie
# den Tastaturfokus haben.
FOCUS_OWNS_KEYS = (ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.Notebook, ttk.Treeview, ttk.Scale,
                   ttk.Combobox)
# Sprachansage an/aus und „wo bin ich?“ (widgets/announcer.py).
ANNOUNCE_KEY = "F9"
STATUS_KEY = "F11"
# Zeichen je Zeile in der Übersicht der Lernkartei-Fächer (Reiter Statistik).
BOX_CHARS_PER_LINE = 20
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
WHATS_NEW_DELAY_MS = 800  # Hinweis nach einem Update, wenn das Fenster steht
# So oft wird nachgesehen, ob ein Hintergrund-Thread einen Fehler protokolliert hat.
ERROR_POLL_MS = 1000
UPDATE_POLL_MS = 500
UPDATE_ASK_AGAIN_DAYS = 7  # nach „Später“ fragt der Start erst so viele Tage danach wieder
# Übungen, die einzeln abfragen (hören, antworten, das nächste), teilen sich
# den Reiter „Einzeln“; oben wählt man, welche. Die Titel bleiben Schlüssel
# der gespeicherten Einstellungen.
ONE_BY_ONE = (N_("Einzelzeichen"), N_("Gruppen"), N_("Wörter"), N_("Rufzeichen"))
ONE_BY_ONE_LABELS = {"Einzelzeichen": N_("Zeichen")}  # sonst wie der Titel
# Angezeigter Reitername, wo er vom Schlüssel abweicht.
TAB_NAMES = {"Kontinuierlich": N_("Am Stück")}
# Einmaliger Hinweis nach einem Update auf (mindestens) diese Version, für
# Änderungen, bei denen man sonst etwas Gewohntes nicht wiederfindet.
WHATS_NEW = {
    "2.40": N_("Zeichen, Gruppen, Wörter und Rufzeichen stehen jetzt gemeinsam im Reiter „Einzeln“; den "
               "Inhalt wählst du dort oben unter „Inhalt“ (oder Alt+1 noch einmal drücken). „Kontinuierlich“ "
               "heißt jetzt „Am Stück“. Alles Weitere steht unter Hilfe, Änderungen."),
    "2.45": N_("Das Tagesziel stellst du jetzt unter „Einstellungen …“ ein (Karte „Üben“). Die Tagesübung "
               "beendet Esc oder F5 erst beim zweiten Druck; dafür gibt es den Knopf „Tagesübung beenden“. "
               "Alles Weitere steht unter Hilfe, Änderungen."),
}


# Restzeit „3:12“: für die Ansage als „3 Min. 12 s“ (announcer.speakable
# macht daraus Minuten und Sekunden).
_CLOCK = re.compile(r"\b(\d+):(\d{2})\b")


def _spoken_clock(match) -> str:
    minutes, seconds = int(match.group(1)), int(match.group(2))
    parts = ([f"{minutes} Min."] if minutes else []) + ([f"{seconds} s"] if seconds or not minutes else [])
    return " ".join(parts)


class MorseTrainerApp:
    """Das Hauptfenster: Kopfleiste mit den gemeinsamen Einstellungen
    (Zeichensatz, Tempo, Tonhöhe, Lektion), Tagesübung, die Übungs-Reiter und
    der Reiter Statistik, Fußzeile, Einstellungsfenster und Tastenkürzel.
    Speichert beim Schließen alles in window_state.json."""
    def __init__(self, root):
        self.root = root
        # Eingabemethode (ibus u. a., XIM) aus: Unter X11 kostet sie jedes
        # Fenster eine Rundreise zum IM-Server, das Hauptfenster bräuchte
        # dann mehrere Sekunden, und antwortet der Server nicht, hängt Tk.
        # Umlaute der Tastatur gehen weiter, nur Tottasten/Compose nicht.
        if root.tk.call("tk", "windowingsystem") == "x11":
            root.tk.call("tk", "useinputmethods", "0")
        self.running_mode = False
        # „Fällige gezielt üben“: (Zeichensatz davor, erweiterter Zeichensatz);
        # nach dem Durchgang kommt der alte zurück, siehe _handle_mode_stop.
        self.drill_restore = None
        self.restart_args = None  # nach einem Update: neu starten mit diesen Argumenten
        self.restart_command = None  # „Jetzt neu starten“ (Sprache, Kontrast): dieser Befehl
        self.groups_offered = set()  # Lektionen, für die der Gruppen-Hinweis schon kam
        self.error_shown = False  # Hinweis auf fehler.log kommt einmal je Sitzung
        root.title(tr("Morsetrainer von {author}").format(author=__author__))
        self._set_icon()
        self.saved_state = self._load_state()
        self.updater = Updater(root, __version__, self.restart_for_update)
        declined = self.saved_state.get("update_declined")
        self.update_declined = declined if isinstance(declined, str) else None  # „Später“ zu dieser Version
        try:
            self.update_declined_on = date.fromisoformat(self.saved_state.get("update_declined_on"))
        except (TypeError, ValueError):
            self.update_declined_on = date.today() if self.update_declined else None
        self.update_available = None  # (Version, Neuerungen) des neueren Releases
        self.update_checked = False  # Updateprüfung beim Start abgeschlossen
        root.geometry(self._initial_geometry())
        root.resizable(True, True)

        # Farbschema vor dem Aufbau (wirkt daher erst nach einem Neustart).
        shared = self.saved_state.get("shared")
        self.contrast_at_start = isinstance(shared, dict) and shared.get("contrast") is True
        theme.set_palette("contrast" if self.contrast_at_start else "light")
        theme.apply(root)
        self.announcer = announcer.install(root)
        announcer.set_main_place(lambda: tr("Reiter {name}.").format(name=self._tab_name()))
        self._build_settings()
        self._restore_shared_settings()
        self._update_more()
        self._build_footer()
        # Vor dem Notizbuch gepackt: steht über den Reitern.
        self.daily_bar = DailyBar(self.root, on_start=lambda: self.daily.start(),
                                  on_continue=lambda: self.daily.continue_now(),
                                  on_end=lambda: self.daily.abort())
        self.daily_end_pressed = 0.0  # Zeitpunkt des ersten Esc/F5 (siehe _confirm_daily_end)
        self.daily_bar.pack()
        self._build_notebook()
        self._follow_station()
        self._build_all_time_tab()
        # Diplome und Lebenslinie füllt _check_awards_at_start, wenn das
        # Fenster schon steht: Die Auswertung braucht nach Jahren Übung Zeit.
        self._refresh_all_time(with_awards=False)
        # Tab-Reihenfolge folgt der Stapelreihenfolge: die Fußzeile (Hilfe)
        # zuletzt, nach Tagesübung und Reitern.
        self.footer.lift()
        self.daily = DailyRunner(self, self.daily_bar)
        self.pending_seals = []  # neue Siegel, die noch kein Diplom-Fenster gezeigt hat
        self.diploma_window = None
        self.root.after(500, self._check_awards_at_start)
        # Ausgabegerät wach halten, damit kein Zeichenanfang verloren geht.
        audio.keep_awake()

        root.bind("<Key>", self._dispatch_key)
        # Schriftgröße in jedem Fenster, auch in Eingabefeldern.
        for keys, direction in ((("plus", "equal", "KP_Add"), 1), (("minus", "KP_Subtract"), -1),
                                (("0", "KP_0", "KP_Insert"), 0)):
            for key in keys:
                for modifier in ("Control", "Command") if sys.platform == "darwin" else ("Control",):
                    root.bind_all(f"<{modifier}-{key}>", lambda e, d=direction: self.zoom(d) or "break")
        # Die Reiter sind erst nach dem Einlesen der Schriftgröße entstanden:
        # ihre Umbruchbreiten jetzt an die Schriftgröße anpassen.
        theme.scale_wraps(root)
        # Alt+1 … Alt+7: die Reiter, Alt+0 zusätzlich der letzte (Statistik,
        # wie vor dem Zusammenlegen der Reiter); auf dem Mac Cmd, Option+Ziffer
        # schreibt dort Sonderzeichen. Strg+B: Bandbedingungen.
        tab_modifier = "Command" if sys.platform == "darwin" else "Alt"
        # Cmd+0 bleibt auf dem Mac der Schrift (normal groß), wie in
        # Mac-Programmen üblich.
        for number in range(1, 10) if sys.platform == "darwin" else range(10):
            root.bind_all(f"<{tab_modifier}-Key-{number}>",
                          lambda e, n=number: self.select_tab(n - 1 if n else -1) or "break")
        # Groß und klein, damit es auch mit Feststelltaste geht; auf dem Mac auch Cmd+B.
        for modifier in ("Control", "Command") if sys.platform == "darwin" else ("Control",):
            for key in ("b", "B"):
                root.bind_all(f"<{modifier}-{key}>", lambda e: self.band_settings.open_window() or "break")
        for modifier in ("Control", "Command") if sys.platform == "darwin" else ("Control",):
            root.bind_all(f"<{modifier}-comma>", lambda e: self.open_settings() or "break")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if sys.platform == "darwin":
            self._bind_mac_keys()

    def _bind_mac_keys(self):
        """Mac: Cmd+Q und „Einstellungen …“ im App-Menü laufen über Tk
        selbst (ohne ::tk::mac::Quit beendet Tk ohne on_close, also ohne zu
        speichern). F9, F11 und F12 sind dort Medientasten bzw. vom System
        belegt (Fn+F11 zeigt den Schreibtisch): zusätzlich Cmd+Umschalt+A
        (Ansage), W (wo bin ich) und T (Tagesübung)."""
        self.root.createcommand("::tk::mac::Quit", self.on_close)
        self.root.createcommand("::tk::mac::ShowPreferences", self.open_settings)
        for letter, action in (("A", self.toggle_announce), ("W", self.read_status),
                               ("T", self._start_daily)):
            for key in (letter, letter.lower()):
                self.root.bind_all(f"<Command-Shift-{key}>", lambda e, a=action: a() or "break")

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
            "update_declined_on": self.update_declined_on.isoformat() if self.update_declined_on else None,
            "one_by_one": self.one_by_one_var.get(),
            "seen_version": __version__,
        }
        try:
            storage.write_json_atomic(WINDOW_STATE_FILE, state, indent=2)
        except OSError as exc:
            return str(exc)
        return None

    def show_whats_new(self) -> None:
        """Nach einem Update einmal zeigen, was sich an der Bedienung geändert
        hat (WHATS_NEW); bei einer frischen Installation nichts."""
        if not self.saved_state:
            return
        seen = self.saved_state.get("seen_version")
        versions = sorted(WHATS_NEW, key=update.parse_version)
        notes = [tr(WHATS_NEW[version]) for version in versions
                 if (seen is None or update.is_newer(version, seen)) and not update.is_newer(version, __version__)]
        if notes:
            messagebox.showinfo(tr("Neu in Version {version}").format(version=__version__), "\n\n".join(notes),
                                parent=self.root)

    def _build_settings(self):
        """Kopfleiste: Koch-Lektion, Tempo, Tonhöhe und Zeichensatz immer
        sichtbar; seltener gebrauchte Optionen klappen darunter auf."""
        header = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)

        # Lektion links, Tempo und Ton rechts; reicht die Breite nicht (große
        # Schrift, schmales Fenster), rutschen Tempo und Ton in eine zweite
        # Zeile, statt sich mit der Lektion zu überdecken.
        top = ttk.Frame(header)
        top.grid(row=0, column=0, columnspan=2, sticky="we")
        lesson_row, tone_row = ttk.Frame(top), ttk.Frame(top)
        wrap_pair(top, lesson_row, tone_row)
        self.charset_var = tk.StringVar(value=DEFAULT_CHARSET)
        self._build_koch_row(lesson_row)
        self.freq_var = tk.IntVar(value=600)
        ttk.Label(tone_row, text="Hz").pack(side="right", padx=(4, 0))
        freq_spin = ttk.Spinbox(tone_row, from_=300, to=1000, increment=50, textvariable=self.freq_var, width=5)
        freq_spin.pack(side="right")
        announcer.name(freq_spin, tr("Tonhöhe"), value=lambda: f"{freq_spin.get()} Hz")
        # Standard für Einsteiger: Koch-Tempo, Zeichen schnell, Pausen lang.
        self.wpm_var = tk.IntVar(value=koch.RECOMMENDED_WPM)
        ttk.Label(tone_row, text="WPM").pack(side="right", padx=(4, 16))
        wpm_spin = ttk.Spinbox(tone_row, from_=5, to=40, textvariable=self.wpm_var, width=4)
        wpm_spin.pack(side="right")
        announcer.name(wpm_spin, tr("Tempo"), value=lambda: f"{wpm_spin.get()} WPM")
        freq_spin.lift()  # Tab wie auf dem Bildschirm: erst Tempo, dann Tonhöhe

        ttk.Label(header, text=tr("Zeichen")).grid(row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 8))
        charset_entry = ttk.Entry(header, textvariable=self.charset_var, font=theme.MONO)
        charset_entry.grid(row=1, column=1, sticky="we", pady=(6, 0))
        # Zeichensatz Zeichen für Zeichen (mit Punkt, Komma … ist er kein Wort).
        announcer.name(charset_entry, tr("Zeichen"),
                       value=lambda: announcer.spell_chars(self.charset_var.get().strip()) or tr("leer"))
        announcer.echo(charset_entry)

        toggle_row = ttk.Frame(header)
        toggle_row.grid(row=2, column=0, columnspan=2, sticky="we", pady=(4, 0))
        more_part, settings_part = ttk.Frame(toggle_row), ttk.Frame(toggle_row)
        wrap_pair(toggle_row, more_part, settings_part)
        self.more_var = tk.BooleanVar(value=False)
        self.more_button = ttk.Button(more_part, style="Flat.TButton", command=self._toggle_more)
        self.more_button.pack(side="left")
        self.extras_var = tk.StringVar(value="")
        theme.hint(more_part, textvariable=self.extras_var).pack(side="left", padx=(8, 0))
        # Umrechnung für alle, die in ZpM/BpM denken (DL-Kurse, RufZ, HST);
        # hier statt neben dem WPM-Feld, weil die obere Zeile voll ist.
        self.cpm_var = tk.StringVar(value="")
        theme.hint(settings_part, textvariable=self.cpm_var).pack(side="right")
        ttk.Button(settings_part, text=tr("Einstellungen … ({key})").format(key=ctrl_key(",")),
                   style="Flat.TButton", command=self.open_settings).pack(side="right", padx=(0, 12))

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
            self.more_frame, text=tr("Schwache Zeichen bevorzugen (ab dem nächsten Durchgang)"),
            variable=self.weighted_var,
        ).pack(anchor="w", pady=2)

        self.vary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.more_frame, text=tr("Tonhöhe und Tempo leicht variieren (gegen Gewöhnung an einen Klang)"),
            variable=self.vary_var,
        ).pack(anchor="w", pady=2)

        # Einstellungen, die man einmal vornimmt (Station, Sprache,
        # Barrierefreiheit, Daten): eigenes Fenster (Strg+Komma), damit der
        # Bereich über den Reitern nur Übungsoptionen enthält. Beim Start
        # versteckt gebaut und dann nur ein- und ausgeblendet.
        window = self.settings_window = tk.Toplevel(self.root)
        window.withdraw()
        window.title(tr("Einstellungen"))
        window.transient(self.root)
        window.configure(background=theme.BG)
        window.resizable(True, False)
        window.protocol("WM_DELETE_WINDOW", self.close_settings)
        window.bind("<Escape>", lambda e: self.close_settings())
        self.settings_focus_before = None
        body = ttk.Frame(window, padding=10)
        body.pack(fill="both", expand=True)
        station_card = theme.card(body, tr("Station"), padx=0)
        practice_card = theme.card(body, tr("Üben"), padx=0)
        language_card = theme.card(body, tr("Sprache / Language"), padx=0)
        access_card = theme.card(body, tr("Barrierefreiheit"), padx=0)
        data_card = theme.card(body, tr("Daten"), padx=0)
        bottom = ttk.Frame(body)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text=tr("Schließen"), command=self.close_settings).pack(side="right")
        # Erst sichtbar, wenn eine Einstellung erst nach einem Neustart wirkt.
        self.restart_button = ttk.Button(bottom, text=tr("Jetzt neu starten"), command=self.restart_now)

        # Eigenes Rufzeichen und Name: für die Diplome und als Vorgabe in
        # den Reitern Contest und Netzwerk (siehe _follow_station).
        station = ttk.Frame(station_card)
        station.pack(fill="x", pady=2)
        self.station_call_var = tk.StringVar(value="")
        self.station_name_var = tk.StringVar(value="")
        ttk.Label(station, text=tr("Rufzeichen", context="eigenes")).pack(side="left")
        call_entry = ttk.Entry(station, textvariable=self.station_call_var, width=12)
        call_entry.pack(side="left", padx=(6, 12))
        ttk.Label(station, text=tr("Name")).pack(side="left")
        name_entry = ttk.Entry(station, textvariable=self.station_name_var, width=14)
        name_entry.pack(side="left", padx=(6, 8))
        announcer.echo(call_entry)
        announcer.echo(name_entry)
        theme.hint(station, text=tr("falls vorhanden; für Diplome, Contest und Netzwerk")).pack(side="left")

        # Tagesziel, angezeigt in der Fußzeile; so lang wie die Tagesübung
        # (core/daily.py).
        self.daily_goal_var = tk.IntVar(value=10)
        goal = ttk.Frame(practice_card)
        goal.pack(fill="x", pady=2)
        ttk.Label(goal, text=tr("Tagesziel")).pack(side="left")
        goal_spin = ttk.Spinbox(goal, from_=0, to=240, increment=5, textvariable=self.daily_goal_var, width=5)
        goal_spin.pack(side="left", padx=(6, 4))
        announcer.name(goal_spin, tr("Tagesziel"), value=lambda: tr("{n} Minuten").format(n=goal_spin.get()))
        ttk.Label(goal, text=tr("Min. pro Tag")).pack(side="left")
        theme.hint(goal, text=tr("0 = ohne Ziel. Lieber täglich kurz als selten lang.")).pack(
            side="left", padx=(8, 0))

        # Zweisprachig beschriftet, damit man auch nach versehentlichem
        # Umschalten zurückfindet; wirkt ab dem nächsten Start (i18n.py).
        language = ttk.Frame(language_card)
        language.pack(fill="x", pady=2)
        self.language_var = tk.StringVar(value=i18n.LANG)
        self.language_box = ttk.Combobox(language, values=list(i18n.LANGUAGES.values()), state="readonly",
                                         width=10)
        self.language_box.set(i18n.LANGUAGES[i18n.LANG])
        self.language_box.pack(side="left", padx=(0, 8))
        self.language_box.bind("<<ComboboxSelected>>", lambda e: self._choose_language())
        self.language_hint_var = tk.StringVar(value="")
        theme.hint(language, textvariable=self.language_hint_var).pack(side="left")

        # Schriftgröße (Barrierefreiheit), auch per Strg+Plus/Minus/0.
        zoom = ttk.Frame(access_card)
        zoom.pack(fill="x", pady=2)
        ttk.Label(zoom, text=tr("Schriftgröße")).pack(side="left")
        self.font_scale_var = tk.IntVar(value=theme.NORMAL_ZOOM)
        self.zoom_box = ttk.Combobox(zoom, values=[f"{step} %" for step in theme.ZOOM_STEPS], state="readonly",
                                     width=7)
        self.zoom_box.set(f"{theme.NORMAL_ZOOM} %")
        self.zoom_box.pack(side="left", padx=(6, 8))
        self.zoom_box.bind("<<ComboboxSelected>>", lambda e: self.set_font_scale(int(self.zoom_box.get().split()[0])))
        theme.hint(zoom, text=tr("Strg+Plus größer, Strg+Minus kleiner, Strg+0 normal")).pack(side="left")
        self.font_scale_var.trace_add("write", lambda *_: self._apply_font_scale())

        # Hoher Kontrast (Barrierefreiheit), ab dem nächsten Start.
        contrast = ttk.Frame(access_card)
        contrast.pack(fill="x", pady=2)
        self.contrast_var = tk.BooleanVar(value=self.contrast_at_start)
        ttk.Checkbutton(contrast, text=tr("Hoher Kontrast (Schwarz, Weiß, Gelb)"), variable=self.contrast_var,
                        command=self._contrast_toggled).pack(side="left")
        self.contrast_hint_var = tk.StringVar(value="")
        theme.hint(contrast, textvariable=self.contrast_hint_var).pack(side="left", padx=(8, 0))

        # Sprachansage für Blinde und Sehbehinderte (widgets/announcer.py).
        speak = ttk.Frame(access_card)
        speak.pack(fill="x", pady=2)
        ttk.Checkbutton(speak, text=tr("Rückmeldung ansagen (F9)"), variable=self.announcer.var,
                        command=self._announce_toggled).pack(side="left")
        self.announce_hint_var = tk.StringVar(value=tr("F11 liest vor, wo du bist"))
        theme.hint(speak, textvariable=self.announce_hint_var, wrap=420).pack(side="left", padx=(8, 0))

        # Bandbedingungen für alle Reiter; dort nur an/aus (band_settings.py).
        self.band_settings = BandSettings(self.root)
        self.band_settings.attach_preview(
            lambda: (self.wpm_var.get(), self.freq_var.get(), self.station_call()), self._preview_blocked)
        band_row = ttk.Frame(self.more_frame)
        band_row.pack(fill="x", pady=2)
        ttk.Label(band_row, text=tr("Bandbedingungen")).pack(side="left")
        ttk.Button(band_row, text=tr("Einstellen … ({key})").format(key=ctrl_key("B")),
                   command=self.band_settings.open_window).pack(side="left", padx=(6, 8))
        self.band_summary_var = tk.StringVar(value="")
        theme.hint(band_row, textvariable=self.band_summary_var, wrap=440).pack(side="left")
        self.band_settings.subscribe(lambda: self.band_summary_var.set(self.band_settings.summary()))

        # Sichern und Einlesen aller Einstellungen und Daten (core/backup.py),
        # etwa für den Umzug auf einen neuen Rechner.
        data = ttk.Frame(data_card)
        data.pack(fill="x", pady=2)
        ttk.Button(data, text=tr("Sichern …"), command=self._export_data).pack(side="left", padx=(0, 4))
        ttk.Button(data, text=tr("Einlesen …"), command=self._import_data).pack(side="left", padx=(0, 8))
        theme.hint(data, text=tr("alle Einstellungen und Statistiken, z. B. für einen neuen Rechner")).pack(
            side="left")

        for var in (self.more_var, self.farnsworth_enabled_var, self.farnsworth_wpm_var, self.wpm_var,
                    self.weighted_var, self.vary_var):
            var.trace_add("write", lambda *_: self._update_more())
        for var in (self.wpm_var, self.farnsworth_wpm_var, self.farnsworth_enabled_var):
            var.trace_add("write", lambda *_: self._update_cpm())
        self._update_cpm()
        ttk.Separator(self.root).pack(fill="x", padx=10, pady=(4, 0))

    def open_settings(self) -> None:
        """Einstellungsfenster zeigen (Strg+Komma); der Fokus geht hinein."""
        window = self.settings_window
        if window.state() == "withdrawn":
            self.settings_focus_before = self.root.focus_get()
        window.deiconify()
        window.lift()
        window.focus_set()
        announcer.say(tr("Einstellungen") + ".")

    def close_settings(self) -> None:
        """Ausblenden und den Fokus zurückgeben, etwa ans Eingabefeld."""
        self.settings_window.withdraw()
        focus, self.settings_focus_before = self.settings_focus_before, None
        try:
            if focus is not None and focus.winfo_exists():
                focus.focus_set()
        except tk.TclError:
            pass

    def _choose_language(self):
        """Gewählte Sprache merken (gespeichert in _save_state); sie gilt ab
        dem nächsten Start, siehe i18n.py."""
        chosen = next(k for k, v in i18n.LANGUAGES.items() if v == self.language_box.get())
        self.language_var.set(chosen)
        self.language_hint_var.set("" if chosen == i18n.LANG else tr("wirkt nach Neustart des Programms"))
        self._show_restart_button()

    def _export_data(self):
        """Einstellungen und Daten als ZIP an einen frei gewählten Ort sichern."""
        self._save_state()  # damit die aktuellen Einstellungen mit hineinkommen
        path = filedialog.asksaveasfilename(
            parent=self.root, title=tr("Daten sichern"), defaultextension=".zip",
            initialfile=tr("Morsetrainer-Sicherung-{date}.zip").format(date=date.today().isoformat()),
            initialdir=str(Path.home()), filetypes=[("ZIP", "*.zip")],
        )
        if not path:
            return
        try:
            count = backup.export_data(Path(path), __version__)
        except OSError as exc:
            messagebox.showerror(tr("Daten sichern"), tr("Die Sicherung konnte nicht geschrieben werden:\n{error}")
                                 .format(error=exc), parent=self.root)
            return
        messagebox.showinfo(tr("Daten sichern"), tr(
            "{count} Dateien gesichert in\n{path}\n\nAuf dem neuen Rechner unter „Einstellungen → Daten → "
            "Einlesen …“ wieder einlesen.").format(count=count, path=path), parent=self.root)

    def _import_data(self):
        """Sicherung einlesen; ersetzt alle Daten, danach beendet sich das
        Programm, ohne die alten Einstellungen zurückzuschreiben."""
        if self.running_mode or self.daily.active:
            messagebox.showinfo(tr("Daten einlesen"), tr("Bitte zuerst die laufende Übung beenden."),
                                parent=self.root)
            return
        path = filedialog.askopenfilename(
            parent=self.root, title=tr("Daten einlesen"), initialdir=str(Path.home()),
            filetypes=[("ZIP", "*.zip"), (tr("Alle Dateien"), "*")],
        )
        if not path:
            return
        try:
            info = backup.read_info(Path(path))
        except backup.BackupError:
            messagebox.showerror(tr("Daten einlesen"), tr("Das ist keine Sicherung des Morsetrainers."),
                                 parent=self.root)
            return
        if not messagebox.askyesno(tr("Daten einlesen"), tr(
                "Sicherung vom {created} (Version {version}) einlesen?\n\nAlle bisherigen Einstellungen und "
                "Statistiken auf diesem Rechner werden ersetzt; der bisherige Stand wird vorher in {folder} "
                "gesichert. Danach beendet sich das Programm, bitte neu starten.").format(
                created=str(info.get("created", "?")).replace("T", " "), version=info.get("version", "?"),
                folder=DATA_DIR), parent=self.root):
            return
        try:
            backup.import_data(Path(path), __version__)
        except (OSError, backup.BackupError) as exc:
            messagebox.showerror(tr("Daten einlesen"), tr("Einlesen fehlgeschlagen:\n{error}").format(error=exc),
                                 parent=self.root)
            return
        messagebox.showinfo(tr("Daten einlesen"), tr(
            "Daten eingelesen. Das Programm beendet sich jetzt; beim nächsten Start gelten die eingelesenen "
            "Einstellungen."), parent=self.root)
        self.on_close(keep_files=True)

    def _update_cpm(self):
        """ZpM-Hinweise zu den WPM-Feldern (PARIS-Umrechnung, core/tempo.py),
        mit Farnsworth fürs effektive Tempo; leer bzw. ohne ZpM, solange ein
        Feld keine Zahl enthält."""
        try:
            wpm = self.wpm_var.get()
            effective = self.farnsworth_wpm()
            if effective is None:
                self.cpm_var.set(tr("{wpm} WPM ≈ {cpm} ZpM").format(wpm=wpm, cpm=tempo.cpm(wpm)))
            else:
                # Gehört wird das effektive Tempo (daneben steht „Farnsworth
                # 10“); nur das Zeichentempo umzurechnen hieße bei 20/10
                # „100 ZpM“ statt rund 50.
                self.cpm_var.set(tr("≈ {cpm} ZpM effektiv").format(cpm=tempo.cpm(effective)))
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
        self.farnsworth_cpm_var.set(tr("{wpm} (nicht bei einzelnen Zeichen)").format(wpm=fw))

    def _contrast_toggled(self) -> None:
        changed = self.contrast_var.get() != self.contrast_at_start
        self.contrast_hint_var.set(tr("wirkt nach Neustart des Programms") if changed else "")
        self._show_restart_button()
        announcer.say(tr("Hoher Kontrast nach Neustart.") if changed and self.contrast_var.get() else "")

    def _show_restart_button(self) -> None:
        """„Jetzt neu starten“ zeigen, solange Sprache oder Kontrast anders
        eingestellt sind als beim Start (und der Neustart möglich ist)."""
        pending = self.language_var.get() != i18n.LANG or self.contrast_var.get() != self.contrast_at_start
        if pending and update.restart_command() is not None:
            self.restart_button.pack(side="left")
        else:
            self.restart_button.pack_forget()

    def restart_now(self) -> None:
        """Alles speichern wie beim Schließen, danach startet main() das
        Programm neu."""
        self.restart_command = update.restart_command()
        self.on_close()

    def toggle_announce(self) -> None:
        """F9: Ansage an/aus, hörbar bestätigt."""
        self.announcer.var.set(not self.announcer.var.get())
        self._announce_toggled()

    def _announce_toggled(self) -> None:
        reason = self.announcer.available()
        if reason is not None:
            # Ohne Stimme: Fehlerton (wer nichts sieht, merkt es so) und der
            # Grund auch dort, wo man gerade hinschaut.
            self.announce_hint_var.set(reason)
            mode = self._active_mode()
            if mode is not None and hasattr(mode, "status_var"):
                mode.status_var.set(reason)
            sfx.play_error()
            return
        self.announcer.say(tr("Ansage an.") if self.announcer.enabled() else tr("Ansage aus."), force=True)

    def read_status(self) -> None:
        """F11: vorlesen, wo man ist – Reiter, Status, Rückmeldung, Restzeit
        oder die Karte der Tagesübung."""
        if self.daily.active and self.daily.card_open:
            self.announcer.say(self.daily.card_text, force=True)
            return
        if self._active_mode() is None:  # Reiter Statistik
            self.announcer.say(self.statistics_spoken(), force=True)
            return
        parts = [self._tab_name()]
        mode = self._active_mode()
        # session_info_var: Adresse und PIN des Trainers im Netzwerk; live_var
        # (Am Stück) und score_var (Contest, Quiz) mit Zwischenstand und Restzeit.
        for attr in ("status_var", "session_info_var", "feedback_var", "live_var", "score_var", "remaining_var",
                     "progress_var"):
            var = getattr(mode, attr, None)
            text = var.get().strip() if var is not None else ""
            if attr in ("live_var", "score_var", "remaining_var"):
                text = _CLOCK.sub(_spoken_clock, text)
            if attr == "progress_var":  # „3/20“ im Reiter Sprechen
                text = re.sub(r"^(\d+)/(\d+)$", lambda m: tr("{done} von {total}").format(
                    done=m.group(1), total=m.group(2)), text)
            if text:
                parts.append(text.replace("\n", ". "))
        self.announcer.say(". ".join(parts) + ".", force=True)

    def select_tab(self, index: int) -> None:
        """Reiter Nr. `index` (ab 0, −1 der letzte) zeigen, wenn er nicht
        gesperrt ist (während eines Durchgangs sind die anderen Reiter
        gesperrt). Eine Ziffer ohne Reiter sagt, wie viele es gibt; die des
        Reiters „Einzeln“ schaltet dort den Inhalt weiter."""
        tabs = self.notebook.tabs()
        if index >= len(tabs):
            announcer.say(tr("Es gibt nur {n} Reiter.").format(n=len(tabs)))
            return
        if self.one_by_one_tab is not None and tabs[index] == str(self.one_by_one_tab) \
                and self.notebook.select() == tabs[index]:
            # Schon in „Einzeln“: dieselbe Taste noch einmal schaltet den Inhalt weiter.
            self._step_content(1)
            return
        if str(self.notebook.tab(tabs[index], "state")) == "normal":
            self.notebook.select(tabs[index])

    def statistics_spoken(self) -> str:
        """Der Reiter Statistik zum Vorlesen (F11): Gesamtergebnis, schwächste
        Zeichen, häufigste Verwechslungen, Lernkartei, Siegel, heute geübt."""
        spell = announcer.spell
        data = stats.load_all_time()
        summary = stats.all_time_summary(data)
        parts = [tr("Statistik")]
        if summary["total"]:
            parts.append(tr("Insgesamt {correct} von {total} Zeichen richtig, {percent} Prozent").format(
                correct=summary["correct"], total=summary["total"], percent=round(summary["accuracy_pct"])))
            weak = [row for row in stats.all_time_char_rows(data) if row[2]][:3]
            if weak:
                parts.append(tr("Die meisten Fehler: ") + ", ".join(
                    tr("{char} {times}").format(char=spell(char), times=announcer.times(wrong))
                    for char, _, wrong, *_ in weak))
        else:
            parts.append(tr("Noch keine Durchgänge"))
        pairs = stats.top_confusions(stats.recent_char_data(), limit=3)
        if pairs:
            parts.append(tr("Häufigste Verwechslungen: ") + ", ".join(
                tr("{sent} als {typed} getippt, {times}").format(sent=spell(sent), typed=spell(typed),
                                                                 times=announcer.times(count))
                for sent, typed, count, _ in pairs))
        review_data = review.load()
        due = review.due_chars(review_data)
        parts.append((tr("Heute in der Lernkartei fällig: ") + ", ".join(spell(ch) for ch in due)) if due
                     else tr("In der Lernkartei ist heute nichts fällig"))
        boxes = [tr("Fach {n}: {chars}").format(n=index + 1, chars=", ".join(spell(ch) for ch in chars))
                 for index, chars in enumerate(review.by_box(review_data)) if chars]
        if boxes:
            parts.append(tr("In der Lernkartei liegen ") + "; ".join(boxes))
        parts.append(self.awards_panel.summary_var.get())
        if self.practice_var.get():
            parts.append(self.practice_var.get())
        return ". ".join(part for part in parts if part) + "."

    def _tab_name(self) -> str:
        """Name des sichtbaren Reiters, wie er angezeigt (und angesagt) wird."""
        name = self.notebook.tab("current", "text")
        if self.one_by_one_tab is not None and self.notebook.select() == str(self.one_by_one_tab):
            current = self.one_by_one_var.get()
            name += ", " + tr(ONE_BY_ONE_LABELS.get(current, current))
        return name

    def _announce_tab(self, event=None) -> None:
        hint = " " + tr("F11 liest die Übersicht vor.") if self._active_mode() is None else ""
        announcer.say(tr("Reiter {name}.").format(name=self._tab_name()) + hint)

    def zoom(self, direction: int) -> None:
        """Strg+Plus (1), Strg+Minus (−1), Strg+0 (0 = normal)."""
        current = self.font_scale_var.get()
        self.set_font_scale(theme.NORMAL_ZOOM if direction == 0 else theme.zoom_step(current, direction))

    def set_font_scale(self, percent: int) -> None:
        """Schriftgröße in Prozent setzen, begrenzt auf die Stufen in
        theme.ZOOM_STEPS (wirkt sofort)."""
        self.font_scale_var.set(min(max(percent, theme.ZOOM_STEPS[0]), theme.ZOOM_STEPS[-1]))

    def _apply_font_scale(self) -> None:
        try:
            percent = self.font_scale_var.get()
        except tk.TclError:
            return
        if percent != theme.scale():
            theme.set_scale(self.root, percent)
            self._fit_window()
        self.zoom_box.set(f"{theme.scale()} %")

    def _fit_window(self) -> None:
        """Nach dem Vergrößern der Schrift: Fenster so weit wachsen lassen,
        dass alles hineinpasst (höchstens bildschirmgroß, nie kleiner)."""
        root = self.root
        if root.state() != "normal":
            return  # maximiert oder minimiert: nicht anfassen
        root.update_idletasks()
        width = min(max(root.winfo_width(), root.winfo_reqwidth()), root.winfo_screenwidth() - 40)
        height = min(max(root.winfo_height(), root.winfo_reqheight()), root.winfo_screenheight() - 80)
        if (width, height) != (root.winfo_width(), root.winfo_height()):
            root.geometry(f"{width}x{height}")

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
        """Lektion und Knopf „Neues Zeichen“ an den Zeichensatz anpassen; ein
        eigener Zeichensatz zeigt „(eigene Zeichen)“ und den Weg zurück zur
        Lektion."""
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
            # So langsame Zeichen lassen sich mitzählen statt als Klangbild
            # erkennen; darauf hinweisen.
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
               "Bei den Gruppen (Reiter Einzeln) hörst du mehrere Zeichen direkt hintereinander, wie im Funkbetrieb, "
               "und tippst sie dann. "
               "Dort wird dir auch die nächste Lektion angeboten.\n\n"
               "Zu den Gruppen wechseln?").format(lesson=lesson, correct=correct, total=total,
                                                     share=correct / total),
        ):
            self.show_mode("Gruppen")

    def _build_footer(self):
        # Vor dem Notebook gepackt, damit es bei kleinem Fenster nicht verdrängt wird.
        """Fußzeile: Übungszeit heute, Hinweis auf Updates, Version und Autor,
        Knopf Hilfe."""
        footer = self.footer = ttk.Frame(self.root, padding=(10, 4))
        footer.pack(side="bottom", fill="x")
        self.practice_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.practice_var).pack(side="left")
        self.update_var = tk.StringVar(value="")  # Updateprüfung beim Start
        update_box = ttk.Frame(footer)
        update_box.pack(side="left", padx=(12, 0))
        ttk.Label(update_box, textvariable=self.update_var, style="Footer.TLabel", wraplength=420).pack(side="left")
        # Erst sichtbar, wenn ein neueres Release da ist: holt das Update-Fenster wieder.
        self.update_button = ttk.Button(update_box, text=tr("Aktualisieren …"), style="Flat.TButton",
                                        command=self.offer_update)
        ttk.Button(footer, text=tr("Hilfe"), style="Flat.TButton",
                   command=lambda: HelpWindow.show(self.root, self.notebook.tab("current", "text"))).pack(
            side="right", padx=(8, 0))
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
        """Tagesziel in Minuten aus dem Reiter Statistik (0 bei ungültigem Feld)."""
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
            "font_scale": (self.font_scale_var, (theme.ZOOM_STEPS[0], theme.ZOOM_STEPS[-1])),
            "announce": (self.announcer.var, None),
            "contrast": (self.contrast_var, None),
        }

    def _shared_settings(self) -> dict:
        saved = self.saved_state.get("shared")
        settings = dict(saved) if isinstance(saved, dict) else {}
        for key, (var, _) in self._shared_vars().items():
            try:
                settings[key] = var.get()
            except tk.TclError:
                pass  # Feld gerade leer/ungültig: zuletzt gespeicherten Wert behalten
        settings["band"] = self.band_settings.settings()
        return settings

    def _restore_shared_settings(self) -> None:
        """Unbekannte, falsch typisierte oder außerhalb des Bereichs liegende
        Werte werden ignoriert, dann bleibt der Standardwert."""
        saved = self.saved_state.get("shared")
        if not isinstance(saved, dict):
            saved = {}
        if not self.band_settings.restore(saved.get("band")):
            self._migrate_band_settings()
        self.band_summary_var.set(self.band_settings.summary())
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

    def _migrate_band_settings(self) -> None:
        """Übernimmt Bandbedingungen aus alten Einstellungsdateien, in denen
        jeder Reiter eigene hatte (QSO und Contest je Störung, die übrigen
        eine Stufe, Gruppen, Wörter und Rufzeichen dazu eine Lautstärke).
        Die erste eingeschaltete Einstellung wird die zentrale."""
        if not any(self.band_settings.restore_panel(self._saved_mode_settings(title).get("band"))
                   for title in ("QSO", "Contest")):
            for title in ("Gruppen", "Wörter", "Rufzeichen", "Kontinuierlich", "Netzwerk"):
                preset = self._saved_mode_settings(title).get("band")
                if preset in band.PRESETS:
                    self.band_settings.set_preset(preset, notify=False)
                    break
        for title in ("Gruppen", "Wörter", "Rufzeichen"):
            data = self._saved_mode_settings(title)
            gain = data.get("band_gain")
            if data.get("band") in band.PRESETS and isinstance(gain, int) and not isinstance(gain, bool):
                spec = self.band_settings.spec()
                self.band_settings.restore({**spec, "gain": gain / 100})
                break

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

        self.awards_panel = AwardsPanel(frame, on_show=lambda seal: self._show_diplomas([seal], tr("Diplom")),
                                        station=lambda: (self.station_call(), self.station_name_var.get().strip()))
        self.lifeline_panel = LifelinePanel(frame)

        review_box = theme.card(frame, tr("Wiederholung über Tage (Lernkartei)"))
        self.review_var = tk.StringVar(value="")
        ttk.Label(review_box, textvariable=self.review_var, justify="left", wraplength=520).pack(anchor="w", pady=4)
        # Welche Zeichen in welchem Fach liegen, ein Fach je Zeile.
        self.boxes_var = tk.StringVar(value="")
        ttk.Label(review_box, textvariable=self.boxes_var, font=theme.MONO, justify="left").pack(
            anchor="w", pady=(0, 6))
        theme.hint(
            review_box, wrap=520,
            text=tr("Sicher und flüssig erkannte Zeichen kommen nach 1, 2, 4, 8, 16 und 32 Tagen wieder, "
                    "unsichere schon am nächsten Tag. Mit „schwache bevorzugt“ kommen fällige Zeichen öfter "
                    "dran. Hochgestuft wird nur aus Zufallszeichen (Zeichen und Gruppen im Reiter Einzeln, Am Stück), "
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
        """Eigenes Rufzeichen aus den Einstellungen, in Großbuchstaben (leer, wenn
        keins eingetragen ist)."""
        return self.station_call_var.get().strip().upper()

    def _follow_station(self):
        """Rufzeichen im Contest und Name im Netzwerk sind eigene Felder (ein
        Contest-Rufzeichen kann anders lauten) mit den zentralen Werten als
        Vorgabe: Sie ziehen mit, solange sie leer sind oder noch den
        vorigen zentralen Wert zeigen.

        Fehlen die zentralen Werte in den gespeicherten Einstellungen, werden
        sie aus den beiden Feldern übernommen – außer dem Platzhalter
        OLD_CONTEST_PLACEHOLDER_CALL."""
        contest = self.modes[self.mode_titles.index("Contest")].my_call_var
        network = self.modes[self.mode_titles.index("Netzwerk")].name_var
        shared = self.saved_state.get("shared")
        shared = shared if isinstance(shared, dict) else {}
        if "station_call" not in shared:
            call = contest.get().strip().upper()
            if call == OLD_CONTEST_PLACEHOLDER_CALL:
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
        statuses = awards.evaluate()  # einmal für Siegel und Übersicht
        new, seeded = awards.check(statuses=statuses)
        today = date.today()
        self.pending_seals += [(key, level, today) for key, level in new]
        self.awards_panel.refresh(awards.overview(statuses=statuses))
        self.lifeline_panel.refresh()
        return seeded

    def _check_awards_at_start(self):
        """Beim allerersten Start still nachtragen, mit einem Hinweis."""
        if self.running_mode:
            return  # nach der Übung prüft _handle_mode_stop
        seeded = self._check_awards()
        if seeded:
            messagebox.showinfo(tr("Diplome"), tr(
                "Aus deinem bisherigen Üben wurden {n} Diplome nachgetragen. Du findest sie im Reiter "
                "Statistik unter „Diplome“ und kannst sie dort ansehen und drucken.").format(n=seeded))
        else:
            self.show_pending_seals()

    def show_pending_seals(self):
        """Zeigt vorgemerkte neue Siegel im Diplom-Fenster, sobald keine Übung
        mehr läuft."""
        if self.pending_seals and not self.running_mode:
            seals, self.pending_seals = self.pending_seals, []
            self._show_diplomas(seals)

    def _show_diplomas(self, seals, title=None):
        if self.diploma_window is not None and self.diploma_window.window is not None:
            self.diploma_window.close()
        self.diploma_window = DiplomaWindow(self.root, seals, self.station_call_var, self.station_name_var,
                                            title)

    def _refresh_all_time(self, with_awards=True):
        """Reiter Statistik neu füllen; ohne `with_awards` bleiben Diplome und
        Lebenslinie für ein gleich folgendes _check_awards() liegen."""
        data = stats.load_all_time()
        self.all_time_panel.refresh(stats.all_time_summary(data), stats.all_time_char_rows(data))
        self.confusion_var.set(self._confusion_text(stats.recent_char_data()))
        review_data = review.load()
        self.review_var.set(self._review_text(review_data))
        self.boxes_var.set(self._boxes_text(review_data))
        self.progress_panel.refresh()
        if with_awards:
            self.awards_panel.refresh()
            self.lifeline_panel.refresh()

    @staticmethod
    def _review_text(data: dict, today=None) -> str:
        """Zeile der Lernkartei im Reiter Statistik: heute fällige Zeichen, sonst
        wann die nächsten kommen."""
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

    @staticmethod
    def _box_label(index: int) -> str:
        """„Fach 1 · jeden Tag“, „Fach 3 · alle 4 Tage“."""
        days = review.INTERVALS[index]
        every = tr("jeden Tag") if days == 1 else tr("alle {days} Tage").format(days=days)
        return tr("Fach {n}").format(n=index + 1) + " · " + every

    @classmethod
    def _boxes_text(cls, data: dict) -> str:
        """Die Fächer der Lernkartei mit ihren Zeichen, ein Fach je Zeile
        („–“ für ein leeres Fach); leer, solange nichts in der Kartei liegt."""
        boxes = review.by_box(data)
        if not any(boxes):
            return ""
        labels = [cls._box_label(index) for index in range(len(boxes))]
        width = max(len(label) for label in labels)
        lines = []
        for label, chars in zip(labels, boxes):
            # Volle Fächer umbrechen, damit die Zeile ins Fenster passt.
            chunks = [chars[i:i + BOX_CHARS_PER_LINE] for i in range(0, len(chars), BOX_CHARS_PER_LINE)] or [""]
            for number, chunk in enumerate(chunks):
                head = label.ljust(width) if number == 0 else " " * width
                lines.append(f"{head}  " + (" ".join(display_text(ch) for ch in chunk) or "–"))
        return "\n".join(lines)

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
            # Zweimal gedrückt: vom Zeichensatz vor dem ersten Druck ausgehen.
            charset = self.drill_restore[0]
        extended = charset.upper() + "".join(ch for ch in due if ch not in charset.upper())
        self.drill_restore = (charset, extended) if extended != charset else None
        self.charset_var.set(extended)
        review.focus = set(due)
        self.weighted_var.set(True)
        self.show_mode("Einzelzeichen")

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
        self.show_mode("Einzelzeichen")

    def _reset_all_time(self):
        """Gesamtstatistik und Lernkartei nach Rückfrage löschen; Durchgänge,
        Lektion, Diplome und Einstellungen bleiben."""
        if messagebox.askyesno(
            tr("Gesamtstatistik zurücksetzen"),
            tr("Gesamtstatistik wirklich zurücksetzen?\n\n"
               "Gelöscht werden die Statistik je Zeichen, die Lernkartei (alle Zeichen fangen "
               "wieder in Fach 1 an) und die bisherigen Verwechslungen.\n\n"
               "Erhalten bleiben die einzelnen Durchgänge, Koch-Lektion, Tagesübung, "
               "Lebenslinie, erreichte Diplome und Einstellungen.\n\n"
               "Das kann nicht rückgängig gemacht werden – vorher am besten unter "
               "„Einstellungen → Daten“ sichern."),
        ):
            stats.reset_all_time()
            self._refresh_all_time()

    def _build_notebook(self):
        """Legt die Übungs-Reiter an (mit den Extras, die jeder bestellt, siehe
        modes/__init__.py) und stellt ihre gespeicherten Einstellungen wieder
        her. Den Reiter Statistik baut danach _build_all_time_tab()."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(6, 4))
        # Mit Tab auf die Reiterleiste: „Reiter, Einzeln, Gruppen“ statt nur „Einzeln“.
        announcer.value_of(self.notebook, self._tab_name)

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
        self.tab_ids = []  # je Modus der Reiter, in dem er steht (bei „Einzeln“ derselbe)
        self.one_by_one_tab = None
        self.one_by_one_frames = {}
        saved = self.saved_state.get("one_by_one")
        self.one_by_one_var = tk.StringVar(value=saved if saved in ONE_BY_ONE else ONE_BY_ONE[0])
        for title, frame_cls in mode_classes:
            if title in ONE_BY_ONE:
                if self.one_by_one_tab is None:
                    self._build_one_by_one_tab()
                tab = self.one_by_one_frames[title] = ttk.Frame(self.one_by_one_body)
                tab_id = str(self.one_by_one_tab)
            else:
                tab = ttk.Frame(self.notebook)
                self.notebook.add(tab, text=tr(TAB_NAMES.get(title, title)))
                tab_id = str(tab)
            extra = {"vary_var": self.vary_var} if getattr(frame_cls, "uses_vary", False) else {}
            if getattr(frame_cls, "uses_band", False):
                extra["band_settings"] = self.band_settings
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
            self.tab_ids.append(tab_id)
        self._show_one_by_one()
        self.notebook.bind("<<NotebookTabChanged>>", self._announce_tab, add="+")
        # Tastatur: Strg+Tab / Strg+Umschalt+Tab blättern durch die Reiter.
        self.notebook.enable_traversal()

    def _build_one_by_one_tab(self):
        """Reiter „Einzeln“: oben die Wahl des Inhalts (Zeichen, Gruppen, Wörter,
        Rufzeichen), darunter die gewählte Übung; die anderen sind ausgeblendet."""
        tab = self.one_by_one_tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("Einzeln"))
        bar = ttk.Frame(tab, padding=(8, 6, 8, 0))
        bar.pack(fill="x")
        # „Inhalt:“ wie in Am Stück, Sprechen und Netzwerk.
        ttk.Label(bar, text=tr("Inhalt:")).pack(side="left", padx=(0, 8))
        self.one_by_one_buttons = []
        for title in ONE_BY_ONE:
            label = tr(ONE_BY_ONE_LABELS.get(title, title))
            button = ttk.Radiobutton(bar, text=label, value=title,
                                     variable=self.one_by_one_var, command=self._show_one_by_one)
            button.pack(side="left", padx=(0, 12))
            announcer.name(button, tr("Inhalt {name}").format(name=label))
            # Pfeiltasten wie in einer Optionsgruppe üblich: der Nachbar wird gewählt.
            for key, step in (("Left", -1), ("Up", -1), ("Right", 1), ("Down", 1)):
                button.bind(f"<{key}>", lambda e, d=step: self._step_content(d, focus=True) or "break")
            self.one_by_one_buttons.append(button)
        one_tab_stop(self.one_by_one_buttons, self.one_by_one_var)
        theme.hint(tab, wrap=640, text=tr(
            "Eins nach dem anderen: hören, antworten, das nächste. Ohne Pause fortlaufend mitschreiben: "
            "Reiter „Am Stück“.")).pack(anchor="w", padx=8)
        self.one_by_one_body = ttk.Frame(tab)
        self.one_by_one_body.pack(fill="both", expand=True)

    def _show_one_by_one(self):
        """Im Reiter „Einzeln“ nur die gewählte Übung zeigen."""
        current = self.one_by_one_var.get()
        for title, frame in self.one_by_one_frames.items():
            if title == current:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    def _step_content(self, step: int, focus=False) -> bool:
        """Im Reiter „Einzeln“ den nächsten (1) oder vorigen (−1) Inhalt
        wählen und ansagen; nicht während eines Durchgangs. `focus`: auch den
        Fokus auf dessen Optionsfeld setzen (Pfeiltasten)."""
        if not self.one_by_one_buttons or self.one_by_one_buttons[0].instate(["disabled"]):
            return False
        index = (ONE_BY_ONE.index(self.one_by_one_var.get()) + step) % len(ONE_BY_ONE)
        self.show_content(ONE_BY_ONE[index])
        if focus:
            self.one_by_one_buttons[index].focus_set()
            announcer.say(tr("Inhalt {name}.").format(name=tr(ONE_BY_ONE_LABELS.get(ONE_BY_ONE[index],
                                                                                   ONE_BY_ONE[index]))))
        else:
            announcer.say(tr("Reiter {name}.").format(name=self._tab_name()))
        return True

    def show_content(self, title: str) -> None:
        """Im Reiter „Einzeln“ den Inhalt `title` wählen, ohne den Reiter zu
        wechseln."""
        if title in ONE_BY_ONE:
            self.one_by_one_var.set(title)
            self._show_one_by_one()

    def show_mode(self, title: str) -> None:
        """Die Übung `title` (Schlüssel aus mode_classes) zeigen: ihren Reiter
        wählen, in „Einzeln“ auch die Übung."""
        self.show_content(title)
        self.notebook.select(self.tab_ids[self.mode_titles.index(title)])

    def _lock_tabs(self):
        # Fokus aus Eingabefeldern oben (Zeichen, WPM …) nehmen, sonst
        # landen die Antworten dort; Modi mit eigenem Feld setzen ihn danach.
        """Ein Durchgang beginnt (on_start der Reiter): andere Reiter, Knöpfe der
        Kopfleiste, Tagesübung und Probehören sperren, Übungszeit starten."""
        self.root.focus_set()
        current = self.notebook.select()
        for tab_id in self.notebook.tabs():
            if tab_id != current:
                self.notebook.tab(tab_id, state="disabled")
        for button in self.one_by_one_buttons:
            button.state(["disabled"])
        # Eigene Tonausgabe würde die des laufenden Modus abbrechen.
        self.running_mode = True
        self.band_settings.stop_preview()
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
        self._refresh_all_time(with_awards=False)
        self._check_awards()  # angezeigt erst nach dem Trennen

    def _network_session_closed(self):
        """Trainer hat seine Sitzung geschlossen: Clubabend gilt auch fürs
        Leiten; das Diplom-Fenster erst jetzt, nicht vor der Gruppe."""
        self._check_awards()
        self.show_pending_seals()

    def _preview_blocked(self):
        """Grund, warum das Probehören der Bandbedingungen gerade nicht geht."""
        if self.running_mode:
            return tr("Probehören erst nach dem Durchgang.")
        network = self.modes[self.mode_titles.index("Netzwerk")]
        if network.server is not None or network.client is not None:
            return tr("Probehören nicht während einer Netzwerk-Sitzung; dort bestimmt der Trainer die "
                      "Bedingungen.")
        return None

    def _unlock_tabs(self):
        for tab_id in self.notebook.tabs():
            self.notebook.tab(tab_id, state="normal")
        for button in self.one_by_one_buttons:
            button.state(["!disabled"])
        self.running_mode = False
        self.band_settings.stop_preview()  # Knopf wieder frei
        self.confusion_button.config(state="normal")
        self.review_button.config(state="normal")
        self.daily_bar.set_enabled(True)
        self._sync_lesson()

    def _handle_mode_stop(self):
        """Ein Durchgang ist zu Ende (on_stop der Reiter): Übungszeit buchen, in der
        Tagesübung zum nächsten Block, sonst Reiter freigeben, Statistik,
        Lektionsaufstieg und Diplome prüfen."""
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
        self._refresh_all_time(with_awards=False)
        self._check_awards()
        self._offer_next_lesson(self._active_mode())
        self._offer_groups(self._active_mode())
        self.show_pending_seals()

    def finish_daily(self):
        """Tagesübung zu Ende (DailyRunner): Reiter wieder frei."""
        self.running_mode = False
        self._unlock_tabs()
        self._refresh_all_time(with_awards=False)
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
        if self.one_by_one_tab is not None and current == str(self.one_by_one_tab):
            return self.modes[self.mode_titles.index(self.one_by_one_var.get())]
        for tab_id, mode in zip(self.tab_ids, self.modes):
            if tab_id == current:
                return mode
        return None

    def _dispatch_key(self, event):
        # Funktionstasten sind Kürzel des aktiven Reiters und gelten auch in
        # Eingabefeldern (dort haben sie sonst keine Bedeutung).
        """Jede Taste im Hauptfenster: Tagesübung (Esc, F5, Enter), Ansage (F9, F11),
        Tagesübung starten (F12), Funktionstasten an den aktiven Reiter, sonst
        an dessen on_key – außer die Taste gehört einem Eingabefeld oder dem
        Bedienelement mit dem Fokus."""
        if event.keysym in ("Escape", "F5") and self.daily.active:
            self._confirm_daily_end(event.keysym)
            return
        if event.keysym == "Return" and self.daily.card_open:
            self.daily.continue_now()
            return
        if event.keysym == ANNOUNCE_KEY:
            self.toggle_announce()
            return
        if event.keysym == STATUS_KEY:
            self.read_status()
            return
        if event.keysym == DAILY_KEY and self._start_daily():
            return
        if event.keysym in FUNCTION_KEYS:
            mode = self._active_mode()
            if mode is not None and hasattr(mode, "on_function_key"):
                mode.on_function_key(event.keysym)
            return
        # Esc beendet in jedem Übungsreiter den Durchgang, auch aus dem
        # Antwortfeld heraus (im Contest bricht es nur das Senden ab).
        if event.keysym == "Escape":
            mode = self._active_mode()
            if mode is not None:
                mode.on_key(event)
            return
        # Tastendrücke, die eigentlich für ein Eingabefeld gedacht sind (z. B.
        # das WPM-Feld beim Ändern der Geschwindigkeit, oder das Antwortfeld im
        # Gruppen-/Rufzeichen-Modus), sollen nicht zusätzlich als Morse-Antwort
        # gewertet werden.
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return
        # Mit der Tastatur auf einen Knopf, Schalter, Reiter oder eine Tabelle
        # gegangen: Leertaste, Enter und Pfeile gehören diesem Element.
        if (isinstance(event.widget, FOCUS_OWNS_KEYS)
                and event.keysym in ("space", "Return", "KP_Enter", "Up", "Down", "Left", "Right")):
            return
        mode = self._active_mode()
        if mode is not None:
            mode.on_key(event)

    def _confirm_daily_end(self, keysym: str) -> None:
        """Esc oder F5 in der Tagesübung: beendet sie erst beim zweiten Druck
        innerhalb von DAILY_END_CONFIRM_S. Ein einzelner Fehlgriff (etwa Esc,
        um ein Nebenfenster zu schließen) soll nicht den Tag kosten; ohne
        Dialog, der Ablauf und Ansage unterbräche."""
        now = time.time()
        if now - self.daily_end_pressed <= DAILY_END_CONFIRM_S:
            self.daily_end_pressed = 0.0
            self.daily_bar.show_notice("")
            self.daily.abort()
            return
        self.daily_end_pressed = now
        text = tr("Noch einmal {key} beendet die Tagesübung.").format(key="Esc" if keysym == "Escape" else keysym)
        self.daily_bar.show_notice(text)
        announcer.say(text)
        self.root.after(int(DAILY_END_CONFIRM_S * 1000), self._clear_daily_notice)

    def _clear_daily_notice(self) -> None:
        if time.time() - self.daily_end_pressed >= DAILY_END_CONFIRM_S:
            self.daily_bar.show_notice("")

    def _start_daily(self) -> bool:
        """Tagesübung starten, wenn gerade nichts läuft; True, wenn gestartet."""
        if self.running_mode or self.daily.active:
            return False
        self.daily.start()
        return True

    def check_for_update(self):
        """Beim Start im Hintergrund: Gibt es auf GitHub ein neueres
        Release? Ohne Internet (oder bei jedem anderen Fehler) bleibt es
        still – das Programm läuft ganz normal weiter."""
        result = {}

        def run():
            try:
                result["version"], result["notes"] = update.latest_release(lang=i18n.LANG)
            except update.UpdateError:
                result["version"] = None
            except Exception:
                result["version"] = None
                raise  # ins Fehlerprotokoll (threading.excepthook)
        threading.Thread(target=run, daemon=True).start()
        self._await_update_check(result)

    def _await_update_check(self, result):
        """Wartet auf das Ergebnis der Updateprüfung beim Start; bei neuerer
        Version Frage, ob geladen werden soll, sonst Hinweis und Knopf in
        der Fußzeile."""
        if "version" not in result:
            self.root.after(UPDATE_POLL_MS, lambda: self._await_update_check(result))
            return
        version = result["version"]
        self.update_checked = True
        if not update.is_newer(version, __version__):
            return
        self.update_available = (version, result.get("notes", ""))
        if self._update_recently_declined(version) or self.running_mode:
            # Kürzlich „Später“, oder es läuft gerade eine Übung: nicht dazwischenfragen.
            self._show_update_available()
            return
        self.offer_update(again=False)

    def _update_recently_declined(self, version) -> bool:
        """Hat der Nutzer diese Version vor weniger als UPDATE_ASK_AGAIN_DAYS
        Tagen mit „Später“ abgelehnt?"""
        return (version == self.update_declined and self.update_declined_on is not None
                and date.today() - self.update_declined_on < timedelta(days=UPDATE_ASK_AGAIN_DAYS))

    def _show_update_available(self) -> None:
        """Fußzeile: „Version … verfügbar“ und der Knopf „Aktualisieren …“."""
        if self.update_available is None or self.updater.busy:
            return
        self.update_var.set(tr("Version {version} verfügbar").format(version=self.update_available[0]))
        self.update_button.pack(side="left", padx=(4, 0))

    def offer_update(self, again=True) -> None:
        """Fenster „Update verfügbar“ zum neueren Release, beim Start oder
        wieder über den Knopf in der Fußzeile (`again`)."""
        if self.update_available is None:
            return
        if self.running_mode:
            # Nicht mitten im Durchgang aktualisieren.
            text = tr("Erst den Durchgang beenden, dann aktualisieren.")
            self.update_var.set(text)
            announcer.say(text)
            return
        version, notes = self.update_available
        outcome = self.updater.offer(version, tr("Version {theirs} ist erschienen, du hast {mine}.").format(
            theirs=version, mine=__version__), self.update_var.set,
            failed=lambda: self.update_button.pack(side="left", padx=(4, 0)), notes=notes, again=again)
        if outcome == DECLINED:
            self.update_declined, self.update_declined_on = version, date.today()
            self._show_update_available()
        elif outcome in (STARTED, HINT):
            self.update_button.pack_forget()  # lädt schon, oder der Link steht in der Fußzeile

    def restart_for_update(self, args):
        """Update ist installiert: wie beim Schließen alles speichern, nach
        dem Ende der Hauptschleife startet main() das neue Programm."""
        self.restart_args = list(args)
        self.on_close()

    def join_network(self, pin: str):
        """Nach dem Neustart durch ein Update (--join PIN): Reiter Netzwerk,
        wieder als Teilnehmer verbinden."""
        for title, mode in zip(self.mode_titles, self.modes):
            if hasattr(mode, "rejoin"):
                self.show_mode(title)
                mode.rejoin(pin)

    def on_close(self, keep_files=False):
        # Jeder Schritt für sich: Ein Fehler beim Speichern oder in einem
        # Reiter darf das Schließen nicht verhindern.
        # Zuerst die Tagesübung beenden: Sie stellt die gemeinsamen Einstellungen
        # zurück, bevor sie gespeichert werden.
        # keep_files: nach dem Einlesen einer Sicherung; Übungszeit und
        # Einstellungen dieses Laufs würden die eingelesenen überschreiben.
        """Programmende: Tagesübung abbrechen, Übungszeit und Einstellungen
        speichern (außer `keep_files`), alle Reiter schließen, Fenster zu."""
        saving = () if keep_files else (self._record_practice, self._save_state_or_warn)
        for step in (lambda: self.daily.abort(quiet=True), *saving,
                     *(mode.on_close for mode in self.modes), audio.release):
            try:
                step()
            except Exception:
                errorlog.record(*sys.exc_info(), version=__version__)
        self.root.destroy()

    def _save_state_or_warn(self) -> None:
        """Einstellungen speichern; geht das nicht (etwa ein schreibgeschützter
        Ordner beim Start aus dem Quelltext), es sagen statt still zu verlieren."""
        error = self._save_state()
        if error:
            messagebox.showwarning(tr("Einstellungen nicht gespeichert"),
                                   tr("Die Einstellungen ließen sich nicht speichern: {error}").format(error=error),
                                   parent=self.root)

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


def _excepthook(*exc) -> None:
    """Unerwarteter Fehler außerhalb von Tk: ins Protokoll und, wenn es eine
    Konsole gibt, auch dorthin (exe und App haben keine; dort hilft das
    Meldungsfenster von _fatal)."""
    errorlog.record(*exc, version=__version__)
    if sys.__stderr__ is not None:
        traceback.print_exception(*exc, file=sys.__stderr__)


def _fatal(text: str) -> None:
    """Der Start scheitert vor dem ersten Fenster: Meldung samt Ort des
    Fehlerprotokolls auf die Konsole, unter Windows (ohne Konsole) auch als
    Meldungsfenster – sonst verschwände das Programm wortlos."""
    message = text + "\n" + tr("Einzelheiten stehen in {path}").format(path=errorlog.LOG_FILE)
    if sys.__stderr__ is not None:
        print(message, file=sys.__stderr__)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "Morsetrainer", 0x10)
        except (AttributeError, OSError):
            pass


def main():
    """Startet das Programm: Fehlerprotokoll einrichten, Reste eines Updates
    entfernen, alte Daten übernehmen, Hauptfenster öffnen."""
    sys.excepthook = _excepthook
    update.cleanup()
    # Übungsdaten aus alten JSON-Dateien in die Datenbank übernehmen
    # (core/migration.py). Scheitert das, bleiben die Dateien liegen und es
    # gibt beim nächsten Start einen neuen Versuch; das Fehlerprotokoll meldet es.
    try:
        migration.run()
    except Exception:
        errorlog.record(*sys.exc_info(), version=__version__)
    # Feste Fensterklasse, passend zu StartupWMClass in der .desktop-Datei:
    # So ordnen Dock und Taskleiste das Fenster dem AppImage-Icon zu.
    try:
        root = tk.Tk(className="Morsetrainer")
    except tk.TclError as exc:  # kein Bildschirm, kaputtes Tk
        errorlog.record(*sys.exc_info(), version=__version__)
        _fatal(tr("Der Morsetrainer kann kein Fenster öffnen: {error}").format(error=exc))
        sys.exit(1)
    app = MorseTrainerApp(root)
    root.report_callback_exception = app.report_callback_exception
    threading.excepthook = app.thread_exception
    root.after(ERROR_POLL_MS, app._check_errors)
    if len(sys.argv) == 3 and sys.argv[1] == "--join":
        root.after(300, lambda: app.join_network(sys.argv[2]))
    else:
        root.after(UPDATE_CHECK_DELAY_MS, app.check_for_update)
        root.after(WHATS_NEW_DELAY_MS, app.show_whats_new)
    root.mainloop()
    found = update.installed()
    if app.restart_args is not None and found is not None:
        update.relaunch(found[0], app.restart_args)
    elif app.restart_command is not None:
        update.relaunch(Path(app.restart_command[0]), app.restart_command[1:])


if __name__ == "__main__":
    main()