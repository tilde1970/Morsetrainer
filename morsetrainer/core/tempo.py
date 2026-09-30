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
