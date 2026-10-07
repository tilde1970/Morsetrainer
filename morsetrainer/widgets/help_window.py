"""Hilfe-Fenster: Anleitung (docs/Anleitung.md) und Änderungen
(CHANGELOG.md) im Programm lesen.

Die Pfade gelten ab dem Verzeichnis von main.py; in AppImage und exe packt
PyInstaller die Dateien mit ein (--add-data), dort liegen sie unter
sys._MEIPASS. Auf Englisch gelten Anleitung.en.md und CHANGELOG.en.md,
falls vorhanden.

Dargestellt wird ein kleiner Teil von Markdown, genug für die beiden
Dateien: Überschriften, Absätze, Listen, **fett**, *kursiv*, `Code`,
Codeblöcke, Links (nur der Text) und Tabellen (je Zeile ein Absatz mit
fetter erster Spalte). Bilder (`![…](…)` oder `<img …>` allein in einer
Zeile) fallen weg."""
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from morsetrainer import i18n
from morsetrainer.i18n import N_, tr
from morsetrainer.widgets import announcer, theme

DOCS = ((N_("Änderungen"), "CHANGELOG.md"), (N_("Anleitung"), "docs/Anleitung.md"))

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>")
_INLINE = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`|\*(.+?)\*|\[([^\]]+)\]\([^)]*\)")


def doc_path(name: str, lang: str = None) -> Path:
    """Pfad von `name`, in einer anderen Sprache als Deutsch die Fassung
    „<Name>.<Sprache>.md“, sofern es sie gibt."""
    base = getattr(sys, "_MEIPASS", None)
    folder = Path(base) if base else Path(__file__).resolve().parents[2]
    lang = lang or i18n.LANG
    if lang != i18n.DEFAULT:
        localized = folder / name.replace(".md", f".{lang}.md")
        if localized.exists():
            return localized
    return folder / name


def parse(text: str):
    """Markdown -> Liste von (Blockart, Zeilentext). Blockarten: h1, h2, h3,
    p, li, code, row, gap. Aufeinanderfolgende Textzeilen werden zu einem
    Absatz bzw. Listenpunkt zusammengefügt."""
    blocks = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            if not in_code:
                blocks.append(("gap", ""))
            continue
        if in_code:
            blocks.append(("code", line))
            continue
        stripped = line.strip()
        if not stripped:
            blocks.append(("gap", ""))
            continue
        if _IMAGE.fullmatch(stripped):
            continue
        heading = re.match(r"(#{1,3})\s+(.*)", stripped)
        if heading:
            blocks.append((f"h{len(heading.group(1))}", heading.group(2)))
            continue
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # Trennzeile |---|---|
            blocks.append(("row", "\t".join(cells)))
            continue
        item = re.match(r"(?:[-*]|\d+\.)\s+(.*)", stripped)
        if item:
            number = re.match(r"(\d+\.)", stripped)
            blocks.append(("li", (number.group(1) + " " if number else "• ") + item.group(1)))
            continue
        if blocks and blocks[-1][0] in ("p", "li"):
            # Fortsetzungszeile desselben Absatzes bzw. Listenpunkts
            kind, previous = blocks[-1]
            blocks[-1] = (kind, previous + " " + stripped)
            continue
        blocks.append(("p", stripped))
    return blocks


def _insert_inline(widget, text: str, base_tags=()):
    """Fügt eine Zeile mit **fett**, `Code`, *kursiv* und Links (nur der Text)
    ein; `base_tags` gelten für die ganze Zeile."""
    pos = 0
    for match in _INLINE.finditer(text):
        widget.insert("end", text[pos:match.start()], base_tags)
        bold, code, italic, link = match.groups()
        if bold is not None:
            _insert_inline(widget, bold, base_tags + ("bold",))
        elif code is not None:
            widget.insert("end", code, base_tags + ("code",))
        elif italic is not None:
            widget.insert("end", italic, base_tags + ("italic",))
        else:
            widget.insert("end", link, base_tags)
        pos = match.end()
    widget.insert("end", text[pos:], base_tags)


def render(widget: tk.Text, text: str) -> None:
    """Stellt Markdown-Text `text` im Textfeld `widget` dar (Blöcke aus
    parse(), Hervorhebungen mit Tags) und sperrt es danach gegen Eingabe."""
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    last = None
    header_row = True
    for kind, line in parse(text):
        if kind == "gap":
            if last not in (None, "gap"):
                widget.insert("end", "\n")
            last = kind
            header_row = True
            continue
        if kind in ("h1", "h2", "h3"):
            if last not in (None, "gap"):
                widget.insert("end", "\n")
            _insert_inline(widget, line, (kind,))
        elif kind == "code":
            widget.insert("end", line, ("code_block",))
        elif kind == "row":
            cells = line.split("\t")
            if header_row:
                header_row = False  # Kopfzeile der Tabelle weglassen
                last = kind
                continue
            _insert_inline(widget, cells[0], ("row", "bold"))
            _insert_inline(widget, ": " + " ".join(cells[1:]), ("row",))
        else:
            _insert_inline(widget, line, (kind,))
        widget.insert("end", "\n")
        last = kind
    widget.configure(state="disabled")


def _setup_tags(widget: tk.Text) -> None:
    widget.tag_configure("h1", font=theme.FEEDBACK, spacing1=4, spacing3=6)
    widget.tag_configure("h2", font=theme.SCORE, spacing1=10, spacing3=4)
    widget.tag_configure("h3", font=theme.HEADING, spacing1=8, spacing3=2)
    widget.tag_configure("bold", font=theme.HEADING)
    widget.tag_configure("italic", font=theme.SMALL_ITALIC)
    widget.tag_configure("code", font=theme.MONO)
    widget.tag_configure("code_block", font=theme.MONO, lmargin1=16, lmargin2=16)
    widget.tag_configure("li", lmargin1=12, lmargin2=26, spacing1=2)
    widget.tag_configure("row", lmargin1=4, lmargin2=16, spacing1=4, spacing3=4)
    widget.tag_configure("p", spacing1=2)


class HelpWindow:
    """Ein Fenster je Hauptfenster; ein zweiter Aufruf holt es nach vorn."""

    _open = None

    @classmethod
    def show(cls, root) -> None:
        """Öffnet das Hilfefenster oder holt das schon offene nach vorn."""
        try:
            if cls._open is not None and cls._open.top.winfo_exists():
                cls._open.top.deiconify()
                cls._open.top.lift()
                return
        except tk.TclError:
            pass  # gehörte zu einem schon zerstörten Hauptfenster
        cls._open = cls(root)

    def __init__(self, root):
        self.top = tk.Toplevel(root)
        self.top.title(tr("Morsetrainer – Hilfe"))
        self.top.configure(background=theme.BG)
        self.top.geometry("760x640")
        # Suchen (Strg+F): im gerade gezeigten Reiter; Enter springt zum
        # nächsten Treffer, Umschalt+Enter zum vorigen.
        bar = ttk.Frame(self.top)
        bar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(bar, text=tr("Suchen:")).pack(side="left")
        self.search_var = tk.StringVar(value="")
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=28)
        announcer.echo(self.search_entry)
        self.search_entry.pack(side="left", padx=(6, 8))
        announcer.name(self.search_entry, tr("Suchen in der Hilfe"))
        self.search_info_var = tk.StringVar(value=tr("Strg+F, Enter: nächster Treffer"))
        theme.hint(bar, textvariable=self.search_info_var).pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.find(1) or "break")
        self.search_entry.bind("<KP_Enter>", lambda e: self.find(1) or "break")
        self.search_entry.bind("<Shift-Return>", lambda e: self.find(-1) or "break")
        self.search_var.trace_add("write", lambda *_: self._new_search())
        self.matches = []  # Anfangspositionen der Treffer im gezeigten Text
        self.match_index = -1
        notebook = self.notebook = ttk.Notebook(self.top)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        notebook.bind("<<NotebookTabChanged>>", lambda e: self._new_search(), add="+")
        self.texts = {}
        for title, name in DOCS:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=tr(title))
            text = tk.Text(frame, wrap="word", padx=14, pady=10, cursor="arrow", font="TkDefaultFont")
            scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            _setup_tags(text)
            text.tag_configure("match", background=theme.SELECT)
            text.tag_configure("match_current", background=theme.ACCENT, foreground=theme.SURFACE)
            try:
                content = doc_path(name).read_text(encoding="utf-8")
            except OSError:
                content = tr("{name} wurde nicht gefunden.").format(name=name)
            render(text, content)
            self.texts[name] = text
        ttk.Button(self.top, text=tr("Schließen"), command=self.top.destroy).pack(anchor="e", padx=8, pady=(0, 8))
        self.top.bind("<Escape>", self._escape)
        for modifier in ("Control", "Command") if sys.platform == "darwin" else ("Control",):
            for key in ("f", "F"):  # auch mit Feststelltaste
                self.top.bind(f"<{modifier}-{key}>", lambda e: self.focus_search() or "break")

    def _current_text(self) -> tk.Text:
        return self.texts[DOCS[self.notebook.index("current")][1]]

    def focus_search(self) -> None:
        """Strg+F: Fokus ins Suchfeld, vorhandener Text ist markiert."""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def _escape(self, event) -> None:
        """Esc im Suchfeld mit Text leert die Suche, sonst schließt es."""
        if event.widget is self.search_entry and self.search_var.get():
            self.search_var.set("")
        else:
            self.top.destroy()

    def _new_search(self) -> None:
        """Suchtext oder Reiter geändert: alle Treffer markieren, den
        ersten zeigen."""
        for text in self.texts.values():
            text.tag_remove("match", "1.0", "end")
            text.tag_remove("match_current", "1.0", "end")
        self.matches, self.match_index = [], -1
        needle = self.search_var.get().strip()
        if not needle:
            self.search_info_var.set(tr("Strg+F, Enter: nächster Treffer"))
            return
        text = self._current_text()
        start = "1.0"
        while True:
            pos = text.search(needle, start, stopindex="end", nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(needle)}c"
            text.tag_add("match", pos, end)
            self.matches.append(pos)
            start = end
        self.find(1)

    def find(self, direction: int) -> None:
        """Zum nächsten (1) oder vorigen (−1) Treffer springen."""
        if not self.matches:
            if self.search_var.get().strip():
                self._say_result(tr("nicht gefunden"))
            return
        text = self._current_text()
        needle = len(self.search_var.get().strip())
        text.tag_remove("match_current", "1.0", "end")
        self.match_index = (self.match_index + direction) % len(self.matches)
        pos = self.matches[self.match_index]
        text.tag_add("match_current", pos, f"{pos}+{needle}c")
        text.see(pos)
        self._say_result(tr("Treffer {n} von {total}").format(n=self.match_index + 1, total=len(self.matches)))

    def _say_result(self, message: str) -> None:
        self.search_info_var.set(message)
        announcer.say(message)
