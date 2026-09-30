"""Kontinuierlicher Durchgang im Netzwerk: Der Trainer schickt den ganzen
Text (Gruppen) auf einmal, jeder Rechner spielt ihn ohne Pause ab (oder
der Lautsprecher des Trainers), die Teilnehmer tippen fortlaufend mit.
Ausgewertet wird am Ende wie in modes/continuous_mode: Alignment über den
ganzen Text, eine Taste zählt nur, wenn sie zeitlich zum Zeichen passt.
Das Ergebnis geht je Gruppe als gewöhnliche Antwort an den Trainer, so
gelten Tabelle, Auflösung und CSV unverändert.

Die Zeitachse (wann welches Zeichen endet) wird aus den Sample-Längen
gerechnet, nicht beim Abspielen gemessen – so gilt sie genauso, wenn der
Lautsprecher des Trainers spielt und dieser Rechner stumm bleibt."""
import threading
import time

from morsetrainer.core import align, audio
from morsetrainer.core.morse import (
    AUDIO_LATENCY, SAMPLE_RATE, build_samples, char_gap_seconds, code_units, silence, word_gap_extra_seconds,
)
from morsetrainer.modes.continuous_mode import STOP_GRACE_SECONDS, WRITE_CHUNK_SECONDS, plausible

DURATION_RANGE = (1, 30)  # Minuten
DEFAULT_DURATION = 5
# Nach dem letzten Zeichen bleibt so lange Zeit, es noch einzutippen.
FINISH_GRACE_SECONDS = 3


def _char_seconds(char, wpm, fw, cache):
    key = (char, wpm, fw)
    if key not in cache:
        cache[key] = len(build_samples(char, wpm, 600, fw)) / SAMPLE_RATE
    return cache[key]


def timeline(groups, wpm: int, fw=None):
    """[(Zeichen, Tonende ab Beginn in s, Gruppe)] und Gesamtdauer. Zwischen
    den Gruppen (und innerhalb, bei Leerzeichen) eine Wortpause."""
    cache, entries, offset = {}, [], 0.0
    word_gap = word_gap_extra_seconds(wpm, fw)
    gap = char_gap_seconds(wpm, fw)
    for index, group in enumerate(groups):
        if index:
            offset += word_gap
        for char in group:
            if char == " ":
                offset += word_gap
                continue
            offset += _char_seconds(char, wpm, fw, cache)
            entries.append((char, offset - gap, index))
    return entries, offset


def make_groups(source, seconds: float, wpm: int, fw=None):
    """So viele Einträge aus `source` (content.ItemSource), wie in `seconds`
    passen – mindestens einer."""
    groups = []
    while True:
        groups.append(source.next()[0])
        if timeline(groups, wpm, fw)[1] >= seconds:
            return groups


def evaluate(entries, start: float, typed: str, key_times, stopped_at=None):
    """Wertet das fortlaufend Getippte aus. `entries` aus timeline(),
    `start`: wann der Ton hörbar begann. `stopped_at`: Abbruch; Gruppen,
    die bis dahin nicht angefangen hatten, fehlen im Ergebnis, und kurz
    davor gesendete Zeichen zählen nicht als verpasst.

    Ergebnis: je Zeichen (gesendet, getippt, richtig, Reaktionszeit oder
    None) für die eigene Statistik, und je Gruppe {Nr.: (getippt, Zeit vom
    Tonende des letzten Zeichens bis zu dessen Taste, oder None)}."""
    ends = [start + end for _, end, _ in entries]
    kept = {group for _, _, group in entries} if stopped_at is None else kept_groups(entries, start, stopped_at)
    sent = "".join(char for char, _, _ in entries)
    chars, typed_in, last_latency = [], {group: "" for group in kept}, {}
    group = entries[0][2] if entries else 0
    for op in align.align(sent, typed):
        if op.expected_index is not None:
            group = entries[op.expected_index][2]
        if group not in kept:
            continue
        if op.kind == align.OpKind.INSERT:
            typed_in[group] += op.received_char  # überzählige Taste: gehört zur Gruppe davor
            continue
        end = ends[op.expected_index]
        if op.kind == align.OpKind.DELETE:
            if stopped_at is None or end <= stopped_at - STOP_GRACE_SECONDS:
                chars.append((op.expected_char, "", False, None))
            continue
        key_time = key_times[op.received_index]
        if not plausible(key_time, end):
            chars.append((op.expected_char, "", False, None))  # vorausgeraten oder viel zu spät
            continue
        reaction = max(key_time - end, 0.001)
        chars.append((op.expected_char, op.received_char, op.kind == align.OpKind.MATCH, reaction))
        typed_in[group] += op.received_char
        last_latency[group] = (op.expected_index, reaction)
    last_index = {}
    for index, (_, _, group) in enumerate(entries):
        last_index[group] = index
    groups = {}
    for group in sorted(kept):
        index, reaction = last_latency.get(group, (None, None))
        groups[group] = (typed_in[group], reaction if index == last_index[group] else None)
    return chars, groups


def kept_groups(entries, start: float, stopped_at: float):
    """Gruppen, deren erstes Zeichen bis `stopped_at` zu hören war."""
    first = {}
    for _, end, group in entries:
        first.setdefault(group, start + end)
    return {group for group, end in first.items() if end <= stopped_at}


def effective_wpm(char: str, reaction: float) -> float:
    return code_units(char) * 1.2 / max(reaction, 0.001)


class Player:
    """Spielt die Gruppen in einem Hintergrund-Thread durchgehend ab (ein
    Stream, wie im Reiter Kontinuierlich). `start` ist danach der Zeitpunkt,
    zu dem der Ton hörbar beginnt; `error` eine Fehlermeldung oder None."""

    def __init__(self, groups, wpm: int, freq: int, fw=None):
        self.groups, self.wpm, self.freq, self.fw = groups, wpm, freq, fw
        self.start = time.time() + AUDIO_LATENCY  # genauer, sobald der Stream offen ist
        self.error = None
        self.stopped = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped = True
        if self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)

    def _run(self):
        try:
            with audio.output_stream() as stream:
                self.start = time.time() + stream.latency
                gap = silence(word_gap_extra_seconds(self.wpm, self.fw))
                for index, group in enumerate(self.groups):
                    if index and not self._write(stream, gap):
                        return
                    for char in group:
                        samples = gap if char == " " else build_samples(char, self.wpm, self.freq, self.fw)
                        if not self._write(stream, samples):
                            return
        except audio.ERRORS as exc:
            self.error = audio.describe(exc)

    def _write(self, stream, samples) -> bool:
        chunk = int(SAMPLE_RATE * WRITE_CHUNK_SECONDS)
        for begin in range(0, len(samples), chunk):
            if self.stopped:
                return False
            stream.write(samples[begin:begin + chunk])
        return True
