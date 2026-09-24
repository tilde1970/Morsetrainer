"""Morsetrainer: Trainingsmodi (Einzelzeichen, Gruppen, Rufzeichen, Kontinuierlich, QSO)
über Tabs, mit gemeinsamen Einstellungen für Zeichensatz, Geschwindigkeit
und Tonhöhe."""
import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import stats
from callsign_mode import CallsignModeFrame
from continuous_mode import ContinuousModeFrame
from group_mode import GroupModeFrame
from qso_mode import QsoModeFrame
from single_mode import SingleModeFrame
from stats_widget import StatsPanel

# Kompletter Koch-Zeichensatz in LCWO-Reihenfolge (lcwo.net).
DEFAULT_CHARSET = "KMURESNAPTLWI.JZ=FOY,VG5/Q92H38B?47C1D60X"
DEFAULT_GEOMETRY = "520x980"
WINDOW_STATE_FILE = Path(__file__).parent / "window_state.json"
FUNCTION_KEYS = {f"F{i}" for i in range(1, 13)}


class MorseTrainerApp:
    def __init__(self, root):
        self.root = root
        root.title("Morsetrainer")
        self.saved_state = self._load_state()
        root.geometry(self._initial_geometry())
        root.resizable(True, True)

        self._build_settings()
        self._restore_shared_settings()
        self._build_notebook()
        self._build_all_time_tab()
        self._refresh_all_time()

        root.bind("<Key>", self._dispatch_key)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _load_state(self) -> dict:
        """window_state.json: Fenstergröße, gemeinsame Einstellungen und die
        Einstellungen der Reiter, die welche speichern (siehe _mode_settings)."""
        try:
            data = json.loads(WINDOW_STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

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
            WINDOW_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
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

        ttk.Label(settings, text="Geschwindigkeit (WPM):").grid(row=1, column=0, sticky="w", **pad)
        self.wpm_var = tk.IntVar(value=15)
        ttk.Spinbox(settings, from_=5, to=40, textvariable=self.wpm_var, width=6).grid(
            row=1, column=1, sticky="w", **pad
        )

        ttk.Label(settings, text="Tonhöhe (Hz):").grid(row=1, column=2, sticky="w", **pad)
        self.freq_var = tk.IntVar(value=600)
        ttk.Spinbox(settings, from_=300, to=1000, increment=50, textvariable=self.freq_var, width=6).grid(
            row=1, column=3, sticky="w", **pad
        )

        farnsworth = ttk.Frame(settings)
        farnsworth.grid(row=2, column=0, columnspan=4, sticky="w", **pad)
        self.farnsworth_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(farnsworth, text="Farnsworth, effektiv", variable=self.farnsworth_enabled_var).pack(
            side="left"
        )
        self.farnsworth_wpm_var = tk.IntVar(value=10)
        ttk.Spinbox(farnsworth, from_=3, to=39, textvariable=self.farnsworth_wpm_var, width=4).pack(
            side="left", padx=(4, 4)
        )
        ttk.Label(farnsworth, text="WPM (Gruppen, Rufzeichen, Kontinuierlich, QSO)").pack(side="left")

        self.weighted_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings, text="Schwache Zeichen bevorzugen (gilt ab nächstem Start)",
            variable=self.weighted_var,
        ).grid(row=3, column=0, columnspan=4, sticky="w", **pad)

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
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Gesamtstatistik")
        self.all_time_panel = StatsPanel(
            frame, title="Gesamtstatistik (alle Durchgänge)", tree_height=20, show_save_label=False
        )
        ttk.Button(frame, text="Gesamtstatistik zurücksetzen", command=self._reset_all_time).pack(
            anchor="w", **pad
        )

    def _refresh_all_time(self):
        data = stats.load_all_time()
        self.all_time_panel.refresh(stats.all_time_summary(data), stats.all_time_char_rows(data))

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
            ("Rufzeichen", CallsignModeFrame),
            ("Kontinuierlich", ContinuousModeFrame),
            ("QSO", QsoModeFrame),
        ]

        self.modes = []
        self.mode_titles = []
        self.tab_ids = []
        for title, frame_cls in mode_classes:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)
            mode = frame_cls(
                tab, self.charset_var, self.wpm_var, self.freq_var, self.weighted_var, self.farnsworth_wpm,
                on_start=self._lock_tabs, on_stop=self._handle_mode_stop,
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

    def _unlock_tabs(self):
        for tab_id in self.notebook.tabs():
            self.notebook.tab(tab_id, state="normal")

    def _handle_mode_stop(self):
        self._unlock_tabs()
        self._refresh_all_time()

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