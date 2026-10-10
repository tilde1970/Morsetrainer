# Morsetrainer – Entwicklung

Für alle, die den Morsetrainer aus dem Quelltext starten oder daran
mitarbeiten möchten. Die Bedienung beschreibt die [Anleitung](Anleitung.md).

## Aus dem Quelltext starten

**Voraussetzungen:** Python 3.10 oder neuer mit Tk, dazu PortAudio für den
Ton. Unter Linux fehlen diese Pakete oft:

```bash
sudo apt install python3-venv python3-tk libportaudio2   # Debian, Ubuntu, Mint
sudo dnf install python3-tkinter portaudio               # Fedora
```

Unter Windows und macOS bringt das Python von python.org Tk mit; PortAudio
kommt dort mit dem Paket `sounddevice`. Für Intel-Macs gelten
Einschränkungen, siehe Anleitung, Abschnitt „Ältere Macs mit
Intel-Prozessor“.

**Einrichten und starten,** im Projektverzeichnis:

1. Virtuelle Umgebung anlegen: `python -m venv .venv`
2. Aktivieren: `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3. Abhängigkeiten installieren: `pip install -r requirements.txt`
4. Stimmen für Ansage und Reiter Sprechen laden (gut 120 MB):
   `packaging/get_voice.sh`. Unter Windows läuft das Skript in der Git Bash
   (kommt mit Git für Windows). Ohne Stimmen läuft alles außer der
   Sprachausgabe.
5. Starten: `python main.py`. Das Hauptfenster öffnet sich.

Die Daten (`stats/`, `window_state.json` …) liegen dann im
Projektverzeichnis.

**Kommandozeile:**

```bash
python main.py --version              # Version anzeigen
python main.py --selftest probe.mp3   # Selbsttest ohne Fenster: Ton, Stimmen, MP3
MORSETRAINER_LANG=en python main.py   # Oberfläche auf Englisch (Linux, macOS)
```

`MORSETRAINER_LANG` hat Vorrang vor der Einstellung; die Sprache, mit der
das Programm lief, wird beim Beenden als Einstellung gespeichert.

`--selftest` prüft, ob PortAudio, Tcl/Tk, beide Stimmen und der MP3-Export
vorhanden sind, schreibt eine kurze Probe als MP3 und endet mit Code 0
(sonst 1 und dem Grund).

## Tests

Die Tests laufen ohne Soundkarte (`tests/__init__.py` ersetzt
`sounddevice` durch eine Attrappe) und mit eigenem Datenverzeichnis; deine
Übungsdaten bleiben unberührt. Für die Oberflächen-Tests braucht es einen
Bildschirm.

```bash
python -m unittest discover tests        # alle Tests
python -m unittest tests.test_i18n       # nur ein Modul
xvfb-run -a python -m unittest discover tests   # Linux ohne Bildschirm (Server, CI)
```

Bei jedem Push auf `main` und bei Pull-Requests laufen die Tests auf
GitHub (`.github/workflows/tests.yml`): unter Linux mit Python 3.10 und
3.12, dazu eine Installationsprobe unter Windows und macOS.

## Texte, Übersetzung und Anleitung

- Die deutschen Texte stehen im Code und sind zugleich die Schlüssel:
  `tr("…")` übersetzt bei der Anzeige, `N_("…")` markiert Texte, die erst
  später übersetzt werden. Die englischen Texte stehen in
  `morsetrainer/i18n_en.py`. `tests/test_i18n.py` prüft, dass es zu jedem
  markierten Text eine Übersetzung mit denselben Platzhaltern gibt.
- Die Anleitung (`docs/Anleitung.md`, `docs/Anleitung.en.md`) zeigt das
  Programm im Hilfefenster an (`morsetrainer/widgets/help_window.py`). Das
  Hilfefenster kennt nur einen Teil von Markdown: Überschriften, Absätze, Listen,
  fett, kursiv, Code, Codeblöcke, Links (nur der Text) und Tabellen; Bilder
  fallen weg. Der Knopf Hilfe springt zur Überschrift mit dem Namen des
  aktuellen Reiters, diese Überschriften müssen also genau so heißen wie
  die Reiter. Beide Sprachen haben dieselbe Gliederung.
- Was sich je Version ändert, steht in `CHANGELOG.md` und
  `CHANGELOG.en.md`.

## Projektstruktur

```
main.py              Startdatei
morsetrainer/
  app.py             Hauptfenster mit allen Reitern
  i18n.py            Sprache (Deutsch/Englisch), Texte in i18n_en.py
  core/              Morsecode, Ton, Bandbedingungen, Texte, Statistik,
                     Datenbank, Tagesübung, Diplome, Sicherung
  modes/             ein Modul je Trainingsreiter
  net/               Netzwerkmodus (Trainer, Teilnehmer, Auswertung), Updates
  widgets/           wiederverwendbare Oberflächen-Bausteine, Hilfefenster
  assets/            Programm-Icons und Motive der Diplome
tests/               automatische Tests
docs/                Anleitung, Entwicklung, Bilder für die README
packaging/           Bauen: AppImage-Skript, Stimmen (get_voice.sh),
                     PyInstaller-Hooks, feste Versionen (constraints.txt),
                     Icon, Desktop-Datei
tools/motive/        Motive der Diplome: Zeichnungen (quellen/) und stich.py,
                     das daraus morsetrainer/assets/motive/ erzeugt
.github/workflows/   Tests; baut AppImage, exe und Mac-App für Releases, mit SHA256SUMS.txt
```

## Bauen und Release

Das AppImage lässt sich unter Linux auch lokal bauen:
`packaging/build_appimage.sh` legt `dist/Morsetrainer-x86_64.AppImage` an.
Voraussetzungen: `pyinstaller` in der aktiven Umgebung, `libportaudio2`
und `appimagetool` im `PATH` (oder in `$APPIMAGETOOL`). Die exe und die
Mac-App baut GitHub; die PyInstaller-Befehle dafür stehen in
`.github/workflows/release.yml`.

Ein Tag `vX.Y` startet `.github/workflows/release.yml`: Es baut AppImage,
exe und Mac-App (ZIP, nur Apple-Prozessor, nicht signiert) mit den festen
Versionen aus `packaging/constraints.txt` und prüft jedes gebaute
Programm mit `--selftest`. Nur wenn das und die Tests gelingen, schreibt es
`SHA256SUMS.txt` und legt alles mit dem Abschnitt der Version aus
`CHANGELOG.md` und darunter (ab „### English“) aus `CHANGELOG.en.md` als Release an; das Update-Fenster im
Programm zeigt den Teil in der Sprache der Oberfläche. Das Update im
Programm lädt nur Dateien, die zu `SHA256SUMS.txt` passen
(`morsetrainer/net/update.py`).

## Mitmachen

Fehler, Wünsche und Fragen bitte als
[Issue auf GitHub](https://github.com/tilde1970/Morsetrainer/issues).
Kommentare, Docstrings und Oberflächentexte sind deutsch; Kommentare
beschreiben den Zweck, nicht die Versionsgeschichte.
