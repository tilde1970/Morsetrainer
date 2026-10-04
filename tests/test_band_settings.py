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
        spec["levels"]["noise"] = 0.3  # leiser als mittel, lauter als leicht
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


class NetworkMessageTest(unittest.TestCase):
    def test_spec_travels_with_preset_for_older_versions(self):
        spec = {"levels": {"noise": 0.5, "qsb": 0.9, "qrn": 0.4}, "gain": 1.2}
        fields = network_mode.band_fields(spec)
        self.assertEqual(fields["band"], "medium")
        self.assertEqual(network_mode.message_spec(fields), spec)
        # Schwächer als jede Stufe: ältere Teilnehmer bekommen wenigstens „leicht“.
        self.assertEqual(network_mode.band_fields({"levels": {"ssb": 0.3}, "gain": 1.0})["band"], "light")
        self.assertEqual(network_mode.band_fields(None), {"band": None})
        self.assertIsNone(network_mode.message_spec({"band": None}))

    def test_message_from_older_trainer_uses_preset(self):
        self.assertEqual(network_mode.message_spec({"band": "heavy"}), band.spec_from_preset("heavy"))
        self.assertIsNone(network_mode.message_spec({"band": ["heavy"]}))


class CentralSettingsTest(AppTestCase):
    def test_saved_and_restored_with_shared_settings(self):
        settings = self.app.band_settings
        settings.set_spec({"levels": {"noise": 0.7, "ssb": 0.2}, "gain": 0.8})
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
