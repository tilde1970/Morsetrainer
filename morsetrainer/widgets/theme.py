"""Einheitliches Aussehen: ttk-Theme auf Basis von "clam" mit eigener
Farbpalette, benannten Schriften und ein paar Stilvarianten.

apply() wird einmal nach dem Erzeugen des Hauptfensters aufgerufen, vor
dem Aufbau der Reiter. Die Reiter verwenden danach nur noch die Namen
hier (Stile, Schriften, Farben) statt eigener Schrift- und Farbangaben.

Stile:
    Accent.TButton    Hauptaktion eines Reiters (Start, Neues QSO)
    Hint.TLabel       Erklärtext, Einheiten, Nebeninfos (gedämpft)
    Status.TLabel     Statuszeile eines Reiters ("Bereit. Drücke Start.")
    Feedback.TLabel   große Rückmeldung (Richtig/Falsch), Farbe per foreground
    Score.TLabel      fette Zwischenstände (Punkte, x / y richtig)
    Footer.TLabel     Fußzeile"""
from tkinter import font as tkfont
from tkinter import ttk

# Palette (hell). Gedämpfte Flächen, ein Akzent, Grün/Rot nur für Ergebnisse.
BG = "#f3f4f6"
SURFACE = "#ffffff"
BORDER = "#d3d7de"
BUTTON = "#e8eaee"
BUTTON_ACTIVE = "#dde1e7"
TEXT = "#1d2127"
MUTED = "#5f6670"
DISABLED = "#a0a6ae"
ACCENT = "#2a6fd0"
ACCENT_ACTIVE = "#215bb0"
SELECT = "#d7e6fa"
OK = "#1e7e34"
ERROR = "#c0392b"
OK_BG = "#d9f2dd"
ERROR_BG = "#f9dcd9"

# Benannte Schriften (erst nach apply() verwendbar).
MONO = "MtMono"             # Mitschrift, Verlauf, Notizen
MONO_LARGE = "MtMonoLarge"  # Gegenüberstellung gesendet/getippt
MONO_ENTRY = "MtMonoEntry"  # Eingabefelder im Contest
STATUS = "MtStatus"
FEEDBACK = "MtFeedback"
SCORE = "MtScore"
SMALL = "MtSmall"
SMALL_ITALIC = "MtSmallItalic"
HEADING = "MtHeading"
# Ein Font-Objekt löscht seine benannte Schrift, sobald es eingesammelt
# wird; daher hier festhalten.
_fonts = []


def _named_fonts(root) -> None:
    base = tkfont.nametofont("TkDefaultFont", root=root)
    family = base.actual("family")
    size = max(base.actual("size"), 10)
    base.configure(size=size)
    tkfont.nametofont("TkTextFont", root=root).configure(size=size)
    mono = tkfont.nametofont("TkFixedFont", root=root).actual("family")
    for name, fam, sz, extra in (
        (MONO, mono, size + 1, {}),
        (MONO_LARGE, mono, size + 3, {}),
        (MONO_ENTRY, mono, size + 6, {}),
        (STATUS, family, size + 3, {}),
        (FEEDBACK, family, size + 8, {"weight": "bold"}),
        (SCORE, family, size + 2, {"weight": "bold"}),
        (SMALL, family, size - 1, {}),
        (SMALL_ITALIC, family, size - 1, {"slant": "italic"}),
        (HEADING, family, size, {"weight": "bold"}),
    ):
        _fonts.append(tkfont.Font(root=root, name=name, family=fam, size=sz, exists=False, **extra))


def apply(root) -> None:
    _named_fonts(root)
    root.configure(background=BG)
    # Klassische Tk-Widgets (Text, Canvas, Klappliste der Combobox).
    root.option_add("*Text.background", SURFACE)
    root.option_add("*Text.foreground", TEXT)
    root.option_add("*Text.relief", "flat")
    root.option_add("*Text.highlightThickness", 1)
    root.option_add("*Text.highlightBackground", BORDER)
    root.option_add("*Text.highlightColor", ACCENT)
    root.option_add("*Text.selectBackground", SELECT)
    root.option_add("*Canvas.background", BG)
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".", background=BG, foreground=TEXT, bordercolor=BORDER, darkcolor=BG, lightcolor=BG,
        troughcolor=BUTTON, focuscolor=ACCENT, selectbackground=SELECT, selectforeground=TEXT,
        insertcolor=TEXT, font="TkDefaultFont",
    )
    style.map(".", foreground=[("disabled", DISABLED)])

    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG)
    style.configure("Hint.TLabel", foreground=MUTED)
    style.configure("Status.TLabel", font=STATUS)
    style.configure("Feedback.TLabel", font=FEEDBACK)
    style.configure("Score.TLabel", font=SCORE)
    style.configure("Footer.TLabel", foreground=MUTED, font=SMALL)

    style.configure("TLabelframe", background=BG, bordercolor=BORDER, relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=MUTED, font=HEADING)

    style.configure("TButton", background=BUTTON, bordercolor=BORDER, lightcolor=BUTTON, darkcolor=BUTTON,
                    padding=(10, 2), anchor="center")
    style.map("TButton",
              background=[("disabled", BG), ("pressed", BUTTON_ACTIVE), ("active", BUTTON_ACTIVE)],
              lightcolor=[("disabled", BG), ("active", BUTTON_ACTIVE)],
              darkcolor=[("disabled", BG), ("active", BUTTON_ACTIVE)],
              bordercolor=[("focus", ACCENT)])
    style.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=HEADING, padding=(18, 4))
    style.map("Accent.TButton",
              background=[("disabled", BUTTON), ("pressed", ACCENT_ACTIVE), ("active", ACCENT_ACTIVE)],
              lightcolor=[("disabled", BUTTON), ("active", ACCENT_ACTIVE)],
              darkcolor=[("disabled", BUTTON), ("active", ACCENT_ACTIVE)],
              foreground=[("disabled", DISABLED)],
              bordercolor=[("disabled", BORDER), ("focus", ACCENT_ACTIVE)])
    # Flacher Knopf ohne Rahmen, z. B. zum Auf-/Zuklappen.
    style.configure("Flat.TButton", background=BG, bordercolor=BG, lightcolor=BG, darkcolor=BG,
                    foreground=ACCENT, padding=(2, 2))
    style.map("Flat.TButton", background=[("active", BUTTON)], lightcolor=[("active", BUTTON)],
              darkcolor=[("active", BUTTON)], bordercolor=[("active", BUTTON)])

    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(widget, fieldbackground=SURFACE, background=BUTTON, bordercolor=BORDER,
                        lightcolor=SURFACE, darkcolor=SURFACE, arrowcolor=MUTED, padding=(4, 2))
        style.map(widget, bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
                  fieldbackground=[("disabled", BG), ("readonly", SURFACE)],
                  background=[("active", BUTTON_ACTIVE)])
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE), ("disabled", BG)],
              selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", TEXT)])

    for widget in ("TCheckbutton", "TRadiobutton"):
        style.configure(widget, background=BG, indicatorbackground=SURFACE, indicatorforeground=ACCENT,
                        upperbordercolor=MUTED, lowerbordercolor=MUTED, padding=(0, 2))
        style.map(widget, background=[("active", BG)],
                  indicatorbackground=[("disabled", BG), ("pressed", SELECT), ("selected", SURFACE)])

    style.configure("TScale", background=BUTTON, troughcolor=BORDER, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON)
    style.map("TScale", background=[("disabled", BG), ("active", ACCENT)])
    style.configure("TScrollbar", background=BUTTON, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                    lightcolor=BUTTON, darkcolor=BUTTON)
    style.map("TScrollbar", background=[("active", BUTTON_ACTIVE)])
    style.configure("TSeparator", background=BORDER)

    style.configure("TNotebook", background=BG, bordercolor=BORDER, tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=BUTTON, foreground=MUTED, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON, padding=(6, 3))
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", BUTTON_ACTIVE)],
              lightcolor=[("selected", BG)],
              darkcolor=[("selected", BG)],
              foreground=[("selected", TEXT), ("disabled", DISABLED)],
              expand=[("selected", (1, 1, 1, 0))])

    row_height = tkfont.nametofont("TkDefaultFont", root=root).metrics("linespace") + 8
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE, rowheight=row_height)
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background=BUTTON, foreground=MUTED, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON, font=HEADING, padding=(4, 3))
    style.map("Treeview.Heading", background=[("active", BUTTON_ACTIVE)])


def hint(parent, text=None, textvariable=None, wrap=None, **kwargs) -> ttk.Label:
    """Gedämpfter Erklärtext; mit `wrap` (Pixel) mehrzeilig, linksbündig."""
    if text is not None:
        kwargs["text"] = text
    if textvariable is not None:
        kwargs["textvariable"] = textvariable
    if wrap:
        kwargs.update(wraplength=wrap, justify="left")
    return ttk.Label(parent, style="Hint.TLabel", **kwargs)


def card(parent, text: str, **pack) -> ttk.LabelFrame:
    """Umrandete Gruppe mit Titel, schon gepackt (Standard: volle Breite)."""
    box = ttk.LabelFrame(parent, text=text, padding=(8, 4, 8, 8))
    box.pack(**({"fill": "x", "padx": 10, "pady": 5} | pack))
    return box

