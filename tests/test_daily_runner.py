"""Tests für den Ablauf der Tagesübung im Hauptfenster (daily_runner.py)."""
import time
from datetime import date
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import daily_runner
from morsetrainer.core import daily, koch, review
from tests.test_modes import AppTestCase


REAL_PLAN = daily.plan


def short_plan(lesson, due_count, today):
    """Wie daily.plan, aber Blöcke von wenigen Sekunden."""
    return [daily.Block(b.kind, b.mode, 0.01, b.params) for b in REAL_PLAN(lesson, due_count, today)]


class DailyRunnerTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.app.charset_var.set(koch.lesson_charset(12))
        self.app.wpm_var.set(20)
        self.app.farnsworth_enabled_var.set(True)
        self.app.farnsworth_wpm_var.set(12)
        self.app.weighted_var.set(False)
        self.runner = self.app.daily

    def _end_block(self):
        """Laufenden Block wie nach Ablauf der Zeit beenden und den nächsten starten."""
        mode = self.runner.mode
        if hasattr(mode, "block_end"):
            mode.block_end = time.time() - 1
            mode.next_char()
        else:
            mode.stop()
        if self.runner.next_id is not None:
            self.app.root.after_cancel(self.runner.next_id)
            self.runner._next_block()

    def test_start_uses_lesson_and_daily_tempo(self):
        self.app.charset_var.set("KMR")  # eigener Zeichensatz: Lektion aus dem Feld
        self.app.lesson_var.set(12)
        self.runner.start()
        self.assertTrue(self.runner.active)
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(12))
        self.assertTrue(self.app.weighted_var.get())
        single = self.runner.mode
        self.assertIs(single, self.mode("Einzelzeichen"))
        self.assertTrue(single.running)
        self.assertIsNotNone(single.block_end)
        self.assertEqual(single.options_card.winfo_manager(), "")
        self.assertEqual(daily.load()["tempo"], {"wpm": 20, "effective": 12})

    def test_abort_restores_settings_and_keeps_tabs_free(self):
        self.app.charset_var.set("KMR")
        self.runner.start()
        self.runner.abort()
        self.assertFalse(self.runner.active)
        self.assertEqual((self.app.charset_var.get(), self.app.weighted_var.get()), ("KMR", False))
        self.assertEqual((self.app.wpm_var.get(), self.app.farnsworth_wpm_var.get()), (20, 12))
        self.assertFalse(self.app.running_mode)
        self.assertTrue(all(self.app.notebook.tab(t, "state") == "normal" for t in self.app.notebook.tabs()))
        self.assertEqual(str(self.app.daily_bar.start_button["state"]), "normal")
        self.assertNotEqual(self.mode("Einzelzeichen").options_card.winfo_manager(), "")
        self.assertEqual(review.focus, set())

    def test_escape_aborts(self):
        self.runner.start()
        self.app._dispatch_key(type("E", (), {"keysym": "Escape", "widget": self.app.root})())
        self.assertFalse(self.runner.active)

    def test_full_run_goes_through_all_blocks(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            seen = []
            while self.runner.active:
                seen.append(self.runner.blocks[self.runner.index].mode)
                self._end_block()
        self.assertEqual(seen, ["single", "group", "word"])
        entry = daily.load()["days"][date.today().isoformat()]
        self.assertEqual([b["kind"] for b in entry["blocks"]], [daily.WARMUP, daily.MAIN, daily.OUTRO])
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(12))  # zurückgestellt
        self.assertEqual(self.app.notebook.index("current"), self.app.mode_titles.index("Wörter"))

    def test_block_that_cannot_start_falls_back_to_groups(self):
        self.app.charset_var.set(koch.lesson_charset(3))  # zu wenige Wörter
        with mock.patch.object(daily, "plan", lambda *a: [daily.Block(daily.OUTRO, "word", 0.01)]):
            self.runner.start()
            self.assertEqual(self.runner.blocks[0].mode, "group")
            self.assertTrue(self.mode("Gruppen").running)
            self.runner.abort()

    def test_no_lesson_question_during_daily(self):
        with mock.patch.object(daily, "plan", short_plan), \
                mock.patch.object(daily_runner.daily, "finish_block", return_value=[]), \
                mock.patch("morsetrainer.app.messagebox.askyesno") as ask:
            self.runner.start()
            while self.runner.active:
                if self.runner.mode is self.mode("Gruppen"):
                    self.runner.mode.koch_result = (koch.lesson_charset(12), 50, 50)
                self._end_block()
        ask.assert_not_called()

    def _end_block_only(self):
        """Laufenden Block beenden, ohne den nächsten zu starten."""
        mode = self.runner.mode
        if hasattr(mode, "block_end"):
            mode.block_end = time.time() - 1
            mode.next_char()
        else:
            mode.stop()

    def test_card_between_blocks_and_enter_continues(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            self._end_block_only()
            self.assertTrue(self.runner.card_open)
            self.assertIsNone(self.runner.mode)
            self.assertEqual(self.app.daily_bar.card.winfo_manager(), "pack")
            self.assertIn("Aufwärmen", str(self.app.daily_bar.card.cget("text")))
            self.app._dispatch_key(type("E", (), {"keysym": "Return", "widget": self.app.root})())
            self.assertFalse(self.runner.card_open)
            self.assertIs(self.runner.mode, self.mode("Gruppen"))
            self.assertEqual(self.app.daily_bar.card.winfo_manager(), "")
            self.runner.abort()

    def test_escape_on_card_ends_daily(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            self._end_block_only()
            self.app._dispatch_key(type("E", (), {"keysym": "Escape", "widget": self.app.root})())
        self.assertFalse(self.runner.active)
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(12))
        self.assertIsNotNone(self.runner.summary.window)  # kurze Bilanz
        self.assertIsNone(self.runner.summary.extra_button)
        self.runner.summary.close()

    def test_full_run_shows_summary_and_quiet_abort_does_not(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            while self.runner.active:
                self._end_block()
        self.assertIsNotNone(self.runner.summary.window)
        self.runner.summary.close()
        self.runner.summary = None
        self.runner.start()
        self.runner.abort(quiet=True)
        self.assertIsNone(self.runner.summary)

    def test_extra_runs_one_block_once(self):
        self.runner.start_extra((daily.CONFUSIONS, "BD"))
        self.assertTrue(self.runner.active)
        self.assertEqual(self.app.charset_var.get(), "BD")
        self.assertIs(self.runner.mode, self.mode("Einzelzeichen"))
        self.runner.abort()
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(12))
        self.assertIsNone(self.runner.summary)  # nach der Zugabe keine zweite Bilanz
        self.assertTrue(daily.load()["days"][date.today().isoformat()][daily.EXTRA])

    def test_rufz_extra(self):
        self.app.lesson_var.set(35)  # genug Zeichen für Rufzeichen
        self.runner.start_extra((daily.RUFZ, ""))
        mode = self.mode("Rufzeichen")
        self.assertIs(self.runner.mode, mode)
        self.assertTrue(mode.rufz_active)
        self.runner.abort()
        self.assertFalse(mode.rufz_var.get())  # Einstellung zurückgestellt

    def test_new_lesson_plays_new_char_first(self):
        state = {"lesson": 12, "lesson_since": date.today().isoformat(), "days": {}}
        daily.save(state)
        with mock.patch.object(self.app, "_play_new_char") as play:
            self.runner.start()
        play.assert_called_once()
        self.assertTrue(self.runner.card_open)
        self.assertIn("Neues Zeichen", str(self.app.daily_bar.card.cget("text")))
        self.runner.continue_now()
        self.assertIs(self.runner.mode, self.mode("Einzelzeichen"))
        self.runner.abort(quiet=True)
