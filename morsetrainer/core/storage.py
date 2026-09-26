"""Sicheres Schreiben und Lesen der Datendateien (all_time.json,
practice.json, window_state.json).

Geschrieben wird erst in eine Nachbardatei, die dann per os.replace die
alte ersetzt: Bricht das Schreiben ab (Absturz, Stromausfall, volle
Platte), bleibt die bisherige Datei vollständig erhalten statt halb
überschrieben. Ist eine Datei trotzdem kaputt, wird sie beim Laden als
"<Name>.defekt-<Zeitstempel>" beiseitegelegt, statt das Programm am Start
zu hindern oder beim nächsten Speichern stillschweigend überschrieben zu
werden."""
import json
import os
from datetime import datetime
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    """Wirft OSError, wenn das Schreiben scheitert; `path` bleibt dann
    unverändert."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fp:
            fp.write(text)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def write_json_atomic(path: Path, data, **dump_options) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, **dump_options))


def load_json(path: Path, default):
    """Inhalt von `path`, oder `default`, wenn die Datei fehlt, nicht lesbar
    ist oder nicht vom Typ von `default` ist. Kaputte Dateien werden
    beiseitegelegt (siehe Moduldoku)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:  # fehlt oder nicht lesbar
        return default
    except UnicodeDecodeError:
        _set_aside(path)
        return default
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        _set_aside(path)
        return default
    if not isinstance(data, type(default)):
        _set_aside(path)
        return default
    return data


def _set_aside(path: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(path, path.with_name(f"{path.name}.defekt-{stamp}"))
    except OSError:
        pass
