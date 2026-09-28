"""Startdatei des Morsetrainers: python main.py"""
import sys

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        from morsetrainer.selftest import run
        sys.exit(run(sys.argv[2]))
    from morsetrainer.app import main
    main()
