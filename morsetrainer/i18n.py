"""Sprache der Oberfläche: Deutsch oder Englisch.

Die deutschen Texte stehen im Code und sind zugleich die Schlüssel: tr()
schlägt sie in i18n_en.EN nach. Texte, die erst später übersetzt werden
(Beschriftungen in Tabellen auf Modulebene, Werte von Klapplisten),
markiert N_() nur; tests/test_i18n.py sammelt beide und prüft, dass es zu
jedem eine Übersetzung mit denselben Platzhaltern gibt.

Werte, die gespeichert werden (Einstellungen in window_state.json,
Klapplisten, Reiternamen), bleiben intern deutsch; übersetzt wird nur die
Anzeige. So gehen beim Umschalten keine Einstellungen verloren.

Die Sprache steht beim Import fest und gilt bis zum Programmende; die
Einstellung (window_state.json, Schlüssel "language") wirkt ab dem nächsten
Start. MORSETRAINER_LANG hat Vorrang (die Tests laufen damit auf Deutsch)."""
import json
import os

from morsetrainer import DATA_DIR

LANGUAGES = {"de": "Deutsch", "en": "English"}
DEFAULT = "de"
SETTING_KEY = "language"


def _configured() -> str:
    lang = os.environ.get("MORSETRAINER_LANG")
    if lang is None:
        try:
            lang = json.loads((DATA_DIR / "window_state.json").read_text(encoding="utf-8")).get(SETTING_KEY)
        except (OSError, ValueError, AttributeError):
            lang = None
    return lang if lang in LANGUAGES else DEFAULT


LANG = _configured()

if LANG == "en":
    from morsetrainer.i18n_en import EN as _TABLE
else:
    _TABLE = {}


def tr(text: str, context: str = "") -> str:
    """`text` in der eingestellten Sprache; fehlt eine Übersetzung, bleibt
    der deutsche Text stehen. `context` unterscheidet gleiche deutsche
    Texte, die im Englischen verschieden heißen („Zeichen“ als Überschrift
    und als Einheit); der Eintrag heißt dann „<context>|<text>“."""
    return _TABLE.get(f"{context}|{text}" if context else text, text)


def N_(text: str) -> str:
    """Markiert `text` zum Übersetzen, ohne es schon zu übersetzen."""
    return text


def number(value, decimals=None) -> str:
    """Zahl mit den Trennzeichen der Sprache: 1234 -> „1.234“ bzw. „1,234“,
    number(1.2, 2) -> „1,20“ bzw. „1.20“."""
    text = f"{value:,}" if decimals is None else f"{value:,.{decimals}f}"
    return text if LANG == "en" else text.translate(str.maketrans(",.", ".,"))


def short_number(value) -> str:
    """Wie f"{value:g}" (Nachkommastellen nur, wenn nötig), mit dem
    Dezimalzeichen der Sprache: 94.7 -> „94,7“ bzw. „94.7“, 100.0 -> „100“."""
    text = f"{value:g}"
    return text if LANG == "en" else text.replace(".", ",")
