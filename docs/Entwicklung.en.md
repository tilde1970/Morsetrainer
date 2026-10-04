# Morsetrainer – Development

For everyone who wants to run the Morsetrainer from source or work on it.
How to use the program is described in the [manual](Anleitung.en.md).

## Running from source

Requires Python 3.10 or newer with Tk.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
packaging/get_voice.sh           # voice for the Speak tab (about 63 MB)
python main.py
```

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
.github/workflows/   builds AppImage, exe and Mac app for releases, with SHA256SUMS.txt
```

## Release

A tag `vX.Y` starts `.github/workflows/release.yml`: it builds AppImage,
exe and Mac app (ZIP, Apple silicon only, unsigned), writes `SHA256SUMS.txt` and creates the release with the version's
section from `CHANGELOG.md`. The update in the program only installs files
that match `SHA256SUMS.txt` (`morsetrainer/net/update.py`).
