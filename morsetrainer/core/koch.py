"""Koch-Methode: Zeichen werden in fester Reihenfolge einzeln dazugenommen,
immer im vollen Zeichentempo. Lektion 1 sind die ersten beiden Zeichen,
jede weitere Lektion bringt ein neues dazu (Reihenfolge wie bei lcwo.net).

Weiter geht es, sobald ein Durchgang mit genug Zeichen zu mindestens
ADVANCE_ACCURACY_PCT richtig mitgeschrieben wurde."""

# Kompletter Koch-Zeichensatz in LCWO-Reihenfolge (lcwo.net).
KOCH_ORDER = "KMURESNAPTLWI.JZ=FOY,VG5/Q92H38B?47C1D60X"
MAX_LESSON = len(KOCH_ORDER) - 1

ADVANCE_ACCURACY_PCT = 90.0
# Unter so vielen gewerteten Zeichen ist die Trefferquote zu zufällig.
ADVANCE_MIN_CHARS = 50

# Zeichentempo und effektives Tempo (Farnsworth), wie Koch es empfiehlt:
# die Zeichen schnell genug, dass man sie als Klangbild hört statt
# Punkte und Striche zu zählen, dafür längere Pausen dazwischen.
RECOMMENDED_WPM = 20
RECOMMENDED_EFFECTIVE_WPM = 10


def lesson_charset(lesson: int) -> str:
    lesson = min(max(lesson, 1), MAX_LESSON)
    return KOCH_ORDER[:lesson + 1]


def lesson_of(charset: str):
    """Lektion, deren Zeichensatz genau `charset` ist, sonst None."""
    lesson = len(charset) - 1
    if 1 <= lesson <= MAX_LESSON and charset == lesson_charset(lesson):
        return lesson
    return None


def newest_char(lesson: int) -> str:
    return lesson_charset(lesson)[-1]


def can_advance(charset: str, correct: int, total: int) -> bool:
    """True, wenn `charset` eine Lektion (nicht die letzte) ist und der
    Durchgang das Kriterium erfüllt."""
    lesson = lesson_of(charset)
    return (
        lesson is not None and lesson < MAX_LESSON
        and total >= ADVANCE_MIN_CHARS
        and correct / total * 100 >= ADVANCE_ACCURACY_PCT
    )
