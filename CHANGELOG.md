# Änderungen

## 2.47

- **Hilfe mit F1:** F1 öffnet die Anleitung beim Abschnitt des Reiters, in
  dem du gerade bist. Im Contest sendet F1 weiter CQ, dort öffnet der Knopf
  „Hilfe (F1)“ die Hilfe. Auf dem Mac geht auch Cmd+Umschalt+H.
- **Englische Hilfe im Reiter Network:** Der Hilfe-Knopf sprang dort zu
  einem falschen Abschnitt; jetzt öffnet er das Kapitel zum Netzwerk.
- **Anleitung überarbeitet:** Fehlende Optionen sind beschrieben (Dauer,
  Quittungston, Zeitlimit, Gruppenlänge, Schalter im Reiter Sprechen),
  Fachbegriffe werden erklärt, und es gibt einen Hinweis, falls das
  AppImage wegen FUSE nicht startet.

## 2.46

- **Lernkartei im Überblick:** Der Reiter Statistik zeigt je Fach, welche
  Zeichen darin liegen, von „Fach 1 · jeden Tag“ bis „Fach 6 · alle 32
  Tage“. F11 liest es mit vor.

## 2.45

- **Mehr Platz im Durchgang:** Bei Gruppen, Wörtern, Rufzeichen und in Am
  Stück sind die Optionen während eines Durchgangs ausgeblendet. So bleiben
  Antwortfeld, Rückmeldung und Stop auch bei großer Schrift oder kleinem
  Bildschirm ohne Rollen sichtbar.
- **Tagesübung nicht aus Versehen beenden:** Esc oder F5 beenden sie erst
  beim zweiten Druck innerhalb von drei Sekunden; der erste wird angezeigt
  und angesagt. Dazu gibt es den Knopf „Tagesübung beenden (Esc)“.
- **Esc stoppt überall:** in allen Übungsreitern, auch aus dem Antwortfeld
  heraus (im Contest bricht Esc weiter das Senden ab). F5 im Contest vor
  dem Start erinnert daran, dass F10 startet.
- **Tastenkürzel an den Knöpfen:** „Start (F5)“, „▶ Tagesübung (10 Min,
  F12)“, „Einstellungen … (Strg+,)“, „Probehören (Strg+P)“ usw.
- **Ziel und Ergebnis sichtbar:** Im Reiter Zeichen steht neben Start „23
  von 50 Zeichen, Ziel 90 %“; nach dem Stoppen steht das Ergebnis in der
  Statuszeile.
- **Tempo in ZpM:** Mit Farnsworth zeigt die Kopfleiste das effektive
  Tempo, das du hörst („≈ 50 ZpM effektiv“ bei 20/10).
- **Hilfe beim Reiter:** Die Hilfe öffnet mit der Anleitung beim Abschnitt
  des Reiters, in dem du gerade bist.
- **Einstellungen:** Das Tagesziel steht jetzt im Fenster „Einstellungen …“
  (Karte „Üben“). Nach dem Umstellen von Sprache oder Kontrast startet
  „Jetzt neu starten“ das Programm gleich neu.
- **Große Schrift und kleine Bildschirme:** Kopfleiste und
  Tagesübungs-Leiste brechen um, statt sich zu überdecken; im Fenster
  Bandbedingungen bleiben Probehören und Schließen unten stehen und
  bekommen beim Öffnen den Fokus.
- **Kleinigkeiten:** Legende zum Wochenstreifen, die Zeile „Inhalt“ ist ein
  einziger Tab-Schritt, Spaltenköpfe nicht mehr abgeschnitten.

## 2.44

- **Diplom Sternstunden:** Das Diplom „Sternensammler“ heißt jetzt
  „Sternstunden“; erreichte Stufen bleiben erhalten. Sterne und Übungstage
  mit einem Datum nach heute (falsch gestellte Uhr) zählen für Sternstunden
  und Ausdauer nicht mehr.
- **Schnellerer Start mit Sprachansage:** Das Fenster erscheint, bevor die
  Stimme geladen ist (etwa 0,5 statt 1,3 Sekunden); die erste Ansage kommt
  dafür einen Augenblick später.
- **Diplome schneller:** Nach einer Übung werden die Diplome einmal statt
  dreimal ausgewertet, und je Durchgang wird ein kleiner Auszug gespeichert.
  So bleiben Start und Auswertung auch nach Jahren Übung zügig und brauchen
  weniger Speicher. Der erste Start nach dem Update legt die Auszüge an.
- **Robuster:** Ein kurzer Lesefehler der Datenbank lässt keine Durchgänge
  mehr dauerhaft aus den Diplomen fallen. Läuft ein zweites
  Programmfenster, wartet die Auswertung nicht mehr bis zu 5 Sekunden. Ein
  Fehler der Sprachausgabe hält den Übungsablauf nicht mehr an.

## 2.43

- **Neues Diplom Sternensammler:** Alle Sterne der Tagesübung zusammen,
  Bronze ab 50, Silber ab 200, Gold ab 500, Platin ab 1.000 Sternen. Jeder
  Stern zählt, auch aus Wochen ohne erreichtes Wochenziel.
- **Wo bin ich? (F11):** liest jetzt auch in Am Stück und im Contest die
  Restzeit und den Zwischenstand vor („Restzeit 3 Minuten 12 Sekunden“,
  „Rate 80 pro Stunde“).
- **Update auf Englisch:** Bei englischer Oberfläche zeigt das
  Update-Fenster künftig die Neuerungen auf Englisch.

## 2.42

- **Update:** Ein eigenes Fenster zeigt, was in der neuen Version neu ist;
  die Ansage liest die Überschriften vor (F11 wiederholt). Nach „Jetzt
  aktualisieren“ steht der Fortschritt im Fenster, bei einem Fehler der
  Grund und der Link zum Herunterladen. Nach „Später“ holt der Knopf
  „Aktualisieren …“ in der Fußzeile das Fenster jederzeit wieder; von
  selbst fragt der Morsetrainer bei dieser Version nach sieben Tagen
  wieder.
- **Sprechen auf Englisch:** Bei englischer Oberfläche spricht der Reiter
  mit der englischen Stimme, buchstabiert im englischen Alphabet (Charlie,
  Mike, X-ray) und sagt die englische Bedeutung.
- **Betriebszeichen** werden mit ihrem Namen angesagt statt buchstabiert:
  „=“ Trennung, „+“ Spruchende, <SK> Ende der Verbindung, <KN> bitte
  kommen, <BK> Unterbrechung (englisch separator, end of message, end of
  contact, over to you only, break). Auch in Hinweisen wie „Neues Zeichen:
  <SK> · Taste *“ („… Taste Stern“).
- **Fortschritt** (Reiter Statistik) nennt den Zeitraum („19 Durchgänge am
  30.09.2026“ bzw. „vom … bis … an 6 Tagen“) statt „seit“; Durchgänge mit
  weniger als 5 Zeichen (kurze Proben) zählen dort nicht mehr mit.

## 2.41

- **Am Stück und Sprechen:** Den Inhalt wählen Optionsfelder statt einer
  Klappliste, wie im Reiter Einzeln, oben im Reiter; alle Möglichkeiten auf einen Blick, Pfeiltasten
  wechseln, die Ansage nennt „Inhalt …“. Während des Durchgangs gesperrt.
- **Sprachansage:** Bei 1 heißt es „eine Minute“, „eine Sekunde“, „nach
  einem Fehlversuch“ und „ein Zeichen“ statt „eins Minute“ usw. Hinweise,
  warum ein Durchgang nicht startet (etwa zu wenige Zeichen für Wendungen
  in Lektion 1, ungültige Eingabe) oder abbricht (keine Tonausgabe), werden
  jetzt auch gesprochen statt nur angezeigt.
- **Hilfe durchsuchen:** findet auch, was anders geschrieben ist:
  Umlaute und Bindestriche egal („Tastenkuerzel“, „Koch Lektion“), andere
  Wörter für dasselbe („Tastaturkürzel“ findet „Tastenkürzel“) und Teile
  zusammengesetzter Wörter; das wird dazugesagt. Steht es nur im anderen
  Reiter (Anleitung oder Änderungen), sagt die Suche, wie oft dort.
- **Sprechen:** buchstabiert immer im Buchstabieralphabet (Alfa, Bravo …);
  die Auswahl „Buchstaben (A, Be, Ce)“ entfällt.
- **Anleitung** neu gegliedert: Erste Schritte, je Reiter ein Abschnitt,
  Tastenkürzel als Tabelle, nummerierte Kapitel mit Inhaltsverzeichnis.
- **Einzeln:** F5 startet und stoppt jetzt auch bei Zeichen, Gruppen,
  Wörtern und Rufzeichen, wie in den anderen Reitern.

## 2.40

- **Neue Reiter:** Zeichen, Gruppen, Wörter und Rufzeichen stehen
  gemeinsam im Reiter **Einzeln** (oben die Wahl unter „Inhalt“, wie in
  den anderen Reitern; sie bleibt gespeichert): eins nach dem anderen, mit Antwort. „Kontinuierlich“ heißt
  jetzt **Am Stück**: ohne Pause fortlaufend mitschreiben. Aus zehn
  Reitern werden sieben; Alt+1 … Alt+7 wählen sie (1 Einzeln, 2 Am Stück,
  3 Sprechen, 4 QSO, 5 Contest, 6 Netzwerk, 7 Statistik), Alt+0 führt wie
  bisher zur Statistik, und Alt+8 oder Alt+9 sagt an, dass es nur sieben
  gibt. Im Reiter Einzeln schaltet Alt+1 noch einmal den Inhalt weiter,
  in der Zeile „Inhalt“ gehen die Pfeiltasten, und die Ansage nennt den
  Inhalt mit („Reiter Einzeln, Gruppen“, „Inhalt Wörter, Optionsfeld“).
  Einstellungen, Statistik und Verlauf bleiben erhalten.
- **Band in der Antwortpause:** In Gruppen, Wörtern und Rufzeichen läuft
  das Band nach jeder Sequenz 6 dB leiser weiter, statt zu verstummen;
  mit der nächsten Sequenz wird es wieder lauter (weich übergeblendet).
  Abschaltbar mit „Band in der Antwortpause“ im Fenster Bandbedingungen
  (zählt für Stufe und Diplom gleich). Die Lösung nach zu vielen
  Fehlversuchen kommt jetzt ohne Störungen.
- **Neue Störungen** unter „Weitere Störungen“: Schaltnetzteil (Brumm mit
  wanderndem Pfeifton), PLC (Datenrauschen aus der Steckdose), Weidezaun
  (Ticken etwa jede Sekunde) und Tastklicks (der Nachbar-Run tastet hart;
  die Klicks gehen auch durch ein schmales Filter). Im Netzwerk hören
  Teilnehmer ab 2.40 die neuen Störungen mit, mit älterer Version nicht.
  „Alle an“ schaltet nur noch die Störungen der oberen Karte ein, nicht
  die eingeklappten weiteren. Mit Sprachansage (F9) wird das Band vor der
  Rückmeldung ausgeblendet, damit sie gut zu verstehen ist.
- **Tastatur:** Enter löst einen Knopf mit Fokus aus, wie die Leertaste
  (z. B. „Schließen“ nach dem Durchtabben).
- **Sprachansage:** „Hz“, „kHz“, „Min“ und „s“ (hinter einer Zahl) werden
  als „Hertz“, „Kilohertz“, „Minuten“ und „Sekunden“ gesprochen statt
  buchstabiert; „Fading“, „Pile-up“ und die Contest-Arten (CQ WW, WPX,
  WAG, ARRL DX, IARU HF) klingen wie bei Funkamateuren, Abkürzungen
  buchstabiert wie Rufzeichen (auch mit der englischen Stimme). In der
  Statistik werden einzelne Zeichen wie „?“ genannt, Verwechslungen als
  „Be gleich 9 mal“ bzw. „gleich einmal“ gelesen und Spaltenköpfe wie
  „Ø Reaktion (s)“ als „Durchschnittsreaktion in Sekunden“. Klammern werden nicht mehr mitgelesen,
  sondern zur Pause; „Staat/Leistung“ heißt „Staat oder Leistung“.
  Zahlenfelder sagen ihre Einheit mit („Lösung zeigen nach, 3
  Fehlversuchen“, „Dauer, 5 Minuten“).
- **Statistik:** Unter „verwechselt mit“ steht kein „–“ mehr für ein
  Zeichen, das gar nicht erkannt wurde; es zählt nur als falsch.
- **Netzwerk:** Der Trainer hört beim Öffnen der Sitzung Adresse und PIN
  (auch mit F11), die Adresse Zahl für Zahl mit „Punkt“, die PIN als
  „PIN-Nummer“ Ziffer für Ziffer.
- **Contest:** Rufzeichen in den Feldern und im Log werden im
  Funkalphabet angesagt (Delta, Lima, Eins …).
- **Fenster schließen:** Die Ansage sagt, wo du gelandet bist („Zurück im
  Hauptfenster. Reiter Einzeln, Gruppen.“).
- **Statistik:** Die Spalte „Ø Zeit“ heißt jetzt „Ø Reaktion“ und zeigt
  die Zeit vom letzten Punkt oder Strich bis zur Eingabe (richtige
  Antworten, gemessene Werte), in allen Übungen gleich. Bisher war es die
  Zeit ab Beginn des Zeichens; lange Zeichen und langsames Tempo sahen
  dadurch schlechter aus. Beim Mitschreiben zählt sie ab dem Tonende oder
  ab deiner vorigen Taste, je nachdem was später kommt: Hinterherschreiben
  oder erst die Gruppe hören, dann tippen gilt nicht mehr als „langsam
  erkannt“ (auch für Lernkartei und Gewichtung). „Ø WPM“ je Zeichen zählt
  nur richtige Antworten, ab Beginn des Zeichens und höchstens so schnell,
  wie gesendet wurde; in Am Stück, QSO-Mittippen und im Netzwerk kamen
  bisher unsinnig hohe Werte heraus (etwa 66 WPM bei 20 gesendeten).
- **Einzeln, Zeichen:** Die Antwort zählt ab dem Ende des letzten Punkts
  oder Strichs. Bisher wurde eine sehr schnelle Taste in der Pause nach
  dem Zeichen verworfen und lief dann als „zu langsam“ ab; auch das
  Zeitlimit zählt jetzt ab dem Tonende, wie beschrieben.
- **Tabellen** (Diplome, Statistik, Contest-Log): Springst du mit Tab
  hinein, ist die erste Zeile gewählt und die Pfeiltasten gehen sofort. Öffnet sich ein Fenster, sagt die Ansage
  seinen Namen („Fenster Bandbedingungen“); spricht das Fenster selbst,
  kommt der Name davor. Tippen in den Feldern der Einstellungen und in
  Zahlenfeldern wird angesagt (Zeichen buchstabiert, Gelöschtes mit
  „gelöscht“), das Feld „Zeichen“ liest seinen Inhalt Zeichen für Zeichen.
- **Schriftgröße:** Pfeile von Zahlenfeldern und Klapplisten, Rollbalken
  und Schieberegler wachsen mit; die ganze Auswertung (Am Stück) und
  die Auflösung (Netzwerk) beginnen in der eingestellten Größe.
- **Schmales Filter bei tiefer Tonhöhe:** Das Filter wandert mit der
  eigenen Tonhöhe wie ein ZF-Filter im Gerät und nimmt bei jeder Tonhöhe
  gleich viel Rauschen weg. Bisher stieß es bei tiefem Ton an die untere
  Flanke des SSB-Filters und nahm mehr Rauschen weg als angezeigt; Stufe
  und Diplom QRN-fest hängen so nicht an der gewählten Tonhöhe.
- **Mac:** Die Anleitung nennt die Mindestversion macOS 14 (Sonoma).
- Fehlt im fertigen Programm eine Stimme, rät die Meldung jetzt zum
  erneuten Herunterladen statt auf ein Skript zu verweisen.
- **Probehören ohne Zeitgrenze:** läuft, bis du es beendest (Knopf, Strg+P
  oder Fenster schließen).
- **Statistik:** Unter der Tabelle steht, was „Ø Reaktion“, „Ø WPM“ und
  „–“ bedeuten.
- **Contest:** Stationen aus W8 (Ohio, Michigan) nennen CQ-Zone 4, aus W9
  ITU-Zone 8; im WAG geben manche DL-Stationen „NM“ (Nicht-Mitglied)
  statt eines DOK.
- **Sprachansage:** „Quebec“ klingt wie vorgeschrieben „Kebeck“. Minimieren
  eines Fensters (oder ein Wechsel der Arbeitsfläche) wird nicht mehr als
  „Zurück im Hauptfenster“ angesagt.
- **Tastatur:** Strg+B, Strg+P und Strg+F gehen auch mit Feststelltaste,
  auf dem Mac auch Cmd+B.
- **Weidezaun:** tickt höchstens einmal je Sekunde, wie es die Norm für
  Weidezaungeräte vorgibt.
- **Fehlermeldungen:** Kann der Morsetrainer kein Fenster öffnen, sagt er
  es auf der Konsole (unter Windows in einem Meldungsfenster) und nennt
  das Fehlerprotokoll, statt wortlos zu verschwinden. Fehlt der Ton,
  steht dabei, was zu tun ist (Gerät belegt, keins gefunden, abgezogen).
  `--help` und `--version` zeigen Aufruf und Version.
- **Nach dem Update** sagt ein Hinweis einmal, wo Gruppen, Wörter und
  Rufzeichen jetzt stehen.
- **Kopfhörer gewechselt:** Ist das Audiogerät weg (abgezogen, keins
  gefunden), liest der Trainer die Geräte neu ein und versucht es noch
  einmal, statt bis zum Neustart stumm zu bleiben (vor allem auf dem Mac).
- **Einstellungen**, die sich beim Beenden nicht speichern lassen (etwa in
  einem schreibgeschützten Ordner), werden gemeldet statt still verloren.
- **Bandbedingungen:** Das Fenster rät, bei „leicht“ bis „mittel“ zu üben;
  „stark“ ist für den Feinschliff.
- **Ältere Intel-Macs:** Die Anleitung nennt Python 3.10 bis 3.13 und
  macOS 13; mit Python 3.14 lässt sich der Trainer dort ohne Sprachausgabe
  einrichten statt gar nicht. Die Entwickleranleitung nennt die nötigen
  Linux-Pakete.
- Intern: Mindestversionen der Abhängigkeiten, Stimmen-Download auf festem
  Stand, Release-Builds mit festen Versionen (packaging/constraints.txt),
  der Selbsttest der Builds prüft auch Ton- und Fensterbibliothek. Öffnen
  und Schließen der Tonausgabe sind gegen gleichzeitige Zugriffe
  gesichert; Stopp und sofortiger Neustart können das Pausengeräusch
  nicht mehr doppelt laufen lassen. Die Tests laufen auch mit Python 3.10,
  dazu eine Probeinstallation auf Windows und macOS. Neues Bild im README.
  Weitere Tests.

## 2.39

- **Probehören im Fenster Bandbedingungen** (Strg+P): 15 Sekunden CQ in
  deiner Tonhöhe und deinem Tempo unter den eingestellten Bedingungen,
  ohne in einen Reiter zu wechseln. Änderungen sind sofort zu hören; zählt
  für nichts. Gesperrt während eines Durchgangs und im Netzwerk.
- **Sprachansage:** Kommt eine neue Ansage, während eine andere noch
  spricht, geht der Ablauf erst nach der neuen weiter. Bisher konnte der
  nächste Morseton sie abschneiden (etwa beim Reiterwechsel mitten in
  einer Ansage).
- **Fenster Bandbedingungen mit Scrollleiste:** Bei großer Schrift oder
  kleinem Bildschirm passt es nicht mehr ganz hinein; was fehlt, ist
  jetzt erreichbar.
- **Kontinuierlich:** Die Auswertung nach dem Stoppen zeigt die letzten
  90 Zeichen statt 30 (in Zeilen zu 30), „Deine Eingabe“ die letzten 120;
  die Anzahl steht in der Überschrift.
- **Schriftgröße auch kleiner:** 90 % und 75 % für kleine Bildschirme.
- **Hilfe durchsuchen** mit Strg+F: Enter springt zum nächsten Treffer,
  Umschalt+Enter zum vorigen; alle Treffer sind markiert.
- **Netzwerk: alle hören dasselbe QRM.** Mit CW-QRM hörte bisher jeder
  Teilnehmer ein anderes Nachbar-QSO und dazu andere Gewitter, Träger und
  Knacker. Jetzt ist alles gleich (Trainer und Teilnehmer ab 2.39).
- Intern: Die Tests laufen jetzt bei jedem Push automatisch auf GitHub,
  ein Release entsteht nur mit grünen Tests. Kommentare und Beschreibungen
  im Quelltext sind überarbeitet (was der Code tut statt Versionsgeschichte).

## 2.38

- **CW-Filter wählbar:** 2,4 kHz (wie bisher), 500 Hz oder 250 Hz um die
  eigene Tonhöhe. Zeichen, Rauschen, QRM und SSB-QRM laufen
  hindurch, der eigene Mithörton im Contest nicht. Das schmale Filter
  klingelt leicht, nimmt Rauschen und weit entferntes QRM weg; das
  Fenster zeigt den Rauschabstand im Filter, und Stufen und Diplom
  rechnen damit.
- **CW-QRM nah an der Frequenz:** Abstand wählbar – weit (300–500 Hz),
  nah (50–200 Hz) oder Zero-Beat. Mit QSB schwankt das QRM jetzt auch,
  unabhängig von den eigenen Stationen.
- **Stärkeunterschiede getrennt vom QSB:** Wie unterschiedlich laut die
  Stationen in QSO und Contest ankommen, ist jetzt ein eigener Schalter
  mit Regler, unabhängig vom Fading. Wer QSB an hatte, behält sie; die
  Stufen-Knöpfe ändern sie nicht.
- **Netzwerk: Gehör schonen.** Teilnehmer können die Störgeräusche bei
  sich leiser stellen (10–90 % der Einstellung des Trainers, nie lauter),
  etwa bei Tinnitus oder Hörgerät. Der Trainer sieht das als ↓ in Tabelle,
  Detailzeile und CSV.
- **Schriftgröße (Barrierefreiheit):** Die ganze Oberfläche lässt sich
  vergrößern, 100 % bis 200 %, unter „Weitere Optionen“ oder mit
  Strg+Plus/Minus/0 in jedem Fenster. Tabellenzeilen, Schalter und
  Zeilenumbrüche wachsen mit, das Hauptfenster auch.
- **Sprachansage (Barrierefreiheit, F9):** Das Programm sagt mit der
  eingebauten Stimme Ergebnisse (in Gruppen, Wörtern, Rufzeichen
  buchstabiert, in Einzelzeichen die Fehler), das Ende eines Durchgangs,
  den Reiterwechsel und die Karten der Tagesübung an; F11 liest vor, wo
  man gerade ist. Der Ablauf wartet auf die Ansage. Deutsche oder
  englische Stimme passend zur Oberfläche; ohne Stimme kommt bei F9 und
  F11 ein Fehlerton. Auch im QSO (nächster
  Schritt, Abfragefelder, Ergebnis mit richtigen Werten), im Contest
  (Logfehler gleich nach dem TU, im Tonstrom), im Reiter Statistik (F11
  liest eine Übersicht vor) und in Tabellen (gewählte Zeile). Mit Tab
  angesprungene Bedienelemente sagen Name, Art und Stand an, Änderungen
  per Tastatur ebenfalls (kleiner eingebauter Screenreader). Im Netzwerk
  hört der Teilnehmer Verbinden/Trennen, das Ergebnis jeder Antwort und
  des Durchgangs; Sequenzen des Trainers haben Vorrang. Die Abendbilanz
  der Tagesübung und das Diplom-Fenster werden ganz vorgelesen; im Reiter
  Sprechen Startprobleme, Ende und MP3-Export.
- **Hoher Kontrast** (Barrierefreiheit): Farbschema Schwarz, Weiß, Gelb
  mit kräftigen Rahmen, unter „Weitere Optionen“, ab dem nächsten Start.
  Alle Schriften mindestens 7:1 zum Grund, auch Diagramme und die Farben
  der QSO-Stationen.
- **Bedienung ohne Maus:** Knöpfe und Schalter sind per Tab erreichbar,
  der Tastaturfokus ist deutlich markiert; Alt+1 … Alt+0 und Strg+Tab
  wechseln die Reiter, Strg+B öffnet die Bandbedingungen, Esc schließt
  auch die Netzwerk-Fenster. Ein Mausklick legt den Fokus weiterhin nicht
  auf Knöpfe, die Leertaste bleibt „Wiederholen“. Tippen ins Notizfeld
  zählt nicht mehr als Antwort.
- **Fenster „Einstellungen“** (Knopf oben rechts, Strg+Komma): Rufzeichen
  und Name, Sprache, Barrierefreiheit und Daten stehen jetzt dort; unter
  „Weitere Optionen“ bleiben nur die Übungsoptionen, der Bereich über den
  Reitern ist halb so hoch.
- Bandbedingungen mit Funkbegriffen: „Bandrauschen“ statt „Rauschen“,
  „SSB-QRM (verstimmte Sprache)“ statt „SSB-Gebrabbel“, „Chirp
  (zwitschernder Sender)“.
- **Weitere Störungen** (aufklappbar im Bandfenster, nicht Teil der
  Stufen): Gewitter (QRN in Schüben), AGC-Pumpen nach Knackern,
  Flatterfading (Aurora), Träger (jemand stimmt ab).
- **Mac:** Cmd+Q speichert jetzt Einstellungen wie Sprache, Schriftgröße
  und Kontrast; Cmd+Komma und „Einstellungen …“ im App-Menü öffnen die
  Einstellungen; Cmd+0 setzt die Schrift zurück. Weil F9, F11 und F12 dort
  Medientasten sind: Cmd+Umschalt+A (Ansage), W (wo bin ich), T
  (Tagesübung).
- **Start aus dem Quelltext:** Die Anleitung nennt jetzt den Schritt, der
  die Stimmen lädt (`packaging/get_voice.sh`); das Skript läuft auch mit
  dem bash von macOS.
- Die Pakete sind durch die englische Stimme gut 60 MB größer; die
  Windows-exe startet dadurch etwas langsamer.
- Ein Netzwerktest hing an der Uhr und kippte unter Last gelegentlich;
  er setzt die Tastenzeiten jetzt selbst.

## 2.37

- **Rauschabstand in dB, echte Stufen:** Das Rauschen steht jetzt als
  Rauschabstand (S/N in 2,4 kHz) im Fenster und reicht von +20 dB bis
  −10 dB; wird es lauter, regelt der „Empfänger“ das Signal herunter (wie
  eine AGC), statt zu übersteuern. Die Stufen sind deutlich auseinander:
  leicht +8 dB, mittel +2 dB, stark −4 dB (bisher +15, +11 und +7,5 dB –
  für geübte Ohren kaum ein Unterschied). Chirp steht in Hz.
- **QSB nach Stufe statt nach Zufall:** Die Tiefe des Fadings folgt dem
  Regler und streut nur noch wenig; zwei überlagerte Schwankungen machen
  den Verlauf unregelmäßig wie auf dem Band.
- **Einsteiger:** Wer die Bandbedingungen zum ersten Mal zuschaltet,
  beginnt mit „leicht“; das Fenster rät, neue Zeichen ohne Störungen zu
  lernen. Die Anleitung zeigt, was in jeder Stufe steckt.
- **Netzwerk:** Alle Teilnehmer hören dasselbe Fading und dieselben
  Stationen (gemeinsamer Zufallswert vom Trainer).
- **Diplom QRN-fest:** zählt in Kontinuierlich nur noch Zufallszeichen –
  Klartext ist im Störnebel durch den Zusammenhang viel leichter (wie
  schon bei QRQ). Erreichte Siegel bleiben.
- Nach dem Schließen des Einstellungsfensters geht der Fokus zurück, etwa
  ins Eingabefeld eines laufenden Durchgangs.
- Das Rauschen vor und nach jeder Sequenz wird weich ein- und
  ausgeblendet, statt im Kopfhörer schlagartig einzusetzen.
- **Fading und QRM laufen weiter:** In Gruppen, Wörtern, Rufzeichen und
  bei Netzwerk-Sequenzen begannen QSB und das Nachbar-QRM bei jeder Sequenz
  wieder an derselben Stelle – jede Gruppe lag im selben Fading-Abschnitt
  (womöglich den ganzen Durchgang im Loch oder nie), und das QRM sendete
  immer denselben Anfang. Jetzt laufen sie wie auf dem Band auch während
  der Antwortpause weiter.
- **Störungen verfälschen die Statistik nicht mehr:** Durchgänge mit
  Bandbedingungen zählen nicht mehr für Zeichenstatistik, Gewichtung,
  Verwechslungen und Lernkartei (im Verlauf erscheinen sie weiter). Damit
  das eindeutig bleibt, lassen sie sich in diesen Reitern nur zwischen zwei
  Durchgängen an- und ausschalten; Stärke und Lautstärke wirken weiter
  sofort.
- **Bandbedingungen, Feinschliff:** Die Kurzfassung unter „Weitere Optionen“
  wird nicht mehr abgeschnitten; eine Störung auf 0 % gilt als aus. Das
  Einstellungsfenster bleibt über dem Hauptfenster und sagt, dass im
  Netzwerk die Einstellung des Trainers gilt. Die Bedingung des Diploms
  QRN-fest nennt jetzt auch, dass die Bandbedingungen den ganzen Lauf an
  bleiben und nicht leichter gestellt werden dürfen.
- **Netzwerk robuster:** Unsinnige Werte für die Bandbedingungen (NaN,
  unendlich) werden verworfen; vorbereitete Störsignale belegen nicht mehr
  unbegrenzt Speicher, wenn der Trainer die Einstellung oft ändert.

## 2.36

- **Bandbedingungen zentral:** Welche Störungen wie stark und wie laut,
  stellst du jetzt an einer Stelle ein (Weitere Optionen oder „Einstellen …“
  im Reiter); die Reiter schalten sie nur noch an oder aus. Damit gibt es
  alle sechs Störungen (auch Chirp, SSB-Gebrabbel, CW-QRM) und die
  Lautstärke überall, nicht mehr nur in QSO und Contest. Leicht, mittel und
  stark bleiben als Schnellwahl und für das Diplom QRN-fest. Alte
  Einstellungen werden übernommen. Im Netzwerk hören Teilnehmer ab dieser
  Version genau die Einstellung des Trainers, ältere die nächste Stufe.
- **Gesamtstatistik zurücksetzen:** Die Abfrage sagt jetzt genau, was
  gelöscht wird (Statistik je Zeichen, Lernkartei, Verwechslungen) und was
  bleibt. Bisher fehlte die Lernkartei, und die Rede war noch von
  Logdateien, die es seit 2.28 nicht mehr gibt.

## 2.35

- **Diplom-Vorschau:** „Vorschau: nächstes Ziel“ im Reiter Statistik unter
  „Diplome“ zeigt das Diplom der nächsten offenen Stufe, mit Stempel
  „VORSCHAU“, ohne Datum und Nummer.

## 2.34

- **Motive wie auf Geldscheinen:** Jedes Diplom hat ein eigenes Motiv im
  Stil eines Stichtiefdrucks – Handtaste, Rennwagen, Weltkugel, Kopfhörer,
  Wählscheibe, Klassenzimmer und mehr. Rechts steht das Clubheim des OV
  Gütersloh (N47), wo der Morsetrainer entsteht.
- **Diplom-Nummer:** Mit eingetragenem Rufzeichen steht oben rechts eine
  Nummer wie `DL1ABC-KOCH-G-20261004` (Rufzeichen, Diplom, Stufe, Datum).
- **Mac-App:** ohne die überflüssigen Windows-Bibliotheken, knapp 1 MB
  kleiner.

## 2.33

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
