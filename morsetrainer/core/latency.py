"""Latenz je Zeichen: die Zeit vom hörbaren Ende des letzten Punkts oder
Strichs bis zur Taste – das Maß für „wie schnell erkannt“, unabhängig von
Zeichenlänge und Tempo (Statistik „Ø Reaktion“, Lernkartei, Gewichtung).

Beim Mitschreiben zählt die Zeit ab dem Tonende oder ab der vorigen Taste,
je nachdem was später kommt. Wer ein, zwei Zeichen hinterherschreibt oder
erst die ganze Gruppe hört und dann tippt, ist nicht langsamer im
Erkennen; gemessen wird, wie lange die Taste nach der frühestmöglichen
Gelegenheit kam."""


def char_latency(typed_time: float, tone_end: float, previous_key=None):
    """Latenz einer Taste beim fortlaufenden Mitschreiben. None für eine
    Taste vor dem Tonende (innerhalb der Messungenauigkeit erlaubt) – das
    ist keine Messung."""
    if typed_time < tone_end:
        return None
    earliest = tone_end if previous_key is None else max(tone_end, previous_key)
    return max(typed_time - earliest, 0.0)


def copy_timing(index: int, typed_index: int, key_times, tone_starts, tone_ends):
    """(Zeit ab Tonbeginn, Latenz) für das gesendete Zeichen `index`, das
    beim Mitschreiben einer Sequenz als Taste `typed_index` kam, oder None,
    wenn die Taste vor dem Tonende lag. Die erste Taste nach dem Ende der
    ganzen Sequenz zählt ab diesem Ende."""
    key_time = key_times[typed_index]
    tone_end = tone_ends[index]
    if key_time < tone_end:
        return None
    if typed_index > 0:
        earliest = max(tone_end, key_times[typed_index - 1])
    elif key_time > tone_ends[-1]:
        earliest = tone_ends[-1]
    else:
        earliest = tone_end
    latency = max(key_time - earliest, 0.0)
    return tone_end - tone_starts[index] + latency, latency
