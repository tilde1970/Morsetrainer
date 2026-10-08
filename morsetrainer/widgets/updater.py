"""Update anbieten, im Hintergrund laden und neu starten (siehe
net/update.py). Genutzt beim Programmstart (neueres Release auf GitHub)
und im Netzwerk-Reiter (Trainer hat eine neuere Version)."""
import os
import re
import threading
import tkinter as tk
from tkinter import ttk

from morsetrainer.i18n import number, tr
from morsetrainer.net import update
from morsetrainer.widgets import announcer, theme
from morsetrainer.widgets.help_window import render, setup_tags

WATCH_MS = 200
HINT, DECLINED, STARTED = "hint", "declined", "started"
# Überschriften der Neuerungen („- **Am Stück:** …“) für die Ansage.
_NOTE_TITLE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*", re.MULTILINE)


class UpdateDialog:
    """Fenster „Update verfügbar“: warum (`intro`), was neu ist (`notes`,
    Markdown aus der Release-Beschreibung), woher geladen wird; Knöpfe
    „Jetzt aktualisieren“ (Enter) und „Später“ (Esc). Nach dem Ja bleibt es
    offen und zeigt den Fortschritt. Die Ansage liest beim Öffnen die Lage
    und die Überschriften der Neuerungen vor, F11 wiederholt."""

    def __init__(self, root, version: str, intro: str, notes: str = ""):
        self.answer = tk.StringVar(root, value="")
        top = self.top = tk.Toplevel(root)
        top.title(tr("Update verfügbar"))
        top.configure(background=theme.BG)
        top.transient(root)
        frame = ttk.Frame(top, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=tr("Update verfügbar"), style="Score.TLabel").pack(anchor="w")
        ttk.Label(frame, text=intro, wraplength=520, justify="left").pack(anchor="w", pady=(2, 8))
        if notes:
            ttk.Label(frame, text=tr("Neu in Version {version}:").format(version=version)).pack(anchor="w")
            box = ttk.Frame(frame)
            box.pack(fill="both", expand=True, pady=(2, 8))
            text = tk.Text(box, height=12, width=70, wrap="word", padx=10, pady=6, cursor="arrow",
                           font="TkDefaultFont")
            scroll = ttk.Scrollbar(box, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            setup_tags(text)
            text.tag_configure("li", spacing1=4, spacing3=4)  # Neuerungen etwas luftiger
            render(text, notes)
        theme.hint(frame, wrap=520, text=tr(
            "Geladen wird von GitHub und mit der Prüfsumme geprüft. Danach startet der Morsetrainer neu; "
            "deine Übungsdaten und Einstellungen bleiben erhalten.")).pack(anchor="w")
        self.progress_var = tk.StringVar(top, value="")
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress_label = ttk.Label(frame, textvariable=self.progress_var, wraplength=520, justify="left")
        self.buttons = ttk.Frame(frame)
        self.buttons.pack(fill="x", pady=(12, 0))
        self.later_button = ttk.Button(self.buttons, text=tr("Später"), command=lambda: self.answer.set("no"))
        self.later_button.pack(side="right")
        self.yes_button = ttk.Button(self.buttons, text=tr("Jetzt aktualisieren"), style="Accent.TButton",
                                     command=lambda: self.answer.set("yes"))
        self.yes_button.pack(side="right", padx=(0, 8))
        titles = [title.rstrip(":").strip() for title in _NOTE_TITLE.findall(notes)]
        self.spoken = intro + (" " + tr("Neu: {titles}.").format(titles=", ".join(titles)) if titles else "") + \
            " " + tr("Enter: jetzt aktualisieren. Escape: später.")
        top.bind("<Return>", lambda e: self.answer.get() or self.answer.set("yes"))
        top.bind("<KP_Enter>", lambda e: self.answer.get() or self.answer.set("yes"))
        top.bind("<Escape>", lambda e: self.answer.get() in ("", "failed") and self._escape())
        top.bind("<F11>", lambda e: announcer.say(self.spoken))
        top.protocol("WM_DELETE_WINDOW", self._escape)
        self.yes_button.focus_set()
        announcer.say(self.spoken)

    def _escape(self):
        if self.answer.get() == "failed":
            self.close()
        elif self.answer.get() == "":
            self.answer.set("no")

    def ask(self) -> bool:
        """Wartet auf die Antwort (modal); bei „Später“ geht das Fenster zu."""
        try:
            self.top.grab_set()
        except tk.TclError:
            pass  # noch nicht sichtbar (etwa in Tests ohne Fenster)
        if not self.answer.get():
            self.top.wait_variable(self.answer)
        if self.answer.get() != "yes":
            self.close()
            return False
        self.buttons.pack_forget()
        self.progress.pack(fill="x", pady=(12, 2))
        self.progress_label.pack(anchor="w")
        return True

    def show_progress(self, text: str, percent=None) -> None:
        """Fortschritt des Downloads im Fenster."""
        self.progress_var.set(text)
        if percent is not None:
            self.progress["value"] = percent

    def show_failed(self, text: str) -> None:
        """Download gescheitert: Grund und Link stehen da, Schließen-Knopf."""
        self.answer.set("failed")
        self.progress.pack_forget()
        self.progress_var.set(text)
        close = ttk.Button(self.top.winfo_children()[0], text=tr("Schließen"), command=self.close)
        close.pack(anchor="e", pady=(10, 0))
        close.focus_set()
        announcer.say(text)

    def close(self) -> None:
        try:
            self.top.grab_release()
            self.top.destroy()
        except tk.TclError:
            pass


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
        self.dialog = None  # UpdateDialog des laufenden Downloads

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

    def offer(self, version, intro, show, prepare=lambda: [], failed=lambda: None, notes="", again=False):
        """Fragt einmal je Version, ob auf `version` aktualisiert werden
        soll (UpdateDialog); mit `again` auch noch einmal, wenn der Nutzer
        selbst danach fragt. `intro` erklärt warum, `notes` sagt, was neu
        ist. `show(text)` zeigt Hinweise und den Fortschritt auch außerhalb
        des Fensters. Bei „Ja“ liefert `prepare()` die Argumente für den
        Neustart; `failed()` nach einem Fehler. Ergebnis: None (nichts zu
        tun), HINT (nur Hinweis), DECLINED (abgelehnt) oder STARTED."""
        if self.busy or not update.is_newer(version, self.version) or (version in self.asked and not again):
            return None
        self.asked.add(version)
        if not self.can_install():
            # Aus dem Quelltext gestartet oder kein Schreibrecht: nur Hinweis.
            hint = intro + " " + tr("Bitte aktualisieren: {url}").format(url=update.release_url(version))
            show(hint)
            announcer.say(hint)
            return HINT
        dialog = UpdateDialog(self.root, version, intro, notes)
        if not dialog.ask():
            return DECLINED
        self.dialog = dialog
        announcer.say(tr("Lade Version {version}.").format(version=version))
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
        dialog = self.dialog
        if status["error"] is not None:
            self.status = None
            text = tr("Update fehlgeschlagen: {error}. Von Hand laden: {url}").format(
                error=status["error"], url=update.release_url(version))
            show(text)
            if dialog is not None:
                dialog.show_failed(text)
            failed()
            return
        if status["installed"]:
            text = tr("Version {version} installiert – starte neu…").format(version=version)
            show(text)
            if dialog is not None:
                dialog.show_progress(text, 100)
            announcer.say(text, then=lambda: self.restart(args))
            return
        percent = 100 * status["done"] // status["total"] if status["total"] else None
        progress = f"{percent} %" if percent is not None else f"{number(status['done'] / 1e6, 1)} MB"
        text = tr("Lade Version {version}… {progress}").format(version=version, progress=progress)
        show(text)
        if dialog is not None:
            dialog.show_progress(text, percent)
        try:
            self.root.after(WATCH_MS, lambda: self._watch(version, show, args, failed))
        except tk.TclError:
            pass  # Fenster schon zu
