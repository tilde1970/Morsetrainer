"""Gesamtstatistik zurücksetzen (stats.reset_all_time, app._reset_all_time): Gelingt es nicht,
bleibt alles wie es war, und man erfährt es."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import db, review, stats
from tests.test_modes import AppTestCase, app_module


class ResetStatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(stats, "STATS_DIR", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)
        db.save_state(stats.ALL_TIME_KEY, {"chars": {"K": {"good": 3}}})
        review._save({"K": {"box": 2, "due": "2026-10-10"}})

    def test_success_clears_everything_and_returns_nothing(self):
        self.assertIsNone(stats.reset_all_time())
        self.assertEqual(db.load_state(stats.ALL_TIME_KEY, {}), {})
        self.assertEqual(review.load(), {})
        self.assertIn("time", db.load_state(stats.RESET_KEY, {}))

    def test_failure_leaves_everything_as_it_was_and_reports_why(self):
        with mock.patch.object(review, "reset", side_effect=db.Error("Datenbank ist gesperrt")):
            error = stats.reset_all_time()
        self.assertEqual(error, "Datenbank ist gesperrt")
        # Eine Transaktion: auch das schon Gelöschte (Gesamtstatistik) ist wieder da.
        self.assertEqual(db.load_state(stats.ALL_TIME_KEY, {}), {"chars": {"K": {"good": 3}}})
        self.assertIn("K", review.load())
        self.assertEqual(db.load_state(stats.RESET_KEY, {}), {})

    def test_failure_without_a_message_still_names_the_kind_of_error(self):
        with mock.patch.object(db, "delete_state", side_effect=OSError()):
            self.assertEqual(stats.reset_all_time(), "OSError")


class ResetDialogTest(AppTestCase):
    def test_failed_reset_is_reported_and_the_display_stays(self):
        with mock.patch.object(app_module.dialog, "askyesno", return_value=True), \
                mock.patch.object(app_module.stats, "reset_all_time", return_value="Datenbank ist gesperrt"), \
                mock.patch.object(app_module.dialog, "showerror") as error, \
                mock.patch.object(self.app, "_refresh_all_time") as refresh:
            self.app._reset_all_time()
        error.assert_called_once()
        self.assertIn("Datenbank ist gesperrt", error.call_args[0][1])
        self.assertIn("unverändert", error.call_args[0][1])
        refresh.assert_not_called()

    def test_successful_reset_refreshes_without_an_error_message(self):
        with mock.patch.object(app_module.dialog, "askyesno", return_value=True), \
                mock.patch.object(app_module.stats, "reset_all_time", return_value=None), \
                mock.patch.object(app_module.dialog, "showerror") as error, \
                mock.patch.object(self.app, "_refresh_all_time") as refresh:
            self.app._reset_all_time()
        error.assert_not_called()
        refresh.assert_called_once()

    def test_declined_reset_does_nothing(self):
        with mock.patch.object(app_module.dialog, "askyesno", return_value=False), \
                mock.patch.object(app_module.stats, "reset_all_time") as reset:
            self.app._reset_all_time()
        reset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
