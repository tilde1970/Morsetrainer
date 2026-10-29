"""Gemeinsame Regel für mitwachsendes Tempo (Gruppen, Wörter, Rufzeichen,
QSO-Automatik).

Ein Tempo besteht aus Zeichentempo `wpm` und effektivem Tempo `fw`
(Farnsworth: längere Pausen; None = aus, dann ist das effektive Tempo das
Zeichentempo). Angepasst wird immer das effektive Tempo:

- schneller: erst die Pausen kürzer; erreicht das effektive Tempo das
  Zeichentempo, fällt Farnsworth weg und das Zeichentempo wächst weiter;
- langsamer: mit Farnsworth nur die Pausen länger; ohne Farnsworth das
  Zeichentempo, aber nicht unter MIN_CHAR_WPM – darunter übernimmt
  Farnsworth, damit die Zeichen nicht so gedehnt werden, dass man
  Punkte und Striche zählen kann."""
from morsetrainer.core.koch import SLOW_CHAR_WPM

MIN_CHAR_WPM = SLOW_CHAR_WPM
LIMITS = (5, 60)
CHARS_PER_WORD = 5  # Normwort PARIS: 1 WPM = 5 Zeichen pro Minute


def effective(wpm: int, fw) -> int:
    """Effektives Tempo; Farnsworth wirkt nur, wenn langsamer als die Zeichen."""
    return fw if fw is not None and fw < wpm else wpm


# Zeitlimit für Einzelzeichen (Sekunden ab Tonende): Tastenzeit plus die Zeit,
# die ein Zeichen im effektiven Tempo hat (CHARS_PER_WORD Zeichen je Wort).
# Die Tastenzeit (Erkennen, Taste suchen) hängt kaum vom Tempo ab; Anfänger
# brauchen mehr, bis der Zeichensatz größer wird. Schätzwerte aus den
# Reaktionszeiten eines geübten Nutzers, für Anfänger nicht gemessen.
KEY_TIME_S = 0.6
BEGINNER_KEY_TIME_S = 1.2
BEGINNER_CHARS = 10   # bis zu so vielen Zeichen gilt die Anfänger-Tastenzeit
PRACTISED_CHARS = 26  # ab so vielen die geübte, dazwischen gleitend


def key_time(charset_size: int) -> float:
    """Tastenzeit des Zeitlimits für einen Zeichensatz dieser Größe."""
    if charset_size <= BEGINNER_CHARS:
        return BEGINNER_KEY_TIME_S
    if charset_size >= PRACTISED_CHARS:
        return KEY_TIME_S
    share = (charset_size - BEGINNER_CHARS) / (PRACTISED_CHARS - BEGINNER_CHARS)
    return BEGINNER_KEY_TIME_S - share * (BEGINNER_KEY_TIME_S - KEY_TIME_S)


def char_limit(wpm: int, fw, charset_size: int) -> float:
    """Zeitlimit in Sekunden ab dem Ende des Tons für ein Zeichen: Tastenzeit
    plus Zeichenzeit im effektiven Tempo. Langsamer geübt heißt mehr Zeit."""
    per_char = 60 / (CHARS_PER_WORD * max(effective(wpm, fw), 1))
    return round(key_time(charset_size) + per_char, 2)


def step(wpm: int, fw, delta: int, limits=LIMITS):
    """(Zeichentempo, effektiv oder None) nach einer Änderung des effektiven
    Tempos um `delta` WPM."""
    target = min(max(effective(wpm, fw) + delta, limits[0]), limits[1])
    if target >= wpm:
        return target, None
    if fw is None and target >= MIN_CHAR_WPM:
        return target, None
    return wpm, target


def label(wpm: int, fw) -> str:
    """"20 WPM" oder "20/12 WPM" (Zeichen/effektiv)."""
    eff = effective(wpm, fw)
    return f"{wpm} WPM" if eff == wpm else f"{wpm}/{eff} WPM"


def cpm(wpm) -> int:
    """Zeichen pro Minute (ZpM/BpM) nach der PARIS-Norm – eine Umrechnung,
    kein Messwert: lange Zeichen (Ziffern, Q, Y) kommen bei gleichem WPM
    seltener."""
    return round(wpm * CHARS_PER_WORD)
