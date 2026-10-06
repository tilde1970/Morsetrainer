#!/usr/bin/env bash
# Lädt die Piper-Stimmen nach voices/ im Projektverzeichnis: Deutsch für
# „Hören & Sagen“ (Reiter Sprechen) und die Ansage, Englisch für die Ansage
# bei englischer Oberfläche. Beim Start aus dem Quelltext sucht das Programm
# sie dort; die Release-Builds packen sie mit ein (--add-data voices:voices).
# Läuft auch mit dem bash 3.2 von macOS (ohne assoziative Arrays) und nimmt
# dort shasum (das sha256sum von macOS ist nicht das von GNU).
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main
# Datei, Ordner auf Hugging Face, SHA256
FILES="
de_DE-thorsten-medium.onnx de/de_DE/thorsten/medium 7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819
de_DE-thorsten-medium.onnx.json de/de_DE/thorsten/medium 974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85
en_US-lessac-medium.onnx en/en_US/lessac/medium 5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f
en_US-lessac-medium.onnx.json en/en_US/lessac/medium efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0
"

if sha256sum --version >/dev/null 2>&1; then
    check() { sha256sum -c "$@"; }
else
    check() { shasum -a 256 -c "$@"; }
fi

mkdir -p voices
echo "$FILES" | while read -r file folder sha; do
    [ -n "$file" ] || continue
    if [ ! -f "voices/$file" ] || ! echo "$sha  voices/$file" | check >/dev/null 2>&1; then
        curl -fsSL -o "voices/$file" "$BASE/$folder/$file"
    fi
    echo "$sha  voices/$file" | check
done
