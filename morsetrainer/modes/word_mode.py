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

from morsetrainer.core import koch, words
from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.sequence_mode import COPY, MEMORIZE, SequenceModeFrame
from morsetrainer.widgets import theme


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
    """Reiter Wörter: Wörter, Q-Gruppen, Abkürzungen und Wendungen (oder eigene
    Wörter aus woerter.txt) aus dem gelernten Zeichensatz; Standard ist
    „Erst merken“, das ganze Wort hören und dann tippen."""
    session_mode = "word"
    # Erst das ganze Wort hören, dann tippen: fördert das Wort als Klangbild
    # statt Buchstabe für Buchstabe.
    default_style = MEMORIZE
    send_prosigns = True
    # Im Wort verrät der Zusammenhang viele Buchstaben.
    char_stats = False
    intro_text = N_(
        "Es kommen CW-Abkürzungen, Q-Gruppen und Wörter aus QSOs – nur solche, die "
        "aus den Zeichen oben bestehen. Mit jeder Koch-Lektion werden es mehr."
    )

    def _build_extra_settings(self, parent):
        """Eigene Einstellungen des Reiters: Zahl der passenden Wörter und Knopf zum
        Bearbeiten der eigenen Wörter (woerter.txt)."""
        self.all_words = dict(words.WORDS)
        self.user_words, self.skipped = {}, []
        self.words_mtime = -1  # Änderungszeit von woerter.txt beim letzten Einlesen (None = fehlt)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 4))
        self.count_var = tk.StringVar(value="")
        theme.hint(row, textvariable=self.count_var, wrap=360).pack(side="left")
        ttk.Button(row, text=tr("Eigene Wörter bearbeiten"), command=self._edit_user_words).pack(side="right")
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
        """Liest woerter.txt bei Bedarf neu und zeigt, wie viele Wörter zum
        Zeichensatz passen (davon eigene) und welche Zeilen übersprungen wurden."""
        self._reload_words()
        user, skipped = self.user_words, self.skipped
        count = len(words.words_for_charset(self._charset(), self.all_words))
        text = tr("Mit dem aktuellen Zeichensatz: {count} von {total} Wörtern").format(
            count=count, total=len(self.all_words))
        if user:
            text += tr(" (davon {n} eigene)").format(n=len(user))
        if skipped:
            text += "\n" + tr("Übersprungen in {file}: ").format(file=words.USER_WORDS_FILE.name) + ", ".join(skipped[:3])
            if len(skipped) > 3:
                text += tr(" und {n} weitere").format(n=len(skipped) - 3)
        self.count_var.set(text)

    def _edit_user_words(self):
        try:
            open_in_editor(words.ensure_user_file())
        except OSError as exc:
            self.status_var.set(tr("{file} lässt sich nicht öffnen: {error}").format(file=words.USER_WORDS_FILE, error=exc))

    def _validate_settings(self) -> bool:
        """Genug Wörter mit dem Zeichensatz? Sonst steht in der Statuszeile, ab
        welcher Lektion es reicht."""
        self._show_count()
        charset = self._charset()
        self.words = words.words_for_charset(charset, self.all_words)
        if not words.enough_words(self.words):
            # Mit einer Handvoll Wörter stünde die Antwort fest (bei RR und UR
            # im Wechsel); dann lieber Gruppen üben.
            first = words.first_lesson_with_words(self.all_words)
            when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
            count = sum(1 for w in self.words if len(w) > 1)
            self.status_var.set(tr("Nur {count} Wörter mit diesen Zeichen").format(count=count) + when + ".\n"
                                + tr("Übe bis dahin mit Gruppen."))
            return False
        self.charset = charset
        return True

    def _setup_pickers(self, weighted: bool):
        # Das neueste Zeichen der Koch-Lektion bevorzugt üben.
        lesson = koch.lesson_of(self.charset)
        favor = koch.newest_char(lesson) if lesson else ""
        self.picker = words.WordPicker(self.words, CharPicker(self.charset, weighted, self.session_stats), favor)

    def _generate_sequence(self) -> str:
        return self.picker.pick()

    def _explain(self, sequence: str) -> str:
        return words.shown_meaning(sequence, self.all_words.get(sequence, ""))

    def _log_charset(self) -> str:
        return self.charset

    def settings(self) -> dict:
        """Wie SequenceModeFrame.settings(), dazu die Kennung, dass die Umstellung
        auf „Erst merken“ schon erfolgt ist."""
        data = super().settings()
        data["memorize_default"] = True  # Umstellung auf „Erst merken“ erledigt
        return data

    def restore_settings(self, data: dict) -> None:
        """Wie SequenceModeFrame; alte Einstellungen ohne diese Kennung werden einmal
        auf „Erst merken“ umgestellt."""
        super().restore_settings(data)
        # Gespeicherte Einstellungen ohne „memorize_default“ stammen aus der
        # Zeit, als „Mitschreiben“ Standard war: einmalig auf „Erst merken“
        # umstellen, danach gilt wieder, was gespeichert ist.
        if data and not data.get("memorize_default") and self.style_var.get() == COPY:
            self.style_var.set(MEMORIZE)
            self.status_var.set(tr("Neu: Wörter jetzt mit „Erst merken“ – erst das ganze Wort hören, "
                                   "dann tippen. Umstellbar unter Eingabe."))
