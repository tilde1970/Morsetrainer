"""Morsetrainer von DL4YM.

Trainingsmodi über Tabs (Einzelzeichen, Gruppen, Wörter, Rufzeichen,
Kontinuierlich, QSO-Hörtraining, aktiver Contest-Betrieb) plus Statistik, mit
gemeinsamen Einstellungen für Zeichensatz (frei oder als Koch-Lektion),
Geschwindigkeit und Tonhöhe."""
import re
import time
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

from morsetrainer import DATA_DIR
from morsetrainer.core import audio, koch, practice, stats, storage
from morsetrainer.core.morse import build_text
from morsetrainer.modes.callsign_mode import CallsignModeFrame
from morsetrainer.modes.continuous_mode import ContinuousModeFrame
from morsetrainer.modes.group_mode import GroupModeFrame
from morsetrainer.modes.qso_mode import QsoModeFrame
from morsetrainer.modes.run_mode import RunModeFrame
from morsetrainer.modes.single_mode import SingleModeFrame
from morsetrainer.modes.word_mode import WordModeFrame
from morsetrainer.widgets.progress_widget import ProgressPanel
from morsetrainer.widgets.stats_widget import StatsPanel
from morsetrainer.widgets.ui_widgets import ScrollableFrame

__author__ = "DL4YM"
__version__ = "2.1"

# Wer neu anfängt, beginnt mit Koch-Lektion 1.
DEFAULT_CHARSET = koch.lesson_charset(1)
DEFAULT_GEOMETRY = "580x980"
WINDOW_STATE_FILE = DATA_DIR / "window_state.json"
FUNCTION_KEYS = {f"F{i}" for i in range(1, 13)}
# So viele Verwechslungspaare (die häufigsten) übt "Diese Verwechslungen üben".
CONFUSION_PAIRS = 4
# Übungszeit in der Fußzeile während eines Durchgangs so oft auffrischen.
PRACTICE_TICK_MS = 15000


class MorseTrainerApp:
    def __init__(self, root):
        self.root = root
        self.running_mode = False
        root.title(f"Morsetrainer von {__author__}")
        self.saved_state = self._load_state()
        root.geometry(self._initial_geometry())
        root.resizable(True, True)

        self._build_settings()
        self._restore_shared_settings()
        self._build_footer()
        self._build_notebook()
        self._build_all_time_tab()
        self._refresh_all_time()

        root.bind("<Key>", self._dispatch_key)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _load_state(self) -> dict:
        """window_state.json: Fenstergröße, gemeinsame Einstellungen und die
        Einstellungen der Reiter, die welche speichern (siehe _mode_settings)."""
        return storage.load_json(WINDOW_STATE_FILE, {})

    def _initial_geometry(self) -> str:
        geometry = self.saved_state.get("geometry")
        if isinstance(geometry, str) and self._geometry_fits_screen(geometry):
            return geometry
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
        }
        try:
            storage.write_json_atomic(WINDOW_STATE_FILE, state, indent=2)
        except OSError:
            pass

    def _build_settings(self):
        pad = {"padx": 8, "pady": 4}
        settings = ttk.LabelFrame(self.root, text="Einstellungen (gemeinsam)")
        settings.pack(fill="x", **pad)

        ttk.Label(settings, text="Zeichen:").grid(row=0, column=0, sticky="w", **pad)
        self.charset_var = tk.StringVar(value=DEFAULT_CHARSET)
        ttk.Entry(settings, textvariable=self.charset_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky="we", **pad
        )

        self._build_koch_row(settings, row=1)

        ttk.Label(settings, text="Geschwindigkeit (WPM):").grid(row=2, column=0, sticky="w", **pad)
        self.wpm_var = tk.IntVar(value=15)
        ttk.Spinbox(settings, from_=5, to=40, textvariable=self.wpm_var, width=6).grid(
            row=2, column=1, sticky="w", **pad
        )

        ttk.Label(settings, text="Tonhöhe (Hz):").grid(row=2, column=2, sticky="w", **pad)
        self.freq_var = tk.IntVar(value=600)
        ttk.Spinbox(settings, from_=300, to=1000, increment=50, textvariable=self.freq_var, width=6).grid(
            row=2, column=3, sticky="w", **pad
        )

        farnsworth = ttk.Frame(settings)
        farnsworth.grid(row=3, column=0, columnspan=4, sticky="w", **pad)
        self.farnsworth_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(farnsworth, text="Farnsworth, effektiv", variable=self.farnsworth_enabled_var).pack(
            side="left"
        )
        self.farnsworth_wpm_var = tk.IntVar(value=10)
        ttk.Spinbox(farnsworth, from_=3, to=39, textvariable=self.farnsworth_wpm_var, width=4).pack(
            side="left", padx=(4, 4)
        )
        ttk.Label(farnsworth, text="WPM (alle außer Einzelzeichen)").pack(side="left")

        self.weighted_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings, text="Schwache Zeichen bevorzugen (gilt ab nächstem Start)",
            variable=self.weighted_var,
        ).grid(row=4, column=0, columnspan=4, sticky="w", **pad)

        self.vary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            settings, text="Tonhöhe und Tempo leicht variieren (gegen Gewöhnung an einen Klang)",
            variable=self.vary_var,
        ).grid(row=5, column=0, columnspan=4, sticky="w", **pad)

        # Einstellbar im Reiter Statistik, angezeigt in der Fußzeile.
        self.daily_goal_var = tk.IntVar(value=15)

    def _build_koch_row(self, settings, row):
        """Koch-Lektion: setzt den Zeichensatz auf die ersten Zeichen der
        Koch-Reihenfolge. Das Feld "Zeichen" bleibt frei editierbar; passt
        es zu keiner Lektion, steht dort "eigener Zeichensatz"."""
        pad = {"padx": 8, "pady": 4}
        ttk.Label(settings, text="Koch-Lektion:").grid(row=row, column=0, sticky="w", **pad)
        frame = ttk.Frame(settings)
        frame.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self.lesson_var = tk.IntVar(value=1)
        spinbox = ttk.Spinbox(
            frame, from_=1, to=koch.MAX_LESSON, textvariable=self.lesson_var, width=4, command=self._apply_lesson
        )
        spinbox.pack(side="left")
        spinbox.bind("<Return>", lambda e: self._apply_lesson())
        self.lesson_info_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.lesson_info_var).pack(side="left", padx=(8, 4))
        # Spielt das neue Zeichen vor; bei eigenem Zeichensatz (z. B. nach
        # "Verwechslungen üben") führt er zurück zur Lektion.
        self.new_char_button = ttk.Button(frame, text="▶ anhören", width=12, command=self._lesson_button)
        self.new_char_button.pack(side="left")
        ttk.Button(
            frame, text=f"Koch-Tempo {koch.RECOMMENDED_WPM}/{koch.RECOMMENDED_EFFECTIVE_WPM}",
            command=self._set_koch_tempo,
        ).pack(side="left", padx=(8, 0))
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
            self.lesson_info_var.set("(eigene Zeichen)")
            try:
                back = self.lesson_var.get()
            except tk.TclError:
                back = 1
            self.new_char_button.config(text=f"↩ Lektion {back}")
        else:
            self.lesson_var.set(lesson)
            self.lesson_info_var.set(f"neu: {koch.newest_char(lesson)}")
            self.new_char_button.config(text="▶ anhören")
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
        try:
            wpm, freq = self.wpm_var.get(), self.freq_var.get()
        except tk.TclError:
            wpm, freq = koch.RECOMMENDED_WPM, 600
        try:
            audio.play(build_text(f"{ch} {ch} {ch}", wpm, freq, self.farnsworth_wpm()))
        except audio.AudioError as exc:
            messagebox.showwarning("Tonausgabe", str(exc))

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
        if messagebox.askyesno(
            "Nächste Koch-Lektion",
            f"Lektion {lesson} geschafft: {correct} von {total} Zeichen richtig "
            f"({correct / total:.0%}).\n\n"
            f"Mit Lektion {lesson + 1} weitermachen? Neu dazu kommt „{new_char}“.",
        ):
            self.charset_var.set(koch.lesson_charset(lesson + 1))
            self._play_new_char()

    def _build_footer(self):
        # Vor dem Notebook gepackt, damit es bei kleinem Fenster nicht verdrängt wird.
        footer = ttk.Frame(self.root)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 4))
        self.practice_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.practice_var, font=("Sans", 9)).pack(side="left")
        ttk.Label(
            footer, text=f"Morsetrainer {__version__} · entwickelt von {__author__} · 73!",
            foreground="gray45", font=("Sans", 8),
        ).pack(side="right")
        self.practice_started = None  # time.time() beim Start eines Durchgangs
        self.practice_tick_id = None
        self.daily_goal_var.trace_add("write", lambda *_: self._update_practice())
        self._update_practice()

    def _update_practice(self):
        """Fußzeile: heutige Übungszeit, Tagesziel und Serie. Ein laufender
        Durchgang zählt schon mit."""
        data = practice.load()
        today = date.today()
        if self.practice_started is not None:
            data[today.isoformat()] = practice.seconds_on(data, today) + time.time() - self.practice_started
        minutes = int(practice.seconds_on(data, today) // 60)
        try:
            goal = max(self.daily_goal_var.get(), 0)
        except tk.TclError:
            goal = 0
        if goal:
            text = f"Heute {minutes} von {goal} Min"
            if minutes >= goal:
                text += " ✓"
        else:
            text = f"Heute {minutes} Min"
        days = practice.streak(data, goal * 60, today)
        if days:
            text += f" · {days} {'Tag' if days == 1 else 'Tage'} in Folge"
        self.practice_var.set(text)

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

    def _build_all_time_tab(self):
        """Eigener Reiter hinter den Trainingsmodi; ist kein Modus, Tasten
        werden dort nicht ausgewertet (siehe _active_mode)."""
        pad = {"padx": 8, "pady": 4}
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Statistik")
        frame = ScrollableFrame(tab).inner
        self.all_time_panel = StatsPanel(
            frame, title="Gesamtstatistik (alle Durchgänge)", tree_height=12, show_save_label=False
        )

        goal = ttk.Frame(frame)
        goal.pack(fill="x", **pad)
        ttk.Label(goal, text="Tagesziel:").pack(side="left")
        ttk.Spinbox(goal, from_=0, to=240, increment=5, textvariable=self.daily_goal_var, width=5).pack(
            side="left", padx=4
        )
        ttk.Label(goal, text="Min. pro Tag (0 = ohne Ziel) – lieber täglich kurz als selten lang",
                  foreground="gray40").pack(side="left")

        confusion_box = ttk.LabelFrame(frame, text="Häufigste Verwechslungen")
        confusion_box.pack(fill="x", **pad)
        self.confusion_var = tk.StringVar(value="")
        ttk.Label(confusion_box, textvariable=self.confusion_var, font=("Consolas", 11), justify="left").pack(
            anchor="w", **pad
        )
        ttk.Label(
            confusion_box, wraplength=440, justify="left", foreground="gray40",
            text="Gesendet → getippt. Paare, die in beide Richtungen auftauchen (↔), sind "
                 "typische Klangverwandte – am besten gezielt zusammen üben, z. B. nur diese "
                 "Zeichen im Zeichensatz oben.",
        ).pack(anchor="w", padx=8, pady=(0, 6))
        self.confusion_button = ttk.Button(
            confusion_box, text=f"Die {CONFUSION_PAIRS} häufigsten gezielt üben", command=self._drill_confusions
        )
        self.confusion_button.pack(anchor="w", padx=8, pady=(0, 8))
        self.progress_panel = ProgressPanel(frame)

        ttk.Button(frame, text="Gesamtstatistik zurücksetzen", command=self._reset_all_time).pack(
            side="bottom", anchor="w", **pad
        )

    def _refresh_all_time(self):
        data = stats.load_all_time()
        self.all_time_panel.refresh(stats.all_time_summary(data), stats.all_time_char_rows(data))
        self.confusion_var.set(self._confusion_text(data))
        self.progress_panel.refresh()

    @staticmethod
    def _confusion_text(data: dict) -> str:
        pairs = stats.top_confusions(data)
        if not pairs:
            return "Noch keine Verwechslungen erfasst\n(werden ab jetzt mitgezählt)."
        seen = {(sent, typed) for sent, typed, _, _ in pairs}
        lines = []
        for sent, typed, count, share in pairs:
            arrow = "↔" if (typed, sent) in seen else "→"
            lines.append(f"{sent} {arrow} {typed}   {count:>3}×   ({share:.0%} der {sent})")
        return "\n".join(lines)

    @staticmethod
    def _confusion_charset(data: dict) -> str:
        """Zeichen der häufigsten Verwechslungspaare, in Reihenfolge."""
        chars = []
        for sent, typed, _, _ in stats.top_confusions(data, limit=CONFUSION_PAIRS):
            for ch in (sent, typed):
                if ch not in chars:
                    chars.append(ch)
        return "".join(chars)

    def _drill_confusions(self):
        """Setzt den Zeichensatz auf die verwechselten Zeichen und wechselt zu
        den Einzelzeichen: ähnlich klingende Zeichen direkt gegeneinander."""
        chars = self._confusion_charset(stats.load_all_time())
        if len(chars) < 2:
            self.confusion_var.set("Noch zu wenige Verwechslungen zum gezielten Üben.")
            return
        self.charset_var.set(chars)
        self.notebook.select(self.tab_ids[self.mode_titles.index("Einzelzeichen")])

    def _reset_all_time(self):
        if messagebox.askyesno(
            "Gesamtstatistik zurücksetzen",
            "Die komplette Gesamtstatistik (alle bisherigen Durchgänge) wirklich löschen?\n"
            "Das kann nicht rückgängig gemacht werden. Die einzelnen Sitzungs-Logdateien "
            "in stats/ bleiben davon unberührt.",
        ):
            stats.reset_all_time()
            self._refresh_all_time()

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=4)

        mode_classes = [
            ("Einzelzeichen", SingleModeFrame),
            ("Gruppen", GroupModeFrame),
            ("Wörter", WordModeFrame),
            ("Rufzeichen", CallsignModeFrame),
            ("Kontinuierlich", ContinuousModeFrame),
            ("QSO", QsoModeFrame),
            ("Contest", RunModeFrame),
        ]

        self.modes = []
        self.mode_titles = []
        self.tab_ids = []
        for title, frame_cls in mode_classes:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)
            extra = {"vary_var": self.vary_var} if getattr(frame_cls, "uses_vary", False) else {}
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
        current = self.notebook.select()
        for tab_id in self.notebook.tabs():
            if tab_id != current:
                self.notebook.tab(tab_id, state="disabled")
        # Eigene Tonausgabe würde die des laufenden Modus abbrechen.
        self.running_mode = True
        self.new_char_button.config(state="disabled")
        self.confusion_button.config(state="disabled")
        if self.practice_started is None:
            self.practice_started = time.time()
            self.practice_tick_id = self.root.after(PRACTICE_TICK_MS, self._practice_tick)

    def _unlock_tabs(self):
        for tab_id in self.notebook.tabs():
            self.notebook.tab(tab_id, state="normal")
        self.running_mode = False
        self.confusion_button.config(state="normal")
        self._sync_lesson()

    def _handle_mode_stop(self):
        self._record_practice()
        self._update_practice()
        self._unlock_tabs()
        self._refresh_all_time()
        self._offer_next_lesson(self._active_mode())

    def _active_mode(self):
        current = self.notebook.select()
        for tab_id, mode in zip(self.tab_ids, self.modes):
            if tab_id == current:
                return mode
        return None

    def _dispatch_key(self, event):
        # Funktionstasten sind Kürzel des aktiven Reiters und gelten auch in
        # Eingabefeldern (dort haben sie sonst keine Bedeutung).
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

    def on_close(self):
        self._record_practice()
        self._save_state()
        for mode in self.modes:
            mode.on_close()
        self.root.destroy()


def main():
    root = tk.Tk()
    MorseTrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()