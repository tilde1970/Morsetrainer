"""Die Übungsdaten in einer SQLite-Datenbank (stats/morsetrainer.db).

Tabellen:
    sessions  ein Durchgang: Zeile "config" und, sobald abgeschlossen,
              Zeile "summary" (beide als JSON)
    events    die Zeilen dazwischen ("char", "group"), je Durchgang in
              der Reihenfolge des Schreibens
    results   Ergebnisse ohne Zeichenstatistik (QSO-Abfrage, Contest …)
    state     Zustände als JSON unter einem Schlüssel (Gesamtstatistik,
              Tagesübung, Diplome, Lernkartei, Übungszeit)
    meta      Verwaltung (z. B. Übernahme der alten JSON-Dateien)

Die Inhalte bleiben JSON, so wie sie bisher in den Dateien standen: Die
Auswertungen arbeiten weiter mit denselben Dictionaries, die Datenbank
filtert nur nach Zeitraum und Modus vor.

Jeder Schreibvorgang wird sofort festgeschrieben (ein Absturz kostet
höchstens die laufende Zeile); mehrere zusammengehörige Änderungen
fasst transaction() zusammen. Zwei Programmfenster auf einem Rechner
dürfen gleichzeitig schreiben (WAL, Wartezeit bei Sperre). Ist die Datei
kaputt, wird sie wie die JSON-Dateien als "<Name>.defekt-<Zeitstempel>"
beiseitegelegt und eine neue begonnen.

Schreibfunktionen werfen bei Fehlern db.Error (Datenbank) oder OSError
(Ordner nicht anlegbar); Lesefunktionen liefern dann leere Ergebnisse."""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

DB_FILE_NAME = "morsetrainer.db"
SCHEMA_VERSION = 1
# So lange wartet ein Fenster, wenn das andere gerade schreibt.
BUSY_TIMEOUT_MS = 5000

Error = sqlite3.Error

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    start_time TEXT NOT NULL,
    mode TEXT NOT NULL,
    config TEXT NOT NULL,
    summary TEXT
);
CREATE INDEX IF NOT EXISTS sessions_start ON sessions (start_time);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_session ON events (session_id, id);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    time TEXT NOT NULL,
    mode TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS results_time ON results (time);
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Eine Verbindung für alle Threads, geschützt durch die Sperre. Die
# Übungen schreiben aus dem Tk-Hauptthread; die Sperre hält auch dann,
# wenn das einmal anders sein sollte.
_lock = threading.RLock()
_path = None
_conn = None
_conn_path = None
# Zählt jedes Öffnen einer Datenbank mit. Wer Durchgänge nach ihrer id
# zwischenspeichert, erkennt daran eine andere Datei (Tests, Import einer
# Sicherung), in der dieselbe id einen anderen Durchgang meint.
generation = 0
_depth = 0  # Tiefe verschachtelter transaction()-Blöcke
# Gelesene config/summary abgeschlossener Durchgänge, {id: (config, summary)}:
# Die ändern sich nicht mehr, sessions() muss sie nicht jedes Mal neu aus
# JSON lesen. Gilt nur für die Datei der Generation in _heads_generation.
_heads = {}
_heads_generation = [None]


@dataclass
class Session:
    id: int
    config: dict
    summary: dict    # None, solange der Durchgang läuft (oder abgebrochen ist)
    events: list     # None, wenn nicht mitgelesen


def path() -> Path:
    """stats/morsetrainer.db, oder die mit use() gesetzte Datei. Folgt
    stats.STATS_DIR, damit Tests mit eigenem Ordner ihre eigene Datenbank
    bekommen."""
    if _path is not None:
        return _path
    from morsetrainer.core import stats  # stats importiert db
    return stats.STATS_DIR / DB_FILE_NAME


def use(new_path) -> None:
    """Auf eine andere Datenbankdatei umschalten (Tests, Import einer
    Sicherung); None = wieder die übliche. Die bisherige wird geschlossen."""
    global _path
    with _lock:
        close()
        _path = Path(new_path) if new_path is not None else None


def close() -> None:
    """Verbindung schließen, z. B. bevor stats/ beim Import ersetzt wird
    (unter Windows ist eine offene Datei gesperrt). Der nächste Zugriff
    öffnet sie wieder."""
    global _conn, _depth
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Error:
                pass
        _conn = None
        _depth = 0


def _open(file: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(file, timeout=BUSY_TIMEOUT_MS / 1000, check_same_thread=False,
                           isolation_level=None)
    try:
        # Eine Datei, die keine Datenbank ist, fällt erst beim ersten Befehl auf.
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("quick_check")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except Error:
        conn.close()
        raise
    return conn


def _set_aside(file: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.replace(file, file.with_name(f"{file.name}.defekt-{stamp}"))
    # Das Journal gehört zur alten Datei und darf nicht auf die neue wirken.
    for suffix in ("-wal", "-shm"):
        file.with_name(file.name + suffix).unlink(missing_ok=True)


def _connection() -> sqlite3.Connection:
    global _conn, _conn_path, generation
    file = path()
    if _conn is not None and file != _conn_path:
        close()
    if _conn is None:
        file.parent.mkdir(parents=True, exist_ok=True)
        try:
            _conn = _open(file)
        except sqlite3.OperationalError:
            raise  # gesperrt, keine Rechte …: Datei nicht anrühren
        except sqlite3.DatabaseError:
            _set_aside(file)
            _conn = _open(file)
        _conn_path = file
        generation += 1
    return _conn


@contextmanager
def transaction():
    """Alle Schreibvorgänge im Block gemeinsam festschreiben oder bei einem
    Fehler gemeinsam verwerfen (z. B. Zusammenfassung eines Durchgangs,
    Gesamtstatistik und Lernkartei). Darf verschachtelt werden."""
    global _depth
    with _lock:
        conn = _connection()
        if _depth == 0:
            conn.execute("BEGIN IMMEDIATE")
        _depth += 1
        try:
            yield
        except BaseException:
            _depth -= 1
            if _depth == 0 and conn.in_transaction:
                conn.execute("ROLLBACK")
                _heads.clear()  # könnte Verworfenes enthalten
            raise
        _depth -= 1
        if _depth == 0:
            try:
                conn.execute("COMMIT")
            except Error:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                _heads.clear()
                raise


def _write(sql: str, params=()) -> int:
    """Einen Befehl ausführen (außerhalb von transaction() sofort
    festgeschrieben); liefert die id der eingefügten Zeile."""
    with transaction():
        return _connection().execute(sql, params).lastrowid


def _read(sql: str, params=()) -> list:
    with _lock:
        try:
            return _connection().execute(sql, params).fetchall()
        except (Error, OSError):
            return []


def _dump(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _load(text):
    """JSON aus einer Zeile, oder None, wenn sie nicht lesbar ist (von Hand
    verändert, beschädigt)."""
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


# --- Zustände -----------------------------------------------------------------

def load_state(key: str, default):
    """Inhalt von `key`, oder `default`, wenn er fehlt, nicht lesbar ist
    oder nicht vom Typ von `default` ist. Ein unlesbarer Eintrag wird unter
    "<key>.defekt-<Zeitstempel>" beiseitegelegt statt beim nächsten
    Speichern stillschweigend überschrieben zu werden."""
    rows = _read("SELECT data FROM state WHERE key = ?", (key,))
    if not rows:
        return default
    data = _load(rows[0][0])
    if not isinstance(data, type(default)):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            _write("UPDATE state SET key = ? WHERE key = ?", (f"{key}.defekt-{stamp}", key))
        except (Error, OSError):
            pass
        return default
    return data


def save_state(key: str, data) -> None:
    _write("INSERT INTO state (key, data) VALUES (?, ?) "
           "ON CONFLICT (key) DO UPDATE SET data = excluded.data", (key, _dump(data)))


def delete_state(key: str) -> None:
    _write("DELETE FROM state WHERE key = ?", (key,))


# --- Durchgänge ---------------------------------------------------------------

def start_session(config: dict) -> int:
    """Legt einen Durchgang an; `config` braucht "start_time" (ISO) und
    "mode". Liefert seine id."""
    return _write("INSERT INTO sessions (start_time, mode, config) VALUES (?, ?, ?)",
                  (config["start_time"], config["mode"], _dump(config)))


def add_event(session_id: int, entry: dict) -> None:
    """Eine Zeile ("type": "char" oder "group") an den Durchgang anhängen."""
    _write("INSERT INTO events (session_id, type, data) VALUES (?, ?, ?)",
           (session_id, entry.get("type", ""), _dump(entry)))


def finish_session(session_id: int, summary: dict) -> None:
    _heads.pop(session_id, None)
    _write("UPDATE sessions SET summary = ? WHERE id = ?", (_dump(summary), session_id))


def delete_session(session_id: int) -> None:
    """Durchgang samt Zeilen entfernen (z. B. ohne ein einziges Zeichen)."""
    _heads.pop(session_id, None)  # SQLite kann die Nummer neu vergeben
    _write("DELETE FROM sessions WHERE id = ?", (session_id,))


def _day_bound(value) -> str:
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value)


def sessions(since=None, until=None, mode=None, events=False) -> list:
    """Durchgänge nach Startzeit, auch nicht abgeschlossene (summary None).
    `since`: Datum oder Zeitpunkt, ab dem (einschließlich); `until`: Tag,
    bis zu dem (einschließlich); `mode`: nur dieser Modus. `events=True`
    liest die Zeilen dazwischen mit. Unlesbare Zeilen fallen weg.
    config und summary abgeschlossener Durchgänge kommen aus einem
    Zwischenspeicher und werden von allen Aufrufern geteilt: nicht ändern."""
    where, params = [], []
    if since is not None:
        where.append("start_time >= ?")
        params.append(_day_bound(since))
    if until is not None:
        where.append("substr(start_time, 1, 10) <= ?")
        params.append(_day_bound(until)[:10])
    if mode is not None:
        where.append("mode = ?")
        params.append(mode)
    sql = "SELECT id, summary IS NOT NULL FROM sessions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = _read(sql + " ORDER BY start_time, id", params)
    gen = generation  # erst nach _read: das Öffnen kann sie hochzählen
    if _heads_generation[0] != gen:
        _heads.clear()
        _heads_generation[0] = gen
    missing = [session_id for session_id, finished in rows if not finished or session_id not in _heads]
    fetched = {}
    for start in range(0, len(missing), 500):
        chunk = missing[start:start + 500]
        for session_id, config_text, summary_text in _read(
                f"SELECT id, config, summary FROM sessions WHERE id IN ({','.join('?' * len(chunk))})", chunk):
            config = _load(config_text)
            summary = _load(summary_text) if summary_text is not None else None
            head = (config if isinstance(config, dict) else None, summary if isinstance(summary, dict) else None)
            fetched[session_id] = head
            if summary_text is not None:
                _heads[session_id] = head
    out = []
    for session_id, finished in rows:
        config, summary = fetched.get(session_id) or _heads.get(session_id, (None, None))
        if config is not None:
            out.append(Session(session_id, config, summary, None))
    if events and out:
        by_id = events_by_session([s.id for s in out])
        for s in out:
            s.events = by_id[s.id]
    return out


def events_by_session(ids) -> dict:
    """{id: [Zeilen in der Reihenfolge des Schreibens]} der Durchgänge `ids`."""
    by_id = {session_id: [] for session_id in ids}
    ids = list(by_id)
    # In Stücken, damit die Zahl der Platzhalter die Grenze von SQLite nicht reißt.
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        rows = _read(f"SELECT session_id, data FROM events WHERE session_id IN "
                     f"({','.join('?' * len(chunk))}) ORDER BY session_id, id", chunk)
        for session_id, text in rows:
            entry = _load(text)
            if isinstance(entry, dict):
                by_id[session_id].append(entry)
    return by_id


def session_events(session_id: int) -> list:
    """Die Zeilen eines Durchgangs in der Reihenfolge des Schreibens."""
    entries = (_load(text) for (text,) in
               _read("SELECT data FROM events WHERE session_id = ? ORDER BY id", (session_id,)))
    return [e for e in entries if isinstance(e, dict)]


# --- Ergebnisse ---------------------------------------------------------------

def add_result(entry: dict) -> None:
    """`entry` braucht "time" (ISO) und "mode"."""
    _write("INSERT INTO results (time, mode, data) VALUES (?, ?, ?)",
           (entry["time"], entry["mode"], _dump(entry)))


def results() -> list:
    """Alle Ergebnisse in der Reihenfolge des Schreibens."""
    entries = (_load(text) for (text,) in _read("SELECT data FROM results ORDER BY id"))
    return [e for e in entries if isinstance(e, dict)]


# --- Verwaltung ---------------------------------------------------------------

def get_meta(key: str):
    rows = _read("SELECT value FROM meta WHERE key = ?", (key,))
    return rows[0][0] if rows else None


def set_meta(key: str, value: str) -> None:
    _write("INSERT INTO meta (key, value) VALUES (?, ?) "
           "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, value))
