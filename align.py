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


def align(expected: str, received: str) -> list[AlignOp]:
    n, m = len(expected), len(received)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if expected[i - 1] == received[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

    ops: list[AlignOp] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if expected[i - 1] == received[j - 1] else 1):
            kind = OpKind.MATCH if expected[i - 1] == received[j - 1] else OpKind.SUBSTITUTE
            ops.append(AlignOp(kind, expected[i - 1], received[j - 1], i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(AlignOp(OpKind.DELETE, expected[i - 1], None, i - 1, None))
            i -= 1
        else:
            ops.append(AlignOp(OpKind.INSERT, None, received[j - 1], None, j - 1))
            j -= 1
    ops.reverse()
    return ops