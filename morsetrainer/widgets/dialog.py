"""Meldungen und Ja/Nein-Fragen, die man auch ohne Hinsehen bedienen kann.

Ersatz für tkinter.messagebox: Dessen Fenster sagt die Ansage nicht an,
F9 und F11 wirken darin nicht, und die Leertaste wählt „Ja“ – wer gerade
noch Zeichen getippt hat, bestätigte so ungewollt etwa die nächste
Koch-Lektion. Hier:

- Beim Öffnen wird der Text angesagt, dazu, was Enter und Escape tun.
- Enter: Ja bzw. OK; Escape und das Schließen des Fensters: Nein.
  Steht der Fokus (mit Tab) auf einem Knopf, gilt Enter diesem Knopf.
- Die Leertaste wirkt nur auf einen Knopf, zu dem man mit Tab gegangen ist.
- F11 wiederholt die Ansage, F9 schaltet die Ansage an oder aus.

Gleiche Aufrufe wie messagebox (askyesno, showinfo, showwarning,
showerror), damit der Umstieg nichts anderes ändert."""
import tkinter as tk
from tkinter import filedialog, ttk

from morsetrainer.i18n import tr
from morsetrainer.widgets import announcer, theme

WRAP = 480


class MessageDialog:
    """Modales Fenster mit `text` und einem Knopf (Meldung) oder zweien
    (Frage). `answer` ist nach dem Schließen True (Ja/OK) oder False."""

    def __init__(self, parent, title: str, text: str, question: bool):
        self.answer = False
        self.parent = parent
        top = self.top = tk.Toplevel(parent)
        top.title(title)
        top.configure(background=theme.BG)
        top.transient(parent.winfo_toplevel())
        top.resizable(False, False)
        frame = ttk.Frame(top, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=text, wraplength=WRAP, justify="left").pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))
        if question:
            # „Ja“ zuerst angelegt: Tab erreicht es vor „Nein“, wie es dasteht.
            yes = ttk.Button(buttons, text=tr("Ja"), style="Accent.TButton", command=self._yes)
            ttk.Button(buttons, text=tr("Nein"), command=self._no).pack(side="right")
            yes.pack(side="right", padx=(0, 8))
            keys = tr("Enter: ja. Escape: nein.")
        else:
            ttk.Button(buttons, text=tr("OK"), style="Accent.TButton", command=self._yes).pack(side="right")
            keys = tr("Enter: schließen.")
        self.spoken = f"{text} {keys}"
        self.keys = {"<Return>": self._enter, "<KP_Enter>": self._enter, "<Escape>": self._no,
                     "<F11>": lambda: self._say(force=True), "<F9>": self._toggle_announce}
        for sequence, action in self.keys.items():
            top.bind(sequence, lambda e, a=action: a())
        top.protocol("WM_DELETE_WINDOW", self._no)
        # Fokus aufs Fenster, nicht auf „Ja“: Eine Leertaste aus dem Tippen
        # davor soll nichts entscheiden.
        top.focus_set()
        self._say()

    def _say(self, force: bool = False) -> None:
        instance = announcer.get()
        if instance is not None:
            instance.say(self.spoken, force=force)

    def _toggle_announce(self) -> None:
        """F9 wie im Hauptfenster; eingeschaltet gleich die Meldung dazu."""
        instance = announcer.get()
        if instance is None:
            return
        instance.var.set(not instance.var.get())
        if instance.enabled():
            instance.say(f"{tr('Ansage an.')} {self.spoken}", force=True)
        else:
            instance.say(tr("Ansage aus."), force=True)

    def _enter(self) -> None:
        focus = self.top.focus_lastfor()
        if isinstance(focus, ttk.Button):
            focus.invoke()
        else:
            self._yes()

    def _yes(self) -> None:
        self.answer = True
        self.close()

    def _no(self) -> None:
        self.answer = False
        self.close()

    def close(self) -> None:
        try:
            self.top.grab_release()
            self.top.destroy()
        except tk.TclError:
            pass

    def wait(self) -> bool:
        """Wartet modal auf die Antwort."""
        try:
            self.top.grab_set()
        except tk.TclError:
            pass  # noch nicht sichtbar (etwa in Tests ohne Fenster)
        try:
            self.top.wait_window()
        except tk.TclError:
            pass
        return self.answer


def _parent(parent):
    return parent if parent is not None else tk._get_default_root()


def askyesno(title: str, text: str, parent=None) -> bool:
    """Ja/Nein-Frage; True bei Ja."""
    return MessageDialog(_parent(parent), title, text, question=True).wait()


def showinfo(title: str, text: str, parent=None) -> None:
    """Hinweis mit einem Knopf „OK“."""
    MessageDialog(_parent(parent), title, text, question=False).wait()


# Warnung und Fehler sehen gleich aus; was los ist, sagen Titel und Text.
showwarning = showinfo
showerror = showinfo


# Steht gerade ein Dateidialog aus (Ansage läuft oder Dialog offen)?
_file_pending = False


def _busy(window, busy: bool) -> None:
    """Wartezeiger während der Ansage vor dem Dateidialog: Sonst sieht man
    nach dem Klick sekundenlang nichts."""
    try:
        window.config(cursor="watch" if busy else "")
    except tk.TclError:
        pass


def _choose_file(ask, keys: str, then, **options) -> None:
    # Der Dateidialog von Tk sagt nichts an; vorher sagen, was kommt und was
    # die Tasten tun, und erst nach der Ansage öffnen (sie liefe sonst
    # über dem Dialog weiter und ginge im Tippen unter). Ein zweiter Druck
    # in der Zeit öffnet keinen zweiten Dialog.
    global _file_pending
    if _file_pending:
        return
    _file_pending = True
    window = _parent(options.get("parent"))
    _busy(window, True)

    def open_dialog():
        global _file_pending
        try:
            path = ask(**options)
        finally:
            _file_pending = False
            _busy(window, False)
        then(path)

    text = tr("Dateiauswahl {title}.").format(title=options.get("title", "")) + " " + keys
    announcer.say(text, then=open_dialog)


def asksaveasfilename(then, **options) -> None:
    """Wie filedialog.asksaveasfilename, aber angesagt; der gewählte Pfad
    (leer bei Abbruch) geht an `then(path)`."""
    _choose_file(filedialog.asksaveasfilename,
                 tr("Enter: unter dem vorgeschlagenen Namen speichern. Escape: abbrechen."),
                 then, **options)


def askopenfilename(then, **options) -> None:
    """Wie filedialog.askopenfilename, aber angesagt; Pfad an `then(path)`."""
    _choose_file(filedialog.askopenfilename,
                 tr("Dateinamen eingeben. Enter: öffnen. Escape: abbrechen."), then, **options)
