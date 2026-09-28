"""Selbsttest für die Release-Builds: prüft ohne Fenster und Soundkarte,
ob Stimme und MP3-Export im gepackten Programm funktionieren.

    morsetrainer --selftest ziel.mp3

Schreibt eine kurze Übung (Morsezeichen plus Ansage) als MP3 und endet mit
Code 0, sonst mit 1 und dem Grund auf stderr."""
import sys

from morsetrainer.core import mp3, speech
from morsetrainer.core.morse import build_text


def run(path: str) -> int:
    for reason in (speech.speaker.available(), mp3.available()):
        if reason:
            print(reason, file=sys.stderr)
            return 1
    voice = speech.speaker.synth(speech.spoken("DL4YM"))
    if not len(voice):
        print(speech.speaker.error or "Keine Sprache erzeugt.", file=sys.stderr)
        return 1
    try:
        with mp3.Mp3Writer(path) as writer:
            writer.write(build_text("DL4YM", 20, 600))
            writer.write(voice)
    except mp3.Mp3Error as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"OK: {path} ({writer.seconds:.1f} s)")
    return 0
