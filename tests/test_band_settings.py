"""Tests für die zentralen Bandbedingungen (core/band.py, widgets/band_settings.py):
einstellen an einer Stelle, in den Reitern nur an/aus."""
import unittest
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import band
from morsetrainer.modes import network_mode
from morsetrainer.widgets.band_settings import toggle_value
from tests.test_modes import AppTestCase


class SpecTest(unittest.TestCase):
    def test_preset_rank_is_the_hardest_level_reached(self):
        self.assertEqual(band.preset_rank(band.spec_from_preset("medium")), "medium")
        spec = band.spec_from_preset("medium")
        spec["levels"]["noise"] = 0.5  # weniger Rauschen als mittel, mehr als leicht
        self.assertEqual(band.preset_rank(spec), "light")
        spec["levels"].update(ssb=1.0, chirp=1.0)  # Zusätzliches hebt die Stufe nicht
        self.assertEqual(band.preset_rank(spec), "light")
        self.assertIsNone(band.preset_rank({"levels": {"ssb": 1.0}, "gain": 1.0}))
        self.assertIsNone(band.preset_rank(None))

    def test_clean_spec_drops_junk_and_clamps(self):
        self.assertIsNone(band.clean_spec("medium"))
        self.assertIsNone(band.clean_spec({"levels": []}))
        spec = band.clean_spec({"levels": {"noise": 3, "qrn": True, "boom": 0.5, "qsb": 0.4}, "gain": 99})
        self.assertEqual(spec, {"levels": {"noise": 1.0, "qsb": 0.4}, "gain": band.GAIN_RANGE[1]})
        # JSON kennt auch NaN und Infinity: im Ton hätten sie nichts verloren.
        spec = band.clean_spec({"levels": {"noise": float("nan"), "qrn": float("inf")}, "gain": float("nan")})
        self.assertEqual(spec, {"levels": {}, "gain": 1.0})

    def test_apply_spec_switches_effects_and_gain(self):
        conditions = band.conditions({"levels": {"noise": 0.2}, "gain": 0.5}, 600)
        self.assertTrue(conditions.enabled["noise"])
        self.assertFalse(conditions.enabled["qsb"])
        self.assertEqual((conditions.levels["noise"], conditions.background_gain), (0.2, 0.5))
        band.apply_spec(conditions, None)
        self.assertFalse(any(conditions.enabled.values()))
        self.assertFalse(conditions.active)

    def test_old_tab_settings_become_on_or_off(self):
        self.assertIs(toggle_value("light"), True)
        self.assertIs(toggle_value(None), False)
        self.assertIs(toggle_value({"noise": {"enabled": False, "level": 40}}), False)
        self.assertIs(toggle_value({"noise": {"enabled": True, "level": 40}}), True)
        self.assertIsNone(toggle_value(7))


class LevelsTest(unittest.TestCase):
    """Rauschabstand in dB, Regelung statt Übersteuern, Fading nach Stufe."""

    def test_presets_are_whole_db_steps(self):
        self.assertEqual([round(band.noise_snr_db(band.PRESETS[p]["noise"]), 6) for p in band.PRESETS],
                         [8.0, 2.0, -4.0])
        self.assertAlmostEqual(band.noise_snr_db(1.0), -10.0)
        self.assertAlmostEqual(band.noise_snr_db(0.6, 2.0), 2.0 - 6.0206, places=3)  # doppelte Lautstärke
        self.assertEqual(band.noise_snr_db(0.5, 0.0), float("inf"))

    def test_measured_snr_matches_and_agc_prevents_clipping(self):
        import numpy as np
        for level in (0.05, 0.6, 1.0):
            conditions = band.conditions({"levels": {"noise": level}, "gain": 1.0}, 600)
            silence = np.zeros(band.SAMPLE_RATE, dtype=np.float32)
            noise_rms = float(np.sqrt(np.mean(conditions.mix([(silence, 0)], len(silence)) ** 2)))
            _, agc = conditions.noise_and_agc()
            measured = 20 * np.log10(band.SIGNAL_RMS * agc / noise_rms)
            self.assertAlmostEqual(measured, band.noise_snr_db(level), delta=0.5)
            self.assertLessEqual(noise_rms, band.NOISE_RMS_CAP * 1.03)  # 1 s Messzeit schwankt etwas
        # Ein Signal unter dem Rauschen übersteuert nicht.
        tone = band.build_text("KM", 25, 600)
        mixed, _ = band.apply_preset(conditions, tone)
        self.assertLess(float(np.max(np.abs(mixed))), 1.0)

    def test_fading_depth_follows_the_level_not_chance(self):
        import numpy as np
        step = band.SAMPLE_RATE // 4
        for level in (0.3, 0.8):
            wanted = level * band.QSB_MAX_DEPTH
            for _ in range(10):
                conditions = band.conditions({"levels": {"qsb": level}, "gain": 1.0}, 600)
                gains = []
                for _ in range(10 * 60 * 4):  # 10 min Bandzeit in Viertelsekunden
                    gains.append(float(conditions.station_gain(0, 1)[0]))
                    conditions.sample_pos += step
                depth = 1 - min(gains) / max(gains)
                # Höchstens die Streuung je Station, und das tiefe Loch kommt auch wirklich.
                self.assertLessEqual(depth, min(wanted * band.QSB_DEPTH_SPREAD[1], band.QSB_MAX_DEPTH) + 0.01)
                self.assertGreaterEqual(depth, 0.75 * wanted * band.QSB_DEPTH_SPREAD[0])


class FadeTest(unittest.TestCase):
    def test_noise_fades_in_and_out_but_signs_stay_untouched(self):
        import numpy as np
        conditions = band.conditions(band.spec_from_preset("heavy"), 600)
        tone = band.build_text("E", 20, 600)
        mixed, lead = band.apply_preset(conditions, tone)
        self.assertEqual(float(mixed[0]), 0.0)
        self.assertEqual(float(mixed[-1]), 0.0)
        fade = int(band.PRESET_FADE_SECONDS * band.SAMPLE_RATE)
        self.assertLess(fade, lead * band.SAMPLE_RATE)
        self.assertLess(fade, band.PRESET_LEAD_SECONDS[1] * band.SAMPLE_RATE)
        self.assertLess(float(np.max(np.abs(mixed[:fade // 10]))), float(np.max(np.abs(mixed[fade:2 * fade]))))


class TimeRunsOnTest(unittest.TestCase):
    """Abfragemodi: Fading und Nachbar-QRM laufen zwischen den Sequenzen
    weiter, statt jedes Mal an derselben Stelle zu beginnen."""

    def test_fading_and_qrm_continue_during_the_answer_pause(self):
        import numpy as np
        conditions = band.conditions({"levels": {"qsb": 1.0, "cw_qrm": 0.5}, "gain": 1.0}, 600)
        tone = np.full(4800, 0.5, dtype=np.float32)
        now = [1000.0]
        with mock.patch.object(band.time, "time", lambda: now[0]):
            band.apply_preset(conditions, tone)
            first = (conditions.sample_pos, conditions.cw_qrm_pos)
            now[0] += 7.0  # Antwortpause
            band.apply_preset(conditions, tone)
        self.assertGreater(conditions.sample_pos, first[0] + 6 * band.SAMPLE_RATE)
        self.assertNotEqual(conditions.cw_qrm_pos, first[1] % len(conditions.cw_qrm))
        # Noch nicht gehörter Vorlauf wird nicht übersprungen.
        with mock.patch.object(band.time, "time", lambda: now[0]):
            before = conditions.sample_pos
            conditions.catch_up()
        self.assertEqual(conditions.sample_pos, before)


class NetworkMessageTest(unittest.TestCase):
    def test_spec_travels_with_preset_for_older_versions(self):
        spec = {"levels": {"noise": 0.7, "qsb": 0.9, "qrn": 0.4}, "gain": 1.2}
        fields = network_mode.band_fields(spec)
        self.assertEqual(fields["band"], "medium")
        self.assertEqual(network_mode.message_spec(fields), spec)
        # Schwächer als jede Stufe: ältere Teilnehmer bekommen wenigstens „leicht“.
        self.assertEqual(network_mode.band_fields({"levels": {"ssb": 0.3}, "gain": 1.0})["band"], "light")
        self.assertEqual(network_mode.band_fields(None), {"band": None})
        self.assertIsNone(network_mode.message_spec({"band": None}))

    def test_everyone_hears_the_same_fading(self):
        import numpy as np
        fields = network_mode.band_fields({"levels": {"qsb": 0.8}, "gain": 1.0, "seed": 4711})
        spec = network_mode.message_spec(fields)
        self.assertEqual(spec["seed"], 4711)
        a, b = band.conditions(spec, 600), band.conditions(spec, 600)
        np.testing.assert_allclose(a.station_gain(0, 4800), b.station_gain(0, 4800))
        self.assertNotIn("seed", band.clean_spec({"levels": {}, "seed": -1}))

    def test_message_from_older_trainer_uses_preset(self):
        self.assertEqual(network_mode.message_spec({"band": "heavy"}), band.spec_from_preset("heavy"))
        self.assertIsNone(network_mode.message_spec({"band": ["heavy"]}))


class NetworkCacheTest(AppTestCase):
    def test_band_cache_stays_small(self):
        net = self.mode("Netzwerk")
        for level in range(10):
            net._band({"levels": {"noise": level / 10}, "gain": 1.0}, 600)
        self.assertLessEqual(len(net._band_cache), network_mode.BAND_CACHE_SIZE)


class FilterAndQrmTest(unittest.TestCase):
    """CW-Filter um die eigene Tonhöhe und CW-QRM in wählbarem Abstand."""

    @staticmethod
    def tone(freq, seconds=1.0):
        import numpy as np
        t = np.arange(int(seconds * band.SAMPLE_RATE)) / band.SAMPLE_RATE
        return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

    @staticmethod
    def blockwise(conditions, samples, station=0):
        import numpy as np
        block = int(band.SAMPLE_RATE * band.PRESET_BLOCK_SECONDS)
        return np.concatenate([conditions.mix([(samples[i:i + block], station)], len(samples[i:i + block]))
                               for i in range(0, len(samples), block)])

    def test_narrow_filter_passes_own_pitch_and_removes_far_signals(self):
        import numpy as np
        half = band.SAMPLE_RATE // 2
        for width, far_db in ((500, -6), (250, -25)):
            spec = {"levels": {"qrn": 0.01}, "gain": 1.0, "filter": width}
            own = self.blockwise(band.conditions(spec, 600), self.tone(600))
            far = self.blockwise(band.conditions(spec, 600), self.tone(950))
            self.assertAlmostEqual(float(np.max(np.abs(own[half:]))), 0.3, delta=0.01)
            self.assertLess(20 * np.log10(np.max(np.abs(far[half:])) / 0.3), far_db)
        # 2,4 kHz wie bisher: nichts zusätzlich gefiltert.
        wide = band.conditions({"levels": {"qrn": 0.01}, "gain": 1.0}, 600)
        self.assertIsNone(wide.filter)

    def test_switching_band_off_resets_the_filter(self):
        # QSO und Contest: Bandbedingungen im laufenden Durchgang abgeschaltet
        # (apply_spec(None)) – ein 250-Hz-Filter darf nicht stehen bleiben.
        conditions = band.conditions({"levels": {"qrn": 0.01}, "gain": 1.0, "filter": 250,
                                      "qrm_offset": "zero"}, 600)
        self.assertIsNotNone(conditions.filter)
        band.apply_spec(conditions, None)
        conditions.prepare(600)
        self.assertIsNone(conditions.filter)
        self.assertEqual(conditions.filter_width, 2400)
        self.assertEqual(conditions.qrm_offset, "far")

    def test_own_sidetone_bypasses_the_filter(self):
        import numpy as np
        conditions = band.conditions({"levels": {"qrn": 0.01}, "gain": 1.0, "filter": 250}, 600)
        out = self.blockwise(conditions, self.tone(1000), station=None)
        self.assertAlmostEqual(float(np.max(np.abs(out))), 0.3, delta=0.01)

    def test_filter_takes_away_noise(self):
        import numpy as np
        silent = np.zeros(band.SAMPLE_RATE, dtype=np.float32)
        rms = {}
        for width in band.FILTER_WIDTHS:
            out = self.blockwise(band.conditions({"levels": {"noise": 0.5}, "gain": 1.0, "filter": width}, 600),
                                 silent)
            rms[width] = float(np.sqrt(np.mean(out[4800:] ** 2)))
        for width in (500, 250):
            measured = 20 * np.log10(rms[2400] / rms[width])
            self.assertAlmostEqual(measured, band.filter_noise_db(width), delta=1.0)
        self.assertGreater(band.filter_noise_db(250), band.filter_noise_db(500) + 2)

    def test_narrow_filter_lowers_the_rank(self):
        spec = band.spec_from_preset("medium")
        self.assertEqual(band.preset_rank(spec | {"filter": 2400}), "medium")
        # Mittel (+2 dB) im 500-Hz-Filter rund +8 dB: wie leicht; im 250-Hz-Filter leichter als leicht.
        self.assertEqual(band.preset_rank(spec | {"filter": 500}), "light")
        self.assertIsNone(band.preset_rank(spec | {"filter": 250}))
        heavy = band.spec_from_preset("heavy") | {"filter": 500}
        self.assertEqual(band.preset_rank(heavy), "medium")  # −4 dB im Filter rund +2 dB

    def test_qrm_lies_in_the_chosen_offset(self):
        import numpy as np
        # Feste Erwartungen, nicht band.QRM_OFFSETS: sonst wandert ein falscher
        # Wert dort unbemerkt in den Test mit.
        for key, (low, high) in {"far": (300, 500), "near": (50, 200), "zero": (0, 15)}.items():
            conditions = band.conditions({"levels": {"cw_qrm": 1.0}, "gain": 1.0, "qrm_offset": key, "seed": 3},
                                         600)
            loop = conditions.cw_qrm
            spectrum = np.abs(np.fft.rfft(loop))
            peak = np.fft.rfftfreq(len(loop), 1 / band.SAMPLE_RATE)[np.argmax(spectrum)]
            # Die Tastung (und gelegentlich Chirp) verschiebt die Spitze um einige Hz.
            self.assertLessEqual(abs(peak - 600), high + 10, key)
            self.assertGreaterEqual(abs(peak - 600), low - 10, key)
        # Abstand im laufenden Durchgang umgestellt: neues QRM.
        before = conditions.cw_qrm
        band.apply_spec(conditions, {"levels": {"cw_qrm": 1.0}, "gain": 1.0, "qrm_offset": "far"})
        conditions.prepare(600)
        self.assertIsNot(conditions.cw_qrm, before)
        self.assertEqual(conditions.cw_qrm_offset, "far")

    def test_same_seed_same_qrm_and_storms(self):
        # Netzwerk: Mit CW-QRM hörten Teilnehmer bis 2.38 anderes QRM und
        # andere Gewitter, Träger und Knacker (das QRM verbrauchte je nach
        # Text verschieden viele Zufallszahlen und nahm den Text aus random).
        import random
        import numpy as np
        spec = {"levels": {"cw_qrm": 1.0, "storm": 1.0, "carrier": 1.0, "qrn": 0.5}, "gain": 1.0, "seed": 7}
        heard = []
        for disturb in (0, 1000):
            for _ in range(disturb):  # anderer Rechner: random steht woanders
                random.random()
            conditions = band.conditions(spec, 600)
            conditions.rewind()
            silent = np.zeros(band.SAMPLE_RATE * 3, dtype=np.float32)
            heard.append((conditions.cw_qrm, conditions.storm_start, conditions.carrier_switch,
                          conditions.noise_pos, self.blockwise(conditions, silent)))
        first, second = heard
        np.testing.assert_array_equal(first[0], second[0])
        self.assertEqual(first[1:4], second[1:4])
        np.testing.assert_array_equal(first[4], second[4])
        other = band.conditions(spec | {"seed": 8}, 600)
        self.assertFalse(len(other.cw_qrm) == len(first[0]) and np.array_equal(other.cw_qrm, first[0]))

    def test_strength_and_fading_are_separate(self):
        import numpy as np
        conditions = band.conditions({"levels": {"strength": 1.0}, "gain": 1.0, "seed": 2}, 600, stations=4)
        gains = [conditions.station_gain(station, 10) for station in range(4)]
        self.assertTrue(all(np.isscalar(gain) for gain in gains))  # ohne QSB kein Verlauf
        self.assertGreater(max(gains) - min(gains), 0.1)
        conditions = band.conditions({"levels": {"qsb": 1.0}, "gain": 1.0, "seed": 2}, 600, stations=4)
        starts = [float(conditions.station_gain(station, 1)[0]) for station in range(4)]
        peaks = [float(np.max(conditions.station_gain(station, 30 * band.SAMPLE_RATE))) for station in range(4)]
        self.assertTrue(all(peak > 0.95 for peak in peaks), (starts, peaks))  # nur Fading, keine Grundstärke

    def test_qrm_fades_with_qsb(self):
        import numpy as np
        conditions = band.conditions({"levels": {"cw_qrm": 1.0, "qsb": 1.0}, "gain": 1.0, "seed": 1}, 600)
        gains = conditions._fading(conditions.qrm_qsb, 30 * band.SAMPLE_RATE)
        self.assertLess(float(np.min(gains)), 0.3)
        self.assertAlmostEqual(float(np.max(gains)), 1.0, delta=0.2)

    def test_spec_keeps_valid_filter_and_offset(self):
        spec = band.clean_spec({"levels": {}, "gain": 1.0, "filter": 500, "qrm_offset": "zero"})
        self.assertEqual((spec["filter"], spec["qrm_offset"]), (500, "zero"))
        spec = band.clean_spec({"levels": {}, "gain": 1.0, "filter": 300, "qrm_offset": "beside"})
        self.assertNotIn("filter", spec)
        self.assertNotIn("qrm_offset", spec)
        self.assertNotIn("filter", band.clean_spec({"levels": {}, "gain": 1.0, "filter": True}))
        plain = {"levels": {"noise": 0.5}, "gain": 1.0}
        self.assertNotEqual(band.spec_key(plain), band.spec_key(plain | {"filter": 250}))
        self.assertNotEqual(band.spec_key(plain), band.spec_key(plain | {"qrm_offset": "near"}))


class ExtraInterferenceTest(unittest.TestCase):
    """Weitere Störungen: Gewitter, AGC-Pumpen, Flattern, Träger."""

    @staticmethod
    def run_band(spec, seconds, signal=None, seed=5):
        import numpy as np
        conditions = band.conditions(spec | {"seed": seed}, 600)
        block = 960
        out = [conditions.mix([] if signal is None else [(signal[i * block:(i + 1) * block], 0)], block)
               for i in range(int(seconds * band.SAMPLE_RATE / block))]
        return np.concatenate(out), conditions

    @staticmethod
    def tone(seconds):
        import numpy as np
        t = np.arange(int(seconds * band.SAMPLE_RATE)) / band.SAMPLE_RATE
        return (0.3 * np.sin(2 * np.pi * 600 * t)).astype(np.float32)

    def test_storm_comes_in_bursts(self):
        import numpy as np
        x, _ = self.run_band({"levels": {"storm": 1.0}, "gain": 1.0}, 60)
        second = band.SAMPLE_RATE
        loud = [bool((np.abs(x[i * second:(i + 1) * second]) > 0.05).any()) for i in range(60)]
        self.assertTrue(5 <= sum(loud) <= 40, loud)
        # In Schüben: eine Sekunde mit Knackern hat meist eine Nachbarin mit Knackern.
        neighbours = sum(1 for i in range(1, 59) if loud[i] and (loud[i - 1] or loud[i + 1]))
        self.assertGreater(neighbours, sum(loud) / 2)
        self.assertFalse(any(loud[:3]))  # nicht gleich zu Beginn

    def test_agc_pumps_after_crashes(self):
        import numpy as np
        tone = self.tone(20)
        pumped, _ = self.run_band({"levels": {"qrn": 1.0, "agc": 1.0}, "gain": 1.0}, 20, tone)
        plain, _ = self.run_band({"levels": {"qrn": 1.0}, "gain": 1.0}, 20, tone)
        window = 480

        def lowest(x):
            return min(float(np.max(np.abs(x[i:i + window]))) for i in range(0, len(x) - window, window))
        self.assertLess(lowest(pumped), 0.15)
        self.assertGreater(lowest(plain), 0.25)
        # Ohne Knacker regelt nichts.
        quiet, _ = self.run_band({"levels": {"agc": 1.0}, "gain": 1.0}, 5, self.tone(5))
        self.assertGreater(lowest(quiet), 0.29)

    def test_flutter_trembles_at_a_few_hertz(self):
        import numpy as np
        x, _ = self.run_band({"levels": {"flutter": 1.0}, "gain": 1.0}, 10, self.tone(10))
        envelope = np.array([np.max(np.abs(x[i:i + 480])) for i in range(0, len(x), 480)])
        spectrum = np.abs(np.fft.rfft(envelope - envelope.mean()))
        peak = np.fft.rfftfreq(len(envelope), 0.01)[np.argmax(spectrum)]
        self.assertTrue(4 <= peak <= 16, peak)
        self.assertLess(float(envelope.min()), 0.15)

    def test_carrier_near_the_frequency_comes_and_goes(self):
        import numpy as np
        x, conditions = self.run_band({"levels": {"carrier": 1.0}, "gain": 1.0}, 60)
        low, high = band.CARRIER_OFFSET_HZ
        self.assertTrue(low <= abs(conditions.carrier_offset) <= high)
        spectrum = np.abs(np.fft.rfft(x))
        peak = np.fft.rfftfreq(len(x), 1 / band.SAMPLE_RATE)[np.argmax(spectrum)]
        self.assertLessEqual(abs(peak - (600 + conditions.carrier_offset)), band.CARRIER_DRIFT_HZ + 2)
        second = band.SAMPLE_RATE
        on = [float(np.max(np.abs(x[i * second:(i + 1) * second]))) > 0.1 for i in range(60)]
        self.assertTrue(any(on) and not all(on), on)
        # Ein schmales Filter nimmt einen Träger weit daneben weg.
        filtered, _ = self.run_band({"levels": {"carrier": 1.0}, "gain": 1.0, "filter": 250}, 60)
        self.assertLess(float(np.max(np.abs(filtered))), float(np.max(np.abs(x))) / 3)

    def test_extras_are_not_part_of_the_levels(self):
        spec = band.spec_from_preset("medium")
        spec["levels"].update(storm=1.0, agc=1.0, flutter=1.0, carrier=1.0)
        self.assertEqual(band.preset_rank(spec), "medium")
        self.assertEqual(band.clean_spec(spec)["levels"]["carrier"], 1.0)
        conditions = band.conditions({"levels": {"carrier": 0.5}, "gain": 1.0}, 600)
        self.assertTrue(conditions.has_background)


class CentralSettingsTest(AppTestCase):
    def test_saved_and_restored_with_shared_settings(self):
        settings = self.app.band_settings
        settings.set_spec({"levels": {"noise": 0.7, "ssb": 0.2, "chirp": 0.0}, "gain": 0.8})  # 0 % wie aus
        saved = self.app._shared_settings()["band"]
        self.assertEqual(saved, {"levels": {"noise": 0.7, "ssb": 0.2}, "gain": 0.8, "version": 2})
        settings.set_preset("light")
        self.app.saved_state = {"shared": {"band": saved}}
        self.app._restore_shared_settings()
        self.assertEqual(settings.spec(), {"levels": {"noise": 0.7, "ssb": 0.2}, "gain": 0.8})
        self.assertIn("SSB-QRM 20 %", self.app.band_summary_var.get())

    def test_migrates_qso_panel_or_group_preset(self):
        settings = self.app.band_settings
        qso = {"noise": {"enabled": True, "level": 60}, "chirp": {"enabled": False, "level": 50}}
        self.app.saved_state = {"modes": {"QSO": {"band": qso}, "Gruppen": {"band": "heavy", "band_gain": 70}}}
        self.app._restore_shared_settings()
        self.assertEqual(settings.spec(), {"levels": {"noise": 0.6}, "gain": 0.7})
        self.app.saved_state = {"modes": {"QSO": {"band": {}}, "Kontinuierlich": {"band": "light"}}}
        self.app._restore_shared_settings()
        self.assertEqual(settings.spec()["levels"], band.PRESETS["light"])

    def test_window_changes_reach_running_contest_and_qso(self):
        settings = self.app.band_settings
        settings.open_window()
        try:
            qso = self.mode("QSO")
            qso.band_var.set(True)
            qso.voices = ((20, 600),)
            qso.band = band.BandConditions(1)
            settings.set_spec({"levels": {"qrn": 0.9}, "gain": 1.0})
            self.assertTrue(qso.band.enabled["qrn"])
            self.assertFalse(qso.band.enabled["noise"])
            qso.band_var.set(False)
            self.assertFalse(qso.band.active)
            settings.set_preset("heavy")
            self.assertEqual(self.app.band_settings.rank_var.get(), "Entspricht mindestens Stufe stark.")
        finally:
            settings.close_window()

    def test_strength_differences_from_older_versions(self):
        settings = self.app.band_settings
        # Bis 2.37 gehörten sie zu QSB: bleiben mit demselben Pegel an.
        self.assertTrue(settings.restore({"levels": {"qsb": 0.8, "noise": 0.5}, "gain": 1.0}))
        self.assertEqual(settings.spec()["levels"]["strength"], 0.8)
        self.assertTrue(settings.restore({"levels": {"noise": 0.5}, "gain": 1.0}))
        self.assertNotIn("strength", settings.spec()["levels"])
        # Neue Fassung: ausgeschaltet bleibt aus.
        self.assertTrue(settings.restore({"levels": {"qsb": 0.8}, "gain": 1.0, "version": 2}))
        self.assertNotIn("strength", settings.spec()["levels"])
        # Stufen-Knöpfe lassen sie, wie sie sind; zur Stufe zählen sie nicht.
        settings.set_spec({"levels": {"strength": 0.7}, "gain": 1.0})
        settings.set_preset("medium")
        self.assertEqual(settings.spec()["levels"]["strength"], 0.7)
        self.assertEqual(band.preset_rank(settings.spec()), "medium")

    def test_filter_and_offset_are_kept_by_presets_and_shown(self):
        settings = self.app.band_settings
        settings.set_spec({"levels": {"noise": 0.6, "cw_qrm": 0.3}, "gain": 1.0, "filter": 500,
                           "qrm_offset": "near"})
        settings.set_preset("heavy")
        spec = settings.spec()
        self.assertEqual((spec["filter"], spec["qrm_offset"]), (500, "near"))
        summary = settings.summary()
        self.assertIn("CW-QRM 30 % nah", summary)
        self.assertIn("Filter 500 Hz", summary)
        settings.open_window()
        try:
            self.assertIn("im Filter S/N", settings.filter_shown.cget("text"))
            self.assertIn("Rauschabstand im Filter", settings.rank_var.get())
        finally:
            settings.close_window()
        # Grundeinstellung: nicht in der Spec (ältere Versionen kennen sie nicht).
        settings.set_spec({"levels": {"noise": 0.6}, "gain": 1.0})
        self.assertEqual(settings.spec(), {"levels": {"noise": 0.6}, "gain": 1.0})

    def test_extra_group_opens_when_something_is_on(self):
        settings = self.app.band_settings
        settings.open_window()
        try:
            self.assertFalse(settings.extras_open)
            self.assertEqual(settings.extra_box.winfo_manager(), "")
            settings._toggle_extras()
            self.assertEqual(settings.extra_box.winfo_manager(), "pack")
        finally:
            settings.close_window()
        settings.set_spec({"levels": {"noise": 0.6, "storm": 0.5, "carrier": 0.4}, "gain": 1.0})
        settings.open_window()
        try:
            self.assertTrue(settings.extras_open)
            self.assertIn("Gewitter 50 %", settings.summary())
            self.assertIn("Träger 40 %", settings.summary())
        finally:
            settings.close_window()

    def test_tabs_only_save_on_or_off(self):
        for title in ("Gruppen", "Kontinuierlich", "QSO", "Contest", "Netzwerk"):
            mode = self.mode(title)
            mode.band_var.set(True)
            self.assertIs(mode.settings()["band"], True)
            mode.restore_settings({"band": None})
            self.assertIs(mode.band_var.get(), False)


class FakeStream:
    """Statt der Soundkarte: sammelt die Blöcke; `gate` hält das erste
    write() an, bis der Test es freigibt."""

    def __init__(self, gate=None):
        import threading
        self.blocks = []
        self.gate = gate
        self.writing = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, block):
        self.writing.set()
        if self.gate is not None:
            self.gate.wait(5)
        self.blocks.append(block)


class PreviewTest(AppTestCase):
    """Probehören im Bandfenster: CQ unter den eingestellten Bedingungen,
    Änderungen gleich hörbar, gesperrt während eines Durchgangs und im
    Netzwerk."""

    def setUp(self):
        super().setUp()
        from morsetrainer.widgets import band_preview
        self.band_preview = band_preview
        self.settings = self.app.band_settings
        self.settings.set_spec({"levels": {"noise": 0.5}, "gain": 1.0})
        self.patches = [mock.patch.object(band_preview, "PREVIEW_SECONDS", 1)]
        for patch in self.patches:
            patch.start()
        self.settings.open_window()

    def tearDown(self):
        self.settings.close_window()
        if self.settings.preview.thread is not None:
            self.settings.preview.thread.join(5)
        for patch in self.patches:
            patch.stop()
        super().tearDown()

    def wait_done(self):
        import time
        end = time.monotonic() + 5
        while self.settings.preview.running and time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)
        self.settings.preview.thread.join(5)
        end = time.monotonic() + 1  # bis die Abfrage im Fenster das Ende bemerkt
        while self.settings.preview_poll is not None and time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)

    def test_plays_cq_and_counts_for_nothing(self):
        import numpy as np
        from morsetrainer.core import db
        self.app.freq_var.set(700)
        self.app.station_call_var.set("dl4ym")
        self.assertEqual(self.band_preview.cq_text(self.app.station_call()), "CQ CQ DE DL4YM DL4YM K")
        self.assertEqual(self.band_preview.cq_text(""), "CQ CQ DE DL1ABC DL1ABC K")
        stream = FakeStream()
        sessions = len(db.sessions())
        with mock.patch.object(self.band_preview.audio, "output_stream", lambda: stream):
            self.settings.toggle_preview()
            self.assertEqual(self.settings.preview_button.cget("text"), "Probehören beenden")
            self.wait_done()
        out = np.concatenate(stream.blocks)
        self.assertEqual(len(out), self.band_preview.SAMPLE_RATE)  # PREVIEW_SECONDS, hier 1 s
        spectrum = np.abs(np.fft.rfft(out))
        peak = np.fft.rfftfreq(len(out), 1 / self.band_preview.SAMPLE_RATE)[np.argmax(spectrum)]
        self.assertAlmostEqual(peak, 700, delta=15)  # eigene Tonhöhe
        self.assertGreater(float(np.std(out[-2400:])), 0.001)  # Rauschen auch in der Pause
        self.assertEqual(self.settings.preview_button.cget("text"), "Probehören")
        self.assertEqual(len(db.sessions()), sessions)  # kein Durchgang in der Statistik

    def test_changes_are_heard_at_once(self):
        import threading
        gate = threading.Event()
        stream = FakeStream(gate)
        with mock.patch.object(self.band_preview.audio, "output_stream", lambda: stream):
            self.settings.toggle_preview()
            self.assertTrue(stream.writing.wait(5))
            self.assertIsNone(self.settings.preview.band.filter)
            self.settings.set_spec({"levels": {"noise": 0.5, "qrn": 0.4}, "gain": 1.0, "filter": 250})
            self.assertIsNotNone(self.settings.preview.band.filter)
            self.assertTrue(self.settings.preview.band.enabled["qrn"])
            # Zweiter Druck stoppt.
            self.settings.toggle_preview()
            gate.set()
            self.wait_done()
        self.assertLess(len(stream.blocks), 5)

    def test_blocked_during_a_run_and_in_the_network(self):
        stream = FakeStream()
        with mock.patch.object(self.band_preview.audio, "output_stream", lambda: stream):
            self.app.running_mode = True
            self.settings.toggle_preview()
            self.assertFalse(self.settings.preview.running)
            self.assertIn("erst nach dem Durchgang", self.settings.preview_var.get())
            self.assertIn("disabled", self.settings.preview_button.state())
            self.app.running_mode = False
            network = self.mode("Netzwerk")
            with mock.patch.object(network, "client", object()):
                self.settings.toggle_preview()
                self.assertFalse(self.settings.preview.running)
                self.assertIn("Netzwerk-Sitzung", self.settings.preview_var.get())
            # Ein Durchgang beginnt: Probehören hört auf.
            gate_free = FakeStream()
            with mock.patch.object(self.band_preview.audio, "output_stream", lambda: gate_free):
                self.settings.toggle_preview()
                self.assertTrue(self.settings.preview.running)
                self.app._lock_tabs()
                self.assertFalse(self.settings.preview.running)
                self.wait_done()
                self.app._unlock_tabs()
        self.assertEqual(self.settings.preview_button.cget("text"), "Probehören")
        self.assertNotIn("disabled", self.settings.preview_button.state())
        self.assertTrue(self.settings.window.bind("<Control-p>"))


class StatisticsTest(AppTestCase):
    def test_runs_with_band_conditions_do_not_feed_the_character_statistics(self):
        g = self.mode("Gruppen")
        g.band_var.set(True)
        g.start()
        try:
            self.assertFalse(g.session_stats.char_stats)
            self.assertIn("disabled", g.band_toggle.check.state())  # an/aus gesperrt
        finally:
            g.stop()
        self.assertNotIn("disabled", g.band_toggle.check.state())
        g.band_var.set(False)
        g.start()
        try:
            self.assertTrue(g.session_stats.char_stats)
        finally:
            g.stop()


class SequenceBandTrackingTest(AppTestCase):
    def test_weakest_conditions_of_the_run_are_logged(self):
        g = self.mode("Gruppen")
        self.app.band_settings.set_preset("heavy")
        g.band_var.set(True)
        g.start()
        g.running = True
        config = tests.session_lines(g.session_stats.session_id)[0]
        self.assertEqual((config["band"], config["band_gain"]), ("heavy", 100))
        self.app.band_settings.set_preset("light")  # mitten im Durchgang leichter gestellt
        g.current_sequence, g.voice = "KM", (20, 600)
        with mock.patch.object(g, "_play", return_value=False):
            g.play_current()
        self.assertEqual(g.band.levels["noise"], band.PRESETS["light"]["noise"])
        with mock.patch.object(g.session_stats, "finalize") as finalize:
            g._finalize_session()
        extra = finalize.call_args[0][0]
        self.assertEqual((extra["band_min"], extra["band_gain_min"]), ("light", 100))
        g.running = False


if __name__ == "__main__":
    unittest.main()
