"""Gemeinsames Tk-Element für Trefferquote, effektives Tempo und die
Fehlertabelle je Zeichen. Dient sowohl der Statistik eines laufenden
Durchgangs als auch der Gesamtstatistik, damit das Layout einheitlich ist
und nicht doppelt gebaut wird."""
import tkinter as tk
from tkinter import ttk

from morsetrainer.core import stats
from morsetrainer.core.morse import display_text
from morsetrainer.i18n import number, tr
from morsetrainer.widgets import theme


def comparison_text(comparison: dict) -> str:
    """„Letzte 7 Tage: Reaktion 0,48 s, 92 % richtig · die 30 Tage davor:
    0,61 s, 88 %“ (stats.period_comparison); leer ohne Durchgänge."""
    def numbers(period):
        accuracy, latency, _ = stats.period_numbers(period)
        parts = [] if latency is None else [tr("Reaktion {s} s").format(s=number(latency, 2))]
        return parts + ([] if accuracy is None else [tr("{pct} % richtig").format(pct=number(accuracy, 0))])

    recent, before = numbers(comparison[stats.RECENT]), numbers(comparison[stats.BEFORE])
    if not recent and not before:
        return ""
    head = tr("Letzte {days} Tage").format(days=stats.COMPARE_DAYS)
    text = f"{head}: " + (", ".join(recent) if recent else tr("nicht geübt"))
    if before:
        text += " · " + tr("die {days} Tage davor").format(days=stats.BEFORE_DAYS) + ": " + ", ".join(before)
    return text


def trend_text(trend) -> str:
    """„0,61 → 0,48“ (Median der Reaktion davor → jetzt) oder „–“."""
    return "–" if trend is None else f"{number(trend[0], 2)} → {number(trend[1], 2)}"


class StatsPanel:
    """Statistik eines Durchgangs bzw. die Gesamtstatistik: richtig/gesamt,
    effektives Tempo und Tabelle je Zeichen mit Verwechslungen. `compare`
    (Gesamtstatistik): dazu die letzten Tage gegen die davor, gesamt und je
    Zeichen."""
    def __init__(self, parent, title=None, tree_height=8, show_save_label=True, compare=False):
        box = theme.card(parent, title or tr("Statistik (aktueller Durchgang)"))
        summary = ttk.Frame(box)
        summary.pack(fill="x", pady=(0, 6))
        self.stats_var = tk.StringVar(value="0 / 0 (0 %)")
        ttk.Label(summary, textvariable=self.stats_var, style="Score.TLabel").pack(side="left")
        self.speed_var = tk.StringVar(value=tr("Ø effektive Geschwindigkeit: –"))
        ttk.Label(summary, textvariable=self.speed_var).pack(side="left", padx=(16, 0))
        self.compare_var = tk.StringVar(value="")
        if compare:
            # Ohne Durchgänge leer und ausgeblendet (sonst bliebe eine Lücke).
            label = theme.fit_wrap(ttk.Label(box, textvariable=self.compare_var, justify="left"), 560)
            self.compare_var.trace_add("write", lambda *_: label.pack(after=summary, anchor="w", pady=(0, 6))
                                       if self.compare_var.get() else label.pack_forget())

        theme.hint(box, text=tr("Zeichen, nach Fehlern sortiert")).pack(anchor="w")
        columns = ("char", "good", "wrong", "avg_rt", "avg_wpm", "confusions")
        if compare:
            columns = columns[:4] + ("trend",) + columns[4:]
        self.compare = compare
        self.char_tree = ttk.Treeview(box, columns=columns, show="headings", height=tree_height)
        headings = {
            "char": tr("Zeichen", context="Spalte"), "good": tr("Richtig"), "wrong": tr("Falsch"),
            "avg_rt": tr("Ø Reaktion (s)"), "avg_wpm": tr("Ø WPM"), "confusions": tr("Verwechselt mit"),
            "trend": tr("davor → jetzt (s)"),
        }
        widths = {"char": 60, "good": 60, "wrong": 55, "avg_rt": 75, "avg_wpm": 60, "confusions": 140, "trend": 110}
        for col in columns:
            self.char_tree.heading(col, text=headings[col])
            self.char_tree.column(col, anchor="w" if col == "confusions" else "center")
        self.char_tree.pack(fill="x", pady=(2, 0))
        theme.fit_columns(self.char_tree, widths)
        theme.hint(box, wrap=520, text=tr(
            "Ø Reaktion: Zeit vom letzten Punkt oder Strich bis zu deiner Taste, Ø WPM: Tempo ab Beginn des "
            "Zeichens (beides nur richtige Antworten). „–“: nicht gemessen, etwa beim Kopfhören.")).pack(
            anchor="w", pady=(2, 0))
        if compare:
            theme.hint(box, wrap=520, text=tr(
                "Reaktion in der Vergleichszeile und in „davor → jetzt“ nur aus Einzelzeichen; kleiner ist "
                "schneller. Davor: die {before} Tage vor den letzten {days}. Die Spalte zeigt den Median, erst "
                "ab {count} Messungen auf jeder Seite (sonst „–“).").format(
                before=stats.BEFORE_DAYS, days=stats.COMPARE_DAYS, count=stats.MIN_TREND_COUNT)).pack(
                anchor="w", pady=(2, 0))

        self.save_var = tk.StringVar(value="")
        if show_save_label:
            theme.hint(box, textvariable=self.save_var).pack(anchor="w", pady=(4, 0))

    def reset(self):
        """Leert Anzeige und Tabelle (neuer Durchgang)."""
        self.stats_var.set("0 / 0 (0 %)")
        self.speed_var.set(tr("Ø effektive Geschwindigkeit: –"))
        self.compare_var.set("")
        self.save_var.set("")
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)

    def refresh(self, summary: dict, rows: list, comparison=None):
        """Zeigt `summary` (wie SessionStats.summary()) und die Zeilen `rows` (wie
        char_rows()) an, mit `compare` dazu `comparison`
        (stats.period_comparison)."""
        self.stats_var.set(f"{summary['correct']} / {summary['total']} ({summary['accuracy_pct']:.0f} %)")
        speed = tr("Ø effektive Geschwindigkeit: {wpm} WPM").format(wpm=number(summary["avg_effective_wpm"], 1))
        if summary.get("cpm"):
            speed += tr(" · {cpm:.0f} ZpM gemessen").format(cpm=summary["cpm"])
        self.speed_var.set(speed)
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)
        # Reaktion: vom Ende des Zeichens bis zur Eingabe (stats.measured_latency);
        # Reaktion und Tempo nur aus richtigen Antworten. „–“, solange es dafür
        # keinen Wert gibt (Kopfhören, nur Fehler …).
        for char, good, wrong, _total, reaction, avg_wpm, confusions in rows:
            reaction = number(reaction, 2) if reaction is not None else "–"
            avg_wpm = number(avg_wpm, 1) if avg_wpm is not None else "–"
            values = [display_text(char), good, wrong, reaction, avg_wpm, confusions]
            if self.compare:
                values.insert(4, trend_text(stats.char_trend(comparison["chars"], char) if comparison else None))
            self.char_tree.insert("", "end", values=values)
        if self.compare:
            self.compare_var.set(comparison_text(comparison) if comparison else "")

    def show_saved(self, session_number, error=None):
        """`session_number`: Nummer des gespeicherten Durchgangs (SessionStats.finalize)."""
        if error:
            self.save_var.set(tr("Protokoll nicht gespeichert: {error}").format(error=error))
        elif session_number is not None:
            self.save_var.set(tr("Gespeichert (Durchgang {number})").format(number=session_number))