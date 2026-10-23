"""Messtests für die erzeugten Signale (core/band.py): Kalibrierung des
Filters, Unabhängigkeit von der Blockgröße, nahtlose Schleifen und das
Spektrum der Tastklicks."""
import unittest

import numpy as np

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import band

RATE = band.SAMPLE_RATE


class FilterCalibrationTest(unittest.TestCase):
    def test_filter_noise_db_matches_ir(self):
        # Das angegebene „nimmt so viel Rauschen weg“ stimmt mit dem Filter
        # überein, das wirklich angewendet wird (Impulsantwort, auf
        # FILTER_IR_SECONDS gekürzt), nicht nur mit dem Idealfilter.
        n = band.FILTER_FFT_SIZE
        f = np.fft.rfftfreq(n, 1 / RATE)
        passband = band._noise_bandwidth(band._passband_gain(f), f)
        for width in (500, 250):
            response = np.abs(np.fft.rfft(band.filter_ir(width, 600), n))
            measured = 10 * np.log10(passband / band._noise_bandwidth(response, f))
            self.assertAlmostEqual(band.filter_noise_db(width), measured, delta=0.3, msg=width)

    def test_snr_at_tone(self):
        # Am Ton selbst, durchs ganze Mischen gemessen, liegt der Rauschabstand
        # um die Rauschminderung des Filters über dem angezeigten Wert: Der
        # Ton kommt mit Verstärkung 1 durch, das Rauschen nicht. Bei jeder
        # Tonhöhe, weil das Filter mit ihr wandert.
        block = int(RATE * band.PRESET_BLOCK_SECONDS)
        seconds = 5
        t = np.arange(seconds * RATE) / RATE
        for pitch in (300, 600, 900):
            tone = (band.AMPLITUDE * np.sin(2 * np.pi * pitch * t)).astype(np.float32)
            for width in (500, 250):
                spec = {"levels": {"noise": 0.6}, "gain": 1.0, "filter": width}
                quiet = band.conditions(spec, pitch)  # nur Rauschen, ohne Station und ohne AGC
                noise = np.concatenate([quiet.mix([], block, receiver_agc=False) for _ in range(len(tone) // block)])
                loud = band.conditions(spec, pitch)
                both = np.concatenate([loud.mix([(tone[i:i + block], 0)], block) for i in range(0, len(tone), block)])
                settled = slice(RATE // 2, None)  # Einschwingen von Filter und Gleiten der Pegel
                signal_rms = np.sqrt(max(np.mean(both[settled] ** 2) - np.mean(noise[settled] ** 2), 1e-12))
                measured = 20 * np.log10(signal_rms / np.sqrt(np.mean(noise[settled] ** 2)))
                expected = band.noise_snr_db(0.6) + band.filter_noise_db(width)
                self.assertAlmostEqual(measured, expected, delta=1.0, msg=(pitch, width))

    def test_filter_has_unity_gain_at_the_own_pitch(self):
        for width in (500, 250):
            h = band.filter_ir(width, 600)
            t = np.arange(len(h)) / RATE
            self.assertAlmostEqual(abs(np.sum(h * np.exp(-2j * np.pi * 600 * t))), 1.0, places=6)


class BlockSizeTest(unittest.TestCase):
    @staticmethod
    def run_blocks(block, spec, seconds=2):
        conditions = band.conditions(spec, 600)
        t = np.arange(seconds * RATE) / RATE
        tone = (0.3 * np.sin(2 * np.pi * 600 * t) * (np.sin(2 * np.pi * 3 * t) > 0)).astype(np.float32)
        return np.concatenate([conditions.mix([(tone[i:i + block], 0)], len(tone[i:i + block]))
                               for i in range(0, len(tone), block)])

    def test_mix_block_size_independent(self):
        # Wie der Ton in Stücke geschnitten wird, ändert das Ergebnis nicht.
        # Ausgenommen sind Knacker (qrn) und das AGC-Pumpen auf sie: Ob in
        # einem Block einer beginnt, wird je Block ausgewürfelt.
        for effect in band.EFFECTS:
            if effect in ("qrn", "agc"):
                continue
            spec = {"levels": {effect: 0.7}, "gain": 1.0, "seed": 3}
            reference = self.run_blocks(960, spec)
            for block in (480, 1920):
                out = self.run_blocks(block, spec)
                scale = float(np.sqrt(np.mean(reference ** 2)))
                self.assertLess(float(np.sqrt(np.mean((out - reference) ** 2))) / scale, 1e-3, (effect, block))

    def test_block_size_independent_with_filter_and_several_effects(self):
        spec = {"levels": {"noise": 0.6, "qsb": 0.5, "cw_qrm": 0.5, "clicks": 0.5, "flutter": 0.5},
                "gain": 1.0, "seed": 3, "filter": 500}
        reference = self.run_blocks(960, spec)
        scale = float(np.sqrt(np.mean(reference ** 2)))
        for block in (480, 1920):
            out = self.run_blocks(block, spec)
            self.assertLess(float(np.sqrt(np.mean((out - reference) ** 2))) / scale, 1e-3, block)


class LoopTest(unittest.TestCase):
    def test_loops_seamless(self):
        # Der Sprung vom Ende einer Schleife zu ihrem Anfang ist nicht größer
        # als die größten Schritte mitten in der Schleife: kein Knacken beim
        # Umlauf.
        conditions = band.conditions({"levels": {e: 0.5 for e in band.EFFECTS}, "gain": 1.0, "seed": 3}, 600)
        loops = {"noise": band._shaped_noise_loop(), "filter noise": band._filter_noise_loop(),
                 "ssb": conditions.ssb, "smps": conditions.smps, "plc": conditions.plc,
                 "cw_qrm": conditions.cw_qrm, "key clicks": conditions.key_clicks}
        for name, loop in loops.items():
            self.assertIsNotNone(loop, name)
            steps = np.abs(np.diff(loop.astype(np.float64)))
            seam = abs(float(loop[0]) - float(loop[-1]))
            self.assertLessEqual(seam, np.percentile(steps, 99.9) + 1e-9, name)


class KeyClickTest(unittest.TestCase):
    @staticmethod
    def clicks(scale=1.0):
        rng = np.random.default_rng(1)
        loop = band._cw_qrm_loop(rng, 600)
        return band._key_clicks(loop * scale, np.random.default_rng(2))

    def test_key_click_sidebands(self):
        # Die Klicks sind breitbandig: im Bereich 300–2600 Hz liegt die
        # Leistungsdichte überall innerhalb von 3 dB, auch weit neben dem
        # Ton des Nachbarn.
        clicks = self.clicks()
        spectrum = np.abs(np.fft.rfft(clicks)) ** 2
        freq = np.fft.rfftfreq(len(clicks), 1 / RATE)

        def density(low, high):
            return spectrum[(freq >= low) & (freq < high)].mean()
        for low, high in ((700, 1200), (1200, 1800), (1800, 2600)):
            self.assertLess(abs(10 * np.log10(density(low, high) / density(300, 700))), 3.0, (low, high))

    def test_key_click_level_does_not_depend_on_the_neighbour_loudness(self):
        np.testing.assert_array_equal(self.clicks(), self.clicks(0.1))

    def test_key_clicks_peak_below_one(self):
        peak = float(np.max(np.abs(self.clicks())))
        self.assertLessEqual(peak, 1.0)
        self.assertGreater(peak, 0.6)


if __name__ == "__main__":
    unittest.main()


class AgcPumpTest(unittest.TestCase):
    @staticmethod
    def rms(levels, seconds=20):
        conditions = band.conditions({"levels": levels, "gain": 1.0, "seed": 3}, 600)
        out = np.concatenate([conditions.mix([], 960, receiver_agc=False) for _ in range(seconds * RATE // 960)])
        return float(np.sqrt(np.mean(out.astype(np.float64) ** 2)))

    def test_pumping_leaves_the_crashes_themselves_alone(self):
        # Ein Knacker ist schneller als die AGC: Er kommt laut durch, erst
        # danach bricht das Signal ein. Ohne Signal darf Pumpen ihn nicht leiser machen.
        plain = self.rms({"qrn": 0.5, "agc": 0.0})
        pumped = self.rms({"qrn": 0.5, "agc": 1.0})
        self.assertGreater(pumped, plain * 0.7)  # höchstens 3 dB leiser


class SwitchOnTest(unittest.TestCase):
    def test_effect_switched_on_during_playback_glides_in(self):
        for effect in ("ssb", "smps", "plc", "cw_qrm"):
            conditions = band.conditions({"levels": {effect: 0.8}, "gain": 1.0, "seed": 3}, 600)
            conditions.enabled[effect] = False
            for _ in range(5):
                conditions.mix([], 960, receiver_agc=False)
            conditions.enabled[effect] = True
            out = conditions.mix([], 960, receiver_agc=False)
            self.assertLess(float(np.max(np.abs(out[:48]))), 0.05, effect)  # erste Millisekunde
