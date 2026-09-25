"""Morsetrainer von DL4YM.

core/     Ton, Morsecode, Bandbedingungen, Texte, Statistik
modes/    ein Modul je Trainingsreiter
widgets/  wiederverwendbare Tk-Bausteine
app.py    Hauptfenster mit allen Reitern"""
from pathlib import Path

# Nutzerdaten (stats/, window_state.json, callsigns.scp) liegen im
# Projektverzeichnis neben main.py, nicht im Paket.
PROJECT_DIR = Path(__file__).resolve().parent.parent
