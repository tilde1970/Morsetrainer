"""Wörter-Modus: sendet CW-Abkürzungen, Q-Gruppen und typische QSO-Wörter,
aber nur solche aus Zeichen des eingestellten Zeichensatzes. Brücke
zwischen Gruppen (Zufall) und QSO (ganzer Text): man lernt, Wortbilder
als Ganzes zu hören. Nach der Antwort wird die Bedeutung angezeigt.

Eigene Wörter kommen aus woerter.txt im Datenverzeichnis; der Knopf
"Eigene Wörter bearbeiten" legt die Datei an und öffnet sie im Editor."""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import words
from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.core.weighting import CharPicker
from morsetrainer.modes.sequence_mode import SequenceModeFrame


def open_in_editor(path) -> None:
    """Öffnet `path` mit dem Standardprogramm des Systems."""
    if sys.platform == "win32":
        os.startfile(path)
        return
    command = ["open" if sys.platform == "darwin" else "xdg-open", str(path)]
    env = dict(os.environ)
    # Als AppImage/PyInstaller zeigt LD_LIBRARY_PATH auf die mitgelieferten
    # Bibliotheken; damit stürzt ein Editor des Systems womöglich ab. Den
    # ursprünglichen Wert hat der PyInstaller-Starter aufbewahrt.
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class WordModeFrame(SequenceModeFrame):
    session_mode = "word"
    send_prosigns = True
    intro_text = (
        "Es kommen CW-Abkürzungen, Q-Gruppen und Wörter aus QSOs – nur solche, die "
        "aus den Zeichen oben bestehen. Mit jeder Koch-Lektion werden es mehr."
    )

    def _build_extra_settings(self, parent):
        self.all_words = dict(words.WORDS)
        self.user_words, self.skipped = {}, []
        self.words_mtime = -1  # Änderungszeit von woerter.txt beim letzten Einlesen (None = fehlt)
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8)
        ttk.Button(row, text="Eigene Wörter bearbeiten", command=self._edit_user_words).pack(side="left")
        self.count_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.count_var, foreground="gray40", wraplength=460, justify="left").pack(
            anchor="w", padx=8, pady=(2, 0)
        )
        self.charset_var.trace_add("write", lambda *_: self._show_count())
        # Nach dem Bearbeiten im Editor: beim Zurückkehren ins Fenster neu zählen.
        self.root.bind("<FocusIn>", lambda e: self._show_count(), add="+")
        self._show_count()

    def _charset(self) -> str:
        return "".join(ch for ch in self.charset_var.get().upper() if ch in MORSE_CODE)

    def _reload_words(self):
        """Liest woerter.txt nur neu ein, wenn sie sich geändert hat (der
        Fokuswechsel, der das auslöst, kommt bei jeder Sequenz)."""
        try:
            mtime = words.USER_WORDS_FILE.stat().st_mtime
        except OSError:
            mtime = None
        if mtime != self.words_mtime:
            self.words_mtime = mtime
            self.all_words, self.user_words, self.skipped = words.load_words()

    def _show_count(self):
        self._reload_words()
        user, skipped = self.user_words, self.skipped
        count = len(words.words_for_charset(self._charset(), self.all_words))
        text = f"Mit dem aktuellen Zeichensatz: {count} von {len(self.all_words)} Wörtern"
        if user:
            text += f" (davon {len(user)} eigene)"
        if skipped:
            text += f"\nÜbersprungen in {words.USER_WORDS_FILE.name}: " + ", ".join(skipped[:3])
            if len(skipped) > 3:
                text += f" und {len(skipped) - 3} weitere"
        self.count_var.set(text)

    def _edit_user_words(self):
        try:
            open_in_editor(words.ensure_user_file())
        except OSError as exc:
            self.status_var.set(f"{words.USER_WORDS_FILE} lässt sich nicht öffnen: {exc}")

    def _validate_settings(self) -> bool:
        self._show_count()
        charset = self._charset()
        self.words = words.words_for_charset(charset, self.all_words)
        if not self.words:
            self.status_var.set("Mit diesen Zeichen gibt es noch keine Wörter – nimm ein paar Zeichen dazu.")
            return False
        self.charset = charset
        return True

    def _setup_pickers(self, weighted: bool):
        self.picker = words.WordPicker(self.words, CharPicker(self.charset, weighted, self.session_stats))

    def _generate_sequence(self) -> str:
        return self.picker.pick()

    def _explain(self, sequence: str) -> str:
        return self.all_words.get(sequence, "")

    def _log_charset(self) -> str:
        return self.charset
