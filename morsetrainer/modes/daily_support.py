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

from morsetrainer.core import review


class DailyModeMixin:
    # Schlüssel aus settings(), die die Tagesübung setzt und danach zurückstellt.
    daily_keys = ()
    daily_minutes = None   # Dauer des laufenden Tagesübungs-Blocks, sonst None
    last_result = None
    _daily_saved = None
    options_card = None
    _options_pack = None
    streak = best_streak = 0

    def daily_configure(self, minutes: float, **values) -> None:
        current = self.settings()
        self._daily_saved = {key: current[key] for key in self.daily_keys if key in current}
        self.restore_settings(values)
        self.daily_minutes = minutes
        self.set_options_visible(False)

    def daily_release(self) -> None:
        if self._daily_saved is not None:
            self.restore_settings(self._daily_saved)
            self._daily_saved = None
        self.daily_minutes = None
        self.set_options_visible(True)

    def daily_result(self):
        return self.last_result

    def _daily_deadline(self):
        """Ende des Tagesübungs-Blocks als time.time(), sonst None."""
        return time.time() + self.daily_minutes * 60 if self.daily_minutes else None

    def _daily_config(self) -> dict:
        """Kennzeichen für die config-Zeile der Sitzungsdatei."""
        return {"daily": True} if self.daily_minutes else {}

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
