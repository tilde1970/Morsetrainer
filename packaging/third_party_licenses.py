"""Schreibt THIRD_PARTY_LICENSES.md: Lizenzen aller Teile, die ein Build
mitbringt, mit ihren Lizenztexten. Läuft in der CI vor PyInstaller, im
Python des Builds: Welche Pakete und Lizenzdateien dabei sind, hängt von
der Plattform ab (numpy bringt unter Windows und macOS andere Bibliotheken
mit). Das Hilfefenster zeigt die Datei im Reiter „Lizenzen“.

Aufruf: python packaging/third_party_licenses.py [Zieldatei]"""
import re
import sys
import tkinter
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent
LICENSES = Path(__file__).resolve().parent / "licenses"
# Was das Programm selbst braucht (requirements.txt); der Rest kommt über
# deren Abhängigkeiten dazu.
TOP_LEVEL = ("numpy", "sounddevice", "piper-tts", "lameenc")
REPO = "https://github.com/tilde1970/Morsetrainer"

HEADER = f"""# Lizenzen / Licenses

Der Quelltext des Morsetrainers steht unter der MIT-Lizenz (LICENSE). Die
fertigen Programmdateien enthalten zusätzlich die Sprachausgabe Piper mit
espeak-ng (GPL-3.0-or-later) und werden darum als Ganzes unter der
GPL-3.0-or-later weitergegeben. Den Quelltext dazu gibt es unter
{REPO} (Tag der Version), die Quellarchive von piper, espeak-ng, lameenc
und LAME hängen am jeweiligen Release.

The Morsetrainer source code is licensed under the MIT license (LICENSE).
The ready-made program files also contain the Piper speech output with
espeak-ng (GPL-3.0-or-later) and are therefore distributed as a whole under
the GPL-3.0-or-later. The source is at {REPO} (tag of the version); the
source archives of piper, espeak-ng, lameenc and LAME are attached to each
release.

Below: every bundled component with its license text.
"""


def _key(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def bundled() -> list:
    """Die mitgelieferten Pakete samt Abhängigkeiten, nach Namen sortiert."""
    found, todo = {}, list(TOP_LEVEL)
    while todo:
        name = todo.pop()
        if _key(name) in found:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # z. B. piper auf Intel-Macs mit neuem Python
        found[_key(name)] = dist
        for text in dist.requires or []:
            requirement = Requirement(text)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                todo.append(requirement.name)
    return sorted(found.values(), key=lambda d: _key(d.metadata["Name"]))


def license_files(dist) -> list:
    """(Pfad im Paket, Text) aller Lizenzdateien eines Pakets."""
    out, seen = [], set()
    for file in dist.files or []:
        name = str(file)
        if name.endswith((".py", ".pyc")) or not re.search(r"LICEN[CS]E|COPYING|NOTICE", name, re.I):
            continue
        try:
            text = Path(dist.locate_file(file)).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if text.strip() not in seen:  # dieselbe Datei an zwei Stellen (piper: COPYING)
            seen.add(text.strip())
            out.append((name.removeprefix("../../../"), text))
    return out


def _block(text: str) -> str:
    # Lizenztexte enthalten keine drei Backticks; sicherheitshalber ersetzen.
    return "```\n" + text.strip("\n").replace("```", "'''") + "\n```\n"


def _section(title: str, lines: list, texts: list) -> str:
    out = [f"## {title}", ""] + lines + [""]
    for name, text in texts:
        out += [f"{name}:", "", _block(text)]
    return "\n".join(out)


def _static(name: str) -> str:
    return (LICENSES / name).read_text(encoding="utf-8")


def build() -> str:
    parts = [HEADER]
    for dist in bundled():
        meta = dist.metadata
        license_name = meta.get("License-Expression") or meta.get("License") or "siehe Text / see text"
        urls = [meta.get("Home-page")] + [u.split(",", 1)[-1].strip() for u in meta.get_all("Project-URL") or []]
        lines = [f"Lizenz / License: {license_name.splitlines()[0]}"]
        url = next((u for u in urls if u), None)
        if url:
            lines.append(f"Web: {url}")
        texts = license_files(dist)
        if not texts:
            lines.append("Kein Lizenztext im Paket; siehe Web. / No license text in the package; see web.")
        parts.append(_section(f"{meta['Name']} {dist.version}", lines, texts))
    parts.append(_section("espeak-ng (in piper-tts)", [
        "Lizenz / License: GPL-3.0-or-later (Text wie bei piper-tts / text as for piper-tts)",
        "Web: https://github.com/espeak-ng/espeak-ng"], []))
    parts.append(_section("LAME 3.100 (in lameenc)", [
        "Lizenz / License: LGPL-2.0-or-later",
        "MP3-Kodierung mit LAME / MP3 encoding with LAME: https://lame.sourceforge.io"],
        [("COPYING", _static("LAME.txt"))]))
    parts.append(_section("PortAudio", ["Lizenz / License: MIT", "Web: https://www.portaudio.com"],
                          [("LICENSE.txt", _static("PortAudio.txt"))]))
    parts.append(_section(f"Python {sys.version.split()[0]}", ["Lizenz / License: PSF-2.0",
                                                               "Web: https://www.python.org"],
                          [("LICENSE", _static("Python.txt"))]))
    parts.append(_section(f"Tcl/Tk {tkinter.TclVersion}", ["Lizenz / License: TCL", "Web: https://www.tcl-lang.org"],
                          [("license.terms", _static("Tcl-Tk.txt"))]))
    parts.append(_section("PyInstaller-Bootloader", [
        "Lizenz / License: GPL-2.0-or-later mit Ausnahme für gebaute Programme / with exception for built programs",
        "Web: https://pyinstaller.org/en/stable/license.html"], []))
    parts.append(_section("Stimmen / Voices", [
        "de_DE-thorsten-medium: Datensatz / dataset Thorsten-Voice, CC0 "
        "(https://github.com/thorstenMueller/Thorsten-Voice)",
        "en_US-ljspeech-medium: Datensatz / dataset LJ Speech, gemeinfrei / public domain "
        "(https://keithito.com/LJ-Speech-Dataset/)",
        "Modelle / models: https://huggingface.co/rhasspy/piper-voices"], []))
    return "\n".join(parts)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "THIRD_PARTY_LICENSES.md"
    target.write_text(build(), encoding="utf-8")
    print(f"{target}: {target.stat().st_size // 1024} KB")
