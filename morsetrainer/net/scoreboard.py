"""Auswertung beim Trainer: wer was geantwortet hat, je Teilnehmer und für
die ganze Gruppe.

Gewertet wird wie in den Sequenz-Reitern per Alignment (core/align.py):
Ein ausgelassenes Zeichen ist genau ein Fehler, zu viel Getipptes zählt als
Fehler. Leerzeichen zählen nicht (eigener Text darf ganze Wortfolgen
enthalten). „Flüssig“ ist eine richtige Antwort nur beim ersten Hören
(ohne „Für alle wiederholen“) und im selben Zeitfenster wie in den
Sequenz-Reitern (sequence_mode.answer_limit): Wer länger braucht, hat
womöglich gezählt statt gehört. Wer bei einer Sequenz verbunden war und nicht geantwortet hat,
hat alle Zeichen verpasst; für die Verwechslungen der Gruppe zählt das
nicht, dort geht es ums Verhören."""
import csv
import io
import statistics
from dataclasses import dataclass

from morsetrainer.core import align
from morsetrainer.core.morse import MORSE_CODE, display_text
from morsetrainer.i18n import number
from morsetrainer.modes.sequence_mode import answer_limit

# Ab so vielen gesendeten Exemplaren taucht ein Zeichen unter den
# schwächsten der Gruppe auf (bei einem Exemplar sagt die Quote nichts).
MIN_CHAR_COUNT = 3


def normalize(text: str) -> str:
    """Nur Morsezeichen, groß, ohne Leerzeichen."""
    return "".join(ch for ch in str(text).upper() if ch in MORSE_CODE)


@dataclass
class Result:
    sent: str
    typed: str
    correct: bool
    correct_chars: int
    total: int
    latency: float = None  # Tonende bis Enter in Sekunden
    replayed: bool = False  # erst nach „Für alle wiederholen“ beantwortet

    @property
    def slow(self) -> bool:
        return self.latency is not None and self.latency > answer_limit(self.total)

    @property
    def fluent(self) -> bool:
        """Richtig beim ersten Hören und im Zeitfenster. Ohne bekannte Zeit
        nicht (dann ist nicht zu sagen, ob gezählt wurde)."""
        return self.correct and not self.replayed and self.latency is not None and not self.slow

    @property
    def char_results(self):
        return align.char_results(self.sent, self.typed)


def evaluate(sent: str, typed: str, latency=None, replayed=False) -> Result:
    """Wertet eine Antwort aus; `sent` und `typed` werden normalisiert."""
    sent, typed = normalize(sent), normalize(typed)
    hits = sum(1 for expected, got, _ in align.char_results(sent, typed) if got == expected)
    correct_chars = max(hits - align.extra_count(sent, typed), 0)
    return Result(sent, typed, typed == sent, correct_chars, len(sent), latency, replayed)


class Scoreboard:
    def __init__(self):
        self.names = []     # Teilnehmer in der Reihenfolge der Anmeldung
        self.items = {}     # Nr. -> gesendeter Text
        self.expected = {}  # Nr. -> Namen, die beim Senden verbunden waren
        self.answers = {}   # Name -> {Nr.: Result}
        self.replayed = set()  # Nummern, die für alle wiederholt wurden

    def add_participant(self, name: str) -> None:
        if name not in self.answers:
            self.names.append(name)
            self.answers[name] = {}

    def add_item(self, n: int, text: str, present) -> None:
        self.items[n] = text
        self.expected[n] = set(present)
        for name in present:
            self.add_participant(name)

    def mark_replayed(self, n: int) -> None:
        """Nr. `n` wurde für alle wiederholt: Wer danach antwortet, hat sie
        zweimal gehört. Das weiß der Trainer selbst, ohne dem Teilnehmer
        glauben zu müssen."""
        self.replayed.add(n)

    def record(self, name: str, n, typed, latency=None):
        """Result der Antwort, oder None, wenn es die Nummer nicht gibt,
        der Teilnehmer beim Senden nicht dabei war oder schon geantwortet hat."""
        if not isinstance(n, int) or n not in self.items or name not in self.expected[n]:
            return None
        if n in self.answers.get(name, {}):
            return None
        if not isinstance(latency, (int, float)) or isinstance(latency, bool) or not 0 <= latency < 3600:
            latency = None
        result = evaluate(self.items[n], typed if isinstance(typed, str) else "", latency, n in self.replayed)
        self.answers[name][n] = result
        return result

    def answered(self, n: int):
        """Namen, die zu Nr. `n` geantwortet haben."""
        return {name for name, answers in self.answers.items() if n in answers}

    def summary(self, name: str) -> dict:
        """Zahlen eines Teilnehmers über alle Sequenzen, bei denen er dabei war."""
        answers = self.answers.get(name, {})
        items = [n for n in self.items if name in self.expected[n]]
        chars_total = sum(len(normalize(self.items[n])) for n in items)
        latencies = [r.latency for r in answers.values() if r.latency is not None]
        return {
            "items": len(items),
            "answered": len(answers),
            "correct_items": sum(1 for r in answers.values() if r.correct),
            "fluent_items": sum(1 for r in answers.values() if r.fluent),
            "chars_correct": sum(r.correct_chars for r in answers.values()),
            "chars_total": chars_total,
            "latency": statistics.median(latencies) if latencies else None,
        }

    def accuracy(self, name=None):
        """Anteil richtiger Zeichen (0..1) eines Teilnehmers oder der ganzen
        Gruppe; None ohne gesendete Zeichen."""
        names = [name] if name is not None else self.names
        correct = total = 0
        for each in names:
            data = self.summary(each)
            correct += data["chars_correct"]
            total += data["chars_total"]
        return correct / total if total else None

    def fluency(self):
        """Anteil flüssig richtiger Sequenzen (0..1) über alle Teilnehmer und
        Sequenzen, bei denen sie dabei waren; None ohne Sequenzen."""
        fluent = total = 0
        for name in self.names:
            data = self.summary(name)
            fluent += data["fluent_items"]
            total += data["items"]
        return fluent / total if total else None

    def confusions(self, limit: int = 5):
        """Häufigste Verwechslungen der Gruppe: [(gesendet, getippt, Anzahl)],
        getippt "" = ausgelassen."""
        counts = {}
        for answers in self.answers.values():
            for result in answers.values():
                for expected, got, _ in result.char_results:
                    if got != expected:
                        counts[(expected, got)] = counts.get((expected, got), 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [(sent, typed, count) for (sent, typed), count in ranked[:limit]]

    def weak_chars(self, limit: int = 5):
        """Zeichen mit der höchsten Fehlerquote der Gruppe: [(Zeichen, Quote)],
        nur beantwortete Sequenzen, ab MIN_CHAR_COUNT Exemplaren."""
        good, total = {}, {}
        for answers in self.answers.values():
            for result in answers.values():
                for expected, got, _ in result.char_results:
                    total[expected] = total.get(expected, 0) + 1
                    good[expected] = good.get(expected, 0) + (got == expected)
        rates = [(ch, 1 - good[ch] / count) for ch, count in total.items() if count >= MIN_CHAR_COUNT]
        rates = [(ch, rate) for ch, rate in rates if rate > 0]
        rates.sort(key=lambda item: (-item[1], item[0]))
        return rates[:limit]

    def csv_text(self, headers) -> str:
        """Tabelle zum Export: je Teilnehmer eine Zeile, je Sequenz eine
        Spalte mit dem Getippten (leer = keine Antwort, – = nicht dabei).
        Richtig, aber nicht flüssig, steht mit „~“ dabei (zu langsam oder
        erst nach der Wiederholung). `headers`: Beschriftungen für Name,
        richtige Zeichen in %, richtige Sequenzen, flüssige Sequenzen,
        Median Zeit bis Enter (s)."""
        numbers = sorted(self.items)
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(list(headers) + [f"{n}: {display_text(self.items[n])}" for n in numbers])
        for name in self.names:
            data = self.summary(name)
            share = data["chars_correct"] / data["chars_total"] * 100 if data["chars_total"] else 0
            latency = number(data["latency"], 1) if data["latency"] is not None else ""
            cells = []
            for n in numbers:
                if name not in self.expected[n]:
                    cells.append("–")
                elif n in self.answers[name]:
                    result = self.answers[name][n]
                    mark = " ✗" if not result.correct else "" if result.fluent else " ~"
                    cells.append(display_text(result.typed) + mark)
                else:
                    cells.append("")
            writer.writerow([name, f"{share:.0f}", f"{data['correct_items']}/{data['items']}",
                             f"{data['fluent_items']}/{data['items']}", latency] + cells)
        return out.getvalue()
