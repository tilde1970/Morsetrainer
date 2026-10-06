"""Gruppen-Modus: sendet eine zufällige Gruppe von Zeichen aus dem
eingestellten Zeichensatz. Die Länge ist entweder zufällig zwischen
"von" und "bis" oder wächst automatisch mit (AdaptiveLength): Einsteiger
fangen bei kurzen Gruppen an und kommen von selbst zu längeren."""
import random
import tkinter as tk
from tkinter import ttk

from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import tr
from morsetrainer.modes.sequence_mode import SequenceModeFrame
from morsetrainer.widgets import theme

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
        als Fehler: es unterbricht die Erfolgsserie, lässt aber die
        Fehlerserie stehen (sonst würde die Länge nie kürzer, solange die
        Wiederholung klappt). Fehler zählen nur im ersten Versuch: eine
        einzelne schwierige Gruppe, die zweimal danebengeht, soll die Länge
        nicht gleich kürzen."""
        if correct and attempts == 1:
            self.good_streak += 1
            self.bad_streak = 0
        elif correct:
            self.good_streak = 0
        elif attempts == 1:
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
    """Reiter Gruppen: Zufallsgruppen aus dem Zeichensatz hören und eintippen.
    Zählt für den Koch-Aufstieg; auf Wunsch wächst die Gruppenlänge mit dem
    Können."""
    session_mode = "group"
    daily_keys = SequenceModeFrame.daily_keys + ("adaptive", "min_len", "max_len")
    send_prosigns = True
    koch_progress = True
    review_promotes = True

    def _build_extra_settings(self, parent):
        """Eigene Einstellungen des Reiters: Gruppenlänge von–bis und wachsende
        Länge."""
        settings = ttk.Frame(parent)
        settings.pack(fill="x", pady=1)
        ttk.Label(settings, text=tr("Gruppenlänge von")).pack(side="left", padx=(0, 4))
        self.min_len_var = tk.IntVar(value=2)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.min_len_var, width=4).pack(side="left")
        ttk.Label(settings, text=tr("bis")).pack(side="left", padx=(8, 4))
        self.max_len_var = tk.IntVar(value=5)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.max_len_var, width=4).pack(side="left")

        adaptive = ttk.Frame(parent)
        adaptive.pack(fill="x", pady=1)
        self.adaptive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            adaptive, text=tr("Länge wächst mit ({longer}× richtig: länger, {shorter} Fehler: kürzer)").format(
                longer=LONGER_AFTER, shorter=SHORTER_AFTER),
            variable=self.adaptive_var,
        ).pack(side="left")
        # Nur während eines Durchgangs mit wachsender Länge, sonst ohne Leerzeile.
        self.length_info_var = tk.StringVar(value="")
        self.length_info_label = theme.hint(parent, textvariable=self.length_info_var)
        self.length_info_var.trace_add("write", lambda *_: self._place_length_info(adaptive))
        self.adaptive = None
        self.saved_length = None  # zuletzt erreichte Länge, Start beim nächsten Mal

    def _validate_settings(self) -> bool:
        """Gültiger Zeichensatz und Gruppenlänge („von“ nicht größer als „bis“)?
        Sonst steht der Grund in der Statuszeile."""
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set(tr("Kein gültiges Zeichen im Zeichensatz!"))
            return False
        try:
            low, high = self.min_len_var.get(), self.max_len_var.get()
        except tk.TclError:
            self.status_var.set(tr("Ungültige Gruppenlänge!"))
            return False
        if low > high:
            self.status_var.set(tr("Gruppenlänge „von“ darf nicht größer als „bis“ sein!"))
            return False
        self.charset = charset
        if self.adaptive_var.get():
            self.adaptive = AdaptiveLength(low, high, self.saved_length)
            self._show_length()
        else:
            self.adaptive = None
            self.length_info_var.set("")
        return True

    def _place_length_info(self, after):
        if self.length_info_var.get():
            self.length_info_label.pack(anchor="w", padx=(24, 0), after=after)
        else:
            self.length_info_label.pack_forget()

    def _show_length(self, change: int = 0):
        note = {1: tr(" – länger, weiter so!"), -1: tr(" – etwas kürzer")}.get(change, "")
        self.length_info_var.set(tr("Aktuelle Gruppenlänge: {length}").format(length=self.adaptive.length) + note)

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
        """Einstellungen zum Speichern: wie SequenceModeFrame, dazu wachsende Länge
        an/aus, zuletzt erreichte Länge und Mindest-/Höchstlänge."""
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
        """Gegenstück zu settings(); ungültige Werte werden übergangen."""
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
