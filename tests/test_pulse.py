"""Ausgabeweg PulseAudio: Auswahl und Rückfall auf PortAudio."""
import unittest
from unittest import mock

import numpy as np

from morsetrainer.core import audio, pulse


class PulseChoiceTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, audio, "_pulse_failed", audio._pulse_failed)
        self.addCleanup(setattr, audio, "_player", audio._player)
        audio._pulse_failed, audio._player = False, None

    def test_env_portaudio_turns_pulse_off(self):
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "portaudio"}):
            self.assertFalse(audio._use_pulse())

    def test_auto_uses_pulse_on_linux_when_available(self):
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "auto"}), \
                mock.patch.object(audio.sys, "platform", "linux"), \
                mock.patch.object(pulse, "available", return_value=True):
            self.assertTrue(audio._use_pulse())
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "auto"}), \
                mock.patch.object(audio.sys, "platform", "win32"), \
                mock.patch.object(pulse, "available", return_value=True):
            self.assertFalse(audio._use_pulse())

    def test_play_falls_back_to_portaudio_when_pulse_cannot_open(self):
        samples = np.zeros(480, dtype=np.float32)
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "auto"}), \
                mock.patch.object(audio.sys, "platform", "linux"), \
                mock.patch.object(pulse, "available", return_value=True), \
                mock.patch.object(pulse, "Player", side_effect=pulse.PulseError("kein Server")), \
                mock.patch.object(audio.sd, "play") as sd_play:
            audio.play(samples)
        sd_play.assert_called_once()
        self.assertTrue(audio._pulse_failed)

    def test_pulse_player_gets_the_tone(self):
        player = mock.Mock(alive=True)
        audio._player = player
        samples = np.zeros(480, dtype=np.float32)
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "auto"}), \
                mock.patch.object(audio.sys, "platform", "linux"), \
                mock.patch.object(pulse, "available", return_value=True):
            audio.play(samples)
            audio.stop()
        player.play.assert_called_once_with(samples)
        player.cancel.assert_called_once()


class BackendDescriptionTest(unittest.TestCase):
    def test_reasons_for_portaudio(self):
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "portaudio"}), \
                mock.patch.object(audio.sys, "platform", "linux"):
            self.assertIn("MORSETRAINER_AUDIO", audio.backend_description())
        with mock.patch.dict("os.environ", {"MORSETRAINER_AUDIO": "auto"}), \
                mock.patch.object(audio.sys, "platform", "linux"), \
                mock.patch.object(pulse, "available", return_value=False):
            self.assertIn("libpulse-simple", audio.backend_description())
        with mock.patch.object(audio.sys, "platform", "win32"):
            self.assertEqual(audio.backend_description(), "PortAudio")

    def test_server_missing_and_present(self):
        env = {"MORSETRAINER_AUDIO": "auto"}
        with mock.patch.dict("os.environ", env), mock.patch.object(audio.sys, "platform", "linux"), \
                mock.patch.object(pulse, "available", return_value=True):
            with mock.patch.object(pulse, "PulseStream", side_effect=pulse.PulseError("Verbindung")):
                self.assertIn("kein PulseAudio-Server", audio.backend_description())
            with mock.patch.object(pulse, "PulseStream"):
                self.assertEqual(audio.backend_description(), "PulseAudio direkt")
