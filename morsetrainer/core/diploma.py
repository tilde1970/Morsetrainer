"""Druckbares Diplom in Urkunden-Optik: Guilloche-Rahmen, Rosetten,
Diplomname auch in Morsezeichen, Siegel mit Bändern in der Farbe der
Stufe, Rufzeichen und Datum. Erzeugt wird eine HTML-Seite mit
eingebettetem SVG, die der Browser druckt (A4 quer), wie beim
Antwortbogen – ohne Bilder oder Schriften aus dem Netz."""
import html
import math

from morsetrainer.core.morse import MORSE_CODE

# Farben der Siegel: Bronze, Silber, Gold, Platin (Fläche, Rand).
SEAL_COLORS = (("#c98a4b", "#8a5524"), ("#c9ced4", "#868c94"), ("#e3b53b", "#a77d0d"), ("#b9cdd6", "#6f8a96"))
SEAL_PLAIN = ("#9fb7d9", "#2a6fd0")  # Diplome ohne Stufen

# Blatt in mm (A4 quer abzüglich Druckrand); alle SVG-Maße in mm.
WIDTH, HEIGHT = 277, 190
BAND = 9.5      # Abstand der Rahmenmitte vom Blattrand
WAVE = 2.6      # Ausschlag der Rahmenwellen
PAPER = "#fbf7ec"
UMLAUTS = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "ß": "SS"}


def seal_colors(level, levels: bool = True) -> tuple:
    return SEAL_COLORS[level] if levels else SEAL_PLAIN


def _mix(color: str, other: str, share: float) -> str:
    """`color` zu `share` in Richtung `other` verschoben."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * share):02x}" for x, y in zip(a, b))


def _path(points, closed: bool = True) -> str:
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return d + (" Z" if closed else "")


def _rounded_rect_point(s: float, x0, y0, w, h, r):
    """Punkt und nach außen zeigende Normale bei Bogenlänge `s` auf einem
    Rechteck mit runden Ecken (im Uhrzeigersinn ab oben links)."""
    straight = (w - 2 * r, h - 2 * r)
    arc = math.pi * r / 2
    corners = ((x0 + w - r, y0 + r), (x0 + w - r, y0 + h - r), (x0 + r, y0 + h - r), (x0 + r, y0 + r))
    starts = ((x0 + r, y0), (x0 + w, y0 + r), (x0 + w - r, y0 + h), (x0, y0 + h - r))
    dirs = ((1, 0), (0, 1), (-1, 0), (0, -1))
    for side in range(4):
        length = straight[side % 2]
        if s <= length:
            (sx, sy), (dx, dy) = starts[side], dirs[side]
            return sx + dx * s, sy + dy * s, dy, -dx
        s -= length
        if s <= arc:
            angle = -math.pi / 2 + side * math.pi / 2 + s / r
            cx, cy = corners[side]
            nx, ny = math.cos(angle), math.sin(angle)
            return cx + nx * r, cy + ny * r, nx, ny
        s -= arc
    return starts[0][0], starts[0][1], 0, -1


def _border(ink: str, accent: str) -> str:
    """Guilloche-Band um das Blatt: verflochtene Wellenlinien."""
    x0 = y0 = BAND
    w, h, r = WIDTH - 2 * BAND, HEIGHT - 2 * BAND, 6
    perimeter = 2 * (w + h - 4 * r) + 2 * math.pi * r
    waves = round(perimeter / 7)            # ganze Wellenzahl: Linie schließt sich
    steps = int(perimeter / 0.6)
    lines = []
    for k in range(6):
        phase = k * math.pi / 3
        amp = WAVE * (1 if k % 2 == 0 else 0.62)
        points = []
        for i in range(steps):
            s = perimeter * i / steps
            x, y, nx, ny = _rounded_rect_point(s, x0, y0, w, h, r)
            off = amp * math.sin(2 * math.pi * waves * s / perimeter + phase)
            points.append((x + nx * off, y + ny * off))
        color = ink if k % 2 == 0 else accent
        lines.append(f'<path d="{_path(points)}" stroke="{color}" stroke-width="0.22" fill="none"/>')
    inner = BAND + WAVE + 2.2
    outer = BAND - WAVE - 1.2
    frames = (f'<rect x="{outer}" y="{outer}" width="{WIDTH - 2 * outer}" height="{HEIGHT - 2 * outer}" rx="8" '
              f'fill="none" stroke="{ink}" stroke-width="0.5"/>'
              f'<rect x="{inner}" y="{inner}" width="{WIDTH - 2 * inner}" height="{HEIGHT - 2 * inner}" rx="4" '
              f'fill="none" stroke="{ink}" stroke-width="0.7"/>'
              f'<rect x="{inner + 1.4}" y="{inner + 1.4}" width="{WIDTH - 2 * inner - 2.8}" '
              f'height="{HEIGHT - 2 * inner - 2.8}" rx="3" fill="none" stroke="{accent}" stroke-width="0.25"/>')
    return "".join(lines) + frames


def _rosette(cx, cy, radius, ink: str, accent: str, rings: int = 3, petals: int = 12, width=0.18) -> str:
    """Guilloche-Rosette: Ringe aus gegeneinander versetzten Wellenkreisen."""
    out = []
    for ring in range(rings):
        base = radius * (1 - ring * 0.3)
        amp = base * 0.16
        n = petals + ring * 4
        for k in range(5):
            phase = k * 2 * math.pi / (5 * n)
            points = []
            for i in range(360):
                t = 2 * math.pi * i / 360
                rho = base - amp + amp * math.sin(n * t + phase * n)
                points.append((cx + rho * math.cos(t), cy + rho * math.sin(t)))
            color = ink if ring % 2 == 0 else accent
            out.append(f'<path d="{_path(points)}" stroke="{color}" stroke-width="{width}" fill="none"/>')
    return "".join(out)


def _corner_rosettes(ink: str, accent: str) -> str:
    out = []
    radius = 7.2
    for cx, cy in ((BAND, BAND), (WIDTH - BAND, BAND), (BAND, HEIGHT - BAND), (WIDTH - BAND, HEIGHT - BAND)):
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{radius + 0.8}" fill="{PAPER}" stroke="{ink}" '
                   f'stroke-width="0.5"/>')
        out.append(_rosette(cx, cy, radius, ink, accent, rings=2, petals=10, width=0.2))
        out.append(f'<circle cx="{cx}" cy="{cy}" r="1.1" fill="{ink}"/>')
    return "".join(out)


def morse_of(text: str) -> list:
    """Morsezeichen je Wort, z. B. "Koch" → [["-.-", "---", "-.-.", "...."]];
    Umlaute als AE/OE/UE, unbekannte Zeichen fallen weg."""
    words = []
    for word in text.upper().split():
        word = "".join(UMLAUTS.get(ch, ch) for ch in word)
        codes = [MORSE_CODE[ch] for ch in word if ch in MORSE_CODE]
        if codes:
            words.append(codes)
    return words


def morse_svg(text: str, color: str, max_width: float = 170, max_unit: float = 1.15) -> str:
    """Text als Punkte und Striche (Einheiten wie beim Geben: Punkt 1,
    Strich 3, Pause im Zeichen 1, zwischen Zeichen 3, zwischen Wörtern 7)."""
    words = morse_of(text)
    if not words:
        return ""
    units = 0
    for wi, word in enumerate(words):
        units += 7 if wi else 0
        for ci, code in enumerate(word):
            units += 3 if ci else 0
            units += sum(1 if s == "." else 3 for s in code) + len(code) - 1
    unit = min(max_unit, max_width / units)
    height = unit * 2
    shapes, x = [], 0.0
    for wi, word in enumerate(words):
        x += 7 * unit if wi else 0
        for ci, code in enumerate(word):
            x += 3 * unit if ci else 0
            for si, sign in enumerate(code):
                x += unit if si else 0
                length = unit if sign == "." else 3 * unit
                shapes.append(f'<rect x="{x:.2f}" y="{(height - unit) / 2:.2f}" width="{length:.2f}" '
                              f'height="{unit:.2f}" rx="{unit / 2:.2f}"/>')
                x += length
    return (f'<svg class="morse" width="{x:.2f}mm" height="{height:.2f}mm" viewBox="0 0 {x:.2f} {height:.2f}" '
            f'fill="{color}" aria-label="{html.escape(text)}">{"".join(shapes)}</svg>')


def seal_svg(level_name: str, colors: tuple, ink: str, ring_text: str) -> str:
    """Siegel mit gezacktem Rand, Bändern und umlaufender Schrift."""
    fill, edge = colors
    light, dark = _mix(fill, "#ffffff", 0.55), _mix(edge, "#000000", 0.15)
    size, c = 50, 25  # Inhalt in 50er-Einheiten, gedruckt in 56 mm
    teeth, outer, inner = 40, 17.5, 16.0
    star = []
    for i in range(teeth * 2):
        angle = math.pi * i / teeth
        rho = outer if i % 2 == 0 else inner
        star.append((c + rho * math.sin(angle), c - 3 + rho * -math.cos(angle)))
    ribbon = _mix(edge, "#000000", 0.25)
    ribbons = (f'<path d="M{c - 9},{c + 6} L{c - 15},{size - 1} L{c - 11.5},{size - 4} L{c - 8},{size - 0.5} '
               f'L{c - 2},{c + 9} Z" fill="{ribbon}"/>'
               f'<path d="M{c + 9},{c + 6} L{c + 15},{size - 1} L{c + 11.5},{size - 4} L{c + 8},{size - 0.5} '
               f'L{c + 2},{c + 9} Z" fill="{ribbon}"/>')
    cy = c - 3
    label = html.escape(level_name) if level_name else "★"
    label_size = 4.6 if len(level_name) <= 6 else 3.6
    ring = html.escape(ring_text)
    return f"""<svg class="seal" width="56mm" height="56mm" viewBox="0 0 {size} {size}">
<defs>
<radialGradient id="metal" cx="38%" cy="32%" r="75%">
<stop offset="0" stop-color="{light}"/><stop offset="0.55" stop-color="{fill}"/><stop offset="1" stop-color="{edge}"/>
</radialGradient>
<path id="ring" d="M{c - 11.6},{cy} a11.6,11.6 0 1,1 23.2,0 a11.6,11.6 0 1,1 -23.2,0"/>
</defs>
{ribbons}
<path d="{_path(star)}" fill="url(#metal)" stroke="{dark}" stroke-width="0.35"/>
<circle cx="{c}" cy="{cy}" r="14.2" fill="none" stroke="{dark}" stroke-width="0.4"/>
<circle cx="{c}" cy="{cy}" r="9.2" fill="none" stroke="{dark}" stroke-width="0.3"/>
<text font-size="2.3" fill="{ink}" font-family="Georgia, 'Noto Serif', serif">
<textPath href="#ring" textLength="{2 * math.pi * 11.6 - 1.2:.2f}" lengthAdjust="spacing">{ring}</textPath></text>
<text x="{c}" y="{cy + label_size * 0.36}" text-anchor="middle" font-size="{label_size}" font-weight="bold"
 fill="{ink}" font-family="Georgia, 'Noto Serif', serif">{label}</text>
</svg>"""


def _ring_text(level_name: str) -> str:
    """Umlaufende Siegelschrift, auf den Kreisumfang aufgefüllt."""
    part = f"MORSETRAINER ★ {level_name.upper()} ★ " if level_name else "MORSETRAINER ★ "
    return part * 2 if len(part) <= 24 else part


def diploma_html(name: str, level_name: str, colors: tuple, condition: str, date_text: str,
                 call: str = "", holder: str = "", labels: dict = None) -> str:
    """HTML-Seite eines Diploms. `level_name` leer bei Diplomen ohne Stufen;
    `call` (groß) und `holder` (Name, darunter) beide leer: ohne
    Empfängerzeile. `labels` liefert die (übersetzten) Texte "title",
    "awarded", "date", "footer"."""
    labels = labels or {}
    esc = html.escape
    fill, edge = colors
    ink = _mix(edge, "#10141c", 0.55)        # Druckfarbe: dunkle Variante der Stufe
    accent = _mix(fill, edge, 0.35)
    recipient = ""
    if call or holder:
        recipient = f'<p class="awarded">{esc(labels.get("awarded", ""))}</p>'
        if call:
            recipient += f'<p class="call">{esc(call)}</p>'
        if holder:
            recipient += f'<p class="holder">{esc(holder)}</p>'
    title = f"{name} – {level_name}" if level_name else name
    watermark = _rosette(WIDTH / 2, HEIGHT / 2 - 4, 62, ink, accent, rings=3, petals=18, width=0.25)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
@page {{ size: A4 landscape; margin: 10mm; }}
html, body {{ margin: 0; background: #fff; color: #1d2127; }}
body {{ font-family: "Noto Serif", Georgia, "DejaVu Serif", serif;
        -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.sheet {{ position: relative; width: {WIDTH}mm; height: {HEIGHT}mm; margin: 0 auto; overflow: hidden;
          background: radial-gradient(ellipse at center, {PAPER} 55%, {_mix(PAPER, accent, 0.18)} 100%); }}
.art {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.watermark {{ opacity: 0.09; }}
.content {{ position: absolute; inset: 24mm 30mm 19mm; display: flex; flex-direction: column;
            align-items: center; text-align: center; }}
.program {{ font-size: 11pt; letter-spacing: 0.45em; text-transform: uppercase; margin: 0; color: {ink}; }}
h1 {{ font-family: "Noto Serif Display", "Noto Serif", Georgia, serif; font-size: 50pt; font-weight: normal;
      letter-spacing: 0.22em; text-transform: uppercase; margin: 2mm 0 0 0.22em; color: {ink}; line-height: 1; }}
.rule {{ display: flex; align-items: center; gap: 3mm; color: {accent}; margin: 2.5mm 0 1mm; }}
.rule::before, .rule::after {{ content: ""; width: 38mm; border-top: 0.35mm solid {accent}; }}
h2 {{ font-family: "Noto Serif Display", "Noto Serif", Georgia, serif; font-size: 28pt; font-weight: normal;
      font-style: italic; margin: 1mm 0 1.5mm; color: #1d2127; }}
.morse {{ display: block; flex-shrink: 0; margin: 0 auto 4mm; }}
.awarded {{ font-size: 11pt; font-style: italic; margin: 0; }}
.call {{ font-family: "DejaVu Sans Mono", "Courier New", monospace; font-size: 32pt; font-weight: bold;
         letter-spacing: 0.12em; margin: 0.5mm 0 1mm; color: {ink}; }}
.holder {{ font-size: 18pt; font-style: italic; margin: 0 0 2mm; }}
.awarded + .holder {{ font-size: 28pt; margin: 1mm 0 3mm; }}
.condition {{ font-size: 11pt; line-height: 1.4; max-width: 175mm; margin: 3mm 0 0; color: #3a3f47; }}
.middle {{ flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
.bottom {{ width: 100%; display: flex; justify-content: space-between; align-items: flex-end;
           font-size: 10.5pt; }}
.line {{ border-top: 0.3mm solid {ink}; padding-top: 1.2mm; width: 80mm; color: #3a3f47; }}
.seal {{ display: block; flex-shrink: 0; margin-bottom: -9mm; }}
</style></head><body>
<div class="sheet">
<svg class="art" viewBox="0 0 {WIDTH} {HEIGHT}" preserveAspectRatio="none">
<g class="watermark">{watermark}</g>
{_border(ink, accent)}
{_corner_rosettes(ink, accent)}
</svg>
<div class="content">
<p class="program">Morsetrainer</p>
<h1>{esc(labels.get("title", "Diplom"))}</h1>
<div class="rule">✦</div>
<h2>{esc(name)}</h2>
{morse_svg(name, _mix(accent, ink, 0.45))}
<div class="middle">
{recipient}
<p class="condition">{esc(condition)}</p>
</div>
<div class="bottom">
<div class="line">{esc(labels.get("date", ""))} {esc(date_text)}</div>
{seal_svg(level_name, colors, ink, _ring_text(level_name))}
<div class="line">{esc(labels.get("footer", ""))}</div>
</div>
</div>
</div>
</body></html>
"""
