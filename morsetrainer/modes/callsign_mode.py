"""Rufzeichen-Modus: sendet echte Amateurfunk-Rufzeichen aus der Super
Check Partial-Datenbank (callsigns.scp, ~50.000 aktive Contest-Rufzeichen,
https://www.supercheckpartial.com – dieselbe Liste, die auch Morse Runner
und viele Contest-Logger verwenden). Zum Aktualisieren einfach die
aktuelle MASTER.SCP von dort als callsigns.scp ablegen.

Optional lässt sich die Liste per Präfix-Filter einschränken (z. B. nur
DL/DK/DJ). Fehlt die Datei, werden wie früher zufällige Rufzeichen nach
dem Muster Präfix + Ziffer + Suffix erzeugt. Auf Wunsch bekommt ein kleiner
Teil der Rufzeichen einen Anhang (/P, /M, selten /QRP, /MM, /AM) oder ein
Gast-Präfix (OE/DL4YM), etwa so häufig wie im Contest.

Rufz-Durchgang (angelehnt an RufzXP): genau RUFZ_CALLS Rufzeichen, je ein
Versuch, kein Wiederholen, das Tempo wächst immer mit; Punkte je richtiges
Rufzeichen = Länge × effektives Tempo (eigene Formel, nicht die von
RufzXP). Vollständige Durchgänge landen im Verlauf, der Bestwert wird
gespeichert.

Standardmäßig kommen nur Rufzeichen aus Zeichen, die im Zeichensatz oben
stehen (auch Anhänge): Ungelernte Zeichen zu raten untergräbt die
Koch-Methode. Abschaltbar für alle, die schon alle Zeichen können."""
import random
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from morsetrainer import DATA_DIR
from morsetrainer.core import koch, stats, tempo
from morsetrainer.modes.sequence_mode import HEAD, SequenceModeFrame
from morsetrainer.widgets import theme
from morsetrainer.core.weighting import CharPicker

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
CALL_CHARS = LETTERS + DIGITS + "/"
CALLSIGN_FILE = DATA_DIR / "callsigns.scp"

# Bei gewichteter Auswahl wird aus so vielen zufälligen Kandidaten eines
# bevorzugt, je schwächer sein schwächstes Zeichen ist.
WEIGHTED_CANDIDATES = 50
# Weniger passende Rufzeichen reichen nicht für einen Durchgang (man würde
# sie auswendig lernen).
MIN_POOL = 30
# Rufzeichen je Rufz-Durchgang.
RUFZ_CALLS = 50


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


# Anteil der Rufzeichen, die einen Anhang oder ein Gast-Präfix bekommen
# (grob wie im Contest; in der SCP-Liste selbst gibt es praktisch keine).
AFFIX_PROBABILITY = 0.08

# Anhänge mit grober Häufigkeit: /P und /M dominieren; /QRP wird selten
# mitgesendet, /MM (maritime mobile) und /AM (aeronautical mobile) sind rar.
SUFFIXES = {"/P": 60, "/M": 25, "/QRP": 5, "/MM": 4, "/AM": 1}

# Gast-Präfixe beim Funken im Ausland (CEPT), z. B. OE/DL4YM.
GUEST_PREFIXES = [
    "OE", "HB9", "PA", "ON", "F", "LX", "OZ", "SM", "LA", "OH", "G", "GM", "GW",
    "EI", "EA", "EA8", "CT", "CT3", "I", "IS0", "SV", "SV9", "9A", "S5", "OK",
    "OM", "SP", "HA", "YO", "LZ", "TF", "OY", "9H", "5B", "4X",
]


def is_us_call(call: str) -> bool:
    return call[0] in "KNW" or ("AA" <= call[:2] <= "AL")


def _fits(text: str, allowed) -> bool:
    return allowed is None or all(ch in allowed for ch in text)


def add_affix(call: str, allowed=None) -> str:
    """Hängt mit AFFIX_PROBABILITY einen Anhang an oder stellt ein
    Gast-Präfix voran, nur aus Zeichen in `allowed` (None = alle).
    Rufzeichen, die schon einen '/' enthalten, bleiben unverändert."""
    if "/" in call or random.random() >= AFFIX_PROBABILITY or not _fits("/", allowed):
        return call
    options = []  # (Ergebnis-Funktion, Gewicht)
    suffixes = {s: w for s, w in SUFFIXES.items() if _fits(s, allowed)}
    guests = [p for p in GUEST_PREFIXES if not call.startswith(p) and _fits(p, allowed)]
    digits = [d for d in DIGITS if _fits(d, allowed)]
    if suffixes:
        options.append((lambda: call + random.choices(list(suffixes), weights=list(suffixes.values()))[0], 7))
    if guests:
        options.append((lambda: f"{random.choice(guests)}/{call}", 3))
    if digits and is_us_call(call):
        # US-Stationen außerhalb ihres Rufzeichenbezirks, z. B. W1AW/4 (selten).
        options.append((lambda: f"{call}/{random.choice(digits)}", 0.5))
    if not options:
        return call
    make = random.choices([o for o, _ in options], weights=[w for _, w in options])[0]
    return make()


def filter_calls(calls, prefixes, allowed):
    """Rufzeichen mit einem der Präfixe (leer = alle), nur aus Zeichen in
    `allowed` (None = alle)."""
    if prefixes:
        calls = [c for c in calls if c.startswith(tuple(prefixes))]
    if allowed is not None:
        calls = [c for c in calls if all(ch in allowed for ch in c)]
    return calls


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
        "auf bestimmte Länder beschränken, z. B. „DL DK DJ DO“ (Textanfang: „G“ "
        "umfasst auch GM, GW …)."
    )

    def _build_extra_settings(self, parent):
        self.all_calls, release = load_callsigns()
        self.pool = []

        settings = ttk.Frame(parent)
        settings.pack(fill="x", pady=1)
        ttk.Label(settings, text="Präfix-Filter:").pack(side="left", padx=(0, 4))
        self.prefix_var = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.prefix_var, width=24).pack(side="left")
        theme.hint(settings, text="(leer = alle)").pack(side="left", padx=(6, 0))

        self.learned_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, text="Nur gelernte Zeichen (Zeichensatz oben)", variable=self.learned_var,
        ).pack(anchor="w", pady=1)

        self.affix_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, text="Anhänge und Gast-Präfixe (/P, /M, OE/…, gelegentlich)",
            variable=self.affix_var,
        ).pack(anchor="w", pady=1)

        self.rufz_var = tk.BooleanVar(value=False)
        rufz = ttk.Frame(parent)
        rufz.pack(fill="x", pady=1)
        ttk.Checkbutton(
            rufz, text=f"Rufz-Durchgang: {RUFZ_CALLS} Rufzeichen, je ein Versuch, Punkte", variable=self.rufz_var,
        ).pack(side="left")
        self.rufz_best = 0
        self.rufz_best_var = tk.StringVar(value="")
        theme.hint(rufz, textvariable=self.rufz_best_var).pack(side="left", padx=(8, 0))
        self.rufz_done = self.rufz_correct = self.rufz_score = 0
        self.rufz_active = False  # Rufz-Durchgang läuft (Schalter beim Start)
        self.rufz_summary = ""
        self.rufz_used = set()
        self.rufz_start_wpm = 0

        if self.all_calls:
            self.list_text = f"Liste: {len(self.all_calls):,} Rufzeichen".replace(",", ".")
            if release:
                self.list_text += f" (SCP {release})"
        else:
            self.list_text = "callsigns.scp nicht gefunden – es werden Rufzeichen nach Muster erzeugt."
        self.list_info_var = tk.StringVar(value=self.list_text)
        theme.hint(parent, textvariable=self.list_info_var, wrap=540).pack(anchor="w", pady=(0, 4))
        for var in (self.prefix_var, self.learned_var, self.charset_var):
            var.trace_add("write", lambda *_: self._update_pool())
        self._update_pool()

    # --- Rufz-Durchgang --------------------------------------------------------
    def _fixed_run(self) -> bool:
        return self.rufz_active

    def _run_complete(self) -> bool:
        return self.rufz_active and self.rufz_done >= RUFZ_CALLS

    def _show_rufz_best(self):
        self.rufz_best_var.set(f"Bestwert {self.rufz_best:,} Punkte".replace(",", ".") if self.rufz_best else "")

    def _show_rufz_progress(self):
        score = f"{self.rufz_score:,}".replace(",", ".")
        self.remaining_var.set(f"Rufzeichen {self.rufz_done}/{RUFZ_CALLS} · {score} Punkte")

    def start(self):
        self.rufz_active = self.rufz_var.get()
        self.rufz_done = self.rufz_correct = self.rufz_score = 0
        self.rufz_used = set()  # im Durchgang schon gesendete Rufzeichen
        super().start()
        if self.running and self.tempo is not None:
            self.rufz_start_wpm = tempo.effective(self.tempo, self.tempo_fw)
        if self.running and self.rufz_active:
            self.repeat_button.config(state="disabled")  # kein „nochmal“ im Rufz
            self._show_rufz_progress()

    def _after_result(self, correct: bool, attempts: int):
        if not self.rufz_active:
            return
        self.rufz_done += 1
        # attempts > 1 heißt hier: richtig, aber zu langsam (nur ein Versuch).
        if correct and attempts == 1:
            # Vor der Tempo-Anpassung: das Tempo, mit dem es gesendet wurde.
            self.rufz_correct += 1
            self.rufz_score += len(self.current_sequence) * tempo.effective(self.tempo, self.tempo_fw)
        self._show_rufz_progress()

    def _finalize_session(self):
        self.rufz_summary = ""
        self.rufz_used = set()
        self.rufz_start_wpm = 0
        if self.rufz_active and self.session_stats is not None:
            score = f"{self.rufz_score:,}".replace(",", ".")
            if self.rufz_done >= RUFZ_CALLS:
                new_best = self.rufz_score > self.rufz_best
                stats.log_result("rufz", self.rufz_correct, self.rufz_done,
                                 self.tempo_best or self.rufz_start_wpm, score=self.rufz_score)
                if new_best:
                    self.rufz_best = self.rufz_score
                    self._show_rufz_best()
                self.rufz_summary = (f"Rufz: {score} Punkte, {self.rufz_correct} von {self.rufz_done} richtig"
                                     + (" – neuer Bestwert!" if new_best else ""))
            else:
                self.rufz_summary = f"Rufz abgebrochen nach {self.rufz_done} Rufzeichen ({score} Punkte, nicht gewertet)."
        super()._finalize_session()

    def stop(self):
        super().stop()
        if self.rufz_summary:
            self.status_var.set(self.rufz_summary)
        self.rufz_active = False

    def _allowed(self):
        """Erlaubte Zeichen (Zeichensatz oben) oder None, wenn alle."""
        if not self.learned_var.get():
            return None
        return set(self.charset_var.get().upper())

    def _update_pool(self):
        """Passende Rufzeichen neu bestimmen und die Anzahl anzeigen."""
        allowed = self._allowed()
        if self.all_calls:
            self.pool = filter_calls(self.all_calls, parse_prefixes(self.prefix_var.get()), allowed)
            if allowed is not None or self.prefix_var.get().strip():
                count = f"{len(self.pool):,}".replace(",", ".")
                self.list_info_var.set(f"{self.list_text} · passend: {count}")
            else:
                self.list_info_var.set(self.list_text)

    def _validate_settings(self) -> bool:
        if self.rufz_var.get() and self.style_var.get() == HEAD:
            self.status_var.set("Der Rufz-Durchgang braucht eine Eingabe – Mitschreiben oder Erst merken.")
            return False
        allowed = self._allowed()
        if not self.all_calls:
            self.pool = []
            if allowed is not None and not (allowed & set(LETTERS) and allowed & set(DIGITS)):
                self.status_var.set("Für Rufzeichen braucht der Zeichensatz Buchstaben und eine Ziffer.")
                return False
            return True
        self._update_pool()
        needed = max(MIN_POOL, RUFZ_CALLS) if self.rufz_var.get() else MIN_POOL
        if len(self.pool) < needed:
            if allowed is not None and not allowed & set(DIGITS):
                first = next(n for n in range(1, koch.MAX_LESSON + 1) if koch.newest_char(n) in DIGITS)
                hint = f"Die erste Ziffer kommt mit Koch-Lektion {first}."
            elif allowed is not None:
                hint = "Weitere Lektionen lernen oder „Nur gelernte Zeichen“ ausschalten."
            else:
                hint = "Präfix-Filter erweitern."
            self.status_var.set(f"Nur {len(self.pool)} passende Rufzeichen.\n{hint}")
            return False
        return True

    def _setup_pickers(self, weighted: bool):
        self.weighted = weighted
        allowed = self._allowed()
        letters = "".join(ch for ch in LETTERS if allowed is None or ch in allowed)
        digits = "".join(ch for ch in DIGITS if allowed is None or ch in allowed)
        self.char_picker = CharPicker(CALL_CHARS, weighted, self.session_stats)
        self.letter_picker = CharPicker(letters, weighted, self.session_stats)
        self.digit_picker = CharPicker(digits, weighted, self.session_stats)

    def _generate_sequence(self) -> str:
        call = self._pick_base_call()
        return add_affix(call, self._allowed()) if self.affix_var.get() else call

    def _pick_base_call(self) -> str:
        if not self.pool:
            return generate_callsign(self.letter_picker, self.digit_picker)
        pool = self.pool
        if self.rufz_active:
            # Im Rufz kein Rufzeichen zweimal: Wiedererkennen schönte die Punkte.
            pool = [c for c in self.pool if c not in self.rufz_used] or self.pool
        call = self._choose(pool)
        if self.rufz_active:
            self.rufz_used.add(call)
        return call

    def _choose(self, pool) -> str:
        if not self.weighted:
            return random.choice(pool)
        candidates = random.sample(pool, min(WEIGHTED_CANDIDATES, len(pool)))
        char_weight = dict(zip(CALL_CHARS, self.char_picker.weights()))
        # Nach dem schwächsten Zeichen: im Mittelwert ginge ein schwaches
        # Zeichen unter fünf sicheren unter.
        scores = [max(char_weight[ch] for ch in call) for call in candidates]
        return random.choices(candidates, weights=scores)[0]

    def _log_charset(self) -> str:
        if not self.pool:
            return "A-Z0-9 (Rufzeichen-Muster)"
        return "callsigns.scp"

    def _session_group_len(self):
        if not self.pool:
            return {"pattern": "prefix(1-2 Buchstaben) + Ziffer + suffix(1-3 Buchstaben)"}
        return {"source": "callsigns.scp", "prefixes": parse_prefixes(self.prefix_var.get()),
                "pool_size": len(self.pool), "affixes": self.affix_var.get(),
                "learned_only": self.learned_var.get()}

    def settings(self) -> dict:
        data = super().settings()
        data["prefixes"] = self.prefix_var.get()
        data["affix"] = self.affix_var.get()
        data["learned_only"] = self.learned_var.get()
        data["rufz"] = self.rufz_var.get()
        data["rufz_best"] = self.rufz_best
        return data

    def restore_settings(self, data: dict) -> None:
        super().restore_settings(data)
        if isinstance(data.get("prefixes"), str):
            self.prefix_var.set(data["prefixes"])
        if isinstance(data.get("affix"), bool):
            self.affix_var.set(data["affix"])
        if isinstance(data.get("learned_only"), bool):
            self.learned_var.set(data["learned_only"])
        if isinstance(data.get("rufz"), bool):
            self.rufz_var.set(data["rufz"])
        best = data.get("rufz_best")
        if isinstance(best, int) and not isinstance(best, bool) and best >= 0:
            self.rufz_best = best
            self._show_rufz_best()
