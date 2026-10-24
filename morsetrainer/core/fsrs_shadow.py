"""Schattenmodell nach FSRS-6 für die Lernkartei (core/review.py).

Schreibt je Zeichen Stabilität "s" (Tage) und Schwierigkeit "d" (1 bis 10)
mit, wie FSRS sie bei denselben Entscheidungen schätzen würde. Es hat keine
Wirkung: Fächer, Fälligkeit, Anzeige und Diplome kommen allein aus dem
Fach. Nach einigen Monaten lässt sich an den Daten prüfen, ob
die vorhergesagte Behaltenswahrscheinlichkeit (retrievability) am
Fälligkeitstag besser zu den Treffern passt als das Fach.

Die Gewichte sind die Standardwerte aus py-fsrs (Anki-Daten von
Faktenwissen), nicht an Morsezeichen angepasst. Bewertung (rating): 1 Again,
2 Hard, 3 Good; Easy gibt es hier nicht."""
import math

WEIGHTS = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
           1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)
AGAIN, HARD, GOOD = 1, 2, 3
MIN_STABILITY = 0.001
DECAY = -WEIGHTS[20]
FACTOR = 0.9 ** (1 / DECAY) - 1


def retrievability(elapsed_days: float, stability: float) -> float:
    """Wahrscheinlichkeit, das Zeichen nach `elapsed_days` Tagen noch zu wissen."""
    return (1 + FACTOR * max(elapsed_days, 0) / stability) ** DECAY


def _clamp_d(value: float) -> float:
    return min(max(value, 1.0), 10.0)


def _initial_d(rating: int, clamp: bool = True) -> float:
    value = WEIGHTS[4] - math.exp(WEIGHTS[5] * (rating - 1)) + 1
    return _clamp_d(value) if clamp else value


def first(rating: int) -> tuple:
    """(Stabilität, Schwierigkeit) nach der ersten Bewertung."""
    return max(WEIGHTS[rating - 1], MIN_STABILITY), _initial_d(rating)


def review(stability: float, difficulty: float, elapsed_days: float, rating: int) -> tuple:
    """(Stabilität, Schwierigkeit) nach einer Wiederholung `elapsed_days` nach der letzten."""
    w = WEIGHTS
    r = retrievability(elapsed_days, stability)
    step = -w[6] * (rating - 3)
    new_d = difficulty + step * (10 - difficulty) / 9
    new_d = _clamp_d(w[7] * _initial_d(4, clamp=False) + (1 - w[7]) * new_d)
    if rating == AGAIN:
        new_s = (w[11] * difficulty ** -w[12] * ((stability + 1) ** w[13] - 1) * math.exp((1 - r) * w[14]))
        new_s = min(new_s, stability)
    else:
        hard = w[15] if rating == HARD else 1.0
        new_s = stability * (1 + math.exp(w[8]) * (11 - difficulty) * stability ** -w[9]
                             * (math.exp((1 - r) * w[10]) - 1) * hard)
    return max(new_s, MIN_STABILITY), new_d


# Auswertung des Protokolls (review.load_log): trifft die Vorhersage der Behaltens-
# wahrscheinlichkeit den Anteil flüssiger Treffer besser als das Fach?
MIN_REPORT = 200  # unter so vielen Entscheidungen mit Vorhersage ist es zu früh für ein Urteil
BIN_EDGES = (0.0, 0.5, 0.7, 0.8, 0.9, 1.0001)
BETTER_MARGIN = 0.002  # Unterschied der Brier-Werte, ab dem ein Verfahren als besser gilt


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _mean(values) -> float:
    return sum(values) / len(values)


def report(log: list) -> dict:
    """Wertet das Protokoll aus. Ergebnis: {"entries", "predicted", "first", "last",
    "brier": {"fsrs", "box", "mean"} (None ohne Daten), "bins", "boxes", "verdict"}.
    Ergebnis der Entscheidung ist der Anteil flüssiger Treffer ("share", 0 bis 1);
    die Vorhersage "p" gibt es erst ab der zweiten Entscheidung eines Zeichens.
    "box" ist das Fach-Verfahren: Mittelwert der Anteile je Fach davor, aus
    denselben Daten berechnet, also günstig für das Fach. "mean": immer der
    Gesamtmittelwert. Urteil: "few" (zu wenig Daten), "fsrs", "box" oder "equal"."""
    entries = [e for e in log if isinstance(e, dict)]
    usable = [e for e in entries if _num(e.get("p")) and _num(e.get("share")) and isinstance(e.get("from"), int)]
    days = sorted(str(e["day"]) for e in entries if isinstance(e.get("day"), str))
    result = {"entries": len(entries), "predicted": len(usable), "first": days[0] if days else None,
              "last": days[-1] if days else None, "brier": None, "bins": [], "boxes": [], "verdict": "few"}
    if not usable:
        return result
    shares = [e["share"] for e in usable]
    overall = _mean(shares)
    by_box = {}
    for e in usable:
        by_box.setdefault(e["from"], []).append(e["share"])
    box_mean = {box: _mean(values) for box, values in by_box.items()}
    result["brier"] = {
        "fsrs": _mean([(e["p"] - e["share"]) ** 2 for e in usable]),
        "box": _mean([(box_mean[e["from"]] - e["share"]) ** 2 for e in usable]),
        "mean": _mean([(overall - s) ** 2 for s in shares]),
    }
    for low, high in zip(BIN_EDGES, BIN_EDGES[1:]):
        group = [e for e in usable if low <= e["p"] < high]
        if group:
            result["bins"].append({"low": low, "high": min(high, 1.0), "n": len(group),
                                   "p": _mean([e["p"] for e in group]), "actual": _mean([e["share"] for e in group])})
    for box in sorted(by_box):
        group = [e for e in usable if e["from"] == box]
        result["boxes"].append({"box": box, "n": len(group), "p": _mean([e["p"] for e in group]),
                                "actual": box_mean[box]})
    if len(usable) >= MIN_REPORT:
        diff = result["brier"]["box"] - result["brier"]["fsrs"]
        result["verdict"] = "fsrs" if diff > BETTER_MARGIN else "box" if diff < -BETTER_MARGIN else "equal"
    return result
