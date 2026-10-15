"""Zustand von Bedienelementen, gleich ob ttk- oder klassisches Tk-Widget.

Tk 9.1 ersetzt bei laufendem Screenreader ttk::checkbutton, ttk::radiobutton,
ttk::spinbox und (unter X11) ttk::scale durch die klassischen Widgets
(library/accessibility.tcl). Das Python-Objekt bleibt ein ttk-Objekt, der
Tk-Befehl dahinter kennt dann aber weder `state` noch `instate`, und
winfo_class() liefert „Checkbutton“ statt „TCheckbutton“. Ohne diese
Hilfen bräche das Sperren und die eigene Ansage ausgerechnet bei
Screenreader-Nutzern. Mit Tk 8.6 und 9.0 ändert sich nichts."""
import tkinter as tk

# Klassische Klasse → entsprechende ttk-Klasse.
CLASSIC = {"Checkbutton": "TCheckbutton", "Radiobutton": "TRadiobutton", "Spinbox": "TSpinbox",
           "Scale": "TScale"}


def widget_class(widget) -> str:
    """winfo_class(), klassische Widgets unter dem Namen der ttk-Klasse."""
    cls = widget.winfo_class()
    return CLASSIC.get(cls, cls)


def is_classic(widget) -> bool:
    return widget.winfo_class() in CLASSIC


def set_enabled(widget, enabled: bool) -> None:
    """Bedienbar machen bzw. sperren."""
    if is_classic(widget):
        widget.configure(state="normal" if enabled else "disabled")
    else:
        widget.state(["!disabled"] if enabled else ["disabled"])


def is_enabled(widget) -> bool:
    if is_classic(widget):
        return str(widget.cget("state")) != "disabled"
    return widget.instate(["!disabled"])


def is_selected(widget) -> bool:
    """Schalter an bzw. Optionsfeld gewählt."""
    if not is_classic(widget):
        return widget.instate(["selected"])
    variable = str(widget.cget("variable"))
    if not variable:
        return False
    try:
        current = str(widget.getvar(variable))
    except tk.TclError:
        return False
    wanted = widget.cget("onvalue") if widget.winfo_class() == "Checkbutton" else widget.cget("value")
    return current == str(wanted)
