#!/usr/bin/env bash
# Lädt die Piper-Stimmen nach voices/ im Projektverzeichnis: Deutsch für
# „Hören & Sagen“ (Reiter Sprechen) und die Ansage, Englisch für die Ansage
# bei englischer Oberfläche. Beim Start aus dem Quelltext sucht das Programm
# sie dort; die Release-Builds packen sie mit ein (--add-data voices:voices).
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main
declare -A URL=(
    [de_DE-thorsten-medium]=$BASE/de/de_DE/thorsten/medium
    [en_US-lessac-medium]=$BASE/en/en_US/lessac/medium
)
declare -A SHA256=(
    [de_DE-thorsten-medium.onnx]=7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819
    [de_DE-thorsten-medium.onnx.json]=974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85
    [en_US-lessac-medium.onnx]=5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f
    [en_US-lessac-medium.onnx.json]=efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0
)

mkdir -p voices
for file in "${!SHA256[@]}"; do
    voice=${file%%.onnx*}
    if [ ! -f "voices/$file" ] || ! echo "${SHA256[$file]}  voices/$file" | sha256sum -c --status; then
        curl -fsSL -o "voices/$file" "${URL[$voice]}/$file"
    fi
    echo "${SHA256[$file]}  voices/$file" | sha256sum -c
done
