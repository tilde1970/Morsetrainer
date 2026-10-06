"""Die Übungs-Reiter. Jeder Reiter ist eine Klasse …ModeFrame, die das
Hauptfenster (app.py) so anlegt und bedient:

Anlegen: Frame(tab, charset_var, wpm_var, freq_var, weighted_var,
farnsworth_wpm, on_start=…, on_stop=…, **extra) mit den gemeinsamen
Einstellungen der Kopfleiste. on_start() sperrt die anderen Reiter, on_stop()
gibt sie frei und wertet den Durchgang aus (Lektion, Diplome). Über
Klassenattribute bestellt ein Reiter Zusätzliches: uses_vary (Tonhöhe und
Tempo variieren), uses_band (zentrale Bandbedingungen), uses_tempo_adjust
(Tempo-Empfehlung übernehmen), uses_network_hooks (Netzwerk-Reiter).

Bedienung:
- start() / stop(): Durchgang beginnen bzw. beenden; toggle_running() wechselt
  zwischen beiden (Start/Stop-Knopf, in manchen Reitern auch F5).
- on_key(event): Taste im Hauptfenster, solange kein Eingabefeld sie
  braucht; on_function_key(key) für F1–F12 (auch aus Eingabefeldern).
- settings() / restore_settings(data): eigene Einstellungen zum Speichern in
  window_state.json bzw. beim Start zurück; Unbrauchbares wird ignoriert.
- on_close(): beim Programmende laufende Wiedergabe und Timer beenden.

Dazu liest das Hauptfenster, wo vorhanden, status_var, feedback_var,
remaining_var und progress_var (für die Ansage „Wo bin ich?“) sowie
koch_result und groups_result (Angebot der nächsten Lektion bzw. der
Gruppen). Für die Tagesübung siehe daily_support.py."""
