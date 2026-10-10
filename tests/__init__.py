"""Tests für den Morsetrainer. Laufen ohne Soundkarte und ohne Fenster:
sounddevice wird durch eine Attrappe ersetzt, bevor Module es importieren.

Aufruf aus dem Projektverzeichnis: python -m unittest discover tests"""
import os
import sys
import types
from pathlib import Path

# Die Tests prüfen deutsche Texte, unabhängig von der Spracheinstellung.
os.environ["MORSETRAINER_LANG"] = "de"
# Ohne Eingabemethode (ibus): Mit ihr kostet unter X11 jedes Tk-Fenster eine
# Rundreise zum IM-Server, die Tests liefen zehnmal so lange und blieben ab
# und zu ganz hängen. Muss vor dem ersten tk.Tk() gesetzt sein.
os.environ["XMODIFIERS"] = "@im=none"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "sounddevice" not in sys.modules:
    _sd = types.ModuleType("sounddevice")
    _sd.OutputStream = None
    _sd.play = _sd.stop = _sd.wait = lambda *args, **kwargs: None
    sys.modules["sounddevice"] = _sd

# Kein Test darf die echten Übungsdaten anfassen: Wer STATS_DIR nicht selbst
# auf einen eigenen Ordner setzt, landet in diesem (samt Datenbank).
import atexit  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

from morsetrainer.core import stats as _stats  # noqa: E402

_guard_dir = Path(tempfile.mkdtemp(prefix="morsetrainer-tests-"))
_stats.STATS_DIR = _guard_dir / "stats"
atexit.register(shutil.rmtree, _guard_dir, True)


def session_lines(session_id: int) -> list:
    """Ein Durchgang aus der Datenbank als Zeilen wie früher in der
    Sitzungsdatei: config, die Zeilen dazwischen, summary (falls vorhanden)."""
    from morsetrainer.core import db
    [session] = [s for s in db.sessions() if s.id == session_id]
    return [session.config, *db.session_events(session_id), *([session.summary] if session.summary else [])]


def release_root(root, owner=None) -> None:
    """Tk-Fenster schließen und seinen Interpreter freigeben. root.destroy()
    allein lässt die Python-Befehle von bind_all, bind_class und Traces im
    Interpreter stehen; sie halten die App und damit den ganzen Interpreter
    fest (etwa 5 MB je Test). `owner`: der Test; seine Attribute (Fenster,
    App, Variablen) werden gelöscht, damit alles hier eingesammelt wird und
    nicht erst, wenn der Test selbst wegfällt. Deshalb zuletzt aufrufen."""
    import gc
    import tkinter as tk
    from morsetrainer.widgets import theme
    interp = root.tk
    try:
        for after_id in interp.splitlist(interp.call("after", "info")):
            root.after_cancel(after_id)  # sonst „invalid command name …“ nach dem Schließen
    except tk.TclError:
        pass
    root.destroy()
    # Variablen löschen ihre Trace-Befehle beim Einsammeln selbst; die sind
    # gleich schon weg. (Ohne Schleifenvariable: sie hielte das letzte Objekt
    # samt allem, woran es hängt, über das Einsammeln unten hinaus fest.)
    for variable in [obj for obj in gc.get_objects()
                     if isinstance(obj, tk.Variable) and getattr(obj, "_tk", None) is interp]:
        variable._tclCommands = None
    variable = None
    for name in interp.splitlist(interp.call("info", "commands")):
        if name[:1].isdigit():  # von tkinter angelegte Python-Befehle
            try:
                interp.deletecommand(name)
            except tk.TclError:
                pass
    theme._fonts[:] = [f for f in theme._fonts if getattr(f, "_tk", None) is not interp]
    if owner is not None:
        for name in [name for name in vars(owner) if not name.startswith("_")]:
            delattr(owner, name)
    # Jetzt im Hauptthread einsammeln. Räumt sonst irgendwann ein anderer
    # Thread (Netzwerk, Audio) Tk-Variablen und -Bilder weg, wartet tkinter
    # dort je Objekt eine Sekunde auf die mainloop, die in Tests nie läuft.
    gc.collect()


def write_session(lines) -> int:
    """Legt einen Durchgang aus Zeilen wie in einer Sitzungsdatei an
    (erste Zeile config mit "start_time" und "mode", eine Zeile "summary"
    schließt ihn ab) und gibt seine id zurück."""
    from morsetrainer.core import db
    config, *rest = lines
    with db.transaction():
        session_id = db.start_session(config)
        for line in rest:
            if line.get("type") == "summary":
                db.finish_session(session_id, line)
            else:
                db.add_event(session_id, line)
    return session_id
