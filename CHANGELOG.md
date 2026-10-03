# Änderungen

## 2.22

- **Tagesübung:** Ein Knopf oben (oder F12) stellt zehn Minuten aus dem
  zusammen, was dran ist – Aufwärmen mit fälligen Zeichen, Hauptteil mit
  Gruppen in festem Tempo, Ausklang mit Wörtern, Rufzeichen oder
  Kontinuierlich, je nach Lektion – und schaltet die Reiter selbst um.
  Die nächste Lektion kommt ohne Nachfrage am Tag nach dem geschafften
  Kriterium; das Tempo wird währenddessen nur bei Bedarf langsamer und
  erst nach Koch auch schneller, einmal am Tag. Drei Sterne am Tag
  (Dabei, Sauber, Weiter), Zwischenkarten zwischen den Blöcken und eine
  Abendbilanz mit Vergleich zur Vorwoche und „Noch 5 Min“. Danach sind
  alle Einstellungen wieder wie vorher. Siehe README, „Tagesübung“.
- **Tagesziel** ist jetzt standardmäßig 10 Minuten (wie die Tagesübung);
  ein schon eingestelltes Ziel bleibt.
- **Einzelzeichen, Zeitlimit:** Das Limit pendelt sich jetzt dort ein, wo
  knapp neun von zehn Zeichen rechtzeitig kommen; bisher war bei jedem
  Stand etwa jedes dritte Zeichen „zu langsam“. Eine Verwechslung macht
  das Limit nicht mehr länger, nur ein verpasstes Zeichen – sonst wuchs es
  bei vielen Verwechslungen, bis wieder Zeit zum Zählen blieb. Untergrenze
  0,5 s statt 0,4 s – darunter würde Reaktionsschnelle geübt, nicht das
  Erkennen.
- **Erstes Zeichen fehlt nicht mehr:** Unter Linux legte das Audiosystem
  das Ausgabegerät nach kurzer Stille schlafen, und vom ersten Zeichen
  nach Start oder Pause fehlte der Anfang (besonders mit
  Bluetooth-Kopfhörern). Der Morsetrainer hält das Gerät jetzt wach.

## 2.21

- **Netzwerk, Papier abtippen:** Nach einem Durchgang im festen Takt trägt
  der Trainer Papierbögen von Teilnehmern ohne Rechner unter
  „Papierbogen eintragen“ ein. Teilnehmer mit Rechner können beim
  Verbinden „auf Papier mitschreiben“ wählen und tippen ihren Zettel am
  Ende selbst ab. Gewertet wird richtig/falsch ohne Zeit, also nicht als
  flüssig und nicht für die Tempo-Empfehlung. Neue Protokollversion:
  Trainer und Teilnehmer brauchen dieselbe Programmversion.
- **Antwortbogen drucken:** Im festen Takt öffnet der Trainer einen
  nummerierten Bogen zum Ausdrucken im Browser, bei Gruppen mit einem
  Kästchen je Zeichen.
- **Fehlerprotokoll:** Unerwartete Programmfehler landen jetzt in
  `fehler.log` im Datenverzeichnis, und das Programm sagt einmal, wo die
  Datei liegt. Bisher passierte in exe und AppImage bei so einem Fehler
  einfach nichts.
- **Robuster:** Ein abgerissener Download lässt das Update nicht mehr
  hängen, ein Fehler beim MP3-Export sperrt den Reiter Sprechen nicht mehr,
  und das Fenster schließt auch dann, wenn beim Speichern etwas schiefgeht.
- **Sprechen:** Die 2 heißt jetzt „Zwo“ wie im Funk, Echo klingt wie
  „Ekko“ statt mit deutschem ch.
- **Ehrlichere Zeichenstatistik:** Wörter, Klartext in Kontinuierlich,
  QSO-Mittippen und Klartext im Netzwerk zählen nicht mehr für die
  Zeichenstatistik, die Gewichtung und die Lernkartei, weil der
  Zusammenhang dort viele Zeichen verrät. Im Verlauf erscheinen sie
  weiter. Beim QSO-Mittippen zählen vorausgeahnte Zeichen („DE“, „599“)
  nicht mehr als richtig.
- **Gruppen, Wörter, Rufzeichen:** Nach einem Fehler kommt jetzt gleich
  die Lösung, gezeigt und vorgespielt, und dann die nächste Sequenz, wie
  beim Weiterkopieren im Funkbetrieb. Einstellbar sind bis zu 3
  Fehlversuche, „nie“ gibt es nicht mehr. Ein Zeichen, das erst nach dem
  Wiederholen erkannt wurde, zählt wie bei den Einzelzeichen als nicht
  erkannt.
- **Zu langsames Zeichentempo:** Unter 18 WPM weist jetzt die Kopfleiste in
  allen Reitern darauf hin, dass man die Zeichen mitzählen kann, und bietet
  das Koch-Tempo an; ebenso der Dialog zur nächsten Lektion. „Tempo wächst
  mit“ dehnt die Zeichen nur noch bis 18 WPM (bisher 15), darunter werden
  die Pausen länger.
- **Kontinuierlich:** Bandbedingungen (leicht, mittel, stark) laufen
  durchgehend unter dem ganzen Durchgang.
- **Fällige gezielt üben:** Fehlende fällige Zeichen kommen nur für einen
  Durchgang dazu, danach gilt wieder der Zeichensatz der Lektion.

## 2.20

- **Sprechen:** Das Buchstabieralphabet klingt jetzt richtig. Die deutsche
  Stimme las die englischen Wörter deutsch, etwa „Mike“ als „Micke“ und
  „Zulu“ als „Tsulu“; jetzt sagt sie „Maik“, „Suhlu“ usw.

## 2.19

- **Netzwerk, kontinuierlich:** Die Bandbedingungen liegen jetzt unter dem
  ganzen Durchgang. Bisher waren nur VVV = und + verrauscht, die Gruppen
  dazwischen nicht.

## 2.18

- **Netzwerk:** Neuer Ablauf „Kontinuierlich“: Gruppen ohne Pause für eine
  eingestellte Dauer, alle tippen fortlaufend mit, ohne Enter. Ausgewertet
  wird am Ende wie im Reiter Kontinuierlich und je Gruppe an den Trainer
  gemeldet (Tabelle, Auflösung, CSV). Neue Protokollversion: Teilnehmer
  brauchen dieselbe Version wie der Trainer (das Update wird angeboten).
- **Netzwerk:** QSO-Klartext kommt in Abschnitten bis zum nächsten =, K
  oder Schlusszeichen (etwa „UR RST 599 599 =“) statt Wort für Wort, und
  die Anzahl zählt ganze QSOs (Vorgabe 1). Bisher brach es nach so vielen
  Wörtern ab, wie Sequenzen eingestellt waren.

## 2.17

- **Netzwerk:** Kein Enter mehr nötig – sobald so viele Zeichen getippt
  sind wie gesendet, ist die Antwort fertig (während des Tons wird wie
  bisher erst danach gewertet). Enter nur noch, wenn man weniger hat; als
  Antwortzeit zählt der letzte Tastendruck.

## 2.16

- **Updates:** Beim Start schaut der Morsetrainer nach, ob es eine neuere
  Version gibt, und bietet an, sie zu laden und neu zu starten (exe bzw.
  AppImage, von GitHub). Ohne Internet bleibt es still; „Nein“ gilt für
  diese Version, danach steht nur ein Hinweis in der Fußzeile.
- **Netzwerk:** Hat der Trainer eine neuere Version, fragt der Teilnehmer
  beim Verbinden, ob er sie laden soll; nach dem Neustart verbindet er sich
  von selbst wieder. Wirkt ab dem nächsten Update – wer noch 2.15 oder
  älter hat, lädt 2.16 einmal von Hand.

## 2.15

- **Netzwerk:** Vor der ersten Sequenz kommt das Anfangszeichen VVV =,
  nach der letzten das Schlusszeichen + – wie in den übrigen Reitern, auch
  unter den Bandbedingungen und über den Lautsprecher des Trainers.
  Abschaltbar unter „Anfangs- und Schlusszeichen senden“.

## 2.14

- **Neuer Reiter „Netzwerk“: Üben in der Gruppe.** Ein Trainer öffnet im
  lokalen Netz eine Sitzung (mit PIN), die Teilnehmer finden sie über
  „Suchen“ und melden sich mit Name oder Rufzeichen an. Alle hören dieselbe
  Sequenz – Einzelzeichen, Gruppen, Wörter, Rufzeichen oder eigenen Text –
  über den eigenen Kopfhörer und tippen mit. Der Trainer sieht live, wer was
  getippt hat, dazu Trefferquote, häufigste Fehler und schwächste Zeichen
  der Gruppe, und kann alles als CSV speichern. Übertragen wird nur Text,
  den Ton erzeugt jeder Rechner selbst.
- Ehrlich gewertet wie in den übrigen Reitern: Als **flüssig** zählt eine
  richtige Antwort nur beim ersten Hören und im üblichen Zeitfenster; nach
  „Für alle wiederholen“ oder zu langsam ist sie richtig, aber unsicher.
  Wer nicht flüssig richtig lag, hört die Lösung noch einmal. Auch
  Wendungen und QSO-Klartext lassen sich senden; bei zu langsamem
  Zeichentempo gibt es einen Hinweis aufs Koch-Tempo.
- Für den Trainer: Ein Klick auf einen Teilnehmer zeigt seine Fehler und
  schwächsten Zeichen; eine Tempo-Empfehlung (ab 90 % flüssig schneller,
  unter 75 % langsamer) lässt sich per Knopf übernehmen. Die CSV enthält
  Tempo, Zeit bis Enter und Wiederholungen je Sequenz sowie Fehler und
  schwache Zeichen je Teilnehmer. F5 Start/Stop, F6 für alle wiederholen,
  F7 weiter.
- Die Teilnehmertabelle wächst mit (bis 12 Zeilen, dann Scrollbalken) und
  lässt sich in ein eigenes Fenster auskoppeln.
- **Fester Takt für Mitschreiben auf Papier:** Die nächste Sequenz kommt
  nach Ton plus Schreibpause (fest je Sequenz, Vorgabe nach Inhalt), egal
  wer geantwortet hat. Bis zum Ende verrät der Trainerbildschirm keine
  Lösung; digitale Teilnehmer sehen nur „Nr. 7 notiert“ und am Ende die
  ganze Liste zum Anhören.
- **Auflösung** in eigenem Fenster für den Beamer: während des Durchgangs
  die laufende Nummer, danach alle Lösungen nummeriert und mehrspaltig,
  Schrift größer/kleiner, Kopieren; ein Klick spielt eine Lösung noch
  einmal ab.
- **Ton für alle über den Lautsprecher:** Auf Wunsch spielt nur der
  Trainerrechner, die Teilnehmer tippen am stummen Rechner – ohne Kopfhörer
  und ohne Versatz zwischen den Rechnern. Im festen Takt spielt der
  Trainerrechner ohnehin gleich mit, für alle, die auf Papier schreiben.
- **Kontinuierlich:** Die ganze Auswertung einer Sitzung lässt sich in
  einem eigenen Fenster zeigen, nach Gruppen gegliedert (ohne Gruppen in
  5er-Blöcken), Fehler rot, mit Schriftgröße, Kopieren und „Nur gesendeter
  Text“. Bisher waren nur die letzten 30 Zeichen zu sehen.
- Bandbedingungen liegen jetzt auch unter Anfangs- und Schlusszeichen
  (VVV =, +): Die Störungen sind von Anfang an da.
- Das Netzwerkprotokoll hat jetzt Version 2: Trainer und Teilnehmer
  brauchen dieselbe Programmversion.
- Das Fenster ist jetzt mindestens 720 Pixel breit, damit alle Reiter
  lesbar bleiben.

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
