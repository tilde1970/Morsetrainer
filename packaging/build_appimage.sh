#!/usr/bin/env bash
# Baut dist/Morsetrainer-x86_64.AppImage. Voraussetzungen: pyinstaller im
# aktiven Python, libportaudio2 installiert, appimagetool im PATH oder als
# $APPIMAGETOOL.
#
# Mit $UPDATE_INFORMATION (z. B. "gh-releases-zsync|user|repo|latest|
# Morsetrainer-x86_64.AppImage.zsync") wird die Update-Quelle eingebettet
# und dist/Morsetrainer-x86_64.AppImage.zsync erzeugt; AppImage-Verwalter
# wie Gear Lever finden Updates dann ohne manuelle Einstellung.
set -euo pipefail
cd "$(dirname "$0")/.."

PORTAUDIO=$(ldconfig -p | awk '/libportaudio\.so\.2 .*x86-64/ {print $NF}' | head -n1 || true)
[ -n "$PORTAUDIO" ] || { echo "libportaudio.so.2 nicht gefunden (apt install libportaudio2)"; exit 1; }

packaging/get_voice.sh

pyinstaller --noconfirm --clean --windowed --name morsetrainer \
    --add-binary "$PORTAUDIO:." \
    --runtime-hook packaging/rthook_portaudio.py \
    --add-data README.md:. --add-data CHANGELOG.md:. \
    --add-data morsetrainer/assets:morsetrainer/assets \
    --add-data voices:voices --additional-hooks-dir packaging/hooks \
    main.py

# Stimme und MP3 im gepackten Programm prüfen (ohne Fenster, ohne Ton).
dist/morsetrainer/morsetrainer --selftest build/selftest.mp3

APPDIR=build/Morsetrainer.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a dist/morsetrainer "$APPDIR/usr/lib/"
# Audio-Systembibliotheken nicht mitliefern, sie müssen zum ALSA/JACK/
# PipeWire des Zielsystems passen (vgl. AppImage-Excludelist). Ebenso die
# C++-Laufzeit: die System-libjack braucht die (neuere) System-libstdc++.
rm -f "$APPDIR"/usr/lib/morsetrainer/_internal/{libasound.so.2,libjack.so.0,libstdc++.so.6,libgcc_s.so.1}
cp packaging/morsetrainer.desktop packaging/morsetrainer.svg "$APPDIR/"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/morsetrainer/morsetrainer" "$@"
RUN
chmod +x "$APPDIR/AppRun"

UPDATE_ARGS=()
[ -n "${UPDATE_INFORMATION:-}" ] && UPDATE_ARGS=(-u "$UPDATE_INFORMATION")
ARCH=x86_64 "${APPIMAGETOOL:-appimagetool}" "${UPDATE_ARGS[@]}" "$APPDIR" dist/Morsetrainer-x86_64.AppImage
# appimagetool legt die .zsync-Datei im aktuellen Verzeichnis ab.
if [ -f Morsetrainer-x86_64.AppImage.zsync ]; then
    mv Morsetrainer-x86_64.AppImage.zsync dist/
fi
