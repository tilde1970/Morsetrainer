"""Selbsttest für die Release-Builds: prüft ohne Fenster und Soundkarte,
ob beide Stimmen (auch mit schnellerem Sprechtempo), der MP3-Export, PortAudio (Ton), Tcl/Tk (Oberfläche) und
die Lizenzdatei im gepackten Programm vorhanden sind.

    morsetrainer --selftest ziel.mp3

Schreibt eine kurze Übung (Morsezeichen plus Ansage) als MP3 und endet mit
Code 0, sonst mit 1 und dem Grund auf stderr."""
import sys
from pathlib import Path

from morsetrainer.core import mp3, speech
from morsetrainer.core.morse import build_text


def _libraries() -> str:
    """Leer, wenn PortAudio und Tcl/Tk geladen werden können, sonst der Grund.
    Beides geht ohne Soundkarte und ohne Bildschirm."""
    try:
        import sounddevice
        portaudio = sounddevice.get_portaudio_version()[1]
    except Exception as exc:  # fehlende Bibliothek: OSError, im Paket auch ImportError
        return f"PortAudio fehlt: {exc}"
    try:
        import tkinter
        tk_version = tkinter.Tcl().eval("info patchlevel")
    except Exception as exc:
        return f"Tcl/Tk fehlt: {exc}"
    print(f"{portaudio}, Tcl/Tk {tk_version}")
    return ""


def run(path: str) -> int:
    """Prüft PortAudio und Tcl/Tk und erzeugt mit beiden Stimmen eine kurze
    Übung als MP3 nach `path`; 0 bei Erfolg, sonst 1 (Grund auf stderr)."""
    missing = _libraries()
    if missing:
        print(missing, file=sys.stderr)
        return 1
    # Im Paket gehören die Lizenzen der Bestandteile dazu (GPL, LGPL, MIT …).
    base = getattr(sys, "_MEIPASS", None)
    if base and not (Path(base) / "THIRD_PARTY_LICENSES.md").is_file():
        print("THIRD_PARTY_LICENSES.md fehlt im Programm.", file=sys.stderr)
        return 1
    speakers = [speech.speaker_for(lang) for lang in speech.VOICES]  # deutsch und englisch (Ansage)
    for reason in [speaker.available() for speaker in speakers] + [mp3.available()]:
        if reason:
            print(reason, file=sys.stderr)
            return 1
    # Im Paket gehört die aktuelle Stimme dazu, nicht eine frühere.
    for lang, name in speech.VOICES.items():
        if speech.voice_path(lang).name != f"{name}.onnx":
            print(f"Stimme {name} fehlt (gefunden: {speech.voice_path(lang).name}).", file=sys.stderr)
            return 1
    voices = []
    for speaker in speakers:
        voice = speaker.synth(speech.spoken("DL4YM", lang=speaker.lang))
        if not len(voice):
            print(speaker.error or "Keine Sprache erzeugt.", file=sys.stderr)
            return 1
        voices.append(voice)
    # Anderes Sprechtempo geht über piper.SynthesisConfig: auch das muss im
    # Paket sein. Ohne Zufall in den Lautdauern, sonst streut die Länge.
    text = speech.spoken("DL4YM", lang=speakers[0].lang)
    normal, fast = (speakers[0].synth(text, rate=rate, steady=True) for rate in (1.0, 1.5))
    if not len(normal) or not len(fast):
        print(speakers[0].error or "Ansage mit festem Takt nicht erzeugt.", file=sys.stderr)
        return 1
    if len(fast) >= 0.9 * len(normal):
        print(f"Schnellere Ansage nicht kürzer ({len(fast)} gegen {len(normal)} Samples).", file=sys.stderr)
        return 1
    try:
        with mp3.Mp3Writer(path) as writer:
            writer.write(build_text("DL4YM", 20, 600))
            for voice in voices:
                writer.write(voice)
    except mp3.Mp3Error as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"OK: {path} ({writer.seconds:.1f} s)")
    return 0
