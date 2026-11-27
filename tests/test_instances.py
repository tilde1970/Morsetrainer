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

    def test_foreign_process_counts_and_missing_one_is_cleaned_up(self):
        entry = self.folder / "4242"
        entry.touch()
        with mock.patch.object(instances.os, "kill", side_effect=PermissionError):
            self.assertEqual(instances.others(self.dir), 1)
        self.assertTrue(entry.exists())
        with mock.patch.object(instances.os, "kill", side_effect=ProcessLookupError):
            self.assertEqual(instances.others(self.dir), 0)
        self.assertFalse(entry.exists())

    def test_no_other_window(self):
        self.assertEqual(instances.others(self.dir), 0)
        self.assertEqual(instances.others(self.dir / "gibt-es-nicht"), 0)

    def test_own_entry_does_not_count(self):
        with mock.patch("atexit.register"):
            instances.register(self.dir)
        self.assertTrue((self.folder / str(os.getpid())).exists())
        self.assertEqual(instances.others(self.dir), 0)

    def test_unregister_removes_the_own_entry_even_without_atexit(self):
        # Das Programm endet mit os._exit, das atexit überspringt: unregister() räumt selbst auf.
        with mock.patch("atexit.register"):
            instances.register(self.dir)
        mine = self.folder / str(os.getpid())
        self.assertTrue(mine.exists())
        instances.unregister()
        self.assertFalse(mine.exists())
        instances.unregister()  # ein zweites Mal ist harmlos

    def test_entries_with_impossible_process_numbers_never_block(self):
        # os.kill(0, …) träfe die ganze Prozessgruppe: solche Nummern gelten als nicht laufend.
        for name in ("0", "-5"):
            (self.folder / name).touch()
        with mock.patch.object(instances.os, "kill") as kill:
            self.assertEqual(instances.others(self.dir), 0)
        kill.assert_not_called()
        self.assertEqual(list(self.folder.iterdir()), [])

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
