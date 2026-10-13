"""Lädt die Quellarchive der GPL- und LGPL-Teile, die in den Builds
stecken, nach sources/: piper (piper1-gpl) mit dem espeak-ng-Stand, den
dessen CMakeLists.txt einbindet, und lameenc mit dem LAME, das dessen
CMakeLists.txt baut. Die Versionen stehen in packaging/constraints.txt (mit
diesen baut die CI). Die Release-CI hängt die Archive ans Release: Wer eine
Programmdatei bekommt, bekommt so auch den Quelltext dazu (GPL/LGPL).

Aufruf: python packaging/gpl_sources.py [Zielordner]"""
import hashlib
import io
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPER = "https://github.com/OHF-Voice/piper1-gpl/archive/refs/tags/v{version}.tar.gz"
ESPEAK = "https://github.com/espeak-ng/espeak-ng/archive/{ref}.tar.gz"
LAMEENC = "https://github.com/chrisstaite/lameenc/archive/refs/tags/v{version}.tar.gz"


def pinned(name: str) -> str:
    """Version von `name` aus packaging/constraints.txt."""
    text = (ROOT / "packaging" / "constraints.txt").read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}==(\S+)", text, re.M)
    if not match:
        raise SystemExit(f"{name} fehlt in packaging/constraints.txt")
    return match.group(1)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def cmake_of(archive: bytes) -> str:
    """CMakeLists.txt aus der obersten Ebene eines GitHub-Archivs."""
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        member = next(m for m in tar.getmembers() if m.name.count("/") == 1 and m.name.endswith("/CMakeLists.txt"))
        return tar.extractfile(member).read().decode("utf-8")


def espeak_ref(cmake: str) -> str:
    """espeak-ng-Stand (GIT_TAG), den piper1-gpl einbindet."""
    match = re.search(r"espeak-ng\.git\s+GIT_TAG\s+(\w+)", cmake)
    if not match:
        raise SystemExit("espeak-ng-Stand in piper1-gpl/CMakeLists.txt nicht gefunden")
    return match.group(1)


def lame_source(cmake: str) -> tuple:
    """(Adresse, Version, SHA256) des LAME-Archivs, das lameenc baut."""
    match = re.search(r"URL\s+(\S*lame-([\d.]+)\.tar\.gz\S*)\s+URL_HASH\s+SHA256=(\w+)", cmake)
    if not match:
        raise SystemExit("LAME-Quelle in lameenc/CMakeLists.txt nicht gefunden")
    return match.group(1), match.group(2), match.group(3).lower()


def save(folder: Path, name: str, data: bytes) -> None:
    (folder / name).write_bytes(data)
    print(f"{name}: {len(data) // 1024} KB")


def main(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    version = pinned("piper-tts")
    piper = fetch(PIPER.format(version=version))
    save(folder, f"piper1-gpl-{version}.tar.gz", piper)
    ref = espeak_ref(cmake_of(piper))
    save(folder, f"espeak-ng-{ref}.tar.gz", fetch(ESPEAK.format(ref=ref)))

    version = pinned("lameenc")
    lameenc = fetch(LAMEENC.format(version=version))
    save(folder, f"lameenc-{version}.tar.gz", lameenc)
    url, lame_version, sha = lame_source(cmake_of(lameenc))
    data = fetch(url)
    if hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit("LAME-Archiv passt nicht zur Prüfsumme in lameenc/CMakeLists.txt")
    save(folder, f"lame-{lame_version}.tar.gz", data)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sources")
