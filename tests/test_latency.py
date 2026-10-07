import unittest

from morsetrainer.core import latency
from morsetrainer.core.morse import code_units, duration_seconds, effective_wpm, tone_seconds


class ToneAndTempoTest(unittest.TestCase):
    def test_tone_ends_with_the_last_element(self):
        # E bei 20 WPM: ein Punkt, 60 ms; die Zeichenpause gehört nicht dazu.
        self.assertAlmostEqual(tone_seconds("E", 20), 0.06)
        self.assertAlmostEqual(duration_seconds("0", 20) - tone_seconds("0", 20), 0.18)
        self.assertEqual(tone_seconds("~", 20), 0.0)

    def test_effective_wpm_never_exceeds_the_sent_tempo(self):
        # Taste gleich nach dem letzten Punkt: so schnell wie gesendet, nicht mehr.
        self.assertAlmostEqual(effective_wpm("E", 0.07, 20), 20)
        self.assertAlmostEqual(effective_wpm("0", tone_seconds("0", 20), 20), 20)

    def test_effective_wpm_counts_from_the_start_of_the_tone(self):
        # 0 bei 20 WPM: 22 Einheiten; Ton 1,14 s, dazu 0,36 s bis zur Taste.
        since_start = tone_seconds("0", 20) + 0.36
        self.assertAlmostEqual(effective_wpm("0", since_start, 20), code_units("0") * 1.2 / 1.5)
        self.assertLess(effective_wpm("0", since_start, 20), 20)


class CharLatencyTest(unittest.TestCase):
    def test_counts_from_the_end_of_the_tone(self):
        self.assertAlmostEqual(latency.char_latency(10.4, 10.0), 0.4)

    def test_key_before_the_end_is_no_measurement(self):
        self.assertIsNone(latency.char_latency(9.9, 10.0))

    def test_writing_behind_counts_from_the_previous_key(self):
        # Das Zeichen endete bei 10,0, die vorige Taste kam erst bei 11,0.
        self.assertAlmostEqual(latency.char_latency(11.3, 10.0, previous_key=11.0), 0.3)
        self.assertAlmostEqual(latency.char_latency(11.3, 10.0, previous_key=9.0), 1.3)


class CopyTimingTest(unittest.TestCase):
    starts = [0.0, 1.0, 2.0, 3.0, 4.0]
    ends = [0.5, 1.5, 2.5, 3.5, 4.5]

    def timing(self, index, typed_index, keys):
        return latency.copy_timing(index, typed_index, keys, self.starts, self.ends)

    def test_copy_while_listening(self):
        keys = [0.8, 1.7, 2.9, 3.6, 4.7]
        since_start, measured = self.timing(2, 2, keys)
        self.assertAlmostEqual(since_start, 0.9)
        self.assertAlmostEqual(measured, 0.4)

    def test_listen_to_the_whole_group_then_type(self):
        # Erst nach der Gruppe getippt: das erste Zeichen zählt ab deren Ende,
        # die weiteren ab der vorigen Taste – keines gilt als langsam erkannt.
        keys = [5.0, 5.2, 5.4, 5.6, 5.8]
        self.assertAlmostEqual(self.timing(0, 0, keys)[1], 0.5)
        self.assertAlmostEqual(self.timing(3, 3, keys)[1], 0.2)

    def test_key_before_the_tone_ended(self):
        self.assertIsNone(self.timing(1, 1, [0.8, 1.4]))


if __name__ == "__main__":
    unittest.main()
