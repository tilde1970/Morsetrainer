"""Englische Texte zu i18n.tr(): deutscher Text -> englischer Text.

Nach Dateien gegliedert. Platzhalter ({name}) und Datumsformate (%d …)
müssen erhalten bleiben; tests/test_i18n.py prüft das und dass zu jedem
markierten Text ein Eintrag existiert."""

EN = {}

# --- app.py ---
EN.update({
    "Morsetrainer von {author}": "Morse trainer by {author}",
    "Zeichen": "Characters",
    "Farnsworth, effektiv": "Farnsworth, effective",
    "Koch-Tempo {wpm}/{effective}": "Koch speed {wpm}/{effective}",
    "Schwache Zeichen bevorzugen (gilt ab nächstem Start)": "Favour weak characters (from the next start)",
    "Tonhöhe und Tempo leicht variieren (gegen Gewöhnung an einen Klang)":
        "Vary pitch and speed slightly (so you don't get used to one sound)",
    "wirkt nach Neustart des Programms": "takes effect after restarting the program",
    "{wpm} WPM ≈ {cpm} ZpM": "{wpm} WPM ≈ {cpm} CPM",
    "WPM ≈ {cpm} ZpM": "WPM ≈ {cpm} CPM",
    "{wpm} (alle außer Einzelzeichen)": "{wpm} (all tabs except Characters)",
    "▾ Weitere Optionen": "▾ More options",
    "▸ Weitere Optionen": "▸ More options",
    "Farnsworth {wpm}": "Farnsworth {wpm}",
    "schwache bevorzugt": "weak favoured",
    "variiert": "varied",
    "Koch-Lektion": "Koch lesson",
    "▶ anhören": "▶ listen",
    "(eigene Zeichen)": "(own characters)",
    "↩ Lektion {lesson}": "↩ Lesson {lesson}",
    "neu: {char}": "new: {char}",
    "Tonausgabe": "Audio output",
    "Nächste Koch-Lektion": "Next Koch lesson",
    "Lektion {lesson} geschafft: {correct} von {total} Zeichen richtig ({share:.0%}).":
        "Lesson {lesson} passed: {correct} of {total} characters correct ({share:.0%}).",
    "Mit Lektion {next} weitermachen? Neu dazu kommt „{char}“.":
        "Continue with lesson {next}? New character: “{char}”.",
    "Du kennst jetzt alle Zeichen. Mit der Abschlusslektion {next} weitermachen? Dort ist kein Zeichen mehr "
    "neu, alle kommen gleichmäßig (schwache weiter öfter). Die Betriebszeichen AR, KN, SK und BK kannst du "
    "danach in den Lektionen {first}–{last} dazunehmen.":
        "You now know all characters. Continue with the final lesson {next}? No character is new there, all "
        "come evenly (weak ones still more often). You can add the prosigns AR, KN, SK and BK afterwards in "
        "lessons {first}–{last}.",
    "alle Zeichen, keins bevorzugt": "all characters, none favoured",
    "Weiter mit Gruppen": "Continue with groups",
    "Die Zeichen von Lektion {lesson} sitzen: {correct} von {total} richtig ({share:.0%}), "
    "mit Zeitlimit.\n\n"
    "Im Reiter Gruppen kommen sie ohne Pause hintereinander, wie im Funkbetrieb. "
    "Dort wird dir auch die nächste Lektion angeboten.\n\n"
    "Zum Reiter Gruppen wechseln?":
        "You know the characters of lesson {lesson}: {correct} of {total} correct ({share:.0%}), "
        "with time limit.\n\n"
        "In the Groups tab they come back to back without a pause, as on the air. "
        "That is also where the next lesson is offered.\n\n"
        "Switch to the Groups tab?",
    "Hilfe": "Help",
    "Morsetrainer {version} · entwickelt von {author} · 73!": "Morsetrainer {version} · developed by {author} · 73!",
    "Heute {minutes} von {goal} Min": "Today {minutes} of {goal} min",
    "Heute {minutes} Min": "Today {minutes} min",
    "Statistik": "Statistics",
    "Gesamtstatistik (alle Durchgänge)": "Overall statistics (all sessions)",
    "Tagesziel": "Daily goal",
    "Min. pro Tag": "min per day",
    "0 = ohne Ziel. Lieber täglich kurz als selten lang.": "0 = no goal. Short and daily beats long and rare.",
    "Wiederholung über Tage (Lernkartei)": "Review over days (spaced repetition)",
    "Sicher und flüssig erkannte Zeichen kommen nach 1, 2, 4, 8, 16 und 32 Tagen wieder, "
    "unsichere schon am nächsten Tag. Mit „schwache bevorzugt“ kommen fällige Zeichen öfter "
    "dran. Hochgestuft wird nur aus Zufallszeichen (Einzelzeichen, Gruppen, Kontinuierlich), "
    "entschieden einmal am Tag ab 5 Versuchen.":
        "Characters recognised reliably and quickly come back after 1, 2, 4, 8, 16 and 32 days, "
        "uncertain ones the next day. With “weak favoured” due characters come up more often. "
        "Only random characters promote a character (tabs Characters, Groups, Continuous); "
        "decided once a day from 5 attempts.",
    "Fällige gezielt üben": "Practise due characters",
    "Häufigste Verwechslungen (letzte {days} Tage)": "Most frequent confusions (last {days} days)",
    "Gesendet → getippt. Paare, die in beide Richtungen auftauchen (↔), sind "
    "typische Klangverwandte – am besten gezielt zusammen üben.":
        "Sent → typed. Pairs that occur in both directions (↔) are typical "
        "sound-alikes – best practised together.",
    "Die {n} häufigsten gezielt üben": "Practise the {n} most frequent",
    "Gesamtstatistik zurücksetzen": "Reset overall statistics",
    "Heute fällig ({n}): ": "Due today ({n}): ",
    "Noch nichts in der Lernkartei – sie füllt sich mit jedem Durchgang.":
        "Nothing in the review box yet – it fills up with every session.",
    "morgen": "tomorrow",
    "am {date}": "on {date}",
    "%d.%m.": "%b %d",
    "Heute ist nichts fällig. Als Nächstes {when}: ": "Nothing due today. Next {when}: ",
    "Keine Verwechslungen in den letzten {days} Tagen.": "No confusions in the last {days} days.",
    "{sent} {arrow} {typed}   {count:>3}×   ({share:.0%} der {sent})":
        "{sent} {arrow} {typed}   {count:>3}×   ({share:.0%} of {sent})",
    "Noch zu wenige Verwechslungen zum gezielten Üben.": "Not enough confusions yet for targeted practice.",
    "Die komplette Gesamtstatistik (alle bisherigen Durchgänge) wirklich löschen?\n"
    "Das kann nicht rückgängig gemacht werden. Die einzelnen Sitzungs-Logdateien "
    "in stats/ bleiben davon unberührt.":
        "Really delete the complete overall statistics (all previous sessions)?\n"
        "This cannot be undone. The individual session log files in stats/ are not affected.",
    "Einzelzeichen": "Characters",  # Reitername, kurz wie die übrigen
    "Gruppen": "Groups",
    "Wörter": "Words",
    "Rufzeichen": "Callsigns",
    "Kontinuierlich": "Continuous",
    "Sprechen": "Speak",
    "QSO": "QSO",
    "Contest": "Contest",
})

# --- core/ ---
EN.update({
    "Keine Tonausgabe möglich: {error}": "No audio output possible: {error}",
    "<{prosign}> · Taste {key}": "<{prosign}> · key {key}",
    "MP3-Export nicht verfügbar: lameenc ist nicht installiert (pip install lameenc).":
        "MP3 export not available: lameenc is not installed (pip install lameenc).",
    "{path} lässt sich nicht schreiben: {error}": "Cannot write {path}: {error}",
    "Sprachausgabe nicht verfügbar: Piper ist nicht installiert (pip install piper-tts).":
        "Speech output not available: Piper is not installed (pip install piper-tts).",
    "Sprachausgabe nicht verfügbar: Stimme {voice} fehlt (packaging/get_voice.sh lädt sie nach {folder}).":
        "Speech output not available: voice {voice} is missing (packaging/get_voice.sh downloads it to {folder}).",
    "Sprachausgabe nicht verfügbar: {error}": "Speech output not available: {error}",
    "Rufz-Durchgang": "RufZ run",
    "QSO mittippen": "QSO typing along",
    "QSO-Abfrage": "QSO log check",
    "QSO-Kopfhören": "QSO head copy",
    "Contest (aktiv)": "Contest (running)",
    # QSO-Arten und Abfrage (qso_text.py)
    "Normales QSO": "Normal QSO",
    "Contest: CQ WW (Zone)": "Contest: CQ WW (zone)",
    "Contest: CQ WPX (Nummer)": "Contest: CQ WPX (serial)",
    "Contest: WAG (DOK)": "Contest: WAG (DOK)",
    "Contest: ARRL DX (Staat/Leistung)": "Contest: ARRL DX (state/power)",
    "Contest: IARU HF (ITU-Zone/HQ)": "Contest: IARU HF (ITU zone/HQ)",
    "der CQ-Station": "of the CQ station",
    "die CQ-Station": "the CQ station",
    "der antwortenden Station": "of the answering station",
    "die antwortende Station": "the answering station",
    "Rufzeichen {of}": "Callsign {of}",
    "Name {of}": "Name {of}",
    "QTH {of}": "QTH {of}",
    "Rapport, den {subject} gab": "Report given by {subject}",
    "Rig {of}": "Rig {of}",
    "Leistung {of}": "Power {of}",
    "Wetter {of}": "Weather {of}",
    "Antenne {of}": "Antenna {of}",
    "Alter des OPs {of}": "Age of the operator {of}",
    "Lizenzjahr des OPs {of}": "Year licensed, operator {of}",
    "Station 1 (CQ)": "Station 1 (CQ)",
    "Station 2": "Station 2",
    "Name": "Name",
    "QTH": "QTH",
    "Rapport (gibt)": "Report (gives)",
    "Run-Station": "Run station",
    "Rufzeichen der Run-Station": "Callsign of the run station",
    "Wie viele QSOs hat die Run-Station geloggt?": "How many QSOs did the run station log?",
    "Austausch von {call}": "Exchange of {call}",
    "Austausch": "Exchange",
})

# --- daily_runner.py, widgets/daily_panel.py (Tagesübung) ---
EN.update({
    "▶ Tagesübung ({minutes} Min)": "▶ Daily practice ({minutes} min)",
    "Mo": "Mon", "Di": "Tue", "Mi": "Wed", "Do": "Thu", "Fr": "Fri", "Sa": "Sat", "So": "Sun",
    "Wochenziel erreicht: {stars} {star}": "Weekly goal reached: {stars} {star}",
    "{stars} von {goal} {star} diese Woche": "{stars} of {goal} {star} this week",
    "1 Tag": "1 day",
    "{n} Tage": "{n} days",
    "Letzte Woche: {days}, {stars} {star}": "Last week: {days}, {stars} {star}",
    "Lektion {a} → {b}": "lesson {a} → {b}",
    "Lektion {a} → Koch geschafft": "lesson {a} → Koch completed",
    "Tagesübung": "Daily practice",
    "{elapsed} von {total} Min": "{elapsed} of {total} min",
    "Aufwärmen": "Warm-up",
    "Hauptteil": "Main part",
    "Ausklang": "Wind-down",
    "Tagesübung geschafft.": "Daily practice done.",
    "Tagesübung abgebrochen – deine Sterne bleiben.": "Daily practice stopped – you keep your stars.",
    "Zugabe": "Encore",
    "Dabei": "Showed up",
    "Sauber": "Clean",
    "Weiter": "Ahead",
    "{n} fällige Zeichen geübt, {sure} davon heute sicher": "{n} due characters practised, {sure} of them solid today",
    "{mode}: {correct} von {total} Zeichen beim ersten Versuch ({share} %)":
        "{mode}: {correct} of {total} characters on the first try ({share} %)",
    "{correct} von {total} Zeichen richtig ({share} %)": "{correct} of {total} characters right ({share} %)",
    "Beste Serie: {n} Zeichen in Folge beim ersten Hören": "Best streak: {n} characters in a row on first hearing",
    "Beste Serie: {n} in Folge fehlerfrei": "Best streak: {n} in a row without a mistake",
    "{char} sitzt jetzt: {now} s (letzte Woche {before} s)": "{char} is sinking in: {now} s (last week {before} s)",
    "alle Zeichen": "all characters",
    "Lektion {lesson}": "lesson {lesson}",
    "Jetzt: {mode}, {what}, {tempo}": "Next: {mode}, {what}, {tempo}",
    "Gruppen bei {wpm} WPM: {before} % → {now} % beim ersten Versuch":
        "Groups at {wpm} WPM: {before} % → {now} % on the first try",
    "{char} kommt schneller: {before} s → {now} s": "{char} comes faster: {before} s → {now} s",
    "Ab morgen Lektion {lesson} – geschafft!": "Lesson {lesson} from tomorrow – well done!",
    "Koch geschafft – ab morgen übst du mit allen Zeichen weiter!":
        "Koch completed – from tomorrow you go on practising with all characters!",
    "Noch {missing} % beim ersten Versuch bis zum Koch-Abschluss":
        "{missing} % more on the first try to complete Koch",
    "Noch {missing} % beim ersten Versuch bis Lektion {lesson}":
        "{missing} % more on the first try to reach lesson {lesson}",
    "Verwechslungen {chars}": "confusions {chars}",
    "Noch {minutes} Min: {what}": "{minutes} more min: {what}",
    "Weiter ▶": "Continue ▶",
    "Enter geht weiter, Esc beendet die Tagesübung": "Enter continues, Esc ends the daily practice",
    "Besser geworden (gegenüber der Vorwoche)": "Improved (compared with the week before)",
    "Stand gehalten.": "Held steady.",
    "Für einen Vergleich mit der Vorwoche fehlen noch Daten.": "Not enough data yet to compare with last week.",
    "Fast geschafft": "Almost there",
    "Fertig": "Done",
    "Neues Zeichen: {char}": "New character: {char}",
    "Neu: {stars}": "New: {stars}",
    "{block} geschafft": "{block} done",
    "Zugabe geschafft.": "Encore done.",
    "Zugabe beendet.": "Encore stopped.",
})

# --- widgets/ ---
EN.update({
    "Änderungen": "Changes",
    "Anleitung": "Manual",
    "Morsetrainer – Hilfe": "Morsetrainer – Help",
    "Schließen": "Close",
    "{name} wurde nicht gefunden.": "{name} was not found.",
    "Fortschritt": "Progress",
    "Lebenslinie": "Lifeline",
    "Sterne gesamt": "Total stars",
    "Tagestempo effektiv (WPM)": "Daily speed, effective (WPM)",
    "Sterne gibt es in der Tagesübung.": "Stars are earned in daily practice.",
    "Noch keine Koch-Lektion geübt.": "No Koch lesson practised yet.",
    "Das Tagestempo kommt mit der ersten Tagesübung.": "The daily speed starts with your first daily practice.",
    "Die Lebenslinie beginnt mit dem ersten Üben.": "The lifeline starts with your first practice.",
    "Seit {date}: {parts}": "Since {date}: {parts}",
    "Lektion {n}": "lesson {n}",
    "Koch geschafft": "Koch completed",
    "1 Siegel": "1 seal",
    "{n} Siegel": "{n} seals",
    "Jan": "Jan",
    "Feb": "Feb",
    "Mär": "Mar",
    "Apr": "Apr",
    "Mai": "May",
    "Jun": "Jun",
    "Jul": "Jul",
    "Aug": "Aug",
    "Sep": "Sep",
    "Okt": "Oct",
    "Nov": "Nov",
    "Dez": "Dec",
    "Modus:": "Mode:",
    "Tabelle": "Table",
    "Diagramm": "Chart",
    "Trefferquote (%)": "Accuracy (%)",
    "Tempo effektiv (WPM)": "Effective speed (WPM)",
    "Zeitpunkt": "Time",
    "Trefferquote": "Accuracy",
    "Tempo eff. (WPM)": "Eff. speed (WPM)",
    "Umfang": "Count",
    "Noch keine Daten für diesen Modus.": "No data for this mode yet.",
    "Noch keine abgeschlossenen Durchgänge.": "No completed sessions yet.",
    "%d.%m. %H:%M": "%b %d %H:%M",
    "%d.%m.%Y": "%Y-%m-%d",
    "%d.%m.%Y %H:%M": "%Y-%m-%d %H:%M",
    "{n} Durchgänge seit {date} · Trefferquote {first:g} % → {last:g} %, Tempo {wpm_first} → {wpm_last} WPM":
        "{n} sessions since {date} · accuracy {first:g} % → {last:g} %, speed {wpm_first} → {wpm_last} WPM",
    " · Punkte zuletzt {last}, bester {best}": " · score last {last}, best {best}",
    "Statistik (aktueller Durchgang)": "Statistics (current session)",
    "Ø effektive Geschwindigkeit: –": "Ø effective speed: –",
    "Ø effektive Geschwindigkeit: {wpm:.1f} WPM": "Ø effective speed: {wpm:.1f} WPM",
    " · {cpm:.0f} ZpM gemessen": " · {cpm:.0f} CPM measured",
    "Zeichen, nach Fehlern sortiert": "Characters, sorted by errors",
    "Spalte|Zeichen": "Char.",
    "Richtig": "Correct",
    "Falsch": "Wrong",
    "Ø Zeit (s)": "Ø time (s)",
    "Ø WPM": "Ø WPM",
    "Verwechselt mit": "Confused with",
    "Protokoll nicht gespeichert: {error}": "Log not saved: {error}",
    "Gespeichert: {path}": "Saved: {path}",
    "Bandbedingungen": "Band conditions",
    "Rauschen": "Noise",
    "Knackstörungen (QRN)": "Static crashes (QRN)",
    "QSB (Fading)": "QSB (fading)",
    "Chirp": "Chirp",
    "SSB-Gebrabbel": "SSB babble",
    "CW-QRM (Nachbar-Run)": "CW QRM (adjacent run)",
    "Alle aus": "All off",
    "Alle an": "All on",
})

# --- modes/qso_mode.py, modes/qso_quiz.py ---
EN.update({
    "Mitschreiben + Abfrage": "Copy + log check",
    "Fortlaufend mittippen": "Type along",
    "Kopfhören + Fragen": "Head copy + questions",
    "Nur hören": "Listen only",
    "aus": "off",
    "selten": "rare",
    "oft": "often",
    "Kurz": "Short",
    "Normal": "Normal",
    "Lang": "Long",
    "Hör einem kompletten CW-QSO oder einem Contest-Run zu. Jede Station hat eine eigene Tonhöhe. "
    "„=“ ist BT (Trennung), „+“ ist AR (Ende des Durchgangs); <SK>, <KN> und <BK> werden "
    "zusammengezogen gesendet und beim Mittippen nicht gezählt. Der Zeichensatz oben gilt hier nicht.":
        "Listen to a complete CW QSO or a contest run. Each station has its own pitch. "
        "“=” is BT (separator), “+” is AR (end of transmission); <SK>, <KN> and <BK> are sent "
        "run together and not counted when typing along. The character set above does not apply here.",
    "Neues QSO (F5)": "New QSO (F5)",
    "Nochmal (F6)": "Again (F6)",
    "Text zeigen (F7)": "Show text (F7)",
    "Text verbergen (F7)": "Hide text (F7)",
    "Bereit. Drücke „Neues QSO“.": "Ready. Press “New QSO”.",
    "Notizen (frei, werden nicht ausgewertet)": "Notes (free, not evaluated)",
    "Deine Eingabe (letzte Zeichen)": "Your input (last characters)",
    "QSO-Text": "QSO text",
    "Art:": "Type:",
    "Auswertung:": "Evaluation:",
    "Länge:": "Length:",
    "(im Contest rufen weitere Stationen gleichzeitig)": "(in contests, more stations call at the same time)",
    "Tempo automatisch anpassen (nach Abfrage/Mittippen, ändert das Tempo oben)":
        "Adjust speed automatically (after log check/typing along, changes the speed above)",
    "ca. {minutes} Min. bei {tempo}": "about {minutes} min at {tempo}",
    "Ungültige Geschwindigkeit oder Tonhöhe!": "Invalid speed or pitch!",
    "Antwort (wie gesendet)": "Answer (as sent)",
    "Erst die Fragen beantworten und prüfen – dann „Nochmal“.": "Answer and check the questions first – then “Again”.",
    "Stop (F5)": "Stop (F5)",
    "Wiederholung – ": "Replay – ",
    "Durchgang {n} von {total}": "Transmission {n} of {total}",
    "QSO zu Ende – tippe die letzten Zeichen noch ein…": "QSO finished – type the last characters…",
    "Ausgewertet – rot markiert: falsch oder verpasst.": "Evaluated – marked red: wrong or missed.",
    "Beantworte die Fragen und drück „Prüfen“.": "Answer the questions and press “Check”.",
    "Ergänze dein Log und drück „Prüfen“.": "Complete your log and press “Check”.",
    "Trag ein, was du gehört hast, und drück „Prüfen“.": "Enter what you heard and press “Check”.",
    "QSO beendet.": "QSO finished.",
    "Gestoppt. ": "Stopped. ",
    "   (gleichzeitig: {calls})": "   (at the same time: {calls})",
    " (vorher einmal „Nochmal“ – Tempo bleibt)": " (“Again” used once before – speed unchanged)",
    " (vorher {n}× „Nochmal“ – Tempo bleibt)": " (“Again” used {n}× before – speed unchanged)",
    "Abfrage ausgewertet.": "Log checked.",
    " Tempo bleibt bei {tempo}.": " Speed stays at {tempo}.",
    " Tempo: {before} → {after}.": " Speed: {before} → {after}.",
    "Abfrage – was hast du mitbekommen?": "Check – what did you copy?",
    "Prüfen (F8)": "Check (F8)",
    "{correct} / {total} richtig": "{correct} / {total} correct",
    "Richtig wäre: ": "Correct would be: ",
})

# Bedeutungen der eingebauten Wörter und Wendungen (core/words.py), nach
# dem Wort statt nach der deutschen Bedeutung: dieselbe deutsche Bedeutung
# kann je Wort anders heißen. Angezeigt über words.shown_meaning().
MEANINGS = {
    # Q-Gruppen
    "QRG": "frequency", "QRL": "busy / is the frequency in use? (also: work)", "QRM": "interference from other stations",
    "QRN": "atmospheric noise", "QRO": "high power", "QRP": "low power",
    "QRQ": "send faster", "QRS": "send slower", "QRT": "closing down",
    "QRU": "nothing more for you", "QRV": "ready", "QRX": "please wait",
    "QRZ": "who is calling?", "QSB": "fading", "QSK": "full break-in (listening between characters)",
    "QSL": "confirmation", "QSO": "contact", "QSY": "change of frequency",
    "QTH": "location", "QTR": "time",
    # Abkürzungen
    "ABT": "about", "AGN": "again", "ANT": "antenna",
    "BK": "break – over to you", "CFM": "confirm", "CL": "closing the station",
    "CPY": "copy", "CQ": "general call", "CUAGN": "see you again",
    "CUL": "see you later", "DE": "from", "DR": "dear",
    "ES": "and", "FB": "fine business – great", "FER": "for", "GA": "good afternoon / go ahead",
    "GB": "goodbye", "GD": "good day", "GE": "good evening", "GL": "good luck",
    "GM": "good morning", "GN": "good night", "HI": "laughter", "HR": "here",
    "HW": "how (copy)?", "MNI": "many", "NR": "number / near",
    "NW": "now", "OM": "old man – fellow ham", "OP": "operator",
    "PSE": "please", "PWR": "power", "RIG": "radio",
    "RPT": "repeat/report", "RST": "report (readability, strength, tone)",
    "SIG": "signal", "SRI": "sorry", "TEMP": "temperature",
    "TKS": "thanks", "TNX": "thanks", "TU": "thank you",
    "UR": "your/you are", "VY": "very", "WX": "weather",
    "XYL": "wife", "YL": "young lady – female operator", "73": "best regards",
    "88": "love and kisses", "5NN": "report 599 (cut numbers)", "599": "best report",
    "TEST": "contest call", "UP": "listening higher up in frequency", "NIL": "nothing",
    "RR": "roger – received", "RE": "regarding",
    # Wörter aus typischen QSOs
    "VERT": "vertical antenna",
    "KEY": "straight key", "BUG": "semi-automatic key", "PADDLE": "paddle",
    "MTR": "meter", "MTRS": "meters",
    "BURO": "QSL bureau", "LOTW": "Logbook of the World",
    "SWL": "shortwave listener", "RX": "receiver", "TX": "transmitter",
    "TRX": "transceiver",
    "PSED": "pleased", "QRPP": "very low power",
    "TMW": "tomorrow", "TDY": "today", "YR": "year",
    "BCNU": "be seeing you", "ENUF": "enough", "WKD": "worked",
    "WL": "well/will", "WPM": "words per minute",
    "DX": "long distance – distant station", "CU": "see you", "RPRT": "report",
    "GUD": "good", "HPE": "hope", "CONDX": "propagation conditions",
    "SKED": "schedule – arranged contact", "OT": "old timer", "OB": "old boy – fellow ham (like OM)",
    "UFB": "ultra fine business – excellent", "DOK": "German district/local club code",
    "SIGS": "signals", "HVY": "heavy (e.g. HVY QRM)", "WID": "with", "FM": "from (also the mode FM)",
    "HV": "have", "BTW": "by the way",
    "SN": "soon", "BN": "been", "OPR": "operator", "HNY": "happy new year",
    "WKG": "working", "CONDS": "propagation conditions",
    "R": "roger – received", "K": "over – go ahead",
    "(": "KN – only the called station may reply", "*": "SK – end of contact",
    # Wendungen
    "CQ CQ DE": "general call from …", "PSE K": "please go ahead", "PSE (": "please go ahead, only you",
    "TNX FER CALL": "thanks for the call", "TNX FER QSO": "thanks for the contact",
    "TNX FER RPRT": "thanks for the report", "UR RST 599": "your report 599", "UR RST IS 579": "your report is 579",
    "UR 5NN": "your report 599", "NAME HR IS": "my name is", "MY NAME IS": "my name is",
    "QTH HR IS": "my location is", "MY QTH IS": "my location is", "HW CPY": "how do you copy?",
    "HW CPY OM": "how do you copy, OM?", "SOLID CPY": "copied everything", "FB OM": "great, OM",
    "R R TNX": "received, thanks", "ALL OK": "copied everything", "PSE AGN": "please repeat",
    "PSE RPT UR NAME": "please repeat your name", "QRZ": "who is calling?", "AGN PSE": "again please",
    "RIG HR IS": "my radio is", "PWR IS 100W": "power 100 watts", "ANT IS DIPOLE": "the antenna is a dipole",
    "WX HR SUNNY": "sunny here", "WX IS CLOUDY": "weather cloudy", "TEMP IS 20C": "temperature 20 degrees",
    "GUD DX": "good luck with DX", "73 ES GL": "best regards and good luck",
    "73 ES CUAGN": "best regards, see you again", "CUL 73": "see you later, best regards", "TU 73": "thanks, best regards",
    "GM OM": "good morning, OM", "GA OM": "good afternoon, OM", "GE OM": "good evening, OM",
    "GL ES 73": "good luck and best regards", "HPE CUAGN": "hope to see you again", "VY 73": "very best regards",
    "QSL VIA BURO": "QSL via the bureau", "QSL VIA LOTW": "QSL via LoTW", "# TU": "over, thanks",
    "TNX ES 73": "thanks and best regards", "5NN TU": "599, thanks", "TU UP": "thanks, listening up",
    "QRL?": "is the frequency in use?", "QSY UP": "moving up", "QRS PSE": "please send slower", "QRQ": "faster",
    "UR SIGS FB": "your signals are great", "HVY QRM": "heavy interference", "HVY QSB": "heavy fading",
    "CONDX NOT GUD": "conditions not good", "TNX FER NICE QSO": "thanks for the nice QSO",
    "SRI QRM": "sorry, interference", "DR OM": "dear OM", "HR QRU": "nothing more here",
    "RR TU": "received, thanks", "TNX QSO": "thanks for the contact", "GM ES TNX": "good morning and thanks",
    "73 TU EE": "best regards, thanks (dit dit)", "TU 73 *": "thanks, best regards, end", "OP HR IS": "operator here is",
    "UR NAME?": "your name?", "PSE QSL": "please confirm",
}

# --- modes/sequence_mode.py (Gruppen, Wörter, Rufzeichen) ---
EN.update({
    "Einstellungen": "Settings",
    "Eingabe:": "Input:",
    "Mitschreiben": "Copy while listening",
    "Erst merken": "Listen first",
    "Kopfhören": "Head copy",
    "Lösung zeigen nach": "Show solution after",
    "Fehlversuchen": "failed attempts",
    "Tempo wächst mit (richtig +{step}, falsch −{step} WPM)": "Speed adapts (correct +{step}, wrong −{step} WPM)",
    "Bandbedingungen:": "Band conditions:",
    "leicht": "light",
    "mittel": "medium",
    "stark": "heavy",
    "(Rauschen, QSB, Knacken, QRM)": "(noise, QSB, static, QRM)",
    "Störgeräusche:": "Noise level:",
    "leiser": "quieter",
    "lauter": "louder",
    "Dauer:": "Duration:",
    "Min.": "min",
    "(0 = ohne Limit)": "(0 = no limit)",
    "Quittungston": "Feedback beep",
    "Start": "Start",
    "Stop": "Stop",
    "Wiederholen (Leertaste)": "Repeat (space bar)",
    "Bereit. Drücke Start.": "Ready. Press Start.",
    "Enter bestätigt": "Enter confirms",
    "Nach dem letzten Zeichen automatisch fertig, sonst Enter":
        "Done automatically after the last character, otherwise Enter",
    "Auflösen (Enter)": "Reveal (Enter)",
    "Gewusst (J)": "Knew it (J)",
    "Nicht gewusst (N)": "Didn't know (N)",
    "Verlauf": "History",
    "Ungültige Dauer, Geschwindigkeit oder Tonhöhe!": "Invalid duration, speed or pitch!",
    "Ungültige Dauer!": "Invalid duration!",
    "Achtung: {text}": "Attention: {text}",
    "Gestoppt.": "Stopped.",
    "{wpm} WPM effektiv": "{wpm} WPM effective",
    "Bestwert {best}, zuletzt {tempo}": "best {best}, last {tempo}",
    "aktuell {tempo}": "now {tempo}",
    "Restzeit {time}": "Time left {time}",
    "Zeit abgelaufen – letzte Eingabe noch": "Time is up – last answer still counts",
    " – selbst bewertet, zählt nicht für Gesamtstatistik und Lektion":
        " – self-assessed, does not count for overall statistics and lesson",
    "Zeit abgelaufen – Durchgang ausgewertet.": "Time is up – session evaluated.",
    "Höre zu…": "Listen…",
    "Höre zu… (Wiederholung)": "Listen… (repeat)",
    "Gewusst? J oder N": "Knew it? J or N",
    "Erkannt? Enter löst auf.": "Recognised? Enter reveals.",
    "Deine Eingabe? (für die Lektion zügig: {limit} s)": "Your answer? (quick for the lesson: {limit} s)",
    "Deine Eingabe? (zügig: {limit} s)": "Your answer? (quick: {limit} s)",
    "Deine Eingabe?": "Your answer?",
    "Wird nach dem Ton ausgewertet…": "Evaluated after the tone…",
    "(zu langsam – keine Punkte)": "(too slow – no points)",
    "(zu langsam – Tempo steigt nicht)": "(too slow – speed does not go up)",
    "(zu langsam)": "(too slow)",
    "(zu langsam – zählt nicht für die Lektion)": "(too slow – does not count for the lesson)",
    "(mit Wiederholen – zählt nicht für die Lektion)": "(with repeat – does not count for the lesson)",
    "Richtig: {text}": "Correct: {text}",
    "Lösung: {text}": "Solution: {text}",
    "Leider falsch – hör noch einmal hin.": "Wrong – listen again.",
    "gesendet": "sent",
    "getippt": "typed",
    "– fehlt/zu viel, ^ falsch": "– missing/extra, ^ wrong",
    "Hör dir die Lösung noch einmal an…": "Listen to the solution again…",
})

# --- modes/group_mode.py ---
EN.update({
    "Gruppenlänge von": "Group length from",
    "bis": "to",
    "Länge wächst mit ({longer}× richtig: länger, {shorter} Fehler: kürzer)":
        "Length adapts ({longer}× correct: longer, {shorter} errors: shorter)",
    "Kein gültiges Zeichen im Zeichensatz!": "No valid character in the character set!",
    "Ungültige Gruppenlänge!": "Invalid group length!",
    "Gruppenlänge „von“ darf nicht größer als „bis“ sein!": "Group length “from” must not be greater than “to”!",
    " – länger, weiter so!": " – longer, keep it up!",
    " – etwas kürzer": " – a bit shorter",
    "Aktuelle Gruppenlänge: {length}": "Current group length: {length}",
})

# --- modes/word_mode.py ---
EN.update({
    "Es kommen CW-Abkürzungen, Q-Gruppen und Wörter aus QSOs – nur solche, die "
    "aus den Zeichen oben bestehen. Mit jeder Koch-Lektion werden es mehr.":
        "You get CW abbreviations, Q codes and words from QSOs – only those made of "
        "the characters above. Every Koch lesson adds more.",
    "Eigene Wörter bearbeiten": "Edit own words",
    "Mit dem aktuellen Zeichensatz: {count} von {total} Wörtern": "With the current character set: {count} of {total} words",
    " (davon {n} eigene)": " ({n} of them your own)",
    "Übersprungen in {file}: ": "Skipped in {file}: ",
    " und {n} weitere": " and {n} more",
    "{file} lässt sich nicht öffnen: {error}": "Cannot open {file}: {error}",
    " – genug gibt es ab Koch-Lektion {lesson}": " – there are enough from Koch lesson {lesson}",
    "Nur {count} Wörter mit diesen Zeichen": "Only {count} words with these characters",
    "Übe bis dahin im Reiter Gruppen.": "Until then, practise in the Groups tab.",
    "Neu: Wörter jetzt mit „Erst merken“ – erst das ganze Wort hören, "
    "dann tippen. Umstellbar unter Eingabe.":
        "New: words now use “Listen first” – hear the whole word first, "
        "then type. You can change this under Input.",
    "# Eigene Wörter für den Reiter „Wörter“ im Morsetrainer.\n"
    "#\n"
    "# Ein Wort pro Zeile, optional mit Bedeutung nach dem ersten „=“, die nach\n"
    "# der Antwort angezeigt wird. Zeilen mit # sind Kommentare. Groß- und\n"
    "# Kleinschreibung ist egal, Ä/Ö/Ü/ß werden zu AE/OE/UE/SS. Wörter mit\n"
    "# Leerzeichen oder Zeichen, die es nicht im Morsecode gibt, werden\n"
    "# übersprungen. Die Wörter kommen zu den eingebauten dazu; steht hier ein\n"
    "# eingebautes Wort mit Bedeutung, gilt deine Bedeutung.\n"
    "#\n"
    "# Nach dem Speichern den Durchgang neu starten.\n"
    "#\n"
    "# Beispiele:\n"
    "# DARC = Deutscher Amateur-Radio-Club\n"
    "# OV = Ortsverband\n"
    "# SOTA = Summits on the Air\n":
        "# Your own words for the “Words” tab in Morsetrainer.\n"
        "#\n"
        "# One word per line, optionally with a meaning after the first “=”, which\n"
        "# is shown after the answer. Lines starting with # are comments. Upper and\n"
        "# lower case do not matter, Ä/Ö/Ü/ß become AE/OE/UE/SS. Words with spaces\n"
        "# or characters that do not exist in Morse code are skipped. The words are\n"
        "# added to the built-in ones; if a built-in word with a meaning appears\n"
        "# here, your meaning is used.\n"
        "#\n"
        "# After saving, restart the session.\n"
        "#\n"
        "# Examples:\n"
        "# ARRL = American Radio Relay League\n"
        "# POTA = Parks on the Air\n"
        "# SOTA = Summits on the Air\n",
})

# --- modes/callsign_mode.py ---
EN.update({
    "Es werden echte Rufzeichen aus der Super-Check-Partial-Liste gesendet "
    "(aktive Contest-Stationen weltweit). Mit dem Präfix-Filter kannst du dich "
    "auf bestimmte Länder beschränken, z. B. „DL DK DJ DO“ (Textanfang: „G“ "
    "umfasst auch GM, GW …).":
        "Real callsigns from the Super Check Partial list are sent "
        "(active contest stations worldwide). With the prefix filter you can limit "
        "them to certain countries, e.g. “K W N” (start of text: “G” also covers GM, GW …).",
    "Präfix-Filter:": "Prefix filter:",
    "(leer = alle)": "(empty = all)",
    "Nur gelernte Zeichen (Zeichensatz oben)": "Only learned characters (character set above)",
    "Anhänge und Gast-Präfixe (/P, /M, OE/…, gelegentlich)": "Suffixes and guest prefixes (/P, /M, OE/…, occasionally)",
    "Rufz-Durchgang: {n} Rufzeichen, je ein Versuch, Punkte": "RufZ run: {n} callsigns, one attempt each, score",
    "▶ Verpasste nachhören (F6)": "▶ Replay missed (F6)",
    "▶ Verpasste nachhören ({n}, F6)": "▶ Replay missed ({n}, F6)",
    "Liste: {n} Rufzeichen": "List: {n} callsigns",
    "callsigns.scp nicht gefunden – es werden Rufzeichen nach Muster erzeugt.":
        "callsigns.scp not found – callsigns are generated from patterns.",
    "Bestwert {score} Punkte": "Best score {score} points",
    " (Start {tempo})": " (start {tempo})",
    "Nachhören beendet. F6 fängt von vorn an.": "Replay finished. F6 starts again.",
    "Nachhören angehalten. F6 fängt von vorn an.": "Replay stopped. F6 starts again.",
    " · ohne QRM/QRN": " · without QRM/QRN",
    "Verpasst {n}/{total} – hör hin…": "Missed {n}/{total} – listen…",
    "Verpasst {n}/{total}: {call}": "Missed {n}/{total}: {call}",
    " (zu langsam)": " (too slow)",
    " (du: {typed})": " (you: {typed})",
    " (nichts getippt)": " (nothing typed)",
    " · F6 nochmal, F7 von vorn, Esc Stopp": " · F6 again, F7 from the start, Esc stop",
    "Rufzeichen {n}/{total} · {score} Punkte": "Callsign {n}/{total} · {score} points",
    "Rufz: {score} Punkte, {correct} von {total} richtig": "RufZ: {score} points, {correct} of {total} correct",
    " – neuer Bestwert!": " – new best!",
    "Rufz abgebrochen nach {n} Rufzeichen ({score} Punkte, nicht gewertet).":
        "RufZ aborted after {n} callsigns ({score} points, not counted).",
    " · passend: {n}": " · matching: {n}",
    "Der Rufz-Durchgang braucht eine Eingabe – Mitschreiben oder Erst merken.":
        "The RufZ run needs typed input – Copy while listening or Listen first.",
    "Für Rufzeichen braucht der Zeichensatz Buchstaben und eine Ziffer.":
        "Callsigns need letters and a digit in the character set.",
    "Die erste Ziffer kommt mit Koch-Lektion {lesson}.": "The first digit comes with Koch lesson {lesson}.",
    "Weitere Lektionen lernen oder „Nur gelernte Zeichen“ ausschalten.":
        "Learn more lessons or switch off “Only learned characters”.",
    "Präfix-Filter erweitern.": "Widen the prefix filter.",
    "Nur {n} passende Rufzeichen.": "Only {n} matching callsigns.",
})

# --- modes/content.py, modes/continuous_mode.py ---
EN.update({
    "Zu wenige Wörter mit diesen Zeichen – erst im Reiter Gruppen üben.":
        "Too few words with these characters – practise in the Groups tab first.",
    "Zu wenige Wendungen mit diesen Zeichen": "Too few phrases with these characters",
    "Rufzeichen brauchen eine Ziffer im Zeichensatz (ab Koch-Lektion 23).":
        "Callsigns need a digit in the character set (from Koch lesson 23).",
    "Zu wenige Rufzeichen mit diesen Zeichen (callsigns.scp fehlt oder Zeichensatz zu klein).":
        "Too few callsigns with these characters (callsigns.scp missing or character set too small).",
    "QSO-Klartext braucht alle Buchstaben und Ziffern, es fehlen noch: {missing}":
        "QSO plain text needs all letters and digits, still missing: {missing}",
    "Zufallszeichen": "Random characters",
    "Wendungen": "Phrases",
    "QSO-Klartext": "QSO plain text",
    "Anzahl QSOs:": "Number of QSOs:",
    "Kontinuierlich (ohne Pause, feste Dauer)": "Continuous (no pauses, fixed duration)",
    "Die Gruppen kommen ohne Pause wie im Reiter „Kontinuierlich“, alle tippen fortlaufend mit, ohne "
    "Enter. Ausgewertet wird am Ende; eine Taste zählt nur, wenn sie zeitlich zum Zeichen passt. Die "
    "Lösungen stehen danach nummeriert unter „Auflösung“.":
        "The groups come without pauses as in the “Continuous” tab, everyone types along continuously, "
        "without Enter. Scoring happens at the end; a key only counts if it fits the character in time. "
        "Afterwards the solutions are listed by number under “Solutions”.",
    "Kontinuierlich geht nicht mit eigenem Text – Gruppen wählen.":
        "Continuous does not work with own text – choose groups.",
    "Kontinuierlich – noch {time}": "Continuous – {time} left",
    "Nachtippen…": "Finishing typing…",
    "Läuft – höre zu und tippe mit, ohne Enter…": "Running – listen and type along, without Enter…",
    "{correct} von {total} Gruppen richtig, {share:.0%} der Zeichen":
        "{correct} of {total} groups correct, {share:.0%} of the characters",
    "Der Ton läuft durch, ohne auf dich zu warten. Tippe mit, was du erkennst "
    "– auch wenn du mal hinterherhinkst. Auswertung erfolgt beim Stoppen. "
    "F5 startet und stoppt, Esc stoppt.":
        "The audio keeps running without waiting for you. Type what you recognise "
        "– even if you fall behind. Evaluation happens when you stop. "
        "F5 starts and stops, Esc stops.",
    "Inhalt:": "Content:",
    "(Klartext zählt nicht für die Lektion)": "(plain text does not count for the lesson)",
    "Gruppen zu": "Groups of",
    "Einheit|Zeichen": "characters",
    "(mit Wortpause dazwischen; 0 = durchgehend)": "(with a word gap in between; 0 = continuous)",
    "Auswertung (letzte Zeichen)": "Evaluation (last characters)",
    "Alles in eigenem Fenster": "Everything in a separate window",
    "Kontinuierlich – ganze Auswertung": "Continuous – full evaluation",
    "Nur gesendeter Text": "Sent text only",
    "Erscheint nach dem Stoppen.": "Appears after stopping.",
    "Gesendet: {n} Zeichen": "Sent: {n} characters",
    "Läuft – höre zu und tippe mit…": "Running – listen and type along…",
    " · vorläufige Trefferquote (letzte {n}): {pct:.0f}%": " · provisional accuracy (last {n}): {pct:.0f}%",
    " · vorläufige Trefferquote: {pct:.0f}%": " · provisional accuracy: {pct:.0f}%",
    "Zeit abgelaufen – tippe die letzten Zeichen noch ein…": "Time is up – type the last characters…",
    "Werte aus…": "Evaluating…",
    "– fehlt/zu viel, ^ falsch oder nicht rechtzeitig": "– missing/extra, ^ wrong or not in time",
})

# --- modes/single_mode.py ---
EN.update({
    "Zeitlimit (wird kürzer, solange du sicher bist)": "Time limit (gets shorter while you answer reliably)",
    "zurücksetzen": "reset",
    "Verlauf (letzte 40)": "History (last 40)",
    "So klingt {char} – und so {typed} (dein Tipp):": "This is {char} – and this is {typed} (your answer):",
    "So klingt {char}:": "This is {char}:",
    "Zu langsam: war {char}": "Too slow: it was {char}",
    "(Limit jetzt {limit} s)": "(limit now {limit} s)",
    "{char} – erst nach Wiederholung, kommt gleich noch mal": "{char} – only after a repeat, it will come again soon",
    ", Limit {limit} s": ", limit {limit} s",
    "Falsch: war {char}, du: {typed}": "Wrong: it was {char}, you: {typed}",
})

# --- modes/listen_mode.py ---
EN.update({
    "Ohne Tastatur üben: Du hörst das Morsezeichen und sagst in der Pause laut, was du "
    "erkannt hast. Dann sagt eine Stimme die Lösung an. Sprechen statt tippen trainiert "
    "das Klangbild – und geht auch beim Spazierengehen. Als MP3 gespeichert läuft die "
    "Übung auf Handy oder im Auto. F5 startet und stoppt, Leertaste wiederholt.":
        "Practise without a keyboard: you hear the Morse code and say out loud during the pause "
        "what you recognised. Then a voice announces the solution. Speaking instead of typing trains "
        "the sound pattern – and also works on a walk. Saved as MP3, the exercise runs on your phone "
        "or in the car. F5 starts and stops, space bar repeats. The voice is German.",
    "Anzahl:": "Count:",
    "Denkpause:": "Thinking pause:",
    "s (+0,3 s je Zeichen)": "s (+0.3 s per character)",
    "Ansage:": "Announcement:",
    "Buchstaben (A, Be, Ce)": "German letter names (A, Be, Ce)",
    "Buchstabieralphabet (Alfa, Bravo)": "Phonetic alphabet (Alfa, Bravo)",
    "Wörter und Wendungen als Ganzes ansagen": "Announce words and phrases as a whole",
    "Beim Buchstabieren mit Bedeutung": "Add the meaning when spelling",
    "Danach noch einmal morsen": "Send the Morse code again afterwards",
    "Als MP3 speichern…": "Save as MP3…",
    "Ungültige Anzahl, Pause, Geschwindigkeit oder Tonhöhe!": "Invalid count, pause, speed or pitch!",
    "Stimme wird geladen…": "Loading voice…",
    "Fertig: {n} Einträge.": "Done: {n} items.",
    "Hör zu …": "Listen …",
    "Sag es laut …": "Say it out loud …",
    "Lösung:": "Solution:",
    "Übung als MP3 speichern": "Save exercise as MP3",
    "Abbrechen": "Cancel",
    "MP3 wird erstellt …": "Creating MP3 …",
    "MP3 abgebrochen.": "MP3 cancelled.",
    "Gespeichert: {path} ({minutes:.0f} Min.)": "Saved: {path} ({minutes:.0f} min)",
})

# --- modes/run_mode.py ---
EN.update({
    "Mein Call": "My call",
    "Sein Call": "Their call",
    "Du bist die Run-Station: F1 ruft CQ, nimm ein Rufzeichen auf, gib mit Enter den "
    "Austausch, trag seinen Austausch ein und logge mit Enter (TU). "
    "Am Ende wird dein Log mit dem verglichen, was wirklich gesendet wurde.":
        "You are the running station: F1 calls CQ, copy a callsign, send the exchange with Enter, "
        "enter the caller's exchange and log with Enter (TU). "
        "At the end your log is compared with what was actually sent.",
    "Contest:": "Contest:",
    "Mein Rufzeichen:": "My callsign:",
    "Mein Austausch:": "My exchange:",
    "Aktivität:": "Activity:",
    "Anrufer gleichzeitig (ca.)": "simultaneous callers (approx.)",
    "Anrufer:": "Callers:",
    "Tempo ±": "Speed ±",
    "WPM, Tonhöhe ±": "WPM, pitch ±",
    "Wenig Tonhöhen-Streuung = dichtes Pile-up nahe deiner Frequenz. "
    "F10 startet und beendet den Contest.":
        "Little pitch spread = dense pile-up close to your frequency. "
        "F10 starts and ends the contest.",
    "Eingabe": "Entry",
    "Enter sendet die passende nächste Nachricht (leer: CQ, mit Call: Austausch, mit "
    "Austausch: TU + loggen). Call nach dem Austausch korrigiert: Enter sendet „Call TU“ "
    "und loggt. Call mit „?“ (z. B. DL1? oder DL?ABC) fragt nur nach. "
    "Achtung: Anrufer antworten manchmal auch auf ein fast richtiges Call. "
    "Esc bricht ab, Leertaste wechselt das Feld.":
        "Enter sends the next appropriate message (empty: CQ, with call: exchange, with "
        "exchange: TU + log). Call corrected after the exchange: Enter sends “Call TU” "
        "and logs. A call with “?” (e.g. DL1? or DL?ABC) only asks. "
        "Note: callers sometimes answer to an almost correct call too. "
        "Esc aborts, space bar switches the field.",
    "Nr": "No.",
    "Ergebnis": "Result",
    "laufende Nummer (automatisch)": "serial number (automatic)",
    "CQ-Zone": "CQ zone",
    "ITU-Zone oder Verband": "ITU zone or society",
    "dein DOK": "your DOK",
    "Bundesstaat": "state",
    "Leistung (z. B. 100, KW)": "power (e.g. 100, KW)",
    "Bitte ein gültiges eigenes Rufzeichen eintragen.": "Please enter a valid callsign of your own.",
    "Bitte deinen Austausch eintragen.": "Please enter your exchange.",
    "Ungültige Einstellung (WPM, Tonhöhe, Aktivität, Dauer oder Anrufer).":
        "Invalid setting (WPM, pitch, activity, duration or callers).",
    "Läuft – F1 oder Enter ruft CQ.": "Running – F1 or Enter calls CQ.",
    "Austausch falsch": "exchange wrong",
    "Beendet: {correct} von {total} QSOs richtig geloggt": "Finished: {correct} of {total} QSOs logged correctly",
    "Beendet.": "Finished.",
    "Zeit abgelaufen. ": "Time is up. ",
    "QSOs: {total} · richtig: {correct} · Rate: {rate:.0f}/h": "QSOs: {total} · correct: {correct} · rate: {rate:.0f}/h",
    " · Rest {time}": " · left {time}",
    "Erst ein Rufzeichen ins Call-Feld eintragen.": "Enter a callsign in the call field first.",
    "Sende: {text} – nicht geloggt ({missing} fehlt)": "Sending: {text} – not logged ({missing} missing)",
    "Sende: {text}": "Sending: {text}",
    "Abgebrochen.": "Aborted.",
    "NIL – keine Station hat dir einen Austausch gegeben": "NIL – no station gave you an exchange",
    " (ähnlich ruft: {call})": " (similar call: {call})",
    "Busted – richtig: {call}": "Busted – correct: {call}",
    "Austausch falsch – richtig: {exchange}": "Exchange wrong – correct: {exchange}",
})

# --- modes/network_mode.py ---
EN.update({
    "Netzwerk": "Network",
    "Eigener Text": "Own text",
    "Abgelehnt: Der Trainer nutzt eine andere Programmversion.":
        "Rejected: the trainer is using a different program version.",
    "Abgelehnt: PIN falsch.": "Rejected: wrong PIN.",
    "Abgelehnt: Name fehlt oder ist schon vergeben.": "Rejected: name missing or already taken.",
    "Üben in der Gruppe im lokalen Netz (Kursraum, Clubheim): Der Trainer gibt vor, alle hören "
    "dieselbe Sequenz über den eigenen Kopfhörer und tippen mit. Übertragen wird nur Text, der "
    "Ton entsteht auf jedem Rechner selbst.":
        "Practise as a group on the local network (classroom, club station): the trainer sets the pace, "
        "everyone hears the same sequence on their own headphones and copies it. Only text is sent; the "
        "sound is generated on each computer.",
    "Ich bin:": "I am:",
    "Teilnehmer": "Participant",
    "Trainer": "Trainer",
    "Sitzung": "Session",
    "Name der Sitzung:": "Session name:",
    "Morsekurs": "Morse class",
    "Port:": "Port:",
    "Sitzung öffnen": "Open session",
    "Sitzung schließen": "Close session",
    "Die Teilnehmer finden die Sitzung über „Suchen“ oder geben die Adresse ein. Beim ersten "
    "Öffnen fragt unter Windows eventuell die Firewall – für private Netzwerke zulassen.":
        "Participants find the session with “Search” or enter the address. The first time, the Windows "
        "firewall may ask – allow it for private networks.",
    "Übung": "Exercise",
    "Anzahl Sequenzen:": "Number of sequences:",
    "(0 = bis Stop)": "(0 = until Stop)",
    "Antwortzeit:": "Answer time:",
    "s nach dem Ton": "s after the tone",
    "Automatisch weiter, sobald alle geantwortet haben oder die Zeit um ist":
        "Continue automatically once everyone has answered or time is up",
    "Auch an diesem Rechner abspielen": "Also play on this computer",
    "Ton für alle nur über diesen Rechner (Lautsprecher)": "Sound for everyone only from this computer (speakers)",
    "Anfangs- und Schlusszeichen senden (VVV = und +)": "Send start and end signs (VVV = and +)",
    "Alle hören denselben Lautsprecher, die Teilnehmer-Rechner bleiben stumm und dienen nur zum Eintippen – "
    "ohne Kopfhörer und ohne Versatz zwischen den Rechnern. Die Lösung kommt dann einmal für alle, wenn jemand "
    "sie nicht flüssig hatte.":
        "Everyone hears the same speakers; the participants' computers stay silent and are only used for "
        "typing – no headphones and no offset between computers. The solution is then played once for "
        "everyone if someone did not have it fluently.",
    "(Lautsprecher)": "(speakers)",
    "Eine Zeile je Sequenz, in dieser Reihenfolge; Leerzeichen werden als Wortabstand gesendet, "
    "aber nicht gewertet. Betriebszeichen: + für AR, ( für KN, * für SK, # für BK – "
    "so tippen es auch die Teilnehmer.":
        "One line per sequence, in this order; spaces are sent as word gaps but not scored. Prosigns: "
        "+ for AR, ( for KN, * for SK, # for BK – participants type them the same way.",
    "Die Antwortzeit ist die harte Grenze. Als flüssig zählt eine richtige Antwort nur beim ersten "
    "Hören und innerhalb von 1,5 s plus 0,6 s je Zeichen nach dem Ton – wer länger braucht, zählt "
    "vermutlich mit.":
        "The answer time is the hard limit. A correct answer only counts as fluent on the first hearing "
        "and within 1.5 s plus 0.6 s per character after the tone – anyone taking longer is probably "
        "counting dits and dahs.",
    "Lösung vorspielen, wenn sie nicht flüssig richtig war": "Play the solution if it was not fluently correct",
    "Zeichentempo {wpm} WPM: So langsame Zeichen lassen sich mitzählen. Besser schnelle Zeichen "
    "mit längeren Pausen (Farnsworth).":
        "Character speed {wpm} WPM: characters this slow can be counted. Better use fast characters "
        "with longer gaps (Farnsworth).",
    "Flüssig": "Fluent",
    "Hinweis: Die Zeichen kamen mit {wpm} WPM, so langsam lassen sie sich mitzählen. Besser mit "
    "Koch-Tempo {rec}/{eff} weiterüben, damit sich das Klangbild einprägt. Für das Koch-Diplom "
    "zählen Läufe erst ab {min} WPM Zeichentempo.":
        "Note: the characters were sent at {wpm} WPM – that slow, they can be counted. Better keep "
        "practising at Koch speed {rec}/{eff} so the sound pattern sticks. For the Koch award, runs "
        "count only from {min} WPM character speed.",
    "(wiederholt)": "(repeated)",
    "(langsam)": "(slow)",
    "(mit Wiederholung – zählt nicht als flüssig)": "(after a repeat – does not count as fluent)",
    "(zu langsam – zählt nicht als flüssig)": "(too slow – does not count as fluent)",
    "Sequenzen flüssig": "Sequences fluent",
    "Weiter (F7)": "Next (F7)",
    "Für alle wiederholen (F6)": "Repeat for everyone (F6)",
    "Häufigste Fehler": "Most common errors",
    "In eigenem Fenster": "In a separate window",
    "Die Tabelle ist in einem eigenen Fenster.": "The table is in a separate window.",
    "Zurückholen": "Bring back",
    "Teilnehmer – {session}": "Participants – {session}",
    "Schwächste Zeichen": "Weakest characters",
    "Einen Teilnehmer anklicken, um seine Fehler zu sehen.": "Click a participant to see their errors.",
    "{name}: Fehler {confusions} · schwächste Zeichen {weak}": "{name}: errors {confusions} · weakest characters {weak}",
    "{tempo}: {share:.0%} der Sequenzen flüssig": "{tempo}: {share:.0%} of sequences fluent",
    "Tempo kann steigen.": "speed can go up.",
    "Tempo lieber senken.": "better lower the speed.",
    "Tempo passt.": "speed is right.",
    "+1 WPM effektiv": "+1 WPM effective",
    "−1 WPM effektiv": "−1 WPM effective",
    "Tempo {before} → {after}, ab der nächsten Sequenz.": "Speed {before} → {after}, from the next sequence.",
    "Öffne eine Sitzung, damit sich Teilnehmer anmelden können.": "Open a session so participants can join.",
    "Status": "Status",
    "Aktuelle Antwort": "Current answer",
    "Zeit (s)": "Time (s)",
    "Als CSV speichern": "Save as CSV",
    "Verbinden": "Connect",
    "Name/Rufzeichen:": "Name/callsign:",
    "PIN:": "PIN:",
    "Trainer:": "Trainer:",
    "Suchen": "Search",
    "Adresse wie beim Trainer angezeigt, z. B. 192.168.1.20 (anderer Port: 192.168.1.20:7400).":
        "Address as shown on the trainer's screen, e.g. 192.168.1.20 (other port: 192.168.1.20:7400).",
    "Suche den Trainer oder gib seine Adresse ein.": "Search for the trainer or enter their address.",
    "Ungültiger Port (1024–65535).": "Invalid port (1024–65535).",
    "Port {port} lässt sich nicht öffnen: {error}": "Cannot open port {port}: {error}",
    "Adresse {address} · PIN {pin}": "Address {address} · PIN {pin}",
    "Warte auf Teilnehmer…": "Waiting for participants…",
    "Sitzung geschlossen.": "Session closed.",
    "Ungültige Anzahl, Antwortzeit, Schreibpause oder Gruppenlänge!":
        "Invalid count, answer time, writing pause or group length!",
    "Ablauf:": "Flow:",
    "Warten auf Antworten": "Wait for answers",
    "Fester Takt (Mitschreiben auf Papier)": "Fixed pace (copying on paper)",
    "Schreibpause:": "Writing pause:",
    "s nach dem Ton, gleich für jede Sequenz": "s after the tone, the same for every sequence",
    "Die nächste Sequenz kommt nach Ton und Schreibpause, egal wer geantwortet hat. Lösungen gibt es erst am "
    "Ende unter „Auflösung“ – dort lassen sie sich auch anhören. Besser Blöcke von 20–25 Sequenzen mit "
    "Auflösung dazwischen als „bis Stop“. Wer ohne Rechner mitschreibt, hört den Ton über die Lautsprecher "
    "dieses Rechners. Die Mitschrift lässt sich danach abtippen: am eigenen Rechner oder hier unter "
    "„Papierbogen eintragen“ – gewertet ohne Zeit.":
        "The next sequence comes after the tone and the writing pause, whoever has answered. Solutions are "
        "shown only at the end under “Solutions” – you can listen to them there, too. Blocks of 20–25 "
        "sequences with solutions in between work better than “until Stop”. Anyone copying without a computer "
        "hears the tone from this computer's speakers. The copy can be typed in afterwards: on one's own "
        "computer or here under “Enter paper sheet” – scored without timing.",
    "Antwortbogen drucken": "Print answer sheet",
    "Papierbogen eintragen": "Enter paper sheet",
    "Papier": "Paper",
    "Papierbogen eintragen – {session}": "Enter paper sheet – {session}",
    "Übernehmen": "Apply",
    "Je Nummer die Zeile vom Zettel, leer = verpasst. Enter springt zur nächsten Nummer. Gewertet wird "
    "richtig oder falsch, ohne Zeit – nicht als flüssig und nicht für die Tempo-Empfehlung.":
        "For each number the line from the sheet, empty = missed. Enter jumps to the next number. Scored as "
        "right or wrong without timing – not as fluent and not for the speed advice.",
    "„{name}“ hat schon am Rechner geantwortet – anderen Namen wählen.":
        "“{name}” has already answered on a computer – choose another name.",
    "Bogen von {name}: {correct} von {total} richtig. Nächster Bogen?":
        "Sheet from {name}: {correct} of {total} right. Next sheet?",
    "Datum": "Date",
    "Im Browser geöffnet, dort drucken: {path}": "Opened in the browser, print from there: {path}",
    "Im festen Takt auf Papier mitschreiben und am Ende abtippen":
        "With fixed pace, copy on paper and type it in at the end",
    "Mitschrift abtippen": "Type in your copy",
    "Je Nummer die Zeile vom Zettel, leer = verpasst. Enter springt zur nächsten Nummer. Gewertet wird "
    "ohne Zeit, also nicht als flüssig.":
        "For each number the line from your sheet, empty = missed. Enter jumps to the next number. Scored "
        "without timing, so not as fluent.",
    "Auswerten": "Evaluate",
    "Durchgang beendet. Tippe jetzt deine Mitschrift ab und dann „Auswerten“.":
        "Run finished. Now type in your copy, then “Evaluate”.",
    "Nr. {n} – schreib mit…": "No. {n} – write it down…",
    "Nr. {n} – auf Papier": "No. {n} – on paper",
    "Auflösung": "Solutions",
    "Auflösung – {session}": "Solutions – {session}",
    "Kopieren": "Copy",
    "In die Zwischenablage kopiert.": "Copied to the clipboard.",
    "Noch keine Sequenzen.": "No sequences yet.",
    "Klick oder Leertaste: anhören · ↻ = für alle wiederholt": "Click or space: listen · ↻ = repeated for all",
    "Verpasst? Lücke lassen und bei der nächsten Nummer weiterschreiben.":
        "Missed one? Leave a gap and carry on with the next number.",
    "Nr. {n}{of}": "No. {n}{of}",
    "Die Lösungen stehen unter „Auflösung“.": "The solutions are under “Solutions”.",
    "Auswertung nach dem Durchgang (fester Takt).": "Results after the run (fixed pace).",
    "eingegangen": "received",
    "Nr.": "No.",
    "Nr. {n} notiert": "No. {n} noted",
    "Warte auf die nächste Sequenz…": "Waiting for the next sequence…",
    "Doppelklick oder Leertaste: noch einmal anhören": "Double-click or space: listen again",
    "Kein eigener Text – eine Zeile je Sequenz eintragen.": "No text of your own – enter one line per sequence.",
    "Durchgang beendet: {n} Sequenzen.": "Run finished: {n} sequences.",
    "{n} Teilnehmer verbunden. Start, wenn alle da sind.": "{n} participant(s) connected. Start when everyone is here.",
    " von {total}": " of {total}",
    "Nr. {n}{of}: {text}": "No. {n}{of}: {text}",
    "{done} von {total} haben geantwortet": "{done} of {total} have answered",
    "weiter mit „Weiter“": "continue with “Next”",
    "verbunden": "connected",
    "getrennt": "disconnected",
    "keine Antwort": "no answer",
    "Gruppe: {share:.0%} der Zeichen richtig, {fluent:.0%} der Sequenzen flüssig":
        "Group: {share:.0%} of characters correct, {fluent:.0%} of sequences fluent",
    "Häufigste Fehler: ": "Most common errors: ",
    "Schwächste Zeichen: ": "Weakest characters: ",
    "Zeichen richtig (%)": "Characters correct (%)",
    "Sequenzen richtig": "Sequences correct",
    "Median Zeit (s)": "Median time (s)",
    "Nicht gespeichert: {error}": "Not saved: {error}",
    "Suche Trainer im Netz…": "Searching the network for a trainer…",
    "Kein Trainer gefunden. Adresse von Hand eingeben?": "No trainer found. Enter the address by hand?",
    "Gefunden: {names}": "Found: {names}",
    "Bitte Name oder Rufzeichen eingeben.": "Please enter a name or callsign.",
    "Bitte die Adresse des Trainers eingeben oder suchen.": "Please enter the trainer's address or search for it.",
    "Verbinde…": "Connecting…",
    "Trennen": "Disconnect",
    "Getrennt.": "Disconnected.",
    "Verbunden mit „{session}“. Warte auf den Trainer…": "Connected to “{session}”. Waiting for the trainer…",
    "Keine Verbindung zum Trainer: {error}": "No connection to the trainer: {error}",
    "Verbindung zum Trainer beendet.": "Connection to the trainer closed.",
    "Durchgang beendet.": "Run finished.",
    "Durchgang beendet: {correct} von {total} Sequenzen richtig.": "Run finished: {correct} of {total} sequences correct.",
    "Warte auf den Trainer…": "Waiting for the trainer…",

    # Updates (widgets/updater.py, app.py, Netzwerk-Reiter)
    "Update": "Update",
    "Version {version} verfügbar": "Version {version} available",
    "Version {theirs} ist erschienen, du hast {mine}.": "Version {theirs} has been released, you have {mine}.",
    "Der Trainer nutzt Version {theirs}, du hast {mine}.": "The trainer uses version {theirs}, you have {mine}.",
    "Jetzt aktualisieren und neu starten? Geladen wird von GitHub.":
        "Update and restart now? It is downloaded from GitHub.",
    "Lade Version {version}… {progress}": "Downloading version {version}… {progress}",
    "Update fehlgeschlagen: {error}. Von Hand laden: {url}": "Update failed: {error}. Download manually: {url}",
    "Version {version} installiert – starte neu…": "Version {version} installed – restarting…",
    "Bitte aktualisieren: {url}": "Please update: {url}",
    # Unerwartete Fehler (app.py, core/errorlog.py)
    "Unerwarteter Fehler": "Unexpected error",
    "Im Programm ist ein unerwarteter Fehler aufgetreten. Einzelheiten stehen in\n{path}\n\n"
    "Bitte schick diese Datei mit, wenn du den Fehler meldest.":
        "An unexpected error occurred in the program. Details are in\n{path}\n\n"
        "Please include this file when you report the error.",
    "MP3 nicht erstellt: {error}": "MP3 not created: {error}",
})

# Diplome (core/awards.py)
EN.update({
    "Bronze": "Bronze", "Silber": "Silver", "Gold": "Gold", "Platin": "Platinum",
    "Koch": "Koch",
    "Bestandener Aufstiegslauf (≥ 50 Zeichen, ≥ 90 % beim ersten Versuch, Zeichen ≥ 18 WPM)":
        "Passed lesson run (≥ 50 characters, ≥ 90 % at the first attempt, characters ≥ 18 WPM)",
    "Lektionen": "lessons",
    "Worked All Letters": "Worked All Letters",
    "Bronze: 10 Buchstaben in Fach 3, Silber: alle 26, Gold: alle Buchstaben in Fach 6 und alle Ziffern "
    "in Fach 4":
        "Bronze: 10 letters in box 3, Silver: all 26, Gold: all letters in box 6 and all digits in box 4",
    "Mitschreiben im Fluss": "Copying in flow",
    "Kontinuierlich mit Klartext ohne eigene Wörter, Zeichensatz mindestens Lektion 15, voller 3-Min.-Lauf, "
    "≥ 90 % abzüglich überzähliger Tasten, Zeichen ≥ 18 WPM; Gold nur mit Wendungen oder QSO":
        "Continuous with plain text without your own words, character set at least lesson 15, full 3-min run, "
        "≥ 90 % minus extra keys, characters ≥ 18 WPM; Gold only with phrases or QSO",
    "WPM eff.": "WPM eff.",
    "Kontinuierlich mit Zufallsgruppen (≥ 5 Zeichen), voller Zeichensatz, ohne Farnsworth, voller "
    "3-Min.-Lauf, ≥ 90 % abzüglich überzähliger Tasten":
        "Continuous with random groups (≥ 5 characters), full character set, no Farnsworth, full 3-min "
        "run, ≥ 90 % minus extra keys",
    "QRN-fest": "QRN-proof",
    "Gruppen oder Kontinuierlich, ≥ 200 Zeichen, Störlautstärke den ganzen Lauf ≥ 100 %, Zeichen ≥ 20 WPM, "
    "effektiv ≥ 12 WPM, bei Gruppen der rechtzeitige erste Versuch; Bronze: Band leicht 90 %, Silber: mittel "
    "90 %, Gold: stark 85 %":
        "Groups or continuous, ≥ 200 characters, noise volume ≥ 100 % for the whole run, characters ≥ 20 WPM, "
        "effective ≥ 12 WPM, in groups the first attempt in time; Bronze: band light 90 %, Silver: medium "
        "90 %, Gold: heavy 85 %",
    "Rufz": "Rufz",
    "Voller Rufz-Durchgang mit 50 Rufzeichen, ohne Präfix-Filter, Zeichentempo beim Start ≥ 20 WPM":
        "Full Rufz run with 50 calls, no prefix filter, character speed at the start ≥ 20 WPM",
    "Punkte": "points",
    "Durchgang ≥ 10 Min.; Bronze: ≥ 20 WPM, 10 QSOs in 10 Min., ≤ 10 % Fehler; Silber: ≥ 25 WPM, "
    "Aktivität ≥ 2, 20 QSOs, ≤ 5 %; Gold: ≥ 30 WPM, Aktivität ≥ 3, 25 QSOs, höchstens 1 Fehler":
        "Run ≥ 10 min; Bronze: ≥ 20 WPM, 10 QSOs in 10 min, ≤ 10 % errors; Silver: ≥ 25 WPM, "
        "activity ≥ 2, 20 QSOs, ≤ 5 %; Gold: ≥ 30 WPM, activity ≥ 3, 25 QSOs, at most 1 error",
    "WPX": "WPX", "QRQ": "QRQ", "WPM": "WPM",
    "Verschiedene WPX-Präfixe, beim ersten Versuch richtig (Rufzeichen und Contest, dort ohne Rückfrage nach "
    "dem Call), Zeichen ≥ 18 WPM":
        "Different WPX prefixes, right at the first attempt (callsigns and contest, there without asking for "
        "the call again), characters ≥ 18 WPM",
    "Präfixe": "prefixes",
    "Kopfhörer": "Headphones",
    "Noch kein Lauf ab Band {band}, der die übrigen Bedingungen erfüllt":
        "No run yet from band {band} that meets the other conditions",
    "Bester Lauf ab Band {band}: {share} % (nötig {need} %)": "Best run from band {band}: {share} % (needed {need} %)",
    "Noch kein Durchgang mit ≥ {wpm} WPM und Aktivität ≥ {activity}":
        "No run yet with ≥ {wpm} WPM and activity ≥ {activity}",
    "Bester Durchgang mit ≥ {wpm} WPM: {rate} QSOs in 10 Min. (nötig {need}), {errors} Fehler ({share} %)":
        "Best run with ≥ {wpm} WPM: {rate} QSOs in 10 min (needed {need}), {errors} errors ({share} %)",
    "Noch kein Paar unter deinen häufigsten Verwechslungen": "No pair among your most frequent confusions yet",
    "Nächstes Paar {pair}: noch {days} Tage ohne Verwechslung, {tries} / {need} Versuche je Zeichen":
        "Next pair {pair}: {days} more days without confusion, {tries} / {need} attempts per character",
    "3 normale QSOs in Folge mit „Kopfhören + Fragen“, alle Fragen richtig, ohne „Nochmal“; Silber und Gold "
    "mit der Länge Normal oder Lang":
        "3 normal QSOs in a row with “Head copy + questions”, all questions right, without “Again”; Silver and "
        "Gold with the length Normal or Long",
    "Verwechslung überwunden": "Confusion overcome",
    "Ein häufig verwechseltes Paar 28 Tage lang mit je ≥ 40 Versuchen höchstens einmal verwechselt":
        "A frequently confused pair confused at most once in 28 days with ≥ 40 attempts each",
    "Paare": "pairs",
    "Ausdauer": "Endurance",
    "Tage mit ≥ 10 Min. Übung, nicht in Folge": "Days with ≥ 10 min practice, not in a row",
    "Tage": "days",
    "Zeichen gehört": "Characters heard",
    "Richtig erkannte Zufallszeichen": "Correctly recognised random characters",
    "Erstes QSO verstanden": "First QSO understood",
    "Normales QSO mit Abfrage, alles richtig, ohne „Nochmal“, ≥ 15 WPM effektiv":
        "Normal QSO with questions, all right, without “Again”, ≥ 15 WPM effective",
    "Worked All Contests": "Worked All Contests",
    "Alle 5 Contest-Arten mit je ≥ 30 QSOs und ≤ 10 % Fehlern":
        "All 5 contest types with ≥ 30 QSOs each and ≤ 10 % errors",
    "Contests": "contests",
    "Clubabend": "Club night",
    "Tage mit zusammen ≥ 10 Min. Netzwerk-Übung, mitgemacht oder als Trainer geleitet":
        "Days with ≥ 10 min of network sessions in total, taken part in or led as trainer",
    "Abende": "evenings",
    "Q-Gruppen-Kenner": "Q-code expert",
    "Jede der 20 Q-Gruppen 3× beim ersten Hören richtig, an mindestens 2 Tagen, Zeichen ≥ 18 WPM":
        "Each of the 20 Q codes right 3× at the first hearing, on at least 2 days, characters ≥ 18 WPM",
    "Q-Gruppen": "Q codes",
    "Alle Ziffern": "All digits",
    "Alle 10 Ziffern mindestens in Fach 3": "All 10 digits at least in box 3",
    "Ziffern": "digits",
    "Diplome": "Awards", "Diplom": "Award", "Siegel": "Seals", "Nächstes Ziel": "Next goal",
    "ab Lektion": "from lesson", "erreicht": "achieved",
    "an einem zweiten Tag wiederholen": "repeat on a second day",
    "{have} / {need} {unit}": "{have} / {need} {unit}",
    "{level}: {progress}": "{level}: {progress}",
    "Stufen: {steps} {unit}": "Levels: {steps} {unit}",
    "Silber und höher: an zwei verschiedenen Tagen.": "Silver and above: on two different days.",
    "{level} am {date}": "{level} on {date}",
    "Erreicht: {seals}": "Achieved: {seals}",
    "Erreicht am {date}": "Achieved on {date}",
    "{seals} Siegel in {awards} von {total} Diplomen": "{seals} seals in {awards} of {total} awards",
    "Noch keine Siegel": "No seals yet",
    "{award} – {level}": "{award} – {level}",
    "{level} ab {target} {unit}": "{level} from {target} {unit}",
    "verliehen an": "awarded to",
    "Datum:": "Date:",
    "Morsetrainer · entwickelt von DL4YM": "Morsetrainer · developed by DL4YM",
    "Neues Siegel": "New seal", "Neue Siegel": "New seals",
    "Drucken": "Print",
    "Auf dem Diplom:": "On the award:",
    "eigenes|Rufzeichen": "Callsign",
    "falls vorhanden; für Diplome, Contest und Netzwerk": "if you have one; for awards, contest and network",
    "ohne eigenes Rufzeichen: ein ausgedachtes eintragen": "no callsign of your own: enter a made-up one",
    "Diplom ansehen und drucken": "View and print award",
    "Aus deinem bisherigen Üben wurden {n} Diplome nachgetragen. Du findest sie im Reiter Statistik unter "
    "„Diplome“ und kannst sie dort ansehen und drucken.":
        "{n} awards were filled in from your practice so far. You will find them in the Statistics tab under "
        "“Awards”, where you can view and print them.",
    "Eine Zeile wählen, um die Bedingung zu sehen. Erreichte Siegel bleiben, auch wenn die Gesamtstatistik "
    "zurückgesetzt wird.":
        "Select a row to see the condition. Seals you have achieved stay, even when the overall statistics "
        "are reset.",
})
