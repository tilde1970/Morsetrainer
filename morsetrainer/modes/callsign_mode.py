"""Rufzeichen-Modus: sendet echte Amateurfunk-Rufzeichen aus der Super
Check Partial-Datenbank (callsigns.scp, ~50.000 aktive Contest-Rufzeichen,
https://www.supercheckpartial.com – dieselbe Liste, die auch Morse Runner
und viele Contest-Logger verwenden). Zum Aktualisieren einfach die
aktuelle MASTER.SCP von dort als callsigns.scp ablegen.

Optional lässt sich die Liste per Präfix-Filter einschränken (z. B. nur
DL/DK/DJ). Fehlt die Datei, werden wie früher zufällige Rufzeichen nach
dem Muster Präfix + Ziffer + Suffix erzeugt. Auf Wunsch bekommt ein Teil
der Rufzeichen einen Anhang (/P, /M, /MM, /AM, /QRP) oder ein Gast-Präfix
(OE/DL4YM).

Unabhängig vom oben eingestellten Zeichensatz, da echte Rufzeichen jeden
Buchstaben enthalten können."""
import random
import statistics
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from morsetrainer import DATA_DIR
from morsetrainer.modes.sequence_mode import SequenceModeFrame
from morsetrainer.core.weighting import CharPicker

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
CALL_CHARS = LETTERS + DIGITS + "/"
CALLSIGN_FILE = DATA_DIR / "callsigns.scp"

# Bei gewichteter Auswahl wird aus so vielen zufälligen Kandidaten dasjenige
# Rufzeichen bevorzugt, das die meisten deiner schwachen Zeichen enthält.
WEIGHTED_CANDIDATES = 50


def load_callsigns(path: Path = CALLSIGN_FILE):
    """Liest eine SCP-Datei. Gibt (Rufzeichen-Liste, Release-String) zurück;
    die Liste ist leer, wenn die Datei fehlt."""
    calls, release = [], ""
    try:
        with open(path, "rt", encoding="ascii", errors="ignore") as fp:
            for line in fp:
                line = line.strip().upper()
                if line.startswith("# RELEASE"):
                    release = line[len("# RELEASE"):].strip()
                if not line or line[0] in "#!":
                    continue
                if all(ch in CALL_CHARS for ch in line):
                    calls.append(line)
    except OSError:
        pass
    return calls, release


# Anteil der Rufzeichen, die einen Anhang oder ein Gast-Präfix bekommen.
AFFIX_PROBABILITY = 0.25

# Anhänge mit grober Häufigkeit: /P ist mit Abstand am häufigsten,
# /MM (maritime mobile) und /AM (aeronautical mobile) eher selten.
SUFFIXES = {"/P": 40, "/M": 20, "/QRP": 10, "/MM": 5, "/AM": 3}

# Gast-Präfixe beim Funken im Ausland (CEPT), z. B. OE/DL4YM.
GUEST_PREFIXES = [
    "OE", "HB9", "PA", "ON", "F", "LX", "OZ", "SM", "LA", "OH", "G", "GM", "GW",
    "EI", "EA", "EA8", "CT", "CT3", "I", "IS0", "SV", "SV9", "9A", "S5", "OK",
    "OM", "SP", "HA", "YO", "LZ", "TF", "OY", "9H", "5B", "4X",
]


def is_us_call(call: str) -> bool:
    return call[0] in "KNW" or ("AA" <= call[:2] <= "AL")


def add_affix(call: str) -> str:
    """Hängt mit AFFIX_PROBABILITY einen Anhang an oder stellt ein
    Gast-Präfix voran. Rufzeichen, die schon einen '/' enthalten, bleiben
    unverändert."""
    if "/" in call or random.random() >= AFFIX_PROBABILITY:
        return call
    kind = random.choices(["suffix", "guest", "area"], weights=[6, 3, 1])[0]
    if kind == "area" and is_us_call(call):
        # US-Stationen außerhalb ihres Rufzeichenbezirks, z. B. W1AW/4.
        return f"{call}/{random.choice(DIGITS)}"
    if kind == "guest":
        guests = [p for p in GUEST_PREFIXES if not call.startswith(p)]
        return f"{random.choice(guests)}/{call}"
    suffix = random.choices(list(SUFFIXES), weights=list(SUFFIXES.values()))[0]
    return f"{call}{suffix}"


def parse_prefixes(text: str):
    return [p for p in text.upper().replace(",", " ").split() if p]


def generate_callsign(letters: CharPicker, digits: CharPicker) -> str:
    prefix_len = random.choices([1, 2], weights=[1, 3])[0]
    prefix = letters.pick(prefix_len)
    digit = digits.pick()
    suffix_len = random.choices([1, 2, 3], weights=[1, 4, 5])[0]
    suffix = letters.pick(suffix_len)
    return f"{prefix}{digit}{suffix}"


class CallsignModeFrame(SequenceModeFrame):
    session_mode = "callsign"
    intro_text = (
        "Es werden echte Rufzeichen aus der Super-Check-Partial-Liste gesendet "
        "(aktive Contest-Stationen weltweit). Mit dem Präfix-Filter kannst du dich "
        "auf bestimmte Länder beschränken, z. B. „DL DK DJ DO“. Der Zeichensatz oben "
        "gilt hier nicht."
    )

    def _build_extra_settings(self, parent):
        self.all_calls, release = load_callsigns()
        self.pool = []

        pad = {"padx": 8, "pady": 4}
        settings = ttk.Frame(parent)
        settings.pack(fill="x", **pad)
        ttk.Label(settings, text="Präfix-Filter:").pack(side="left", padx=(0, 4))
        self.prefix_var = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.prefix_var, width=24).pack(side="left")
        ttk.Label(settings, text="(leer = alle)").pack(side="left", padx=(6, 0))

        self.affix_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, text="Anhänge und Gast-Präfixe (/P, /M, /MM, /AM, /QRP, OE/…)",
            variable=self.affix_var,
        ).pack(anchor="w", padx=8)

        if self.all_calls:
            info = f"Liste: {len(self.all_calls):,} Rufzeichen".replace(",", ".")
            if release:
                info += f" (SCP {release})"
        else:
            info = "callsigns.scp nicht gefunden – es werden Rufzeichen nach Muster erzeugt."
        self.list_info_var = tk.StringVar(value=info)
        ttk.Label(parent, textvariable=self.list_info_var).pack(anchor="w", padx=8)

    def _validate_settings(self) -> bool:
        if not self.all_calls:
            self.pool = []
            return True
        prefixes = parse_prefixes(self.prefix_var.get())
        if prefixes:
            self.pool = [c for c in self.all_calls if c.startswith(tuple(prefixes))]
        else:
            self.pool = self.all_calls
        if not self.pool:
            self.status_var.set("Kein Rufzeichen passt zum Präfix-Filter!")
            return False
        return True

    def _setup_pickers(self, weighted: bool):
        self.weighted = weighted
        self.char_picker = CharPicker(CALL_CHARS, weighted, self.session_stats)
        self.letter_picker = CharPicker(LETTERS, weighted, self.session_stats)
        self.digit_picker = CharPicker(DIGITS, weighted, self.session_stats)

    def _generate_sequence(self) -> str:
        call = self._pick_base_call()
        return add_affix(call) if self.affix_var.get() else call

    def _pick_base_call(self) -> str:
        if not self.pool:
            return generate_callsign(self.letter_picker, self.digit_picker)
        if not self.weighted:
            return random.choice(self.pool)
        candidates = random.sample(self.pool, min(WEIGHTED_CANDIDATES, len(self.pool)))
        char_weight = dict(zip(CALL_CHARS, self.char_picker.weights()))
        scores = [statistics.mean(char_weight[ch] for ch in call) for call in candidates]
        return random.choices(candidates, weights=scores)[0]

    def _log_charset(self) -> str:
        if not self.pool:
            return "A-Z0-9 (Rufzeichen-Muster)"
        return "callsigns.scp"

    def _session_group_len(self):
        if not self.pool:
            return {"pattern": "prefix(1-2 Buchstaben) + Ziffer + suffix(1-3 Buchstaben)"}
        return {"source": "callsigns.scp", "prefixes": parse_prefixes(self.prefix_var.get()),
                "pool_size": len(self.pool), "affixes": self.affix_var.get()}