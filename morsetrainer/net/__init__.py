"""Netzwerkmodus: ein Trainer gibt vor, mehrere Teilnehmer im lokalen Netz
hören und tippen mit.

Übers Netz geht nur Text, kein Ton: Der Trainer schickt je Durchgang den
Text samt Tempo und Bandbedingungen, jeder Teilnehmer erzeugt den Ton
selbst (eigener Kopfhörer, eigene Tonhöhe, keine Aussetzer). Die Antworten
gehen an den Trainer zurück, der sie in einer Tabelle sieht.

protocol.py  Nachrichten (JSON-Zeilen über TCP), Ports, Suche per UDP
server.py    Trainerseite: nimmt Teilnehmer an, verteilt, sammelt ein
client.py    Teilnehmerseite: verbindet sich, empfängt, antwortet
scoreboard.py  Auswertung aller Antworten beim Trainer (ohne Netz, ohne Tk)"""
