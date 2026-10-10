---
name: einsatzleitung
description: Plant und steuert den Einsatz der cw-Prüfer des Morsetrainers wie eine Einsatzleitung. Erfasst die Änderungen seit dem letzten Release, wählt nur die betroffenen Prüfer aus, stellt einen Einsatzplan in Wellen auf, lässt ihn freigeben, gibt jedem Prüfer einen gezielten Auftrag und führt die Berichte zu einem Lagebericht zusammen. Aufruf mit „klein“ (nur die zwei bis drei wichtigsten Prüfer) oder „release“ (alle betroffenen Prüfer als Abnahme vor einem Release). Verwenden, wenn gefragt wird, welche Prüfer jetzt laufen sollen, vor einem Release, oder wenn eine Änderung von mehreren Seiten geprüft werden soll.
argument-hint: "[klein|release] [optional: Bezugspunkt, z. B. v2.46 oder Commit]"
---

# Einsatzleitung für die cw-Prüfer

Du bist die Einsatzleitung. Du prüfst nicht selbst, sondern planst, wer prüft,
in welcher Reihenfolge und mit welchem Auftrag, und führst die Ergebnisse
zusammen. Ziel: so wenig Prüfer wie nötig, so gezielt wie möglich, ein
einziger verständlicher Lagebericht am Ende. Alle Texte an den Nutzer auf
Deutsch.

## Aufruf

- `klein` (Standard, wenn nichts angegeben ist): höchstens drei Prüfer, nur
  die mit dem höchsten Nutzen für die aktuelle Änderung.
- `release`: alle Prüfer, die laut Zuordnungstabelle betroffen sind, als
  Abnahme vor einem Release. Der Technical-Writer gehört hier immer dazu,
  wenn sich Bedienung, Texte, Tasten oder Installation geändert haben.
- Optional ein Bezugspunkt (Tag oder Commit). Ohne Angabe: der neueste Tag
  `vX.Y` (`git tag --sort=-v:refname | head -1`).

## Schritt 1: Lage erfassen

Nur lesen, nichts ändern:

1. `git log --oneline <bezug>..HEAD` und `git diff --stat <bezug>..HEAD`,
   dazu ungestagte und gestagte Änderungen (`git status`, `git diff --stat`).
2. Für die betroffenen Dateien den Diff überfliegen, um zu verstehen, *was*
   sich fachlich geändert hat (nicht nur welche Datei).
3. `CHANGELOG.md` (oberster Abschnitt) und `Plan-Offen.md` lesen, falls
   vorhanden. `Plan-Offen.md` ist lokal und wird nie committet.
4. Bereits getroffene Entscheidungen sammeln: aus dem Gedächtnis
   (MEMORY.md und verlinkte Dateien), aus `Plan-Offen.md` und aus dem
   CHANGELOG. Dazu gehören abgelehnte Prüfer-Vorschläge. Diese Liste geht
   später an jeden Prüfer mit, damit nichts erneut vorgeschlagen wird.

Gibt es seit dem Bezugspunkt keine Änderungen, sag das und brich ab.

## Schritt 2: Prüfer zuordnen

Zuordnung nach Art der Änderung (eine Datei kann mehrere Zeilen treffen):

| Änderung | Prüfer |
|---|---|
| Audio, Timing, Störungen: `core/audio.py`, `band.py`, `pause_noise.py`, `latency.py`, `tempo.py`, `sfx.py`, `mp3.py`, `net/stream.py` | performance, code |
| Datenhaltung und Statistik: `core/db.py`, `stats.py`, `storage.py`, `migration.py`, `backup.py`, `review.py`, `weighting.py` | test, code, bei Mengen-/Laufzeitfragen performance |
| Lernlogik: `core/koch.py`, `practice.py`, `daily.py`, `week.py`, `awards.py`, `lifeline.py`, `modes/*` | didaktik, test, teilnehmer |
| CW-Inhalte: `core/morse.py`, `words.py`, `qso_text.py`, `woerter.txt`, Rufzeichen-, Contest-, Q-Gruppen-Material, `modes/content.py`, `qso_*`, `callsign_mode.py` | fachinhalt, bei Lernwirkung didaktik |
| Oberfläche: `widgets/*`, `app.py`, `i18n*.py`, Dialoge, Reiter, Menüs, Tastenkürzel | usability, barrierefreiheit, teilnehmer |
| Sprachausgabe: `core/speech.py`, `widgets/announcer.py`, `voices/` | barrierefreiheit, plattform |
| Netzwerk: `net/*`, `modes/network_mode.py` | code, test, bei Durchsatz performance |
| Installation und Verpackung: `requirements.txt`, `packaging/*`, `net/update.py`, `widgets/updater.py`, Pfade, Start | plattform, code |
| Farben, Schrift, Kontrast, Vergrößerung: `widgets/theme.py` | barrierefreiheit, usability |
| Fehlerbehandlung allgemein, größere Umbauten, unerklärliche Abstürze | code |
| Bedienung, Texte, Tasten, Installation oder Funktionen geändert | technical-writer (immer zuletzt) |
| Nur Doku geändert | technical-writer, sonst niemand |
| Nur Tests geändert | test |

Die Prüfer heißen als `subagent_type`: `cw-code-pruefer`,
`cw-test-pruefer`, `cw-performance-pruefer`, `cw-plattform-pruefer`,
`cw-didaktik-pruefer`, `cw-teilnehmer-pruefer`, `cw-usability-pruefer`,
`cw-barrierefreiheits-pruefer`,
`cw-fachinhalts-pruefer`, `cw-technical-writer`.

Bei `klein`: nach Nutzen sortieren und auf höchstens drei kürzen. Vorrang
hat, wer Fehler findet, die Nutzer direkt treffen (Absturz, Datenverlust,
falsche Inhalte, unbedienbar), vor Stil- und Komfortfragen.

## Schritt 3: Einsatzplan in Wellen

Regeln für die Reihenfolge:

- **Welle 1:** rein lesende Prüfer (code, test, didaktik, teilnehmer,
  fachinhalt) parallel in einer Nachricht starten.
- **Welle 2:** Prüfer mit Messungen oder virtueller Anzeige (performance,
  plattform, usability, barrierefreiheit) höchstens zu zweit gleichzeitig, damit sie sich
  Messwerte und Rechenzeit nicht gegenseitig verfälschen. Sie dürfen parallel
  zu Welle 1 laufen, wenn höchstens zwei von ihnen dabei sind.
- **Letzte Welle:** `cw-technical-writer` allein und erst, wenn alle
  anderen fertig sind, weil er als Einziger Dateien ändert. Er bekommt die
  für die Doku relevanten Befunde der anderen mit.

Den Plan dem Nutzer als knappe Tabelle zeigen: Welle, Prüfer, Auftrag in
einem Satz, Grund für die Auswahl. Darunter, wer bewusst *nicht* eingesetzt
wird und warum. Dann mit AskUserQuestion freigeben lassen (Optionen etwa:
„Plan so starten“, „Nur Welle 1“, „Kürzen“). Ohne Freigabe keinen Prüfer
starten.

## Schritt 4: Aufträge erteilen

Jeder Prüfer startet ohne Gesprächskontext. Der Auftrag muss deshalb für
sich allein verständlich sein und enthält:

1. Bezugspunkt und Liste der geänderten Dateien, die *diesen* Prüfer
   betreffen, mit ein, zwei Sätzen, was sich fachlich geändert hat.
2. Den Schwerpunkt: welche Frage er beantworten soll. Kein pauschales
   „prüf alles“.
3. Die Liste der getroffenen Entscheidungen und abgelehnten Vorschläge aus
   Schritt 1 mit der Bitte, sie nicht erneut vorzuschlagen.
4. Grenzen: nichts committen; volle Testsuite nicht ausführen, nur
   betroffene Testmodule; nie echte Nutzerdaten; `callsigns.scp`,
   `docs/bilder/Silo.jpg` und `Plan-Offen.md` nicht anfassen.
5. Berichtsform: Befunde mit Schwere (kritisch / hoch / mittel / niedrig),
   Fundstelle `datei:zeile`, Beleg und Vorschlag; am Ende eine Zeile
   „Freigabe aus Sicht dieses Prüfers: ja / mit Vorbehalt / nein“.

Prüfer laufen im Hintergrund. Während sie laufen, keine Ergebnisse vorweg
nehmen; wenn der Nutzer fragt, sagen, wer noch läuft.

## Schritt 5: Lagebericht

Wenn alle Berichte da sind:

1. **Entdoppeln:** gleiche Ursache an derselben Stelle nur einmal, mit
   Nennung aller Prüfer, die sie gefunden haben (mehrfach gefunden = höheres
   Gewicht).
2. **Widersprüche abgleichen:** wenn Prüfer Gegensätzliches empfehlen (z. B.
   Didaktik gegen Usability), beide Seiten kurz darstellen und eine
   Empfehlung geben.
3. **Gegen Entscheidungen prüfen:** Befunde, die einer getroffenen
   Entscheidung widersprechen, nicht als offen führen, sondern in einer
   eigenen kurzen Zeile „bewusst entschieden, erneut vorgeschlagen von …“.
4. **Stichproben:** kritische und hohe Befunde selbst am Code nachprüfen,
   bevor sie in den Bericht kommen. Was sich nicht bestätigt, als
   „nicht bestätigt“ kennzeichnen.
5. **Ordnen** nach Schwere, dann nach Aufwand.

Aufbau des Lageberichts (Deutsch, knapp):

- Kopf: Bezugspunkt, Stufe, eingesetzte Prüfer, Gesamturteil
  („releasefähig“ / „releasefähig nach Punkt X“ / „nicht releasefähig“).
- Vor dem Release nötig: kritisch und hoch, je mit Fundstelle und Vorschlag.
- Kann warten: mittel und niedrig, kurz.
- Ideen und Vorschläge (z. B. neue Lernmethoden), getrennt von Fehlern.
- Was der Technical-Writer geändert hat, falls eingesetzt.
- Bewusst entschiedene Punkte, die erneut aufkamen.

Danach anbieten, die offenen Punkte in `Plan-Offen.md` einzutragen. Erst nach
ausdrücklicher Freigabe eintragen. Kein Commit, kein Release, keine
Codeänderung im Rahmen der Einsatzleitung; Korrekturen sind ein eigener
Auftrag des Nutzers.
