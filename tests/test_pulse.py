"""Ausgabeweg PulseAudio: Auswahl und Rückfall auf PortAudio."""
import time
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


class FakeStream:
    """Ersatz für PulseStream: zählt Schreibaufrufe, ohne Gerät."""
    opened = []

    def __init__(self, samplerate, latency, name="Morsetrainer"):
        self.latency, self.closed, self.writes = latency, False, 0
        FakeStream.opened.append(self)

    def write(self, samples):
        self.writes += 1
        time.sleep(0.005)
        return False

    def flush(self):
        pass

    def close(self):
        self.closed = True


class SinkChangeTest(unittest.TestCase):
    def test_new_default_sink_reopens_the_stream(self):
        FakeStream.opened = []
        sinks = ["lautsprecher"]
        with mock.patch.object(pulse, "PulseStream", FakeStream), \
                mock.patch.object(pulse, "default_sink", lambda: sinks[0]), \
                mock.patch.object(pulse, "_SINK_POLL_SECONDS", 0.01):
            player = pulse.Player(48000, 0.05)
            try:
                time.sleep(0.1)
                self.assertEqual(len(FakeStream.opened), 1)  # kein Wechsel, kein Neuöffnen
                sinks[0] = "bluetooth-kopfhoerer"
                deadline = time.time() + 2
                while len(FakeStream.opened) < 2 and time.time() < deadline:
                    time.sleep(0.01)
                self.assertEqual(len(FakeStream.opened), 2)
                old, new = FakeStream.opened
                self.assertTrue(old.closed)
                self.assertIs(player.stream, new)
                time.sleep(0.05)
                self.assertGreater(new.writes, 0)
            finally:
                player.close()

    def test_failed_reopen_keeps_the_old_stream(self):
        FakeStream.opened = []
        sinks = ["a"]

        def opener(samplerate, latency, name="Morsetrainer"):
            if FakeStream.opened:
                raise pulse.PulseError("weg")
            return FakeStream(samplerate, latency, name)

        with mock.patch.object(pulse, "PulseStream", opener), \
                mock.patch.object(pulse, "default_sink", lambda: sinks[0]), \
                mock.patch.object(pulse, "_SINK_POLL_SECONDS", 0.01):
            player = pulse.Player(48000, 0.05)
            try:
                sinks[0] = "b"
                time.sleep(0.2)
                self.assertTrue(player.alive)
                self.assertIs(player.stream, FakeStream.opened[0])
                self.assertFalse(FakeStream.opened[0].closed)
            finally:
                player.close()

    def test_without_pactl_no_sink(self):
        with mock.patch.object(pulse.shutil, "which", return_value=None):
            self.assertIsNone(pulse.default_sink())


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


class ErrorLogPathTest(unittest.TestCase):
    def test_entry_names_the_output_path(self):
        import tempfile
        from pathlib import Path

        from morsetrainer.core import errorlog
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(errorlog, "LOG_FILE", Path(tmp) / "fehler.log"), \
                mock.patch.object(audio, "active_path", return_value="PulseAudio"):
            errorlog.record(ValueError, ValueError("x"), None, version="9.9")
            errorlog.take_unseen()
            text = (Path(tmp) / "fehler.log").read_text(encoding="utf-8")
        self.assertIn("Tonausgabe: PulseAudio", text)
