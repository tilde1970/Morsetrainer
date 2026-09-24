"""Gruppen-Modus: sendet eine zufällige Gruppe von Zeichen aus dem
eingestellten Zeichensatz (konfigurierbare Länge)."""
import random
import tkinter as tk
from tkinter import ttk

from morse import MORSE_CODE
from sequence_mode import SequenceModeFrame
from weighting import CharPicker


class GroupModeFrame(SequenceModeFrame):
    session_mode = "group"
    send_prosigns = True

    def _build_extra_settings(self, parent):
        pad = {"padx": 8, "pady": 4}
        settings = ttk.Frame(parent)
        settings.pack(fill="x", **pad)
        ttk.Label(settings, text="Gruppenlänge von:").pack(side="left", padx=(0, 4))
        self.min_len_var = tk.IntVar(value=3)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.min_len_var, width=4).pack(side="left")
        ttk.Label(settings, text="bis:").pack(side="left", padx=(8, 4))
        self.max_len_var = tk.IntVar(value=5)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.max_len_var, width=4).pack(side="left")

    def _validate_settings(self) -> bool:
        charset = "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)
        if not charset:
            self.status_var.set("Kein gültiges Zeichen im Zeichensatz!")
            return False
        if self.min_len_var.get() > self.max_len_var.get():
            self.status_var.set("Gruppenlänge 'von' darf nicht größer als 'bis' sein!")
            return False
        self.charset = charset
        return True

    def _setup_pickers(self, weighted: bool):
        self.picker = CharPicker(self.charset, weighted, self.session_stats)

    def _generate_sequence(self) -> str:
        length = random.randint(self.min_len_var.get(), self.max_len_var.get())
        return self.picker.pick(length)

    def _log_charset(self) -> str:
        return self.charset

    def _session_group_len(self):
        return (self.min_len_var.get(), self.max_len_var.get())