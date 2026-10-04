"""Bandbedingungen an einer Stelle: welche Störungen wie stark und wie laut
die Störgeräusche insgesamt sind. Eingestellt in einem eigenen Fenster
(erreichbar über „Weitere Optionen“ und jeden Reiter), die Reiter schalten
sie nur an oder aus (BandToggle). Änderungen wirken sofort, auch in einem
laufenden Durchgang."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import band
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import theme

# Störungen (Schlüssel aus band.EFFECTS, Beschriftung, Startwert in %).
BAND_OPTIONS = (
    ("noise", N_("Rauschen"), 40),
    ("qrn", N_("Knackstörungen (QRN)"), 50),
    ("qsb", N_("QSB (Fading)"), 50),
    ("chirp", N_("Chirp"), 50),
    ("ssb", N_("SSB-Gebrabbel"), 40),
    ("cw_qrm", N_("CW-QRM (Nachbar-Run)"), 35),
)
SHORT_NAMES = {"noise": N_("Rauschen"), "qrn": "QRN", "qsb": "QSB", "chirp": N_("Chirp"),
               "ssb": "SSB", "cw_qrm": "CW-QRM"}
PRESET_NAMES = {"light": N_("leicht"), "medium": N_("mittel"), "heavy": N_("stark")}
# Startwerte, solange nichts gespeichert ist.
DEFAULT_PRESET = "medium"
# Lautstärke der Störgeräusche gegenüber den Zeichen, in Prozent.
GAIN_RANGE = (round(band.GAIN_RANGE[0] * 100), round(band.GAIN_RANGE[1] * 100))


def toggle_value(value):
    """An/aus aus einer gespeicherten Reiter-Einstellung, auch aus älteren
    Versionen (Stufe als Text, Schalter je Störung als dict); None, wenn
    der Wert nichts aussagt. None selbst heißt aus (Tagesübung)."""
    if value is None or isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        return value in band.PRESETS
    if isinstance(value, dict):
        return any(isinstance(v, dict) and v.get("enabled") is True for v in value.values())
    return None


class BandSettings:
    """Hält die Einstellung als Tk-Variablen; spec() liefert sie als
    band-Spec. Reiter melden sich mit subscribe() für Änderungen an."""

    def __init__(self, root):
        self.root = root
        self.controls = {}  # Schlüssel -> (an/aus, Pegel in %)
        for key, _, default in BAND_OPTIONS:
            self.controls[key] = (tk.BooleanVar(value=False), tk.DoubleVar(value=default))
        self.gain_var = tk.DoubleVar(value=100)
        self.listeners = []
        self.window = None
        self.set_preset(DEFAULT_PRESET, notify=False)

    # --- Werte -----------------------------------------------------------
    def spec(self) -> dict:
        return {
            "levels": {key: round(level.get()) / 100 for key, (on, level) in self.controls.items() if on.get()},
            "gain": round(self.gain_var.get()) / 100,
        }

    def set_spec(self, spec, notify=True) -> None:
        for key, (on, level) in self.controls.items():
            on.set(key in spec["levels"])
            if key in spec["levels"]:
                level.set(round(spec["levels"][key] * 100))
        self.gain_var.set(round(spec["gain"] * 100))
        if notify:
            self._changed()

    def set_preset(self, preset: str, notify=True) -> None:
        """Stufe übernehmen; die Lautstärke bleibt."""
        spec = band.spec_from_preset(preset)
        spec["gain"] = round(self.gain_var.get()) / 100
        self.set_spec(spec, notify)

    def settings(self) -> dict:
        """Zum Speichern (window_state.json, Abschnitt shared)."""
        return self.spec()

    def restore(self, data) -> bool:
        """Gegenstück zu settings(); False, wenn nichts Brauchbares dabei war."""
        spec = band.clean_spec(data)
        if spec is None:
            return False
        self.set_spec(spec, notify=False)
        return True

    def restore_panel(self, data) -> bool:
        """Übernimmt die frühere Einstellung des QSO- oder Contest-Reiters
        ({Störung: {"enabled", "level"}}), wenn dort etwas an war."""
        if toggle_value(data) is not True:
            return False
        levels = {}
        for key, values in data.items():
            if key in self.controls and isinstance(values, dict) and values.get("enabled") is True:
                level = values.get("level")
                if isinstance(level, (int, float)) and not isinstance(level, bool):
                    levels[key] = min(max(float(level), 0.0), 100.0) / 100
        return self.restore({"levels": levels, "gain": round(self.gain_var.get()) / 100})

    def summary(self) -> str:
        """Kurzfassung für die Reiter, z. B. „Rauschen 40 %, QRN 30 % ·
        Lautstärke 100 % · Stufe mittel“."""
        spec = self.spec()
        parts = [f"{tr(SHORT_NAMES[key])} {round(level * 100)} %" for key, level in spec["levels"].items()]
        text = ", ".join(parts) if parts else tr("keine Störung eingeschaltet")
        text += " · " + tr("Lautstärke {gain} %").format(gain=round(spec["gain"] * 100))
        rank = band.preset_rank(spec)
        if rank:
            text += " · " + tr("Stufe {name}").format(name=tr(PRESET_NAMES[rank]))
        return text

    def subscribe(self, callback) -> None:
        self.listeners.append(callback)

    def _changed(self) -> None:
        self._update_window()
        for callback in self.listeners:
            callback()

    # --- Fenster ---------------------------------------------------------
    def open_window(self) -> None:
        if self.window is not None:
            self.window.deiconify()
            self.window.lift()
            return
        window = self.window = tk.Toplevel(self.root)
        window.title(tr("Bandbedingungen"))
        window.configure(background=theme.BG)
        window.resizable(True, False)
        window.protocol("WM_DELETE_WINDOW", self.close_window)
        window.bind("<Escape>", lambda e: self.close_window())
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        theme.hint(frame, wrap=460, text=tr(
            "Gilt für alle Reiter; dort schaltest du die Bandbedingungen nur an oder aus. Änderungen wirken "
            "sofort, auch im laufenden Durchgang.")).pack(anchor="w", pady=(0, 6))

        presets = ttk.Frame(frame)
        presets.pack(fill="x", pady=(0, 4))
        ttk.Label(presets, text=tr("Stufe:")).pack(side="left", padx=(0, 6))
        for preset, name in PRESET_NAMES.items():
            ttk.Button(presets, text=tr(name), command=lambda p=preset: self.set_preset(p)).pack(side="left", padx=2)

        box = theme.card(frame, tr("Störungen"), padx=0)
        box.columnconfigure(1, weight=1)
        self.widgets = {}
        for row, (key, label, _) in enumerate(BAND_OPTIONS):
            on, level = self.controls[key]
            ttk.Checkbutton(box, text=tr(label), variable=on, command=self._changed).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=1)
            scale = ttk.Scale(box, from_=0, to=100, variable=level, length=200, command=lambda _: self._changed())
            scale.grid(row=row, column=1, sticky="we", pady=1)
            shown = ttk.Label(box, width=5, anchor="e")
            shown.grid(row=row, column=2, padx=(6, 0))
            self.widgets[key] = (scale, shown)
        buttons = ttk.Frame(box)
        buttons.grid(row=len(BAND_OPTIONS), column=0, columnspan=3, sticky="e", pady=(6, 0))
        ttk.Button(buttons, text=tr("Alle aus"), command=lambda: self._set_all(False)).pack(side="right")
        ttk.Button(buttons, text=tr("Alle an"), command=lambda: self._set_all(True)).pack(side="right", padx=4)

        gain = theme.card(frame, tr("Lautstärke der Störgeräusche"), padx=0)
        row = ttk.Frame(gain)
        row.pack(fill="x")
        theme.hint(row, text=tr("leiser")).pack(side="left")
        ttk.Scale(row, from_=GAIN_RANGE[0], to=GAIN_RANGE[1], variable=self.gain_var, length=220,
                  command=lambda _: self._changed()).pack(side="left", fill="x", expand=True, padx=6)
        theme.hint(row, text=tr("lauter")).pack(side="left")
        self.gain_shown = ttk.Label(row, width=6, anchor="e")
        self.gain_shown.pack(side="left", padx=(6, 0))
        theme.hint(gain, wrap=440, text=tr(
            "Gegenüber den Zeichen; 100 % ist die normale Mischung. Für das Diplom QRN-fest zählt mindestens "
            "100 % und mindestens die Stufe.")).pack(anchor="w", pady=(4, 0))

        self.rank_var = tk.StringVar(value="")
        theme.hint(frame, textvariable=self.rank_var).pack(anchor="w", pady=(4, 0))
        ttk.Button(frame, text=tr("Schließen"), command=self.close_window).pack(anchor="e", pady=(8, 0))
        self._update_window()

    def close_window(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None

    def _set_all(self, enabled: bool) -> None:
        for on, _ in self.controls.values():
            on.set(enabled)
        self._changed()

    def _update_window(self) -> None:
        if self.window is None:
            return
        for key, (scale, shown) in self.widgets.items():
            on, level = self.controls[key]
            scale.state(["!disabled"] if on.get() else ["disabled"])
            shown.config(text=f"{round(level.get())} %", foreground="" if on.get() else theme.DISABLED)
        self.gain_shown.config(text=f"{round(self.gain_var.get())} %")
        rank = band.preset_rank(self.spec())
        self.rank_var.set(tr("Entspricht mindestens Stufe {name}.").format(name=tr(PRESET_NAMES[rank])) if rank
                          else tr("Schwächer als Stufe leicht."))


class BandToggle:
    """Zeile für einen Reiter: Schalter „Bandbedingungen“, Kurzfassung der
    zentralen Einstellung und Knopf zum Einstellen. `variable` ist die
    BooleanVar des Reiters; `on_change` (optional) wird bei jeder Änderung
    von Schalter oder zentraler Einstellung aufgerufen."""

    def __init__(self, parent, settings: BandSettings, variable, on_change=None, **pack):
        self.settings = settings
        self.variable = variable
        self.on_change = on_change
        self.frame = ttk.Frame(parent)
        self.frame.pack(**({"fill": "x", "pady": 1} | pack))
        top = ttk.Frame(self.frame)
        top.pack(fill="x")
        ttk.Checkbutton(top, text=tr("Bandbedingungen"), variable=variable).pack(side="left")
        ttk.Button(top, text=tr("Einstellen …"), style="Flat.TButton",
                   command=settings.open_window).pack(side="left", padx=(6, 0))
        self.summary_var = tk.StringVar(value="")
        self.summary = theme.hint(self.frame, textvariable=self.summary_var, wrap=520)
        self.summary.pack(anchor="w", padx=(22, 0))
        variable.trace_add("write", lambda *_: self._changed())
        settings.subscribe(self._changed)
        self._show()

    def _show(self) -> None:
        self.summary_var.set(self.settings.summary())
        self.summary.config(foreground="" if self.variable.get() else theme.DISABLED)

    def _changed(self) -> None:
        self._show()
        if self.on_change is not None:
            self.on_change()
