"""Statistik je Durchgang: Ergebnis je Zeichen und effektives Mitschreibtempo,
gespeichert in der Datenbank (core/db.py). Jede Zeile wird sofort geschrieben,
damit ein Absturz den Durchgang nicht verliert (nach dem Vorbild des
JsonlLogger in morse_trainer_cont.py aus WZab/morse_trainer).

Ein Durchgang besteht aus (als JSON, je eine Datenbankzeile):
    {"type": "config", ...}
    {"type": "char", "char": "A", "typed": "A", "correct": true, ...}
    {"type": "group", "sent": "KMU", "typed": "KMU", ...}   (nur Gruppen-Modi)
    {"type": "summary", "total": 12, "correct": 10, "per_char": {...}}

Der Zustand "all_time" in der Datenbank summiert je Zeichen über alle
Durchgänge, auch welche Zeichen stattdessen getippt wurden ("confusions";
"" = verpasst)."""
import math
import statistics
from datetime import datetime, timedelta

from morsetrainer import DATA_DIR
from morsetrainer.core import db
from morsetrainer.core import tempo
from morsetrainer.core.koch import SLOW_CHAR_WPM
from morsetrainer.core.morse import display_text, sounds_similar
from morsetrainer.i18n import N_, ctrl_key, tr

STATS_DIR = DATA_DIR / "stats"

# Latenzen darüber (z. B. weil man kurz abgelenkt war) werden gekappt,
# damit ein einzelner Ausreißer den Schnitt eines Zeichens nicht verzerrt.
LATENCY_CAP_S = 5.0

# So viele Verwechslungen je Zeichen zeigt die Tabelle an.
CONFUSIONS_SHOWN = 3


# Ursachen eines Fehlers (record_char): „heard“ ist die Verwechslung mit einem
# anderen Zeichen, alle anderen sind keine und fließen nicht in die Liste der
# Verwechslungen ein.
HEARD = "heard"
CAUSE_LABELS = {
    "late": N_("zu langsam"),
    "replay": N_("erst nach Wiederholung"),
    "missed": N_("verpasst"),
    "swap": N_("vertauscht"),
}


def format_confusions(confusions: dict, causes=None) -> str:
    """{"5": 12, "S": 3, "": 2} -> "5 (12), S (3)". Fehler ohne anderes
    Zeichen ("") sind keine Verwechslung; mit `causes` ({"late": 2, …}) steht
    dahinter, was sie waren („zu langsam 2×“), ohne Angabe (ältere Daten)
    „ohne Eingabe“."""
    top = sorted(((typed, count) for typed, count in confusions.items() if typed),
                 key=lambda item: (-item[1], item[0]))[:CONFUSIONS_SHOWN]
    text = ", ".join(f"{display_text(typed)} ({count})" for typed, count in top)
    causes = {cause: n for cause, n in (causes or {}).items() if cause in CAUSE_LABELS and n}
    other = [f"{tr(label)} {causes[cause]}×" for cause, label in CAUSE_LABELS.items() if cause in causes]
    rest = confusions.get("", 0) - sum(causes.values())
    if rest > 0:
        other.append(f"{tr('ohne Eingabe')} {rest}×")
    return "; ".join(part for part in (text, ", ".join(other)) if part)


def _tally(per_char: dict, char, typed, correct, reaction_time, effective_wpm, latency, assumed, timed, cause) -> None:
    """Zählt eine Antwort in `per_char` ({Zeichen: Summen}) mit."""
    agg = per_char.setdefault(
        char, {"good": 0, "wrong": 0, "reaction_times": [], "effective_wpms": [], "correct_effective_wpms": [],
               "correct_reaction_times": [], "latencies": [], "assumed_latencies": [], "confusions": {},
               "untimed": 0, "causes": {}})
    if not correct:
        agg["wrong"] += 1
        # Nur ein anderes Zeichen ist eine Verwechslung; sonst zählt es unter "".
        key = typed if cause == HEARD else ""
        agg["confusions"][key] = agg["confusions"].get(key, 0) + 1
        agg["causes"][cause] = agg["causes"].get(cause, 0) + 1
    if not timed:
        if correct:
            agg["good"] += 1
            agg["untimed"] += 1
        return
    if correct:
        agg["good"] += 1
        agg["correct_effective_wpms"].append(effective_wpm)
        agg["correct_reaction_times"].append(reaction_time)
        if latency is not None:
            capped = min(max(latency, 0.0), LATENCY_CAP_S)
            agg["latencies"].append(capped)
            if assumed:
                agg["assumed_latencies"].append(capped)
    agg["reaction_times"].append(reaction_time)
    agg["effective_wpms"].append(effective_wpm)


class SessionStats:
    """Zeichnet einen Durchgang auf: jedes Zeichen sofort in die Datenbank, am
    Ende die Zusammenfassung samt Übernahme in Gesamtstatistik und Lernkartei
    (finalize)."""
    def __init__(self, mode: str, charset: str, wpm: int, freq: int, group_len=None, farnsworth_wpm=None,
                 self_assessed=False, in_history=True, review_promote=False, char_stats=True, config_extra=None,
                 persist=True):
        """`self_assessed`: Ergebnisse beruhen auf eigener Bewertung (Kopfhören,
        J/N). Sie werden protokolliert, aber nicht in die Gesamtstatistik und den
        Fortschrittsverlauf übernommen. `in_history=False`: Die Sitzung hat
        einen eigenen Eintrag im Verlauf (z. B. Rufz über log_result) und
        erscheint dort nicht zusätzlich; die Zeichenstatistik zählt normal.
        `review_promote`: Zufallszeichen, die Sitzung darf Zeichen in der
        Lernkartei hochstufen (core/review.py); sonst nur zurückstufen.
        `char_stats=False`: Klartext (Wörter, QSOs …), bei dem der
        Zusammenhang viele Zeichen verrät. Die Sitzung erscheint im Verlauf,
        fließt aber nicht in die Zeichenstatistik, die Gewichtung und die
        Lernkartei ein; schwache Zeichen wirkten sonst sicherer, als sie sind.
        `config_extra`: weitere Felder für die config-Zeile (Lektion,
        Bandbedingungen …), damit sich später nachvollziehen lässt, unter
        welchen Bedingungen geübt wurde."""
        self.review_promote = review_promote
        # Entspannte Tagesübung (ohne Zeitlimit): zählt nicht für die Lernkartei.
        self.review_skip = bool((config_extra or {}).get("relaxed"))
        self.char_stats = char_stats
        self.start_time = datetime.now()
        self.self_assessed = self_assessed
        self.mode = mode
        self.charset = charset
        self.wpm = wpm
        self.freq = freq
        self.group_len = group_len
        self.rounds = []  # Ergebnisse je Zeichen, flach über den ganzen Durchgang
        # per_char zählt alles, was im Durchgang geschah (Anzeige); kept_char ohne die
        # erneuten Abfragen nach einem Fehler: nur das geht in Gesamtstatistik,
        # Lernkartei und Gewichtung ein (eine Bestätigung ist kein Erkennen).
        self.per_char = {}
        self.kept_char = {}

        # Lässt sich das Protokoll nicht schreiben (Platte voll, keine
        # Schreibrechte), geht die Übung ohne Protokoll weiter.
        self.log_error = None
        self.session_id = None
        config = {
            "type": "config",
            "mode": mode,
            "charset": charset,
            "wpm": wpm,
            "freq": freq,
            "group_len": group_len,
            "farnsworth_wpm": farnsworth_wpm,
            "start_time": self.start_time.isoformat(timespec="seconds"),
            **({"self_assessed": True} if self_assessed else {}),
            **({"in_history": False} if not in_history else {}),
            **({"char_stats": False} if not char_stats else {}),
            **(config_extra or {}),
        }
        try:
            if persist:  # False: ein abgestürzter Durchgang wird nur nachgerechnet (recover_unfinished)
                self.session_id = db.start_session(config)
        except (db.Error, OSError) as exc:
            self.log_error = str(exc)
        # Hochstufungen in der Lernkartei durch diese Sitzung (review.update).
        self.review_events = []

    def _write_line(self, obj: dict) -> None:
        """Nach dem ersten Fehler schreibt der Durchgang nichts mehr; er
        bleibt ohne Zusammenfassung wie nach einem Absturz."""
        if self.session_id is None or self.log_error is not None:
            return
        try:
            db.add_event(self.session_id, obj)
        except (db.Error, OSError) as exc:
            self.log_error = str(exc)

    def record_char(self, char: str, typed: str, correct: bool, reaction_time: float, effective_wpm: float,
                    latency=None, assumed=False, timed=True, cause=None, retry=False, lag_chars=None) -> None:
        """Ergebnis für ein einzelnes Zeichen festhalten und sofort speichern.

        `latency` ist die Zeit vom Ende des Tons (des letzten Punkts oder
        Strichs) bis zum Tastendruck, unabhängig von Zeichenlänge und Tempo;
        beim fortlaufenden Mitschreiben ab der vorigen Taste, wenn die später
        kam. Nur wo sie sich einem einzelnen Zeichen zuordnen lässt, sonst
        None (siehe core/latency). `reaction_time` ist die Zeit ab Tonbeginn,
        `effective_wpm` das daraus gerechnete Tempo (morse.effective_wpm).
        `assumed`: nicht gemessen, sondern für eine richtige, aber unsichere
        Antwort gesetzt (2 × die übliche Latenz); zählt für die Gewichtung
        dieses Zeichens, nicht für die übliche Latenz. `timed` False: In der
        Zeit steckt etwas anderes (F11-Ansage ohne Zeitlimit); die Antwort
        zählt richtig/falsch, aber in keinen Zeit- und Tempowert und in der
        Lernkartei weder als flüssig noch als langsam.
        `cause` (bei einem Fehler): HEARD (ein anderes Zeichen getippt, Standard
        mit getipptem Zeichen), "late" (zu langsam), "replay" (erst nach
        Wiederholung), "missed" (nichts getippt, Standard ohne), "swap"
        (mit dem Nachbarn vertauscht); nur HEARD ist eine Verwechslung.
        `retry`: erneute Abfrage kurz nach einem Fehler; sie zählt im Durchgang,
        aber nicht in Gesamtstatistik, Lernkartei und Gewichtung.
        `lag_chars`: Beim Mitschreiben am Stück, wie viele Zeichen die Taste hinter
        dem Tonende des Zeichens kam (Sekunden mal Zeichen je Sekunde beim damals
        gesendeten Tempo), auch wenn sie hinterherschreibt (anders als `latency`,
        die ab der vorigen Taste zählt); nur für core/insights."""
        if not correct and cause is None:
            cause = HEARD if typed else "missed"
        entry = {
            "char": char,
            "typed": typed,
            "correct": correct,
            "reaction_time_s": round(reaction_time, 3),
            "effective_wpm": round(effective_wpm, 1),
        }
        if not correct:
            entry["cause"] = cause
        if retry:
            entry["retry"] = True
        if latency is not None and timed:
            entry["latency_s"] = round(latency, 3)
            if assumed:
                entry["latency_assumed"] = True
        if lag_chars is not None and timed:
            entry["lag_chars"] = round(lag_chars, 2)
        if not timed:
            entry["untimed"] = True
        self.rounds.append(entry)
        self._write_line({"type": "char", **entry})
        args = (char, typed, correct, reaction_time, effective_wpm, latency, assumed, timed, cause)
        _tally(self.per_char, *args)
        if not retry:
            _tally(self.kept_char, *args)

    def record_group(self, sent: str, typed: str, wpm=None, first=None) -> None:
        """Eine abgeschickte Gruppe festhalten (zusätzlich zu den record_char-
        Aufrufen, die der Aufrufer je Zeichen macht). `wpm`: Tempo, mit dem sie
        gesendet wurde, falls es von dem des Durchgangs abweicht. `first`: beim
        ersten Versuch flüssig richtig (ohne Wiederholen, im Zeitfenster) – für die
        Diplome WPX und Q-Gruppen-Kenner."""
        entry = {"type": "group", "sent": sent, "typed": typed}
        if wpm is not None:
            entry["wpm"] = wpm
        if first is not None:
            entry["first"] = first
        self._write_line(entry)

    def char_rows(self):
        """Zeilen je Zeichen (Zeichen, richtig, falsch, gesamt, Reaktionszeit,
        effektives Tempo, Verwechslungen), für die Anzeige; die Reaktionszeit
        siehe measured_latency(). Tempo und Reaktion nur aus richtigen
        Antworten (None, solange es keine gibt); Fehler zählt „falsch“."""
        rows = []
        for char, e in self.per_char.items():
            total = e["good"] + e["wrong"]
            reaction = measured_latency(sum(e["latencies"]), len(e["latencies"]),
                                        sum(e["assumed_latencies"]), len(e["assumed_latencies"]))
            avg_wpm = statistics.mean(e["correct_effective_wpms"]) if e["correct_effective_wpms"] else None
            rows.append((char, e["good"], e["wrong"], total, reaction, avg_wpm,
                         format_confusions(e["confusions"], e["causes"])))
        rows.sort(key=_weakness)
        return rows

    def summary(self):
        """Zusammenfassung des Durchgangs: Anzahl, richtige, Trefferquote in %,
        mittleres effektives Tempo der richtigen Zeichen und Zeichen pro Minute."""
        total = len(self.rounds)
        correct = sum(1 for r in self.rounds if r["correct"])
        accuracy = (correct / total * 100) if total else 0.0
        timed = [r for r in self.rounds if r["correct"] and not r.get("untimed")]
        wpms = [r["effective_wpm"] for r in timed]
        avg_wpm = statistics.mean(wpms) if wpms else 0.0
        times = [r["reaction_time_s"] for r in timed]
        return {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(accuracy, 1),
            "avg_effective_wpm": round(avg_wpm, 1),
            "cpm": _cpm(len(times), sum(times)),
        }

    def _per_char_summary(self):
        """Je Zeichen: richtig, falsch, mittlere Reaktionszeit, mittleres
        effektives Tempo und Verwechslungen (für die Zusammenfassung)."""
        out = {}
        for char, e in self.kept_char.items():
            out[char] = {
                "good": e["good"],
                "wrong": e["wrong"],
                "avg_reaction_time_s": round(statistics.mean(e["reaction_times"]), 3)
                if e["reaction_times"] else 0.0,
                "avg_effective_wpm": round(statistics.mean(e["effective_wpms"]), 1)
                if e["effective_wpms"] else 0.0,
                "confusions": e["confusions"],
                "causes": e["causes"],
            }
        return out

    def finalize(self, extra=None):
        """Zusammenfassung schreiben und in Gesamtstatistik und Lernkartei
        übernehmen, alles in einer Transaktion, damit ein Absturz sie nicht
        auseinanderbringt. Gibt die Nummer des Durchgangs (Datenbank-id) zurück,
        oder None, wenn er nicht gespeichert wurde oder nie etwas aufgezeichnet hat
        (der leere Durchgang wird dann entfernt). `extra` ergänzt Felder der
        Zusammenfassung (z. B. "wpm_effective_reached")."""
        self.duration_s = round((datetime.now() - self.start_time).total_seconds(), 1)
        if not self.rounds:
            if self.session_id is not None:
                try:
                    db.delete_session(self.session_id)
                except (db.Error, OSError):
                    pass
            return None
        summary = {
            "type": "summary", **self.summary(), "duration_s": self.duration_s, **(extra or {}),
            "per_char": self._per_char_summary(),
        }
        return self._commit(summary)

    def _commit(self, summary: dict, merge: bool = True, promote=None, events=None):
        """Zusammenfassung schreiben und, mit `merge`, in Gesamtstatistik und Lernkartei
        übernehmen, in einer Transaktion: ein Durchgang mit Zusammenfassung ist übernommen,
        einer ohne nicht (daran erkennt recover_unfinished, was fehlt)."""
        try:
            with db.transaction():
                # Hat ihn inzwischen ein anderes Fenster als abgestürzt abgeschlossen, nicht doppelt zählen.
                if self.session_id is not None and db.is_finished(self.session_id):
                    return self.session_id
                if self.session_id is not None:
                    db.finish_session(self.session_id, summary)
                if merge and not self.self_assessed and self.char_stats:
                    _merge_all_time(self)
                    from morsetrainer.core import review  # review importiert stats
                    if promote is None:
                        promote = self.review_promote and review.can_promote(self.charset)
                    if not self.review_skip:
                        review.update(self.kept_char, promote=promote,
                                      events=self.review_events if events is None else events,
                                      fast=(self.wpm or 0) >= SLOW_CHAR_WPM)
        except (db.Error, OSError) as exc:
            self.log_error = self.log_error or str(exc)
        return self.session_id if self.log_error is None else None


# Ein Durchgang ohne Zusammenfassung gilt erst nach so langer Zeit als abgestürzt
# (ein anderes Fenster könnte ihn noch üben).
RECOVER_AFTER = timedelta(hours=2)


def recover_unfinished(now=None) -> int:
    """Schließt Durchgänge ab, die ohne Zusammenfassung blieben (Absturz, hartes
    Beenden): Aus ihren gespeicherten Zeichen entsteht die Zusammenfassung, und sie
    gehen in die Gesamtstatistik und die Lernkartei ein, als wären sie normal zu Ende
    gegangen (ohne Hochstufungen; die Dauer ist die Summe der Reaktionszeiten).
    Durchgänge vor dem letzten Zurücksetzen der Gesamtstatistik bekommen nur die
    Zusammenfassung. Ohne eine einzige Zeile werden sie entfernt. Gibt die Zahl der
    nachgetragenen Durchgänge zurück."""
    now = now or datetime.now()
    reset = _after_reset(datetime.min)
    done = 0
    for session_id, config in db.unfinished_sessions():
        try:
            start = datetime.fromisoformat(config["start_time"])
            if now - start < RECOVER_AFTER:
                continue
            events = db.session_events(session_id)
            if not events:
                db.delete_session(session_id)
                continue
            rows = [e for e in events if e.get("type") == "char"]
            if not rows:
                continue  # nur Gruppen o. Ä.: daraus lässt sich nichts nachrechnen
            session = SessionStats(
                config.get("mode", ""), config.get("charset", ""), config.get("wpm"), config.get("freq"),
                group_len=config.get("group_len"), farnsworth_wpm=config.get("farnsworth_wpm"),
                self_assessed=bool(config.get("self_assessed")), in_history=config.get("in_history") is not False,
                char_stats=config.get("char_stats") is not False, persist=False,
                config_extra={"relaxed": True} if config.get("relaxed") else None)
            session.start_time = start
            for e in rows:
                session.record_char(e.get("char", ""), e.get("typed", ""), bool(e.get("correct")),
                                    float(e.get("reaction_time_s") or 0), float(e.get("effective_wpm") or 0),
                                    latency=e.get("latency_s"), assumed=bool(e.get("latency_assumed")),
                                    timed=not e.get("untimed"), cause=e.get("cause"), retry=bool(e.get("retry")))
            session.session_id = session_id
            session.duration_s = round(sum(r["reaction_time_s"] for r in session.rounds), 1)
            summary = {"type": "summary", **session.summary(), "duration_s": session.duration_s,
                       "per_char": session._per_char_summary(), "recovered": True}
            if session._commit(summary, merge=start >= reset, promote=False, events=[]) is not None:
                done += 1
        except (TypeError, ValueError, KeyError, AttributeError):
            continue  # unlesbare Zeilen: dieser Durchgang bleibt, wie er ist
        except (db.Error, OSError):
            break
    return done


def _merge_all_time(session: "SessionStats") -> None:
    """Addiert die Ergebnisse je Zeichen aus `session` zur Gesamtstatistik und
    speichert sie (aufgerufen innerhalb der Transaktion von finalize)."""
    all_time = load_all_time()
    for char, e in session.kept_char.items():
        x = all_time.setdefault(
            char,
            {
                "good": 0, "wrong": 0,
                "total_reaction_time_s": 0.0, "total_effective_wpm": 0.0,
                "correct_effective_wpm_total": 0.0, "attempts": 0,
            },
        )
        x["good"] += e["good"]
        x["wrong"] += e["wrong"]
        x["total_reaction_time_s"] += sum(e["reaction_times"])
        x["total_effective_wpm"] += sum(e["effective_wpms"])
        x["correct_effective_wpm_total"] += sum(e["correct_effective_wpms"])
        x["attempts"] += e["good"] + e["wrong"]
        # Richtige ohne Zeit (record_char, `timed`): nicht im Tempo-Schnitt.
        x["untimed"] = x.get("untimed", 0) + e.get("untimed", 0)
        # Für die gemessenen Zeichen pro Minute. Einträge ohne diese Felder
        # (ältere Daten) beginnen hier bei null.
        correct_times = e.get("correct_reaction_times", [])
        x["correct_reaction_time_s"] = x.get("correct_reaction_time_s", 0.0) + sum(correct_times)
        x["correct_timed_count"] = x.get("correct_timed_count", 0) + len(correct_times)
        # Latenz-Felder fehlen in älteren Einträgen der Gesamtstatistik: bei null beginnen.
        x["total_latency_s"] = x.get("total_latency_s", 0.0) + sum(e["latencies"])
        x["latency_count"] = x.get("latency_count", 0) + len(e["latencies"])
        # Davon angenommen statt gemessen (siehe record_char, `assumed`).
        x["assumed_latency_s"] = x.get("assumed_latency_s", 0.0) + sum(e["assumed_latencies"])
        x["assumed_latency_count"] = x.get("assumed_latency_count", 0) + len(e["assumed_latencies"])
        confusions = x.setdefault("confusions", {})
        for typed, count in e["confusions"].items():
            confusions[typed] = confusions.get(typed, 0) + count
        causes = x.setdefault("causes", {})
        for cause, count in e["causes"].items():
            causes[cause] = causes.get(cause, 0) + count
    db.save_state(ALL_TIME_KEY, all_time)


ALL_TIME_KEY = "all_time"
RESET_KEY = "reset"


def load_all_time() -> dict:
    """Summen je Zeichen über alle bisherigen Durchgänge. Ein beschädigter
    Eintrag wird beiseitegelegt (siehe db.load_state), statt abzustürzen; ein
    einzelnes beschädigtes Zeichen wird bereinigt (_clean_all_time)."""
    return _clean_all_time(db.load_state(ALL_TIME_KEY, {}))


# Zahlenfelder eines Zeichens der Gesamtstatistik, die Auswertung und Übernahme voraussetzen.
ALL_TIME_COUNTS = ("good", "wrong", "attempts")
ALL_TIME_SUMS = ("total_reaction_time_s", "total_effective_wpm", "correct_effective_wpm_total")
# Felder, die ältere Einträge nicht haben: fehlen sie oder sind unbrauchbar, beginnen sie bei null.
ALL_TIME_OPTIONAL = ("untimed", "correct_reaction_time_s", "correct_timed_count", "total_latency_s",
                     "latency_count", "assumed_latency_s", "assumed_latency_count")


def _is_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _clean_all_time(all_time: dict) -> dict:
    """Die Gesamtstatistik ohne Einträge, an denen Übernahme und Auswertung
    scheitern würden (von Hand geändert, kaputter Import, künftiges Format):
    Was kein Wörterbuch ist, entfällt; fehlende oder unbrauchbare Zahlenfelder
    beginnen bei null."""
    clean = {}
    for char, entry in all_time.items():
        if not isinstance(entry, dict):
            continue
        entry = dict(entry)
        for key in ALL_TIME_COUNTS:
            if type(entry.get(key)) is not int or entry[key] < 0:
                entry[key] = 0
        for key in ALL_TIME_SUMS:
            if not _is_number(entry.get(key)):
                entry[key] = 0.0
        for key in ALL_TIME_OPTIONAL:
            if key in entry and not _is_number(entry[key]):
                del entry[key]
        for key in ("confusions", "causes"):
            if not isinstance(entry.get(key), dict):
                entry.pop(key, None)
        clean[char] = entry
    return clean


def reset_all_time() -> None:
    """Gesamtstatistik löschen. Die Protokolle der einzelnen Durchgänge
    bleiben, nur die laufenden Summen werden geleert. Der Zeitpunkt wird
    gemerkt, damit recent_char_data() ältere Protokolle übergeht."""
    from morsetrainer.core import review
    try:
        with db.transaction():
            db.delete_state(ALL_TIME_KEY)
            review.reset()
            db.save_state(RESET_KEY, {"time": datetime.now().isoformat(timespec="seconds")})
    except (db.Error, OSError):
        pass


# Verwechslungen „vergessen“: nur Sitzungen der letzten so vielen Tage.
RECENT_DAYS = 30


def _after_reset(cutoff: datetime) -> datetime:
    """`cutoff`, aber nicht vor dem letzten Zurücksetzen der Gesamtstatistik."""
    reset = db.load_state(RESET_KEY, {}).get("time")
    try:
        reset = datetime.fromisoformat(reset) if reset else None
        # Ein Zurücksetzen in der Zukunft (Uhr ging falsch) würde alles bis dahin ausblenden.
        if reset is None or reset > datetime.now() + CLOCK_TOLERANCE:
            return cutoff
        return max(cutoff, reset)
    except (TypeError, ValueError):  # kein Text, kein Zeitpunkt oder mit Zeitzone
        return cutoff


# So weit darf ein gespeicherter Zeitpunkt vor der Uhr liegen, bevor er als Uhrenfehler gilt.
CLOCK_TOLERANCE = timedelta(days=1)


def clock_ahead(now=None):
    """Startzeit des letzten Durchgangs, wenn sie in der Zukunft liegt (die Uhr
    des Rechners ging bei einer früheren Übung falsch oder geht jetzt nach),
    sonst None. Datum und Siegel, die damit entstanden, bleiben, wie sie sind."""
    now = now or datetime.now()
    try:
        latest = datetime.fromisoformat(db.latest_start())
    except (TypeError, ValueError):
        return None
    return latest if latest.tzinfo is None and latest > now + CLOCK_TOLERANCE else None


def _char_events(since: datetime, completed_only: bool = False):
    """(Startzeit, Modus, Zeile) aller Zeichen-Zeilen der Durchgänge ab
    `since`, ohne selbst bewertete Sitzungen und Klartext (zählen nicht für
    Zeichen); mit `completed_only` auch ohne Durchgänge, die nie abgeschlossen
    wurden (Absturz, Programm beendet)."""
    for session in db.sessions(since=since.replace(microsecond=0), events=True):
        if session.config.get("self_assessed") or session.config.get("char_stats") is False:
            continue
        if completed_only and not session.summary:
            continue
        try:
            start = datetime.fromisoformat(session.config["start_time"])
        except (KeyError, TypeError, ValueError):
            continue
        if start.tzinfo is not None:  # von Hand eingetragen: in Ortszeit wie alle anderen
            start = start.astimezone().replace(tzinfo=None)
        for obj in session.events:
            if obj.get("type") == "char" and "char" in obj:
                yield start, session.config.get("mode"), obj


def recent_char_data(days: int = RECENT_DAYS, now=None) -> dict:
    """Zeichenstatistik wie die Gesamtstatistik ({Zeichen: {"good", "wrong",
    "confusions", "causes", "latencies", "assumed_latencies"}}), aber nur aus
    den Durchgängen der letzten `days` Tage und nach dem letzten Zurücksetzen.
    Längst behobene Verwechslungen fallen so heraus. Selbst bewertete
    Sitzungen, Klartext und erneute Abfragen nach einem Fehler zählen nicht."""
    now = now or datetime.now()
    data = {}
    for _start, _mode, obj in _char_events(_after_reset(now - timedelta(days=days))):
        if obj.get("retry"):
            continue  # erneute Abfrage nach einem Fehler: zählt nicht (siehe record_char)
        e = data.setdefault(obj["char"], {"good": 0, "wrong": 0, "confusions": {}, "causes": {},
                                          "latencies": [], "assumed_latencies": []})
        if obj.get("correct"):
            e["good"] += 1
            latency = obj.get("latency_s")
            if not obj.get("untimed") and type(latency) in (int, float) and math.isfinite(latency):
                capped = min(max(latency, 0.0), LATENCY_CAP_S)
                e["latencies"].append(capped)
                if obj.get("latency_assumed"):
                    e["assumed_latencies"].append(capped)
        else:
            e["wrong"] += 1
            typed = obj.get("typed", "")
            # Ältere Zeilen ohne Ursache: ein getipptes Zeichen war eine Verwechslung.
            cause = obj.get("cause") or (HEARD if typed else "missed")
            key = typed if cause == HEARD else ""
            e["confusions"][key] = e["confusions"].get(key, 0) + 1
            e["causes"][cause] = e["causes"].get(cause, 0) + 1
    return data


# Vergleich im Reiter Statistik: die letzten COMPARE_DAYS Tage gegen die
# BEFORE_DAYS Tage davor. Der Schnitt über alle Durchgänge bewegt sich kaum,
# weil die alten, langsamen Antworten dauerhaft mitzählen.
COMPARE_DAYS = 7
BEFORE_DAYS = 30
# Die Reaktion nur aus diesem Modus: Beim fortlaufenden Mitschreiben zählt
# sie ab der vorigen Taste (core/latency), ein anderer Mix der Modi in den
# beiden Zeiträumen täuschte sonst Fortschritt vor (wie daily.latencies).
REACTION_MODE = "single"
# Trend je Zeichen erst ab so vielen gemessenen Reaktionen auf jeder Seite;
# darunter ist ein Unterschied meist Zufall.
MIN_TREND_COUNT = 20
# Die Vergleichszeile nennt einen Zeitraum erst ab so vielen Antworten.
MIN_COMPARE_COUNT = 10
RECENT, BEFORE = "recent", "before"


def _new_period() -> dict:
    return {"good": 0, "wrong": 0, "latency_s": 0.0, "latency_count": 0, "latencies": []}


def _measured(obj: dict):
    """Gemessene Reaktion einer richtigen Antwort, gekappt; sonst None."""
    latency = obj.get("latency_s")
    if (obj.get("correct") is not True or obj.get("latency_assumed") or type(latency) not in (int, float)
            or not math.isfinite(latency)):
        return None
    return min(max(latency, 0.0), LATENCY_CAP_S)


def period_comparison(now=None) -> dict:
    """Trefferquote und Reaktion der letzten COMPARE_DAYS Tage (RECENT) und
    der BEFORE_DAYS Tage davor (BEFORE), gesamt und je Zeichen:
    {RECENT: Zahlen, BEFORE: Zahlen, "chars": {Zeichen: {RECENT, BEFORE}},
    "modes": {Modus: {RECENT: [richtig, falsch], BEFORE: [...]}}, "before_days":
    Tage, die BEFORE wirklich abdeckt (weniger als BEFORE_DAYS bei jungen
    Daten)}. Trefferquote aus allen Modi (je Modus unter "modes", weil der
    Modus-Mix den Schnitt verschiebt), Reaktion nur aus REACTION_MODE: richtige
    Antworten, gemessen (nicht angenommen), gekappt bei LATENCY_CAP_S. Nur
    abgeschlossene Durchgänge zählen, ohne Wiederholungsabfragen und Zeichen
    ohne Zeitmessung (wie in der Gewichtung). Nach period_numbers() bzw.
    char_trend() lesen."""
    now = now or datetime.now()
    split = now - timedelta(days=COMPARE_DAYS)
    result = {RECENT: _new_period(), BEFORE: _new_period(), "chars": {}, "modes": {}, "before_days": BEFORE_DAYS}
    earliest = split
    for start, mode, obj in _char_events(_after_reset(split - timedelta(days=BEFORE_DAYS)), completed_only=True):
        if obj.get("retry") or obj.get("untimed"):
            continue
        side = RECENT if start >= split else BEFORE
        if side == BEFORE:
            earliest = min(earliest, start)
        if isinstance(mode, str):
            counts = result["modes"].setdefault(mode, {RECENT: [0, 0], BEFORE: [0, 0]})[side]
            counts[0 if obj.get("correct") is True else 1] += 1
        char = result["chars"].setdefault(obj["char"], {RECENT: _new_period(), BEFORE: _new_period()})
        latency = _measured(obj) if mode == REACTION_MODE else None
        for period in (result[side], char[side]):
            period["good" if obj.get("correct") is True else "wrong"] += 1
            if latency is not None:
                period["latency_s"] += latency
                period["latency_count"] += 1
                period["latencies"].append(latency)
    if earliest < split:
        result["before_days"] = min(BEFORE_DAYS, max((split - earliest).days, 1))
    return result


# So viele Antworten in den letzten Tagen, damit ein Zeichen als „neu“ gilt (kein Ausreißer).
NEW_CHAR_MIN_COUNT = 3


def new_chars(comparison: dict) -> list:
    """Zeichen, die in den letzten COMPARE_DAYS Tagen mindestens NEW_CHAR_MIN_COUNT
    mal vorkamen, davor aber gar nicht (nach period_comparison())."""
    return sorted(char for char, entry in comparison.get("chars", {}).items()
                  if entry[BEFORE]["good"] + entry[BEFORE]["wrong"] == 0
                  and entry[RECENT]["good"] + entry[RECENT]["wrong"] >= NEW_CHAR_MIN_COUNT)


def period_numbers(period: dict):
    """(Trefferquote in Prozent, Reaktion als Median in s, gemessene Reaktionen)
    eines Zeitraums; None, wo es nichts gibt. Median wie in der Zeichentabelle
    (char_trend), robust gegen einzelne lange Antworten."""
    total = period["good"] + period["wrong"]
    accuracy = period["good"] / total * 100 if total else None
    count = period["latency_count"]
    return accuracy, (statistics.median(period["latencies"]) if count else None), count


def char_trend(chars: dict, char: str):
    """(Reaktion davor, Reaktion zuletzt) eines Zeichens als Median – robust
    gegen einzelne lange Antworten – oder None, solange eine Seite weniger als
    MIN_TREND_COUNT Messungen hat."""
    entry = chars.get(char)
    if entry is None:
        return None
    before, recent = entry[BEFORE]["latencies"], entry[RECENT]["latencies"]
    if min(len(before), len(recent)) < MIN_TREND_COUNT:
        return None
    return statistics.median(before), statistics.median(recent)


def measured_latency(total_s: float, count: int, assumed_s: float, assumed_count: int):
    """Mittlere Reaktionszeit: vom Ende des Tons (letzter Punkt oder Strich)
    bis zum Tastendruck, nur richtige Antworten und nur gemessene Werte (ohne
    die für „richtig, aber unsicher“ angenommenen); None ohne Messung. Anders
    als die Zeit ab Beginn des Zeichens hängt sie nicht von Zeichenlänge und
    Tempo ab."""
    count -= assumed_count
    return (total_s - assumed_s) / count if count > 0 else None


def all_time_char_rows(all_time: dict):
    """Zeilen wie SessionStats.char_rows(), aber aus den gespeicherten
    Gesamtsummen statt aus einem laufenden Durchgang."""
    rows = []
    for char, e in all_time.items():
        total = e["good"] + e["wrong"]
        avg_rt = measured_latency(e.get("total_latency_s", 0.0), e.get("latency_count", 0),
                                  e.get("assumed_latency_s", 0.0), e.get("assumed_latency_count", 0))
        # Nur richtige Antworten mit Zeit (wie die Zeile darüber, all_time_summary).
        timed_good = e["good"] - e.get("untimed", 0)
        avg_wpm = e.get("correct_effective_wpm_total", 0.0) / timed_good if timed_good > 0 else None
        rows.append((char, e["good"], e["wrong"], total, avg_rt, avg_wpm,
                     format_confusions(e.get("confusions", {}), e.get("causes"))))
    rows.sort(key=_weakness)
    return rows


def _weakness(row):
    """Sortierschlüssel für die Zeichentabelle: die höchste Fehlerquote zuerst
    (geglättet, damit 1 von 2 nicht vor 40 von 50 steht), dann die meisten Fehler."""
    _, _, wrong, total, *_ = row
    return (-(wrong + 1) / (total + 2) if wrong else 0.0, -wrong, row[0])


def all_time_summary(all_time: dict):
    """Zusammenfassung wie SessionStats.summary(), aber aus den gespeicherten
    Gesamtsummen statt aus einem laufenden Durchgang."""
    total = sum(e["good"] + e["wrong"] for e in all_time.values())
    correct = sum(e["good"] for e in all_time.values())
    accuracy = (correct / total * 100) if total else 0.0
    correct_wpm_total = sum(e.get("correct_effective_wpm_total", 0.0) for e in all_time.values())
    timed_correct = correct - sum(e.get("untimed", 0) for e in all_time.values())
    avg_wpm = (correct_wpm_total / timed_correct) if timed_correct > 0 else 0.0
    timed = sum(e.get("correct_timed_count", 0) for e in all_time.values())
    timed_s = sum(e.get("correct_reaction_time_s", 0.0) for e in all_time.values())
    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(accuracy, 1),
        "avg_effective_wpm": round(avg_wpm, 1),
        "cpm": _cpm(timed, timed_s),
    }


def _cpm(count: int, seconds: float) -> float:
    """Gemessene Zeichen pro Minute: richtig erkannte Zeichen durch die dafür
    gebrauchte Zeit (Zeichen plus Reaktion); 0.0 ohne Messung."""
    return round(count * 60 / seconds, 1) if count and seconds > 0 else 0.0

# Ursachen-Rückblick (error_review): erst ab so vielen Fehlern und diesem Anteil
# an den Antworten, sonst bliebe nur das Lob stehen.
REVIEW_MIN_ERRORS = 4
REVIEW_MIN_SHARE = 0.05
REVIEW_MAX_CAUSES = 3
REVIEW_PAIR_MIN = 2
REVIEW_ORDER = (HEARD, "late", "missed", "replay", "swap")


def error_review(per_char: dict):
    """Woran die Fehler eines Durchgangs lagen, aus SessionStats.kept_char:
    {"total", "answers", "causes": {Ursache: Anzahl}, "pair": (gesendet,
    getippt, Anzahl) oder None}. Das häufigste Paar zählt nur als echte
    Verwechslung."""
    total = answers = 0
    causes, pairs = {}, {}
    for char, e in per_char.items():
        total += e["wrong"]
        answers += e["good"] + e["wrong"]
        for cause, n in e.get("causes", {}).items():
            causes[cause] = causes.get(cause, 0) + n
        for typed, n in e["confusions"].items():
            if typed:
                pairs[(char, typed)] = n
    best = max(pairs.items(), key=lambda item: (item[1], item[0]), default=None)
    pair = (*best[0], best[1]) if best and best[1] >= REVIEW_PAIR_MIN else None
    return {"total": total, "answers": answers, "causes": causes, "pair": pair}


def _times(n: int) -> str:
    return {2: tr("zweimal"), 3: tr("dreimal")}.get(n) or tr("{n}-mal").format(n=n)


def error_review_line(review: dict) -> str:
    """„Woran es lag: Von 9 Fehlern waren 5 Verwechslungen (B für 6 dreimal), 3
    zu langsam, 1 verpasst.“ oder "" bei zu wenigen Fehlern."""
    total = review["total"]
    if total < REVIEW_MIN_ERRORS or total < REVIEW_MIN_SHARE * review["answers"]:
        return ""
    known = sorted(((cause, n) for cause, n in review["causes"].items() if cause in REVIEW_ORDER and n),
                   key=lambda item: (-item[1], REVIEW_ORDER.index(item[0])))
    parts = []
    for cause, n in known[:REVIEW_MAX_CAUSES]:
        if cause == HEARD:
            text = tr("{n} Verwechslung") if n == 1 else tr("{n} Verwechslungen")
            text = text.format(n=n)
            if review["pair"]:
                sent, typed, count = review["pair"]
                text += " (" + tr("{sent} für {typed} {times}").format(
                    sent=display_text(sent), typed=display_text(typed), times=_times(count)) + ")"
        else:
            text = tr(REVIEW_PARTS[cause]).format(n=n)
        parts.append(text)
    rest = total - sum(n for _, n in known[:REVIEW_MAX_CAUSES])
    if rest > 0:
        parts.append(tr("{n} andere").format(n=rest))
    return tr("Woran es lag: Von {total} Fehlern waren {parts}.").format(total=total, parts=", ".join(parts))


REVIEW_PARTS = {
    "late": N_("{n} zu langsam"),
    "missed": N_("{n} verpasst"),
    "replay": N_("{n} erst nach Wiederholung"),
    "swap": N_("{n} vertauscht"),
}


def error_review_tip(review: dict, relaxed_hint: bool = True) -> str:
    """Ein Tipp zur Ursache, die mindestens die Hälfte der Fehler ausmacht;
    "" sonst. `relaxed_hint` False: kein Hinweis auf die entspannte Tagesübung
    (steht schon anderswo)."""
    if not error_review_line(review):
        return ""
    total = review["total"]
    causes = review["causes"]
    if causes.get(HEARD, 0) * 2 >= total:
        return tr("Tipp: Diese Verwechslungen kannst du im Reiter Statistik gezielt üben.")
    if causes.get("late", 0) * 2 >= total and relaxed_hint:
        return tr("Tipp: Die entspannte Tagesübung ({key}) übt ohne Zeitlimit.").format(key=ctrl_key(","))
    if causes.get("missed", 0) * 2 >= total:
        return tr("Tipp: Bei vielen verpassten Zeichen hilft ein etwas langsameres Tempo.")
    return ""


# Darunter ist eine Verwechslung noch kein Muster, sondern wohl Zufall.
MIN_CONFUSION_COUNT = 3


def top_confusions(all_time: dict, limit=10, min_count: int = 1, similar_only: bool = False):
    """Häufigste Verwechslungen über alle Zeichen: [(gesendet, getippt,
    Anzahl, Anteil an den Versuchen des Zeichens)], verpasste Zeichen nicht
    mitgezählt. `limit` None: alle. `min_count`: erst ab so vielen Fällen.
    `similar_only`: nur Paare, die klanglich verwechselbar sind
    (morse.sounds_similar), nicht Tippfehler."""
    pairs = []
    for char, e in all_time.items():
        attempts = e["good"] + e["wrong"]
        for typed, count in e.get("confusions", {}).items():
            if typed and count >= min_count and (not similar_only or sounds_similar(char, typed)):
                pairs.append((char, typed, count, count / attempts if attempts else 0.0))
    pairs.sort(key=lambda p: (-p[2], p[0], p[1]))
    return pairs[:limit]


# Für „zuletzt am schwächsten“: erst ab so vielen Antworten im Fenster.
MIN_RANK_ATTEMPTS = 5


def weakest_chars(recent: dict, all_time: dict, limit: int = 3):
    """[(Zeichen, Fehlerquote)] der schwächsten Zeichen, höchste zuerst: nach
    den Antworten der letzten Tage (`recent`), sonst, wo es dort zu wenige
    gibt, nach der Gesamtstatistik. Nur Zeichen mit Fehlern."""
    rates = {}
    for source in (all_time, recent):  # recent überschreibt, wo genug da ist
        for char, e in source.items():
            total = e["good"] + e["wrong"]
            if total >= MIN_RANK_ATTEMPTS:
                rates[char] = e["wrong"] / total
    ranked = sorted(((char, rate) for char, rate in rates.items() if rate > 0),
                    key=lambda item: (-item[1], item[0]))
    return ranked[:limit]


# --- Verlauf -------------------------------------------------------------------
# Beschriftungen deutsch; übersetzt wird bei der Anzeige (progress_widget).
HISTORY_MODES = {
    "single": N_("Zeichen"),  # wie der Inhalt im Reiter Einzeln
    "group": N_("Gruppen"),
    "word": N_("Wörter"),
    "callsign": N_("Rufzeichen"),
    "rufz": N_("Rufz-Durchgang"),
    "continuous": N_("Am Stück"),
    "qso": N_("QSO mittippen"),
    "qso_quiz": N_("QSO-Abfrage"),
    "qso_head": N_("QSO-Kopfhören"),
    "contest": N_("Contest (aktiv)"),
    "network": N_("Netzwerk"),
}


def log_result(mode: str, correct: int, total: int, wpm: int, **extra) -> None:
    """Speichert ein Ergebnis ohne Zeichenstatistik (QSO-Abfrage, Contest …),
    eins je Durchgang, für den Verlauf und die Diplome. Lässt sich nicht schreiben (Platte voll, keine Schreibrechte), fehlt
    das Ergebnis im Verlauf; die Auswertung auf dem Schirm geht weiter."""
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "correct": correct,
        "total": total,
        "accuracy_pct": round(correct / total * 100, 1) if total else 0.0,
        "wpm": wpm,
        **extra,
    }
    try:
        db.add_result(entry)
    except (db.Error, OSError):
        pass


def _session_effective_wpm(config: dict, summary: dict) -> int:
    """Effektives Tempo eines Durchgangs für den Verlauf, damit Durchgänge
    mit und ohne Farnsworth vergleichbar sind. Bei mitwachsendem Tempo das
    erreichte; ältere Durchgänge kennen nur das erreichte Zeichentempo."""
    if summary.get("wpm_effective_reached"):
        return int(summary["wpm_effective_reached"])
    wpm = int(summary.get("wpm_reached") or config["wpm"])
    fw = config.get("farnsworth_wpm")
    return tempo.effective(wpm, int(fw) if fw else None)


# Kürzere Durchgänge (Proben, gleich abgebrochen) sagen über den Fortschritt
# nichts und fehlen im Reiter Statistik unter Fortschritt; für Diplome und
# Zeichenstatistik zählen sie weiter.
MIN_HISTORY_TOTAL = 5


def load_history(min_total: int = 1):
    """Alle abgeschlossenen Durchgänge, chronologisch: [{"time": datetime,
    "mode", "accuracy_pct", "wpm", "total"}]. Quelle sind die Durchgänge
    (config + summary, ab `min_total` Zeichen) und die Ergebnisse
    (log_result)."""
    history = []
    for session in db.sessions():
        config, summary = session.config, session.summary
        if (not config or not summary or not summary.get("total")
                or summary["total"] < min_total or config.get("self_assessed")
                or config.get("in_history") is False):
            continue
        try:
            history.append({
                "time": datetime.fromisoformat(config["start_time"]),
                "mode": config["mode"],
                "accuracy_pct": float(summary["accuracy_pct"]),
                "wpm": _session_effective_wpm(config, summary),
                "total": int(summary["total"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    for obj in db.results():
        # Übersprungenes Kopfhör-QSO, geleitete Netzwerk-Sitzung: nur für die Diplome.
        if obj.get("skipped") or obj.get("role") == "trainer":
            continue
        try:
            history.append({
                "time": datetime.fromisoformat(obj["time"]),
                "mode": obj["mode"],
                "accuracy_pct": float(obj["accuracy_pct"]),
                "wpm": int(obj["wpm"]),
                "total": int(obj["total"]),
                **({"score": int(obj["score"])} if "score" in obj else {}),
            })
        except (KeyError, TypeError, ValueError):
            continue
    history.sort(key=lambda entry: entry["time"])
    return history
