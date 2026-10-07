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
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# Paletten. Hell: gedämpfte Flächen, ein Akzent, Grün/Rot nur für
# Ergebnisse. Hoher Kontrast (Barrierefreiheit, für Sehbehinderte): Schwarz,
# Weiß und Gelb, kräftige Rahmen; jede Textfarbe hat auf ihrem Grund
# mindestens 7:1 (WCAG AAA). Gewählt wird vor apply() mit set_palette();
# die Reiter lesen die Farben zur Laufzeit als theme.X.
PALETTES = {
    "light": {
        "BG": "#f3f4f6", "SURFACE": "#ffffff", "BORDER": "#d3d7de", "BUTTON": "#e8eaee",
        "BUTTON_ACTIVE": "#dde1e7", "TEXT": "#1d2127", "MUTED": "#5f6670", "DISABLED": "#a0a6ae",
        "ACCENT": "#2a6fd0", "ACCENT_ACTIVE": "#215bb0",
        "FOCUS": "#8db4ea",  # Rahmen des Eingabefelds mit Tastaturfokus
        "SELECT": "#d7e6fa", "OK": "#1e7e34", "ERROR": "#c0392b", "OK_BG": "#d9f2dd", "ERROR_BG": "#f9dcd9",
        "GRID": "#e4e6ea",  # Hilfslinien in Diagrammen
        "TROUGH": "#d3d7de",  # Schiene der Schieberegler
        # QSO: Station 1 bzw. Run-Station, dann abwechselnd die Gegenstationen.
        "STATION_COLORS": ("#1f5fbf", "#b35900", "#2e8b57"),
        "BORDER_WIDTH": 1,
    },
    "contrast": {
        "BG": "#000000", "SURFACE": "#000000", "BORDER": "#ffffff", "BUTTON": "#1a1a1a",
        "BUTTON_ACTIVE": "#333333", "TEXT": "#ffffff", "MUTED": "#e0e0e0", "DISABLED": "#9e9e9e",
        "ACCENT": "#ffd400", "ACCENT_ACTIVE": "#ffe766", "FOCUS": "#ffd400", "SELECT": "#00468c",
        "OK": "#6cf06c", "ERROR": "#ff8080", "OK_BG": "#003d00", "ERROR_BG": "#5c0000",
        "GRID": "#5a5a5a", "TROUGH": "#4d4d4d", "STATION_COLORS": ("#80c8ff", "#ffb84d", "#7cfc9a"),
        "BORDER_WIDTH": 2,
    },
}
PALETTE = "light"
globals().update(PALETTES[PALETTE])


def set_palette(name: str) -> None:
    """Palette wählen (vor apply(), also beim Programmstart)."""
    global PALETTE
    PALETTE = name if name in PALETTES else "light"
    globals().update(PALETTES[PALETTE])

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

# Schriftgröße im Programm (Barrierefreiheit): Prozent der Größe bei
# apply(). Alle Tk- und benannten Schriften wachsen mit, ebenso die
# Zeilenhöhe der Tabellen und die Umbruchbreite mehrzeiliger Texte.
# Unter 100 % für kleine Bildschirme (Netbook, Beamer mit wenig Auflösung).
ZOOM_STEPS = (75, 90, 100, 110, 125, 150, 175, 200)
NORMAL_ZOOM = 100  # Grundeinstellung, Strg+0
_STD_FONTS = ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
              "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont")
_base_sizes = {}  # Schriftname -> Größe bei 100 %
INDICATOR_SIZE = 10  # Kästchen von Schaltern bei 100 % (wie clam)
ARROW_SIZE = 14  # Pfeile, Breite der Rollbalken, Dicke der Schieberegler bei 100 % (wie clam)
SLIDER_LENGTH = 30  # Griff der Schieberegler bei 100 % (wie clam)
_scale = 100


def _named_fonts(root) -> None:
    """Legt die benannten Schriften (MONO, STATUS, FEEDBACK …) an, abgeleitet
    von der Systemschrift (mindestens 10 pt), und merkt ihre Grundgrößen für
    die Schriftgröße."""
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
    global _scale
    _scale = 100
    _base_sizes.clear()
    for name in _STD_FONTS + (MONO, MONO_LARGE, MONO_ENTRY, STATUS, FEEDBACK, SCORE, SMALL, SMALL_ITALIC, HEADING):
        try:
            named = tkfont.nametofont(name, root=root)
        except tk.TclError:
            continue
        _base_sizes[name] = int(named.cget("size")) or named.actual("size")


def scale() -> int:
    """Aktuelle Schriftgröße in Prozent."""
    return _scale


def scaled(pixels: int) -> int:
    """Pixelmaß (z. B. Umbruchbreite) für die aktuelle Schriftgröße."""
    return round(pixels * _scale / 100)


def scaled_size(size: int, low: int, high: int) -> int:
    """Startgröße einer eigenen Schrift (Fenster mit eigenem A−/A+) für die
    aktuelle Schriftgröße, begrenzt auf `low` … `high`."""
    return min(max(scaled(size), low), high)


def scaled_geometry(window, width: int, height: int) -> str:
    """Fenstergröße „BxH“ für die aktuelle Schriftgröße, höchstens so groß
    wie der Bildschirm erlaubt."""
    return (f"{min(scaled(width), window.winfo_screenwidth() - 40)}"
            f"x{min(scaled(height), window.winfo_screenheight() - 80)}")


def set_scale(root, percent: int) -> None:
    """Schriftgröße für das ganze Programm (ZOOM_STEPS[0] … [-1] Prozent)."""
    global _scale
    _scale = min(max(int(percent), ZOOM_STEPS[0]), ZOOM_STEPS[-1])
    for name, size in _base_sizes.items():
        tkfont.nametofont(name, root=root).configure(size=round(size * _scale / 100))
    _row_height(ttk.Style(root), root)
    scale_wraps(root)


def zoom_step(percent: int, direction: int) -> int:
    """Nächste Stufe aus ZOOM_STEPS nach oben (+1) oder unten (−1)."""
    if direction > 0:
        return next((step for step in ZOOM_STEPS if step > percent), ZOOM_STEPS[-1])
    return next((step for step in reversed(ZOOM_STEPS) if step < percent), ZOOM_STEPS[0])


def scale_wraps(widget) -> None:
    """Umbruchbreiten unter `widget` an die Schriftgröße anpassen; die
    ursprüngliche Breite merkt sich jedes Widget beim ersten Mal."""
    for child in widget.winfo_children():
        base = getattr(child, "_mt_wrap", None)
        if base is None:
            try:
                base = int(float(str(child.cget("wraplength"))))
            except (tk.TclError, ValueError):
                base = 0
            child._mt_wrap = base
        if base:
            child.configure(wraplength=scaled(base))
        scale_wraps(child)


def _row_height(style, root) -> None:
    """Maße, die nicht von selbst mit der Schrift wachsen: Tabellenzeilen,
    die Kästchen von Schaltern, Pfeile von Zahlenfeldern und Klapplisten,
    Rollbalken und Schieberegler."""
    row_height = tkfont.nametofont("TkDefaultFont", root=root).metrics("linespace") + 8
    style.configure("Treeview", rowheight=row_height)
    for widget in ("TCheckbutton", "TRadiobutton"):
        style.configure(widget, indicatorsize=scaled(INDICATOR_SIZE))
    for widget in ("TSpinbox", "TCombobox", "TScrollbar", "TScale"):
        style.configure(widget, arrowsize=scaled(ARROW_SIZE))
    style.configure("TScale", sliderlength=scaled(SLIDER_LENGTH))


def apply(root) -> None:
    """Wendet Farben, Schriften und Stile des gewählten Farbschemas auf das
    ganze Programm an (einmal beim Start, vor dem Aufbau der Fenster)."""
    _named_fonts(root)
    root.configure(background=BG)
    # Klassische Tk-Widgets (Text, Canvas, Klappliste der Combobox).
    root.option_add("*Text.background", SURFACE)
    root.option_add("*Text.foreground", TEXT)
    root.option_add("*Text.relief", "flat")
    root.option_add("*Text.highlightThickness", BORDER_WIDTH)
    root.option_add("*Text.insertBackground", TEXT)
    root.option_add("*Text.selectForeground", TEXT)
    root.option_add("*Text.highlightBackground", BORDER)
    root.option_add("*Text.highlightColor", FOCUS)
    root.option_add("*Text.selectBackground", SELECT)
    root.option_add("*Canvas.background", BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    # Knöpfe und Schalter sind per Tab erreichbar (Tastaturbedienung), nehmen
    # beim Anklicken mit der Maus aber keinen Fokus: Die Leertaste heißt in
    # den Reitern "Wiederholen" und würde sonst den zuletzt angeklickten Knopf
    # auslösen (z. B. Start/Stop).
    try:
        root.tk.eval(
            "proc ::ttk::clickToFocus {w} {"
            " if {[winfo class $w] in {TButton TCheckbutton TRadiobutton}} return;"
            " if {[ttk::takesFocus $w]} { focus $w } }")
    except tk.TclError:
        pass
    # In Textfeldern (Notizen, eigener Text) führt Tab weiter, statt ein
    # Tabzeichen einzufügen; wie Tk selbst über tk::TabToWindow, damit das
    # Ziel <<TraverseIn>> bekommt (Fokus-Ansage).
    root.bind_class("Text", "<Tab>", lambda e: (_tab_to(e.widget.tk_focusNext()), "break")[1])
    for back in ("<Shift-Tab>", "<Shift-ISO_Left_Tab>"):  # X11 meldet Umschalt+Tab als ISO_Left_Tab
        try:
            root.bind_class("Text", back, lambda e: (_tab_to(e.widget.tk_focusPrev()), "break")[1])
        except tk.TclError:
            pass

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".", background=BG, foreground=TEXT, bordercolor=BORDER, darkcolor=BG, lightcolor=BG,
        troughcolor=BUTTON, focuscolor=ACCENT, selectbackground=SELECT, selectforeground=TEXT,
        insertcolor=TEXT, font="TkDefaultFont", focusthickness=2,
    )
    style.map(".", foreground=[("disabled", DISABLED)])

    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG)
    style.configure("Hint.TLabel", foreground=MUTED)
    style.configure("Status.TLabel", font=STATUS)
    style.configure("Feedback.TLabel", font=FEEDBACK)
    style.configure("Score.TLabel", font=SCORE)
    style.configure("Footer.TLabel", foreground=MUTED, font=SMALL)

    style.configure("TLabelframe", background=BG, bordercolor=BORDER, relief="solid", borderwidth=BORDER_WIDTH)
    style.configure("TLabelframe.Label", background=BG, foreground=MUTED, font=HEADING)

    style.configure("TButton", background=BUTTON, bordercolor=BORDER, lightcolor=BUTTON, darkcolor=BUTTON,
                    padding=(10, 2), anchor="center", borderwidth=BORDER_WIDTH)
    # Tastaturfokus deutlich sichtbar: Rahmen innen und außen in der
    # Akzentfarbe (beim Akzent-Knopf in der Schriftfarbe), Schalter mit
    # hinterlegter Beschriftung, Schieberegler mit farbiger Schiene.
    style.map("TButton",
              background=[("disabled", BG), ("pressed", BUTTON_ACTIVE), ("active", BUTTON_ACTIVE)],
              lightcolor=[("disabled", BG), ("focus", ACCENT), ("active", BUTTON_ACTIVE)],
              darkcolor=[("disabled", BG), ("focus", ACCENT), ("active", BUTTON_ACTIVE)],
              bordercolor=[("focus", ACCENT)])
    # Schrift auf dem Akzent: weiß auf Blau, im hohen Kontrast schwarz auf Gelb.
    style.configure("Accent.TButton", background=ACCENT, foreground=SURFACE, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=HEADING, padding=(18, 4))
    style.map("Accent.TButton",
              background=[("disabled", BUTTON), ("pressed", ACCENT_ACTIVE), ("active", ACCENT_ACTIVE)],
              lightcolor=[("disabled", BUTTON), ("focus", TEXT), ("active", ACCENT_ACTIVE)],
              darkcolor=[("disabled", BUTTON), ("focus", TEXT), ("active", ACCENT_ACTIVE)],
              foreground=[("disabled", DISABLED)],
              bordercolor=[("disabled", BORDER), ("focus", TEXT)])
    # Flacher Knopf ohne Rahmen, z. B. zum Auf-/Zuklappen.
    style.configure("Flat.TButton", background=BG, bordercolor=BG, lightcolor=BG, darkcolor=BG,
                    foreground=ACCENT, padding=(2, 2))
    style.map("Flat.TButton", background=[("active", BUTTON)], lightcolor=[("active", BUTTON)],
              darkcolor=[("active", BUTTON)], bordercolor=[("focus", ACCENT), ("active", BUTTON)])

    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(widget, fieldbackground=SURFACE, background=BUTTON, bordercolor=BORDER,
                        lightcolor=SURFACE, darkcolor=SURFACE, arrowcolor=MUTED, padding=(4, 2),
                        borderwidth=BORDER_WIDTH)
        style.map(widget, bordercolor=[("focus", FOCUS)],
                  fieldbackground=[("disabled", BG), ("readonly", SURFACE)],
                  background=[("active", BUTTON_ACTIVE)])
    # clam färbt die Schrift einer fokussierten Klappliste weiß (für ein
    # blaues Feld); unser Feld bleibt weiß, also auch die Schrift dunkel.
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE), ("disabled", BG)],
              foreground=[("disabled", DISABLED), ("readonly", TEXT)],
              selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", TEXT)])

    for widget in ("TCheckbutton", "TRadiobutton"):
        style.configure(widget, background=BG, indicatorbackground=SURFACE, indicatorforeground=ACCENT,
                        upperbordercolor=MUTED, lowerbordercolor=MUTED, padding=(0, 2))
        style.map(widget, background=[("focus", SELECT), ("active", BG)],
                  indicatorbackground=[("disabled", BG), ("pressed", SELECT), ("selected", SURFACE)])

    style.configure("TScale", background=BUTTON, troughcolor=TROUGH, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON)
    style.map("TScale", background=[("disabled", BG), ("active", ACCENT)], troughcolor=[("focus", ACCENT)])
    style.configure("TScrollbar", background=BUTTON, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                    lightcolor=BUTTON, darkcolor=BUTTON)
    style.map("TScrollbar", background=[("active", BUTTON_ACTIVE)])
    style.configure("TSeparator", background=BORDER)

    style.configure("TNotebook", background=BG, bordercolor=BORDER, tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=BUTTON, foreground=MUTED, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON, padding=(5, 3), font=SMALL)
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", BUTTON_ACTIVE)],
              lightcolor=[("selected", BG)],
              darkcolor=[("selected", BG)],
              foreground=[("selected", TEXT), ("disabled", DISABLED)],
              expand=[("selected", (1, 1, 1, 0))])

    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE)
    _row_height(style, root)
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background=BUTTON, foreground=MUTED, bordercolor=BORDER,
                    lightcolor=BUTTON, darkcolor=BUTTON, font=HEADING, padding=(4, 3))
    style.map("Treeview.Heading", background=[("active", BUTTON_ACTIVE)])
    # Später geöffnete Fenster: Umbruchbreiten gleich passend zur Schriftgröße.
    root.bind_class("Toplevel", "<Map>", _on_window_shown, add="+")


def _tab_to(widget) -> None:
    if widget is not None:
        widget.tk.call("tk::TabToWindow", widget)


def _on_window_shown(event) -> None:
    if _scale != 100 and isinstance(event.widget, tk.Toplevel):
        scale_wraps(event.widget)


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

