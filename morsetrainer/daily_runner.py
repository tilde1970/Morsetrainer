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
from datetime import date

from morsetrainer.core import awards, daily, koch, practice, review, stats, week
from morsetrainer.i18n import tr
from morsetrainer.widgets import announcer
from morsetrainer.widgets.daily_panel import (
    BLOCK_LABELS, ENTER_GRACE_S, EveningSummary, block_lines, moment_line, preview_line, review_line, stars_named)
from morsetrainer.modes.sequence_mode import COPY, MEMORIZE
from morsetrainer.widgets.awards_panel import seal_name

# Reiter je Modus der Blöcke (deutsche Titel = Schlüssel, siehe app.py).
MODE_TITLES = {"single": "Einzelzeichen", "group": "Gruppen", "word": "Wörter", "callsign": "Rufzeichen",
               "continuous": "Kontinuierlich"}
# Feste Einstellungen je Modus (Schlüssel wie settings() des Reiters).
_SEQUENCE = {"adaptive_tempo": False, "band": False, "give_up": 1}
MODE_SETTINGS = {
    # Das Zeitlimit kommt aus daily.warmup_limit(): ein Limit aus dem Reiter
    # soll nicht ins Aufwärmen nachwirken.
    "single": {"icr": True},
    "group": {**_SEQUENCE, "input_style": COPY, "adaptive": True, "min_len": 2, "max_len": 6},
    "word": {**_SEQUENCE, "input_style": MEMORIZE},
    "callsign": {**_SEQUENCE, "input_style": COPY, "prefixes": "", "learned_only": True, "rufz": False},
    "continuous": {"band": False},
}
# Ein Block, der kürzer lief, wurde von Hand gestoppt (die Reiter enden
# sonst erst nach Ablauf der Zeit und der letzten Eingabe).
STOPPED_EARLY_MIN = 0.1
TICK_MS = 1000


class DailyRunner:
    """Führt die Tagesübung durch: stellt die Blöcke zusammen (core/daily.py),
    schaltet nacheinander die passenden Reiter mit festen Einstellungen ein,
    zeigt dazwischen die Zwischenkarte und am Ende die Abendbilanz."""
    def __init__(self, app, bar):
        self.app = app
        self.bar = bar
        self.active = False
        self.aborting = False
        self.quiet = False
        self.state = {}
        self.blocks = []
        self.index = -1
        self.mode = None
        self.block_started = None
        self.done_minutes = 0.0
        self.saved_shared = None
        self.saved_content = None  # Inhalt im Reiter „Einzeln“ vor der Tagesübung
        self.tick_id = None
        self.card_open = False
        self.card_shown = 0.0
        self.card_text = ""  # zuletzt gezeigte Karte als Ansage
        self.extra = False
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
        self.tick_id = self.app.root.after(TICK_MS, self._tick)

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
        self.state["tempo"] = daily.current_tempo(self.state, wpm, app.farnsworth_wpm())
        daily.save(self.state)

        charset = daily.lesson_charset(lesson, review.boxed_chars())
        self.due = review.due_chars(known=charset)
        self._begin(charset, daily.plan(lesson, len(self.due), self.today))
        if daily.is_new_lesson(self.state, self.today) and 1 < lesson < daily.POST_KOCH and koch.newest_char(lesson):
            # Neue Lektion: das neue Zeichen erst einmal anhören (Lektion 41 bringt keins).
            char = koch.newest_char(lesson)
            self._show_card(tr("Neues Zeichen: {char}").format(char=char),
                            [preview_line(self.blocks[0], lesson, self.state["tempo"])])
            app._play_new_char()
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
        self.bar.set_enabled(False)
        self.bar.show_active()
        self._tick()

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
        block = self.blocks[self.index]
        if not self._start_block(block) and block.mode != "group":
            # Zu wenige Wörter oder Rufzeichen für den Zeichensatz: stattdessen Gruppen.
            self.blocks[self.index] = block = daily.Block(block.kind, "group", block.minutes, {})
            self._start_block(block)
        if self.mode is None:
            self._finish(completed=False)

    def _start_block(self, block) -> bool:
        """Wechselt zum Reiter des Blocks, setzt seine festen Einstellungen und
        startet ihn; False, wenn der Reiter nicht starten konnte."""
        app = self.app
        title = MODE_TITLES[block.mode]
        mode = app.modes[app.mode_titles.index(title)]
        # Zwischen den Blöcken sind die Reiter noch gesperrt; der neue Reiter
        # sperrt sie beim Start wieder.
        for tab_id in app.notebook.tabs():
            app.notebook.tab(tab_id, state="normal")
        app.show_mode(title)
        review.focus = self._focus(block) if block.kind == daily.WARMUP else set()
        settings = {**MODE_SETTINGS[block.mode], **block.params}
        if block.mode == "single":
            settings["icr_limit"] = daily.warmup_limit(self.state)
        mode.daily_configure(block.minutes, **settings)
        self.mode = mode
        self.block_started = time.time()
        mode.start()
        if not mode.running:
            mode.daily_release()
            self.mode = None
            self.block_started = None
            review.focus = set()
            return False
        # Stop beendet hier nicht nur den Block, sondern die ganze Übung.
        mode.start_button.config(text=tr("Tagesübung beenden"))
        return True

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
        if block.mode == "single":
            self.state["icr_limit"] = mode.limit  # vor daily_release(): das ist das Limit des Reiters
        mode.daily_release()
        for attr in ("koch_result", "groups_result"):  # keine Ja/Nein-Fragen danach
            if hasattr(mode, attr):
                setattr(mode, attr, None)
        review.focus = set()
        self.mode = None
        self.block_started = None
        minutes = result.get("minutes", 0.0)
        self.done_minutes += minutes
        # Ein Rufz-Durchgang endet nach seinen Rufzeichen, nicht nach der Zeit.
        stopped_early = minutes < block.minutes - STOPPED_EARLY_MIN and not block.params.get("rufz")
        new_stars = daily.finish_block(self.state, self.today, block, result)
        daily.save(self.state)
        if self.aborting or stopped_early:
            self._finish(completed=False)
        elif self.index + 1 >= len(self.blocks):
            self._next_block()  # letzter Block: gleich zur Abendbilanz
        else:
            self._show_block_card(block, result, new_stars)

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
        if block.mode == "single":
            lines += [moment_line(m) for m in daily.char_moments(self.today)]
        following = self.blocks[self.index + 1]
        lines.append(preview_line(following, daily.current_lesson(self.state, 1), self.state["tempo"]))
        title = tr("{block} geschafft").format(block=tr(BLOCK_LABELS[block.kind]))
        self._show_card(title, lines, strong)

    def _show_card(self, title: str, lines, strong=()) -> None:
        """Die Karte bleibt stehen, bis man weitergeht (continue_now)."""
        self.bar.show_card(title, lines, strong)
        self.card_open = True
        self.card_shown = time.time()
        # Ansage (Barrierefreiheit); F11 liest sie noch einmal vor.
        self.card_text = ". ".join([title, *lines, "Weiter mit Enter"]) + "."
        announcer.say(self.card_text)
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
        if self.tick_id is not None:
            self.app.root.after_cancel(self.tick_id)
        self.tick_id = None
        if self.mode is not None:
            self.mode.daily_release()
            self.mode = None
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
            note = tr("Tagesübung geschafft.") if completed else tr("Tagesübung abgebrochen – deine Sterne bleiben.")
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
        if completed:
            app = self.app
            lesson = daily.current_lesson(self.state, 1)
            charset = daily.lesson_charset(lesson, review.boxed_chars())
            confusions = app._confusion_charset(stats.recent_char_data(), stats.load_all_time())
            confusions = "".join(ch for ch in confusions if ch in charset)
            offer = daily.extra_offer(self.state, self.today, lesson, confusions)
        self.summary = EveningSummary(
            self.app.root, stars, daily.week_comparison(self.today), daily.lesson_outlook(self.state, self.today),
            offer, self.start_extra, completed, week.stars_in_week(self.state, self.today),
            # Nur Siegel, die noch kein Diplom-Fenster gezeigt hat; es folgt beim Schließen.
            seals=[seal_name(awards.BY_KEY[key], level) for key, level, _ in self.app.pending_seals],
            on_close=self.app.show_pending_seals)
