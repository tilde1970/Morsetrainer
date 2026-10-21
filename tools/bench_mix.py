"""Misst die Mischzeit von BandConditions.mix je 20-ms-Block (Echtzeitfaktor).
Aufruf aus dem Projektordner:  python3 tools/bench_mix.py [Wiederholungen]
Ohne Ton, ohne Datenordner. Grenzen: Block 20 ms, Puffer 100 ms."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from morsetrainer.core.band import BandConditions  # noqa: E402
from morsetrainer.core.morse import SAMPLE_RATE  # noqa: E402

N = int(SAMPLE_RATE * 0.02)
REP = int(sys.argv[1]) if len(sys.argv) > 1 else 15
SETS = {"QSB": ["noise", "qsb", "strength"],
        "QSB+Flattern": ["noise", "qsb", "flutter", "strength"],
        "voll": ["noise", "qsb", "flutter", "strength", "qrn", "cw_qrm", "clicks", "carrier", "agc"]}


def band(n, seed, effects):
    b = BandConditions(n, seed=seed)
    for e in effects:
        b.enabled[e] = True
    b.prepare(600)
    for _ in range(5):
        b.mix([(np.full(N, 0.2, np.float32), 0)], N)  # eingelaufen
    return b


def ms(f):
    t = time.perf_counter()
    f()
    return (time.perf_counter() - t) * 1000


for name, effects in SETS.items():
    print("==", name)
    for n in (3, 6, 10, 20):
        src = [(np.full(N, 0.2, np.float32), s) for s in range(n)]
        first, one, steady = [], [], []
        for r in range(REP + 1):
            b = band(n, r, effects)
            first.append(ms(lambda: b.mix(src, N)))                      # alle n Stationen erstmals
            steady += [ms(lambda: b.mix(src, N)) for _ in range(50)]
            b2 = band(n, 100 + r, effects)
            one.append(ms(lambda: b2.mix([(src[-1][0], n - 1)], N)))     # eine neue Station
        first, one, steady = first[1:], one[1:], steady[50:]
        p = lambda a, q: float(np.percentile(a, q))  # noqa: E731
        print(f"n={n:2d} erster Block med {np.median(first):6.1f} max {max(first):6.1f} | "
              f"eine neue Station med {np.median(one):5.2f} max {max(one):5.2f} | "
              f"eingeschwungen med {np.median(steady):5.2f} p99 {p(steady, 99):5.2f} max {max(steady):5.2f} ms (Block 20 ms)")
