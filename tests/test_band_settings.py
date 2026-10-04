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


class CentralSettingsTest(AppTestCase):
    def test_saved_and_restored_with_shared_settings(self):
        settings = self.app.band_settings
        settings.set_spec({"levels": {"noise": 0.7, "ssb": 0.2, "chirp": 0.0}, "gain": 0.8})  # 0 % wie aus
        saved = self.app._shared_settings()["band"]
        self.assertEqual(saved, {"levels": {"noise": 0.7, "ssb": 0.2}, "gain": 0.8})
        settings.set_preset("light")
        self.app.saved_state = {"shared": {"band": saved}}
        self.app._restore_shared_settings()
        self.assertEqual(settings.spec(), saved)
        self.assertIn("SSB 20 %", self.app.band_summary_var.get())

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

    def test_tabs_only_save_on_or_off(self):
        for title in ("Gruppen", "Kontinuierlich", "QSO", "Contest", "Netzwerk"):
            mode = self.mode(title)
            mode.band_var.set(True)
            self.assertIs(mode.settings()["band"], True)
            mode.restore_settings({"band": None})
            self.assertIs(mode.band_var.get(), False)


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
