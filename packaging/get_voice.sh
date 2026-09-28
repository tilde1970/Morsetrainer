#!/usr/bin/env bash
# Lädt die Piper-Stimme für „Hören & Sagen“ (Reiter Sprechen) nach voices/
# im Projektverzeichnis. Beim Start aus dem Quelltext sucht das Programm sie
# dort; die Release-Builds packen sie mit ein (--add-data voices:voices).
set -euo pipefail
cd "$(dirname "$0")/.."

VOICE=de_DE-thorsten-medium
URL=https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium
declare -A SHA256=(
    [$VOICE.onnx]=7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819
    [$VOICE.onnx.json]=974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85
)

mkdir -p voices
for file in "${!SHA256[@]}"; do
    if [ ! -f "voices/$file" ] || ! echo "${SHA256[$file]}  voices/$file" | sha256sum -c --status; then
        curl -fsSL -o "voices/$file" "$URL/$file"
    fi
    echo "${SHA256[$file]}  voices/$file" | sha256sum -c
done
