# Morsetrainer

Ein CW-Trainer für Einsteiger bis Contester, entwickelt von **DL4YM**.

Vom Lernen einzelner Zeichen nach der Koch-Methode bis zum eigenen
Contest-Pile-up unter realistischen Kurzwellenbedingungen.

## Trainingsmodi

| Reiter | Was du übst |
|---|---|
| **Einzelzeichen** | Einzelne Zeichen erkennen, gemessen wird auch die Reaktionszeit. Mit Zeitlimit (Instant Character Recognition): Das Limit wird kürzer, solange du sicher bist. |
| **Gruppen** | Zeichengruppen hören und mitschreiben. Die Gruppenlänge wächst auf Wunsch mit: kurz anfangen, nach 5 richtigen Gruppen eine länger, nach 2 Fehlern eine kürzer. |
| **Wörter** | CW-Abkürzungen, Q-Gruppen und QSO-Wörter, nur aus den Zeichen, die du schon kannst. Nach der Antwort wird die Bedeutung angezeigt. Eigene Wörter lassen sich ergänzen (siehe Daten). |
| **Rufzeichen** | Echte Rufzeichen aus der Super-Check-Partial-Liste, auf Wunsch mit /P, /M, OE/… |
| **Kontinuierlich** | Der Ton läuft ohne Pause durch, du tippst mit (wie beim Mithören). |
| **QSO** | Komplette QSOs hören: normales QSO oder Contest-Runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) mit Pile-ups. Auswertung per Abfrage/Log, durch Mittippen oder nur zum Hören. |
| **Contest** | Du bist selbst die Run-Station (ähnlich Morse Runner): CQ rufen, Anrufer aufnehmen, Austausch geben, loggen. Das Log wird am Ende geprüft. |
| **Statistik** | Gesamtstatistik je Zeichen, häufigste Verwechslungen (mit Knopf, um sie gezielt zu üben), Tagesziel und Fortschrittsverlauf je Modus. |

In **Gruppen, Wörter und Rufzeichen** kannst du wählen:

- **Eingabe:** *Mitschreiben* (tippen, während der Ton läuft), *Erst merken*
  (tippen nach dem Ton) oder *Kopfhören* (nichts tippen; Enter löst auf, dann
  J = gewusst, N = nicht gewusst).
- **Tempo wächst mit** (wie bei RufzXP): richtig beim ersten Versuch +1 WPM,
  jeder Fehlversuch −1 WPM. Der Fortschrittsverlauf zeigt dann das erreichte
  Tempo.
- **Bandbedingungen** in drei Stufen: leicht, mittel, stark.

### Lernweg für Einsteiger

1. **Koch-Lektion** oben auf 1 stellen (K und M) und mit **Koch-Tempo 20/10**
   das empfohlene Tempo setzen: Die Zeichen kommen schnell genug, dass du
   sie als Klangbild hörst statt Punkte und Striche zu zählen, dafür mit
   längeren Pausen dazwischen. „▶ anhören“ spielt das neue Zeichen vor.
2. Im Reiter **Einzelzeichen** die Zeichen kennenlernen.
3. Im Reiter **Gruppen** üben. Schreib mit, während der Ton läuft, wie beim
   Einzelzeichen. Falsche Stellen werden markiert, und nach 3 Fehlversuchen
   siehst und hörst du die Lösung.
4. Wer in den Gruppen (oder im Modus Kontinuierlich) in einem Durchgang mit
   mindestens 50 Zeichen 90 % beim ersten Versuch schafft, bekommt die
   nächste Lektion angeboten. Schwache und neue Zeichen kommen automatisch
   öfter dran.
5. Ab etwa Lektion 5 lohnt sich der Reiter **Wörter**, danach
   **Kontinuierlich** und **QSO**.
6. Sitzen die Zeichen, im Reiter **Einzelzeichen** das **Zeitlimit**
   einschalten: Dann bleibt keine Zeit mehr zum Zählen, das Zeichen muss als
   Reflex kommen.
7. Im Reiter **Statistik** zeigt „Die 4 häufigsten gezielt üben“, welche
   Zeichen du verwechselst, und übt genau diese gegeneinander. „↩ Lektion“
   oben führt zurück zu deiner Lektion.

Außerdem hilfreich:

- **Täglich kurz** üben schlägt selten lang: Die Fußzeile zeigt die heutige
  Übungszeit, das Tagesziel (einstellbar im Reiter Statistik) und wie viele
  Tage in Folge du es erreicht hast.
- **Tonhöhe und Tempo leicht variieren** (gemeinsame Einstellung): Wer immer
  nur genau einen Klang hört, tut sich auf dem Band schwerer.

### Bandbedingungen (QSO und Contest)

Einzeln zuschaltbar und regelbar: Rauschen, Knackstörungen (QRN), QSB,
Chirp, SSB-Gebrabbel und CW-QRM auf der Nachbarfrequenz.

### Tastenkürzel

- **Einzelzeichen, Gruppen, Wörter, Rufzeichen:** Leertaste wiederholt.
  Beim Kopfhören: Enter löst auf, J = gewusst, N = nicht gewusst.
- **QSO:** F5 neues QSO/Stop, F6 nochmal hören, F7 Text zeigen, F8 prüfen.
- **Contest:** F1 CQ, F2 Austausch, F3 TU/loggen, F4 eigenes Call,
  F5 sein Call, F7 „?“, F8 „AGN“. Enter sendet die passende nächste
  Nachricht (ESM), Esc bricht das Senden ab.

## Download

Fertige Programme gibt es unter
[Releases](https://github.com/tilde1970/Morsetrainer/releases):

- **Linux:** `Morsetrainer-x86_64.AppImage` herunterladen, ausführbar machen
  (`chmod +x Morsetrainer-x86_64.AppImage`) und starten.
- **Windows:** `Morsetrainer.exe` herunterladen und starten. Da die Datei
  nicht signiert ist, warnt Windows SmartScreen beim ersten Start
  („Weitere Informationen“ → „Trotzdem ausführen“).

Python wird dafür nicht benötigt.

## Aus dem Quelltext starten

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
packaging/           AppImage-Build (Icon, Desktop-Datei)
.github/workflows/   baut AppImage und exe für Releases
```

## Daten

Aus dem Quelltext gestartet liegen die Daten im Programmverzeichnis, beim
AppImage in `~/.local/share/morsetrainer/`, bei der exe in
`%APPDATA%\Morsetrainer\`.


- `stats/`: Sitzungsprotokolle, Gesamtstatistik (`all_time.json`),
  Ergebnisse von QSO-Abfragen und Contests (`results.jsonl`) und die
  Übungszeit pro Tag (`practice.json`).
- `window_state.json`: Fenstergröße und alle Einstellungen.
- `callsigns.scp`: Rufzeichenliste (Super Check Partial). Sie ist **nicht
  im Repository enthalten**. Lade die aktuelle `MASTER.SCP` von
  [supercheckpartial.com](https://www.supercheckpartial.com) herunter und
  lege sie als `callsigns.scp` in das Datenverzeichnis. Ohne die Datei
  erzeugt der Trainer Rufzeichen nach Landesmuster.
- `woerter.txt`: eigene Wörter für den Reiter „Wörter“, eins pro Zeile,
  optional mit Bedeutung: `DOK = Distrikts-Ortsverbandskenner`. Der Knopf
  „Eigene Wörter bearbeiten“ legt die Datei mit Anleitung an und öffnet sie.
  Die Wörter kommen zu den eingebauten dazu.

## Lizenz

MIT, siehe [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
