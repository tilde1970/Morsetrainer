#!/usr/bin/env bash
# Lädt die Piper-Stimmen nach voices/ im Projektverzeichnis: Deutsch für
# „Hören & Sagen“ (Reiter Sprechen) und die Ansage, Englisch für die Ansage
# bei englischer Oberfläche. Beim Start aus dem Quelltext sucht das Programm
# sie dort; die Release-Builds packen sie mit ein (--add-data voices:voices).
# Läuft auch mit dem bash 3.2 von macOS (ohne assoziative Arrays) und nimmt
# dort shasum (das sha256sum von macOS ist nicht das von GNU).
set -euo pipefail
cd "$(dirname "$0")/.."

# Beide Stimmen beruhen auf freien Datensätzen (Thorsten: CC0, LJ Speech:
# gemeinfrei) und dürfen darum in die Builds.
# Fester Stand des Repos statt „main“: Ändert sich dort eine Datei, lädt
# der Build weiter dieselbe (die Prüfsummen unten passen zu diesem Stand).
REVISION=c10ece1aade47bb51c153c893d14e5bf8e5b7117
BASE=https://huggingface.co/rhasspy/piper-voices/resolve/$REVISION
# Datei, Ordner auf Hugging Face, SHA256
FILES="
de_DE-thorsten-medium.onnx de/de_DE/thorsten/medium 7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819
de_DE-thorsten-medium.onnx.json de/de_DE/thorsten/medium 974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85
en_US-ljspeech-medium.onnx en/en_US/ljspeech/medium 6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22
en_US-ljspeech-medium.onnx.json en/en_US/ljspeech/medium 141d612cc0a95ed7efc1ca936b845c2364967f2e9217c5dbfcf69fc4d6c65860
"

# Das sha256sum von macOS kennt --version auch, darum auf GNU prüfen.
if sha256sum --version 2>/dev/null | grep -q GNU; then
    check() { sha256sum -c "$@"; }
else
    check() { shasum -a 256 -c "$@"; }
fi

mkdir -p voices
# Frühere englische Stimme (Datensatz nur für die Forschung): weg, damit
# --add-data voices:voices sie nicht in einen Build packt.
rm -f voices/en_US-lessac-medium.onnx voices/en_US-lessac-medium.onnx.json
echo "$FILES" | while read -r file folder sha; do
    [ -n "$file" ] || continue
    if [ ! -f "voices/$file" ] || ! echo "$sha  voices/$file" | check >/dev/null 2>&1; then
        curl -fsSL -o "voices/$file" "$BASE/$folder/$file"
    fi
    echo "$sha  voices/$file" | check
done
