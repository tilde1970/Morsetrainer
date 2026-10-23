"""Startdatei des Morsetrainers: python main.py"""
import sys

USAGE = """Morsetrainer von DL4YM

  python main.py                 Programm starten
  python main.py --join PIN      nach einem Update wieder mit dem Trainer
                                 verbinden (Adresse und Name sind gespeichert)
  python main.py --selftest X.mp3  Selbsttest (Ton, Stimme, MP3) ohne Fenster
  python main.py --version       Version anzeigen"""

MISSING_LIBRARY = """Der Morsetrainer kann nicht starten: {what} fehlt.

  Debian, Ubuntu, Mint:  sudo apt install python3-tk libportaudio2
  Fedora:                sudo dnf install python3-tkinter portaudio

Danach prüft  python main.py --selftest probe.mp3  ohne Fenster und Ton,
ob alles da ist. ({error})"""


def missing_library(exc):
    """Lesbarer Hinweis, wenn ein Systempaket fehlt (Tk oder PortAudio beim Start
    aus dem Quelltext), sonst None."""
    text = str(exc)
    if "tkinter" in text.lower():
        return MISSING_LIBRARY.format(what="Tk (python3-tk)", error=text)
    if "portaudio" in text.lower():
        return MISSING_LIBRARY.format(what="PortAudio (libportaudio2)", error=text)
    return None


def import_app():
    try:
        import morsetrainer.app as app
    except (ImportError, OSError) as exc:
        message = missing_library(exc)
        if message is None:
            raise
        if sys.stderr is not None:  # ohne Konsole (Windows-exe) gibt es keine Ausgabe
            print(message, file=sys.stderr)
        sys.exit(1)
    return app


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    if len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"Morsetrainer {import_app().__version__}")
        sys.exit(0)
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        from morsetrainer.selftest import run
        sys.exit(run(sys.argv[2]))
    import_app().main()
