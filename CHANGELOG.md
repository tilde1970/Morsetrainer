# Änderungen

## 2.13

- **Neuer Reiter „Sprechen“ (Hören & Sagen):** ohne Tastatur üben wie mit
  Morse Code Ninja. Nach dem Morsezeichen sagst du laut, was du gehört hast;
  dann sagt eine Stimme (Piper, offline) die Lösung an und das Zeichen kommt
  noch einmal. Für Zeichen, Gruppen, Wörter, Wendungen und Rufzeichen;
  Zeichen und Rufzeichen werden buchstabiert, Wörter und Wendungen als Ganzes
  bzw. mit ihrer Bedeutung angesagt.
- **Als MP3 speichern:** dieselbe Übung als Datei für Handy oder Auto.
- **Klartext im Reiter Kontinuierlich:** statt Zufallszeichen auch Wörter,
  QSO-Wendungen („TNX FER CALL“, „UR RST 599“), Rufzeichen oder ganze QSOs
  am Stück.
- **Lernkartei (Wiederholung über Tage):** Sicher und flüssig erkannte
  Zeichen kommen nach 1, 2, 4, 8, 16 und 32 Tagen wieder, unsichere schon am
  nächsten Tag. Entschieden wird einmal am Tag ab 5 Versuchen; hochgestuft
  nur aus Zufallszeichen, weil in Wörtern und Klartext der Zusammenhang
  mithilft. Fällige Zeichen kommen mit „schwache bevorzugt“ öfter; im Reiter
  Statistik lassen sie sich gezielt üben.
- **Zeichen pro Minute:** Neben den WPM-Feldern steht das Tempo auch in
  ZpM (≈ 5 × WPM nach der PARIS-Norm). Die Statistik zeigt zusätzlich die
  tatsächlich erreichten Zeichen pro Minute, gemessen aus den richtig
  erkannten Zeichen und der dafür gebrauchten Zeit.
- **English:** Die Oberfläche gibt es jetzt auch auf Englisch, umschaltbar
  unter „▸ Weitere Optionen“ → „Sprache / Language“ (wirkt nach Neustart).
  Hilfe, Bedeutungen der Abkürzungen und die Fragen beim Kopfhören sind mit
  übersetzt; die Stimme im Reiter „Sprechen“ bleibt deutsch.

## 2.12

- **Programmicon:** Fenster, Taskleiste und die Windows-exe zeigen jetzt
  dasselbe Icon wie Gear Lever (blau mit Punkt, Strich und „CW“).

## 2.11

- **Hilfe im Programm:** Der Knopf „Hilfe“ in der Fußzeile zeigt diese
  Änderungen und die Anleitung (README).
- **Unsichere Antworten:** Die angenommene Latenz für richtige, aber unsichere
  Zeichen (nach Wiederholen oder zu langsam) fließt nicht mehr in den üblichen
  Wert ein, an dem sie gemessen wird. Sonst stieg der Maßstab mit jedem
  Durchgang, besonders bei „Erst merken“.

## 2.10

- Richtige, aber unsichere Zeichen zählen mit der doppelten üblichen Latenz
  (höchstens 5 s) statt pauschal 5 s. Sie kommen öfter dran, ohne die
  Gewichtung zu überziehen. Im Rufzeichen-Reiter gilt dafür der
  Rufzeichen-Zeichensatz.

## 2.9

- **Rufz-Durchgang** im Reiter Rufzeichen (angelehnt an RufzXP): 50 Rufzeichen,
  je ein Versuch, das Tempo wächst mit, Punkte = Länge × effektives Tempo,
  Bestwert mit Starttempo und Verlauf.
- **Verpasste Rufzeichen nachhören** nach dem Rufz, auch die zu langsam
  erkannten: erst nur hören, dann mit Lösung und deiner Eingabe noch einmal,
  im Originaltempo. F6 nochmal, F7 von vorn, Esc anhalten.
- **Wörter:** „Erst merken“ ist Standard (bestehende Einstellungen werden
  einmalig umgestellt). Neue Kürzel wie DX, CU, RPRT, UFB, DOK, SN, BN, WKG,
  dazu R, K und die Betriebszeichen KN und SK. Ein schwaches Zeichen kommt
  öfter, aber in wechselnden Wörtern.
- **Zeitfenster sichtbar:** Nach dem Ton steht, wie zügig die Antwort kommen
  soll; zu langsame Antworten werden vermerkt.
- **QSO:** neue Auswertung „Kopfhören + Fragen“ mit Inhaltsfragen (Name, QTH,
  Rig, Wetter … bzw. Austausch); Pile-ups einstellbar, Standard „Kurz“ mit
  geschätzter Dauer.
- **Einzelzeichen:** Rückmeldung mit eigener Zeit und Limit; nach einer
  Verwechslung Korrekturton richtig – getippt – richtig.
- **Statistik:** Verwechslungen der letzten 30 Tage.
- **Kontinuierlich:** Gegenüberstellung nach dem Stoppen, F5 startet und
  stoppt, Esc stoppt.
- **Contest:** „?“ im Call-Feld fragt nach (DL1?, DL?ABC), Zusammenfassung
  nach Fehlerart, Tempo- und Tonhöhen-Streuung der Anrufer einstellbar, F10
  startet und beendet.

## 2.8

- **Ehrliche Messwerte in allen Reitern:** Nur der erste Versuch geht in die
  Statistik; für die Koch-Lektion zählt er nur ohne Wiederholen und im
  Zeitfenster. Kopfhören ist selbst bewertet und zählt nicht mit.
- **Einheitliche Tempo-Regel:** Angepasst wird das effektive Tempo, erst über
  die Farnsworth-Pausen, dann über das Zeichentempo (nicht unter 15 WPM).
- **Rufzeichen:** standardmäßig nur aus gelernten Zeichen, Anhänge wie /P
  seltener und realistischer.
- **Wörter:** erst ab 10 passenden Wörtern, Wörter mit dem neuesten
  Koch-Zeichen bevorzugt.
- **Kontinuierlich:** Zeichen in Gruppen mit Wortpause.
- **Contest:** Anrufer antworten auch auf ein fast richtiges Call; unbemerkt
  steht „Busted“ im Log.

## 2.7

- Behoben: In Gruppen, Wörtern und Rufzeichen blieb seit 2.5 der Durchgang
  nach einer richtigen Antwort stehen.

## 2.6

- AppImage mit eingebetteter Update-Information, damit Programme wie Gear
  Lever neue Versionen finden.

## 2.5

- Koch-Lektionen 41–44: die Betriebszeichen AR, KN, SK und BK.
- Nach 90 % in Einzelzeichen wird der Wechsel zu den Gruppen angeboten.
- Vertipper landen nicht mehr in der Verwechslungsübung.

## 2.4

- Einzelzeichen: Zeitlimit standardmäßig an; ein falsches Zeichen wird mit
  Lösung vorgespielt und erst nach ein paar anderen erneut abgefragt.
- Die Leertaste stoppt nicht mehr versehentlich den Durchgang.

## 2.3

- Neue, kompakte Oberfläche mit eigenem Design, alle Reiter gleich aufgebaut.
- Regler für die Lautstärke der Störgeräusche.
- Bedeutungen von QRL, CUAGN und NR ergänzt.

## 2.2

- **Lernweg nach Koch:** Lektionen mit Aufstieg bei 90 %, neues Zeichen
  anhören, Koch-Tempo 20/10.
- **Neuer Reiter Wörter** mit Bedeutung und eigenen Wörtern (woerter.txt).
- Eingabearten Mitschreiben, Erst merken und Kopfhören; Fehlerstellen
  markiert.
- Gruppenlänge und Tempo wachsen auf Wunsch mit; Bandbedingungen in drei
  Stufen.
- Einzelzeichen mit mitwachsendem Zeitlimit, Verwechslungen gezielt üben,
  Tagesziel mit Serie.
- Robuster: Datendateien werden sicher geschrieben, Fehler der Tonausgabe
  beenden den Durchgang mit Meldung.

## 2.1

- Die Leertaste wiederholt in Einzelzeichen, Gruppen und Rufzeichen.

## 2.0

- Erste Version: Einzelzeichen, Gruppen, Rufzeichen, Kontinuierlich, QSO mit
  Pile-up und Bandbedingungen, Contest als Run-Station (ähnlich Morse Runner),
  Statistik mit Verwechslungen und Fortschrittsverlauf.
- Fertige Programme als AppImage (Linux) und exe (Windows).
