"""Übungsinhalte für „Hören & Sagen“ und „Kontinuierlich“: Zeichen,
Gruppen, Wörter, Wendungen, Rufzeichen und QSO-Klartext – jeweils nur aus
dem eingestellten Zeichensatz."""
import random
from datetime import date

from morsetrainer.core import qso_text, words
from morsetrainer.core.weighting import CharPicker
from morsetrainer.i18n import N_, tr
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
PLAIN_TEXT = {"words", "plain", "phrases", "qso", "custom", "numbers"}

# Zahlen: so viele Ziffern müssen gelernt sein, damit es genug Auswahl gibt.
MIN_NUMBER_DIGITS = 4
# Telegrafieteile der Kurzwellenbänder in kHz (IARU-Region-1-Bandplan, Stand Juni 2016).
BAND_RANGES_KHZ = ((3500, 3570), (7000, 7040), (10100, 10130), (14000, 14070), (18068, 18095),
                   (21000, 21070), (24890, 24915), (28000, 28070))
WATTS = (5, 10, 20, 50, 100, 200, 400, 750, 1000)


def _frequency_khz() -> str:
    return str(random.randint(*random.choice(BAND_RANGES_KHZ)))


def _frequency_mhz() -> str:
    return f"{random.randint(*random.choice(BAND_RANGES_KHZ)) / 1000:.3f}"


def _short_number() -> str:
    """Kurzzahl wie im Contest: 5NN für 599, T für 0 (TT7 = 007)."""
    return "5NN" if random.random() < 0.4 else qso_text.cut_number(random.randint(1, 99))


# Zahlen, wie sie im Funk vorkommen: (Gewicht, Erzeuger, Bedeutung). Die
# Bedeutung steht nach dem Üben in der Legende; die MHz-Schreibweise braucht
# den Punkt unter den gelernten Zeichen.
NUMBER_KINDS = (
    (5, lambda: random.choices(list(qso_text.RST_WEIGHTS), weights=list(qso_text.RST_WEIGHTS.values()))[0],
     N_("Rapport")),
    (3, lambda: str(random.randint(1, 40)), N_("CQ-Zone")),
    (4, lambda: str(random.randint(1, 999)), N_("Seriennummer")),
    (4, _frequency_khz, N_("Frequenz in kHz")),
    (2, _frequency_mhz, N_("Frequenz in MHz")),
    (2, lambda: str(random.choice(WATTS)), N_("Leistung in Watt")),
    (2, lambda: f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}", N_("Uhrzeit in UTC")),
    (3, _short_number, N_("Kurzzahl (5NN = 599, T = 0)")),
    (1, lambda: str(random.randint(1950, date.today().year)), N_("Jahr")),
)


def first_lesson_with_digits(count: int = MIN_NUMBER_DIGITS):
    """Erste Koch-Lektion mit mindestens `count` Ziffern, oder None."""
    from morsetrainer.core import koch
    return next((lesson for lesson in range(1, koch.MAX_LESSON + 1)
                 if sum(ch.isdigit() for ch in koch.lesson_charset(lesson)) >= count), None)


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

    Arten: chars, groups, words, phrases, calls, numbers (Zahlen wie Rapport,
    Zone, Frequenz mit ihrer Bedeutung) und qso (Klartext eines normalen
    QSOs, Wort für Wort; braucht alle Buchstaben und Ziffern)."""

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
        elif kind == "plain":
            self.items = words.words_for_charset(charset, words.PLAIN_WORDS)
            self.word_picker = words.WordPicker(self.items, self.picker, boost=words.PLAIN_CORE)
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
        minimum = words.PLAIN_MIN_WORDS if self.kind == "plain" else words.MIN_WORDS
        if self.kind in ("words", "plain") and not words.enough_words(self.items, minimum):
            return tr("Zu wenige Wörter mit diesen Zeichen – erst mit Gruppen üben.")
        if self.kind == "phrases" and len(self.items) < MIN_ITEMS:
            first = first_lesson_with_phrases()
            when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
            return tr("Zu wenige Wendungen mit diesen Zeichen") + when + "."
        if self.kind == "calls" and len(self.items) < MIN_CALLS:
            if not (set(self.charset) & set("0123456789")):
                return tr("Rufzeichen brauchen eine Ziffer im Zeichensatz (ab Koch-Lektion 23).")
            return tr("Zu wenige Rufzeichen mit diesen Zeichen (callsigns.scp fehlt oder Zeichensatz zu klein).")
        if self.kind == "numbers" and sum(ch.isdigit() for ch in self.charset) < MIN_NUMBER_DIGITS:
            first = first_lesson_with_digits()
            when = tr(" – genug gibt es ab Koch-Lektion {lesson}").format(lesson=first) if first else ""
            return tr("Zahlen brauchen mindestens vier Ziffern im Zeichensatz") + when + "."
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
        if self.kind == "numbers":
            for _ in range(20):
                text, meaning = self._number()
                if text != self.last:
                    break
            self.last = text
            return text, meaning
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

    def _number(self):
        """Eine Zahl mit ihrer Bedeutung, nur aus gelernten Zeichen; fehlt zu
        vielen Arten ein Zeichen, kommen Zufallsziffern."""
        allowed = set(self.charset)
        for _ in range(60):
            _, make, meaning = random.choices(NUMBER_KINDS, weights=[kind[0] for kind in NUMBER_KINDS])[0]
            text = make()
            if set(text) <= allowed:
                return text, tr(meaning)
        digits = "".join(ch for ch in self.charset if ch.isdigit())
        return "".join(random.choice(digits) for _ in range(3)), tr("Zahl")

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
        if self.kind in ("words", "plain"):
            return self.word_picker.pick()
        return random.choice(self.items)
