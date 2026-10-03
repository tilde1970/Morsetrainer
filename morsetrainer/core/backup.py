"""Alle Einstellungen und Daten in eine ZIP-Datei sichern und von dort
wieder einlesen, etwa für den Umzug auf einen neuen Rechner.

Gesichert wird, was in DATA_DIR dem Benutzer gehört: stats/ (Sitzungen,
Gesamtstatistik, Tagesübung, Diplome, Übungszeit, Wiederholungen),
window_state.json (alle Einstellungen), woerter.txt und callsigns.scp.
Nicht dabei sind die Stimme für die Sprachausgabe (groß, lässt sich neu
laden), das Fehlerprotokoll sowie halb geschriebene (*.tmp) und
beiseitegelegte (*.defekt-*) Dateien.

Beim Einlesen wird stats/ vollständig ersetzt; die übrigen Dateien nur,
wenn die Sicherung sie enthält. Vorher landet der bisherige Stand als
"vor-import-<Zeitstempel>.zip" in DATA_DIR, damit sich ein versehentlicher
Import rückgängig machen lässt."""
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from morsetrainer import DATA_DIR

MARKER = "morsetrainer-sicherung.json"
FORMAT = 1
TOP_FILES = ("window_state.json", "woerter.txt", "callsigns.scp")
STATS = "stats"


class BackupError(Exception):
    """Die Datei ist keine (lesbare) Sicherung des Morsetrainers."""


def _wanted(path: Path) -> bool:
    return path.is_file() and not path.name.endswith(".tmp") and ".defekt-" not in path.name


def _members(data_dir: Path):
    """(Datei, Name im Archiv) aller zu sichernden Dateien."""
    for name in TOP_FILES:
        path = data_dir / name
        if _wanted(path):
            yield path, name
    stats_dir = data_dir / STATS
    if stats_dir.is_dir():
        for path in sorted(stats_dir.rglob("*")):
            if _wanted(path):
                yield path, path.relative_to(data_dir).as_posix()


def export_data(target: Path, version: str, data_dir: Path = DATA_DIR) -> int:
    """Schreibt die Sicherung nach `target` (erst in eine Nachbardatei, die
    dann die alte ersetzt) und gibt die Zahl der Dateien zurück. Wirft
    OSError, wenn das Schreiben scheitert."""
    target = Path(target)
    tmp = target.with_name(target.name + ".tmp")
    count = 0
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MARKER, json.dumps({
                "format": FORMAT, "version": version,
                "created": datetime.now().isoformat(timespec="seconds"),
            }, indent=2))
            for path, name in _members(data_dir):
                archive.write(path, name)
                count += 1
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return count


def _safe_name(name: str) -> bool:
    """Nur bekannte Dateien und stats/…, nichts außerhalb (absolute Pfade, ..)."""
    if name in TOP_FILES or name == MARKER:
        return True
    parts = PurePosixPath(name).parts
    return (len(parts) >= 2 and parts[0] == STATS and ".." not in parts
            and "\\" not in name and ":" not in name)


def read_info(source: Path) -> dict:
    """Kopfdaten der Sicherung (format, version, created); wirft
    BackupError, wenn `source` keine Sicherung ist."""
    try:
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if MARKER not in names:
                raise BackupError("marker")
            info = json.loads(archive.read(MARKER).decode("utf-8"))
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError(str(exc)) from exc
    if not isinstance(info, dict) or not isinstance(info.get("format"), int) or info["format"] > FORMAT:
        raise BackupError("format")
    if not all(_safe_name(n) for n in names if not n.endswith("/")):
        raise BackupError("names")
    return info


def import_data(source: Path, version: str, data_dir: Path = DATA_DIR) -> Path:
    """Ersetzt die Daten in `data_dir` durch die Sicherung `source` und gibt
    den Pfad der vorher angelegten Sicherung des bisherigen Stands zurück.
    Wirft BackupError (keine Sicherung) oder OSError; in beiden Fällen
    bleiben die bisherigen Daten erhalten, sofern das Ersetzen nicht selbst
    mittendrin scheitert (dann hilft die Sicherung des bisherigen Stands)."""
    read_info(source)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    previous = data_dir / f"vor-import-{stamp}.zip"
    export_data(previous, version, data_dir)

    staging = data_dir / f".import-{stamp}"
    old_stats = data_dir / f".stats-alt-{stamp}"
    try:
        with zipfile.ZipFile(source) as archive:
            for name in archive.namelist():
                if name == MARKER or name.endswith("/"):
                    continue
                dest = staging.joinpath(*PurePosixPath(name).parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
        (staging / STATS).mkdir(parents=True, exist_ok=True)

        stats_dir = data_dir / STATS
        if stats_dir.exists():
            os.replace(stats_dir, old_stats)
        try:
            os.replace(staging / STATS, stats_dir)
        except OSError:
            if old_stats.exists():
                os.replace(old_stats, stats_dir)
            raise
        for name in TOP_FILES:
            if (staging / name).is_file():
                os.replace(staging / name, data_dir / name)
        shutil.rmtree(old_stats, ignore_errors=True)
    except zipfile.BadZipFile as exc:
        raise BackupError(str(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return previous
