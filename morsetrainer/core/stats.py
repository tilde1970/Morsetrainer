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
import statistics
from datetime import datetime, timedelta

from morsetrainer import DATA_DIR
from morsetrainer.core import db
from morsetrainer.core import tempo
from morsetrainer.core.koch import SLOW_CHAR_WPM
from morsetrainer.core.morse import display_text
from morsetrainer.i18n import N_

STATS_DIR = DATA_DIR / "stats"

# Latenzen darüber (z. B. weil man kurz abgelenkt war) werden gekappt,
# damit ein einzelner Ausreißer den Schnitt eines Zeichens nicht verzerrt.
LATENCY_CAP_S = 5.0

# So viele Verwechslungen je Zeichen zeigt die Tabelle an.
CONFUSIONS_SHOWN = 3


def format_confusions(confusions: dict) -> str:
    """{"5": 12, "S": 3, "": 2} -> "5 (12), S (3)". Verpasste Zeichen ("")
    sind keine Verwechslung (das Zeichen wurde gar nicht erkannt); sie
    zählen nur als falsch."""
    top = sorted(((typed, count) for typed, count in confusions.items() if typed),
                 key=lambda item: (-item[1], item[0]))[:CONFUSIONS_SHOWN]
    return ", ".join(f"{display_text(typed)} ({count})" for typed, count in top)


class SessionStats:
    """Zeichnet einen Durchgang auf: jedes Zeichen sofort in die Datenbank, am
    Ende die Zusammenfassung samt Übernahme in Gesamtstatistik und Lernkartei
    (finalize)."""
    def __init__(self, mode: str, charset: str, wpm: int, freq: int, group_len=None, farnsworth_wpm=None,
                 self_assessed=False, in_history=True, review_promote=False, char_stats=True, config_extra=None):
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
        self.char_stats = char_stats
        self.start_time = datetime.now()
        self.self_assessed = self_assessed
        self.mode = mode
        self.charset = charset
        self.wpm = wpm
        self.freq = freq
        self.group_len = group_len
        self.rounds = []  # Ergebnisse je Zeichen, flach über den ganzen Durchgang
        self.per_char = {}

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
                    latency=None, assumed=False) -> None:
        """Ergebnis für ein einzelnes Zeichen festhalten und sofort speichern.

        `latency` ist die Zeit vom Ende des Tons (des letzten Punkts oder
        Strichs) bis zum Tastendruck, unabhängig von Zeichenlänge und Tempo;
        beim fortlaufenden Mitschreiben ab der vorigen Taste, wenn die später
        kam. Nur wo sie sich einem einzelnen Zeichen zuordnen lässt, sonst
        None (siehe core/latency). `reaction_time` ist die Zeit ab Tonbeginn,
        `effective_wpm` das daraus gerechnete Tempo (morse.effective_wpm).
        `assumed`: nicht gemessen, sondern für eine richtige, aber unsichere
        Antwort gesetzt (2 × die übliche Latenz); zählt für die Gewichtung
        dieses Zeichens, nicht für die übliche Latenz."""
        entry = {
            "char": char,
            "typed": typed,
            "correct": correct,
            "reaction_time_s": round(reaction_time, 3),
            "effective_wpm": round(effective_wpm, 1),
        }
        if latency is not None:
            entry["latency_s"] = round(latency, 3)
            if assumed:
                entry["latency_assumed"] = True
        self.rounds.append(entry)
        self._write_line({"type": "char", **entry})

        agg = self.per_char.setdefault(
            char, {"good": 0, "wrong": 0, "reaction_times": [], "effective_wpms": [], "correct_effective_wpms": [],
                   "correct_reaction_times": [], "latencies": [], "assumed_latencies": [], "confusions": {}}
        )
        if correct:
            agg["good"] += 1
            agg["correct_effective_wpms"].append(effective_wpm)
            agg["correct_reaction_times"].append(reaction_time)
            if latency is not None:
                capped = min(max(latency, 0.0), LATENCY_CAP_S)
                agg["latencies"].append(capped)
                if assumed:
                    agg["assumed_latencies"].append(capped)
        else:
            agg["wrong"] += 1
            agg["confusions"][typed] = agg["confusions"].get(typed, 0) + 1
        agg["reaction_times"].append(reaction_time)
        agg["effective_wpms"].append(effective_wpm)

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
            rows.append((char, e["good"], e["wrong"], total, reaction, avg_wpm, format_confusions(e["confusions"])))
        rows.sort(key=lambda r: (-r[2], r[0]))
        return rows

    def summary(self):
        """Zusammenfassung des Durchgangs: Anzahl, richtige, Trefferquote in %,
        mittleres effektives Tempo der richtigen Zeichen und Zeichen pro Minute."""
        total = len(self.rounds)
        correct = sum(1 for r in self.rounds if r["correct"])
        accuracy = (correct / total * 100) if total else 0.0
        wpms = [r["effective_wpm"] for r in self.rounds if r["correct"]]
        avg_wpm = statistics.mean(wpms) if wpms else 0.0
        times = [r["reaction_time_s"] for r in self.rounds if r["correct"]]
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
        for char, e in self.per_char.items():
            out[char] = {
                "good": e["good"],
                "wrong": e["wrong"],
                "avg_reaction_time_s": round(statistics.mean(e["reaction_times"]), 3)
                if e["reaction_times"] else 0.0,
                "avg_effective_wpm": round(statistics.mean(e["effective_wpms"]), 1)
                if e["effective_wpms"] else 0.0,
                "confusions": e["confusions"],
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
        try:
            with db.transaction():
                if self.session_id is not None and self.log_error is None:
                    db.finish_session(self.session_id, summary)
                if not self.self_assessed and self.char_stats:
                    _merge_all_time(self)
                    from morsetrainer.core import review  # review importiert stats
                    review.update(self.per_char, promote=self.review_promote and review.can_promote(self.charset),
                                  events=self.review_events, fast=(self.wpm or 0) >= SLOW_CHAR_WPM)
        except (db.Error, OSError) as exc:
            self.log_error = self.log_error or str(exc)
        return self.session_id if self.log_error is None else None


def _merge_all_time(session: "SessionStats") -> None:
    """Addiert die Ergebnisse je Zeichen aus `session` zur Gesamtstatistik und
    speichert sie (aufgerufen innerhalb der Transaktion von finalize)."""
    all_time = load_all_time()
    for char, e in session.per_char.items():
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
    db.save_state(ALL_TIME_KEY, all_time)


ALL_TIME_KEY = "all_time"
RESET_KEY = "reset"


def load_all_time() -> dict:
    """Summen je Zeichen über alle bisherigen Durchgänge. Ein beschädigter
    Eintrag wird beiseitegelegt (siehe db.load_state), statt abzustürzen."""
    return db.load_state(ALL_TIME_KEY, {})


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


def recent_char_data(days: int = RECENT_DAYS, now=None) -> dict:
    """Zeichenstatistik wie die Gesamtstatistik ({Zeichen: {"good", "wrong",
    "confusions"}}), aber nur aus den Durchgängen der letzten `days`
    Tage und nach dem letzten Zurücksetzen. Längst behobene Verwechslungen
    fallen so heraus. Selbst bewertete Sitzungen und Klartext zählen nicht."""
    now = now or datetime.now()
    cutoff = now - timedelta(days=days)
    reset = db.load_state(RESET_KEY, {}).get("time")
    try:
        cutoff = max(cutoff, datetime.fromisoformat(reset)) if reset else cutoff
    except (TypeError, ValueError):
        pass
    data = {}
    for session in db.sessions(since=cutoff.replace(microsecond=0), events=True):
        if session.config.get("self_assessed") or session.config.get("char_stats") is False:
            continue
        for obj in session.events:
            if obj.get("type") != "char" or "char" not in obj:
                continue
            e = data.setdefault(obj["char"], {"good": 0, "wrong": 0, "confusions": {}})
            if obj.get("correct"):
                e["good"] += 1
            else:
                e["wrong"] += 1
                typed = obj.get("typed", "")
                e["confusions"][typed] = e["confusions"].get(typed, 0) + 1
    return data


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
        # Nur richtige Antworten (wie die Zeile darüber, all_time_summary).
        avg_wpm = e.get("correct_effective_wpm_total", 0.0) / e["good"] if e["good"] else None
        rows.append((char, e["good"], e["wrong"], total, avg_rt, avg_wpm, format_confusions(e.get("confusions", {}))))
    rows.sort(key=lambda r: (-r[2], r[0]))
    return rows


def all_time_summary(all_time: dict):
    """Zusammenfassung wie SessionStats.summary(), aber aus den gespeicherten
    Gesamtsummen statt aus einem laufenden Durchgang."""
    total = sum(e["good"] + e["wrong"] for e in all_time.values())
    correct = sum(e["good"] for e in all_time.values())
    accuracy = (correct / total * 100) if total else 0.0
    correct_wpm_total = sum(e.get("correct_effective_wpm_total", 0.0) for e in all_time.values())
    avg_wpm = (correct_wpm_total / correct) if correct else 0.0
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

def top_confusions(all_time: dict, limit=10):
    """Häufigste Verwechslungen über alle Zeichen: [(gesendet, getippt,
    Anzahl, Anteil an den Versuchen des Zeichens)], verpasste Zeichen nicht
    mitgezählt. `limit` None: alle."""
    pairs = []
    for char, e in all_time.items():
        attempts = e["good"] + e["wrong"]
        for typed, count in e.get("confusions", {}).items():
            if typed:
                pairs.append((char, typed, count, count / attempts if attempts else 0.0))
    pairs.sort(key=lambda p: (-p[2], p[0], p[1]))
    return pairs[:limit]


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


def load_history():
    """Alle abgeschlossenen Durchgänge, chronologisch: [{"time": datetime,
    "mode", "accuracy_pct", "wpm", "total"}]. Quelle sind die Durchgänge
    (config + summary) und die Ergebnisse (log_result)."""
    history = []
    for session in db.sessions():
        config, summary = session.config, session.summary
        if (not config or not summary or not summary.get("total") or config.get("self_assessed")
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
