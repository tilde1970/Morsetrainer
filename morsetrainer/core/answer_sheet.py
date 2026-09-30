"""Druckbarer Antwortbogen zum Mitschreiben auf Papier (Netzwerk-Reiter,
fester Takt): nummerierte Zeilen, spaltenweise von oben nach unten wie in
der Auflösung, bei Gruppen und Einzelzeichen je Zeichen ein Kästchen.
Erzeugt wird eine HTML-Seite, die der Browser druckt (A4)."""
import html

# Zeilen je Spalte und Spalten je Seite, nach Breite einer Zeile.
ROWS_PER_COLUMN = 25
MAX_BOXES = 10


def columns_for(boxes) -> int:
    """Spalten je Seite: Kästchen brauchen je 7 mm, eine freie Zeile so
    viel Platz wie ein Wort oder ein Rufzeichen."""
    if boxes is None:
        return 2
    return 4 if boxes <= 2 else 3 if boxes <= 6 else 2


def pages(count: int, columns: int, rows: int = ROWS_PER_COLUMN):
    """Nummern je Seite und Spalte: [[[1, 2, …, 25], [26, …]], …]."""
    per_page = rows * columns
    result = []
    for first in range(1, count + 1, per_page):
        numbers = list(range(first, min(first + per_page, count + 1)))
        result.append([numbers[i:i + rows] for i in range(0, len(numbers), rows)])
    return result


def answer_sheet_html(count: int, boxes=None, title="", details="", labels=None) -> str:
    """HTML-Seite mit `count` Zeilen; `boxes`: Kästchen je Zeile (Gruppen,
    Einzelzeichen) oder None für eine freie Linie. `title` und `details`
    stehen im Kopf, `labels` liefert die (übersetzten) Beschriftungen
    "name", "date", "hint"."""
    labels = labels or {}
    if boxes is not None:
        boxes = max(1, min(int(boxes), MAX_BOXES))
    columns = columns_for(boxes)
    if boxes is None:
        cell = '<span class="line"></span>'
    else:
        cell = '<span class="box"></span>' * boxes
    head = (f'<header><h1>{html.escape(title)}</h1><p class="details">{html.escape(details)}</p>'
            f'<p class="fields"><span>{html.escape(labels.get("name", "Name"))}:</span><span class="fill"></span>'
            f'<span>{html.escape(labels.get("date", "Datum"))}:</span><span class="fill short"></span></p>'
            f'<p class="hint">{html.escape(labels.get("hint", ""))}</p></header>')
    body = []
    for page in pages(count, columns):
        cols = []
        for numbers in page:
            rows = "".join(f'<div class="row"><span class="n">{n}.</span>{cell}</div>' for n in numbers)
            cols.append(f'<div class="col">{rows}</div>')
        body.append(f'<section class="page">{head}<div class="cols">{"".join(cols)}</div></section>')
        head = ""  # Kopf nur auf der ersten Seite
    width = max(len(str(count)), 1) + 1
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
@page {{ size: A4; margin: 12mm; }}
body {{ font-family: sans-serif; color: #000; background: #fff; margin: 0; }}
.page {{ break-after: page; }}
.page:last-child {{ break-after: auto; }}
h1 {{ font-size: 16pt; margin: 0 0 1mm; }}
.details, .hint {{ font-size: 10pt; margin: 0 0 2mm; }}
.fields {{ display: flex; gap: 3mm; align-items: flex-end; font-size: 11pt; margin: 4mm 0 3mm; }}
.fill {{ flex: 1; border-bottom: 1px solid #000; }}
.fill.short {{ flex: 0 0 35mm; }}
.cols {{ display: flex; gap: 6mm; }}
.col {{ flex: 1; }}
.row {{ display: flex; align-items: flex-end; height: 9.2mm; }}
.n {{ font-family: monospace; font-size: 11pt; width: {width}ch; text-align: right; margin-right: 2mm;
      flex: none; }}
.box {{ width: 6.5mm; height: 7.5mm; border: 1px solid #666; margin-right: 0.5mm; flex: none; }}
.line {{ flex: 1; border-bottom: 1px solid #666; height: 7mm; }}
</style></head><body>
{"".join(body)}
</body></html>
"""
