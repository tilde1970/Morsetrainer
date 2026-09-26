"""Gruppen-Modus: sendet eine zufällige Gruppe von Zeichen aus dem
eingestellten Zeichensatz. Die Länge ist entweder zufällig zwischen
"von" und "bis" oder wächst automatisch mit (AdaptiveLength): Einsteiger
fangen bei kurzen Gruppen an und kommen von selbst zu längeren."""
import random
import tkinter as tk
from tkinter import ttk

from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.core.weighting import CharPicker
from morsetrainer.modes.sequence_mode import SequenceModeFrame

# So viele Gruppen in Folge beim ersten Versuch richtig -> eine länger.
LONGER_AFTER = 5
# So viele Fehlversuche in Folge -> eine kürzer.
SHORTER_AFTER = 2


class AdaptiveLength:
    """Gruppenlänge zwischen `low` und `high`, die mit dem Erfolg wächst."""

    def __init__(self, low: int, high: int, start=None):
        self.low, self.high = low, high
        self.length = min(max(start if start is not None else low, low), high)
        self.good_streak = 0
        self.bad_streak = 0

    def update(self, correct: bool, attempts: int) -> int:
        """Gibt -1, 0 oder +1 zurück, je nachdem wie sich die Länge ändert.
        Richtig erst nach einer Wiederholung zählt weder als Erfolg noch
        als Fehler, unterbricht aber die Erfolgsserie."""
        if correct and attempts == 1:
            self.good_streak += 1
            self.bad_streak = 0
        elif correct:
            self.good_streak = self.bad_streak = 0
        else:
            self.bad_streak += 1
            self.good_streak = 0
        if self.good_streak >= LONGER_AFTER and self.length < self.high:
            self.length += 1
            self.good_streak = 0
            return 1
        if self.bad_streak >= SHORTER_AFTER and self.length > self.low:
            self.length -= 1
            self.bad_streak = 0
            return -1
        return 0


class GroupModeFrame(SequenceModeFrame):
    session_mode = "group"
    send_prosigns = True
    koch_progress = True

    def _build_extra_settings(self, parent):
        pad = {"padx": 8, "pady": 4}
        settings = ttk.Frame(parent)
        settings.pack(fill="x", **pad)
        ttk.Label(settings, text="Gruppenlänge von:").pack(side="left", padx=(0, 4))
        self.min_len_var = tk.IntVar(value=2)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.min_len_var, width=4).pack(side="left")
        ttk.Label(settings, text="bis:").pack(side="left", padx=(8, 4))
        self.max_len_var = tk.IntVar(value=5)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.max_len_var, width=4).pack(side="left")

        adaptive = ttk.Frame(parent)
        adaptive.pack(fill="x", padx=8)
        self.adaptive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            adaptive, text=f"Länge wächst mit ({LONGER_AFTER}× richtig: länger, "
                           f"{SHORTER_AFTER} Fehler: kürzer)",
            variable=self.adaptive_var,
        ).pack(side="left", padx=(8, 0))
        self.length_info_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.length_info_var, foreground="gray40").pack(anchor="w", padx=16)
        self.adaptive = None
        self.saved_length = None  # zuletzt erreichte Länge, Start beim nächsten Mal

    def _validate_settings(self) -> bool:
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set("Kein gültiges Zeichen im Zeichensatz!")
            return False
        try:
            low, high = self.min_len_var.get(), self.max_len_var.get()
        except tk.TclError:
            self.status_var.set("Ungültige Gruppenlänge!")
            return False
        if low > high:
            self.status_var.set("Gruppenlänge 'von' darf nicht größer als 'bis' sein!")
            return False
        self.charset = charset
        if self.adaptive_var.get():
            self.adaptive = AdaptiveLength(low, high, self.saved_length)
            self._show_length()
        else:
            self.adaptive = None
            self.length_info_var.set("")
        return True

    def _show_length(self, change: int = 0):
        note = {1: " – länger, weiter so!", -1: " – etwas kürzer"}.get(change, "")
        self.length_info_var.set(f"Aktuelle Gruppenlänge: {self.adaptive.length}{note}")

    def _setup_pickers(self, weighted: bool):
        self.picker = CharPicker(self.charset, weighted, self.session_stats)

    def _generate_sequence(self) -> str:
        if self.adaptive is not None:
            length = self.adaptive.length
        else:
            length = random.randint(self.min_len_var.get(), self.max_len_var.get())
        return self.picker.pick(length)

    def _after_result(self, correct: bool, attempts: int):
        if self.adaptive is not None:
            change = self.adaptive.update(correct, attempts)
            self.saved_length = self.adaptive.length
            self._show_length(change)

    def _log_charset(self) -> str:
        return self.charset

    def _session_group_len(self):
        return (self.min_len_var.get(), self.max_len_var.get(), "adaptiv" if self.adaptive else "zufällig")

    def settings(self) -> dict:
        data = super().settings()
        data["adaptive"] = self.adaptive_var.get()
        if self.saved_length is not None:
            data["length"] = self.saved_length
        for key, var in (("min_len", self.min_len_var), ("max_len", self.max_len_var)):
            try:
                data[key] = var.get()
            except tk.TclError:
                pass
        return data

    def restore_settings(self, data: dict) -> None:
        super().restore_settings(data)
        if isinstance(data.get("adaptive"), bool):
            self.adaptive_var.set(data["adaptive"])
        for key, var in (("min_len", self.min_len_var), ("max_len", self.max_len_var)):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 10:
                var.set(value)
        length = data.get("length")
        if isinstance(length, int) and not isinstance(length, bool) and 1 <= length <= 10:
            self.saved_length = length
