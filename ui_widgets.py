"""Wiederverwendbare Tk-Bausteine: scrollbarer Bereich und das Panel für die
Bandbedingungen (genutzt vom QSO- und vom Contest-Reiter)."""
import tkinter as tk
from tkinter import ttk

# Bandbedingungen (Schlüssel aus band.EFFECTS, Beschriftung, Startwert in %).
BAND_OPTIONS = (
    ("noise", "Rauschen", 40),
    ("qrn", "Knackstörungen (QRN)", 50),
    ("qsb", "QSB (Fading)", 50),
    ("chirp", "Chirp", 50),
    ("ssb", "SSB-Gebrabbel", 40),
    ("cw_qrm", "CW-QRM (Nachbar-Run)", 35),
)


class ScrollableFrame:
    """Frame mit senkrechter Scrollleiste, falls der Inhalt (z. B. ein
    langes Contest-Log samt Klartext) nicht ins Fenster passt."""

    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.canvas.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _bind_wheel(self, active: bool):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if active:
                self.canvas.bind_all(sequence, self._on_wheel)
            else:
                self.canvas.unbind_all(sequence)

    def _on_wheel(self, event):
        # Textfelder und Tabellen scrollen selbst.
        if isinstance(event.widget, (tk.Text, ttk.Treeview)):
            return
        if self.canvas.yview() == (0.0, 1.0):
            return
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")


class BandSettingsPanel:
    """Je Störung: Schalter, Regler (0–100 %) und Anzeige des Werts. Der
    Regler ist nur aktiv, wenn die Störung eingeschaltet ist. `on_change`
    wird bei jeder Änderung aufgerufen; der Aufrufer überträgt die Werte
    dann mit apply_to() auf seine BandConditions."""

    def __init__(self, parent, on_change):
        self.on_change = on_change
        box = ttk.LabelFrame(parent, text="Bandbedingungen")
        box.pack(fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        self.controls = {}  # Schlüssel -> (an/aus, Pegel, Regler, Anzeigetext, Anzeige)
        for row, (key, label, default) in enumerate(BAND_OPTIONS):
            enabled = tk.BooleanVar(value=False)
            level = tk.DoubleVar(value=default)
            shown = tk.StringVar(value=f"{default} %")
            ttk.Checkbutton(box, text=label, variable=enabled, command=self._changed).grid(
                row=row, column=0, sticky="w", padx=(8, 12), pady=1
            )
            scale = ttk.Scale(box, from_=0, to=100, variable=level,
                              command=lambda _, key=key: self._on_level(key))
            scale.grid(row=row, column=1, sticky="we", pady=1)
            value_label = ttk.Label(box, textvariable=shown, width=5, anchor="e")
            value_label.grid(row=row, column=2, padx=(4, 8))
            self.controls[key] = (enabled, level, scale, shown, value_label)
        buttons = ttk.Frame(box)
        buttons.grid(row=len(BAND_OPTIONS), column=0, columnspan=3, sticky="e", padx=8, pady=(2, 6))
        ttk.Button(buttons, text="Alle aus", command=lambda: self.set_all(False)).pack(side="right")
        ttk.Button(buttons, text="Alle an", command=lambda: self.set_all(True)).pack(side="right", padx=4)
        self._update_widgets()

    def _on_level(self, key):
        _, level, _, shown, _ = self.controls[key]
        shown.set(f"{round(level.get())} %")
        self._changed()

    def _changed(self):
        self._update_widgets()
        self.on_change()

    def _update_widgets(self):
        for enabled, _, scale, _, value_label in self.controls.values():
            scale.state(["!disabled"] if enabled.get() else ["disabled"])
            value_label.config(foreground="" if enabled.get() else "gray55")

    def set_all(self, enabled: bool):
        for var, *_ in self.controls.values():
            var.set(enabled)
        self._changed()

    def apply_to(self, band) -> None:
        """Überträgt Schalter und Pegel auf BandConditions (oder nichts, wenn
        None). Auch während der Wiedergabe: der Audio-Thread liest nur die
        einfachen Werte."""
        if band is None:
            return
        for key, (enabled, level, *_) in self.controls.items():
            band.enabled[key] = enabled.get()
            band.levels[key] = level.get() / 100

    def settings(self) -> dict:
        return {
            key: {"enabled": enabled.get(), "level": round(level.get())}
            for key, (enabled, level, *_) in self.controls.items()
        }

    def restore(self, data) -> None:
        """Gegenstück zu settings(); unbekannte oder kaputte Werte werden
        ignoriert."""
        if not isinstance(data, dict):
            return
        for key, values in data.items():
            if key not in self.controls or not isinstance(values, dict):
                continue
            enabled, level, _, shown, _ = self.controls[key]
            enabled.set(bool(values.get("enabled", False)))
            try:
                value = min(max(float(values.get("level", level.get())), 0.0), 100.0)
            except (TypeError, ValueError):
                continue
            level.set(value)
            shown.set(f"{round(value)} %")
        self._changed()