# Morsetrainer – Anleitung

Ein CW-Trainer für Einsteiger bis Contester, entwickelt von **DL4YM**.
Diese Anleitung steht auch im Programm unter **Hilfe**. Einen kurzen
Überblick mit Bildern gibt die [README](../README.md).

## Trainingsmodi

| Reiter | Was du übst |
|---|---|
| **Einzelzeichen** | Einzelne Zeichen erkennen; nach jeder Antwort steht deine Zeit und das aktuelle Limit, z. B. „0,38 s, Limit 1,20 s“. Mit Zeitlimit (Instant Character Recognition): Das Limit wird kürzer, solange du sicher bist, und länger, wenn du Zeichen verpasst; eine Verwechslung ändert es nicht. Nach einer Verwechslung hörst du das richtige und dein getipptes Zeichen direkt nacheinander. |
| **Gruppen** | Zeichengruppen hören und mitschreiben. Die Gruppenlänge wächst auf Wunsch mit: kurz anfangen, nach 5 richtigen Gruppen eine länger, nach 2 falschen Gruppen (jeweils beim ersten Versuch) eine kürzer. |
| **Wörter** | CW-Abkürzungen, Q-Gruppen und QSO-Wörter, nur aus den Zeichen, die du schon kannst. Standard ist „Erst merken“: erst das ganze Wort hören, dann tippen; eine zu langsame Antwort wird vermerkt. Auch R, K und die Betriebszeichen KN und SK kommen vor (zählen aber nicht als Wörter für die Mindestzahl). Ein schwaches Zeichen kommt öfter, aber in wechselnden Wörtern. Nach der Antwort wird die Bedeutung angezeigt. Eigene Wörter lassen sich ergänzen (siehe Daten). |
| **Rufzeichen** | Echte Rufzeichen aus der Super-Check-Partial-Liste, standardmäßig nur aus Zeichen, die du schon gelernt hast (ab Koch-Lektion 23 mit der ersten Ziffer). Gelegentlich mit /P, /M, OE/… wie im Contest. Wahlweise als **Rufz-Durchgang** (angelehnt an RufzXP): 50 Rufzeichen, je ein Versuch, das Tempo wächst mit, Punkte = Länge × effektives Tempo, Bestwert (mit Starttempo) und Verlauf; danach lassen sich die verpassten und die zu langsam erkannten Rufzeichen nachhören (F6): erst nur hören, dann mit Lösung noch einmal, im Originaltempo. |
| **Kontinuierlich** | Der Ton läuft ohne Warten durch, du tippst mit (wie beim Mithören); die Zeichen kommen in Gruppen (Standard 5) mit Wortpause dazwischen. Statt Zufallszeichen auch als **Klartext**: Wörter, typische QSO-Wendungen („TNX FER CALL“, „UR RST 599“), Rufzeichen oder ganze QSOs am Stück (Klartext zählt nicht für die Lektion). Auf Wunsch mit **Bandbedingungen**, die durchgehend unter dem ganzen Durchgang liegen. Nach dem Stoppen (F5 oder Esc) zeigt eine Gegenüberstellung die letzten Zeichen; **Alles in eigenem Fenster** zeigt die ganze Sitzung, nach den gesendeten Gruppen gegliedert (ohne Gruppen in 5er-Blöcken), Fehler rot, Schrift größer/kleiner, kopierbar – wahlweise nur den gesendeten Text zum Vergleichen mit dem Zettel. Gewertet wird eine Taste nur, wenn sie zum Zeichen passt: nicht vorab geraten und höchstens 5 s danach; zu viel Getipptes zählt als Fehler. |
| **Sprechen** | Hören & Sagen ohne Tastatur (wie Morse Code Ninja): Morsezeichen, Denkpause, in der du laut sagst, was du gehört hast, dann sagt eine Stimme die Lösung an – Zeichen, Gruppen und Rufzeichen buchstabiert (deutsche Buchstabennamen oder Buchstabieralphabet), Wörter und Wendungen als Ganzes bzw. mit ihrer Bedeutung („TNX“ → „danke“) – und das Zeichen kommt noch einmal. Die Denkpause ist bewusst knapp (Standard 1 s plus 0,3 s je Zeichen). Inhalte: Zeichen, Gruppen, Wörter, Wendungen, Rufzeichen. **Als MP3 speichern** für unterwegs (Handy, Auto). Zählt nur für die Übungszeit. |
| **QSO** | Komplette QSOs hören: normales QSO oder Contest-Runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) mit einstellbaren Pile-ups (Standard aus). Auswertung per Abfrage/Log, durch Mittippen, als **Kopfhören + Fragen** (ohne Notizen, danach Inhaltsfragen zu Name, QTH, Rig, Wetter … bzw. Austausch) oder nur zum Hören. Neben der Länge steht die geschätzte Dauer; wie oft vor dem Prüfen „Nochmal“ gehört wurde, wird vermerkt. |
| **Contest** | Du bist selbst die Run-Station (ähnlich Morse Runner): CQ rufen, Anrufer aufnehmen, Austausch geben, loggen. Wie im echten Contest antworten Anrufer manchmal auch auf ein fast richtiges Rufzeichen – wer den Fehler bemerkt, korrigiert das Call und bestätigt mit Enter („Call TU“), sonst steht „Busted“ im Log. „?“ im Call-Feld fragt nach (DL1?, DL?ABC). Tempo- und Tonhöhen-Streuung der Anrufer sind einstellbar, am Ende gibt es eine Zusammenfassung nach Fehlerart; F10 startet und beendet. |
| **Netzwerk** | Üben in der Gruppe im lokalen Netz (Kurs, Clubabend): Ein Trainer gibt vor, alle hören dieselbe Sequenz über den eigenen Kopfhörer und tippen mit; der Trainer sieht live, wer was getippt hat. Siehe unten. |
| **Statistik** | Gesamtstatistik je Zeichen (nur aus Zufallszeichen und Rufzeichen; bei Wörtern, Wendungen und QSOs verrät der Zusammenhang zu viele Zeichen), **Lernkartei** (Wiederholung über Tage: sicher und flüssig erkannte Zeichen kommen nach 1, 2, 4 … 32 Tagen wieder, unsichere am nächsten Tag; entschieden wird einmal am Tag ab 5 Versuchen, hochgestuft nur aus Zufallszeichen; fällige kommen mit „schwache bevorzugt“ öfter und lassen sich gezielt üben), häufigste Verwechslungen (mit Knopf, um sie gezielt zu üben), Tagesziel, **Diplome** und **Lebenslinie** (siehe unten) und Fortschrittsverlauf je Modus. |

In **Gruppen, Wörter und Rufzeichen** kannst du wählen:

- **Eingabe:** *Mitschreiben* (tippen, während der Ton läuft), *Erst merken*
  (tippen nach dem Ton) oder *Kopfhören* (nichts tippen; Enter löst auf, dann
  J = gewusst, N = nicht gewusst). Kopfhören beruht auf deiner eigenen
  Bewertung und zählt daher nicht für die Gesamtstatistik und die Lektion.
- **Tempo wächst mit** (wie bei RufzXP): richtig beim ersten Versuch +1 WPM,
  falsch beim ersten Versuch −1 WPM – gemeint ist das effektive Tempo. Mit
  Farnsworth werden erst die Pausen kürzer; sind sie weg, wird das
  Zeichentempo schneller. Langsamer werden die Zeichen höchstens bis 18 WPM,
  darunter werden die Pausen länger, damit man nicht mitzählen kann. Dieselbe
  Regel gilt für „Tempo automatisch anpassen“ im QSO-Reiter. Der
  Fortschrittsverlauf zeigt das effektive Tempo (z. B. 10 bei 20/10 WPM).
- **Bandbedingungen** an- und ausschalten (eingestellt werden sie zentral,
  siehe unten). Sie liegen auch unter dem Anfangszeichen (VVV =) und dem
  Schlusszeichen (+).

## Tagesübung

Keine Lust zu entscheiden, was du heute übst? **▶ Tagesübung (10 Min)**
oben in der Kopfleiste (oder F12) stellt zehn Minuten aus dem zusammen, was
dran ist, und schaltet die Reiter selbst um:

| Stand | Aufwärmen | Hauptteil | Ausklang |
|---|---|---|---|
| Lektion 1–9 | Einzelzeichen mit Zeitlimit, 3–4 Min | Gruppen, festes Tempo | Kontinuierlich, Gruppen von 3, 2 Min |
| Lektion 10–29 | wie oben | wie oben | Wörter, 2 Min |
| Lektion 30–41 | wie oben | wie oben | Wörter oder Rufzeichen im Tageswechsel, 2 Min |
| nach Koch (Lektion 41 bestanden) | Einzelzeichen, 2 Min | Kontinuierlich, Gruppen von 5, 4 Min | Rufzeichen, 4 Min |

- **Aufwärmen** mit allen Zeichen der Lektion; die heute fälligen Zeichen
  der Lernkartei kommen öfter, ist nichts fällig, deine häufigsten
  Verwechslungen. Bei vielen fälligen Zeichen wird es etwas länger, der
  Hauptteil entsprechend kürzer. Das Zeitlimit macht weiter, wo es beim
  letzten Mal aufgehört hat, und wird hier nie länger als 1,5 s.
- **Tempo:** Im Hauptteil bleibt das Tempo fest (Zeichen mindestens
  18 WPM). Angepasst wird einmal am Tag, wirksam ab dem nächsten: unter
  75 % beim ersten Versuch (mindestens 100 Zeichen) 1 WPM langsamer. Nach
  Koch wird es ab 90 % auch 1 WPM schneller; vorher nicht, denn ein guter
  Tag bringt dann schon das nächste Zeichen.
- **Lektion:** Erfüllt der Hauptteil das Koch-Kriterium (50 Zeichen, 90 %
  beim ersten Versuch), gilt ab dem nächsten Tag die nächste Lektion –
  ohne Nachfrage. Die Tagesübung führt dafür ihre eigene Lektion, beim
  ersten Mal die aus der Kopfleiste; Lektion und Zeichensatz oben bleiben
  für das freie Üben, wie du sie eingestellt hast.
- **Drei Sterne am Tag:** ★ *Dabei* für die vollen 10 Minuten, ★ *Sauber*
  für 90 % beim ersten Versuch im Hauptteil (in den ersten drei Tagen einer
  neuen Lektion 80 %), ★ *Weiter* für echten Fortschritt: Aufstieg
  vorgemerkt, ein Zeichen erstmals in Fach 3 der Lernkartei oder ein
  Tagestempo, das du noch nie hattest. Eine zweite Tagesübung am selben Tag kann
  fehlende Sterne nachholen; verdiente Sterne gehen nie verloren, auch
  nicht beim Abbrechen.
- **Zwischen den Blöcken** zeigt eine kurze Karte das Ergebnis, neue Sterne
  und was als Nächstes kommt. Sie bleibt stehen, bis du mit Enter oder
  „Weiter“ fortfährst; Esc beendet die Tagesübung. Die Einstellungen der Reiter sind danach wieder wie vorher.
- **Abendbilanz:** Sterne, was gegenüber der Vorwoche besser geworden ist
  (Reaktionszeit je Zeichen bei Einzelzeichen, Gruppenquote; nur mit genug
  Daten und bei gleichem Tempo, nie „schlechter“), wie viel bis zur
  nächsten Lektion fehlt, der Stand zum Wochenziel und, wenn der Hauptteil
  gut lief, einmal am Tag **Noch 5 Min** mit etwas anderem: deine
  Verwechslungen aus der Lektion, einen Rufz-Durchgang oder Wörter.
- **Woche:** Neben dem Knopf steht der Wochenstreifen ab Montag, z. B.
  „Mo ★★★  Di ★★  Mi ✓  Do –  Fr ·“ (✓ = ohne Tagesübung frei geübt, mit
  erreichtem Tagesziel; – = nicht geübt), daneben der Stand zum
  **Wochenziel von 12 Sternen**. Das schaffst du mit vier bis fünf
  Übungstagen; ein ausgelassener Tag kostet nicht die Woche. Bis zur
  ersten Tagesübung einer neuen Woche steht dort ein Rückblick, z. B.
  „Letzte Woche: 4 Tage, 11 ★, Lektion 12 → 13“.

## Diplome

Wie DXCC oder WAC im Funkbetrieb: Diplome für das, was du dauerhaft
kannst, in Stufen **Bronze, Silber, Gold** und teils **Platin**. Geprüft
wird nach jeder Übung; ein neues Siegel zeigt ein Fenster mit Datum und
Knopf **Drucken** – das Diplom öffnet sich als Urkunde im Browser (A4
quer) mit deinem Rufzeichen und Namen aus „Einstellungen …“ (im
Fenster auch änderbar). In der
Tagesübung kommt das Fenster erst nach der Abendbilanz, die die neuen
Siegel aus der Tagesübung auch nennt.

Jedes Diplom hat links ein eigenes Motiv im Stil eines Stichtiefdrucks wie
auf Geldscheinen, etwa die Handtaste bei Koch, den Rennwagen bei QRQ oder
die Wählscheibe bei „Alle Ziffern“. Rechts steht das Clubheim des OV
Gütersloh (N47), wo der Morsetrainer entsteht.

<img src="bilder/diplom.png" width="640" alt="Beispiel: Koch-Diplom in Gold für DL1ABC">

**Diplom-Nummer:** Mit eingetragenem Rufzeichen steht oben rechts eine
Nummer wie `DL1ABC-KOCH-G-20261004`: Rufzeichen, Diplom, Stufe (B, S, G,
P) und Datum. Sie ist eindeutig, weil jede Stufe je Rufzeichen nur einmal
vergeben wird.

Die Übersicht steht im Reiter **Statistik** unter „Diplome“: alle
Diplome mit erreichten Siegeln, dem nächsten Ziel (z. B. „Silber: 18 / 25
Lektionen“) und ab welcher Lektion es erreichbar ist; offene stehen grau.
Clubabend geht nur gemeinsam im Netzwerk und steht ohne Siegel am Ende.
Eine gewählte Zeile zeigt Bedingung und Tage der Siegel, bei QRN-fest,
Contest und Verwechslung auch, wie nah du der nächsten Stufe bist (bester
Lauf bzw. das nächste Paar mit verbleibenden Tagen); „Diplom ansehen
und drucken“ zeigt das Diplom der höchsten Stufe. „Vorschau: nächstes
Ziel“ zeigt, wie das Diplom der nächsten offenen Stufe aussehen wird – mit
dem Stempel „VORSCHAU“, ohne Datum und Nummer.

| Diplom | Stufen | ab Lektion | Bedingung |
|---|---|---|---|
| Koch | Lektion 10 / 25 / 41 | 1 | Bestandener Aufstiegslauf: ≥ 50 Zeichen, ≥ 90 % beim ersten Versuch, Zeichen ≥ 18 WPM (Gruppen oder Kontinuierlich) |
| Worked All Letters | 10 / alle 26 Buchstaben in Fach 3; Gold: alle in Fach 6 und alle Ziffern in Fach 4 | 1 | Lernkartei; es zählt das höchste je erreichte Fach, erreicht mit Zeichen ≥ 18 WPM |
| Mitschreiben im Fluss | 10 / 15 / 22 WPM effektiv | 15 | Kontinuierlich mit Klartext (Wörter, Wendungen, QSO; Gold nur Wendungen oder QSO), Zeichensatz mindestens Lektion 15, voller 3-Min.-Lauf, ≥ 90 % abzüglich überzähliger Tasten, Zeichen ≥ 18 WPM. Mit eigenen Wörtern aus `woerter.txt` zählt „Wörter“ nicht |
| QRQ | 20 / 25 / 30 / 35 WPM | 40 | Kontinuierlich mit Zufallsgruppen (≥ 5 Zeichen) aus dem vollen Zeichensatz, ohne Farnsworth, voller 3-Min.-Lauf, ≥ 90 % abzüglich überzähliger Tasten |
| QRN-fest | Band leicht 90 % / mittel 90 % / stark 85 % | 25 | Gruppen oder Kontinuierlich mit Zufallszeichen, ≥ 200 Zeichen, Bandbedingungen den ganzen Lauf an und nicht leichter gestellt, Störlautstärke ≥ 100 %, Zeichen ≥ 20 WPM, effektiv ≥ 12 WPM; bei Gruppen zählt der rechtzeitige erste Versuch |
| Rufz | 2.000 / 3.500 / 5.500 / 7.500 Punkte | 27 | Voller Durchgang mit 50 Rufzeichen, ohne Präfix-Filter, Starttempo ≥ 20 WPM |
| Contest | siehe rechts | 41 | Durchgang ≥ 10 Min.; Bronze: ≥ 20 WPM, 10 QSOs in 10 Min., ≤ 10 % Fehler; Silber: ≥ 25 WPM, Aktivität ≥ 2, 20 QSOs, ≤ 5 % Fehler; Gold: ≥ 30 WPM, Aktivität ≥ 3, 25 QSOs, höchstens 1 Fehler |
| WPX | 100 / 400 / 1.200 / 2.000 Präfixe | 25 | Verschiedene WPX-Präfixe, beim ersten Versuch richtig (Rufzeichen und Contest, dort ohne Rückfrage nach dem Call), Zeichen ≥ 18 WPM |
| Kopfhörer | 15 / 20 / 25 WPM effektiv | 41 | 3 normale QSOs in Folge mit „Kopfhören + Fragen“, alle Fragen richtig, ohne „Nochmal“, Zeichen ≥ 18 WPM; Silber und Gold mit der Länge Normal oder Lang. Ein QSO ohne „Prüfen“ zu überspringen, unterbricht die Folge |
| Verwechslung überwunden | 1 / 3 / 6 Paare | 5 | Ein Paar, das zu deinen häufigsten Verwechslungen gehörte, 28 Tage lang mit je ≥ 40 Versuchen höchstens einmal verwechselt |
| Ausdauer | 10 / 50 / 150 / 365 Tage | – | Tage mit ≥ 10 Min. Übung, nicht in Folge |
| Zeichen gehört | 5.000 / 25.000 / 100.000 / 250.000 | – | Richtig erkannte Zufallszeichen, Zeichen ≥ 18 WPM |
| Clubabend | 1 / 5 / 15 / 40 Abende | – | Tage mit zusammen ≥ 10 Min. Netzwerk-Übung, mitgemacht oder als Trainer geleitet (nur Durchgänge mit Teilnehmern) |
| Erstes QSO verstanden | – | 40 | Normales QSO mit Abfrage, alles richtig, ohne „Nochmal“, ≥ 15 WPM effektiv, Zeichen ≥ 18 WPM |
| Worked All Contests | – | 41 | Alle 5 Contest-Arten mit je ≥ 30 QSOs und ≤ 10 % Fehlern |
| Q-Gruppen-Kenner | – | 40 | Jede der 20 Q-Gruppen 3× beim ersten Hören richtig, an mindestens 2 Tagen, Zeichen ≥ 18 WPM |
| Alle Ziffern | – | 39 | Alle 10 Ziffern mindestens in Fach 3, erreicht mit Zeichen ≥ 18 WPM |

- Bei Koch, Fluss, QRQ, QRN-fest, Rufz und Contest gilt **Silber und höher
  erst an zwei verschiedenen Tagen** – ein Glückstreffer reicht nicht. Wer
  gleich in Lektion 41 einsteigt, bekommt am ersten Tag Bronze und mit einem
  weiteren bestandenen Lauf an einem anderen Tag Silber und Gold.
- Gezählt werden nur Durchgänge ohne Selbstbewertung.
- Erreichte Siegel stehen mit Datum in der Datenbank und gehen nie
  verloren, auch nicht mit „Gesamtstatistik zurücksetzen“.
- Beim ersten Start mit Diplomen wird still nachgetragen, was sich aus dem
  bisherigen Üben ergibt (mit dem Tag, an dem es erreicht wurde); ein
  Hinweis sagt, wie viele Diplome es sind.

## Lebenslinie

Unter den Diplomen im Reiter **Statistik** zeigt die **Lebenslinie** den
langen Weg vom ersten Üben bis heute: Sterne der Tagesübung aufsummiert,
die höchste geübte Koch-Lektion (bis zur Abschlusslektion 41) und das
Tagestempo der Tagesübung, darunter die Siegel der Diplome als Rauten in
ihrer Farbe. Alle drei Linien steigen nur oder bleiben stehen; mit der
Maus siehst du für jeden Tag die Werte und die Siegel. Die Lebenslinie
bleibt auch nach „Gesamtstatistik zurücksetzen“ vollständig.

## Lernweg für Einsteiger

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
   Einzelzeichen. Nach einem Fehler siehst und hörst du die Lösung, dann
   geht es weiter wie im Funkbetrieb; schwache Zeichen kommen über die
   Gewichtung später wieder. Unter „Lösung zeigen nach“ lassen sich bis zu
   3 Fehlversuche einstellen: Dann werden erst nur die falschen Stellen
   markiert und die Gruppe kommt noch einmal.
4. Wer in den Gruppen (oder im Modus Kontinuierlich) in einem Durchgang mit
   mindestens 50 Zeichen 90 % beim ersten Versuch schafft, bekommt die
   nächste Lektion angeboten. Für die Lektion zählt ein erster Versuch nur,
   wenn du die Gruppe nicht mit der Leertaste wiederholt hast und zügig
   geantwortet hast (1,5 s plus 0,6 s je Zeichen nach Tonende); zu viel
   Getipptes zählt als Fehler. Schwache und neue Zeichen kommen automatisch
   öfter dran. Nach den 40 Lektionen von lcwo.net schließt Lektion 41 ab:
   alle Zeichen, keins mehr als neu bevorzugt (schwache kommen weiter
   öfter). Wer möchte, nimmt danach in den Lektionen 42–45 die
   Betriebszeichen aus dem QSO dazu: AR (Taste `+`), KN (`(`), SK (`*`) und
   BK (`#`). Dorthin wird nicht von selbst weitergeschaltet, die Lektion
   stellst du oben ein; danach wird dir das nächste Betriebszeichen wieder
   angeboten. Gelernte Betriebszeichen wiederholt auch die Tagesübung.
5. Ab Lektion 6 gibt es genug Wörter für den Reiter **Wörter** (Wörter mit
   dem neuesten Zeichen kommen bevorzugt), danach
   **Kontinuierlich** und **QSO**.
6. Im Reiter **Statistik** (Verwechslungen der letzten 30 Tage) zeigt „Die 4 häufigsten gezielt üben“, welche
   Zeichen du verwechselst, und übt genau diese gegeneinander. „↩ Lektion“
   oben führt zurück zu deiner Lektion.

Außerdem hilfreich:

- **Täglich kurz** üben schlägt selten lang: Die Fußzeile zeigt die heutige
  Übungszeit und das Tagesziel (einstellbar im Reiter Statistik), der
  Wochenstreifen oben die Tage, an denen du geübt hast.
- **Tonhöhe und Tempo leicht variieren** (gemeinsame Einstellung): Wer immer
  nur genau einen Klang hört, tut sich auf dem Band schwerer.
- **Einstellungen …** (oben rechts neben „Weitere Optionen“, oder
  **Strg+Komma**) öffnet ein Fenster mit allem, was man einmal einstellt:
  Rufzeichen und Name, Sprache, Barrierefreiheit (Schriftgröße, hoher
  Kontrast, Ansage) und Daten sichern/einlesen. Unter „▸ Weitere Optionen“
  bleiben die Übungsoptionen: Farnsworth, schwache Zeichen, variieren,
  Bandbedingungen.
- **Sprache:** Unter „Einstellungen …“ → „Sprache / Language“ lässt sich
  die Oberfläche auf Englisch umstellen (wirkt nach Neustart). Die Stimme im
  Reiter „Sprechen“ bleibt deutsch.
- **Schriftgröße:** Unter „Einstellungen …“ → „Schriftgröße“ oder mit
  **Strg+Plus**, **Strg+Minus** und **Strg+0** (normal) wird die ganze
  Oberfläche größer, bis 200 %; das Fenster wächst mit. Die Einstellung
  bleibt gespeichert.
- **Rufzeichen und Name:** Unter „Einstellungen …“ einmal eintragen.
  Sie stehen auf den Diplomen und sind die Vorgabe für „Mein
  Rufzeichen“ im Contest und „Name/Rufzeichen“ im Netzwerk (dort ohne Name
  das Rufzeichen). Beide Felder ziehen mit, bis du dort etwas anderes
  einträgst, etwa ein Contest-Rufzeichen. Ohne eigenes Rufzeichen genügt
  der Name: Er steht dann allein auf dem Diplom; für den Contest trägst du
  dort ein ausgedachtes Rufzeichen ein.

## Bandbedingungen

Eingestellt wird an einer Stelle: **Weitere Optionen → Bandbedingungen
→ Einstellen …** oder „Einstellen …“ in einem Reiter. Einzeln zuschaltbar
und regelbar sind Bandrauschen, Knackstörungen (QRN), QSB, Chirp
(zwitschernder Sender), SSB-QRM (verstimmte Sprache), CW-QRM auf der
Nachbarfrequenz und **Stärkeunterschiede** (wie
unterschiedlich laut die Stationen in QSO und Contest ankommen – bis 2.37
ein Teil von QSB, jetzt getrennt vom Fading); dazu die **Lautstärke der
Störgeräusche** gegenüber den Zeichen. Die Knöpfe **leicht**, **mittel**
und **stark** setzen die Stufen, nach denen auch das Diplom QRN-fest
zählt; das Fenster zeigt, welcher Stufe die Einstellung mindestens
entspricht.

Das Rauschen wird als **Rauschabstand (S/N)** angegeben, gemessen in
2,4 kHz Bandbreite gegenüber dem ungeschwächten Signal; der Regler reicht
von +20 dB bis −10 dB. Das Ohr hört CW wie durch ein Filter von etwa
50 Hz, dort ist der Abstand rund 17 dB größer – −4 dB fühlen sich also
an wie gut +13 dB im schmalen Filter. Wird das Rauschen lauter als der
Empfänger es durchließe, regelt er wie eine AGC das Signal herunter
statt zu übersteuern. Chirp steht in Hz (größte Ablage beim Tasten).

| Stufe | Rauschen (S/N) | QSB (tiefstes Loch) | dazu |
|---|---|---|---|
| leicht | +8 dB | 30 % (ca. −3 dB) | – |
| mittel | +2 dB | 50 % (ca. −5,5 dB) | QRN 30 % |
| stark | −4 dB | 80 % (ca. −12 dB) | QRN 50 %, CW-QRM 30 % |

Das Fading wechselt unregelmäßig (zwei überlagerte Schwankungen), seine
Tiefe folgt dem Regler und streut nur wenig – die Stufe bestimmt die
Schwierigkeit, nicht der Zufall.

**CW-QRM-Abstand:** Der Nachbar-Run liegt **weit** (300–500 Hz) daneben,
**nah** (50–200 Hz) oder auf **Zero-Beat** (fast auf deiner Frequenz).
Nah und Zero-Beat sind das eigentliche Training im selektiven Hören, wie
es Contester brauchen. Mit eingeschaltetem QSB schwankt auch das QRM, und
zwar unabhängig von deinen Stationen.

**CW-Filter:** 2,4 kHz (wie ein SSB-Filter, die Grundeinstellung),
500 Hz oder 250 Hz um deine Tonhöhe. Zeichen, Rauschen und Störungen
laufen hindurch, dein eigener Mithörton im Contest nicht. Ein schmales
Filter nimmt Rauschen weg (500 Hz rund 6 dB, 250 Hz rund 9 dB) und
QRM, das weit daneben liegt; es klingelt aber leicht, und Stationen
neben deiner Tonhöhe (Anrufer im Contest, die Gegenstation im QSO)
werden leiser. Gegen QRM nah oder auf Zero-Beat hilft es nicht. Der
S/N-Wert bezieht sich weiter auf 2,4 kHz; das Fenster zeigt zusätzlich
den Wert im Filter. Für die Stufen und das Diplom zählt der Wert im
Filter: „mittel“ mit 500-Hz-Filter entspricht etwa „leicht“.

**Wann zuschalten?** Neue Zeichen ohne Störungen lernen. Bandbedingungen
lohnen sich, wenn der Zeichensatz ohne Störungen sicher sitzt (90 % und
mehr); dann mit „leicht“ beginnen.

In den Reitern (Gruppen, Wörter, Rufzeichen, Kontinuierlich, QSO, Contest,
Netzwerk) schaltest du die Bandbedingungen nur an oder aus. Stärke und
Lautstärke wirken sofort, auch im laufenden Durchgang; für das Diplom
zählt dann das Schwächste im Durchgang. An und aus geht in Gruppen,
Wörtern, Rufzeichen, Kontinuierlich und Netzwerk nur zwischen zwei
Durchgängen, in QSO und Contest jederzeit. Im Netzwerk hören alle
Teilnehmer die Einstellung des Trainers, mit demselben Fading,
denselben Stationen und demselben Nachbar-QRM, Gewitter und Träger
(Trainer und Teilnehmer ab Version 2.39). Nur wer eine eigene
`callsigns.scp` hat, hört im QRM womöglich andere Rufzeichen.

Wie auf dem Band laufen Fading, Rauschen und das Nachbar-QRM auch während
deiner Antwortpause weiter; jede Sequenz trifft eine andere Stelle.

Durchgänge mit Bandbedingungen erscheinen im Verlauf, zählen aber nicht
für die Zeichenstatistik, die Gewichtung, die Verwechslungen und die
Lernkartei: Ein Zeichen, das im Rauschen oder in einem QSB-Loch
untergeht, sagt nichts darüber, ob du es kannst.

## Netzwerk: Üben in der Gruppe

Für Kursabende und Clubheim: Alle Rechner sind im selben Netz (WLAN oder
LAN), einer ist der Trainer, die anderen melden sich als Teilnehmer an.
Übertragen wird nur Text; den Ton erzeugt jeder Rechner selbst – ohne
Aussetzer, mit eigenem Kopfhörer und eigener Tonhöhe.

**Trainer:** Im Reiter *Netzwerk* „Trainer“ wählen, **Sitzung öffnen**.
Angezeigt werden Adresse und eine vierstellige PIN für die Teilnehmer.
Dann Inhalt (Einzelzeichen, Gruppen, Wörter, Rufzeichen, Wendungen,
QSO-Klartext oder **eigener Text**, eine Zeile je Sequenz; Betriebszeichen
als + für AR, ( für KN, * für SK, # für BK), Anzahl Sequenzen (bei
QSO-Klartext ganze QSOs, gesendet in Abschnitten bis zum nächsten =, K
oder Schlusszeichen wie „UR RST 599 599 =“), Antwortzeit und
Bandbedingungen wählen; Zeichensatz, Tempo und Farnsworth kommen aus der
Kopfleiste. Bei langsamem Zeichentempo (unter 18 WPM) weist die
Kopfleiste in allen Reitern darauf hin, dass man die Zeichen mitzählen
kann, und bietet das Koch-Tempo 20/10 an.
Nach **Start** kommt zuerst das Anfangszeichen VVV = (abschaltbar), nach der
letzten Sequenz das Schlusszeichen +. Dann bekommen alle dieselbe Sequenz
zur selben Zeit. Die
nächste kommt, sobald alle geantwortet haben oder die Antwortzeit um ist
(oder mit **Weiter**); **Für alle wiederholen** spielt die aktuelle noch
einmal. Die Tabelle zeigt je Teilnehmer die aktuelle Antwort, den Anteil
richtiger Zeichen, wie viele Sequenzen **flüssig** richtig waren und die
typische Zeit vom Tonende bis Enter, darunter die Gruppe: Trefferquote,
Anteil flüssiger Sequenzen, häufigste Fehler, schwächste Zeichen. Flüssig
heißt: richtig beim ersten Hören und schnell genug, dass nicht gezählt
wurde – im selben Zeitfenster wie in den Reitern Gruppen, Wörter und
Rufzeichen (1,5 s plus 0,6 s je Zeichen nach dem Ton). Die Antwortzeit ist
nur die harte Grenze. Ein Klick auf einen Teilnehmer zeigt seine Fehler und
schwächsten Zeichen. Bei vielen Teilnehmern lässt sich die Tabelle **in ein
eigenes Fenster** auskoppeln (etwa für einen zweiten Bildschirm oder den
Beamer); dort wirken F5–F7 ebenso, Schließen holt sie zurück in den Reiter. Nach genug Sequenzen im selben Tempo (50 Zeichen über
alle) gibt es eine **Tempo-Empfehlung**: ab 90 % flüssig schneller, unter
75 % langsamer, per Knopf um 1 WPM effektiv übernehmbar. **Als CSV
speichern** legt eine Tabelle in `stats/` ab: je Teilnehmer eine Zeile mit
Trefferquote, flüssigen Sequenzen, häufigsten Fehlern und schwächsten
Zeichen, je Sequenz eine Spalte (mit Tempo; ↻ = für alle wiederholt) mit
dem Getippten und der Zeit bis zur Antwort.

**Fester Takt (Mitschreiben auf Papier):** Unter *Ablauf* statt „Warten
auf Antworten“ den festen Takt wählen – für Kurse, in denen nicht jeder
einen Rechner hat. Die nächste Sequenz kommt dann nach Ton plus
**Schreibpause**, egal wer schon geantwortet hat. Die Pause gilt gleich für
jede Sequenz; die Vorgabe richtet sich nach dem Inhalt (Einzelzeichen 2 s,
Wörter 3 s, Gruppen, Rufzeichen und eigener Text 4 s, Wendungen und QSO 5 s),
denn wer zu lange Zeit hat, fängt an zu grübeln. Bis zum Ende zeigt der
Trainerbildschirm keine Lösung – er hängt womöglich am Beamer: Der Status
nennt nur „Nr. 7 von 20“, die Tabelle nur, ob eine Antwort eingegangen ist,
Auswertung und eigener Text sind ausgeblendet. **Für alle wiederholen**
(F6) bleibt für Notfälle und verlängert die Frist; **Weiter** (F7) geht
sofort zur nächsten. Besser Blöcke von 20–25 Sequenzen mit Auflösung
dazwischen als „bis Stop“. Wer nur mit Zettel und Stift dabei ist, braucht
weder Rechner noch Anmeldung, hört aber über die Lautsprecher des Trainers:
Beim Umschalten auf den festen Takt ist „Auch an diesem Rechner abspielen“
daher gleich eingeschaltet. Sie vergleichen selbst mit der Auflösung –
oder geben ihren Zettel ab, und der Trainer tippt ihn nach dem Durchgang
unter **Papierbogen eintragen** ein (Name, dann je Nummer die Zeile, leer =
verpasst; derselbe Name ersetzt den Bogen). Wer einen Rechner hat und
trotzdem mit dem Stift schreiben will, hakt beim Verbinden „Im festen Takt
auf Papier mitschreiben und am Ende abtippen“ an: Während des Durchgangs
bleibt das Eingabefeld zu, danach erscheint je Nummer ein Feld zum
Abtippen, **Auswerten** schickt es an den Trainer. Abgetippte Antworten
zählen für richtig/falsch, Fehler und schwache Zeichen, aber ohne Zeit:
nicht als flüssig und nicht für die Tempo-Empfehlung, und in der eigenen
Statistik nicht für Gewichtung und Lernkartei. In der Tabelle steht bei
ihnen „Papier“.

**Gehör schonen:** Wer Tinnitus hat oder ein Hörgerät trägt, hakt als
Teilnehmer „Störgeräusche bei mir leiser“ an und wählt 10–90 % der
Einstellung des Trainers. Leiser werden nur Rauschen und Störungen, die
Zeichen bleiben gleich; lauter als beim Trainer geht nicht. Damit die
Ergebnisse vergleichbar bleiben, sieht der Trainer ein **↓** hinter dem
Status, in der Detailzeile und in der CSV-Datei. Spielt der Lautsprecher
des Trainers, gilt seine Einstellung. Trainer bis Version 2.37 zeigen
die Markierung nicht.

**Antwortbogen drucken** (bei den Optionen des festen Takts) öffnet einen
Bogen im Browser zum Ausdrucken: Name, Datum, nummerierte Zeilen
spaltenweise wie in der Auflösung – bei Gruppen und Einzelzeichen mit
einem Kästchen je Zeichen, sonst mit freier Linie; so viele Zeilen wie
eingestellt (bei „bis Stop“ und QSOs 25).

**Kontinuierlich:** Unter *Ablauf* „Kontinuierlich“ wählen und die
**Dauer** in Minuten einstellen. Dann kommen Gruppen (oder Wörter,
Rufzeichen …) ohne Pause wie im Reiter *Kontinuierlich*, bis die Zeit um
ist; alle tippen fortlaufend mit, ohne Enter. Ausgewertet wird am Ende wie
dort: Eine Taste zählt nur, wenn sie zeitlich zum Zeichen passt. Jeder
Teilnehmer meldet sein Ergebnis je Gruppe, damit gelten Tabelle,
Auflösung (nummerierte Gruppen) und CSV wie gewohnt; während des
Durchgangs zeigt der Trainerbildschirm wie im festen Takt nichts, was
Lösungen verrät, nur die Restzeit. Stop vorzeitig wertet bis dahin.
Bandbedingungen liegen unter dem ganzen Durchgang; eigenen Text gibt es
hier nicht.

**Ton für alle über den Lautsprecher:** Mit „Ton für alle nur über diesen
Rechner (Lautsprecher)“ spielt nur der Trainerrechner, die
Teilnehmer-Rechner bleiben stumm und dienen nur zum Eintippen. So braucht
niemand Kopfhörer, und alle hören gleichzeitig dasselbe – jeder Rechner
spielt sonst etwas versetzt, je nach Netz und Soundkarte. Die Zeit bis zur
Antwort rechnen die Teilnehmer-Rechner ab dem Eingang der Sequenz. Die
Lösung kommt in diesem Fall einmal für alle über den Lautsprecher, sobald
jemand sie nicht flüssig richtig hatte. Das geht in beiden Abläufen und
passt gut zum festen Takt, wenn Papier und Rechner gemischt sind.

**Auflösung:** Der Knopf neben „Als CSV speichern“ öffnet ein eigenes
Fenster für den Beamer, in beiden Abläufen. Während des Durchgangs zeigt es
groß die laufende Nummer („Verpasst? Lücke lassen und bei der nächsten
Nummer weiterschreiben.“), danach alle Lösungen nummeriert, spaltenweise
von oben nach unten wie auf dem Zettel, in Monoschrift; ↻ markiert, was
für alle wiederholt wurde. A−/A+ (oder +/−) ändern die Schriftgröße,
**Kopieren** legt die Liste in die Zwischenablage. Ein Klick auf eine
Lösung – oder Pfeiltasten und Leertaste – spielt sie am Trainerrechner
noch einmal ab, ohne Störungen: So wird aus dem Nachlesen ein Nachhören.

**Teilnehmer:** „Teilnehmer“ wählen, Name oder Rufzeichen und die PIN
eintragen, **Suchen** (oder die Adresse des Trainers eingeben) und
**Verbinden**. Getippt wird schon während des Tons; mit dem letzten
Zeichen ist die Antwort fertig, Enter braucht es nur, wenn man weniger
Zeichen hat. Je Sequenz gibt es einen Versuch, danach steht die Lösung da. War sie nicht
flüssig richtig, kommt die Sequenz zur Lösung noch einmal (abschaltbar
beim Trainer). Wer nicht rechtzeitig fertig wird, dem wird das bis dahin
Getippte gewertet. Im festen Takt steht danach nur „Nr. 7 notiert“;
die Lösungen kommen am Ende als Liste mit gesendet, getippt und ✓/✗, und
jede Sequenz lässt sich per Doppelklick oder Leertaste noch einmal hören.
Die Ergebnisse zählen für die eigene Statistik wie ein
normaler Durchgang, mit der Zeit je Zeichen wie beim Mitschreiben; nach
„Für alle wiederholen“ oder zu langsam gilt ein richtiges Zeichen als
unsicher und kommt mit „schwache bevorzugt“ öfter. Übungszeit zählt nur,
solange ein Durchgang läuft, nicht beim Warten auf den Trainer.

Der Trainer braucht den Port 7373 (TCP) und für die Suche 7374 (UDP).
Unter Windows fragt beim ersten Öffnen die Firewall – für private
Netzwerke zulassen. Findet die Suche nichts (manche WLANs blockieren
Broadcasts), die angezeigte Adresse von Hand eingeben.

Hat der Trainer eine neuere Programmversion, fragt der Teilnehmer beim
Verbinden, ob er sie laden soll (siehe *Updates*); danach startet der
Morsetrainer neu und verbindet sich wieder mit dem Trainer.

**Sicherheit:** Die Verbindung ist nicht verschlüsselt, und die
vierstellige PIN hält nur Versehen ab, keinen Angreifer. Wer im selben
Netz mitliest, sieht Namen, Übungstext und Antworten und könnte sich mit
der PIN anmelden. Der Netzwerkmodus ist für das Club- oder Heimnetz
gedacht; in fremden oder öffentlichen WLANs (Hotel, Café, Messe) besser
keine Sitzung öffnen und die Sitzung nach dem Kurs schließen. Ein Update
reicht der Trainer nicht weiter: Er nennt nur seine Versionsnummer,
geladen wird immer von GitHub (siehe *Updates*).

Ab Version 2.31 bremst der Trainer das Durchprobieren der PIN: Nach 5
falschen PINs ist der Rechner eine Minute gesperrt (auch für die richtige
PIN), und unter Adresse und PIN steht „Zu oft falsche PIN von …“. Taucht
ein Unbekannter in der Tabelle auf, ihn auswählen und **Entfernen**: Die
Verbindung wird getrennt, und dieser Rechner kommt bis zum Schließen der
Sitzung nicht wieder herein. Außerdem trennt der Trainer Rechner, die ihn
mit Verbindungen oder Nachrichten überschütten.

## Hilfe im Programm

Der Knopf **Hilfe** rechts in der Fußzeile zeigt die Änderungen der
Versionen (CHANGELOG.md) und diese Anleitung.

## Barrierefreiheit

- **Ansage (F9):** Das Programm sagt mit der eingebauten Stimme selbst an,
  was sonst nur auf dem Bildschirm steht – ohne Screenreader. F9 schaltet
  die Ansage an und aus (auch unter „Einstellungen …“ → „Rückmeldung
  ansagen“), die Stimme bestätigt es.
- **Was angesagt wird:** in Gruppen, Wörtern und Rufzeichen das Ergebnis
  jeder Antwort („Richtig“, „Falsch. Hör noch einmal hin“, nach dem letzten
  Versuch „Gesendet: Ka, Emm, U. Getippt: Ka, Emm, Emm“), beim Kopfhören
  die Lösung; in Einzelzeichen nur Fehler („Falsch. Ka, nicht Emm“), bei
  richtigen Antworten kommt der kurze Quittungston; am Ende jedes
  Durchgangs das Ergebnis; der Name des Reiters beim Wechseln; die Karten
  der Tagesübung. Der Ablauf wartet, bis die Ansage zu Ende ist.
- **QSO:** am Ende, was jetzt zu tun ist („Trag ins Log ein … F8 prüft“)
  bzw. beim Mittippen das Ergebnis in Prozent; in der Abfrage beim
  Hineinspringen der Name des Feldes („Name, Station 2“), nach „Prüfen“
  das Ergebnis mit den richtigen Werten (Rufzeichen buchstabiert, Namen
  als Wort) und beim erneuten Besuch eines Feldes, ob es richtig war.
- **Contest:** Fehler beim Loggen gleich nach deinem TU, im Tonstrom über
  dem Pile-up („Busted. Richtig: Delta, Lima, Eins …“, „Austausch falsch“,
  „Nicht im Log“); richtig geloggte QSOs bleiben still, damit die Rate
  nicht leidet. Am Ende das Ergebnis.
- **Netzwerk (als Teilnehmer):** Verbinden, Trennen und Ablehnung; nach
  jeder Antwort „Richtig“ oder „Falsch. Richtig wäre: Ka, Emm, U“ (im
  festen Takt nicht, dort kommt gleich die nächste Sequenz); am Ende das
  Ergebnis, nach dem Schlusszeichen; beim Papier die Aufforderung zum
  Abtippen und danach das Ergebnis. Neue Sequenzen des Trainers haben
  Vorrang und unterbrechen eine Ansage; die Lösung wird erst nach der
  Ansage nachgespielt.
- **Abendbilanz:** wird ganz vorgelesen – Sterne, Wochenziel, was besser
  geworden ist, was fast geschafft ist, neue Siegel –, dann „Enter:
  Fertig“ und, falls angeboten, „Mit Tab: Noch 5 Min …“. F11 im Fenster
  wiederholt sie. Symbole wie %, →, ≥ oder ★ spricht die Ansage als Wort.
- **Sprechen:** Der Reiter spricht beim Üben selbst; angesagt wird nur,
  warum er nicht startet, das Ende („Fertig: 20 Einträge“), der MP3-Export
  und sein Ergebnis. F11 nennt den Fortschritt („3 von 20“).
- **Diplom-Fenster:** neue Siegel mit Bedingung und Datum, dann der
  Hinweis auf Tab und Escape; die Drucken-Knöpfe sagen, welches Diplom sie
  drucken. F11 im Fenster wiederholt.
- **Bedienelemente:** Springst du mit Tab in ein Feld, einen Knopf oder
  Schalter, sagt es, was es ist und wie es steht („Sprache / Language,
  Auswahl, Deutsch“, „Hoher Kontrast, Schalter, aus“, „Tempo, Zahlenfeld,
  20 WPM“); was du mit Leertaste, Pfeiltasten oder in einer Auswahl
  änderst, wird ebenfalls angesagt. Setzt das Programm den Fokus selbst
  (etwa ins Antwortfeld), bleibt es still.
- **Tabellen:** Gehst du mit den Pfeiltasten durch eine Tabelle
  (Statistik, Diplome, Contest-Log), wird die Zeile mit den Spaltennamen
  vorgelesen.
- **Wo bin ich? (F11):** liest Reiter, Status, letzte Rückmeldung und
  Restzeit vor, in der Tagesübung die aktuelle Karte, im Reiter Statistik
  eine Übersicht (Gesamtergebnis, meiste Fehler, Verwechslungen,
  Lernkartei, Siegel, heute geübt) – auch bei ausgeschalteter Ansage.
- **Schriftgröße:** Strg+Plus/Strg+Minus/Strg+0, siehe oben.
- **Hoher Kontrast:** „Einstellungen …“ → „Hoher Kontrast (Schwarz,
  Weiß, Gelb)“, wirkt nach einem Neustart. Schwarzer Grund, weiße Schrift,
  gelbe Hauptknöpfe und Markierungen, kräftige Rahmen; jede Schrift hebt
  sich mindestens 7:1 vom Grund ab. Richtig und falsch stehen immer auch
  als Text da, nicht nur als Farbe.
- Die Ansage spricht die Sprache der Oberfläche: deutsch mit der Stimme
  Thorsten, englisch mit der Stimme Lessac (Rufzeichen dann „Delta Lima
  One“). Fehlt die Stimme, kommt bei F9 und F11 ein Fehlerton, und der
  Grund steht in der Statuszeile. Der Reiter Sprechen bleibt deutsch.

## Tastenkürzel

- **Überall:** Strg+Plus/Strg+Minus Schrift größer/kleiner, Strg+0 normal
  (auf dem Mac auch Cmd); F9 Ansage an/aus, F11 vorlesen, wo du bist;
  Alt+1 … Alt+9 und Alt+0 wechseln zu Reiter 1 … 10, Strg+Tab blättert
  durch die Reiter (auf dem Mac Cmd+1 … Cmd+9); Strg+B öffnet die
  Bandbedingungen, Strg+Komma die Einstellungen (auf dem Mac auch Cmd+Komma).
- **Auf dem Mac** sind F9, F11 und F12 Medientasten oder vom System belegt
  (Fn+F11 zeigt den Schreibtisch). Dafür gibt es Cmd+Umschalt+A (Ansage
  an/aus), Cmd+Umschalt+W (wo bin ich) und Cmd+Umschalt+T (Tagesübung).
- **Ohne Maus:** Tab und Umschalt+Tab gehen durch alle Felder, Knöpfe und
  Schalter (der Fokus ist farbig markiert), Leertaste drückt den Knopf
  bzw. schaltet um, Pfeiltasten wählen in Listen, Reglern und Reitern.
  Esc schließt die Nebenfenster.
- **Tagesübung:** F12 startet, Enter überspringt die Zwischenkarte, Esc
  beendet.
- **Einzelzeichen, Gruppen, Wörter, Rufzeichen:** Leertaste wiederholt.
  Beim Kopfhören: Enter löst auf, J = gewusst, N = nicht gewusst.
- **Rufz (nach dem Durchgang):** F6 verpasste Rufzeichen nachhören bzw. das aktuelle nochmal, F7 von vorn, Esc anhalten.
- **Sprechen:** F5 Start/Stop, Leertaste spielt den aktuellen Eintrag noch einmal, Esc stoppt.
- **QSO:** F5 neues QSO/Stop, F6 nochmal hören, F7 Text zeigen, F8 prüfen.
- **Netzwerk (Trainer):** F5 Start/Stop, F6 für alle wiederholen, F7 weiter.
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

Ab Version 2.30 liegt neben den Programmen `SHA256SUMS.txt` mit ihren
Prüfsummen. Zum Nachprüfen unter Linux im Download-Ordner
`sha256sum -c --ignore-missing SHA256SUMS.txt`, unter Windows in der
PowerShell `Get-FileHash Morsetrainer.exe` und den Wert mit der Zeile in
`SHA256SUMS.txt` vergleichen.

### macOS

Für Macs mit Apple-Prozessor (M1 und neuer) gibt es
`Morsetrainer-macOS.zip`. Herunterladen, entpacken (Doppelklick, falls der
Browser das nicht schon getan hat) und `Morsetrainer.app` in den Ordner
„Programme“ ziehen. Die App ist bisher nicht auf einem Mac getestet –
Rückmeldungen sind willkommen.

Da die App nicht bei Apple signiert ist (dafür bräuchte es ein bezahltes
Apple-Entwicklerkonto), blockiert macOS den ersten Start:

- **macOS 15 (Sequoia) und neuer:** Die App einmal per Doppelklick
  starten und die Meldung mit „Fertig“ schließen. Dann
  „Systemeinstellungen“ → „Datenschutz & Sicherheit“, ganz unten bei
  „Morsetrainer wurde blockiert“ auf „Dennoch öffnen“ klicken und mit dem
  Passwort bestätigen.
- **macOS 14 und älter:** Im Finder mit Rechtsklick (oder Ctrl-Klick) auf
  `Morsetrainer.app` → „Öffnen“, dann in der Meldung noch einmal „Öffnen“.

Danach startet die App ganz normal. Meldet macOS, die App sei
„beschädigt“, hilft im Terminal
`xattr -dr com.apple.quarantine /Applications/Morsetrainer.app`.

Die Daten liegen in `~/Library/Application Support/Morsetrainer/`. Das
automatische Update gibt es auf dem Mac nicht, nur den Hinweis auf eine
neue Version; dann die neue ZIP-Datei laden und die App im Ordner
„Programme“ ersetzen. Die Daten bleiben dabei erhalten. Nach jedem
Austausch will macOS die Freigabe noch einmal.

**Ältere Macs mit Intel-Prozessor** starten den Morsetrainer aus dem
Quelltext:

1. Python 3.10 oder neuer von [python.org](https://www.python.org/downloads/macos/)
   installieren. Dieses Python bringt ein funktionierendes Tk mit; mit dem
   Python aus Homebrew bleibt das Fenster oft leer oder es fehlt `tkinter`.
2. Unter [Releases](https://github.com/tilde1970/Morsetrainer/releases) beim
   neuesten Release „Source code (zip)“ laden und entpacken.
3. Im Terminal in den entpackten Ordner wechseln und einmalig einrichten:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   bash packaging/get_voice.sh
   ```

   Der letzte Befehl lädt die Stimmen für Ansage und Reiter Sprechen
   (gut 120 MB); ohne ihn läuft alles andere, nur gesprochen wird nicht.

4. Starten mit `python main.py`. Später reichen
   `source .venv/bin/activate` und `python main.py` im selben Ordner.

So gestartet liegen die Daten im entpackten Ordner. Zum Aktualisieren den
neuen Quelltext entpacken und `stats/`, `window_state.json` und ggf.
`callsigns.scp` und `woerter.txt` aus dem alten Ordner hineinkopieren.

### Updates

Beim Start schaut der Morsetrainer im Hintergrund nach, ob es ein neueres
Release gibt, und fragt dann, ob er es laden soll. Mit „Ja“ lädt er die
exe bzw. das AppImage von GitHub, tauscht die eigene Datei aus und startet
neu; mit „Nein“ fragt er bei dieser Version nicht noch einmal, unten in
der Fußzeile steht nur „Version … verfügbar“. Ohne Internet passiert
nichts, das Programm läuft ganz normal. Aus dem Quelltext gestartet und
auf dem Mac gibt es nur den Hinweis. Liegt die Datei in einem Ordner ohne
Schreibrecht, bitte von Hand herunterladen.

Geladen wird nur aus diesem Repository über HTTPS und nur eine neuere
Version. Die Datei muss zur Prüfsumme in `SHA256SUMS.txt` desselben
Releases passen, sonst wird sie verworfen und das Programm bleibt, wie es
ist. Das fängt abgebrochene und beschädigte Downloads ab. Vor einem
übernommenen GitHub-Konto schützt es nicht – wer das Release austauschen
kann, tauscht auch die Prüfsumme; eine Signatur gibt es nicht.

## Daten

Aus dem Quelltext gestartet liegen die Daten im Programmverzeichnis, beim
AppImage in `~/.local/share/morsetrainer/`, bei der exe in
`%APPDATA%\Morsetrainer\`, bei der Mac-App in
`~/Library/Application Support/Morsetrainer/`.

- `stats/morsetrainer.db`: alle Übungsdaten in einer SQLite-Datenbank –
  jeder Durchgang mit seinen Zeichen, Ergebnisse von QSO-Abfragen und
  Contests, Gesamtstatistik, Lernkartei, Tagesübung mit Sternen, Lektion
  und Tagestempo, Übungszeit pro Tag und die erreichten Diplome. Jede
  Zeile wird sofort gespeichert; ein Absturz kostet höchstens die
  laufende. Ist die Datei beschädigt, wird sie als
  `morsetrainer.db.defekt-<Zeit>` beiseitegelegt und eine neue begonnen.
- Außerdem in `stats/`: das zuletzt geöffnete Diplom (`diplom.html`) und
  die CSV-Tabellen aus dem Reiter Netzwerk (`…-netzwerk.csv`).
- Bis Version 2.27 lagen die Übungsdaten als einzelne Dateien in `stats/`
  (`*.jsonl`, `all_time.json`, `review.json`, `daily.json`, `awards.json`,
  `practice.json`, `results.jsonl`). Der erste Start einer neueren Version
  übernimmt sie in die Datenbank und verschiebt sie danach nach
  `stats/alt-json/`; gelöscht wird nichts.
- `window_state.json`: Fenstergröße und alle Einstellungen, auch die Sprache.
- `callsigns.scp`: Rufzeichenliste (Super Check Partial). Sie ist **nicht
  im Repository enthalten**. Lade die aktuelle `MASTER.SCP` von
  [supercheckpartial.com](https://www.supercheckpartial.com) herunter und
  lege sie als `callsigns.scp` in das Datenverzeichnis. Ohne die Datei
  erzeugt der Trainer Rufzeichen nach Landesmuster.
- `woerter.txt`: eigene Wörter für den Reiter „Wörter“, eins pro Zeile,
  optional mit Bedeutung: `DOK = Distrikts-Ortsverbandskenner`. Der Knopf
  „Eigene Wörter bearbeiten“ legt die Datei mit Anleitung an und öffnet sie.
  Die Wörter kommen zu den eingebauten dazu.

### Sichern und auf einen neuen Rechner umziehen

Unter „Einstellungen → Daten“ sichert **Sichern …** alle Einstellungen
und Daten (`stats/`, `window_state.json`, `woerter.txt`, `callsigns.scp`)
in eine ZIP-Datei an einem Ort deiner Wahl, etwa auf einem USB-Stick.
**Einlesen …** holt sie auf dem neuen Rechner zurück: `stats/` wird
vollständig ersetzt, die anderen Dateien, soweit sie in der Sicherung
sind. Der bisherige Stand landet vorher als `vor-import-<Zeit>.zip` im
Datenverzeichnis. Danach beendet sich das Programm; beim nächsten Start
gelten die eingelesenen Einstellungen. Die Datenbank kommt als stimmiger
Stand in die Sicherung, auch wenn gerade geübt wird; beim Einlesen wird
sie vorher geprüft. Sicherungen von Version 2.27 und älter lassen sich
weiter einlesen, ihre Dateien übernimmt der nächste Start. Die Stimme für die Sprachausgabe
(`voices/`) ist nicht dabei, sie steckt im AppImage bzw. in der exe.
