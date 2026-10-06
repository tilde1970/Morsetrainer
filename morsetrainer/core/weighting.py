"""Gewichtete Zeichenauswahl: Zeichen, die du oft falsch oder nur langsam
erkennst, kommen häufiger dran. Grundlage sind die Werte pro Zeichen aus
der Gesamtstatistik (core/stats.py) plus der laufenden Sitzung.

Fehler: Die Fehlerquote wird mit (falsch + 1) / (gesamt + 2) geglättet,
damit neue oder selten geübte Zeichen nicht bei 0 % oder 100 % landen –
ein noch nie geübtes Zeichen startet bei 50 %.

Tempo: Verglichen wird die mittlere Latenz (Tonende bis Tastendruck, nur
richtige Antworten) eines Zeichens mit dem Median über den Zeichensatz.
Wer für ein Zeichen doppelt so lange wie üblich braucht, bekommt den
vollen Zuschlag SPEED_WEIGHT; schneller als der Median gibt keinen Abzug.
Erst ab MIN_LATENCY_SAMPLES Messungen zählt das Tempo eines Zeichens.

Auf alles kommt ein Grundgewicht MIN_WEIGHT, damit auch sicher
beherrschte Zeichen weiter vorkommen: ein Zeichen mit 50 % Fehlern kommt
dadurch rund 6-mal so oft wie eines, das nie falsch war und im üblichen
Tempo erkannt wird.

Heute fällige Zeichen der Lernkartei (core/review.py) zählen zusätzlich
doppelt (review.DUE_FACTOR), beim gezielten Üben vierfach
(review.FOCUS_FACTOR)."""
import random
import statistics

from morsetrainer.core import review, stats

MIN_WEIGHT = 0.1
SPEED_WEIGHT = 0.5
MIN_LATENCY_SAMPLES = 3


class CharPicker:
    """Wählt das nächste Zeichen aus `charset`: gleichverteilt oder, mit
    `weighted`, schwache Zeichen öfter (Fehlerquote, langsame Antworten, fällig
    in der Lernkartei)."""
    def __init__(self, charset: str, weighted: bool, session=None):
        """`session` ist die laufende SessionStats; deren Ergebnisse fließen
        sofort mit ein (in die Gesamtstatistik kommen sie erst beim Beenden)."""
        self.charset = charset
        self.weighted = weighted
        self.session = session
        self.all_time = stats.load_all_time() if weighted else {}
        # Heute fällig in der Lernkartei (core/review.py): öfter dran.
        self.due = set(review.due_chars()) if weighted else set()

    def _session_chars(self):
        return self.session.per_char if self.session is not None else {}

    def _error_rate(self, ch: str) -> float:
        good = wrong = 0
        for source in (self.all_time, self._session_chars()):
            e = source.get(ch)
            if e:
                good += e["good"]
                wrong += e["wrong"]
        return (wrong + 1) / (good + wrong + 2)

    def _mean_latency(self, ch: str, measured_only=False):
        """Mittlere Latenz eines Zeichens. `measured_only`: ohne die für
        unsichere Antworten angenommenen Werte (die hängen selbst am Median
        und trieben ihn sonst Durchgang für Durchgang hoch)."""
        total, count = 0.0, 0
        e = self.all_time.get(ch)
        if e:
            total += e.get("total_latency_s", 0.0)
            count += e.get("latency_count", 0)
            if measured_only:
                total -= e.get("assumed_latency_s", 0.0)
                count -= e.get("assumed_latency_count", 0)
        e = self._session_chars().get(ch)
        if e:
            total += sum(e["latencies"])
            count += len(e["latencies"])
            if measured_only:
                total -= sum(e.get("assumed_latencies", ()))
                count -= len(e.get("assumed_latencies", ()))
        return total / count if count >= MIN_LATENCY_SAMPLES else None

    def median_latency(self):
        """Median der gemessenen mittleren Latenzen über den Zeichensatz, oder
        None, solange kein Zeichen genug Messungen hat. Maßstab sowohl für
        die Langsamkeit als auch für die Latenz unsicherer Antworten."""
        known = [lat for lat in (self._mean_latency(ch, measured_only=True) for ch in self.charset)
                 if lat is not None]
        return statistics.median(known) if known else None

    def weights(self):
        """Gewicht je Zeichen in der Reihenfolge von `charset`: Grundgewicht plus
        Fehlerquote, plus Zuschlag für Antworten langsamer als der Median, mal
        Faktor für fällige bzw. gezielt geübte Zeichen."""
        latencies = {ch: self._mean_latency(ch) for ch in self.charset}
        median = self.median_latency() or 0.0

        weights = []
        for ch in self.charset:
            weight = MIN_WEIGHT + self._error_rate(ch)
            lat = latencies[ch]
            if lat is not None and median > 0:
                slowness = min(max((lat - median) / median, 0.0), 1.0)
                weight += SPEED_WEIGHT * slowness
            if ch in review.focus:
                weight *= review.FOCUS_FACTOR
            elif ch in self.due:
                weight *= review.DUE_FACTOR
            weights.append(weight)
        return weights

    def pick(self, k: int = 1, exclude: str = "") -> str:
        """`exclude`: Zeichen, die gerade nicht gezogen werden sollen (bleibt
        dann keins übrig, zählt es nicht)."""
        pairs = [(ch, w) for ch, w in zip(self.charset, self._all_weights()) if ch not in exclude]
        if not pairs:
            pairs = list(zip(self.charset, self._all_weights()))
        chars, weights = zip(*pairs)
        return "".join(random.choices(chars, weights=weights, k=k))

    def _all_weights(self):
        return self.weights() if self.weighted else [1.0] * len(self.charset)