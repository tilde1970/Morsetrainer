"""Motive der Diplome im Stil eines Stichtiefdrucks (wie auf Geldscheinen).

Quelle je Motiv: eine Zeichnung in quellen/<Name>.svg – Flächen mit
Grauverläufen für die Schattierung, Umrisse als stroke="#000". Daraus wird
morsetrainer/assets/motive/<Name>.svg: die Flächen als waagerechte Linien,
deren Dicke der Dunkelheit folgt (in dunklen Partien eine zweite, schräge
Lage), dazu ein zartes Oval als Grund; darunter die Umrisse der Zeichnung,
in Papierfarbe gefüllt, damit sich die Teile richtig verdecken.

Die Ausgabe nutzt currentColor (Linien) und var(--paper) (Füllungen), die
Diplomseite setzt beides. <Name> ist der Schlüssel des Diploms
(core/awards.py), n47 das Clubheim des OV Gütersloh rechts auf jedem
klassischen Diplom.

Nur für die Entwicklung: braucht Pillow und Chromium (zum Rastern der
Zeichnung). Aufruf aus dem Projektverzeichnis:

    python tools/motive/stich.py            # alle Motive
    python tools/motive/stich.py koch qrq   # nur diese"""
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "quellen"
TARGET = HERE.parents[1] / "morsetrainer" / "assets" / "motive"
LEVELS = 6


def render(svg_text: str, width: int, height: int, out: Path) -> Image.Image:
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg_text)
    subprocess.run(["chromium", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={width},{height}", f"--screenshot={out}", f"file://{f.name}"],
                   capture_output=True, check=True)
    return Image.open(out).convert("L")


def stich(src: Path, dst: Path, spacing=5.6, max_w=4.8, step=2.0, outline=2.4, vignette=0.09,
          cross_from=0.6, pad=40) -> int:
    svg = src.read_text(encoding="utf-8")
    w, h = map(int, re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups())
    tmp = Path(tempfile.mkdtemp())
    full = render(svg, w, h, tmp / "full.png")
    box = ImageChops.difference(full, Image.new("L", full.size, 255)).getbbox()
    x0, y0 = max(0, box[0] - pad), max(0, box[1] - pad)
    x1, y1 = min(w, box[2] + pad), min(h, box[3] + pad)
    fills = svg.replace('stroke="#000"', 'stroke="none"')
    im = render(fills, w, h, tmp / "fills.png").filter(ImageFilter.GaussianBlur(0.8))
    px = im.load()
    cw, ch = x1 - x0, y1 - y0

    def dark(x, y):
        d = 1 - px[int(x), int(y)] / 255 if x0 <= x < x1 and y0 <= y < y1 else 0
        r = ((x - (x0 + x1) / 2) / (cw * 0.5)) ** 2 + ((y - (y0 + y1) / 2) / (ch * 0.5)) ** 2
        if r < 1:
            d = max(d, vignette * (1 - r) ** 0.35)
        return d

    by_level = {lv: [] for lv in range(1, LEVELS + 1)}

    def lay(angle, f):
        ca, sa = math.cos(angle), math.sin(angle)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        diag = math.hypot(cw, ch) / 2
        k = -diag
        while k < diag:
            s, cur, start = -diag, 0, None
            while s <= diag + step:
                x, y = cx + ca * s - sa * k, cy + sa * s + ca * k
                lv = min(LEVELS, round(f(dark(x, y)) * LEVELS)) if s <= diag else 0
                if lv != cur:
                    if cur and start is not None and math.dist(start, (x, y)) > 0.5:
                        by_level[cur].append((start, (x, y)))
                    cur, start = lv, (x, y)
                s += step
            k += spacing

    lay(0.0, lambda d: d ** 0.9)
    lay(math.radians(-30), lambda d: max(0.0, (d - cross_from) / (1 - cross_from)))
    parts = []
    for lv, segs in by_level.items():
        if segs:
            d = "".join(f"M{a[0]:.0f} {a[1]:.0f}L{b[0]:.0f} {b[1]:.0f}" for a, b in segs)
            parts.append(f'<path d="{d}" stroke-width="{max_w * lv / LEVELS:.2f}"/>')
    # Umrisse: die Zeichnung ohne Verläufe, in Papierfarbe gefüllt
    body = svg[svg.index(">", svg.index("<svg")) + 1:svg.rindex("</svg>")]
    body = re.sub(r"<defs>.*?</defs>", "", body, flags=re.S)
    body = re.sub(r'<rect width="\d+" height="\d+" fill="#fff"/>', "", body)
    body = re.sub(r'fill="[^"]*"', 'fill="var(--paper, #fff)"', body)
    body = re.sub(r'stroke="#000"', 'stroke="currentColor"', body)
    body = re.sub(r'<[^<>]*stroke="#fff"[^<>]*/>', "", body)    # Glanzlinien
    body = re.sub(r'<[^<>]*stroke="none"[^<>]*/>', "", body)    # Glanzpunkte
    body = re.sub(r'stroke-width="([\d.]+)"', lambda m: f'stroke-width="{float(m.group(1)) * outline / 3:.2f}"', body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"\s+", " ", body)
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {cw} {ch}">'
           f'{body}<g stroke="currentColor" fill="none">{"".join(parts)}</g></svg>')
    dst.write_text(out, encoding="utf-8")
    return len(out)


def main(names) -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    sources = [SOURCES / f"{n}.svg" for n in names] if names else sorted(SOURCES.glob("*.svg"))
    for src in sources:
        size = stich(src, TARGET / src.name)
        print(f"{src.stem}: {size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
