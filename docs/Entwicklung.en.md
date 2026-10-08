# Morsetrainer – Development

For everyone who wants to run the Morsetrainer from source or work on it.
How to use the program is described in the [manual](Anleitung.en.md).

## Running from source

Requires Python 3.10 or newer with Tk, plus PortAudio for sound. On
Linux these packages are often missing:

```bash
sudo apt install python3-venv python3-tk libportaudio2   # Debian, Ubuntu, Mint
sudo dnf install python3-tkinter portaudio               # Fedora
```

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
packaging/get_voice.sh           # voices for announcements and the Speak tab (about 120 MB)
python main.py
```

On Windows, `get_voice.sh` runs in Git Bash (comes with Git for Windows).
Without the voices everything except speech works.

Tests:

```bash
python -m unittest discover tests
```

## Project structure

```
main.py              start file
morsetrainer/
  app.py             main window with all tabs
  i18n.py            language (German/English), texts in i18n_en.py
  core/              Morse code, audio, band conditions, texts, statistics
  modes/             one module per training tab
  net/               network mode (trainer, participants, scoring), updates
  widgets/           reusable interface building blocks
tests/               automated tests
docs/                manual, development, pictures for the README
packaging/           AppImage build (icon, desktop file)
tools/motive/        award motifs: drawings (quellen/) and stich.py, which
                     generates morsetrainer/assets/motive/ from them
.github/workflows/   builds AppImage, exe and Mac app for releases, with SHA256SUMS.txt
```

## Release

A tag `vX.Y` starts `.github/workflows/release.yml`: it builds AppImage,
exe and Mac app (ZIP, Apple silicon only, unsigned), writes `SHA256SUMS.txt` and creates the release with the version's
section from `CHANGELOG.md` and below it (from “### English”) the one from
`CHANGELOG.en.md`; the update window in the program shows the part in the
interface language. The update in the program only installs files
that match `SHA256SUMS.txt` (`morsetrainer/net/update.py`).
