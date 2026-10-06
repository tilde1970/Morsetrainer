"""Koch-Methode: Zeichen werden in fester Reihenfolge einzeln dazugenommen,
immer im vollen Zeichentempo. Lektion 1 sind die ersten beiden Zeichen,
jede weitere Lektion bis 40 bringt ein neues dazu (Reihenfolge wie bei
lcwo.net). Lektion 41 schließt ab: alle Zeichen, keins mehr bevorzugt.
Die Betriebszeichen AR, KN, SK und BK folgen auf Wunsch in den Lektionen
42–45; dorthin wird nicht von selbst weitergeschaltet.

Weiter geht es, sobald ein Durchgang mit genug Zeichen zu mindestens
ADVANCE_ACCURACY_PCT richtig mitgeschrieben wurde."""

# Kompletter Koch-Zeichensatz in LCWO-Reihenfolge (lcwo.net).
LCWO_ORDER = "KMURESNAPTLWI.JZ=FOY,VG5/Q92H38B?47C1D60X"
# Betriebszeichen der Lektionen 42–45 (Platzhalter siehe morse.PROSIGN_KEYS).
PROSIGN_ORDER = "+(*#"
KOCH_ORDER = LCWO_ORDER + PROSIGN_ORDER
LCWO_LESSONS = len(LCWO_ORDER) - 1          # 40
FINAL_LESSON = LCWO_LESSONS + 1             # 41: Abschluss, letzte Lektion mit Aufstieg
MAX_LESSON = FINAL_LESSON + len(PROSIGN_ORDER)
# Lektion 41 hat dieselben Zeichen wie 40, nur sortiert: So bleibt sie am
# Zeichensatz erkennbar, und im Feld „Zeichen“ steht alles übersichtlich.
FINAL_CHARSET = "".join(sorted(LCWO_ORDER, key=lambda ch: (not ch.isalpha(), not ch.isdigit(), ch)))

ADVANCE_ACCURACY_PCT = 90.0
# Unter so vielen gewerteten Zeichen ist die Trefferquote zu zufällig.
ADVANCE_MIN_CHARS = 50

# Zeichentempo und effektives Tempo (Farnsworth), wie Koch es empfiehlt:
# die Zeichen schnell genug, dass man sie als Klangbild hört statt
# Punkte und Striche zu zählen, dafür längere Pausen dazwischen.
RECOMMENDED_WPM = 20
RECOMMENDED_EFFECTIVE_WPM = 10
# Darunter lassen sich die Punkte und Striche eines Zeichens mitzählen; dann
# lieber schnelle Zeichen mit Farnsworth-Pausen.
SLOW_CHAR_WPM = RECOMMENDED_WPM - 2


def lesson_charset(lesson: int) -> str:
    """Zeichensatz einer Koch-Lektion (1 … MAX_LESSON): Lektion n bringt
    n + 1 Zeichen, die Abschlusslektion alle sortiert, die Lektionen danach
    die Betriebszeichen dazu."""
    lesson = min(max(lesson, 1), MAX_LESSON)
    if lesson == FINAL_LESSON:
        return FINAL_CHARSET
    if lesson > FINAL_LESSON:
        return KOCH_ORDER[:lesson]
    return KOCH_ORDER[:lesson + 1]


def lesson_of(charset: str):
    """Lektion, deren Zeichensatz genau `charset` ist, sonst None."""
    return next((n for n in range(1, MAX_LESSON + 1) if charset == lesson_charset(n)), None)


def newest_char(lesson: int) -> str:
    """Das Zeichen, das die Lektion neu bringt; in Lektion 41 keins ("")."""
    if lesson == FINAL_LESSON:
        return ""
    return lesson_charset(lesson)[-1]


def passed(correct: int, total: int) -> bool:
    """Durchgang mit genug Zeichen und mindestens ADVANCE_ACCURACY_PCT."""
    return total >= ADVANCE_MIN_CHARS and correct / total * 100 >= ADVANCE_ACCURACY_PCT


def can_advance(charset: str, correct: int, total: int) -> bool:
    """True, wenn der Durchgang das Kriterium erfüllt und `charset` eine
    Lektion mit Nachfolger ist: vor der Abschlusslektion 41 oder unter den
    Betriebszeichen-Lektionen 42–44. Von 41 zu den Betriebszeichen geht es
    nur von Hand; wer dort angefangen hat, bekommt sie danach einzeln."""
    lesson = lesson_of(charset)
    return (lesson is not None and lesson != FINAL_LESSON and lesson < MAX_LESSON
            and passed(correct, total))
