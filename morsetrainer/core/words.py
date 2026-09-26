"""Wörter für den Wörter-Modus: CW-Abkürzungen, Q-Gruppen und Wörter, wie
sie in QSOs vorkommen. Zu Abkürzungen gibt es eine kurze Bedeutung, die
nach der Antwort angezeigt wird ("" = selbsterklärend).

Gesendet werden nur Wörter, die ausschließlich aus Zeichen des
eingestellten Zeichensatzes bestehen; so gibt es schon in frühen
Koch-Lektionen etwas zu hören.

Eigene Wörter stehen in woerter.txt im Datenverzeichnis (siehe
load_words) und kommen zu den eingebauten dazu."""
import random
import statistics
from pathlib import Path

from morsetrainer import DATA_DIR
from morsetrainer.core.morse import MORSE_CODE

USER_WORDS_FILE = DATA_DIR / "woerter.txt"

USER_WORDS_TEMPLATE = """\
# Eigene Wörter für den Reiter „Wörter“ im Morsetrainer.
#
# Ein Wort pro Zeile, optional mit Bedeutung nach dem ersten „=“, die nach
# der Antwort angezeigt wird. Zeilen mit # sind Kommentare. Groß- und
# Kleinschreibung ist egal, Ä/Ö/Ü/ß werden zu AE/OE/UE/SS. Wörter mit
# Leerzeichen oder Zeichen, die es nicht im Morsecode gibt, werden
# übersprungen. Die Wörter kommen zu den eingebauten dazu; steht hier ein
# eingebautes Wort mit Bedeutung, gilt deine Bedeutung.
#
# Nach dem Speichern den Durchgang neu starten.
#
# Beispiele:
# DOK = Distrikts-Ortsverbandskenner
# DARC = Deutscher Amateur-Radio-Club
# UFB = ultra fine business – super
"""

_UMLAUTS = str.maketrans({"Ä": "AE", "Ö": "OE", "Ü": "UE", "ß": "SS", "ẞ": "SS"})

WORDS = {
    # Q-Gruppen
    "QRG": "Frequenz", "QRL": "beschäftigt / Frequenz belegt? (auch: Arbeit)", "QRM": "Störungen durch andere Stationen",
    "QRN": "atmosphärische Störungen", "QRO": "hohe Leistung", "QRP": "kleine Leistung",
    "QRQ": "schneller geben", "QRS": "langsamer geben", "QRT": "Sendeschluss",
    "QRU": "nichts mehr für dich", "QRV": "bereit", "QRX": "bitte warten",
    "QRZ": "wer ruft?", "QSB": "Schwund (Fading)", "QSK": "Mithören zwischen den Zeichen",
    "QSL": "Bestätigung", "QSO": "Funkverbindung", "QSY": "Frequenzwechsel",
    "QTH": "Standort", "QTR": "Uhrzeit",
    # Abkürzungen
    "ABT": "about – ungefähr", "AGN": "again – nochmal", "ANT": "antenna – Antenne",
    "BK": "break – Umschalten", "CFM": "confirm – bestätige", "CL": "closing – schließe die Station",
    "CPY": "copy – aufnehmen", "CQ": "allgemeiner Anruf", "CUAGN": "see you again – auf Wiederhören",
    "CUL": "see you later – bis später", "DE": "von", "DR": "dear – lieber",
    "ES": "und", "FB": "fine business – prima", "FER": "for – für", "GA": "good afternoon",
    "GB": "goodbye", "GD": "guten Tag", "GE": "good evening", "GL": "good luck – viel Glück",
    "GM": "good morning", "GN": "good night", "HI": "Lachen", "HR": "here – hier",
    "HW": "how – wie (aufgenommen)?", "MNI": "many – viele", "NR": "number / near – Nummer / nahe bei",
    "NW": "now – jetzt", "OM": "old man – Funkfreund", "OP": "operator – Funker",
    "PSE": "please – bitte", "PWR": "power – Leistung", "RIG": "Funkgerät",
    "RPT": "repeat/report – wiederholen/Rapport", "RST": "Rapport (Lesbarkeit, Stärke, Ton)",
    "SIG": "signal", "SRI": "sorry – Entschuldigung", "TEMP": "Temperatur",
    "TKS": "thanks – danke", "TNX": "thanks – danke", "TU": "thank you – danke",
    "UR": "your/you are – dein/du bist", "VY": "very – sehr", "WX": "weather – Wetter",
    "XYL": "Ehefrau", "YL": "young lady – Funkerin", "73": "viele Grüße",
    "88": "Liebe und Küsse", "5NN": "Rapport 599 (gekürzt)", "599": "bester Rapport",
    "TEST": "Contest-Anruf", "UP": "höher auf der Frequenz hören", "NIL": "nichts",
    "OK": "", "RR": "roger – verstanden", "RE": "regarding – betreffend",
    # Wörter aus typischen QSOs
    "NAME": "", "HERE": "", "THE": "", "AND": "", "ARE": "", "IS": "", "AT": "", "IN": "",
    "ON": "", "TO": "", "FOR": "", "MY": "", "ME": "", "SO": "", "NO": "", "SURE": "",
    "NICE": "", "GOOD": "", "FINE": "", "MEET": "", "WELL": "", "SUN": "", "SUNNY": "",
    "RAIN": "", "WARM": "", "COLD": "", "WIND": "", "SNOW": "", "CLOUDY": "", "HOT": "",
    "WIRE": "", "DIPOLE": "", "YAGI": "", "VERT": "vertical – Vertikalantenne",
    "KEY": "Taste", "BUG": "halbautomatische Taste", "PADDLE": "Paddle",
    "WATT": "", "WATTS": "", "BAND": "", "MTR": "meter", "MTRS": "meters",
    "LOG": "", "CARD": "", "BURO": "QSL-Büro", "DIRECT": "", "LOTW": "Logbook of the World",
    "SWL": "Kurzwellenhörer", "RX": "receiver – Empfänger", "TX": "transmitter – Sender",
    "TRX": "Transceiver", "ALL": "", "NOT": "", "BUT": "", "NEW": "", "OLD": "",
    "YEARS": "", "AGE": "", "JOB": "", "RETIRED": "", "HOME": "", "TOWN": "", "CITY": "",
    "NEAR": "", "WORK": "", "SEE": "", "HOPE": "", "SOON": "", "TIME": "", "LATE": "",
    "EARLY": "", "BEST": "", "WISHES": "", "PSED": "pleased – erfreut", "QRPP": "sehr kleine Leistung",
    "TMW": "tomorrow – morgen", "TDY": "today – heute", "YR": "year – Jahr",
    "BCNU": "be seeing you – bis bald", "ENUF": "enough – genug", "WKD": "worked – gearbeitet",
    "WL": "well/will", "WPM": "words per minute", "INFO": "", "SPEED": "",
}


def parse_user_words(text: str) -> tuple[dict, list[str]]:
    """Liest den Inhalt von woerter.txt: ({Wort: Bedeutung}, übersprungene
    Zeilen)."""
    found, skipped = {}, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        word, _, note = line.partition("=")
        word = word.strip().upper().translate(_UMLAUTS)
        if word and all(ch in MORSE_CODE for ch in word):
            found[word] = note.strip()
        else:
            skipped.append(line)
    return found, skipped


def load_words(path: Path = None) -> tuple[dict, dict, list[str]]:
    """Eingebaute plus eigene Wörter: ({Wort: Bedeutung} gesamt, nur die
    eigenen, übersprungene Zeilen). Fehlt die Datei, gibt es nur die
    eingebauten."""
    try:
        text = (path or USER_WORDS_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return dict(WORDS), {}, []
    user, skipped = parse_user_words(text)
    combined = dict(WORDS)
    for word, note in user.items():
        if note or word not in combined:
            combined[word] = note
    return combined, user, skipped


def ensure_user_file(path: Path = None) -> Path:
    """Legt woerter.txt mit Anleitung an, falls es sie noch nicht gibt."""
    path = path or USER_WORDS_FILE
    if not path.exists():
        path.write_text(USER_WORDS_TEMPLATE, encoding="utf-8")
    return path


def words_for_charset(charset: str, words=WORDS) -> list[str]:
    """Alle Wörter aus `words`, die nur aus Zeichen von `charset` bestehen."""
    allowed = set(charset)
    return sorted(w for w in words if set(w) <= allowed)


class WordPicker:
    """Wählt Wörter zufällig oder, gewichtet, bevorzugt solche mit
    schwachen Zeichen (Gewichte vom CharPicker). Dasselbe Wort kommt nicht
    zweimal direkt hintereinander, sofern es mehr als eins gibt."""

    CANDIDATES = 12

    def __init__(self, words, char_picker=None):
        self.words = list(words)
        self.char_picker = char_picker
        self.last = None

    def pick(self) -> str:
        pool = [w for w in self.words if w != self.last] or self.words
        if self.char_picker is None or not self.char_picker.weighted:
            word = random.choice(pool)
        else:
            weight = dict(zip(self.char_picker.charset, self.char_picker.weights()))
            candidates = random.sample(pool, min(self.CANDIDATES, len(pool)))
            scores = [statistics.mean(weight[ch] for ch in w) for w in candidates]
            word = random.choices(candidates, weights=scores)[0]
        self.last = word
        return word
