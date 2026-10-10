"""Startdatei des Morsetrainers: python main.py"""
import sys

USAGE = """Morsetrainer von DL4YM

  python main.py                 Programm starten
  python main.py --join PIN      nach einem Update wieder mit dem Trainer
                                 verbinden (Adresse und Name sind gespeichert)
  python main.py --selftest X.mp3  Selbsttest (Ton, Stimme, MP3) ohne Fenster
  python main.py --version       Version anzeigen"""

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    if len(sys.argv) == 2 and sys.argv[1] == "--version":
        from morsetrainer.app import __version__
        print(f"Morsetrainer {__version__}")
        sys.exit(0)
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        from morsetrainer.selftest import run
        sys.exit(run(sys.argv[2]))
    from morsetrainer.app import main
    main()
