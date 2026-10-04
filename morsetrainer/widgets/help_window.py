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
from morsetrainer.widgets import theme

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
        if cls._open is not None and cls._open.top.winfo_exists():
            cls._open.top.deiconify()
            cls._open.top.lift()
            return
        cls._open = cls(root)

    def __init__(self, root):
        self.top = tk.Toplevel(root)
        self.top.title(tr("Morsetrainer – Hilfe"))
        self.top.configure(background=theme.BG)
        self.top.geometry("760x640")
        notebook = ttk.Notebook(self.top)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
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
            try:
                content = doc_path(name).read_text(encoding="utf-8")
            except OSError:
                content = tr("{name} wurde nicht gefunden.").format(name=name)
            render(text, content)
            self.texts[name] = text
        ttk.Button(self.top, text=tr("Schließen"), command=self.top.destroy).pack(anchor="e", padx=8, pady=(0, 8))
        self.top.bind("<Escape>", lambda e: self.top.destroy())
