"""Update anbieten, im Hintergrund laden und neu starten (siehe
net/update.py). Genutzt beim Programmstart (neueres Release auf GitHub)
und im Netzwerk-Reiter (Trainer hat eine neuere Version)."""
import os
import threading
import tkinter as tk
from tkinter import messagebox

from morsetrainer.i18n import number, tr
from morsetrainer.net import update

WATCH_MS = 200
HINT, DECLINED, STARTED = "hint", "declined", "started"


class Updater:
    """Updates aus dem Programm heraus: fragt einmal je Version nach, lädt im
    Hintergrund, ersetzt das Programm und startet neu (oder zeigt nur den
    Link, wo sich nichts ersetzen lässt)."""
    def __init__(self, root, version, restart):
        """`restart(args)`: Programm beenden (alles speichern) und das neue
        mit `args` starten."""
        self.root = root
        self.version = version
        self.restart = restart
        self.asked = set()  # Versionen, nach denen schon gefragt wurde
        self.status = None  # laufender Download: Fortschritt aus dem Thread

    @property
    def busy(self) -> bool:
        """Läuft gerade ein Download?"""
        return self.status is not None

    @staticmethod
    def can_install() -> bool:
        """Lässt sich das Programm selbst ersetzen (gepackte exe bzw. AppImage mit
        Schreibrecht im Ordner)?"""
        found = update.installed()
        return found is not None and os.access(found[0].parent, os.W_OK)

    def offer(self, version, intro, show, prepare=lambda: [], failed=lambda: None):
        """Fragt einmal je Version, ob auf `version` aktualisiert werden
        soll; `intro` erklärt warum. `show(text)` zeigt Hinweise und den
        Fortschritt. Bei „Ja“ liefert `prepare()` die Argumente für den
        Neustart; `failed()` nach einem Fehler. Ergebnis: None (nichts zu
        tun), HINT (nur Hinweis), DECLINED (abgelehnt) oder STARTED."""
        if self.busy or not update.is_newer(version, self.version) or version in self.asked:
            return None
        self.asked.add(version)
        if not self.can_install():
            # Aus dem Quelltext gestartet oder kein Schreibrecht: nur Hinweis.
            show(intro + " " + tr("Bitte aktualisieren: {url}").format(url=update.release_url(version)))
            return HINT
        if not messagebox.askyesno(tr("Update"), intro + "\n\n" + tr(
                "Jetzt aktualisieren und neu starten? Geladen wird von GitHub."), parent=self.root):
            return DECLINED
        args = prepare()
        target, asset = update.installed()
        status = self.status = {"done": 0, "total": 0, "installed": False, "error": None}

        def run():
            def progress(done, total):
                status["done"], status["total"] = done, total
            try:
                update.install(update.download(version, target, asset, progress), target)
                status["installed"] = True
            except update.UpdateError as exc:
                status["error"] = str(exc)
            except Exception as exc:
                status["error"] = str(exc) or type(exc).__name__
                raise  # ins Fehlerprotokoll (threading.excepthook)
        threading.Thread(target=run, daemon=True).start()
        self._watch(version, show, args, failed)
        return STARTED

    def _watch(self, version, show, args, failed):
        """Verfolgt den Download im GUI-Thread: Fortschritt zeigen, bei Fehler den
        Link zum Herunterladen, nach erfolgreicher Installation neu starten."""
        status = self.status
        if status["error"] is not None:
            self.status = None
            show(tr("Update fehlgeschlagen: {error}. Von Hand laden: {url}").format(
                error=status["error"], url=update.release_url(version)))
            failed()
            return
        if status["installed"]:
            show(tr("Version {version} installiert – starte neu…").format(version=version))
            self.restart(args)
            return
        progress = (f"{100 * status['done'] // status['total']} %" if status["total"]
                    else f"{number(status['done'] / 1e6, 1)} MB")
        show(tr("Lade Version {version}… {progress}").format(version=version, progress=progress))
        try:
            self.root.after(WATCH_MS, lambda: self._watch(version, show, args, failed))
        except tk.TclError:
            pass  # Fenster schon zu
