"""Übersetzung: Zu jedem mit tr() oder N_() markierten Text gibt es einen
englischen Eintrag mit denselben Platzhaltern, und kein Eintrag ist
verwaist. Markiert werden nur Literale (keine f-Strings)."""
import ast
import json
import os
import re
import string
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und Sprache)
from morsetrainer import i18n
from morsetrainer.core import words
from morsetrainer.i18n_en import EN, MEANINGS

PACKAGE = Path(__file__).resolve().parent.parent / "morsetrainer"


def marked_texts():
    """{Text: [Fundstellen]} aller tr("…")/N_("…") im Paket, dazu die
    Aufrufe, deren Argument kein Literal ist (erlaubt, wenn der Wert aus
    N_() stammt) als Liste unter None."""
    found = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("tr", "N_") and node.args):
                continue
            arg = node.args[0]
            where = f"{path.relative_to(PACKAGE.parent)}:{node.lineno}"
            if isinstance(arg, ast.JoinedStr):
                found.setdefault(None, []).append(f"f-String in {where}")
            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                context = next((kw.value.value for kw in node.keywords if kw.arg == "context"), "")
                found.setdefault(f"{context}|{arg.value}" if context else arg.value, []).append(where)
    return found


def placeholders(text):
    """Namen der {}-Platzhalter und ob es ein Datumsformat ist (dessen
    %-Codes dürfen sich unterscheiden, z. B. %d.%m. -> %b %d)."""
    names = {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}
    return names, bool(re.search(r"%[a-zA-Z]", text))


class TranslationTest(unittest.TestCase):
    def test_no_f_strings_are_marked(self):
        self.assertEqual(marked_texts().get(None, []), [])

    def test_every_marked_text_has_an_english_entry(self):
        missing = {text: where for text, where in marked_texts().items() if text is not None and text not in EN}
        self.assertEqual(missing, {})

    def test_no_orphaned_entries(self):
        self.assertEqual(sorted(set(EN) - set(marked_texts())), [])

    def test_placeholders_match(self):
        wrong = {de: en for de, en in EN.items() if placeholders(de) != placeholders(en)}
        self.assertEqual(wrong, {})

    def test_every_builtin_meaning_has_an_english_one(self):
        builtin = {word for word, meaning in {**words.WORDS, **words.PHRASES}.items() if meaning}
        self.assertEqual(sorted(builtin - set(MEANINGS)), [])
        self.assertEqual(sorted(set(MEANINGS) - builtin), [])

    def test_shown_meaning_keeps_own_meanings(self):
        with mock.patch.object(i18n, "LANG", "en"):
            self.assertEqual(words.shown_meaning("TNX", words.WORDS["TNX"]), "thanks")
            self.assertEqual(words.shown_meaning("TNX", "eigene Bedeutung"), "eigene Bedeutung")
            self.assertEqual(words.shown_meaning("NAME", ""), "")
        self.assertEqual(words.shown_meaning("TNX", words.WORDS["TNX"]), words.WORDS["TNX"])

    def test_tests_run_in_german(self):
        self.assertEqual(i18n.LANG, "de")
        self.assertEqual(i18n.tr("Hilfe"), "Hilfe")


class LanguageSettingTest(unittest.TestCase):
    def test_language_comes_from_window_state(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ), \
                mock.patch.object(i18n, "DATA_DIR", Path(tmp)):
            os.environ.pop("MORSETRAINER_LANG", None)
            state = Path(tmp) / "window_state.json"
            self.assertEqual(i18n._configured(), "de")  # keine Datei
            state.write_text(json.dumps({"language": "en"}), encoding="utf-8")
            self.assertEqual(i18n._configured(), "en")
            state.write_text(json.dumps({"language": "xx"}), encoding="utf-8")
            self.assertEqual(i18n._configured(), "de")
            state.write_text("kaputt", encoding="utf-8")
            self.assertEqual(i18n._configured(), "de")
            os.environ["MORSETRAINER_LANG"] = "en"
            self.assertEqual(i18n._configured(), "en")

    def test_numbers_use_the_separators_of_the_language(self):
        self.assertEqual((i18n.number(12345), i18n.number(0.38, 2)), ("12.345", "0,38"))
        with mock.patch.object(i18n, "LANG", "en"):
            self.assertEqual((i18n.number(12345), i18n.number(0.38, 2)), ("12,345", "0.38"))

    def test_short_numbers_only_show_needed_decimals(self):
        self.assertEqual([i18n.short_number(v) for v in (94.7, 100.0, 5)], ["94,7", "100", "5"])
        with mock.patch.object(i18n, "LANG", "en"):
            self.assertEqual([i18n.short_number(v) for v in (94.7, 100.0, 5)], ["94.7", "100", "5"])

    def test_context_picks_its_own_entry(self):
        with mock.patch.object(i18n, "_TABLE", EN):
            self.assertEqual(i18n.tr("Zeichen"), "Characters")
            self.assertEqual(i18n.tr("Zeichen", context="Einheit"), "characters")
            # Rolle („Ich bin: Teilnehmer“) und Überschrift der Tabelle
            self.assertEqual(i18n.tr("Teilnehmer"), "Participant")
            self.assertEqual(i18n.tr("Teilnehmer", context="Mehrzahl"), "Participants")
            self.assertEqual(i18n.tr("gibt es nicht"), "gibt es nicht")

    def test_help_uses_english_files(self):
        from morsetrainer.widgets import help_window
        for _, name in help_window.DOCS:
            self.assertTrue(help_window.doc_path(name).exists())
            self.assertEqual(help_window.doc_path(name).name, Path(name).name)
            self.assertEqual(help_window.doc_path(name, "en").name, Path(name).name.replace(".md", ".en.md"))
            self.assertTrue(help_window.doc_path(name, "en").exists())


class TkLanguageTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_choice_box_shows_english_but_keeps_german_value(self):
        from morsetrainer.widgets.ui_widgets import ChoiceBox
        with mock.patch.object(i18n, "_TABLE", EN):
            var = tk.StringVar(value="aus")
            box = ChoiceBox(self.root, var, ["aus", "selten", "oft"])
            self.assertEqual(box.get(), "off")
            self.assertEqual(list(box["values"]), ["off", "rare", "often"])
            box.set("often")  # Auswahl in der Liste
            self.assertEqual(var.get(), "oft")
            var.set("selten")  # z. B. restore_settings
            self.assertEqual(box.get(), "rare")

    def test_language_choice_is_saved(self):
        from morsetrainer import app as app_module
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(app_module, "WINDOW_STATE_FILE", Path(tmp) / "window_state.json"):
            app = app_module.MorseTrainerApp(self.root)
            self.assertEqual(app.language_hint_var.get(), "")
            app.language_box.set("English")
            app._choose_language()
            self.assertIn("Neustart", app.language_hint_var.get())
            app._save_state()
            saved = json.loads((Path(tmp) / "window_state.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["language"], "en")
            for mode in app.modes:
                mode.on_close()
