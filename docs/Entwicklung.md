# Morsetrainer – Entwicklung

Für alle, die den Morsetrainer aus dem Quelltext starten oder daran
mitarbeiten möchten. Die Bedienung beschreibt die [Anleitung](Anleitung.md).

## Aus dem Quelltext starten

Voraussetzung ist Python 3.10 oder neuer mit Tk, dazu PortAudio für den
Ton. Unter Linux fehlen diese Pakete oft:

```bash
sudo apt install python3-venv python3-tk libportaudio2   # Debian, Ubuntu, Mint
sudo dnf install python3-tkinter portaudio               # Fedora
```

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
packaging/get_voice.sh           # Stimmen für Ansage und Reiter Sprechen (gut 120 MB)
python main.py
```

Unter Windows läuft `get_voice.sh` in der Git Bash (kommt mit Git für
Windows). Ohne Stimmen läuft alles außer der Sprachausgabe.

Tests:

```bash
python -m unittest discover tests
```

## Projektstruktur

```
main.py              Startdatei
morsetrainer/
  app.py             Hauptfenster mit allen Reitern
  i18n.py            Sprache (Deutsch/Englisch), Texte in i18n_en.py
  core/              Morsecode, Ton, Bandbedingungen, Texte, Statistik
  modes/             ein Modul je Trainingsreiter
  net/               Netzwerkmodus (Trainer, Teilnehmer, Auswertung), Updates
  widgets/           wiederverwendbare Oberflächen-Bausteine
tests/               automatische Tests
docs/                Anleitung, Entwicklung, Bilder für die README
packaging/           AppImage-Build (Icon, Desktop-Datei)
tools/motive/        Motive der Diplome: Zeichnungen (quellen/) und stich.py,
                     das daraus morsetrainer/assets/motive/ erzeugt
.github/workflows/   baut AppImage, exe und Mac-App für Releases, mit SHA256SUMS.txt
```

## Release

Ein Tag `vX.Y` startet `.github/workflows/release.yml`: Es baut AppImage,
exe und Mac-App (ZIP, nur Apple-Prozessor, nicht signiert), schreibt `SHA256SUMS.txt` und legt alles mit dem Abschnitt der
Version aus `CHANGELOG.md` als Release an. Das Update im Programm lädt nur
Dateien, die zu `SHA256SUMS.txt` passen (`morsetrainer/net/update.py`).
