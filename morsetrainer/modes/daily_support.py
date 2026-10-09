"""Schnittstelle der Reiter für die Tagesübung (core/daily.py).

Die Tagesübung schaltet nacheinander vorhandene Reiter mit festen
Einstellungen ein. Jeder beteiligte Reiter erbt DailyModeMixin:

- daily_configure(minutes, **werte): feste Einstellungen setzen (dieselben
  Schlüssel wie settings()), Dauer des Blocks in Minuten (auch krumme
  Werte), Einstellungskarte ausblenden. Vorher werden genau die Werte der
  Schlüssel in `daily_keys` gemerkt.
- daily_release(): diese Werte zurückstellen, Karte wieder zeigen. Was der
  Reiter beim Üben lernt (Zeitlimit, Gruppenlänge, Rufz-Bestwert), bleibt.
- daily_result(): Ergebnis des zuletzt beendeten Durchgangs.

Der Reiter merkt sich dafür in `options_card` seine Einstellungskarte und
ruft beim Auswerten _remember_result() auf; die längste Serie richtiger
Antworten beim ersten Hören zählt er in _count_streak()."""
import time
import tkinter as tk

from morsetrainer.core import review
from morsetrainer.i18n import number, tr
from morsetrainer.widgets import announcer


class DailyModeMixin:
    # Schlüssel aus settings(), die die Tagesübung setzt und danach zurückstellt.
    """Tagesübungs-Schnittstelle eines Reiters (siehe Modulbeschreibung)."""
    daily_keys = ()
    daily_minutes = None   # Dauer des laufenden Tagesübungs-Blocks, sonst None
    last_result = None
    _daily_saved = None
    options_card = None
    _options_pack = None
    streak = best_streak = 0

    def daily_configure(self, minutes: float, **values) -> None:
        """Merkt die Werte der `daily_keys`, setzt die festen Werte `values`, die
        Blockdauer `minutes` und blendet die Einstellungskarte aus."""
        current = self.settings()
        self._daily_saved = {key: current[key] for key in self.daily_keys if key in current}
        self.restore_settings(values)
        self.daily_minutes = minutes
        self.set_options_visible(False)

    def daily_release(self) -> None:
        """Stellt die gemerkten Werte zurück und zeigt die Einstellungskarte wieder."""
        if self._daily_saved is not None:
            self.restore_settings(self._daily_saved)
            self._daily_saved = None
        self.daily_minutes = None
        self.set_options_visible(True)

    def daily_result(self):
        """Ergebnis des zuletzt beendeten Durchgangs (siehe _remember_result), oder
        None."""
        return self.last_result

    def _daily_deadline(self):
        """Ende des Tagesübungs-Blocks als time.time(), sonst None."""
        return time.time() + self.daily_minutes * 60 if self.daily_minutes else None

    def _daily_config(self) -> dict:
        """Kennzeichen für die config-Zeile des gespeicherten Durchgangs."""
        return {"daily": True} if self.daily_minutes else {}

    def show_options_for_run(self, running: bool) -> None:
        """Während eines Durchgangs ist die Einstellungskarte weg, damit
        Antwortfeld, Status und Stop auch bei großer Schrift oder kleinem
        Bildschirm ohne Rollen zu sehen sind; danach ist sie wieder da (in
        der Tagesübung erst mit daily_release)."""
        card = self.options_card
        if running and card is not None:
            # Fokus in der Karte (etwa F5 im Feld „Dauer“): Tasten gingen
            # sonst an ein unsichtbares Feld.
            try:
                focus = card.focus_get()
            except (KeyError, tk.TclError):  # Fokus in einer Klappliste
                focus = None
            if focus is not None and str(focus).startswith(str(card)):
                self.start_button.focus_set()
        self.set_options_visible(not running and not self.daily_minutes)

    def set_options_visible(self, visible: bool) -> None:
        """Einstellungskarte aus- und an derselben Stelle wieder einblenden."""
        card = self.options_card
        if card is None:
            return
        if not visible and card.winfo_manager() == "pack":
            siblings = card.master.pack_slaves()
            index = siblings.index(card)
            following = siblings[index + 1] if index + 1 < len(siblings) else None
            self._options_pack = (card.pack_info(), following)
            card.pack_forget()
        elif visible and self._options_pack is not None:
            info, following = self._options_pack
            info.pop("in", None)
            if following is not None and following.winfo_exists() and following.winfo_manager() == "pack":
                info["before"] = following
            card.pack(**info)
            self._options_pack = None

    def _remember_result(self, session, summary: dict, **extra) -> None:
        """Ergebnis eines Durchgangs für daily_result(); `session` ist die
        gerade abgeschlossene SessionStats (nach finalize())."""
        self.last_result = {
            "correct": summary.get("correct", 0),
            "total": summary.get("total", 0),
            "minutes": round(getattr(session, "duration_s", 0.0) / 60, 2),
            "wpm": session.wpm,
            "review_events": list(getattr(session, "review_events", [])),
            "best_streak": self.best_streak,
            # Je Zeichen [Versuche, flüssig richtig] für die Zwischenkarte.
            "chars": {ch: [e["good"] + e["wrong"], review.fluent_count(e)]
                      for ch, e in getattr(session, "per_char", {}).items()},
            **extra,
        }
        # In der Tagesübung sagt die Zwischenkarte das Ergebnis an.
        if not self.daily_minutes and summary.get("total"):
            announcer.say(tr("Durchgang beendet. {correct} von {total} Zeichen richtig.").format(
                correct=summary["correct"], total=summary["total"]))

    def _stopped_text(self) -> str:
        """Statuszeile nach dem Stop: das Ergebnis des Durchgangs, wie es auch
        angesagt wird (_remember_result); ohne gewertete Zeichen „Gestoppt.“."""
        result = self.last_result or {}
        correct, total = result.get("correct", 0), result.get("total", 0)
        if not total:
            return tr("Gestoppt.")
        return tr("Durchgang beendet: {correct} von {total} Zeichen richtig ({share} %).").format(
            correct=correct, total=total, share=number(round(correct / total * 100)))

    def _count_streak(self, clean: bool = None) -> None:
        """Serie fortsetzen (`clean`: beim ersten Hören richtig, ohne
        Wiederholen) oder abbrechen; None beginnt einen neuen Durchgang."""
        if clean is None:
            self.streak = self.best_streak = 0
        elif clean:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0
