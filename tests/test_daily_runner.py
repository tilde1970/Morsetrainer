"""Tests für den Ablauf der Tagesübung im Hauptfenster (daily_runner.py)."""
import time
import unittest
from datetime import date
from tkinter import ttk
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer import daily_runner
from morsetrainer.core import band, daily, koch, review
from tests.test_modes import AppTestCase, app_module


REAL_PLAN = daily.plan


class ModeNameTest(unittest.TestCase):
    def test_outro_names_band_level_and_contest(self):
        from morsetrainer.widgets.daily_panel import mode_name
        self.assertEqual(mode_name(daily.band_outro("light")), "Am Stück mit Band leicht")
        contest = daily.Block(daily.OUTRO, daily.QSO_LOG, 3.5, {"kind": "wag"})
        self.assertEqual(mode_name(contest), "QSO-Abfrage, Contest WAG (DOK)")
        self.assertEqual(daily_runner.block_text(contest), "Tagesübung, Ausklang: QSO-Abfrage, Contest WAG (DOK), 3,5 Minuten.")


def short_plan(*args, **kwargs):
    """Wie daily.plan, aber Blöcke von wenigen Sekunden."""
    return [daily.Block(b.kind, b.mode, 0.01, b.params) for b in REAL_PLAN(*args, **kwargs)]


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
        if self.runner.card_open:
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

    def _key(self, keysym):
        self.app._dispatch_key(type("E", (), {"keysym": keysym, "widget": self.app.root})())

    def test_escape_twice_aborts(self):
        # Ein einzelner Fehlgriff (Esc für ein Nebenfenster, F5 aus Gewohnheit)
        # kostet nicht den Tag; erst der zweite Druck beendet.
        self.runner.start()
        self._key("Escape")
        self.assertTrue(self.runner.active)
        self.assertTrue(self.runner.mode.running)
        self.assertEqual(self.app.daily_bar.notice_var.get(), "Noch einmal Esc beendet die Tagesübung.")
        self._key("Escape")
        self.assertFalse(self.runner.active)
        self.assertEqual(self.app.daily_bar.notice_var.get(), "")

    def test_second_key_too_late_only_warns_again(self):
        self.runner.start()
        self._key("F5")
        self.assertEqual(self.app.daily_bar.notice_var.get(), "Noch einmal F5 beendet die Tagesübung.")
        self.app.daily_end_pressed -= app_module.DAILY_END_CONFIRM_S + 1
        self._key("F5")
        self.assertTrue(self.runner.active)
        self._key("Escape")
        self.assertFalse(self.runner.active)

    def test_end_buttons_say_they_end_the_daily_practice(self):
        self.runner.start()
        self.assertEqual(self.runner.mode.start_button.cget("text"), "Tagesübung beenden (Esc)")
        self.assertNotEqual(str(self.runner.mode.start_button.cget("style")), "Accent.TButton")
        button = self.runner.mode.start_button
        self.app.daily_bar.end_button.invoke()
        self.assertFalse(self.runner.active)
        self.assertEqual(self.mode("Einzelzeichen").start_button.cget("text"), "Start (F5)")
        self.assertEqual(str(button.cget("style")), "Accent.TButton")  # der Start ist wieder blau

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
        # Auch die Inhaltswahl im Reiter Einzeln ist wieder wie vorher.
        self.assertEqual(self.app.one_by_one_var.get(), "Einzelzeichen")
        self.assertEqual(self.app._tab_name(), "Einzeln, Zeichen")

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
                mock.patch("morsetrainer.app.dialog.askyesno") as ask:
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
            enter = type("E", (), {"keysym": "Return", "widget": self.app.root})()
            self.app._dispatch_key(enter)
            self.assertTrue(self.runner.card_open)  # Enter gleich danach gehört noch zur Antwort
            self.runner.card_shown -= daily_runner.ENTER_GRACE_S
            self.app._dispatch_key(enter)
            self.assertFalse(self.runner.card_open)
            self.assertIs(self.runner.mode, self.mode("Gruppen"))
            self.assertEqual(self.app.daily_bar.card.winfo_manager(), "")
            self.runner.abort()

    def test_card_waits_for_continue_button(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            self._end_block_only()
            self.runner.card_shown -= 60  # auch nach einer Minute: kein Weiter von selbst
            self.app.root.update()
            self.assertTrue(self.runner.card_open)
            self.assertIsNone(self.runner.mode)
            button = next(w for w in self.app.daily_bar.card.winfo_children()[1].winfo_children()
                          if isinstance(w, ttk.Button))
            button.invoke()
            self.assertFalse(self.runner.card_open)
            self.assertIs(self.runner.mode, self.mode("Gruppen"))
            self.runner.abort()

    def test_escape_on_card_ends_daily(self):
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.start()
            self._end_block_only()
            self._key("Escape")
            self.assertTrue(self.runner.active)
            self._key("Escape")
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

    def test_summary_points_to_prosign_lessons_once(self):
        daily.save({"lesson": daily.POST_KOCH, "days": {}})
        self.app.lesson_var.set(koch.FINAL_LESSON)
        self.app._apply_lesson()
        self.runner.state, self.runner.today = daily.load(), date.today()
        self.runner._show_summary(set(), True)
        summary = self.runner.summary
        self.assertIsNotNone(summary.prosign_button)
        self.assertIn("AR, KN, SK und BK", summary.spoken)
        self.assertIn("Mit Tab: Lektion 42 einstellen.", summary.spoken)
        summary.prosign_button.invoke()
        self.assertIsNone(summary.window)
        self.assertEqual(self.app.lesson_var.get(), koch.FINAL_LESSON + 1)
        self.assertEqual(self.app.charset_var.get(), koch.lesson_charset(koch.FINAL_LESSON + 1))
        self.assertEqual(daily.load()[daily.PROSIGN_HINT], date.today().isoformat())
        self.app.lesson_var.set(koch.FINAL_LESSON)
        self.runner._show_summary(set(), True)  # nur einmal
        self.assertIsNone(self.runner.summary.prosign_button)
        self.runner.summary.close()

    def _qso_outro(self, mode):
        """Tagesübung nur mit einem QSO-Ausklang starten und das QSO zu Ende spielen."""
        import contextlib
        from morsetrainer.modes import qso_mode

        class FakeStream:  # spielt sofort, ohne Gerät
            latency = 0.0

            def write(self, block):
                pass

        block = daily.Block(daily.OUTRO, mode, daily.OUTRO_POST_MINUTES, {"kind": "cqww"} if mode == daily.QSO_LOG else {})
        with mock.patch.object(daily, "plan", lambda *args, **kwargs: [block]), \
                mock.patch.object(qso_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())):
            self.runner.start()
            qso = self.mode("QSO")
            self.assertIs(self.runner.mode, qso)
            end = time.monotonic() + 20
            while qso.running and time.monotonic() < end:
                self.root.update()
                time.sleep(0.01)
        self.assertFalse(qso.running)
        self.assertIsNone(qso.audio_error)
        return qso

    def test_qso_outro_ends_with_the_check_not_with_the_playback(self):
        qso = self._qso_outro(daily.QSO_HEAD)
        self.assertEqual(qso.settings()["eval"], "head")
        self.assertEqual(qso.options_card.winfo_manager(), "")  # Einstellungen ausgeblendet
        self.assertTrue(self.runner.active)  # Fragen stehen noch aus
        self.assertEqual(str(qso.replay_button["state"]), "disabled")
        qso.on_function_key("F6")  # gesperrt, aber nicht still
        self.assertEqual(qso.status_var.get(), "In der Tagesübung zählt das erste Hören – kein „Nochmal“.")
        first = qso.quiz.entries[min(qso.quiz.entries)]
        with mock.patch.object(first, "focus_set") as focus:
            qso.running, qso.play_thread = True, None  # das Ende noch einmal, mit beobachtetem Fokus
            qso._finish()
        focus.assert_called_once()
        qso.quiz.check()
        self.assertFalse(self.runner.active)
        self.assertIn("Tagesübung geschafft", self.runner.summary.spoken)
        block = daily.load()["days"][date.today().isoformat()]["blocks"][-1]
        self.assertEqual((block["mode"], block["checked"], block["total"]), (daily.QSO_HEAD, True, 3))
        self.assertEqual(block["minutes"], daily.OUTRO_POST_MINUTES)  # zählt als ganzer Ausklang
        self.runner.summary.close()
        self.assertEqual(qso.settings()["eval"], "quiz")  # Einstellungen des Reiters zurück
        self.assertEqual(qso.start_button["text"], "Neues QSO (F5)")

    def test_qso_outro_instruction_is_not_cut_by_the_field(self):
        from morsetrainer.modes import qso_mode
        qso = self._qso_outro(daily.QSO_HEAD)
        key = min(qso.quiz.entries)
        with mock.patch.object(qso_mode.announcer, "say") as say:
            qso.running, qso.play_thread = True, None  # das Ende noch einmal, mit beobachteter Ansage
            qso._finish()
            qso.quiz._announce_field(key)  # FocusIn des ersten Felds: still
        self.assertEqual(len(say.call_args_list), 1)
        text = say.call_args.args[0]
        self.assertTrue(text.startswith("QSO zu Ende. 3 Fragen. Erstes Feld: "), text)
        self.assertTrue(text.endswith("Tab: nächstes Feld, F8 prüft."), text)
        with mock.patch.object(qso_mode.announcer, "say") as say:
            qso.quiz._announce_field(key)  # später wieder mit Feldansage
        say.assert_called_once()
        self.runner.abort(quiet=True)

    def test_qso_outro_without_check_is_not_completed(self):
        qso = self._qso_outro(daily.QSO_LOG)
        self.assertEqual(qso.settings()["kind"], "cqww")
        qso.toggle_running()  # Knopf „Tagesübung beenden“ statt eines neuen QSOs
        self.assertFalse(self.runner.active)
        self.assertIn("kein Stern", self.runner.summary.spoken)
        self.runner.summary.close()
        # Danach wieder ein gewöhnlicher QSO-Reiter.
        self.assertEqual(qso.start_button["text"], "Neues QSO (F5)")
        self.assertEqual(str(qso.replay_button["state"]), "normal")
        self.assertEqual(qso.status_var.get(), "QSO beendet.")

    def test_skip_qso_swaps_the_block_for_callsigns_of_the_same_length(self):
        import contextlib
        from morsetrainer.modes import qso_mode

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        self.app.lesson_var.set(koch.FINAL_LESSON)  # genug Zeichen für Rufzeichen
        block = daily.Block(daily.OUTRO, daily.QSO_LOG, daily.OUTRO_POST_MINUTES, {"kind": "cqww"})
        with mock.patch.object(daily, "plan", lambda *args, **kwargs: [block]), \
                mock.patch.object(qso_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())):
            self.runner.start()
            qso = self.mode("QSO")
            self.assertEqual(self.runner.bar.skip_button.winfo_manager(), "pack")
            with mock.patch.object(self.runner, "_start_block") as start_block:
                self.runner.skip_qso()
                self.root.update()
            self.assertFalse(qso.running)
            self.assertTrue(self.runner.active)
            swapped = start_block.call_args.args[0]
            self.assertEqual((swapped.mode, swapped.minutes), ("callsign", daily.OUTRO_POST_MINUTES))
            self.assertIs(self.runner.blocks[0], swapped)
            self.assertIsNone(self.runner.mode)
            self.assertEqual(self.runner.bar.skip_button.winfo_manager(), "")
            self.runner.abort(quiet=True)
        self.assertFalse(self.runner.active)

    def test_skip_is_not_offered_during_the_questions_and_is_announced(self):
        import contextlib
        from morsetrainer.i18n import skip_key
        from morsetrainer.modes import qso_mode

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        block = daily.Block(daily.OUTRO, daily.QSO_LOG, daily.OUTRO_POST_MINUTES, {"kind": "cqww"})
        with mock.patch.object(daily, "plan", lambda *args, **kwargs: [block]), \
                mock.patch.object(qso_mode.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())), \
                mock.patch.object(daily_runner.announcer, "say",
                                  side_effect=lambda text, then=None, **kw: then and then()) as say:
            self.runner.start()
            self.assertIn(f"Überspringen mit {skip_key()}.", say.call_args_list[0].args[0])
            qso = self.mode("QSO")
            self.assertTrue(self.runner._skippable())
            self.assertIn(skip_key(), self.runner.spoken_status())
            end = time.monotonic() + 20
            while qso.running and time.monotonic() < end:
                self.root.update()
                time.sleep(0.01)
            self.assertFalse(qso.running)  # jetzt die Abfrage
            self.assertFalse(self.runner._skippable())
            self.assertNotIn(skip_key(), self.runner.spoken_status())
            self.runner.skip_qso()
            self.assertIs(self.runner.blocks[0], block)
            self.assertIs(self.runner.mode, qso)
            self.runner.abort(quiet=True)

    def test_qso_outros_can_be_turned_off(self):
        self.app.lesson_var.set(koch.FINAL_LESSON)
        self.runner.state = {}
        seen = []

        def fake_plan(lesson, due, turn, qso=frozenset(), *args, **kwargs):
            seen.append(set(qso))
            return [daily.Block(daily.OUTRO, "callsign", 1)]

        with mock.patch.object(daily, "plan", fake_plan), mock.patch.object(daily, "stage", lambda lesson: daily.POST), \
                mock.patch.object(daily, "qso_outros", lambda *args: {daily.QSO_LOG}), \
                mock.patch.object(daily_runner.announcer, "say"):
            self.app.daily_qso_var.set(False)
            self.runner.start()
            self.runner.abort(quiet=True)
            self.app.daily_qso_var.set(True)
            self.runner.start()
            self.runner.abort(quiet=True)
        self.assertEqual(seen, [set(), {daily.QSO_LOG}])

    def _band_outro(self, gain, cw_filter=500):
        """Tagesübung nur mit dem Band-Ausklang starten, ohne den Block laufen zu lassen."""
        settings = self.app.band_settings
        spec = {"levels": {"noise": 0.1, "smps": 0.5, "strength": 0.5}, "gain": gain}
        settings.set_spec(spec | ({"filter": cw_filter} if cw_filter else {}))
        own = settings.spec()
        with mock.patch.object(daily, "plan", lambda *args, **kwargs: [daily.band_outro("medium")]), \
                mock.patch.object(daily_runner.announcer, "say") as say:
            self.runner.start()
        return own, say.call_args[0][0]

    def test_band_outro_sets_the_stage_and_restores_own_settings(self):
        own, text = self._band_outro(1.3)
        settings = self.app.band_settings
        spec = settings.spec()
        self.assertEqual(band.preset_rank(spec, self.app.freq_var.get()), "medium")
        self.assertNotIn("smps", spec["levels"])
        self.assertEqual(spec["gain"], 1.0)  # lauter als 100 % nicht
        self.assertNotIn("filter", spec)  # die Stufen gelten ohne schmales Filter
        self.assertNotIn("strength", spec["levels"])  # eine Station: keine Stärkeunterschiede
        self.assertTrue(self.mode("Kontinuierlich").band_var.get())
        self.assertIn("Am Stück mit Band mittel, 4 Minuten.", text)
        self.assertNotIn("QRN-fest", text)
        self.assertIn("CW-Filter für den Ausklang in der Grundeinstellung, danach wieder deins.", text)
        # Das Bandfenster sagt, wer die Einstellung gesetzt hat.
        from morsetrainer.widgets import band_settings
        with mock.patch.object(band_settings.announcer, "say") as say:
            settings.open_window()
        self.root.update()
        self.assertTrue(settings.note_label.winfo_ismapped())
        self.assertTrue(say.call_args[0][0].startswith("Gesetzt von der Tagesübung: Stufe mittel"))
        self.runner.abort()
        self.assertEqual(settings.spec(), own)
        self.assertFalse(self.mode("Kontinuierlich").band_var.get())
        self.root.update()
        self.assertFalse(settings.note_label.winfo_ismapped())  # auch im offenen Fenster wieder weg
        settings.close_window()

    def test_band_outro_stopped_early_is_marked(self):
        self._band_outro(1.0)
        mode = self.runner.mode
        with mock.patch.object(mode, "daily_result", return_value={"correct": 190, "total": 200, "minutes": 1.0}):
            self.runner.on_block_end(mode)
        block = self.runner.state["days"][self.runner.today.isoformat()]["blocks"][-1]
        self.assertEqual((block["band"], block.get("stopped")), ("medium", True))  # zählt nicht für die Stufe
        self.assertFalse(self.runner.active)

    def test_band_outro_without_own_filter_says_nothing_about_it(self):
        _, text = self._band_outro(1.0, cw_filter=None)
        self.assertNotIn("CW-Filter", text)
        self.runner.abort()

    def test_band_outro_keeps_a_lower_noise_volume_and_says_so(self):
        own, text = self._band_outro(0.6)
        self.assertEqual(self.app.band_settings.spec()["gain"], 0.6)
        self.assertIn("Störlautstärke 60 %, zählt nicht für das Diplom QRN-fest.", text)
        self.runner.abort()
        self.assertEqual(self.app.band_settings.spec(), own)

    def test_summary_tells_the_next_band_stage(self):
        from morsetrainer.widgets import daily_panel
        self.runner.state, self.runner.today = daily.load(), date.today()
        with mock.patch.object(daily, "band_change", return_value=("light", "medium")):
            self.runner._show_summary(set(), True)
        self.assertIn("Zweimal 90 % geschafft – nächster Band-Ausklang: mittel", self.runner.summary.spoken)
        self.runner.summary.close()
        self.assertIn("wieder leicht", daily_panel.band_change_line(("medium", "light")))
        self.assertEqual(daily_panel.band_change_line(None), "")

    def test_band_outro_records_the_weakest_stage(self):
        with mock.patch.object(daily, "plan", lambda *args, **kwargs: [daily.band_outro("light")] * 2), \
                mock.patch.object(daily_runner.announcer, "say"):
            self.runner.start()
        mode = self.runner.mode
        mode.band_rank_min = None  # zwischendurch ausgeschaltet
        with mock.patch.object(mode, "daily_result", return_value={"correct": 5, "total": 5, "minutes": 4.0}):
            self.runner.on_block_end(mode)
        block = daily.load()["days"][date.today().isoformat()]["blocks"][-1]
        self.assertEqual((block["band"], block["band_min"]), ("light", None))
        self.runner.abort(quiet=True)

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
        self.runner.card_shown -= daily_runner.ENTER_GRACE_S
        self.runner.continue_now()
        self.assertIs(self.runner.mode, self.mode("Einzelzeichen"))
        self.runner.abort(quiet=True)

    def test_first_day_in_lesson_1_plays_k_and_m_first(self):
        daily.save({"days": {}})
        self.app.lesson_var.set(1)
        self.app.charset_var.set(koch.lesson_charset(1))
        with mock.patch.object(self.app, "_play_new_char") as play:
            self.runner.start()
        self.assertTrue(self.runner.card_open)
        play.assert_called_once_with("KM")
        self.assertIn("Neue Zeichen: K und M", str(self.app.daily_bar.card.cget("text")))
        self.runner.abort(quiet=True)

    def test_later_days_in_lesson_1_start_directly(self):
        daily.save({"lesson": 1, "days": {"2020-01-01": {"stars": [], "minutes": 5.0, "blocks": [{"kind": "main"}]}}})
        self.app.lesson_var.set(1)
        self.app.charset_var.set(koch.lesson_charset(1))
        self.runner.start()
        self.assertFalse(self.runner.card_open)
        self.runner.abort(quiet=True)

    def test_idle_bar_points_new_users_to_daily_practice_and_refresher(self):
        daily.save({"days": {}})
        self.runner.refresh_idle()
        self.assertIn("Wiedereinsteiger", self.app.daily_bar.note_var.get())
        daily.save({"days": {"2020-01-01": {"stars": [], "minutes": 5.0}}})
        self.runner.refresh_idle()
        self.assertNotIn("Neu hier", self.app.daily_bar.note_var.get())

    def test_card_points_to_relaxed_practice_when_limit_was_too_tight(self):
        self.runner.start()
        self.runner.card_open = False
        block = self.runner.blocks[0]
        result = {"correct": 10, "total": 24, "timeouts": 12, "minutes": block.minutes}
        with mock.patch.object(self.runner, "_show_card") as card:
            self.runner._show_block_card(block, result, [])
        self.assertTrue(any("Entspannte Tagesübung" in line for line in card.call_args[0][1]))
        self.app.daily_relaxed_var.set(True)
        with mock.patch.object(self.runner, "_show_card") as card:
            self.runner._show_block_card(block, result, [])
        self.assertFalse(any("Entspannte Tagesübung" in line for line in card.call_args[0][1]))
        self.runner.abort(quiet=True)

    def _card_lines(self, block, result, state=None):
        if state is not None:
            self.runner.state = state
        with mock.patch.object(self.runner, "_show_card") as card:
            self.runner._show_block_card(block, result, [])
        return card.call_args[0][1]

    def test_card_gives_the_error_review_with_one_tip(self):
        self.runner.start()
        block = self.runner.blocks[1]
        errors = {"total": 9, "answers": 100, "causes": {"heard": 6, "late": 3}, "pair": ("B", "6", 3)}
        lines = self._card_lines(block, {"correct": 80, "total": 100, "minutes": block.minutes, "errors": errors})
        self.assertIn("Woran es lag: Von 9 Fehlern waren 6 Verwechslungen (B für 6 dreimal), 3 zu langsam.", lines)
        self.assertEqual(sum(line.startswith("Tipp:") for line in lines), 1)
        few = dict(errors, total=2, causes={"heard": 2})
        lines = self._card_lines(block, {"correct": 98, "total": 100, "minutes": block.minutes, "errors": few})
        self.assertFalse([line for line in lines if line.startswith(("Woran", "Tipp"))])
        self.runner.abort(quiet=True)

    def test_relaxed_tip_only_in_the_warmup_and_not_twice(self):
        self.runner.start()
        warmup, main = self.runner.blocks[0], self.runner.blocks[1]
        errors = {"total": 12, "answers": 24, "causes": {"late": 12}, "pair": None}
        result = {"correct": 12, "total": 24, "timeouts": 12, "minutes": warmup.minutes, "errors": errors}
        lines = self._card_lines(warmup, result)
        self.assertEqual(sum("Entspannte Tagesübung" in line for line in lines), 1)  # nur der Hinweis „Zu knapp?“
        lines = self._card_lines(main, dict(result, minutes=main.minutes))
        self.assertFalse([line for line in lines if "Entspannte Tagesübung" in line])
        self.runner.abort(quiet=True)

    def test_warmup_card_counts_the_solid_characters_after_a_break(self):
        self.runner.start()
        warmup = self.runner.blocks[0]
        result = {"correct": 20, "total": 24, "minutes": warmup.minutes,
                  "chars": {"K": (8, 8), "M": (8, 4), "R": (1, 1)}}
        self.runner.pause_sure = "KMR"
        text = "Nach der Pause: von 2 früher sicheren Zeichen saßen 1 gleich wieder. Der Rest kommt in den nächsten Tagen zurück."
        self.assertIn(text, self._card_lines(warmup, result))
        all_back = dict(result, chars={"K": (8, 8), "M": (8, 8)})
        self.assertIn("Nach der Pause: alle 2 früher sicheren Zeichen saßen gleich wieder.", self._card_lines(warmup, all_back))
        self.runner.pause_sure = ""
        self.assertNotIn(text, self._card_lines(warmup, result))
        self.runner.pause_sure = "KMR"
        self.assertFalse([line for line in self._card_lines(self.runner.blocks[1], result) if line.startswith("Nach der Pause")])
        self.runner.abort(quiet=True)

    def test_card_after_a_weak_main_part_says_it_happens(self):
        self.runner.start()
        main = self.runner.blocks[1]
        state = daily.load()
        state["tempo"] = {"wpm": 20, "effective": 12}
        state.update(pending_tempo={"wpm": 20, "effective": 11}, pending_tempo_since=date.today().isoformat())
        self.runner.today = date.today()
        lines = self._card_lines(main, {"correct": 50, "total": 100, "minutes": main.minutes}, state)
        self.assertIn("Das kommt vor – morgen läuft es etwas langsamer, bis es wieder sitzt.", lines)
        state["pending_tempo_since"] = "2000-01-01"
        lines = self._card_lines(main, {"correct": 90, "total": 100, "minutes": main.minutes}, state)
        self.assertNotIn("Das kommt vor – morgen läuft es etwas langsamer, bis es wieder sitzt.", lines)
        self.runner.abort(quiet=True)

    def test_welcome_back_after_a_long_break(self):
        from datetime import timedelta
        long_ago = (date.today() - timedelta(days=30)).isoformat()
        daily.save({"lesson": 12, "days": {long_ago: {"stars": [], "blocks": [{"kind": daily.MAIN}],
                                                          "progress": [], "minutes": 10.0, "lesson": 12}}})
        self.runner.refresh_idle()
        self.assertIn("Schön, dass du wieder da bist", self.app.daily_bar.note_var.get())
        recent = (date.today() - timedelta(days=5)).isoformat()
        daily.save({"lesson": 12, "days": {recent: {"stars": [], "blocks": [{"kind": daily.MAIN}],
                                                       "progress": [], "minutes": 10.0, "lesson": 12}}})
        self.runner.refresh_idle()
        self.assertNotIn("wieder da bist", self.app.daily_bar.note_var.get())

    def test_pause_note_starts_at_fourteen_days(self):
        from datetime import timedelta
        from morsetrainer.core import db, review
        db.save_state(review.STATE_KEY, {"K": {"box": 4, "due": "2000-01-01"}, "M": {"box": 3, "due": "2000-01-01"}})
        for gap, expected in ((13, ""), (14, "KM"), (15, "KM")):
            day = (date.today() - timedelta(days=gap)).isoformat()
            daily.save({"lesson": 12, "days": {day: {"stars": [], "blocks": [{"kind": daily.MAIN}],
                                                      "progress": [], "minutes": 10.0, "lesson": 12}}})
            self.runner.start()
            self.assertEqual(self.runner.pause_sure, expected, gap)
            self.runner.abort(quiet=True)
        daily.save({"lesson": 12, "days": {}})  # noch nie geübt: kein Hinweis
        self.runner.start()
        self.assertEqual(self.runner.pause_sure, "")
        self.runner.abort(quiet=True)

    def test_evening_summary_fills_the_gap_with_todays_numbers(self):
        from morsetrainer.widgets.daily_panel import EveningSummary
        text = "Heute: 190 Zeichen gehört."
        few = EveningSummary(self.app.root, [daily.DABEI], {"status": daily.FEW, "better": []}, today=text)
        self.assertIn(text, few.spoken)
        few.close(follow=False)
        held = EveningSummary(self.app.root, [daily.DABEI], {"status": daily.HELD, "better": []}, today=text)
        self.assertNotIn(text, held.spoken)
        held.close(follow=False)

    def test_quit_asks_twice_during_daily_practice(self):
        self.runner.start()
        with mock.patch.object(self.app, "on_close") as close:
            self.app._request_close("Strg+Q")
            close.assert_not_called()
            self.assertIn("das Programm", self.app.daily_bar.notice_var.get())
            self.app._request_close("Strg+Q")
            close.assert_called_once()
        self.runner.abort(quiet=True)

    def test_quit_is_immediate_without_daily_practice(self):
        with mock.patch.object(self.app, "on_close") as close:
            self.app._request_close("Strg+Q")
        close.assert_called_once()

    def test_warmup_limit_follows_the_tempo(self):
        from morsetrainer.core import tempo
        daily.save({"lesson": 12, "days": {}, "icr_limit": 0.8, "tempo": {"wpm": 20, "effective": 10}})
        self.runner.start()
        single = self.mode("Einzelzeichen")
        single.next_char()
        # Ein alter gespeicherter Wert (icr_limit 0,8) wirkt nicht mehr.
        self.assertEqual(single.limit, tempo.char_limit(20, 10, len(set(single.charset))))
        self.runner.abort(quiet=True)

    def test_tempo_from_yesterday_applies_at_start(self):
        daily.save({"lesson": 12, "days": {}, "tempo": {"wpm": 20, "effective": 12},
                    "pending_tempo": {"wpm": 20, "effective": 11}, "pending_tempo_since": "2000-01-01"})
        self.runner.start()
        self.assertEqual(self.app.farnsworth_wpm_var.get(), 11)
        self.runner.abort(quiet=True)
        self.assertEqual(daily.load()["tempo"], {"wpm": 20, "effective": 11})
        self.assertEqual(self.app.farnsworth_wpm_var.get(), 12)  # zurückgestellt

    def test_idle_bar_shows_week_and_review(self):
        from datetime import timedelta
        today = date.today()
        last_week = today - timedelta(days=today.weekday() + 3)
        daily.save({"lesson": 12, "days": {last_week.isoformat(): {
            "stars": [daily.DABEI], "blocks": [{"kind": daily.MAIN}], "progress": [], "minutes": 10.0,
            "lesson": 12}}})
        with mock.patch.object(daily, "plan", short_plan):
            self.runner.refresh_idle()
            self.assertIn("Letzte Woche: 1 Tag, 1 ★", self.app.daily_bar.note_var.get())
            self.assertIn("0 ★ diese Woche, Ziel 8", self.app.daily_bar.goal_var.get())
            self.runner.start()
            self.runner.abort(quiet=True)
        self.assertIn("Tagesübung beendet", self.app.daily_bar.note_var.get())  # ohne Stern
