# Morsetrainer – Development

For everyone who wants to run the Morsetrainer from source or work on it.
How to use the program is described in the [manual](Anleitung.en.md).

## Running from source

**Requirements:** Python 3.10 or newer with Tk, plus PortAudio for sound.
On Linux these packages are often missing:

```bash
sudo apt install python3-venv python3-tk libportaudio2   # Debian, Ubuntu, Mint
sudo dnf install python3-tkinter portaudio               # Fedora
```

On Windows and macOS the Python from python.org comes with Tk; PortAudio
comes with the `sounddevice` package there. Intel Macs have some
restrictions, see the manual, section “Older Macs with an Intel processor”.

**Set up and start,** in the project directory:

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3. Install the dependencies: `pip install -r requirements.txt`
4. Download the voices for announcements and the Speak tab (about 120 MB):
   `packaging/get_voice.sh`. On Windows the script runs in Git Bash (comes
   with Git for Windows). Without the voices everything except speech
   works.
5. Start: `python main.py`. The main window opens.

The data (`stats/`, `window_state.json` …) then lives in the project
directory.

**Command line:**

```bash
python main.py --version              # show the version
python main.py --selftest probe.mp3   # self-test without a window: sound, voices, MP3
MORSETRAINER_LANG=en python main.py   # English interface (Linux, macOS)
```

`MORSETRAINER_LANG` takes precedence over the setting but does not change
it: on exit the saved language is kept unless you choose another one in the
settings.

`--selftest` checks that PortAudio, Tcl/Tk, both voices and the MP3 export
are present, writes a short sample as MP3 and exits with code 0 (otherwise
1 and the reason).

## Tests

The tests run without a sound card (`tests/__init__.py` replaces
`sounddevice` with a dummy) and with their own data directory; your
practice data stays untouched. The interface tests need a display.

```bash
python -m unittest discover tests        # all tests
python -m unittest tests.test_i18n       # a single module
xvfb-run -a python -m unittest discover tests   # Linux without a display (server, CI)
```

On every push to `main` and on pull requests the tests run on GitHub
(`.github/workflows/tests.yml`): on Linux with Python 3.10 and 3.12, plus
an installation check on Windows and macOS.

## Texts, translation and manual

- The German texts are in the code and are also the keys: `tr("…")`
  translates when displayed, `N_("…")` marks texts that are translated
  later. The English texts are in `morsetrainer/i18n_en.py`.
  `tests/test_i18n.py` checks that every marked text has a translation
  with the same placeholders.
- The program shows the manual (`docs/Anleitung.md`,
  `docs/Anleitung.en.md`) in the help window
  (`morsetrainer/widgets/help_window.py`). The help window knows only part
  of Markdown: headings, paragraphs, lists, bold, italic, code, code
  blocks, links (text only) and tables; images are left out. The Help
  button jumps to the heading named like the current tab, so these
  headings must be named exactly like the tabs. Both languages have the
  same structure.
- What changes in each version is in `CHANGELOG.md` and
  `CHANGELOG.en.md`.

## Project structure

```
main.py              start file
morsetrainer/
  app.py             main window with all tabs
  i18n.py            language (German/English), texts in i18n_en.py
  core/              Morse code, audio, band conditions, texts, statistics,
                     database, daily practice, awards, backup
  modes/             one module per training tab
  net/               network mode (trainer, participants, scoring), updates
  widgets/           reusable interface building blocks, help window
  assets/            program icons and award motifs
tests/               automated tests
docs/                manual, development, pictures for the README
packaging/           building: AppImage script, voices (get_voice.sh),
                     PyInstaller hooks, pinned versions (constraints.txt),
                     icon, desktop file
tools/motive/        award motifs: drawings (quellen/) and stich.py, which
                     generates morsetrainer/assets/motive/ from them
.github/workflows/   tests; builds AppImage, exe and Mac app for releases, with SHA256SUMS.txt
```

## Building and release

On Linux the AppImage can also be built locally:
`packaging/build_appimage.sh` creates `dist/Morsetrainer-x86_64.AppImage`.
Requirements: `pyinstaller` in the active environment, `libportaudio2`
and `appimagetool` in the `PATH` (or in `$APPIMAGETOOL`). GitHub builds
the exe and the Mac app; the PyInstaller commands for them are in
`.github/workflows/release.yml`.

A tag `vX.Y` starts `.github/workflows/release.yml`: it builds AppImage,
exe and Mac app (ZIP, Apple silicon only, unsigned) with the pinned
versions from `packaging/constraints.txt` and checks each built program
with `--selftest`. Only if that and the tests succeed does it write
`SHA256SUMS.txt` and create the release with the version's section from
`CHANGELOG.md` and below it (from “### English”) the one from
`CHANGELOG.en.md`; the update window in the program shows the part in the
interface language. The update in the program only installs files that
match `SHA256SUMS.txt` (`morsetrainer/net/update.py`).

## Contributing

Please report bugs, wishes and questions as an
[issue on GitHub](https://github.com/tilde1970/Morsetrainer/issues).
Comments, docstrings and interface texts are in German; comments describe
the purpose, not the version history.
