"""Bandbedingungen an einer Stelle: welche Störungen wie stark und wie laut
die Störgeräusche insgesamt sind. Eingestellt in einem eigenen Fenster
(erreichbar über „Weitere Optionen“ und jeden Reiter), die Reiter schalten
sie nur an oder aus (BandToggle). Änderungen wirken sofort, auch in einem
laufenden Durchgang."""
import sys
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import band
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.band_preview import BandPreview
from morsetrainer.widgets.ui_widgets import ScrollableFrame

# Störungen (Schlüssel aus band.EFFECTS, Beschriftung, Startwert in %).
BAND_OPTIONS = (
    ("noise", N_("Bandrauschen"), 60),
    ("qrn", N_("Knackstörungen (QRN)"), 30),
    ("qsb", N_("QSB (Fading)"), 50),
    ("strength", N_("Stärkeunterschiede (QSO, Contest)"), 50),
    ("chirp", N_("Chirp (zwitschernder Sender)"), 50),
    ("ssb", N_("SSB-QRM (verstimmte Sprache)"), 40),
    ("cw_qrm", N_("CW-QRM (Nachbar-Run)"), 30),
)
# Weitere Störungen: eigene, aufklappbare Gruppe; gehören zu keiner Stufe.
EXTRA_OPTIONS = (
    ("storm", N_("Gewitter (QRN in Schüben)"), 50),
    ("agc", N_("AGC-Pumpen nach Knackern"), 50),
    ("flutter", N_("Flatterfading (Aurora)"), 40),
    ("carrier", N_("Träger (jemand stimmt ab)"), 40),
    ("smps", N_("Schaltnetzteil (Brumm, Pfeifton)"), 40),
    ("plc", N_("PLC (Datenrauschen aus der Steckdose)"), 30),
    ("fence", N_("Weidezaun (Ticken)"), 40),
    ("clicks", N_("Tastklicks (Nachbar tastet hart)"), 50),
)
SHORT_NAMES = {"noise": N_("Bandrauschen"), "qrn": "QRN", "qsb": "QSB", "chirp": "Chirp",
               "ssb": "SSB-QRM", "cw_qrm": "CW-QRM", "strength": N_("Stärke"), "storm": N_("Gewitter"),
               "agc": N_("AGC-Pumpen"), "flutter": N_("Flattern"), "carrier": N_("Träger"),
               "smps": N_("Netzteil"), "plc": "PLC", "fence": N_("Weidezaun"), "clicks": N_("Tastklicks")}
PRESET_NAMES = {"light": N_("leicht"), "medium": N_("mittel"), "heavy": N_("stark")}
FILTER_NAMES = {2400: N_("2,4 kHz"), 500: N_("500 Hz"), 250: N_("250 Hz")}
QRM_OFFSET_NAMES = {"far": N_("weit (300–500 Hz)"), "near": N_("nah (50–200 Hz)"), "zero": N_("Zero-Beat")}
QRM_OFFSET_SHORT = {"far": N_("weit"), "near": N_("nah"), "zero": N_("Zero-Beat")}
# Startwerte, solange nichts gespeichert ist: wer zum ersten Mal zuschaltet,
# soll nicht gleich im tiefen Fading landen.
DEFAULT_PRESET = "light"
# Formatkennung der gespeicherten Einstellungen. Fehlt sie, sind es alte
# Einstellungen, in denen QSB die Stärkeunterschiede mit einschloss
# (restore() schaltet sie dann mit ein).
SETTINGS_VERSION = 2
# Höchstens dieser Anteil der Bildschirmhöhe; was nicht passt, wird gescrollt.
WINDOW_MAX_SCREEN_SHARE = 0.85
# So oft schaut das Fenster, ob das Probehören zu Ende ist.
PREVIEW_POLL_MS = 200
# Lautstärke der Störgeräusche gegenüber den Zeichen, in Prozent.
GAIN_RANGE = (round(band.GAIN_RANGE[0] * 100), round(band.GAIN_RANGE[1] * 100))


def signed_db(value: float) -> str:
    """„+8 dB“, „−4 dB“ (mit echtem Minuszeichen)."""
    return f"{value:+.0f} dB".replace("-", "−")


def level_text(key: str, level: float, gain: float = 1.0) -> str:
    """Anzeige eines Pegels (0..1) in der Sprache der Funkamateure:
    Rauschen als Rauschabstand (2,4 kHz), Chirp als Frequenzablage, sonst
    Prozent."""
    if key == "noise":
        return tr("S/N {db}").format(db=signed_db(band.noise_snr_db(level, gain)))
    if key == "chirp":
        return tr("bis {hz} Hz").format(hz=round(band.chirp_max_hz(level)))
    return f"{round(level * 100)} %"


def toggle_value(value):
    """An/aus aus einer gespeicherten Reiter-Einstellung: True/False, in
    alten Einstellungen auch eine Stufe als Text oder Schalter je Störung
    als dict. None, wenn der Wert nichts aussagt; None selbst heißt aus
    (Tagesübung)."""
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
        for key, _, default in BAND_OPTIONS + EXTRA_OPTIONS:
            self.controls[key] = (tk.BooleanVar(value=False), tk.DoubleVar(value=default))
        self.gain_var = tk.DoubleVar(value=100)
        self.filter_var = tk.IntVar(value=band.DEFAULT_FILTER)
        self.qrm_offset_var = tk.StringVar(value=band.DEFAULT_QRM_OFFSET)
        self.listeners = []
        self.window = None
        self.focus_before = None  # Fokus im Hauptfenster vor dem Öffnen
        self.preview = None  # BandPreview, sobald attach_preview() gerufen ist
        self.preview_blocked = lambda: None  # Grund, warum gerade nicht, sonst None
        self.preview_poll = None  # after-ID der Abfrage, ob das Probehören zu Ende ist
        self.set_preset(DEFAULT_PRESET, notify=False)
        self.controls["strength"][0].set(True)

    # --- Werte -----------------------------------------------------------
    def spec(self) -> dict:
        """Eingeschaltete Störungen mit Pegel über 0 % (0 % wäre nicht zu
        hören); Filter und QRM-Abstand nur, wenn nicht die Grundeinstellung."""
        spec = {
            "levels": {key: round(level.get()) / 100 for key, (on, level) in self.controls.items()
                       if on.get() and round(level.get()) > 0},
            "gain": round(self.gain_var.get()) / 100,
        }
        if self.filter_var.get() != band.DEFAULT_FILTER:
            spec["filter"] = self.filter_var.get()
        if self.qrm_offset_var.get() != band.DEFAULT_QRM_OFFSET:
            spec["qrm_offset"] = self.qrm_offset_var.get()
        return spec

    def set_spec(self, spec, notify=True) -> None:
        """Übernimmt `spec` in die Regler und Schalter; mit `notify` erfahren es
        Fenster und Reiter."""
        for key, (on, level) in self.controls.items():
            on.set(key in spec["levels"])
            if key in spec["levels"]:
                level.set(round(spec["levels"][key] * 100))
        self.gain_var.set(round(spec["gain"] * 100))
        self.filter_var.set(spec.get("filter", band.DEFAULT_FILTER))
        self.qrm_offset_var.set(spec.get("qrm_offset", band.DEFAULT_QRM_OFFSET))
        if notify:
            self._changed()

    def set_preset(self, preset: str, notify=True) -> None:
        """Stufe übernehmen; Lautstärke, Stärkeunterschiede, Filter und
        QRM-Abstand bleiben (sie gehören nicht zur Stufe)."""
        current = self.spec()
        spec = band.spec_from_preset(preset)
        spec["gain"] = current["gain"]
        if "strength" in current["levels"]:
            spec["levels"]["strength"] = current["levels"]["strength"]
        spec |= {key: current[key] for key in ("filter", "qrm_offset") if key in current}
        self.set_spec(spec, notify)

    def settings(self) -> dict:
        """Zum Speichern (window_state.json, Abschnitt shared)."""
        return self.spec() | {"version": SETTINGS_VERSION}

    def restore(self, data) -> bool:
        """Gegenstück zu settings(); False, wenn nichts Brauchbares dabei war.
        Alte Einstellungen ohne Formatkennung (SETTINGS_VERSION): Ist QSB an,
        werden auch die Stärkeunterschiede mit demselben Pegel eingeschaltet,
        denn dort gehörten sie zu QSB."""
        spec = band.clean_spec(data)
        if spec is None:
            return False
        if data.get("version") is None and "qsb" in spec["levels"]:
            spec["levels"].setdefault("strength", spec["levels"]["qsb"])
        self.set_spec(spec, notify=False)
        return True

    def restore_panel(self, data) -> bool:
        """Übernimmt die eigene Einstellung, die der QSO- oder Contest-Reiter
        in alten Einstellungsdateien hat ({Störung: {"enabled", "level"}}),
        wenn dort etwas an war."""
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
        """Kurzfassung für die Reiter, z. B. „Rauschen S/N +2 dB, QRN 30 %,
        QSB 50 %, CW-QRM 30 % nah · Filter 500 Hz · Lautstärke 100 % ·
        Stufe mittel“."""
        spec = self.spec()
        parts = [f"{tr(SHORT_NAMES[key])} {level_text(key, level, spec['gain'])}"
                 + (f" {tr(QRM_OFFSET_SHORT[spec['qrm_offset']])}"
                    if key in ("cw_qrm", "clicks") and "qrm_offset" in spec
                    else "")
                 for key, level in spec["levels"].items()]
        text = ", ".join(parts) if parts else tr("keine Störung eingeschaltet")
        if "filter" in spec:
            text += " · " + tr("Filter {width}").format(width=tr(FILTER_NAMES[spec["filter"]]))
        text += " · " + tr("Lautstärke {gain} %").format(gain=round(spec["gain"] * 100))
        rank = band.preset_rank(spec, self.pitch())
        if rank:
            text += " · " + tr("Stufe {name}").format(name=tr(PRESET_NAMES[rank]))
        return text

    def pitch(self) -> float:
        """Eigene Tonhöhe für S/N im Filter und Stufe (aus der Kopfleiste über
        attach_preview, sonst 600 Hz)."""
        try:
            return float(self.preview.params()[1]) if self.preview is not None else 600.0
        except (tk.TclError, TypeError, ValueError):
            return 600.0

    def pitch_changed(self) -> None:
        """Tonhöhe in der Kopfleiste geändert: Kurzfassung und Fenster neu."""
        self._changed()

    def attach_preview(self, params, blocked) -> None:
        """Probehören einrichten: `params()` liefert (WpM, Tonhöhe,
        Rufzeichen), `blocked()` den Grund, warum es gerade nicht geht
        (Durchgang läuft, Netzwerk), sonst None."""
        self.preview = BandPreview(self, params)
        self.preview_blocked = blocked

    def toggle_preview(self) -> None:
        """Probehören starten bzw. beenden (Knopf, Strg+P); gesperrt, solange
        preview_blocked() einen Grund nennt."""
        if self.preview is None:
            return
        if self.preview.running:
            self.preview.stop()
        elif self.preview_blocked() is None:
            self.preview.start()
            self._poll_preview()
        self._show_preview()

    def stop_preview(self) -> None:
        """Ein Durchgang beginnt oder das Fenster geht zu."""
        if self.preview is not None and self.preview.running:
            self.preview.stop()
        self._show_preview()

    def _poll_preview(self) -> None:
        self.preview_poll = None
        self._show_preview()
        if self.preview.running and self.window is not None:
            self.preview_poll = self.root.after(PREVIEW_POLL_MS, self._poll_preview)

    def _show_preview(self) -> None:
        """Knopf und Hinweis des Probehörens auf den Stand bringen: läuft, gesperrt
        (mit Grund), Fehler oder bereit."""
        if self.window is None or not hasattr(self, "preview_button"):
            return
        running = self.preview is not None and self.preview.running
        blocked = self.preview_blocked() if self.preview is not None else None
        self.preview_button.config(text=tr("Probehören beenden") if running else tr("Probehören"))
        self.preview_button.state(["disabled"] if blocked and not running else ["!disabled"])
        if running:
            text = tr("CQ mit diesen Bedingungen, bis du stoppst; Änderungen sind gleich zu hören.")
        elif blocked:
            text = blocked
        elif self.preview is not None and self.preview.error:
            text = self.preview.error
        else:
            text = tr("Zählt nicht für Statistik, Übungszeit und Diplome.")
        self.preview_var.set(text)

    def subscribe(self, callback) -> None:
        """`callback()` bei jeder Änderung der Einstellung aufrufen (Reiter,
        Kurzfassung, Probehören)."""
        self.listeners.append(callback)

    def _changed(self) -> None:
        self._update_window()
        for callback in self.listeners:
            callback()

    # --- Fenster ---------------------------------------------------------
    def open_window(self) -> None:
        """Öffnet das Fenster Bandbedingungen (oder holt es nach vorn) und merkt,
        wo der Fokus vorher war."""
        if self.window is not None:
            self.window.deiconify()
            self.window.lift()
            return
        self.focus_before = self.root.focus_get()
        window = self.window = tk.Toplevel(self.root)
        window.title(tr("Bandbedingungen"))
        window.transient(self.root)  # bleibt über dem Hauptfenster
        window.configure(background=theme.BG)
        window.protocol("WM_DELETE_WINDOW", self.close_window)
        window.bind("<Escape>", lambda e: self.close_window())
        # Mit Scrollleiste: Bei großer Schrift oder kleinem Bildschirm passt
        # das Fenster nicht ganz auf den Bildschirm.
        self.scroller = ScrollableFrame(window)
        frame = self.content = ttk.Frame(self.scroller.inner, padding=10)
        frame.pack(fill="both", expand=True)
        theme.hint(frame, wrap=460, text=tr(
            "Gilt für alle Reiter; dort schaltest du die Bandbedingungen nur an oder aus. Änderungen wirken "
            "sofort, auch im laufenden Durchgang. Im Netzwerk hören alle die Einstellung des Trainers.")).pack(
            anchor="w", pady=(0, 2))
        theme.hint(frame, wrap=460, text=tr(
            "Neue Zeichen ohne Störungen lernen. Zuschalten, wenn der Zeichensatz ohne Störungen sicher sitzt "
            "(90 % und mehr), und mit „leicht“ beginnen.")).pack(anchor="w", pady=(0, 6))

        presets = ttk.Frame(frame)
        presets.pack(fill="x", pady=(0, 4))
        ttk.Label(presets, text=tr("Stufe:")).pack(side="left", padx=(0, 6))
        for preset, name in PRESET_NAMES.items():
            ttk.Button(presets, text=tr(name), command=lambda p=preset: self.set_preset(p)).pack(side="left", padx=2)

        box = theme.card(frame, tr("Störungen"), padx=0)
        box.columnconfigure(1, weight=1)
        self.widgets = {}
        for row, (key, label, _) in enumerate(BAND_OPTIONS):
            self._option_row(box, row, key, label)
        offsets = ttk.Frame(box)
        offsets.grid(row=len(BAND_OPTIONS), column=0, columnspan=3, sticky="w", padx=(22, 0), pady=(0, 2))
        theme.hint(offsets, text=tr("CW-QRM-Abstand:")).pack(side="left", padx=(0, 6))
        self.offset_buttons = []
        for key, name in QRM_OFFSET_NAMES.items():
            button = ttk.Radiobutton(offsets, text=tr(name), value=key, variable=self.qrm_offset_var,
                                     command=self._changed)
            button.pack(side="left", padx=(0, 8))
            self.offset_buttons.append(button)
        buttons = ttk.Frame(box)
        buttons.grid(row=len(BAND_OPTIONS) + 1, column=0, columnspan=3, sticky="e", pady=(6, 0))
        ttk.Button(buttons, text=tr("Alle aus"), command=lambda: self._set_all(False)).pack(side="right")
        ttk.Button(buttons, text=tr("Alle an"), command=lambda: self._set_all(True)).pack(side="right", padx=4)

        # Weitere Störungen, aufklappbar; offen, sobald darin etwas an ist.
        self.extra_button = ttk.Button(frame, style="Flat.TButton", command=self._toggle_extras)
        self.extra_button.pack(anchor="w", padx=10)
        self.extra_box = ttk.Frame(frame, padding=(10, 0, 10, 4))
        self.extra_box.columnconfigure(1, weight=1)
        for row, (key, label, _) in enumerate(EXTRA_OPTIONS):
            self._option_row(self.extra_box, row, key, label)
        theme.hint(self.extra_box, wrap=440, text=tr(
            "Gehören zu keiner Stufe und zählen nicht für das Diplom QRN-fest. Die Tastklicks kommen vom "
            "Nachbar-Run (CW-QRM-Abstand gilt) und sind auch zu hören, wenn sein Ton aus ist oder draußen "
            "vor dem Filter bleibt.")).grid(
            row=len(EXTRA_OPTIONS), column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.extras_open = any(self.controls[key][0].get() for key, _, _ in EXTRA_OPTIONS)
        self._show_extras()

        receiver = theme.card(frame, tr("CW-Filter"), padx=0)
        self.receiver_card = receiver
        row = ttk.Frame(receiver)
        row.pack(fill="x")
        for width, name in FILTER_NAMES.items():
            ttk.Radiobutton(row, text=tr(name), value=width, variable=self.filter_var,
                            command=self._changed).pack(side="left", padx=(0, 12))
        self.filter_shown = ttk.Label(row, anchor="e")
        self.filter_shown.pack(side="right")
        theme.hint(receiver, wrap=440, text=tr(
            "Um deine Tonhöhe; Zeichen, Rauschen und Störungen laufen hindurch. Ein schmales Filter nimmt "
            "Rauschen und weiter entferntes QRM weg, klingelt aber leicht; Stationen neben deiner Tonhöhe "
            "werden leiser. Gegen QRM nah oder Zero-Beat hilft es nicht – dann hilft nur das Ohr.")).pack(
            anchor="w", pady=(4, 0))

        gain = theme.card(frame, tr("Lautstärke der Störgeräusche"), padx=0)
        row = ttk.Frame(gain)
        row.pack(fill="x")
        theme.hint(row, text=tr("leiser")).pack(side="left")
        gain_scale = ttk.Scale(row, from_=GAIN_RANGE[0], to=GAIN_RANGE[1], variable=self.gain_var, length=220,
                               command=lambda _: self._changed())
        gain_scale.pack(side="left", fill="x", expand=True, padx=6)
        announcer.name(gain_scale, tr("Lautstärke der Störgeräusche"),
                       value=lambda: f"{round(self.gain_var.get())} %")
        theme.hint(row, text=tr("lauter")).pack(side="left")
        self.gain_shown = ttk.Label(row, width=6, anchor="e")
        self.gain_shown.pack(side="left", padx=(6, 0))
        theme.hint(box, wrap=440, text=tr(
            "S/N: Rauschabstand in 2,4 kHz Bandbreite gegenüber dem ungeschwächten Signal; im Ohr, das CW "
            "wie ein Filter von etwa 50 Hz hört, sind es rund 17 dB mehr.")).grid(
            row=len(BAND_OPTIONS) + 2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        theme.hint(gain, wrap=440, text=tr(
            "Alle Störgeräusche gemeinsam gegenüber den Zeichen; verschiebt auch den Rauschabstand. 100 % ist "
            "die normale Mischung, für das Diplom QRN-fest müssen es mindestens 100 % sein.")).pack(
            anchor="w", pady=(4, 0))

        self.rank_var = tk.StringVar(value="")
        theme.hint(frame, textvariable=self.rank_var, wrap=460).pack(anchor="w", pady=(4, 0))
        bottom = ttk.Frame(frame)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text=tr("Schließen"), command=self.close_window).pack(side="right")
        self.preview_var = tk.StringVar(value="")
        if self.preview is not None:
            # Strg+P (auf dem Mac auch Cmd+P): die Bedingungen gleich hören.
            self.preview_button = ttk.Button(bottom, command=self.toggle_preview, width=18)
            self.preview_button.pack(side="left")
            theme.hint(frame, textvariable=self.preview_var, wrap=460).pack(anchor="w", pady=(4, 0))
            for modifier in ("Control", "Command") if sys.platform == "darwin" else ("Control",):
                window.bind(f"<{modifier}-p>", lambda e: self.toggle_preview() or "break")
        self._update_window()
        self._show_preview()
        self._fit_window()

    def _fit_window(self) -> None:
        """So groß wie der Inhalt, aber nicht höher als der Bildschirm
        erlaubt; der Rest ist mit der Scrollleiste erreichbar."""
        self.window.update_idletasks()
        limit = int(self.window.winfo_screenheight() * WINDOW_MAX_SCREEN_SHARE)
        self.scroller.canvas.config(width=self.content.winfo_reqwidth(),
                                    height=min(self.content.winfo_reqheight(), limit))

    def close_window(self) -> None:
        """Schließt das Fenster und gibt den Fokus zurück, etwa an das
        Eingabefeld eines laufenden Durchgangs."""
        if self.preview is not None:
            self.preview.stop()
        if self.preview_poll is not None:
            self.root.after_cancel(self.preview_poll)
            self.preview_poll = None
        if self.window is not None:
            self.window.destroy()
            self.window = None
        focus, self.focus_before = self.focus_before, None
        try:
            if focus is not None and focus.winfo_exists():
                focus.focus_set()
        except tk.TclError:
            pass

    def _option_row(self, box, row: int, key: str, label: str) -> None:
        """Schalter, Regler und angezeigter Wert einer Störung."""
        on, level = self.controls[key]
        ttk.Checkbutton(box, text=tr(label), variable=on, command=self._changed).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=1)
        scale = ttk.Scale(box, from_=0, to=100, variable=level, length=200, command=lambda _: self._changed())
        scale.grid(row=row, column=1, sticky="we", pady=1)
        announcer.name(scale, tr(label), value=lambda k=key, v=level: level_text(
            k, round(v.get()) / 100, round(self.gain_var.get()) / 100))
        shown = ttk.Label(box, width=11, anchor="e")
        shown.grid(row=row, column=2, padx=(6, 0))
        self.widgets[key] = (scale, shown)

    def _toggle_extras(self) -> None:
        self.extras_open = not self.extras_open
        self._show_extras()
        self._fit_window()

    def _show_extras(self) -> None:
        self.extra_button.config(text=("▾ " if self.extras_open else "▸ ") + tr("Weitere Störungen"))
        if self.extras_open:
            self.extra_box.pack(fill="x", after=self.extra_button)
        else:
            self.extra_box.pack_forget()

    def _set_all(self, enabled: bool) -> None:
        for on, _ in self.controls.values():
            on.set(enabled)
        self._changed()

    def _update_window(self) -> None:
        """Fenster auf den Stand bringen: Regler nur bei eingeschalteter Störung
        bedienbar, angezeigte Werte, QRM-Abstand, S/N im Filter und welcher Stufe
        die Einstellung entspricht."""
        if self.window is None:
            return
        for key, (scale, shown) in self.widgets.items():
            on, level = self.controls[key]
            scale.state(["!disabled"] if on.get() else ["disabled"])
            shown.config(text=level_text(key, round(level.get()) / 100, round(self.gain_var.get()) / 100),
                         foreground="" if on.get() else theme.DISABLED)
        self.gain_shown.config(text=f"{round(self.gain_var.get())} %")
        neighbour = self.controls["cw_qrm"][0].get() or self.controls["clicks"][0].get()
        for button in self.offset_buttons:
            button.state(["!disabled"] if neighbour else ["disabled"])
        spec = self.spec()
        if "filter" in spec and "noise" in spec["levels"]:
            snr = (band.noise_snr_db(spec["levels"]["noise"], spec["gain"])
                   + band.filter_noise_db(spec["filter"], self.pitch()))
            self.filter_shown.config(text=tr("im Filter S/N {db}").format(db=signed_db(snr)))
        else:
            self.filter_shown.config(text="")
        rank = band.preset_rank(spec, self.pitch())
        if rank:
            text = tr("Entspricht mindestens Stufe {name}.").format(name=tr(PRESET_NAMES[rank]))
        else:
            light = band.PRESETS["light"]
            text = tr("Keiner Stufe zugeordnet: Stufe leicht braucht mindestens Rauschen {snr} "
                      "und QSB {qsb} %.").format(snr=level_text("noise", light["noise"]),
                                                  qsb=round(light["qsb"] * 100))
        if "filter" in spec:
            text += " " + tr("Mit schmalem Filter zählt der Rauschabstand im Filter.")
        self.rank_var.set(text)


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
        self.check = ttk.Checkbutton(top, text=tr("Bandbedingungen"), variable=variable)
        self.check.pack(side="left")
        ttk.Button(top, text=tr("Einstellen …"), style="Flat.TButton",
                   command=settings.open_window).pack(side="left", padx=(6, 0))
        self.locked_hint = theme.hint(top, text=tr("an/aus erst nach dem Durchgang"))
        self.summary_var = tk.StringVar(value="")
        self.summary = theme.hint(self.frame, textvariable=self.summary_var, wrap=520)
        self.summary.pack(anchor="w", padx=(22, 0))
        variable.trace_add("write", lambda *_: self._changed())
        settings.subscribe(self._changed)
        self._show()

    def set_locked(self, locked: bool) -> None:
        """Während eines Durchgangs: an/aus gesperrt (davon hängt ab, ob er
        für die Zeichenstatistik zählt); Stärke und Lautstärke bleiben
        einstellbar."""
        self.check.state(["disabled"] if locked else ["!disabled"])
        if locked:
            self.locked_hint.pack(side="left", padx=(8, 0))
        else:
            self.locked_hint.pack_forget()

    def _show(self) -> None:
        self.summary_var.set(self.settings.summary())
        self.summary.config(foreground="" if self.variable.get() else theme.DISABLED)

    def _changed(self) -> None:
        self._show()
        if self.on_change is not None:
            self.on_change()
