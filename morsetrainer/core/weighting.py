"""Gewichtete Zeichenauswahl: Zeichen, die du oft falsch oder nur langsam
erkennst, kommen häufiger dran. Grundlage sind die Werte pro Zeichen aus
der Gesamtstatistik (core/stats.py) plus der laufenden Sitzung.

Fehler: Die Fehlerquote stammt vor allem aus den letzten RECENT_DAYS Tagen;
was davor war, zählt nur mit OLD_WEIGHT (ein Zeichen, das inzwischen sitzt,
soll nicht ewig bevorzugt werden, ein neu schwaches soll bald auffallen).
Sie wird mit (falsch + 1) / (gesamt + 2) geglättet,
damit neue oder selten geübte Zeichen nicht bei 0 % oder 100 % landen –
ein noch nie geübtes Zeichen startet bei 50 %. Hat ein Zeichen zuletzt
mindestens MIN_RECENT_ATTEMPTS Antworten, gilt mindestens die Quote dieser
letzten Antworten: Auch ein Zeichen mit vielen alten richtigen Antworten
fällt auf, wenn es jetzt wackelt.

Verwechslungen: Wurde ein Zeichen oft für ein anderes gehalten, bekommt auch
das andere einen Zuschlag (PARTNER_WEIGHT mal Anteil der Verwechslungen), denn
nur im Vergleich lässt sich der Unterschied lernen.

Tempo: Verglichen wird die Latenz (Tonende bis Tastendruck, nur richtige
Antworten) eines Zeichens mit dem Median über den Zeichensatz. Sie ist der
Median der letzten RECENT_DAYS Tage, wo es dort genug Messungen gibt, sonst
der Mittelwert über alles. Wer für ein Zeichen doppelt so lange wie üblich
braucht, bekommt den vollen Zuschlag SPEED_WEIGHT; schneller als der Median
gibt keinen Abzug. Erst ab MIN_LATENCY_SAMPLES Messungen zählt das Tempo eines
Zeichens.

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

RECENT_DAYS = 14
OLD_WEIGHT = 0.25
MIN_WEIGHT = 0.1
SPEED_WEIGHT = 0.5
MIN_LATENCY_SAMPLES = 3
MIN_RECENT_ATTEMPTS = 5
PARTNER_WEIGHT = 0.5


def _without(values, remove) -> list:
    """`values` ohne die Werte aus `remove` (je einmal)."""
    left = list(values)
    for value in remove:
        left.remove(value)
    return left


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
        self.recent = stats.recent_char_data(RECENT_DAYS) if weighted else {}
        # Latenzen der letzten Tage, mit (False) und ohne (True) die angenommenen Werte.
        self._recent_latencies = {
            False: {ch: e.get("latencies", ()) for ch, e in self.recent.items()},
            True: {ch: _without(e.get("latencies", ()), e.get("assumed_latencies", ()))
                   for ch, e in self.recent.items()}}
        # Heute fällig in der Lernkartei (core/review.py): öfter dran.
        self.due = set(review.due_chars()) if weighted else set()

    def _session_chars(self):
        # Ohne die erneuten Abfragen nach einem Fehler, wie die Gesamtstatistik.
        if self.session is None:
            return {}
        return getattr(self.session, "kept_char", self.session.per_char)

    def _error_rate(self, ch: str) -> float:
        good = wrong = 0.0
        recent = self.recent.get(ch) or {}
        total = self.all_time.get(ch) or {}
        good += recent.get("good", 0) + OLD_WEIGHT * max(total.get("good", 0) - recent.get("good", 0), 0)
        wrong += recent.get("wrong", 0) + OLD_WEIGHT * max(total.get("wrong", 0) - recent.get("wrong", 0), 0)
        e = self._session_chars().get(ch)
        recent_good, recent_wrong = recent.get("good", 0), recent.get("wrong", 0)
        if e:
            good += e["good"]
            wrong += e["wrong"]
            recent_good += e["good"]
            recent_wrong += e["wrong"]
        rate = (wrong + 1) / (good + wrong + 2)
        if recent_good + recent_wrong >= MIN_RECENT_ATTEMPTS:
            rate = max(rate, (recent_wrong + 1) / (recent_good + recent_wrong + 2))
        return rate

    def _partner_bonus(self) -> dict:
        """Zuschlag für Zeichen des Zeichensatzes, mit denen andere in letzter
        Zeit verwechselt wurden: {Zeichen: PARTNER_WEIGHT * Anteil}."""
        confused = {}
        for sent in self.charset:
            counts = dict((self.recent.get(sent) or {}).get("confusions", {}))
            e = self._session_chars().get(sent)
            if e:
                for typed, n in e["confusions"].items():
                    counts[typed] = counts.get(typed, 0) + n
            attempts = sum((self.recent.get(sent) or {}).get(k, 0) for k in ("good", "wrong"))
            attempts += (e["good"] + e["wrong"]) if e else 0
            for typed, n in counts.items():
                if typed and typed in self.charset and typed != sent and n >= stats.MIN_CONFUSION_COUNT:
                    confused[typed] = confused.get(typed, 0.0) + PARTNER_WEIGHT * min(n / max(attempts, 1), 1.0)
        return confused

    def _mean_latency(self, ch: str, measured_only=False):
        """Typische Latenz eines Zeichens: Median der letzten Tage und des
        Durchgangs, wo es genug Messungen gibt, sonst der Mittelwert über alles.
        `measured_only`: ohne die für unsichere Antworten angenommenen Werte (die
        hängen selbst am Median und trieben ihn sonst Durchgang für Durchgang
        hoch)."""
        samples = list(self._recent_latencies[measured_only].get(ch, ()))
        e = self._session_chars().get(ch)
        if e:
            samples += _without(e["latencies"], e.get("assumed_latencies", ()) if measured_only else ())
        if len(samples) >= MIN_LATENCY_SAMPLES:
            return statistics.median(samples)
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

        partners = self._partner_bonus()
        weights = []
        for ch in self.charset:
            weight = MIN_WEIGHT + self._error_rate(ch) + partners.get(ch, 0.0)
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