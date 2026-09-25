# Morsetrainer

Ein CW-Trainer für Einsteiger bis Contester, entwickelt von **DL4YM**.

Vom Lernen einzelner Zeichen nach der Koch-Methode bis zum eigenen
Contest-Pile-up unter realistischen Kurzwellenbedingungen.

## Trainingsmodi

| Reiter | Was du übst |
|---|---|
| **Einzelzeichen** | Einzelne Zeichen erkennen, gemessen wird auch die Reaktionszeit. |
| **Gruppen** | Zeichengruppen hören und als Ganzes eingeben. |
| **Rufzeichen** | Echte Rufzeichen aus der Super-Check-Partial-Liste, auf Wunsch mit /P, /M, OE/… |
| **Kontinuierlich** | Der Ton läuft ohne Pause durch, du tippst mit (wie beim Mithören). |
| **QSO** | Komplette QSOs hören: normales QSO oder Contest-Runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) mit Pile-ups. Auswertung per Abfrage/Log, durch Mittippen oder nur zum Hören. |
| **Contest** | Du bist selbst die Run-Station (ähnlich Morse Runner): CQ rufen, Anrufer aufnehmen, Austausch geben, loggen. Das Log wird am Ende geprüft. |
| **Statistik** | Gesamtstatistik je Zeichen, häufigste Verwechslungen und Fortschrittsverlauf je Modus. |

### Bandbedingungen (QSO und Contest)

Einzeln zuschaltbar und regelbar: Rauschen, Knackstörungen (QRN), QSB,
Chirp, SSB-Gebrabbel und CW-QRM auf der Nachbarfrequenz.

### Tastenkürzel

- **QSO:** F5 neues QSO/Stop, F6 nochmal hören, F7 Text zeigen, F8 prüfen.
- **Contest:** F1 CQ, F2 Austausch, F3 TU/loggen, F4 eigenes Call,
  F5 sein Call, F7 „?“, F8 „AGN“. Enter sendet die passende nächste
  Nachricht (ESM), Esc bricht das Senden ab.

## Installation und Start

Voraussetzung ist Python 3.10 oder neuer mit Tk.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
  core/              Morsecode, Ton, Bandbedingungen, Texte, Statistik
  modes/             ein Modul je Trainingsreiter
  widgets/           wiederverwendbare Oberflächen-Bausteine
tests/               automatische Tests
```

## Daten

- `stats/`: Sitzungsprotokolle, Gesamtstatistik (`all_time.json`) und
  Ergebnisse von QSO-Abfragen und Contests (`results.jsonl`).
- `window_state.json`: Fenstergröße und alle Einstellungen.
- `callsigns.scp`: Rufzeichenliste (Super Check Partial). Sie ist **nicht
  im Repository enthalten**. Lade die aktuelle `MASTER.SCP` von
  [supercheckpartial.com](https://www.supercheckpartial.com) herunter und
  lege sie als `callsigns.scp` ins Programmverzeichnis. Ohne die Datei
  erzeugt der Trainer Rufzeichen nach Landesmuster.

## Lizenz

MIT, siehe [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
