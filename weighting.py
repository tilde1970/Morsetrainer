"""Gewichtete Zeichenauswahl: Zeichen, die du oft falsch oder nur langsam
erkennst, kommen häufiger dran. Grundlage sind die Werte pro Zeichen aus
der Gesamtstatistik (stats/all_time.json) plus der laufenden Sitzung.

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
Tempo erkannt wird."""
import random
import statistics

import stats

MIN_WEIGHT = 0.1
SPEED_WEIGHT = 0.5
MIN_LATENCY_SAMPLES = 3


class CharPicker:
    def __init__(self, charset: str, weighted: bool, session=None):
        """`session` ist die laufende SessionStats; deren Ergebnisse fließen
        sofort mit ein (sie landen erst beim Beenden in all_time.json)."""
        self.charset = charset
        self.weighted = weighted
        self.session = session
        self.all_time = stats.load_all_time() if weighted else {}

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

    def _mean_latency(self, ch: str):
        total, count = 0.0, 0
        e = self.all_time.get(ch)
        if e:
            total += e.get("total_latency_s", 0.0)
            count += e.get("latency_count", 0)
        e = self._session_chars().get(ch)
        if e:
            total += sum(e["latencies"])
            count += len(e["latencies"])
        return total / count if count >= MIN_LATENCY_SAMPLES else None

    def weights(self):
        latencies = {ch: self._mean_latency(ch) for ch in self.charset}
        known = [lat for lat in latencies.values() if lat is not None]
        median = statistics.median(known) if known else 0.0

        weights = []
        for ch in self.charset:
            weight = MIN_WEIGHT + self._error_rate(ch)
            lat = latencies[ch]
            if lat is not None and median > 0:
                slowness = min(max((lat - median) / median, 0.0), 1.0)
                weight += SPEED_WEIGHT * slowness
            weights.append(weight)
        return weights

    def pick(self, k: int = 1) -> str:
        if not self.weighted:
            return "".join(random.choice(self.charset) for _ in range(k))
        return "".join(random.choices(self.charset, weights=self.weights(), k=k))