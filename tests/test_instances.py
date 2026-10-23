"""Welche Fenster mit dem Datenordner arbeiten (core/instances.py)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import instances


class InstancesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.folder = self.dir / instances.DIR_NAME
        self.folder.mkdir()

    def test_no_other_window(self):
        self.assertEqual(instances.others(self.dir), 0)
        self.assertEqual(instances.others(self.dir / "gibt-es-nicht"), 0)

    def test_own_entry_does_not_count(self):
        with mock.patch("atexit.register"):
            instances.register(self.dir)
        self.assertTrue((self.folder / str(os.getpid())).exists())
        self.assertEqual(instances.others(self.dir), 0)

    def test_running_process_counts_and_dead_one_is_cleaned_up(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            (self.folder / str(child.pid)).touch()
            self.assertEqual(instances.others(self.dir), 1)
        finally:
            child.kill()
            child.wait()
        self.assertEqual(instances.others(self.dir), 0)
        self.assertFalse((self.folder / str(child.pid)).exists())

    def test_foreign_files_are_ignored(self):
        (self.folder / "notizen.txt").touch()
        self.assertEqual(instances.others(self.dir), 0)
        self.assertTrue((self.folder / "notizen.txt").exists())


if __name__ == "__main__":
    unittest.main()
