#!/usr/bin/env bash
# Baut dist/Morsetrainer-x86_64.AppImage. Voraussetzungen: pyinstaller im
# aktiven Python, libportaudio2 installiert, appimagetool im PATH oder als
# $APPIMAGETOOL.
set -euo pipefail
cd "$(dirname "$0")/.."

PORTAUDIO=$(ldconfig -p | awk '/libportaudio\.so\.2 .*x86-64/ {print $NF}' | head -n1 || true)
[ -n "$PORTAUDIO" ] || { echo "libportaudio.so.2 nicht gefunden (apt install libportaudio2)"; exit 1; }

pyinstaller --noconfirm --clean --windowed --name morsetrainer \
    --add-binary "$PORTAUDIO:." \
    --runtime-hook packaging/rthook_portaudio.py \
    main.py

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

ARCH=x86_64 "${APPIMAGETOOL:-appimagetool}" "$APPDIR" dist/Morsetrainer-x86_64.AppImage
