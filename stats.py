"""Session statistics for the Morsetrainer: per-character results and
effective copying speed, persisted as JSON Lines (one JSON object per
line, flushed immediately so a crash doesn't lose the session — inspired
by the JsonlLogger in WZab/morse_trainer's morse_trainer_cont.py).

A session file looks like:
    {"type": "config", ...}
    {"type": "char", "char": "A", "typed": "A", "correct": true, ...}
    {"type": "group", "sent": "KMU", "typed": "KMU", ...}   (group mode only)
    {"type": "summary", "total": 12, "correct": 10, "per_char": {...}}

stats/all_time.json accumulates per-character totals across all sessions,
including which characters were typed instead ("confusions"; "" = missed).
"""
import json
import statistics
from datetime import datetime
from pathlib import Path

STATS_DIR = Path(__file__).parent / "stats"
ALL_TIME_FILE = STATS_DIR / "all_time.json"

# Latenzen darüber (z. B. weil man kurz abgelenkt war) werden gekappt,
# damit ein einzelner Ausreißer den Schnitt eines Zeichens nicht verzerrt.
LATENCY_CAP_S = 5.0

# So viele Verwechslungen je Zeichen zeigt die Tabelle an.
CONFUSIONS_SHOWN = 3


def format_confusions(confusions: dict) -> str:
    """{"5": 12, "S": 3, "": 2} -> "5 (12), S (3), – (2)"; "–" = verpasst."""
    top = sorted(confusions.items(), key=lambda item: (-item[1], item[0]))[:CONFUSIONS_SHOWN]
    return ", ".join(f"{typed or '–'} ({count})" for typed, count in top)


class SessionStats:
    def __init__(self, mode: str, charset: str, wpm: int, freq: int, group_len=None, farnsworth_wpm=None):
        self.start_time = datetime.now()
        self.mode = mode
        self.charset = charset
        self.wpm = wpm
        self.freq = freq
        self.group_len = group_len
        self.rounds = []  # flat list of per-character results, across the whole session
        self.per_char = {}

        STATS_DIR.mkdir(exist_ok=True)
        self.log_path = STATS_DIR / f"{self.start_time.strftime('%Y-%m-%d_%H%M%S')}-{mode}.jsonl"
        self._fp = open(self.log_path, "a", encoding="utf-8")
        self._write_line({
            "type": "config",
            "mode": mode,
            "charset": charset,
            "wpm": wpm,
            "freq": freq,
            "group_len": group_len,
            "farnsworth_wpm": farnsworth_wpm,
            "start_time": self.start_time.isoformat(timespec="seconds"),
        })

    def _write_line(self, obj: dict) -> None:
        self._fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._fp.flush()

    def record_char(self, char: str, typed: str, correct: bool, reaction_time: float, effective_wpm: float,
                    latency=None) -> None:
        """Record the result for a single character and flush it to disk.

        `latency` is the time from the end of the character's playback to the
        keypress, independent of character length and WPM. Only modes that
        can attribute it to a single character pass it (not the group modes,
        where only the whole group's time is known)."""
        entry = {
            "char": char,
            "typed": typed,
            "correct": correct,
            "reaction_time_s": round(reaction_time, 3),
            "effective_wpm": round(effective_wpm, 1),
        }
        if latency is not None:
            entry["latency_s"] = round(latency, 3)
        self.rounds.append(entry)
        self._write_line({"type": "char", **entry})

        agg = self.per_char.setdefault(
            char, {"good": 0, "wrong": 0, "reaction_times": [], "effective_wpms": [], "correct_effective_wpms": [],
                   "latencies": [], "confusions": {}}
        )
        if correct:
            agg["good"] += 1
            agg["correct_effective_wpms"].append(effective_wpm)
            if latency is not None:
                agg["latencies"].append(min(max(latency, 0.0), LATENCY_CAP_S))
        else:
            agg["wrong"] += 1
            agg["confusions"][typed] = agg["confusions"].get(typed, 0) + 1
        agg["reaction_times"].append(reaction_time)
        agg["effective_wpms"].append(effective_wpm)

    def record_group(self, sent: str, typed: str) -> None:
        """Log a group-mode commit at the group level (in addition to the
        per-character record_char calls the caller makes for it)."""
        self._write_line({"type": "group", "sent": sent, "typed": typed})

    def char_rows(self):
        """Per-character rows (char, good, wrong, total, avg_reaction_s, avg_wpm,
        confusions text), sorted by error count descending, for display."""
        rows = []
        for char, e in self.per_char.items():
            total = e["good"] + e["wrong"]
            avg_rt = statistics.mean(e["reaction_times"]) if e["reaction_times"] else 0.0
            avg_wpm = statistics.mean(e["effective_wpms"]) if e["effective_wpms"] else 0.0
            rows.append((char, e["good"], e["wrong"], total, avg_rt, avg_wpm, format_confusions(e["confusions"])))
        rows.sort(key=lambda r: (-r[2], r[0]))
        return rows

    def summary(self):
        total = len(self.rounds)
        correct = sum(1 for r in self.rounds if r["correct"])
        accuracy = (correct / total * 100) if total else 0.0
        wpms = [r["effective_wpm"] for r in self.rounds if r["correct"]]
        avg_wpm = statistics.mean(wpms) if wpms else 0.0
        return {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(accuracy, 1),
            "avg_effective_wpm": round(avg_wpm, 1),
        }

    def _per_char_summary(self):
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

    def finalize(self):
        """Write the closing summary line, merge into all_time.json, and
        close the log file. Returns the log file path, or None if nothing
        was ever recorded (in which case the empty file is removed)."""
        if not self.rounds:
            self._fp.close()
            self.log_path.unlink(missing_ok=True)
            return None
        self._write_line({"type": "summary", **self.summary(), "per_char": self._per_char_summary()})
        self._fp.close()
        _merge_all_time(self)
        return self.log_path


def _merge_all_time(session: "SessionStats") -> None:
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
        # Ältere all_time.json-Einträge kennen die Latenz-Felder noch nicht.
        x["total_latency_s"] = x.get("total_latency_s", 0.0) + sum(e["latencies"])
        x["latency_count"] = x.get("latency_count", 0) + len(e["latencies"])
        confusions = x.setdefault("confusions", {})
        for typed, count in e["confusions"].items():
            confusions[typed] = confusions.get(typed, 0) + count
    STATS_DIR.mkdir(exist_ok=True)
    with open(ALL_TIME_FILE, "wt", encoding="utf-8") as fp:
        json.dump(all_time, fp, indent=2, ensure_ascii=False)


def load_all_time() -> dict:
    """Cumulative per-character totals across all past sessions."""
    if ALL_TIME_FILE.exists():
        with open(ALL_TIME_FILE, "rt", encoding="utf-8") as fp:
            return json.load(fp)
    return {}


def reset_all_time() -> None:
    """Wipe the cumulative statistics. Individual session log files are
    untouched — only the running totals in all_time.json are cleared."""
    if ALL_TIME_FILE.exists():
        ALL_TIME_FILE.unlink()


def all_time_char_rows(all_time: dict):
    """Same shape as SessionStats.char_rows(), computed from the persisted
    cumulative totals instead of an in-memory session."""
    rows = []
    for char, e in all_time.items():
        total = e["good"] + e["wrong"]
        avg_rt = e["total_reaction_time_s"] / total if total else 0.0
        avg_wpm = e["total_effective_wpm"] / total if total else 0.0
        rows.append((char, e["good"], e["wrong"], total, avg_rt, avg_wpm, format_confusions(e.get("confusions", {}))))
    rows.sort(key=lambda r: (-r[2], r[0]))
    return rows


def all_time_summary(all_time: dict):
    """Same shape as SessionStats.summary(), computed from the persisted
    cumulative totals instead of an in-memory session."""
    total = sum(e["good"] + e["wrong"] for e in all_time.values())
    correct = sum(e["good"] for e in all_time.values())
    accuracy = (correct / total * 100) if total else 0.0
    correct_wpm_total = sum(e.get("correct_effective_wpm_total", 0.0) for e in all_time.values())
    avg_wpm = (correct_wpm_total / correct) if correct else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(accuracy, 1),
        "avg_effective_wpm": round(avg_wpm, 1),
    }

def top_confusions(all_time: dict, limit: int = 10):
    """Häufigste Verwechslungen über alle Zeichen: [(gesendet, getippt,
    Anzahl, Anteil an den Versuchen des Zeichens)], verpasste Zeichen nicht
    mitgezählt."""
    pairs = []
    for char, e in all_time.items():
        attempts = e["good"] + e["wrong"]
        for typed, count in e.get("confusions", {}).items():
            if typed:
                pairs.append((char, typed, count, count / attempts if attempts else 0.0))
    pairs.sort(key=lambda p: (-p[2], p[0], p[1]))
    return pairs[:limit]


# --- Verlauf -------------------------------------------------------------------
# Ergebnisse, die keine Zeichenstatistik haben (QSO-Abfrage, Contest-Runs),
# eine Zeile pro Durchgang.
RESULTS_FILE = STATS_DIR / "results.jsonl"

HISTORY_MODES = {
    "single": "Einzelzeichen",
    "group": "Gruppen",
    "callsign": "Rufzeichen",
    "continuous": "Kontinuierlich",
    "qso": "QSO mittippen",
    "qso_quiz": "QSO-Abfrage",
    "contest": "Contest (aktiv)",
}


def log_result(mode: str, correct: int, total: int, wpm: int, **extra) -> None:
    """Hängt ein Ergebnis an stats/results.jsonl an (für den Verlauf)."""
    STATS_DIR.mkdir(exist_ok=True)
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "correct": correct,
        "total": total,
        "accuracy_pct": round(correct / total * 100, 1) if total else 0.0,
        "wpm": wpm,
        **extra,
    }
    with open(RESULTS_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path):
    try:
        with open(path, "rt", encoding="utf-8") as fp:
            for line in fp:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue  # z. B. halb geschriebene Zeile nach einem Absturz
    except OSError:
        return


def load_history():
    """Alle abgeschlossenen Durchgänge, chronologisch: [{"time": datetime,
    "mode", "accuracy_pct", "wpm", "total"}]. Quelle sind die Sitzungsdateien
    (Zeile "config" + "summary") und results.jsonl."""
    history = []
    for path in STATS_DIR.glob("20*.jsonl"):
        config = summary = None
        for obj in _read_jsonl(path):
            if obj.get("type") == "config":
                config = obj
            elif obj.get("type") == "summary":
                summary = obj
        if not config or not summary or not summary.get("total"):
            continue
        try:
            history.append({
                "time": datetime.fromisoformat(config["start_time"]),
                "mode": config["mode"],
                "accuracy_pct": float(summary["accuracy_pct"]),
                "wpm": int(config["wpm"]),
                "total": int(summary["total"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    for obj in _read_jsonl(RESULTS_FILE):
        try:
            history.append({
                "time": datetime.fromisoformat(obj["time"]),
                "mode": obj["mode"],
                "accuracy_pct": float(obj["accuracy_pct"]),
                "wpm": int(obj["wpm"]),
                "total": int(obj["total"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    history.sort(key=lambda entry: entry["time"])
    return history
