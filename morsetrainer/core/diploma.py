"""Druckbares Diplom in Urkunden-Optik: Rahmen, Siegel in der Farbe der
Stufe, Diplomname, Rufzeichen und Datum. Erzeugt wird eine HTML-Seite,
die der Browser druckt (A4 quer), wie beim Antwortbogen."""
import html

# Farben der Siegel: Bronze, Silber, Gold, Platin (Fläche, Rand).
SEAL_COLORS = (("#c98a4b", "#8a5524"), ("#c9ced4", "#868c94"), ("#e3b53b", "#a77d0d"), ("#b9cdd6", "#6f8a96"))
SEAL_PLAIN = ("#9fb7d9", "#2a6fd0")  # Diplome ohne Stufen


def seal_colors(level, levels: bool = True) -> tuple:
    return SEAL_COLORS[level] if levels else SEAL_PLAIN


def diploma_html(name: str, level_name: str, colors: tuple, condition: str, date_text: str,
                 call: str = "", holder: str = "", labels: dict = None) -> str:
    """HTML-Seite eines Diploms. `level_name` leer bei Diplomen ohne Stufen;
    `call` (groß) und `holder` (Name, darunter) beide leer: ohne
    Empfängerzeile. `labels` liefert die (übersetzten) Texte "title",
    "awarded", "date", "footer"."""
    labels = labels or {}
    esc = html.escape
    fill, edge = colors
    recipient = ""
    if call or holder:
        recipient = f'<p class="awarded">{esc(labels.get("awarded", ""))}</p>'
        if call:
            recipient += f'<p class="call">{esc(call)}</p>'
        if holder:
            recipient += f'<p class="holder">{esc(holder)}</p>'
    seal_text = esc(level_name) if level_name else "★"
    title = f"{name} – {level_name}" if level_name else name
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
@page {{ size: A4 landscape; margin: 10mm; }}
html, body {{ margin: 0; background: #fff; color: #1d2127; }}
body {{ font-family: Georgia, "DejaVu Serif", serif; }}
.sheet {{ box-sizing: border-box; width: 277mm; height: 190mm; margin: 0 auto; padding: 4mm;
          border: 2.5mm double #5b4a2e; }}
.inner {{ box-sizing: border-box; height: 100%; border: 0.4mm solid #5b4a2e; padding: 12mm 18mm;
          display: flex; flex-direction: column; align-items: center; text-align: center; }}
.program {{ font-size: 13pt; letter-spacing: 0.3em; text-transform: uppercase; margin: 0; color: #5b4a2e; }}
h1 {{ font-size: 38pt; font-weight: normal; margin: 4mm 0 2mm; letter-spacing: 0.08em; }}
h2 {{ font-size: 24pt; font-weight: normal; font-style: italic; margin: 0 0 6mm; }}
.awarded {{ font-size: 12pt; margin: 0; }}
.call {{ font-family: "DejaVu Sans Mono", monospace; font-size: 26pt; font-weight: bold; letter-spacing: 0.1em;
         margin: 1mm 0 4mm; }}
.holder {{ font-size: 18pt; font-style: italic; margin: 0 0 4mm; }}
.call + .holder {{ margin-top: -2mm; }}
.awarded + .holder {{ font-size: 26pt; margin: 1mm 0 4mm; }}
.condition {{ font-size: 12pt; max-width: 190mm; margin: 0 0 4mm; }}
.seal {{ width: 34mm; height: 34mm; border-radius: 50%; display: flex; align-items: center;
         justify-content: center; background: {fill}; border: 1.6mm solid {edge};
         box-shadow: inset 0 0 0 1.2mm #fff6; font-size: 13pt; font-weight: bold; color: #1d2127;
         -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.bottom {{ margin-top: auto; width: 100%; display: flex; justify-content: space-between; align-items: flex-end;
           font-size: 11pt; }}
.line {{ border-top: 0.3mm solid #1d2127; padding-top: 1mm; min-width: 55mm; }}
</style></head><body>
<div class="sheet"><div class="inner">
<p class="program">Morsetrainer</p>
<h1>{esc(labels.get("title", "Diplom"))}</h1>
<h2>{esc(name)}</h2>
{recipient}
<p class="condition">{esc(condition)}</p>
<div class="bottom">
<div class="line">{esc(labels.get("date", ""))} {esc(date_text)}</div>
<div class="seal">{seal_text}</div>
<div class="line">{esc(labels.get("footer", ""))}</div>
</div>
</div></div>
</body></html>
"""
