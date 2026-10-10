# Morsetrainer

Ein Trainer für Morsetelegrafie (CW) für Windows, Linux und macOS, für
Einsteiger ohne Vorkenntnisse bis zu Contestern (Teilnehmern an
Funkwettbewerben), entwickelt von **DL4YM**.

Vom Lernen einzelner Zeichen nach der Koch-Methode bis zum eigenen
Contest-Pile-up unter realistischen Kurzwellenbedingungen – allein am
eigenen Rechner oder gemeinsam am Clubabend im lokalen Netz.

**English:** The program can be switched to English under
„Einstellungen …“ (or Ctrl+Comma) → „Sprache / Language“. English overview: [README.en.md](README.en.md).

## Was er kann

- **Koch-Methode** mit den Lektionen von lcwo.net und Koch-Tempo 20/10:
  Zeichen als Klangbild hören statt Punkte und Striche zu zählen. Die
  nächste Lektion wird angeboten, sobald 90 % sitzen.
- **Tagesübung (10 Min):** stellt zusammen, was heute dran ist –
  Aufwärmen, Hauptteil, Ausklang – mit drei Sternen am Tag und Wochenziel.
- **Übungen:** Einzelzeichen mit Zeitlimit, Gruppen, Wörter und
  Q-Gruppen, echte Rufzeichen (auch als Rufz-Durchgang), Mitschreiben im
  Fluss, Hören & Sagen ohne Tastatur (auch als MP3), komplette QSOs und
  Contest-Betrieb als Run-Station wie im Morse Runner.
- **Bandbedingungen:** Rauschen, QRN, QSB, Chirp, SSB-Gebrabbel und
  CW-QRM, einzeln regelbar.
- **Statistik:** je Zeichen, Lernkartei über Tage, häufigste
  Verwechslungen zum gezielten Üben, Diplome in Bronze, Silber und Gold
  zum Ausdrucken, Lebenslinie.
- **Netzwerk:** Kurs oder Clubabend im lokalen Netz. Der Trainer gibt vor,
  alle hören dieselbe Sequenz und tippen mit, der Trainer sieht live, wer
  was getippt hat. Auch mit festem Takt für Papier und Bleistift.
- **Barrierefrei:** Der Trainer soll auch ohne Blick auf den Bildschirm
  bedienbar sein. Eine eingebaute Stimme sagt Ergebnisse, Reiter, Fenster
  und Bedienelemente an, alles geht mit der Tastatur, dazu Schriftgröße
  bis 200 % und hoher Kontrast.

## So sieht er aus

### Mitschreiben im Koch-Tempo

<img src="docs/bilder/gruppen.png" width="640" alt="Hauptfenster im Reiter Einzeln mit dem Inhalt Gruppen. Oben Koch-Lektion 15, 20 WPM, 600 Hz und Farnsworth 10. Mitten im Durchgang: das Antwortfeld mit ESJ, die Rückmeldung „Richtig: ESJ“ und darunter die Statistik des Durchgangs, 3 von 3 richtig.">

### Diplom zum Ausdrucken

<img src="docs/bilder/diplom.png" width="640" alt="Beispiel-Diplom Koch in Gold für DL1ABC, Max Mustermann, im Stil einer Urkunde: links eine Handtaste, rechts ein Clubheim mit Antennenmast, unten ein goldenes Siegel, oben rechts die Diplom-Nummer.">

### Clubabend im Netzwerk

<img src="docs/bilder/netzwerk.png" width="640" alt="Tabelle des Trainers am Clubabend mit vier Teilnehmern: je Name der Status, die aktuelle Antwort, der Anteil richtiger Zeichen, die flüssig richtigen Sequenzen und die Zeit. Darunter das Ergebnis der Gruppe, 97 % der Zeichen richtig und 85 % der Sequenzen flüssig, die häufigsten Fehler und die Tempo-Empfehlung.">

## Download

Fertige Programme gibt es unter
[Releases](https://github.com/tilde1970/Morsetrainer/releases), Python
wird dafür nicht benötigt:

- **Linux:** `Morsetrainer-x86_64.AppImage` herunterladen, ausführbar machen
  (`chmod +x Morsetrainer-x86_64.AppImage`) und starten. Startet es mit
  einer Meldung zu FUSE nicht: siehe
  [Anleitung, Abschnitt „Linux und Windows“](docs/Anleitung.md).
- **Windows:** `Morsetrainer.exe` herunterladen und starten. Da die Datei
  nicht signiert ist, warnt Windows SmartScreen beim ersten Start
  („Weitere Informationen“ → „Trotzdem ausführen“).
- **macOS (Apple-Prozessor):** `Morsetrainer-macOS.zip` herunterladen,
  entpacken und `Morsetrainer.app` in „Programme“ ziehen. Die App ist nicht
  signiert, beim ersten Start musst du sie freigeben. Wie das geht und
  was für Intel-Macs gilt, steht in der
  [Anleitung, Abschnitt macOS](docs/Anleitung.md#macos).

Neben den Programmen liegt `SHA256SUMS.txt` mit den Prüfsummen. Zum
Nachprüfen unter Linux `sha256sum -c --ignore-missing SHA256SUMS.txt`,
unter Windows in der PowerShell `Get-FileHash Morsetrainer.exe` und mit
der Zeile in `SHA256SUMS.txt` vergleichen.

## Erste Schritte

1. Oben **Koch-Lektion 1** einstellen (K und M); „▶ anhören“ spielt das
   neue Zeichen vor.
2. Im Reiter **Einzeln** unter **Zeichen** die Zeichen kennenlernen, dann
   unter **Gruppen** mitschreiben, während der Ton läuft.
3. Oder einfach **▶ Tagesübung (10 Min)** drücken (F12) – sie schaltet die
   Reiter selbst um.
4. Mit Strg+Komma (oder dem Knopf „Einstellungen …“ oben rechts)
   Rufzeichen und Name eintragen; sie stehen auf den Diplomen.

Alles Weitere steht in der [Anleitung](docs/Anleitung.md). Im Programm
öffnet sie F1 oder der Knopf **Hilfe (F1)** unten rechts, gleich beim
Abschnitt des Reiters, in dem du gerade bist.

## Barrierefreiheit

Der Morsetrainer soll auch für Sehbehinderte und Blinde gut nutzbar sein,
daran wird laufend weitergearbeitet:

- **Ansage (F9)** mit eingebauter Stimme, ohne Screenreader: Ergebnis
  jeder Antwort, Ende eines Durchgangs, Reiter, Fenster, Felder und
  Schalter beim Springen mit Tab. **F11** sagt, wo man gerade ist.
- **Tastatur:** Alles ist ohne Maus erreichbar, mit Kürzeln für die
  wichtigsten Abläufe (Tagesübung F12, Bandbedingungen, Reiter).
- **Sehen:** Schriftgröße mit Strg+Plus und Strg+Minus (75–200 %), hoher Kontrast
  (Schwarz, Weiß, Gelb, mindestens 7:1); richtig und falsch stehen immer
  auch als Text da, nicht nur als Farbe.

Screenreader erreichen die Oberfläche (Tk) bisher kaum, deshalb spricht
das Programm selbst. Einzelheiten stehen in der
[Anleitung, Abschnitt 8 „Barrierefreiheit“](docs/Anleitung.md#8-barrierefreiheit).
Rückmeldungen, was noch fehlt oder stört, sind sehr willkommen (siehe
„Rückmeldung“ unten).

## Sicherheit

- **Updates:** Beim Start fragt der Morsetrainer, wenn es ein neueres
  Release gibt, und tauscht auf Wunsch die exe bzw. das AppImage aus.
  Geladen wird nur aus diesem Repository über HTTPS, und die Datei muss zur
  Prüfsumme in `SHA256SUMS.txt` passen. Das fängt beschädigte Downloads
  ab, ersetzt aber keine Signatur: Wer das Release austauschen kann, kann
  auch die Prüfsumme austauschen.
- **Netzwerkmodus:** unverschlüsselt über TCP. Gedacht für das Club- oder
  Heimnetz, nicht für öffentliche WLANs. Nach 5 falschen PINs ist ein
  Rechner eine Minute gesperrt, Unbekannte kann der Trainer entfernen.
  Updates reicht der Trainer nicht weiter, er nennt nur seine
  Versionsnummer.

## Mehr

- [Anleitung](docs/Anleitung.md): alle Reiter, Tagesübung, Diplome,
  Netzwerk, Tastenkürzel, Daten und Sicherung
- [Änderungen](CHANGELOG.md) je Version
- [Entwicklung](docs/Entwicklung.md): aus dem Quelltext starten, Tests,
  Projektstruktur, Release

## Rückmeldung

Fehler, Wünsche und Fragen bitte als
[Issue auf GitHub](https://github.com/tilde1970/Morsetrainer/issues).
Bei einem Programmfehler zeigt der Morsetrainer, wo die Datei `fehler.log`
liegt; leg sie dem Issue bei.

## Lizenz

MIT, siehe [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
