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

from morsetrainer.core import align, tempo
from morsetrainer.core.morse import MORSE_CODE, display_text
from morsetrainer.i18n import number
from morsetrainer.modes.sequence_mode import answer_limit

# Ab so vielen gesendeten Exemplaren (je Teilnehmer im Schnitt) taucht ein
# Zeichen unter den schwächsten auf; bei einem Exemplar sagt die Quote nichts.
MIN_CHAR_COUNT = 3

# Tempo-Empfehlung (Regel wie beim mitwachsenden Tempo, core/tempo.py): erst
# ab so vielen gesendeten Zeichen im aktuellen Tempo über alle Teilnehmer,
# schneller ab diesem Anteil flüssiger Sequenzen, langsamer darunter.
ADVICE_MIN_CHARS = 50
ADVICE_FASTER = 0.9
ADVICE_SLOWER = 0.75


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
        self.tempos = {}    # Nr. -> (Zeichentempo, effektiv oder None)
        self.expected = {}  # Nr. -> Namen, die beim Senden verbunden waren
        self.answers = {}   # Name -> {Nr.: Result}
        self.replayed = set()  # Nummern, die für alle wiederholt wurden

    def add_participant(self, name: str) -> None:
        if name not in self.answers:
            self.names.append(name)
            self.answers[name] = {}

    def add_item(self, n: int, text: str, present, wpm=None, fw=None) -> None:
        self.items[n] = text
        self.tempos[n] = (wpm, fw)
        self.expected[n] = set(present)
        for name in present:
            self.add_participant(name)

    def drop_items(self, numbers) -> None:
        """Nummern aus der Wertung nehmen (kontinuierlich: beim Stop noch
        nicht gesendete Gruppen)."""
        for n in numbers:
            self.items.pop(n, None)
            self.tempos.pop(n, None)
            self.expected.pop(n, None)
            for answers in self.answers.values():
                answers.pop(n, None)

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

    def _results(self, name=None):
        """Alle Antworten, oder nur die von `name`."""
        names = [name] if name is not None else self.names
        return [result for each in names for result in self.answers.get(each, {}).values()]

    def confusions(self, limit: int = 5, name=None):
        """Häufigste Verwechslungen der Gruppe (oder eines Teilnehmers):
        [(gesendet, getippt, Anzahl)], getippt "" = ausgelassen."""
        counts = {}
        for result in self._results(name):
            for expected, got, _ in result.char_results:
                if got != expected:
                    counts[(expected, got)] = counts.get((expected, got), 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [(sent, typed, count) for (sent, typed), count in ranked[:limit]]

    def weak_chars(self, limit: int = 5, name=None):
        """Zeichen mit der höchsten Fehlerquote: [(Zeichen, Quote, Anzahl)],
        nur beantwortete Sequenzen. Für die Gruppe erst ab MIN_CHAR_COUNT
        Exemplaren je Teilnehmer (bei acht Leuten sind drei Zufall)."""
        good, total = {}, {}
        for result in self._results(name):
            for expected, got, _ in result.char_results:
                total[expected] = total.get(expected, 0) + 1
                good[expected] = good.get(expected, 0) + (got == expected)
        minimum = MIN_CHAR_COUNT * (1 if name is not None else max(len(self.names), 1))
        rates = [(ch, 1 - good[ch] / count, count) for ch, count in total.items() if count >= minimum]
        rates = [entry for entry in rates if entry[1] > 0]
        rates.sort(key=lambda entry: (-entry[1], entry[0]))
        return rates[:limit]

    def tempo_advice(self):
        """Empfehlung für das effektive Tempo aus den letzten Sequenzen im
        aktuellen Tempo: (Tempo, Anteil flüssig, Schritt +1/0/−1) oder None,
        solange zu wenig gehört wurde. Nicht beantwortet zählt als nicht
        flüssig."""
        numbers = sorted(self.items, reverse=True)
        if not numbers:
            return None
        current = self.tempos.get(numbers[0])
        if current is None or current[0] is None:
            return None
        chars = fluent = slots = 0
        for n in numbers:
            if self.tempos.get(n) != current:
                break
            for name in self.expected[n]:
                slots += 1
                chars += len(normalize(self.items[n]))
                result = self.answers.get(name, {}).get(n)
                fluent += bool(result is not None and result.fluent)
        if chars < ADVICE_MIN_CHARS or not slots:
            return None
        share = fluent / slots
        step = 1 if share >= ADVICE_FASTER else -1 if share < ADVICE_SLOWER else 0
        return current, share, step

    def csv_text(self, headers) -> str:
        """Tabelle zum Export: je Teilnehmer eine Zeile, je Sequenz eine
        Spalte mit dem Getippten und der Zeit bis Enter (leer = keine
        Antwort, – = nicht dabei). Der Spaltenkopf nennt das Tempo, ↻ heißt
        „für alle wiederholt“. Richtig, aber nicht flüssig, steht mit „~“
        dabei (zu langsam oder erst nach der Wiederholung). `headers`:
        Beschriftungen für Name, richtige Zeichen in %, richtige Sequenzen,
        flüssige Sequenzen, Median Zeit bis Enter (s), häufigste Fehler,
        schwächste Zeichen."""
        numbers = sorted(self.items)
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        columns = []
        for n in numbers:
            column = f"{n}: {display_text(self.items[n])}"
            wpm, fw = self.tempos.get(n, (None, None))
            if wpm is not None:
                column += f" ({tempo.label(wpm, fw)})"
            if n in self.replayed:
                column += " ↻"
            columns.append(column)
        writer.writerow(list(headers) + columns)
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
                    cell = display_text(result.typed) + mark
                    if result.latency is not None:
                        cell += f" ({number(result.latency, 1)} s)"
                    cells.append(cell.strip())
                else:
                    cells.append("")
            writer.writerow([name, f"{share:.0f}", f"{data['correct_items']}/{data['items']}",
                             f"{data['fluent_items']}/{data['items']}", latency,
                             format_confusions(self.confusions(3, name)), format_weak(self.weak_chars(3, name))]
                            + cells)
        return out.getvalue()


def format_confusions(confusions) -> str:
    """„R→S 2×, K→– 1×“ (– = ausgelassen)."""
    return ", ".join(f"{display_text(sent)}→{display_text(typed) or '–'} {count}×"
                     for sent, typed, count in confusions)


def format_weak(weak) -> str:
    """„H 40 % (10)“: Fehlerquote und wie oft gesendet."""
    return ", ".join(f"{display_text(ch)} {rate:.0%} ({count})" for ch, rate, count in weak)


# Auflösung (Beamer, Papier): höchstens so viele Zeilen je Spalte, so viele Spalten.
SOLUTION_ROWS = 10
SOLUTION_MAX_COLUMNS = 5
SOLUTION_GAP = "    "


def solution_cells(board: Scoreboard):
    """[(Nr., „ 7. KMRSU ↻“)] aller gesendeten Sequenzen; die Nummern
    rechtsbündig, ↻ = für alle wiederholt (auf Papier sonst nicht zu sehen)."""
    numbers = sorted(board.items)
    width = len(str(numbers[-1])) if numbers else 1
    return [(n, f"{n:>{width}}. {display_text(board.items[n])}" + (" ↻" if n in board.replayed else ""))
            for n in numbers]


def solution_columns(count: int) -> int:
    return max(1, min(SOLUTION_MAX_COLUMNS, -(-count // SOLUTION_ROWS)))


def solution_rows(cells, columns: int):
    """Zeilen der mehrspaltigen Auflösung, spaltenweise nummeriert (wie auf
    dem Zettel von oben nach unten): [[(Nr., Zelle aufgefüllt)], …]."""
    if not cells:
        return []
    height = -(-len(cells) // columns)
    blocks = [cells[i:i + height] for i in range(0, len(cells), height)]
    widths = [max(len(cell) for _, cell in block) for block in blocks]
    return [[(block[row][0], block[row][1].ljust(width)) for block, width in zip(blocks, widths) if row < len(block)]
            for row in range(height)]


def solution_text(cells, columns: int) -> str:
    """Die Auflösung als Text zum Kopieren."""
    return "\n".join(SOLUTION_GAP.join(cell for _, cell in row).rstrip() for row in solution_rows(cells, columns))
