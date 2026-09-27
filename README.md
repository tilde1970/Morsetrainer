# Morsetrainer

Ein CW-Trainer für Einsteiger bis Contester, entwickelt von **DL4YM**.

Vom Lernen einzelner Zeichen nach der Koch-Methode bis zum eigenen
Contest-Pile-up unter realistischen Kurzwellenbedingungen.

## Trainingsmodi

| Reiter | Was du übst |
|---|---|
| **Einzelzeichen** | Einzelne Zeichen erkennen; nach jeder Antwort steht deine Zeit und das aktuelle Limit, z. B. „0,38 s, Limit 1,20 s“. Mit Zeitlimit (Instant Character Recognition): Das Limit wird kürzer, solange du sicher bist. Nach einer Verwechslung hörst du das richtige und dein getipptes Zeichen direkt nacheinander. |
| **Gruppen** | Zeichengruppen hören und mitschreiben. Die Gruppenlänge wächst auf Wunsch mit: kurz anfangen, nach 5 richtigen Gruppen eine länger, nach 2 falschen Gruppen (jeweils beim ersten Versuch) eine kürzer. |
| **Wörter** | CW-Abkürzungen, Q-Gruppen und QSO-Wörter, nur aus den Zeichen, die du schon kannst. Standard ist „Erst merken“: erst das ganze Wort hören, dann tippen; eine zu langsame Antwort wird vermerkt. Auch R, K und die Betriebszeichen KN und SK kommen vor (zählen aber nicht als Wörter für die Mindestzahl). Ein schwaches Zeichen kommt öfter, aber in wechselnden Wörtern. Nach der Antwort wird die Bedeutung angezeigt. Eigene Wörter lassen sich ergänzen (siehe Daten). |
| **Rufzeichen** | Echte Rufzeichen aus der Super-Check-Partial-Liste, standardmäßig nur aus Zeichen, die du schon gelernt hast (ab Koch-Lektion 23 mit der ersten Ziffer). Gelegentlich mit /P, /M, OE/… wie im Contest. Wahlweise als **Rufz-Durchgang** (angelehnt an RufzXP): 50 Rufzeichen, je ein Versuch, das Tempo wächst mit, Punkte = Länge × effektives Tempo, Bestwert (mit Starttempo) und Verlauf; danach lassen sich die verpassten und die zu langsam erkannten Rufzeichen nachhören (F6): erst nur hören, dann mit Lösung noch einmal, im Originaltempo. |
| **Kontinuierlich** | Der Ton läuft ohne Warten durch, du tippst mit (wie beim Mithören); die Zeichen kommen in Gruppen (Standard 5) mit Wortpause dazwischen. Nach dem Stoppen (F5 oder Esc) zeigt eine Gegenüberstellung die letzten Zeichen. Gewertet wird eine Taste nur, wenn sie zum Zeichen passt: nicht vorab geraten und höchstens 5 s danach; zu viel Getipptes zählt als Fehler. |
| **QSO** | Komplette QSOs hören: normales QSO oder Contest-Runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) mit einstellbaren Pile-ups (Standard aus). Auswertung per Abfrage/Log, durch Mittippen, als **Kopfhören + Fragen** (ohne Notizen, danach Inhaltsfragen zu Name, QTH, Rig, Wetter … bzw. Austausch) oder nur zum Hören. Neben der Länge steht die geschätzte Dauer; wie oft vor dem Prüfen „Nochmal“ gehört wurde, wird vermerkt. |
| **Contest** | Du bist selbst die Run-Station (ähnlich Morse Runner): CQ rufen, Anrufer aufnehmen, Austausch geben, loggen. Wie im echten Contest antworten Anrufer manchmal auch auf ein fast richtiges Rufzeichen – wer den Fehler bemerkt, korrigiert das Call und bestätigt mit Enter („Call TU“), sonst steht „Busted“ im Log. „?“ im Call-Feld fragt nach (DL1?, DL?ABC). Tempo- und Tonhöhen-Streuung der Anrufer sind einstellbar, am Ende gibt es eine Zusammenfassung nach Fehlerart; F10 startet und beendet. |
| **Statistik** | Gesamtstatistik je Zeichen, häufigste Verwechslungen (mit Knopf, um sie gezielt zu üben), Tagesziel und Fortschrittsverlauf je Modus. |

In **Gruppen, Wörter und Rufzeichen** kannst du wählen:

- **Eingabe:** *Mitschreiben* (tippen, während der Ton läuft), *Erst merken*
  (tippen nach dem Ton) oder *Kopfhören* (nichts tippen; Enter löst auf, dann
  J = gewusst, N = nicht gewusst). Kopfhören beruht auf deiner eigenen
  Bewertung und zählt daher nicht für die Gesamtstatistik und die Lektion.
- **Tempo wächst mit** (wie bei RufzXP): richtig beim ersten Versuch +1 WPM,
  falsch beim ersten Versuch −1 WPM – gemeint ist das effektive Tempo. Mit
  Farnsworth werden erst die Pausen kürzer; sind sie weg, wird das
  Zeichentempo schneller. Langsamer werden die Zeichen höchstens bis 15 WPM,
  darunter werden die Pausen länger, damit man nicht mitzählen kann. Dieselbe
  Regel gilt für „Tempo automatisch anpassen“ im QSO-Reiter. Der
  Fortschrittsverlauf zeigt das effektive Tempo (z. B. 10 bei 20/10 WPM).
- **Bandbedingungen** in drei Stufen: leicht, mittel, stark.

### Lernweg für Einsteiger

1. **Koch-Lektion** oben auf 1 stellen (K und M). Voreingestellt ist das
   **Koch-Tempo 20/10** (unter „▸ Weitere Optionen“ jederzeit wieder
   herstellbar): Die Zeichen kommen schnell genug, dass du sie als Klangbild
   hörst statt Punkte und Striche zu zählen, dafür mit längeren Pausen
   dazwischen. „▶ anhören“ spielt das neue Zeichen vor.
2. Im Reiter **Einzelzeichen** die Zeichen kennenlernen. Das **Zeitlimit**
   ist von Anfang an eingeschaltet: Es bleibt keine Zeit zum Zählen von
   Punkten und Strichen, das Zeichen muss als Klangbild kommen. Ein falsch
   erkanntes Zeichen hörst du gleich noch einmal, während die Lösung
   dasteht; abgefragt wird es erst nach ein paar anderen Zeichen wieder.
   Die Leertaste wiederholt ein Zeichen, verlängert aber die Frist nicht;
   erst nach der Wiederholung erkannt zählt als nicht erkannt.
   Nach einem Durchgang mit mindestens 50 Zeichen und 90 % richtig – mit
   Zeitlimit von Anfang bis Ende, am Schluss höchstens 1,5 s – schlägt die
   App vor, bei den Gruppen weiterzumachen.
3. Im Reiter **Gruppen** üben. Schreib mit, während der Ton läuft, wie beim
   Einzelzeichen. Nach einem Fehler werden nur die falschen Stellen markiert
   und die Gruppe kommt noch einmal – hör sie dir an, statt sie abzulesen.
   Nach 3 Fehlversuchen siehst und hörst du die Lösung.
4. Wer in den Gruppen (oder im Modus Kontinuierlich) in einem Durchgang mit
   mindestens 50 Zeichen 90 % beim ersten Versuch schafft, bekommt die
   nächste Lektion angeboten. Für die Lektion zählt ein erster Versuch nur,
   wenn du die Gruppe nicht mit der Leertaste wiederholt hast und zügig
   geantwortet hast (1,5 s plus 0,6 s je Zeichen nach Tonende); zu viel
   Getipptes zählt als Fehler. Schwache und neue Zeichen kommen automatisch
   öfter dran. Nach den 40 Lektionen von lcwo.net folgen in den Lektionen
   41–44 die Betriebszeichen aus dem QSO: AR (Taste `+`), KN (`(`),
   SK (`*`) und BK (`#`).
5. Ab Lektion 6 gibt es genug Wörter für den Reiter **Wörter** (Wörter mit
   dem neuesten Zeichen kommen bevorzugt), danach
   **Kontinuierlich** und **QSO**.
6. Im Reiter **Statistik** (Verwechslungen der letzten 30 Tage) zeigt „Die 4 häufigsten gezielt üben“, welche
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

### Hilfe im Programm

Der Knopf **Hilfe** rechts in der Fußzeile zeigt die Änderungen der
Versionen (CHANGELOG.md) und diese Anleitung.

### Tastenkürzel

- **Einzelzeichen, Gruppen, Wörter, Rufzeichen:** Leertaste wiederholt.
  Beim Kopfhören: Enter löst auf, J = gewusst, N = nicht gewusst.
- **Rufz (nach dem Durchgang):** F6 verpasste Rufzeichen nachhören bzw. das aktuelle nochmal, F7 von vorn, Esc anhalten.
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
