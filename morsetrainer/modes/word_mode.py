"""Wörter-Modus: sendet CW-Abkürzungen, Q-Gruppen und typische QSO-Wörter
oder, wahlweise, kurze Wendungen aus QSOs („TNX FER CALL“), aber nur solche
aus Zeichen des eingestellten Zeichensatzes. Brücke zwischen Gruppen
(Zufall) und QSO (ganzer Text): man lernt, Wortbilder und ganze Wendungen
als Ganzes zu hören. Nach der Antwort wird die Bedeutung angezeigt.
Wendungen kommen mit Wortabstand, getippt wird ohne Leerzeichen; das
Zeitfenster ist zweigeteilt (erste Taste, dann Tippen).

Eigene Wörter kommen aus woerter.txt im Datenverzeichnis; der Knopf
"Eigene Wörter bearbeiten" legt die Datei an und öffnet sie im Editor."""
import os
import random
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import koch, words
from morsetrainer.core.morse import MORSE_CODE
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import N_, tr
from morsetrainer.modes.content import MIN_ITEMS as MIN_PHRASES, first_lesson_with_phrases
from morsetrainer.modes.sequence_mode import COPY, FIRST_KEY_S, MEMORIZE, SequenceModeFrame
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.ui_widgets import ChoiceButtons

# Was der Reiter sendet: angezeigter (deutscher) Name → gespeicherter Wert.
# „Abkürzungen“ (words.WORDS, dazu eigene Wörter), „Klartext“ (ausgeschriebene
# Wörter, words.PLAIN_WORDS), Wendungen oder Abkürzungen gemischt mit Wendungen.
CONTENTS = {N_("Abkürzungen"): "words", N_("Klartext"): "plain", N_("Wendungen"): "phrases", N_("gemischt"): "mixed"}
# „gemischt“: so viele Sequenzen sind Wendungen, die übrigen Wörter.
# Gemischt statt eigener Wendungs-Tage: Wechsel festigt besser als Blöcke,
# und die wenigen Wendungen der ersten Lektionen lernte man sonst auswendig.
PHRASE_SHARE = 1 / 3


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
    """Reiter Wörter: Wörter, Q-Gruppen und Abkürzungen (dazu eigene Wörter
    aus woerter.txt) oder Wendungen aus dem gelernten Zeichensatz; Standard
    ist „Erst merken“, das ganze Wort hören und dann tippen."""
    session_mode = "word"
    daily_keys = (*SequenceModeFrame.daily_keys, "content")
    # Erst das ganze Wort hören, dann tippen: fördert das Wort als Klangbild
    # statt Buchstabe für Buchstabe.
    default_style = MEMORIZE
    send_prosigns = True
    # Im Wort verrät der Zusammenhang viele Buchstaben.
    char_stats = False
    intro_text = N_(
        "Es kommen CW-Abkürzungen, Q-Gruppen und Wörter aus QSOs, unter „Art“ auch ganze "
        "Wendungen – nur solche, die aus den Zeichen oben bestehen. Mit jeder Koch-Lektion werden es mehr."
    )

    def _build_extra_settings(self, parent):
        """Eigene Einstellungen des Reiters: Zahl der passenden Wörter und Knopf zum
        Bearbeiten der eigenen Wörter (woerter.txt)."""
        self.all_words = dict(words.WORDS)
        self.user_words, self.skipped = {}, []
        self.words_mtime = -1  # Änderungszeit von woerter.txt beim letzten Einlesen (None = fehlt)
        self.phrase_list, self.phrase_picker = [], None
        self.content_var = tk.StringVar(value=N_("Abkürzungen"))
        choice = ttk.Frame(parent)
        choice.pack(fill="x", pady=(0, 4))
        ttk.Label(choice, text=tr("Art:")).pack(side="left", padx=(0, 8))
        self.content_buttons = ChoiceButtons(choice, self.content_var, CONTENTS, tr("Art"))
        self.content_buttons.pack(side="left")
        self.content_var.trace_add("write", lambda *_: self._show_count())
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 4))
        self.count_var = tk.StringVar(value="")
        theme.hint(row, textvariable=self.count_var, wrap=360).pack(side="left")
        ttk.Button(row, text=tr("Eigene Wörter bearbeiten"), command=self._edit_user_words).pack(side="right")
        self.charset_var.trace_add("write", lambda *_: self._show_count())
        # Nach dem Bearbeiten im Editor: beim Zurückkehren ins Fenster neu zählen.
        self.root.bind("<FocusIn>", lambda e: self._show_count(), add="+")
        self._show_count()

    def _content(self) -> str:
        return CONTENTS.get(self.content_var.get(), "words")

    def _phrases(self) -> bool:
        return self._content() == "phrases"

    @property
    def first_key_limit(self):
        # Wendungen sind lang: ein Fenster ab Tonende maße vor allem das Tippen.
        return FIRST_KEY_S if self._phrases() or " " in self.current_sequence else None

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
        if self._phrases():
            count = len(words.phrases_for_charset(self._charset()))
            self.count_var.set(tr("Mit dem aktuellen Zeichensatz: {count} von {total} Wendungen").format(
                count=count, total=len(words.PHRASES)))
            return
        if self._content() == "plain":
            count = len(words.words_for_charset(self._charset(), words.PLAIN_WORDS))
            self.count_var.set(tr("Mit dem aktuellen Zeichensatz: {count} von {total} Wörtern").format(
                count=count, total=len(words.PLAIN_WORDS)))
            return
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
        if self._content() == "mixed":
            phrases = len(words.phrases_for_charset(self._charset()))
            text += "\n" + (tr("Dazu jede dritte Sequenz eine von {n} Wendungen").format(n=phrases)
                            if phrases >= MIN_PHRASES else tr("Für Wendungen reichen die Zeichen noch nicht."))
        self.count_var.set(text)

    def idle_hint(self) -> str:
        """Für F11 vor dem Start: die Zählzeile (wie viele Wörter bzw.
        Wendungen passen, ob Wendungen dazukommen)."""
        return self.count_var.get()

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
        self.phrase_list = []  # Wendungen, die „gemischt“ unter die Wörter mischt
        if self._phrases():
            self.words = words.phrases_for_charset(charset)
            if len(self.words) < MIN_PHRASES:
                first = first_lesson_with_phrases()
                when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
                announcer.problem(self.status_var, tr("Nur {count} Wendungen mit diesen Zeichen").format(
                    count=len(self.words)) + when + ".\n" + tr("Übe bis dahin mit Wörtern."))
                return False
            self.charset = charset
            return True
        plain = self._content() == "plain"
        pool = words.PLAIN_WORDS if plain else self.all_words
        minimum = words.PLAIN_MIN_WORDS if plain else words.MIN_WORDS
        self.words = words.words_for_charset(charset, pool)
        # Gemischt: Reichen die Wendungen nicht, kommen nur Wörter.
        if self._content() == "mixed":
            phrases = words.phrases_for_charset(charset)
            self.phrase_list = phrases if len(phrases) >= MIN_PHRASES else []
        if not words.enough_words(self.words, minimum):
            # Mit einer Handvoll Wörter stünde die Antwort fest (bei RR und UR
            # im Wechsel); dann lieber Gruppen üben.
            first = words.first_lesson_with_words(pool, minimum)
            when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
            count = sum(1 for w in self.words if len(w) > 1)
            announcer.problem(self.status_var, tr("Nur {count} Wörter mit diesen Zeichen").format(count=count)
                              + when + ".\n" + tr("Übe bis dahin mit Gruppen."))
            return False
        self.charset = charset
        return True

    def _setup_pickers(self, weighted: bool):
        # Das neueste Zeichen der Koch-Lektion bevorzugt üben.
        lesson = koch.lesson_of(self.charset)
        favor = koch.newest_char(lesson) if lesson else ""
        chars = CharPicker(self.charset, weighted, self.session_stats)
        core = words.PLAIN_CORE if self._content() == "plain" else frozenset()
        self.picker = words.WordPicker(self.words, chars, favor, boost=core)
        phrases = self.phrase_list
        self.phrase_picker = words.WordPicker(phrases, chars, favor) if phrases else None

    def _generate_sequence(self) -> str:
        if self.phrase_picker is not None and random.random() < PHRASE_SHARE:
            return self.phrase_picker.pick()
        return self.picker.pick()

    def _explain(self, sequence: str) -> str:
        content = self._content()
        if content == "phrases":
            meaning = words.PHRASES.get(sequence, "")
        elif content == "plain":
            meaning = ""
        else:
            meaning = self.all_words.get(sequence) or (words.PHRASES.get(sequence, "") if content == "mixed" else "")
        return words.shown_meaning(sequence, meaning)

    def _config_extra(self, spec, freq: float) -> dict:
        return {**super()._config_extra(spec, freq), "content": CONTENTS.get(self.content_var.get(), "words")}

    def _log_charset(self) -> str:
        return self.charset

    def settings(self) -> dict:
        """Wie SequenceModeFrame.settings(), dazu die Kennung, dass die Umstellung
        auf „Erst merken“ schon erfolgt ist."""
        data = super().settings()
        data["memorize_default"] = True  # Umstellung auf „Erst merken“ erledigt
        data["content"] = CONTENTS.get(self.content_var.get(), "words")
        return data

    def restore_settings(self, data: dict) -> None:
        """Wie SequenceModeFrame; alte Einstellungen ohne diese Kennung werden einmal
        auf „Erst merken“ umgestellt."""
        super().restore_settings(data)
        chosen = {value: key for key, value in CONTENTS.items()}.get(data.get("content"))
        if chosen:
            self.content_var.set(chosen)
        # Gespeicherte Einstellungen ohne „memorize_default“ stammen aus der
        # Zeit, als „Mitschreiben“ Standard war: einmalig auf „Erst merken“
        # umstellen, danach gilt wieder, was gespeichert ist.
        if data and not data.get("memorize_default") and self.style_var.get() == COPY:
            self.style_var.set(MEMORIZE)
            self.status_var.set(tr("Neu: Wörter jetzt mit „Erst merken“ – erst das ganze Wort hören, "
                                   "dann tippen. Umstellbar unter Eingabe."))
