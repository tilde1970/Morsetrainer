"""Alle Einstellungen und Daten in eine ZIP-Datei sichern und von dort
wieder einlesen, etwa für den Umzug auf einen neuen Rechner.

Gesichert wird, was in DATA_DIR dem Benutzer gehört: stats/ (Sitzungen,
Gesamtstatistik, Tagesübung, Diplome, Übungszeit, Wiederholungen),
window_state.json (alle Einstellungen), woerter.txt und callsigns.scp.
Nicht dabei sind die Stimme für die Sprachausgabe (groß, lässt sich neu
laden), das Fehlerprotokoll sowie halb geschriebene (*.tmp) und
beiseitegelegte (*.defekt-*) Dateien.

Die Datenbank (core/db.py) wird nicht als Datei kopiert, sondern über die
Sicherungsfunktion von SQLite: Das ergibt einen stimmigen Stand, auch wenn
gerade geschrieben wird oder Änderungen noch im Journal (-wal) stehen.

Beim Einlesen wird stats/ vollständig ersetzt; die übrigen Dateien nur,
wenn die Sicherung sie enthält. Vorher landet der bisherige Stand als
"vor-import-<Zeitstempel>.zip" in DATA_DIR, damit sich ein versehentlicher
Import rückgängig machen lässt. Vor dem Ersetzen wird die mitgelieferte
Datenbank geprüft und die eigene Verbindung geschlossen.

Zusätzlich legt das Programm beim Beenden höchstens alle 7 Tage eine
Sicherung in "auto-sicherung/" an (die letzten 4 bleiben), siehe auto_backup."""
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
import zlib
from datetime import date, datetime
from pathlib import Path, PurePosixPath

from morsetrainer import DATA_DIR
from morsetrainer.core import db

AUTO_DIR = "auto-sicherung"
AUTO_INTERVAL_DAYS = 7
AUTO_KEEP = 4
# Merkzettel im Datenordner: die letzte automatische Sicherung ist gescheitert
# (beim Beenden lässt sich das nicht mehr melden; der nächste Start tut es).
AUTO_FAILED = "auto-sicherung-fehler.txt"

MARKER = "morsetrainer-sicherung.json"
FORMAT = 1
TOP_FILES = ("window_state.json", "woerter.txt", "callsigns.scp")
STATS = "stats"


class BackupError(Exception):
    """Die Datei ist keine (lesbare) Sicherung des Morsetrainers."""


# Gehören zur Datenbankdatei und stecken im Schnappschuss mit drin.
DB_COMPANIONS = ("-wal", "-shm", "-journal")


# Hilfsdateien: "….tmp<PID>" (halb geschriebene Sicherung), "….halt<PID>" (festgehaltenes Journal).
TEMP_NAME = re.compile(r"\.(tmp|halt)\d*$")


def _wanted(path: Path) -> bool:
    return (path.is_file() and not TEMP_NAME.search(path.name) and ".defekt-" not in path.name
            and ".vor-v" not in path.name and not path.name.endswith(DB_COMPANIONS))


def _members(data_dir: Path):
    """(Datei, Name im Archiv) aller zu sichernden Dateien außer der
    Datenbank (die schreibt export_data als Schnappschuss)."""
    for name in TOP_FILES:
        path = data_dir / name
        if _wanted(path):
            yield path, name
    stats_dir = data_dir / STATS
    database = stats_dir / db.DB_FILE_NAME
    if stats_dir.is_dir():
        for path in sorted(stats_dir.rglob("*")):
            if _wanted(path) and path != database:
                yield path, path.relative_to(data_dir).as_posix()


def _snapshot(database: Path, target: Path) -> None:
    """Stimmiger Stand der Datenbank nach `target`; wirft OSError, wenn sie
    sich nicht lesen lässt (gesperrt, beschädigt)."""
    try:
        source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=db.BUSY_TIMEOUT_MS / 1000)
        try:
            dest = sqlite3.connect(target)
            try:
                source.backup(dest)
            finally:
                dest.close()
        finally:
            source.close()
    except sqlite3.Error as exc:
        raise OSError(f"{database.name}: {exc}") from exc


def export_data(target: Path, version: str, data_dir: Path = DATA_DIR) -> int:
    """Schreibt die Sicherung nach `target` (erst in eine Nachbardatei, die
    dann die alte ersetzt) und gibt die Zahl der Dateien zurück. Wirft
    OSError, wenn das Schreiben scheitert."""
    target = Path(target)
    tmp = target.with_name(f"{target.name}.tmp{os.getpid()}")
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
            database = data_dir / STATS / db.DB_FILE_NAME
            if database.is_file():
                # Der Schnappschuss liegt neben den Daten, nicht im oft kleinen /tmp.
                with tempfile.TemporaryDirectory(dir=data_dir) as folder:
                    copy = Path(folder) / db.DB_FILE_NAME
                    _snapshot(database, copy)
                    archive.write(copy, f"{STATS}/{db.DB_FILE_NAME}")
                count += 1
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return count


def _auto_files(folder: Path, today: date) -> list:
    """Die automatischen Sicherungen im Ordner, älteste zuerst: nur Namen
    "auto-<Datum>.zip" mit lesbarem Datum, nicht in der Zukunft (eine falsch
    gestellte Uhr soll die Sicherung weder bremsen noch die Auswahl der zu
    löschenden verschieben)."""
    found = []
    for path in folder.glob("auto-*.zip") if folder.is_dir() else ():
        if not re.fullmatch(r"auto-\d{4}-\d{2}-\d{2}\.zip", path.name):
            continue
        try:
            day = date.fromisoformat(path.name[5:15])
        except ValueError:
            continue
        if day <= today:
            found.append((day, path))
    return [path for _day, path in sorted(found)]


def auto_backup_due(data_dir: Path = DATA_DIR, today: date = None) -> bool:
    """Ist eine automatische Sicherung fällig: Datenbank da, keine beiseitegelegt
    (die neue wäre leer und verdrängte die guten) und die letzte mindestens
    AUTO_INTERVAL_DAYS her?"""
    today = today or date.today()
    if db.aside_file is not None or not (data_dir / STATS / db.DB_FILE_NAME).is_file():
        return False
    existing = _auto_files(data_dir / AUTO_DIR, today)
    return not existing or (today - date.fromisoformat(existing[-1].name[5:15])).days >= AUTO_INTERVAL_DAYS


def auto_backup(version: str, data_dir: Path = DATA_DIR, today: date = None):
    """Legt "<data_dir>/auto-sicherung/auto-<Datum>.zip" an, wenn eine fällig ist
    (auto_backup_due); die ältesten über AUTO_KEEP hinaus werden erst gelöscht,
    wenn die neue sich als Sicherung lesen lässt. Gibt den Pfad zurück, sonst
    None. Wirft bei einem Fehler (nach dem Merkzettel AUTO_FAILED) eine
    Ausnahme; hat ein anderes Fenster die Sicherung inzwischen angelegt, ist
    das kein Fehler. Der Ordner liegt außerhalb von stats/ und kommt nicht in
    die manuelle Sicherung."""
    today = today or date.today()
    if not auto_backup_due(data_dir, today):
        return None
    folder = data_dir / AUTO_DIR
    target = folder / f"auto-{today.isoformat()}.zip"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        _remove_old_temp_files(folder)
        export_data(target, version, data_dir)
        read_info(target)  # nur eine lesbare Sicherung darf ältere verdrängen
    except Exception as exc:
        if not isinstance(exc, BackupError):
            try:
                read_info(target)
                return None  # ein anderes Fenster war fertig
            except (BackupError, OSError):
                pass
        target.unlink(missing_ok=True)
        reason = (exc.strerror if isinstance(exc, OSError) and exc.strerror else None) or str(exc) or type(exc).__name__
        try:
            (data_dir / AUTO_FAILED).write_text(reason, encoding="utf-8")
        except OSError:
            pass
        raise
    (data_dir / AUTO_FAILED).unlink(missing_ok=True)
    for old in _auto_files(folder, today)[:-AUTO_KEEP]:
        old.unlink(missing_ok=True)
    return target


def _remove_old_temp_files(folder: Path) -> None:
    """Reste halb geschriebener Sicherungen (hartes Beenden), nicht die eines
    gerade laufenden anderen Fensters (die sind jung)."""
    cutoff = datetime.now().timestamp() - 24 * 3600
    for path in folder.glob("*.zip.tmp*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def auto_backup_failure(data_dir: Path = DATA_DIR):
    """Der Grund, warum die letzte automatische Sicherung scheiterte, oder
    None, wenn sie nicht gescheitert ist. Der Merkzettel verschwindet mit der
    nächsten gelungenen Sicherung."""
    try:
        return (data_dir / AUTO_FAILED).read_text(encoding="utf-8").strip() or "?"
    except OSError:
        return None


# Was zipfile bei kaputten oder ungewöhnlichen Archiven wirft: verschlüsselt
# (RuntimeError), unbekanntes Kompressionsverfahren (NotImplementedError),
# abgeschnitten (EOFError), beschädigte Daten (zlib.error).
ZIP_ERRORS = (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error)


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
            # Alle Dateien einmal lesen (Prüfsumme): Was sich nicht entpacken
            # lässt, fällt hier auf und nicht erst mitten im Ersetzen.
            if archive.testzip() is not None:
                raise BackupError("crc")
    except (OSError, *ZIP_ERRORS, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError(str(exc)) from exc
    if not isinstance(info, dict) or not isinstance(info.get("format"), int) or info["format"] > FORMAT:
        raise BackupError("format")
    if not all(_safe_name(n) for n in names if not n.endswith("/")):
        raise BackupError("names")
    return info


def _check_database(database: Path) -> None:
    """Wirft BackupError, wenn die mitgelieferte Datenbank keine ist oder
    beschädigt ist (sonst würde sie beim nächsten Start beiseitegelegt)."""
    if not database.is_file():
        return
    try:
        conn = sqlite3.connect(database)
        try:
            ok = conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise BackupError(str(exc)) from exc
    if not ok:
        raise BackupError("database")
    if version > db.SCHEMA_VERSION:
        raise BackupError("Die Sicherung stammt von einer neueren Programmfassung; bitte erst das Programm aktualisieren.")


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
        _check_database(staging / STATS / db.DB_FILE_NAME)

        # Unter Windows ist eine offene Datei gesperrt; der nächste Zugriff
        # öffnet die eingelesene Datenbank.
        db.close()
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
    except ZIP_ERRORS as exc:
        raise BackupError(str(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return previous
