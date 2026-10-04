# Änderungen

## Unveröffentlicht

- **Mac-App:** Für Macs mit Apple-Prozessor (M1 und neuer) gibt es jetzt
  `Morsetrainer-macOS.zip` im Release. Die App ist nicht bei Apple
  signiert; beim ersten Start muss man sie freigeben, unter macOS 15 in
  „Datenschutz & Sicherheit“ mit „Dennoch öffnen“ (siehe Anleitung). Die
  Daten liegen in `~/Library/Application Support/Morsetrainer/`. Ein
  automatisches Update gibt es auf dem Mac nicht, nur den Hinweis auf eine
  neue Version. Intel-Macs starten den Morsetrainer aus dem Quelltext, die
  Anleitung beschreibt wie. Noch nicht auf einem Mac getestet –
  Rückmeldungen sind willkommen.

## 2.32

- **Koch-Diplom:** Silber und Gold gibt es wie bei Fluss, QRQ, QRN-fest,
  Rufz und Contest erst an zwei verschiedenen Tagen. Wer gleich in
  Lektion 41 einsteigt, bekam bisher mit einem einzigen Lauf alle drei
  Stufen. Schon erreichte Siegel bleiben.
- **Lebenslinie:** „Koch geschafft“ steht erst da, wenn Lektion 41
  bestanden ist (Gold im Koch-Diplom), nicht schon nach einem Durchgang in
  Lektion 41.
- **Dezimalkomma:** Statistiktabelle, Geschwindigkeit und Fortschritt
  zeigen auf Deutsch Kommas („2,27“, „94,7 %“) statt Punkten.
- **Contest:** Die Auswahl zeigt nur noch den Namen („CQ WW (Zone)“)
  statt „Contest: Contest: …“.
- **Kleinigkeiten:** Überschrift „Participants“ auf Englisch, keine leeren
  Zeilen mehr im Reiter Gruppen und im Sitzungskasten des Netzwerks, „Verlauf
  (letzte 10)“ bzw. „(letzte 40)“ in allen Reitern, Fortschrittstext ohne
  verwaisten Zeilenumbruch.
- **Schneller Start unter Linux:** Mit der Eingabemethode ibus (Standard
  unter Ubuntu) brauchte das Hauptfenster etwa 9 s zum Aufbau, jetzt unter
  1 s. Der Morsetrainer nutzt keine Eingabemethode mehr; Umlaute der
  Tastatur gehen weiter, Tottasten und Compose-Folgen nicht.
- **Klapplisten lesbar:** Eine Klappliste mit Tastaturfokus zeigte weiße
  Schrift auf weißem Feld und wirkte leer – am auffälligsten die
  Contest-Auswahl beim Öffnen des Reiters Contest.

## 2.31

- **Netzwerk sicherer:** Nach 5 falschen PINs ist ein Rechner eine Minute
  gesperrt, der Trainer sieht einen Hinweis. Bisher ließ sich die PIN in
  Sekunden durchprobieren.
- **Teilnehmer entfernen:** Der Trainer kann einen gewählten Teilnehmer
  aus der Sitzung werfen; dieser Rechner kommt bis zum Schließen der
  Sitzung nicht wieder herein.
- **Robuster:** Der Trainer begrenzt die Zahl der Verbindungen und trennt
  Rechner, die ihn mit Nachrichten überschütten; die Tabelle wird nicht
  mehr für jede einzelne Nachricht neu aufgebaut.

## 2.30

- **Updates mit Prüfsumme:** Jedes Release enthält `SHA256SUMS.txt` mit den
  Prüfsummen. Das Update im Programm installiert nur eine Datei, die dazu
  passt; ein beschädigter oder falscher Download wird verworfen und das
  Programm bleibt, wie es ist.
- **Anleitung:** Die README ist jetzt ein kurzer Überblick mit Bildern; die
  ausführliche Anleitung steht in `docs/Anleitung.md` und wie bisher im
  Programm unter „Hilfe“. Neu darin: Hinweise zur Sicherheit von Updates
  und Netzwerkmodus und wie man die Prüfsummen von Hand nachprüft.

## 2.29

- **Schneller:** Statistik, Lebenslinie und Diplome werden nach einem
  Durchgang schneller ausgewertet; das macht sich bemerkbar, wenn sich
  über die Jahre viele Durchgänge angesammelt haben.

## 2.28

- **Datenbank:** Alle Übungsdaten liegen jetzt in einer Datei
  (`stats/morsetrainer.db`, SQLite) statt in vielen einzelnen JSON-Dateien.
  Der Abschluss eines Durchgangs, die Gesamtstatistik und die Lernkartei
  werden gemeinsam gespeichert, ein Absturz kann sie nicht mehr
  auseinanderbringen. Beim ersten Start werden die bisherigen Dateien
  übernommen und nach `stats/alt-json/` verschoben; gelöscht wird nichts.
- **Daten sichern:** Die Datenbank kommt als stimmiger Stand in die
  Sicherung, auch wenn gerade geübt wird. Beim Einlesen wird sie vorher
  geprüft; eine beschädigte Sicherung ersetzt nichts. Ältere Sicherungen
  lassen sich weiter einlesen.

## 2.27

- **Stabilität:** Bricht die Tonausgabe in Kontinuierlich, QSO oder Contest
  mit einem unerwarteten Fehler ab, endet die Übung mit einer Meldung,
  statt auf „läuft“ stehen zu bleiben. Hängt das Audiogerät nach Stop
  (Bluetooth), stört der alte Durchgang einen sofort neu gestarteten nicht
  mehr. Zwei Programmfenster auf einem Rechner schreiben ihre Dateien
  nicht mehr über dieselbe Zwischendatei. Wird der Verbindungsaufbau
  im Netzwerk genau im falschen Moment abgebrochen, bleibt die Verbindung
  nicht mehr offen.

## 2.26

- **Diplome nur mit schnellen Zeichen:** Worked All Letters und Alle
  Ziffern zählen ein Fach der Lernkartei nur, wenn es mit Zeichen ab 18 WPM
  erreicht wurde; die Lernkartei selbst arbeitet wie bisher. Fächer von
  vor dieser Version zählen weiter. Auch „Zeichen gehört“ zählt nur noch
  Übungen ab 18 WPM Zeichentempo.
- **QSO:** Das Ergebnis speichert jetzt auch das Zeichentempo. Für
  Kopfhörer und Erstes QSO verstanden zählen neue QSOs erst ab 18 WPM
  Zeichentempo, ältere Ergebnisse wie bisher.
- **Urkunde:** Bei Worked All Letters, QRN-fest und Contest steht auf dem
  Diplom nur noch die Bedingung der erreichten Stufe statt aller Stufen.
- **Abendbilanz:** Sie nennt nur noch die Siegel aus der Tagesübung, nicht
  noch einmal die, deren Fenster heute schon kam.
- **Clubabend:** Das Diplom geht nur gemeinsam im Netzwerk. Ohne Siegel
  steht es am Ende der Übersicht, mit „gemeinsam im Netzwerk“ statt
  „0 / 1 Abend“.

## 2.25

- **Betriebszeichen:** In den Lektionen 42–45 wird nach bestandenem
  Durchgang wieder das nächste Betriebszeichen angeboten (AR → KN → SK →
  BK), wie bei den Lektionen davor. Betriebszeichen, die schon in der
  Lernkartei liegen, nimmt die Tagesübung nach Koch mit dazu, damit sie
  wiederholt werden und nicht verblassen.
- **Netzwerk:** Eine abgerissene Verbindung (WLAN weg, Rechner im
  Ruhezustand) fällt jetzt nach etwa 15 Sekunden auf, auch mitten im
  Durchgang: Trainer und Teilnehmer schicken sich dafür regelmäßig ein
  Lebenszeichen. Der Name ist dann wieder frei, und der Teilnehmer kann
  sich gleich neu anmelden; bisher blieb er bis zu einer Viertelstunde
  belegt. Vom selben Rechner geht das Wiederverbinden sofort, auch bevor
  die Trennung aufgefallen ist. Mit älteren Versionen auf der anderen
  Seite dauert es etwas länger (etwa eine halbe Minute, solange gerade
  nichts gesendet wird). Überlange Antworten aus dem Netz werden gekürzt,
  damit das Trainer-Fenster nicht hängt.
- **Stabilität:** Lässt sich ein Ergebnis nicht speichern (Platte voll),
  läuft die Auswertung bei Rufz, Contest und QSO trotzdem zu Ende. Von Hand
  veränderte oder beschädigte Statistikdateien bringen die Diplome nicht
  mehr nach jeder Übung zum Scheitern. Beim Daten einlesen werden auch
  beschädigte oder verschlüsselte ZIP-Dateien sauber abgelehnt, bevor
  etwas ersetzt wird.

## 2.24

- **Clubabend:** Netzwerk-Übungen aus Versionen vor 2.22 zählen wieder.
  Ihre Protokolle enthalten keine Dauer, deshalb galten sie seit 2.23 als
  0 Minuten und das Diplom fehlte. Für sie genügt wie früher die
  Teilnahme an dem Tag.

## 2.23

- **Daten sichern und einlesen:** Unter „Weitere Optionen → Daten“
  lassen sich alle Einstellungen und Statistiken als ZIP-Datei an einen
  frei gewählten Ort sichern und auf einem anderen Rechner wieder
  einlesen. Der bisherige Stand wird vor dem Einlesen automatisch
  gesichert. Siehe README, „Sichern und auf einen neuen Rechner umziehen“.
- **Clubabend mit Stufen, auch für den Trainer:** Das Diplom Clubabend
  hat jetzt Bronze bis Platin (1 / 5 / 15 / 40 Abende). Ein Abend zählt
  ab zusammen 10 Minuten Netzwerk-Übung an einem Tag, mitgemacht oder als
  Trainer geleitet (nur Durchgänge mit Teilnehmern). Schon erhaltene
  Siegel bleiben. Das Diplom-Fenster kommt beim Trainer erst nach
  „Sitzung schließen“, nicht vor der Gruppe. Statistik und Übungszeit bleiben beim Trainer unberührt.
- **Lebenslinie:** Im Reiter Statistik unter den Diplomen ein Diagramm
  vom ersten Üben bis heute – Sterne gesamt, höchste geübte Koch-Lektion
  und Tagestempo der Tagesübung auf einer gemeinsamen Zeitachse, darunter
  die Siegel der Diplome. Das Tagestempo wird dafür ab jetzt je Tag
  gespeichert. Siehe README, „Lebenslinie“.
- **Koch-Lektion 41 schließt ab:** Nach den 40 Lektionen von lcwo.net
  bringt Lektion 41 kein neues Zeichen mehr, alle Zeichen kommen
  gleichmäßig (schwache weiter öfter); im Feld „Zeichen“ stehen sie
  sortiert. Die Betriebszeichen AR, KN, SK und BK sind jetzt optional in
  den Lektionen 42–45; dorthin wird weder nach einem Durchgang noch in der
  Tagesübung von selbst weitergeschaltet. Die Tagesübung gilt nach
  Lektion 41 als „nach Koch“ und übt dann ohne Betriebszeichen; ein Stand
  aus den bisherigen Lektionen 42–45 zählt als „nach Koch“. Koch-Gold gibt
  es für Lektion 41, Contest, Kopfhörer und Worked All Contests sind ab
  Lektion 41 erreichbar.

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
- **Woche statt Serie:** Neben dem Knopf stehen die Sterne der Woche je Tag
  (frei geübte Tage mit ✓) und der Stand zum Wochenziel von 12 Sternen; zu
  Beginn einer Woche ein Rückblick auf die letzte. Die Serie „X Tage in
  Folge“ in der Fußzeile entfällt: Sie fiel nach einem ausgelassenen Tag
  auf null.
- **Diplome:** 17 Diplome wie im Funkbetrieb (Koch, Worked All Letters,
  QRQ, QRN-fest, Rufz, Contest, WPX, Kopfhörer, Ausdauer …), meist in den
  Stufen Bronze, Silber, Gold und teils Platin. Neue Siegel zeigt ein
  Fenster nach der Übung (in der Tagesübung nach der Abendbilanz), das
  Diplom lässt sich mit Rufzeichen als Urkunde drucken. Übersicht mit
  Fortschritt im Reiter Statistik; beim ersten Start wird nachgetragen,
  was du schon erreicht hast. Erreichtes geht nie verloren. Siehe README,
  „Diplome“.
- **Rufzeichen und Name** stehen jetzt zentral unter „Weitere Optionen“:
  für die Diplome und als Vorgabe im Contest und Netzwerk, die dort
  eigenständig bleiben (z. B. für ein Contest-Rufzeichen). Vorhandene
  Einträge werden übernommen. Der Contest-Reiter gibt nicht mehr DL4YM
  als eigenes Rufzeichen vor. Wer noch kein Rufzeichen hat, trägt nur den
  Namen ein.
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
