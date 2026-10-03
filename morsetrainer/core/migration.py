"""Übernahme der alten JSON-Dateien in die Datenbank (core/db.py).

Bis Version 2.27 lagen die Übungsdaten als einzelne Dateien in stats/:
eine "<Startzeit>-<Modus>.jsonl" je Durchgang, results.jsonl und die
Zustände all_time.json, daily.json, awards.json, review.json,
practice.json und reset.json. run() liest sie in einer einzigen
Transaktion ein; erst danach werden sie nach stats/alt-json/ verschoben.
Gelöscht wird nichts.

Scheitert das Einlesen, bleibt die Datenbank, wie sie war, und die
Dateien bleiben liegen: Beim nächsten Start gibt es einen neuen Versuch.
Scheitert erst das Verschieben, merkt sich die Datenbank die übernommenen
Dateien und verschiebt sie beim nächsten Mal nur noch, statt sie doppelt
einzulesen. So greift die Übernahme auch nach dem Einlesen einer älteren
Sicherung, die noch die Dateien enthält."""
import json
import os
from datetime import datetime
from pathlib import Path

from morsetrainer.core import db, storage

ARCHIVE_DIR_NAME = "alt-json"
RESULTS_FILE_NAME = "results.jsonl"
# Datei -> Schlüssel in der Tabelle state
STATE_FILES = {
    "all_time.json": "all_time",
    "daily.json": "daily",
    "awards.json": "awards",
    "review.json": "review",
    "practice.json": "practice",
    "reset.json": "reset",
}
# Unter diesem Präfix merkt sich die Tabelle meta die übernommenen Dateien.
META_PREFIX = "legacy:"


def legacy_files(stats_dir: Path) -> list:
    """Die alten Dateien in `stats_dir`, Durchgänge nach Startzeit."""
    if not stats_dir.is_dir():
        return []
    files = sorted(p for p in stats_dir.glob("20*.jsonl") if p.is_file())
    for name in (RESULTS_FILE_NAME, *STATE_FILES):
        path = stats_dir / name
        if path.is_file():
            files.append(path)
    return files


def _lines(path: Path):
    """Die lesbaren Zeilen einer JSON-Lines-Datei; halb geschriebene (nach
    einem Absturz) oder beschädigte fallen weg wie beim bisherigen Lesen."""
    with open(path, "rt", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def _start_from_name(path: Path):
    """("2026-10-03T10:48:55", "single") aus "2026-10-03_104855-single.jsonl"."""
    stem = path.stem
    try:
        start = datetime.strptime(stem[:17], "%Y-%m-%d_%H%M%S")
    except ValueError:
        return None, None
    mode = stem[18:] if stem[17:18] == "-" else ""
    return start.isoformat(timespec="seconds"), mode


def _import_session(path: Path) -> None:
    config = summary = None
    events = []
    for obj in _lines(path):
        kind = obj.get("type")
        if kind == "config":
            config = config or obj
        elif kind == "summary":
            summary = obj
        else:
            events.append(obj)
    start, mode = _start_from_name(path)
    if config is None:
        # Erste Zeile verloren: Ohne Startzeit aus dem Namen ist nichts zuzuordnen.
        if start is None:
            return
        config = {"type": "config", "mode": mode, "start_time": start}
    if not isinstance(config.get("start_time"), str):
        if start is None:
            return
        config["start_time"] = start
    if not isinstance(config.get("mode"), str):
        config["mode"] = mode or ""
    session_id = db.start_session(config)
    for entry in events:
        db.add_event(session_id, entry)
    if summary is not None:
        db.finish_session(session_id, summary)


def _import_results(path: Path) -> None:
    for obj in _lines(path):
        # Ohne Zeit oder Modus haben die Auswertungen solche Zeilen schon immer übergangen.
        if isinstance(obj.get("time"), str) and isinstance(obj.get("mode"), str):
            db.add_result(obj)


def _import(path: Path) -> None:
    if path.name in STATE_FILES:
        # Eine kaputte Datei legt load_json beiseite; sie wird nicht übernommen.
        data = storage.load_json(path, {})
        if path.exists():
            db.save_state(STATE_FILES[path.name], data)
    elif path.name == RESULTS_FILE_NAME:
        _import_results(path)
    else:
        _import_session(path)


def run(stats_dir: Path = None) -> int:
    """Übernimmt die alten Dateien aus `stats_dir` (Standard: der Ordner
    der Datenbank) und gibt ihre Zahl zurück; 0, wenn es keine gibt. Wirft
    db.Error oder OSError, wenn das Einlesen scheitert; die Datenbank
    bleibt dann unverändert und die Dateien liegen weiter in stats/."""
    stats_dir = Path(stats_dir) if stats_dir is not None else db.path().parent
    files = legacy_files(stats_dir)
    if not files:
        return 0
    new = [p for p in files if db.get_meta(META_PREFIX + p.name) is None]
    if new:
        stamp = datetime.now().isoformat(timespec="seconds")
        with db.transaction():
            for path in new:
                _import(path)
                db.set_meta(META_PREFIX + path.name, stamp)
    _archive(stats_dir, files)
    return len(new)


def _archive(stats_dir: Path, files: list) -> None:
    """Übernommene Dateien nach stats/alt-json/ verschieben. Was sich nicht
    verschieben lässt, bleibt liegen und wird beim nächsten Start erneut
    versucht (aber nicht noch einmal eingelesen)."""
    archive = stats_dir / ARCHIVE_DIR_NAME
    try:
        archive.mkdir(exist_ok=True)
    except OSError:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for path in files:
        if not path.exists():  # eine kaputte Zustandsdatei liegt schon als .defekt-* daneben
            continue
        target = archive / path.name
        if target.exists():  # nichts überschreiben, was schon im Archiv liegt
            target = archive / f"{path.name}.{stamp}"
        try:
            os.replace(path, target)
        except OSError:
            pass
