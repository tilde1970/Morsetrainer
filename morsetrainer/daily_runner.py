"""Ablauf der Tagesübung: schaltet nacheinander die vorhandenen Reiter mit
festen Einstellungen ein (Regeln in core/daily.py, Schnittstelle der
Reiter in modes/daily_support.py).

Vorher werden die gemeinsamen Einstellungen (Zeichensatz, Tempo,
Gewichtung) gemerkt und danach zurückgestellt; die Tagesübung arbeitet mit
ihrer eigenen Lektion und ihrem Tagestempo. Ein Block, der von Hand
gestoppt wird (Stop, F5, Esc), beendet die ganze Tagesübung; bereits
verdiente Sterne bleiben."""
import time
from datetime import date

from morsetrainer.core import daily, koch, review, stats
from morsetrainer.i18n import tr
from morsetrainer.modes.sequence_mode import COPY, MEMORIZE

# Reiter je Modus der Blöcke (deutsche Titel = Schlüssel, siehe app.py).
MODE_TITLES = {"single": "Einzelzeichen", "group": "Gruppen", "word": "Wörter", "callsign": "Rufzeichen",
               "continuous": "Kontinuierlich"}
# Feste Einstellungen je Modus (Schlüssel wie settings() des Reiters).
_SEQUENCE = {"adaptive_tempo": False, "band": None, "give_up": 1}
MODE_SETTINGS = {
    "single": {"icr": True},
    "group": {**_SEQUENCE, "input_style": COPY, "adaptive": True, "min_len": 2, "max_len": 6},
    "word": {**_SEQUENCE, "input_style": MEMORIZE},
    "callsign": {**_SEQUENCE, "input_style": COPY, "prefixes": "", "learned_only": True, "rufz": False},
    "continuous": {"band": None},
}
# Ein Block, der kürzer lief, wurde von Hand gestoppt (die Reiter enden
# sonst erst nach Ablauf der Zeit und der letzten Eingabe).
STOPPED_EARLY_MIN = 0.1
PAUSE_BETWEEN_MS = 1500
TICK_MS = 1000


class DailyRunner:
    def __init__(self, app, bar):
        self.app = app
        self.bar = bar
        self.active = False
        self.aborting = False
        self.state = {}
        self.blocks = []
        self.index = -1
        self.mode = None
        self.block_started = None
        self.done_minutes = 0.0
        self.saved_shared = None
        self.tick_id = None
        self.next_id = None
        self.refresh_idle()

    # --- Anzeige ---------------------------------------------------------------
    def refresh_idle(self, note: str = "") -> None:
        self.bar.show_idle(daily.stars_on(daily.load(), date.today()), note)

    def _tick(self) -> None:
        elapsed = self.done_minutes
        if self.block_started is not None:
            elapsed += (time.time() - self.block_started) / 60
        self.bar.update(self.blocks, self.index, elapsed, daily.stars_on(self.state, self.today))
        self.tick_id = self.app.root.after(TICK_MS, self._tick)

    # --- Start ---------------------------------------------------------------------
    def start(self) -> None:
        if self.active or self.app.running_mode:
            return
        app = self.app
        self.today = date.today()
        self.state = daily.load()
        fallback = koch.lesson_of(app.charset_var.get().strip().upper()) or self._lesson_field()
        lesson = daily.current_lesson(self.state, fallback)
        self.state["lesson"] = lesson
        daily.apply_pending_lesson(self.state, self.today)
        lesson = self.state["lesson"]
        try:
            wpm = app.wpm_var.get()
        except Exception:
            wpm = koch.RECOMMENDED_WPM
        self.state["tempo"] = daily.current_tempo(self.state, wpm, app.farnsworth_wpm())
        daily.save(self.state)

        self.saved_shared = {key: var.get() for key, var in self._shared().items()}
        charset = daily.lesson_charset(lesson)
        app.charset_var.set(charset)
        self._apply_tempo(self.state["tempo"])
        app.weighted_var.set(True)
        self.due = review.due_chars(known=charset)
        self.blocks = daily.plan(lesson, len(self.due), self.today)
        self.index = -1
        self.done_minutes = 0.0
        self.active, self.aborting = True, False
        self.bar.set_enabled(False)
        self.bar.show_active()
        self._tick()
        self._next_block()

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
        self.next_id = None
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
        app = self.app
        title = MODE_TITLES[block.mode]
        mode = app.modes[app.mode_titles.index(title)]
        # Zwischen den Blöcken sind die Reiter noch gesperrt; der neue Reiter
        # sperrt sie beim Start wieder.
        for tab_id in app.notebook.tabs():
            app.notebook.tab(tab_id, state="normal")
        app.notebook.select(app.tab_ids[app.mode_titles.index(title)])
        review.focus = self._focus(block) if block.kind == daily.WARMUP else set()
        mode.daily_configure(block.minutes, **MODE_SETTINGS[block.mode], **block.params)
        self.mode = mode
        self.block_started = time.time()
        mode.start()
        if not mode.running:
            mode.daily_release()
            self.mode = None
            self.block_started = None
            review.focus = set()
            return False
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
        mode.daily_release()
        for attr in ("koch_result", "groups_result"):  # keine Ja/Nein-Fragen danach
            if hasattr(mode, attr):
                setattr(mode, attr, None)
        review.focus = set()
        self.mode = None
        self.block_started = None
        minutes = result.get("minutes", 0.0)
        self.done_minutes += minutes
        stopped_early = minutes < block.minutes - STOPPED_EARLY_MIN
        daily.finish_block(self.state, self.today, block, result)
        daily.save(self.state)
        if self.aborting or stopped_early:
            self._finish(completed=False)
        else:
            self.next_id = self.app.root.after(PAUSE_BETWEEN_MS, self._next_block)

    # --- Ende ----------------------------------------------------------------------
    def abort(self) -> None:
        """Esc oder Programmende: laufenden Block regulär beenden (Statistik
        wird gespeichert), dann die Tagesübung."""
        if not self.active:
            return
        self.aborting = True
        if self.mode is not None and self.mode.running:
            self.mode.stop()  # führt über on_block_end zu _finish
        else:
            self._finish(completed=False)

    def _finish(self, completed: bool) -> None:
        if not self.active:
            return
        self.active = False
        for after_id in (self.tick_id, self.next_id):
            if after_id is not None:
                self.app.root.after_cancel(after_id)
        self.tick_id = self.next_id = None
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
        self.bar.set_enabled(True)
        stars = daily.stars_on(self.state, self.today)
        note = tr("Tagesübung geschafft.") if completed else tr("Tagesübung abgebrochen – deine Sterne bleiben.")
        self.bar.show_idle(stars, note)
        self.app.finish_daily()
