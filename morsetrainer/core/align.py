"""Levenshtein-based alignment between an expected and a received character
sequence, used by the continuous training mode to figure out which sent
characters were copied correctly, misheard, or missed entirely, even if the
trainee falls behind or skips a character (analogous to align_chars in
WZab/morse_trainer's morse_trainer_cont.py, reimplemented directly on plain
strings)."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OpKind(Enum):
    MATCH = "match"
    SUBSTITUTE = "substitute"
    DELETE = "delete"   # in `expected` but missing from `received` (missed)
    INSERT = "insert"   # in `received` but not in `expected` (stray keystroke)


@dataclass
class AlignOp:
    kind: OpKind
    expected_char: Optional[str]
    received_char: Optional[str]
    expected_index: Optional[int]
    received_index: Optional[int]


# Breite des Bands um die Diagonale (in Zeichen, zusätzlich zum
# Längenunterschied). Wer mitschreibt, liegt nie weiter daneben; so wächst
# der Aufwand nur linear mit der Länge statt quadratisch.
BAND = 50


def align(expected: str, received: str) -> list[AlignOp]:
    """Levenshtein-Alignment, berechnet in einem Band um die Diagonale von
    (0, 0) nach (len(expected), len(received)). Solange die optimale
    Zuordnung im Band liegt, ist das Ergebnis dasselbe wie ohne Band."""
    n, m = len(expected), len(received)
    band = BAND + abs(n - m)
    inf = n + m + 1
    # Zeile i umfasst die Spalten lo[i] .. lo[i] + len(rows[i]) - 1.
    lo, rows = [], []
    for i in range(n + 1):
        center = round(i * m / n) if n else 0
        first, last = max(0, center - band), min(m, center + band)
        lo.append(first)
        rows.append([inf] * (last - first + 1))

    def cell(i, j):
        k = j - lo[i]
        return rows[i][k] if 0 <= k < len(rows[i]) else inf

    for j in range(len(rows[0])):
        rows[0][j] = j
    for i in range(1, n + 1):
        row, first = rows[i], lo[i]
        prev, prev_first = rows[i - 1], lo[i - 1]
        prev_len = len(prev)
        exp_char = expected[i - 1]
        for k in range(len(row)):
            j = first + k
            if j == 0:
                row[k] = i
                continue
            pk = j - prev_first
            up = prev[pk] if 0 <= pk < prev_len else inf
            diag = prev[pk - 1] if 0 <= pk - 1 < prev_len else inf
            left = row[k - 1] if k > 0 else inf
            row[k] = min(up + 1, left + 1, diag + (exp_char != received[j - 1]))

    ops: list[AlignOp] = []
    i, j = n, m
    while i > 0 or j > 0:
        here = cell(i, j)
        if i > 0 and j > 0 and here == cell(i - 1, j - 1) + (0 if expected[i - 1] == received[j - 1] else 1):
            kind = OpKind.MATCH if expected[i - 1] == received[j - 1] else OpKind.SUBSTITUTE
            ops.append(AlignOp(kind, expected[i - 1], received[j - 1], i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and here == cell(i - 1, j) + 1:
            ops.append(AlignOp(OpKind.DELETE, expected[i - 1], None, i - 1, None))
            i -= 1
        else:
            ops.append(AlignOp(OpKind.INSERT, None, received[j - 1], None, j - 1))
            j -= 1
    ops.reverse()
    return ops

def char_results(expected: str, received: str) -> list[tuple[str, str, Optional[int]]]:
    """Pro gesendetem Zeichen (expected_char, getipptes Zeichen oder "" wenn
    ausgelassen, Index im getippten Text oder None). Überzählige getippte
    Zeichen gehören zu keinem gesendeten und fehlen daher."""
    return [
        (op.expected_char, op.received_char or "", op.received_index)
        for op in align(expected, received)
        if op.kind != OpKind.INSERT
    ]


def diff_rows(expected: str, received: str) -> tuple[str, str, str]:
    """Drei gleich lange Zeilen zum Untereinanderschreiben: gesendet,
    getippt und "^" unter jeder falschen Stelle. Lücken sind "–"."""
    sent_row, typed_row, marks = [], [], []
    for op in align(expected, received):
        sent_row.append(op.expected_char or "–")
        typed_row.append(op.received_char or "–")
        marks.append(" " if op.kind == OpKind.MATCH else "^")
    return " ".join(sent_row), " ".join(typed_row), " ".join(marks).rstrip()
