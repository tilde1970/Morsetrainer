# Morsetrainer – Entwicklung

Für alle, die den Morsetrainer aus dem Quelltext starten oder daran
mitarbeiten möchten. Die Bedienung beschreibt die [Anleitung](Anleitung.md).

## Aus dem Quelltext starten

Voraussetzung ist Python 3.10 oder neuer mit Tk.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
packaging/get_voice.sh           # Stimme für den Reiter Sprechen (ca. 63 MB)
python main.py
```

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
.github/workflows/   baut AppImage und exe für Releases, mit SHA256SUMS.txt
```

## Release

Ein Tag `vX.Y` startet `.github/workflows/release.yml`: Es baut AppImage
und exe, schreibt `SHA256SUMS.txt` und legt alles mit dem Abschnitt der
Version aus `CHANGELOG.md` als Release an. Das Update im Programm lädt nur
Dateien, die zu `SHA256SUMS.txt` passen (`morsetrainer/net/update.py`).
