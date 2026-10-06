"""Übungsinhalte für „Hören & Sagen“ und „Kontinuierlich“: Zeichen,
Gruppen, Wörter, Wendungen, Rufzeichen und QSO-Klartext – jeweils nur aus
dem eingestellten Zeichensatz."""
import random

from morsetrainer.core import qso_text, words
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import tr
from morsetrainer.modes import callsign_mode

# Unter so vielen passenden Wendungen stünde die Antwort fest.
MIN_ITEMS = 15
MIN_CALLS = 30
# So viele QSOs werden probehalber erzeugt, um die nötigen Zeichen zu finden.
QSO_SAMPLES = 8
# Mit diesen Wörtern endet ein Abschnitt eines QSOs: Trennung, Übergabe,
# Ende (=, K, AR, KN, SK, BK).
QSO_SECTION_ENDS = {"=", "K", "+", "(", "*", "#"}
# Klartext: Der Zusammenhang verrät viele Zeichen, er zählt daher nicht für
# die Zeichenstatistik (SessionStats, char_stats). Rufzeichen zählen.
PLAIN_TEXT = {"words", "phrases", "qso", "custom"}


def qso_sections(charset: str) -> list:
    """Ein normales QSO in Abschnitten bis zum nächsten =, K, AR, KN, SK
    oder BK, etwa „UR RST 599 599 =“. Wörter mit noch nicht gelernten
    Zeichen fallen weg (wie in ItemSource)."""
    allowed = set(charset)
    sections, current = [], []
    for word in qso_text.generate_qso().text().split():
        if set(word) <= allowed:
            current.append(word)
        if word in QSO_SECTION_ENDS and current:
            sections.append(" ".join(current))
            current = []
    if current:
        sections.append(" ".join(current))
    return sections


def first_lesson_with_phrases():
    """Erste Koch-Lektion, deren Zeichen für genug Wendungen reichen, oder None."""
    from morsetrainer.core import koch
    for lesson in range(1, koch.MAX_LESSON + 1):
        if len(words.phrases_for_charset(koch.lesson_charset(lesson))) >= MIN_ITEMS:
            return lesson
    return None


class ItemSource:
    """Liefert (Text, Bedeutung) für die gewählte Inhaltsart, nur aus Zeichen
    von `charset`. Gleiche Wörter, Wendungen und Rufzeichen nicht direkt
    hintereinander.

    Arten: chars, groups, words, phrases, calls und qso (Klartext eines
    normalen QSOs, Wort für Wort; braucht alle Buchstaben und Ziffern)."""

    def __init__(self, kind: str, charset: str, group_len: int = 5, weighted: bool = False):
        self.kind = kind
        self.charset = charset
        self.group_len = group_len
        self.picker = CharPicker(charset, weighted)
        self.last = None
        self.items = []
        self.meanings = {}
        if kind == "words":
            all_words, _, _ = words.load_words()
            self.items = words.words_for_charset(charset, all_words)
            self.meanings = all_words
            self.word_picker = words.WordPicker(self.items, self.picker)
        elif kind == "phrases":
            self.items = words.phrases_for_charset(charset)
            self.meanings = words.PHRASES
        elif kind == "calls":
            calls, _ = callsign_mode.load_callsigns()
            self.items = callsign_mode.filter_calls(calls, [], set(charset))
        elif kind == "qso":
            self.qso_words = []

    def has_user_words(self) -> bool:
        """Eigene Wörter dabei (zählen nicht fürs Diplom Fluss: eine kurze
        eigene Liste wird wiedererkannt statt mitgeschrieben)."""
        return self.kind == "words" and any(item not in words.WORDS for item in self.items)

    def problem(self):
        """Grund, warum mit diesem Zeichensatz nichts Sinnvolles kommt, sonst None."""
        if not self.charset:
            return tr("Kein gültiges Zeichen im Zeichensatz!")
        if self.kind == "words" and not words.enough_words(self.items):
            return tr("Zu wenige Wörter mit diesen Zeichen – erst im Reiter Gruppen üben.")
        if self.kind == "phrases" and len(self.items) < MIN_ITEMS:
            first = first_lesson_with_phrases()
            when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
            return tr("Zu wenige Wendungen mit diesen Zeichen") + when + "."
        if self.kind == "calls" and len(self.items) < MIN_CALLS:
            if not (set(self.charset) & set("0123456789")):
                return tr("Rufzeichen brauchen eine Ziffer im Zeichensatz (ab Koch-Lektion 23).")
            return tr("Zu wenige Rufzeichen mit diesen Zeichen (callsigns.scp fehlt oder Zeichensatz zu klein).")
        if self.kind == "qso":
            needed = set()
            for _ in range(QSO_SAMPLES):
                needed |= set(qso_text.generate_qso().text().replace(" ", ""))
            missing = "".join(sorted(ch for ch in needed - set(self.charset) if ch.isalnum()))
            if missing:
                return tr("QSO-Klartext braucht alle Buchstaben und Ziffern, es fehlen noch: {missing}").format(missing=missing)
        return None

    def next(self):
        """Nächster Eintrag als (Text, Bedeutung); Wörter, Wendungen und Rufzeichen
        nicht zweimal hintereinander."""
        if self.kind in ("qso", "chars", "groups"):
            # Klartext: Wiederholungen gehören dazu; Zufallszeichen: bei
            # kleinem Zeichensatz stünde sonst die Antwort fest (K M K M …).
            text = self._draw()
            return text, self.meanings.get(text, "")
        for _ in range(20):
            text = self._draw()
            if text != self.last:
                break
        self.last = text
        return text, self.meanings.get(text, "")

    def _draw(self) -> str:
        """Ein Eintrag der gewählten Art: Zeichen, Gruppe, Wort (gewichtet), Wort
        aus einem erzeugten QSO (nur mit gelernten Zeichen) oder zufällig aus der
        Liste."""
        if self.kind == "qso":
            # Wörter mit noch nicht gelernten Satz- oder Betriebszeichen
            # (etwa <KN> vor Lektion 42) fallen weg.
            while not self.qso_words:
                allowed = set(self.charset)
                self.qso_words = [w for w in qso_text.generate_qso().text().split() if set(w) <= allowed]
            return self.qso_words.pop(0)
        if self.kind == "chars":
            return self.picker.pick()
        if self.kind == "groups":
            return self.picker.pick(self.group_len)
        if self.kind == "words":
            return self.word_picker.pick()
        return random.choice(self.items)
