"""Ablauf der Tagesübung: schaltet nacheinander die vorhandenen Reiter mit
festen Einstellungen ein (Regeln in core/daily.py, Schnittstelle der
Reiter in modes/daily_support.py).

Vorher werden die gemeinsamen Einstellungen (Zeichensatz, Tempo,
Gewichtung) gemerkt und danach zurückgestellt; die Tagesübung arbeitet mit
ihrer eigenen Lektion und ihrem Tagestempo. Ein Block, der von Hand
gestoppt wird (Knopf im Reiter oder in der Leiste, zweimal Esc oder F5),
beendet die ganze Tagesübung; bereits verdiente Sterne bleiben.

Zwischen den Blöcken steht die Zwischenkarte, bis man mit Enter (oder dem
Knopf) weitergeht; am Ende die Abendbilanz. Aus ihr startet „Noch 5 Min“ eine Zugabe:
ein einzelner Block mit demselben Ablauf, danach ohne neue Bilanz."""
import time
import tkinter as tk
from datetime import date

from morsetrainer.core import awards, daily, koch, practice, qso_text, review, stats, week
from morsetrainer.i18n import N_, ctrl_key, short_number, skip_key, tr
from morsetrainer.widgets import announcer, band_settings
from morsetrainer.widgets.daily_panel import (
    BLOCK_LABELS, ENTER_GRACE_S, EveningSummary, block_lines, end_note, minutes_text, mode_name, moment_line,
    preview_line, review_line, stars_named, today_line)
from morsetrainer.modes.qso_mode import EVAL_HEAD, EVAL_QUIZ, estimate_minutes
from morsetrainer.modes.sequence_mode import COPY, MEMORIZE
from morsetrainer.widgets.awards_panel import seal_name

# Reiter je Modus der Blöcke (deutsche Titel = Schlüssel, siehe app.py).
MODE_TITLES = {"single": "Einzelzeichen", "group": "Gruppen", "word": "Wörter", "callsign": "Rufzeichen",
               "continuous": "Kontinuierlich", daily.QSO_HEAD: "QSO", daily.QSO_LOG: "QSO"}
# Contest-Arten für den Ausklang mit Log, im Wechsel über die Zyklen.
CONTEST_KINDS = tuple(kind for kind in qso_text.QSO_TYPES if kind != qso_text.RAGCHEW)


# Nach langer Pause, solange noch keine Tagesübung wieder lief.
WELCOME_BACK_NOTE = N_("Schön, dass du wieder da bist. Nach einer Pause sind die ersten Tage schwerer – "
                       "das Tempo gleicht sich an.")
# Solange noch keine Tagesübung lief, steht das in der Leiste.
FIRST_START_NOTE = N_("Neu hier? Los geht es mit ▶ Tagesübung. CW früher gekonnt? Unter „▸ Weitere Optionen“ "
                      "den Haken „Wiedereinsteiger“ setzen.")


def block_text(block) -> str:
    """Ansage vor einem Block, z. B. „Tagesübung, Aufwärmen: Zeichen,
    3 Minuten.“"""
    return tr("Tagesübung, {block}: {mode}, {minutes} Minuten.").format(
        block=tr(BLOCK_LABELS[block.kind]), mode=mode_name(block), minutes=short_number(block.minutes))


# Feste Einstellungen je Modus (Schlüssel wie settings() des Reiters).
_SEQUENCE = {"adaptive_tempo": False, "band": False, "give_up": 1}
MODE_SETTINGS = {
    # Das Zeitlimit kommt aus daily.warmup_limit(): ein Limit aus dem Reiter
    # soll nicht ins Aufwärmen nachwirken.
    "single": {"icr": True},
    "group": {**_SEQUENCE, "input_style": COPY, "adaptive": True, "min_len": 2, "max_len": 6},
    "word": {**_SEQUENCE, "input_style": MEMORIZE, "content": "words"},
    "callsign": {**_SEQUENCE, "input_style": COPY, "prefixes": "", "learned_only": True, "rufz": False},
    "continuous": {"band": False},
    # Kurz, ohne Pile-up, ohne Tempo-Automatik; „Nochmal“ sperrt der Reiter selbst.
    daily.QSO_HEAD: {"kind": qso_text.RAGCHEW, "eval": EVAL_HEAD, "length": qso_text.LENGTH_SHORT,
                     "adaptive": False, "pileups": "aus", "band": False},
    daily.QSO_LOG: {"eval": EVAL_QUIZ, "length": qso_text.LENGTH_SHORT, "adaptive": False, "pileups": "aus",
                    "band": False},
}
# Ein Block, der kürzer lief, wurde von Hand gestoppt (die Reiter enden
# sonst erst nach Ablauf der Zeit und der letzten Eingabe).
STOPPED_EARLY_MIN = 0.1
TICK_MS = 1000
QSO_MODES = (daily.QSO_HEAD, daily.QSO_LOG)


class DailyRunner:
    """Führt die Tagesübung durch: stellt die Blöcke zusammen (core/daily.py),
    schaltet nacheinander die passenden Reiter mit festen Einstellungen ein,
    zeigt dazwischen die Zwischenkarte und am Ende die Abendbilanz."""
    def __init__(self, app, bar):
        self.app = app
        self.bar = bar
        self.active = False
        self.aborting = False
        self.skipping = False  # QSO-Block wird gerade zum Überspringen gestoppt
        self.skip_note = ""    # Ansage vor dem Ersatzblock
        self.last_note = ""    # skip_note der letzten Blockansage
        self.quiet = False
        self.state = {}
        self.blocks = []
        self.index = -1
        self.mode = None
        self.block_started = None
        self.done_minutes = 0.0
        self.saved_shared = None
        self.saved_content = None  # Inhalt im Reiter „Einzeln“ vor der Tagesübung
        self.saved_band = None  # Bandeinstellung vor dem Band-Ausklang
        self.tick_id = None
        self.card_open = False
        self.card_shown = 0.0
        self.card_text = ""  # zuletzt gezeigte Karte als Ansage
        self.extra = False
        self.pause_sure = ""
        self.summary = None
        self.refresh_idle()

    # --- Anzeige ---------------------------------------------------------------
    def refresh_idle(self, note: str = "") -> None:
        """Leiste ohne Tagesübung; ohne `note` steht dort der Wochenrückblick,
        solange diese Woche noch keine Tagesübung lief."""
        state = daily.load()
        practice_data = practice.load()
        if not note:
            review_data = week.last_week_review(state, practice_data, self.app.daily_goal_minutes() * 60, date.today())
            note = review_line(review_data) if review_data else ""
        if not note and not state.get("days"):
            note = tr(FIRST_START_NOTE)
        elif not note:
            gap = daily.days_since_practice(state, date.today())
            if gap is not None and gap >= daily.WELCOME_BACK_DAYS:
                note = tr(WELCOME_BACK_NOTE)
        self.bar.show_idle(note)
        self.refresh_week(practice_data, state)

    def refresh_week(self, practice_data=None, state=None) -> None:
        """Wochenstreifen und Stand zum Wochenziel."""
        if self.active:
            return  # die Leiste zeigt gerade den Ablauf
        state = daily.load() if state is None else state
        practice_data = practice.load() if practice_data is None else practice_data
        today = date.today()
        self.bar.show_week(week.strip(state, practice_data, self.app.daily_goal_minutes() * 60, today),
                           week.stars_in_week(state, today))

    def _tick(self) -> None:
        elapsed = self.done_minutes
        if self.block_started is not None:
            elapsed += (time.time() - self.block_started) / 60
        self.bar.update(self.blocks, self.index, elapsed, daily.stars_on(self.state, self.today))
        self.bar.set_skippable(self._skippable())
        self.tick_id = self.app.root.after(TICK_MS, self._tick)

    def spoken_status(self) -> str:
        """Für F11 während eines Blocks: welcher Block, wie weit die Übung ist
        und welche Sterne heute schon da sind (Zeiten als „M:SS“)."""
        elapsed = self.done_minutes
        if self.block_started is not None:
            elapsed += (time.time() - self.block_started) / 60
        stars = daily.stars_on(self.state, self.today)
        block = self.blocks[self.index]
        text = tr("Tagesübung, {block}: {mode}, Block {n} von {total}, {elapsed} von {minutes} Minuten, {stars}.").format(
            block=tr(BLOCK_LABELS[block.kind]), mode=mode_name(block), n=self.index + 1, total=len(self.blocks),
            elapsed=minutes_text(min(elapsed, daily.TOTAL_MINUTES)), minutes=daily.TOTAL_MINUTES,
            stars=stars_named(stars) if stars else tr("noch kein Stern"))
        if self._skippable():
            text += " " + tr("Überspringen mit {key}.").format(key=skip_key())
        return text

    def _refresh(self) -> bool:
        """Ist „Wiedereinsteiger“ in den weiteren Optionen angehakt?"""
        return bool(self.app.refresh_var.get())

    # --- Start ---------------------------------------------------------------------
    def start(self) -> None:
        """Beginnt die Tagesübung (nicht während eines Durchgangs): Lektion und
        Tempo für heute bestimmen, Blöcke planen, ersten Block starten."""
        if self.active or self.app.running_mode:
            return
        app = self.app
        self.extra = False
        self.today = date.today()
        self.state = daily.load()
        fallback = koch.lesson_of(app.charset_var.get().strip().upper()) or self._lesson_field()
        lesson = daily.current_lesson(self.state, fallback)
        self.state["lesson"] = lesson
        daily.apply_pending_lesson(self.state, self.today)
        daily.apply_pending_tempo(self.state, self.today)
        lesson = self.state["lesson"]
        try:
            wpm = app.wpm_var.get()
        except Exception:
            wpm = koch.RECOMMENDED_WPM
        self.state["tempo"] = daily.current_tempo(self.state, wpm, app.farnsworth_wpm(), self._refresh())
        daily.save(self.state)

        charset = daily.lesson_charset(lesson, review.boxed_chars())
        self.due = review.due_chars(known=charset)
        gap = daily.days_since_practice(self.state, self.today)
        self.pause_sure = (daily.sure_before_pause(review.load(), charset)
                           if gap is not None and gap >= daily.WELCOME_BACK_DAYS else "")
        turn = daily.practice_days(self.state, self.today)
        # Jeder zweite Zyklus hat statt des Contest-Runs Bandbedingungen.
        contest = CONTEST_KINDS[turn // (2 * len(daily.POST_CYCLE)) % len(CONTEST_KINDS)]
        qso, band = set(), None
        if daily.stage(lesson) == daily.POST:
            effective = self.state["tempo"]["effective"]
            if self.app.daily_qso_var.get():
                qso = daily.qso_outros(effective, review.boxed_chars(), lambda mode: self._qso_fits(mode, contest))
            if effective >= daily.BAND_MIN_EFFECTIVE:
                band = daily.band_level(self.state, self.today)
        self._begin(charset, daily.plan(lesson, len(self.due), turn, qso, contest, band))
        # Neue Lektion oder allererster Tag in Lektion 1: die neuen Zeichen erst einmal
        # anhören (Lektion 41 bringt keins).
        if lesson == 1 and turn == 0 and not self.state.get("days", {}).get(self.today.isoformat(), {}).get("blocks"):
            chars = koch.lesson_charset(1)
        elif daily.is_new_lesson(self.state, self.today) and 1 < lesson < daily.POST_KOCH:
            chars = koch.newest_char(lesson)
        else:
            chars = ""
        if chars:
            # Vorspielen erst nach der Ansage, sie schnitte sonst das Zeichen ab;
            # ist die Karte bis dahin schon weitergeschaltet, nicht mehr (der
            # Block liefe sonst gleichzeitig an).
            title = (tr("Neue Zeichen: {char}") if len(chars) > 1 else tr("Neues Zeichen: {char}"))
            shown = tr(" und ").join(chars)
            self._show_card(title.format(char=shown),
                            [preview_line(self.blocks[0], lesson, self.state["tempo"])],
                            then=lambda: self.card_open and self.active and app._play_new_char(chars),
                            spoken_title=title.format(char=tr(" und ").join(announcer.spell(ch) for ch in chars)))
        else:
            self._next_block()

    def start_extra(self, offer) -> None:
        """„Noch 5 Min“ aus der Abendbilanz: ein Block, einmal am Tag."""
        if self.active or self.app.running_mode:
            return
        kind, chars = offer
        self.extra = True
        self.today = date.today()
        self.state = daily.load()
        daily.day_entry(self.state, self.today)[daily.EXTRA] = True
        daily.save(self.state)
        lesson = daily.current_lesson(self.state, self._lesson_field())
        tempo = daily.current_tempo(self.state, self.app.wpm_var.get(), self.app.farnsworth_wpm())
        self.state["tempo"] = tempo
        self.due = ""
        self.pause_sure = ""
        if kind == daily.CONFUSIONS:
            block = daily.Block(daily.EXTRA, "single", daily.EXTRA_MINUTES)
            charset = chars
        elif kind == daily.RUFZ:
            block = daily.Block(daily.EXTRA, "callsign", daily.EXTRA_MINUTES, {"rufz": True})
            charset = daily.lesson_charset(lesson, review.boxed_chars())
        else:
            block = daily.Block(daily.EXTRA, "word", daily.EXTRA_MINUTES)
            charset = daily.lesson_charset(lesson, review.boxed_chars())
        self._begin(charset, [block])
        self._next_block()

    def _begin(self, charset: str, blocks: list) -> None:
        """Gemeinsame Einstellungen sichern und für die Tagesübung setzen."""
        app = self.app
        self.saved_shared = {key: var.get() for key, var in self._shared().items()}
        self.saved_content = app.one_by_one_var.get()
        app.charset_var.set(charset)
        self._apply_tempo(self.state["tempo"])
        app.weighted_var.set(True)
        self.blocks = blocks
        self.index = -1
        self.done_minutes = 0.0
        self.active, self.aborting = True, False
        self.skipping, self.skip_note = False, ""
        self.bar.set_enabled(False)
        self.bar.show_active()
        self._tick()

    def _qso_fits(self, mode: str, contest: str) -> bool:
        """Passt ein kurzes QSO (bzw. ein kurzer Contest-Run) im Tagestempo mit
        den Fragen in den Ausklang?"""
        tempo = self.state["tempo"]
        fw = tempo["effective"] if tempo["effective"] < tempo["wpm"] else None
        kind = qso_text.RAGCHEW if mode == daily.QSO_HEAD else contest
        return estimate_minutes(kind, qso_text.LENGTH_SHORT, tempo["wpm"], fw, samples=5) <= daily.QSO_MAX_MINUTES

    def _lesson_field(self) -> int:
        try:
            return self.app.lesson_var.get()
        except Exception:
            return 1

    def _shared(self) -> dict:
        app = self.app
        return {"charset": app.charset_var, "wpm": app.wpm_var, "farnsworth_enabled": app.farnsworth_enabled_var,
                "farnsworth_wpm": app.farnsworth_wpm_var, "weighted": app.weighted_var}

    def _apply_tempo(self, tempo: dict) -> None:
        app = self.app
        app.wpm_var.set(tempo["wpm"])
        if tempo["effective"] < tempo["wpm"]:
            app.farnsworth_wpm_var.set(tempo["effective"])
            app.farnsworth_enabled_var.set(True)
        else:
            app.farnsworth_enabled_var.set(False)

    # --- Blöcke --------------------------------------------------------------------
    def _next_block(self) -> None:
        """Startet den nächsten Block oder beendet die Übung nach dem letzten;
        reicht der Zeichensatz für Wörter oder Rufzeichen nicht, wird es ein
        Gruppen-Block."""
        self.card_open = False
        self.bar.hide_card()
        if not self.active:
            return
        self.index += 1
        if self.index >= len(self.blocks):
            self._finish(completed=True)
            return
        self._start_block(self.blocks[self.index])

    def _start_block(self, block) -> None:
        """Wechselt still zum Reiter des Blocks, setzt seine festen
        Einstellungen, sagt den Block an und startet ihn erst danach (sonst
        liefe die Ansage über dem ersten Zeichen, und es zählte als zu
        langsam)."""
        app = self.app
        title = MODE_TITLES[block.mode]
        mode = app.modes[app.mode_titles.index(title)]
        # Zwischen den Blöcken bleiben die anderen Reiter gesperrt, auch
        # während der Ansage; der neue Reiter sperrt sie beim Start selbst.
        tab_id = app.tab_ids[app.mode_titles.index(title)]
        app.notebook.tab(tab_id, state="normal")
        app.show_mode(title, announce=False)
        for other in app.notebook.tabs():
            if other != tab_id:
                app.notebook.tab(other, state="disabled")
        review.focus = self._focus(block) if block.kind == daily.WARMUP else set()
        settings = {**MODE_SETTINGS[block.mode], **block.params}
        preset = settings.pop(daily.BAND_PRESET, None)
        text = self.skip_note + block_text(block)
        self.last_note, self.skip_note = self.skip_note, ""
        if block.mode in QSO_MODES:
            text += " " + tr("Überspringen mit {key}.").format(key=skip_key())
        self.bar.set_skippable(block.mode in QSO_MODES)
        if preset:
            gain, own_filter = self._set_band(preset)
            if own_filter:
                text += " " + tr("CW-Filter für den Ausklang in der Grundeinstellung, danach wieder deins.")
            if gain < 100:
                text += " " + tr("Störlautstärke {gain} %, zählt nicht für das Diplom QRN-fest.").format(gain=gain)
        relaxed = block.mode == "single" and bool(self.app.daily_relaxed_var.get())
        if block.mode == "single":
            if relaxed:
                settings["icr"] = False  # ohne Zeitlimit; der Block zählt nicht für die Lernkartei
            else:
                settings["icr_limit"] = daily.warmup_limit(self.state)
        mode.daily_relaxed = relaxed
        mode.daily_configure(block.minutes, **settings)
        self.mode = mode
        announcer.say(text, then=lambda: self._run_block(block, mode))

    def _set_band(self, preset: str) -> tuple:
        """Stellt die Bandbedingungen für den Ausklang auf die Stufe `preset`
        (die eigene Einstellung wird gemerkt, _release_band). Das Filter steht
        auf der Grundeinstellung, für die die Stufen gelten (ein schmales
        machte aus „mittel“ „leicht“), die Stärkeunterschiede sind aus (bei
        einer Station nur ein zufälliger Abzug, den die Stufe nicht kennt).
        Die Störlautstärke steht auf 100 %; wer
        sie leiser gestellt hat (etwa wegen eines Hörproblems), behält das.
        Gibt (Störlautstärke in Prozent, ob ein eigenes Filter zurückgestellt
        wurde) zurück."""
        settings = self.app.band_settings
        if self.saved_band is None:
            self.saved_band = settings.spec()
        spec = settings.spec()
        own_filter = spec.pop("filter", None) is not None
        spec["levels"].pop("strength", None)
        spec["gain"] = min(spec["gain"], 1.0)
        settings.set_spec(spec, notify=False)
        settings.set_preset(preset)
        settings.note_var.set(tr("Gesetzt von der Tagesübung: Stufe {name} für den Band-Ausklang, Filter in der "
                                 "Grundeinstellung. Danach gilt wieder deine eigene Einstellung.").format(
            name=tr(band_settings.PRESET_NAMES[preset])))
        return round(settings.spec()["gain"] * 100), own_filter

    def _release_band(self) -> None:
        """Eigene Bandeinstellung nach dem Band-Ausklang zurück."""
        if self.saved_band is not None:
            self.app.band_settings.note_var.set("")
            self.app.band_settings.set_spec(self.saved_band)
            self.saved_band = None

    def _run_block(self, block, mode) -> None:
        """Nach der Blockansage: Reiter starten. Reichen Wörter oder
        Rufzeichen für den Zeichensatz nicht, wird es ein Gruppen-Block."""
        if not self.active or self.mode is not mode:
            return  # während der Ansage abgebrochen
        self.block_started = time.time()
        if not mode.running:  # sonst schon mit dem Start-Knopf während der Ansage gestartet
            mode.start()
        if not mode.running:
            mode.daily_release()
            self.mode = None
            self.block_started = None
            review.focus = set()
            if block.mode != "group":
                self.blocks[self.index] = block = daily.Block(block.kind, "group", block.minutes, {})
                self.skip_note = self.last_note  # „QSO übersprungen“ soll nicht verloren gehen
                self._start_block(block)
            else:
                self._finish(completed=False)
            return
        # Stop beendet hier nicht nur den Block, sondern die ganze Übung.
        mode.daily_end_button()

    def _focus(self, block) -> set:
        charset = self.app.charset_var.get().upper()
        if block.params.get("focus") == "due":
            return set(self.due)
        chars = self.app._confusion_charset(stats.recent_char_data(), stats.load_all_time())
        return {ch for ch in chars if ch in charset}  # leer: nur die Gewichtung schwacher Zeichen

    def on_block_end(self, mode) -> None:
        """Vom Hauptfenster, wenn der Reiter gestoppt hat (on_stop)."""
        if mode is not self.mode:
            return
        block = self.blocks[self.index]
        result = mode.daily_result() or {}
        if block.params.get(daily.BAND_PRESET):
            # Schwächste Stufe im Lauf: wer leichter stellt, steigt damit nicht auf.
            result = {**result, "band_min": getattr(mode, "band_rank_min", None)}
            self._release_band()
        if block.mode == "single":
            self.state["icr_limit"] = mode.limit  # vor daily_release(): das ist das Limit des Reiters
        mode.daily_release()
        for attr in ("koch_result", "groups_result"):  # keine Ja/Nein-Fragen danach
            if hasattr(mode, attr):
                setattr(mode, attr, None)
        review.focus = set()
        self.mode = None
        self.block_started = None
        if self.skipping and not self.aborting:
            self.skipping = False
            self._swap_for_callsigns(block)
            return
        minutes = result.get("minutes", 0.0)
        self.done_minutes += minutes
        # Ein Rufz-Durchgang endet nach seinen Rufzeichen, ein QSO mit dem
        # Prüfen der Abfrage, nicht nach der Zeit.
        if block.mode in QSO_MODES:
            stopped_early = not result.get("checked")
            if not stopped_early:
                # Ein geprüftes QSO ist der ganze Ausklang, auch wenn der Run
                # kürzer war; sonst kostete es den Stern Dabei.
                result = {**result, "minutes": max(minutes, block.minutes)}
                self.done_minutes += result["minutes"] - minutes
        else:
            stopped_early = minutes < block.minutes - STOPPED_EARLY_MIN and not block.params.get("rufz")
        if self.aborting or stopped_early:
            result = {**result, "stopped": True}  # zählt nicht für die Bandstufe
        new_stars = daily.finish_block(self.state, self.today, block, result, self._refresh())
        daily.save(self.state)
        if self.aborting or stopped_early:
            self._finish(completed=False)
        elif self.index + 1 >= len(self.blocks):
            self._next_block()  # letzter Block: gleich zur Abendbilanz
        else:
            self._show_block_card(block, result, new_stars)

    def skip_qso(self) -> None:
        """„QSO überspringen“ (Knopf oder Tastenkürzel): Der QSO-Block wird durch
        Rufzeichen derselben Dauer ersetzt, so bleibt ★ Dabei erreichbar. Ein
        angefangenes QSO zählt nicht für den Block, seine Antworten stehen
        in der Statistik."""
        if not self._skippable():
            return
        block = self.blocks[self.index]
        if not self._skippable():
            return
        if self.mode.running:
            self.skipping = self.mode.daily_skipping = True
            self.mode.stop()  # führt über on_block_end zu _swap_for_callsigns
        else:  # noch in der Blockansage
            self.mode.daily_release()
            self.mode = None
            self._swap_for_callsigns(block)

    def _skippable(self) -> bool:
        """Läuft ein QSO-Block, der Ton spielt oder noch angesagt wird? Danach, bei
        der Abfrage, würde Überspringen die Antworten verwerfen."""
        if not self.active or self.card_open or self.mode is None or self.skipping:
            return False
        block = self.blocks[self.index]
        return block.mode in QSO_MODES and (self.mode.running or self.block_started is None)

    def _swap_for_callsigns(self, block) -> None:
        self.bar.set_skippable(False)
        self.skip_note = tr("QSO übersprungen. Stattdessen Rufzeichen.") + " "
        self.blocks[self.index] = replacement = daily.Block(block.kind, "callsign", block.minutes)
        self._start_block(replacement)

    # --- Zwischenkarte -----------------------------------------------------------
    def _show_block_card(self, block, result: dict, new_stars) -> None:
        """Zwischenkarte nach einem Block: Ergebnis, neue Sterne, Fortschritte
        einzelner Zeichen und was als Nächstes kommt."""
        summary = daily.block_summary(block, result, self.due if block.kind == daily.WARMUP else "")
        lines = block_lines(summary)
        strong = []
        if new_stars:
            strong.append(tr("Neu: {stars}").format(stars=stars_named(new_stars)))
            lines += strong
        check = daily.pause_check(result, self.pause_sure) if block.kind == daily.WARMUP else None
        if check:
            if check[1] < check[0]:
                lines.append(tr("Nach der Pause: von {tried} früher sicheren Zeichen saßen {back} gleich wieder. "
                                "Der Rest kommt in den nächsten Tagen zurück.").format(tried=check[0], back=check[1]))
            else:
                lines.append(tr("Nach der Pause: alle {tried} früher sicheren Zeichen saßen gleich wieder.")
                             .format(tried=check[0]))
        if block.mode == "single":
            lines += [moment_line(m) for m in daily.char_moments(self.today)]
        tight = (block.kind == daily.WARMUP and not self.app.daily_relaxed_var.get()
                 and daily.too_tight(result))
        if tight:
            lines.append(tr("Zu knapp? Unter Einstellungen ({key}) gibt es die „Entspannte Tagesübung“: "
                            "das Aufwärmen ohne Zeitlimit.").format(key=ctrl_key(",")))
        errors = result.get("errors")
        if errors and stats.error_review_line(errors):
            # Der Hinweis auf die entspannte Tagesübung gehört nur zum Aufwärmen und nur einmal.
            relaxed_tip = (block.kind == daily.WARMUP and not tight and not self.app.daily_relaxed_var.get())
            lines += [line for line in (stats.error_review_line(errors),
                                        stats.error_review_tip(errors, relaxed_hint=relaxed_tip)) if line]
        if block.kind == daily.MAIN and daily.slower_tomorrow(self.state, self.today):
            lines.append(tr("Das kommt vor – morgen läuft es etwas langsamer, bis es wieder sitzt."))
        following = self.blocks[self.index + 1]
        lines.append(preview_line(following, daily.current_lesson(self.state, 1), self.state["tempo"]))
        title = tr("{block} geschafft").format(block=tr(BLOCK_LABELS[block.kind]))
        self._show_card(title, lines, strong)

    def _show_card(self, title: str, lines, strong=(), then=None, spoken_title=None) -> None:
        """Die Karte bleibt stehen, bis man weitergeht (continue_now);
        `then` kommt nach ihrer Ansage, `spoken_title` ersetzt dort den Titel
        (etwa mit buchstabiertem Zeichen)."""
        self.bar.show_card(title, lines, strong)
        self.card_open = True
        self.card_shown = time.time()
        # Ansage (Barrierefreiheit); F11 liest sie noch einmal vor.
        self.card_text = ". ".join([spoken_title or title, *lines, tr("Weiter mit Enter")]) + "."
        announcer.say(self.card_text, then=then)
        self.app.root.focus_set()  # Enter und Esc sollen ankommen

    def continue_now(self) -> None:
        """Enter oder „Weiter“ auf der Zwischenkarte: nächster Block."""
        if self.active and self.card_open and time.time() - self.card_shown >= ENTER_GRACE_S:
            self._next_block()

    # --- Ende ----------------------------------------------------------------------
    def abort(self, quiet: bool = False) -> None:
        """Esc oder Programmende (`quiet`: ohne Bilanz): laufenden Block
        regulär beenden (Statistik wird gespeichert), dann die Tagesübung."""
        if not self.active:
            return
        self.aborting = True
        self.quiet = quiet
        if self.mode is not None and self.mode.running:
            self.mode.stop()  # führt über on_block_end zu _finish
        else:
            self._finish(completed=False)

    def _finish(self, completed: bool) -> None:
        """Beendet die Tagesübung (fertig oder abgebrochen): Reiter-Einstellungen
        zurück, Tag mit Sternen speichern, Ende ansagen und die Abendbilanz
        zeigen (nach einer Zugabe nur neue Siegel; beim stillen Abbruch, etwa
        am Programmende, nichts davon)."""
        if not self.active:
            return
        self.active = False
        self.card_open = False
        self.bar.set_skippable(False)
        if self.tick_id is not None:
            self.app.root.after_cancel(self.tick_id)
        self.tick_id = None
        if self.mode is not None:
            self.mode.daily_release()
            self.mode = None
        self._release_band()
        review.focus = set()
        daily.finish_day(self.state, self.today, completed)
        daily.save(self.state)
        if self.saved_shared is not None:
            for key, var in self._shared().items():
                var.set(self.saved_shared[key])
            self.saved_shared = None
        if self.saved_content is not None:
            # Die Inhaltswahl wird gespeichert; sonst stünde „Einzeln“ beim
            # nächsten Start auf dem Inhalt des letzten Blocks.
            self.app.show_content(self.saved_content)
            self.saved_content = None
        self.bar.set_enabled(True)
        stars = daily.stars_on(self.state, self.today)
        if self.extra:
            note = tr("Zugabe geschafft.") if completed else tr("Zugabe beendet.")
        else:
            note = end_note(completed, stars)
        self.bar.show_idle(note)
        if not (self.aborting and self.quiet):
            announcer.say(note)
        self.refresh_week(state=self.state)
        self.app.finish_daily()
        if self.aborting and self.quiet:
            return
        if self.extra:
            self.app.show_pending_seals()
        else:
            self._show_summary(stars, completed)

    def _show_summary(self, stars, completed: bool) -> None:
        """Öffnet die Abendbilanz, nach einer vollständigen Übung mit dem Angebot
        „Noch 5 Min“."""
        offer = None
        prosigns = False
        if completed:
            app = self.app
            lesson = daily.current_lesson(self.state, 1)
            learned = review.boxed_chars()
            charset = daily.lesson_charset(lesson, learned)
            confusions = app._confusion_charset(stats.recent_char_data(), stats.load_all_time())
            confusions = "".join(ch for ch in confusions if ch in charset)
            offer = daily.extra_offer(self.state, self.today, lesson, confusions)
            try:
                header_lesson = app.lesson_var.get()
            except tk.TclError:
                header_lesson = 1
            prosigns = daily.prosign_hint_due(self.state, header_lesson, learned)
            if prosigns:
                self.state[daily.PROSIGN_HINT] = self.today.isoformat()
                daily.save(self.state)
        tempo = daily.tempo_outlook(self.state, self.today) if completed else None
        if tempo and tempo["plateau"]:
            self.state[daily.PLATEAU_HINT] = self.today.isoformat()
            daily.save(self.state)
        self.summary = EveningSummary(
            self.app.root, stars, daily.week_comparison(self.today), daily.lesson_outlook(self.state, self.today, self._refresh()),
            offer, self.start_extra, completed, week.stars_in_week(self.state, self.today),
            # Nur Siegel, die noch kein Diplom-Fenster gezeigt hat; es folgt beim Schließen.
            seals=[seal_name(awards.BY_KEY[key], level) for key, level, _ in self.app.pending_seals],
            on_close=self.app.show_pending_seals,
            on_prosigns=self.app.start_prosign_lessons if prosigns else None,
            band=daily.band_change(self.state, self.today), tempo=tempo,
            today=today_line(daily.today_numbers(self.state, self.today),
                             sum(len(chars) for chars in review.by_box()[1:])))
