"""Erzeugt realistische CW-QSOs mit den üblichen Abkürzungen.

- Normales QSO (Ragchew) zwischen zwei Stationen: Station 1 ruft CQ,
  Station 2 antwortet, dann werden Rapport, Name, QTH und je nach Länge
  Rig, Wetter, Alter usw. ausgetauscht.
- Contest-Run: eine Run-Station ruft CQ TEST und arbeitet mehrere Anrufer
  nacheinander ab, mit dem Austausch des jeweiligen Contests (CQ WW: Zone,
  CQ WPX: Seriennummer, WAG: DOK bzw. Nummer, ARRL DX: Bundesstaat bzw.
  Leistung, IARU HF: ITU-Zone bzw. Verbandskürzel der HQ-Stationen), inkl. typischer Rückfragen („F5X?“, „AGN?“) und Kurzzahlen
  (5NN, TT7).

Die Rufzeichen stammen aus callsigns.scp (wie im Rufzeichen-Modus); Name,
QTH, Zone usw. passen zum Land des Rufzeichens. Fehlt die Datei, werden
Rufzeichen nach Landesmuster erzeugt.

Neben dem Text liefert jedes QSO die Abfrage (was man mitloggen sollte)
als Tabelle aus Spalten und Zeilen."""
import random
import re
from dataclasses import dataclass
from datetime import datetime

from morsetrainer.modes.callsign_mode import load_callsigns
from morsetrainer.core.morse import BK, KN, MORSE_CODE, SK

# Kurz: nur Rapport/Name/QTH; Normal: + Rig, Leistung, Wetter;
# Lang: + Antenne, Alter, lizenziert seit, QSL-Info.
# Im Contest bestimmt die Länge die Anzahl der QSOs im Run.
LENGTH_SHORT, LENGTH_NORMAL, LENGTH_LONG = 0, 1, 2
CONTEST_QSO_COUNTS = (3, 5, 8)
# Anteil der Anrufe, bei denen weitere Stationen gleichzeitig rufen, und
# wie viele.
PILEUP_PROBABILITY = 0.45
PILEUP_EXTRA_CALLERS = (1, 2)

RAGCHEW = "ragchew"
QSO_TYPES = {
    RAGCHEW: "Normales QSO",
    "cqww": "Contest: CQ WW (Zone)",
    "wpx": "Contest: CQ WPX (Nummer)",
    "wag": "Contest: WAG (DOK)",
    "arrldx": "Contest: ARRL DX (Staat/Leistung)",
    "iaru": "Contest: IARU HF (ITU-Zone/HQ)",
}

# Arten, wie ein Abfragefeld verglichen wird (siehe qso_mode.normalize).
TEXT, RST, NUMBER = "text", "rst", "number"


@dataclass(frozen=True)
class Country:
    key: str
    pattern: str            # Regex auf den Rufzeichenanfang
    sample_prefixes: tuple  # für erzeugte Rufzeichen, wenn callsigns.scp fehlt
    zone: int               # CQ-Zone (für USA/Russland je nach Ziffer, siehe cq_zone)
    names: tuple
    qths: tuple


COUNTRIES = [
    Country("DL", r"D[A-R][0-9]", ("DL", "DK", "DJ", "DO", "DF", "DG"), 14,
            ("HANS", "PETER", "KLAUS", "UWE", "JENS", "FRANK", "MICHAEL", "ANDREAS", "THOMAS",
             "WOLFGANG", "JUERGEN", "STEFAN", "SABINE", "ANJA", "DIRK", "HOLGER"),
            ("BERLIN", "HAMBURG", "MUENCHEN", "KOELN", "OELDE", "MUENSTER", "DRESDEN", "LEIPZIG",
             "BREMEN", "HANNOVER", "STUTTGART", "KIEL", "ROSTOCK", "BIELEFELD", "KASSEL", "ERFURT")),
    Country("F", r"F[0-9]", ("F",), 14,
            ("JEAN", "PIERRE", "MICHEL", "ALAIN", "PHILIPPE", "PATRICK", "BERNARD"),
            ("PARIS", "LYON", "MARSEILLE", "TOULOUSE", "NANTES", "BORDEAUX", "LILLE", "DIJON")),
    Country("GM", r"(GM|MM|2M)[0-9]", ("GM", "MM"), 14,
            ("ANGUS", "IAN", "JOHN", "DOUGLAS", "ALAN"),
            ("EDINBURGH", "GLASGOW", "ABERDEEN", "DUNDEE", "INVERNESS")),
    Country("G", r"(G|M|2E)[0-9]", ("G", "M"), 14,
            ("JOHN", "DAVID", "PAUL", "MIKE", "STEVE", "CHRIS", "RICHARD", "PETE"),
            ("LONDON", "LEEDS", "YORK", "BRISTOL", "LEICESTER", "OXFORD", "NORWICH", "EXETER")),
    Country("I", r"I[A-Z]?[0-9]", ("I", "IK", "IZ", "IW"), 15,
            ("MARCO", "LUCA", "GIOVANNI", "PAOLO", "FRANCO", "GIUSEPPE"),
            ("ROMA", "MILANO", "TORINO", "NAPOLI", "BOLOGNA", "FIRENZE", "GENOVA")),
    Country("EA", r"E[A-H][0-9]", ("EA", "EB", "EC"), 14,
            ("JOSE", "ANTONIO", "CARLOS", "JAVIER", "MANUEL", "PACO"),
            ("MADRID", "BARCELONA", "VALENCIA", "SEVILLA", "BILBAO", "MALAGA")),
    Country("PA", r"P[A-I][0-9]", ("PA", "PD", "PE"), 14,
            ("JAN", "PIET", "HENK", "KEES", "WILLEM", "BAS"),
            ("AMSTERDAM", "UTRECHT", "ROTTERDAM", "GRONINGEN", "EINDHOVEN")),
    Country("ON", r"O[N-T][0-9]", ("ON",), 14,
            ("LUC", "MARC", "JEF", "DIRK", "PATRICK"),
            ("BRUSSEL", "GENT", "ANTWERPEN", "BRUGGE", "LIEGE")),
    Country("OE", r"OE[0-9]", ("OE",), 15,
            ("FRANZ", "JOSEF", "KARL", "GERHARD", "HERBERT"),
            ("WIEN", "GRAZ", "LINZ", "SALZBURG", "INNSBRUCK", "KLAGENFURT")),
    Country("HB", r"HB9", ("HB9",), 14,
            ("URS", "BEAT", "MARKUS", "RETO", "HANSRUEDI"),
            ("ZUERICH", "BERN", "BASEL", "LUZERN", "CHUR")),
    Country("SP", r"(S[N-R]|3Z)[0-9]", ("SP", "SQ", "SO"), 15,
            ("PIOTR", "TOMASZ", "KRZYSZTOF", "MAREK", "JANUSZ"),
            ("WARSZAWA", "KRAKOW", "GDANSK", "POZNAN", "WROCLAW", "LODZ")),
    Country("OK", r"O[KL][0-9]", ("OK", "OL"), 15,
            ("JIRI", "PAVEL", "JAN", "PETR", "KAREL"),
            ("PRAHA", "BRNO", "OSTRAVA", "PLZEN", "OLOMOUC")),
    Country("OZ", r"OZ[0-9]", ("OZ",), 14,
            ("LARS", "SOREN", "JENS", "NIELS", "HENRIK"),
            ("KOBENHAVN", "ODENSE", "AARHUS", "AALBORG", "ESBJERG")),
    Country("SM", r"(S[A-M]|[78]S)[0-9]", ("SM", "SA"), 14,
            ("ANDERS", "LARS", "BENGT", "STEFAN", "OLLE"),
            ("STOCKHOLM", "GOTEBORG", "MALMO", "UPPSALA", "KIRUNA")),
    Country("LA", r"L[A-N][0-9]", ("LA", "LB"), 14,
            ("OLE", "KNUT", "ARNE", "BJORN", "SVEIN"),
            ("OSLO", "BERGEN", "TRONDHEIM", "STAVANGER", "TROMSO")),
    Country("OH", r"O[F-I][0-9]", ("OH",), 15,
            ("JUHA", "PEKKA", "MATTI", "KARI", "JARI"),
            ("HELSINKI", "TAMPERE", "OULU", "TURKU", "ESPOO")),
    Country("W", r"([KNW][A-Z]?|A[A-L])[0-9]", ("W", "K", "N", "KB", "WA", "AA"), 5,
            ("BOB", "JIM", "BILL", "TOM", "JOE", "DAVE", "RICK", "GARY", "STEVE"),
            ("BOSTON", "DENVER", "DALLAS", "SEATTLE", "CHICAGO", "ATLANTA", "PHOENIX", "MIAMI")),
    Country("JA", r"(J[A-S]|7[J-N])[0-9]", ("JA", "JH", "JR", "JE"), 25,
            ("HIRO", "TAKA", "KEN", "YOSHI", "MASA"),
            ("TOKYO", "OSAKA", "NAGOYA", "SAPPORO", "KYOTO", "SENDAI")),
    Country("UA", r"(R[A-Z]?|U[A-I])[0-9]", ("RA", "UA", "RN", "RX"), 16,
            ("SERGEI", "ALEX", "VLAD", "IGOR", "YURI", "OLEG"),
            ("MOSKVA", "KAZAN", "SAMARA", "OMSK", "NOVOSIBIRSK", "SOCHI")),
]

RIGS = ("IC7300", "IC7610", "IC705", "IC7851", "FT991", "FTDX10", "FTDX101", "FT817", "FT710",
        "K3", "K4", "KX2", "KX3", "TS590", "TS890", "FLEX6600", "HOMEBREW")
POWERS = ("5W", "10W", "50W", "100W", "100W", "100W", "400W", "750W")
ANTENNAS = ("DIPOLE", "VERTICAL", "YAGI", "GP", "LOOP", "WINDOM", "EFHW", "HEXBEAM", "LW")
WEATHER = ("SUNNY", "CLOUDY", "RAIN", "FOG", "WINDY", "CLEAR", "SNOW")
# Rapporte mit grober Häufigkeit (599 ist in der Praxis mit Abstand am häufigsten).
RST_WEIGHTS = {"599": 30, "589": 12, "579": 15, "569": 8, "559": 10, "549": 5, "449": 4, "339": 2}

# ARRL DX: US-Stationen senden ihren Bundesstaat (nach Rufzeichenbezirk),
# alle anderen ihre Leistung.
US_STATES = {
    "1": ("MA", "CT", "ME", "NH", "RI", "VT"), "2": ("NY", "NJ"), "3": ("PA", "MD", "DE"),
    "4": ("FL", "GA", "NC", "SC", "VA", "TN", "AL", "KY"), "5": ("TX", "OK", "LA", "AR", "MS", "NM"),
    "6": ("CA",), "7": ("WA", "OR", "AZ", "UT", "NV", "ID", "MT", "WY"), "8": ("OH", "MI", "WV"),
    "9": ("IL", "IN", "WI"), "0": ("CO", "MN", "IA", "MO", "KS", "NE", "ND", "SD"),
}
ARRL_POWERS = ("KW", "KW", "1TT", "1TT", "5TT", "4TT", "100", "5T")
# IARU HF: ITU-Zonen (für USA/Russland je nach Ziffer, siehe itu_zone).
ITU_ZONES = {
    "DL": 28, "F": 27, "GM": 27, "G": 27, "I": 28, "EA": 37, "PA": 27, "ON": 27, "OE": 28, "HB": 28,
    "SP": 28, "OK": 28, "OZ": 18, "SM": 18, "LA": 18, "OH": 18, "W": 8, "JA": 45, "UA": 29,
}
# HQ-Stationen der IARU-Mitgliedsverbände senden statt der Zone das
# Verbandskürzel (Auswahl).
IARU_HQ_STATIONS = {
    "DA0HQ": "DARC", "TM0HQ": "REF", "HB9HQ": "USKA", "OL9HQ": "CRC", "S50HQ": "ZRS",
    "9A1HQ": "HRS", "LY0HQ": "LRMD",
}
IARU_HQ_RUN_PROBABILITY = 0.25
IARU_HQ_CALLER_PROBABILITY = 0.1
# Buchstaben, mit denen DOKs beginnen (Distrikte des DARC).
DOK_LETTERS = "ABCDEFGHIKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class Station:
    call: str
    name: str
    qth: str
    rig: str
    pwr: str
    ant: str
    wx: str
    age: int
    licensed: int


@dataclass(frozen=True)
class Qso:
    kind: str                # Schlüssel aus QSO_TYPES
    calls: tuple             # Rufzeichen je Stationsindex (0 = ruft CQ bzw. Run-Station)
    transmissions: tuple     # ((Stationsindex, Text), …)
    quiz_columns: tuple      # Spaltenüberschriften der Abfrage
    quiz_rows: tuple         # ((Zeilenname, (Zelle, …)), …); Zelle = (Erwartet, Art) oder None
    # Pile-up: weitere Stationen, die gleichzeitig mit einem Durchgang rufen,
    # aber nicht gearbeitet werden: ((Durchgangsindex, ((Station, Text,
    # Verzögerung in s), …)), …). Ihre Stationsindizes folgen in `calls` nach
    # den gearbeiteten Stationen.
    pileups: tuple = ()

    @property
    def is_contest(self) -> bool:
        return self.kind != RAGCHEW

    def text(self) -> str:
        return " ".join(text for _, text in self.transmissions)


_call_pool = None  # [(Rufzeichen, Country)], beim ersten Gebrauch geladen


def _country_of(call: str):
    for country in COUNTRIES:
        if re.match(country.pattern, call):
            return country
    return None


def _load_pool():
    global _call_pool
    if _call_pool is None:
        calls, _release = load_callsigns()
        _call_pool = [(c, country) for c in calls if "/" not in c and (country := _country_of(c))]
    return _call_pool


def _generated_call(country: Country) -> str:
    prefix = random.choice(country.sample_prefixes)
    suffix_len = random.choices([1, 2, 3], weights=[1, 4, 5])[0]
    suffix = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(suffix_len))
    digit = "" if prefix[-1].isdigit() else random.choice("0123456789")
    return f"{prefix}{digit}{suffix}"


def _pick_call(exclude=(), countries=None):
    """Zufälliges Rufzeichen, optional nur aus bestimmten Ländern (Keys)."""
    pool = [(c, k) for c, k in _load_pool() if countries is None or k.key in countries]
    candidates = [k for k in COUNTRIES if countries is None or k.key in countries]
    while True:
        if pool:
            call, country = random.choice(pool)
        else:
            country = random.choice(candidates)
            call = _generated_call(country)
        if call not in exclude:
            return call, country


def _district(call: str) -> str:
    return next((ch for ch in call if ch.isdigit()), "1")


def cq_zone(call: str, country: Country) -> int:
    district = _district(call)
    if country.key == "W":
        if call.startswith(("KH6", "NH6", "WH6", "AH6")):
            return 31
        if call.startswith(("KL7", "NL7", "WL7", "AL7")):
            return 1
        return {"6": 3, "7": 3, "5": 4, "9": 4, "0": 4}.get(district, 5)
    if country.key == "UA":
        return {"9": 17, "0": 19}.get(district, 16)
    return country.zone


def itu_zone(call: str, country: Country) -> int:
    district = _district(call)
    if country.key == "W":
        if call.startswith(("KH6", "NH6", "WH6", "AH6")):
            return 61
        if call.startswith(("KL7", "NL7", "WL7", "AL7")):
            return 1
        return {"6": 6, "7": 6, "5": 7, "9": 7, "0": 7}.get(district, 8)
    if country.key == "UA":
        return {"9": 30, "0": 32}.get(district, 29)
    return ITU_ZONES[country.key]


def _make_station(exclude=()) -> Station:
    call, country = _pick_call(exclude)
    wx = random.choice(WEATHER)
    temp = random.randint(0, 3) if wx == "SNOW" else random.randint(5, 30)
    age = random.randint(18, 85)
    licensed = random.randint(max(datetime.now().year - (age - 14), 1950), datetime.now().year - 1)
    return Station(
        call=call, name=random.choice(country.names), qth=random.choice(country.qths),
        rig=random.choice(RIGS), pwr=random.choice(POWERS), ant=random.choice(ANTENNAS),
        wx=f"{wx} TEMP {temp}C", age=age, licensed=licensed,
    )


def _pick_rst() -> str:
    return random.choices(list(RST_WEIGHTS), weights=list(RST_WEIGHTS.values()))[0]


def _greeting() -> str:
    hour = datetime.now().hour
    return "GM" if hour < 12 else "GA" if hour < 18 else "GE"


def _over() -> str:
    """Ende eines Durchgangs an eine bestimmte Station: KN (nur die
    Gegenstation soll antworten) oder einfach K."""
    return KN if random.random() < 0.6 else "K"


def _repeat(word: str, times: int) -> str:
    return " ".join([word] * times)


def _check(txs) -> None:
    for _, text in txs:
        assert all(ch == " " or ch in MORSE_CODE for ch in text), text


def generate_qso(kind: str = RAGCHEW, length: int = LENGTH_NORMAL) -> Qso:
    if kind == RAGCHEW:
        return _generate_ragchew(length)
    return _generate_contest(kind, CONTEST_QSO_COUNTS[length])


# --- Normales QSO -------------------------------------------------------------
def _station_info(st: Station, length: int) -> list:
    """Rig/Wetter/… einer Station, je nach QSO-Länge."""
    parts = []
    if length >= LENGTH_NORMAL:
        rig = f"RIG {st.rig} PWR {st.pwr}"
        if length >= LENGTH_LONG:
            rig += f" ANT {st.ant}"
        parts += [rig, "=", f"WX {st.wx}", "="]
    if length >= LENGTH_LONG:
        parts += [f"AGE {st.age} ES HAM SINCE {st.licensed}", "="]
    return parts


def _generate_ragchew(length: int) -> Qso:
    a = _make_station()
    b = _make_station(exclude={a.call})
    rst_a, rst_b = _pick_rst(), _pick_rst()
    greet = _greeting()

    txs = [
        (0, f"{_repeat('CQ', random.choice([2, 3]))} DE {_repeat(a.call, random.choice([2, 3]))} K"),
        (1, f"{a.call} DE {_repeat(b.call, 2)} K"),
    ]

    opening = "TNX FER CALL" if length == LENGTH_SHORT else f"{greet} DR OM ES TNX FER CALL"
    tx = [f"{b.call} DE {a.call}", opening, "=",
          f"UR RST {rst_a} {rst_a}", "=", f"NAME {_repeat(a.name, 2)}", "=", f"QTH {_repeat(a.qth, 2)}", "=",
          "HW?", "+", f"{b.call} DE {a.call} {_over()}"]
    txs.append((0, " ".join(tx)))

    tx = [f"{a.call} DE {b.call} R", f"{greet} {a.name} TNX FER RPRT", "=",
          f"UR RST {rst_b} {rst_b}", "=", f"NAME {_repeat(b.name, 2)}", "=", f"QTH {_repeat(b.qth, 2)}", "="]
    tx += _station_info(b, length)
    if length == LENGTH_SHORT:
        tx += ["TNX QSO 73 ES GL", SK, f"{a.call} DE {b.call}"]
    else:
        if length >= LENGTH_LONG:
            tx += ["QSL VIA BURO", "="]
        tx += ["HW?", "+", f"{a.call} DE {b.call} {_over()}"]
    txs.append((1, " ".join(tx)))

    if length == LENGTH_SHORT:
        txs.append((0, f"{b.call} DE {a.call} R TNX {b.name} 73 GL TU E E"))
    else:
        # Schneller Wechsel ohne Rufzeichen: BK.
        opening = f"{BK} R R" if random.random() < 0.3 else f"{b.call} DE {a.call} R R"
        tx = [f"{opening} TNX {b.name} FER INFO", "="]
        tx += _station_info(a, length)
        if length >= LENGTH_LONG:
            tx += ["QSL OK VIA BURO", "="]
        tx += ["TNX FER NICE QSO ES HPE CUAGN", "=", "73 ES GL", SK, f"{b.call} DE {a.call}"]
        txs.append((0, " ".join(tx)))
        txs.append((1, f"{a.call} DE {b.call} R TNX {a.name} FER QSO 73 ES GD DX {SK} {a.call} DE {b.call} TU E E"))

    _check(txs)
    return Qso(
        kind=RAGCHEW, calls=(a.call, b.call), transmissions=tuple(txs),
        quiz_columns=("Station 1 (CQ)", "Station 2"),
        quiz_rows=(
            ("Rufzeichen", ((a.call, TEXT), (b.call, TEXT))),
            ("Name", ((a.name, TEXT), (b.name, TEXT))),
            ("QTH", ((a.qth, TEXT), (b.qth, TEXT))),
            ("Rapport (gibt)", ((rst_a, RST), (rst_b, RST))),
        ),
    )


# --- Contest ------------------------------------------------------------------
def _cut_serial(number: int) -> str:
    """Seriennummer wie im Contest üblich: meist dreistellig mit T für
    führende Nullen (7 -> TT7), manchmal einfach als Zahl."""
    if number >= 100 or random.random() < 0.3:
        return str(number)
    return f"{number:03d}".replace("0", "T", 3 - len(str(number)))


def _contest_rst() -> str:
    return "5NN" if random.random() < 0.9 else "599"


class _Exchange:
    """Liefert den Austausch einer Station im jeweiligen Contest; Seriennummern
    zählen pro Station hoch."""

    def __init__(self, kind: str, call: str, country: Country, first_serial: int):
        self.kind = kind
        self.call = call
        self.country = country
        self.serial = first_serial
        if kind == "wag" and country.key == "DL":
            self.fixed = (f"{random.choice(DOK_LETTERS)}{random.randint(1, 60):02d}", TEXT)
        elif kind == "cqww":
            self.fixed = (str(cq_zone(call, country)), NUMBER)
        elif kind == "arrldx" and country.key == "W":
            self.fixed = (random.choice(US_STATES[_district(call)]), TEXT)
        elif kind == "arrldx":
            self.fixed = (random.choice(ARRL_POWERS), NUMBER)
        elif kind == "iaru" and call in IARU_HQ_STATIONS:
            self.fixed = (IARU_HQ_STATIONS[call], TEXT)
        elif kind == "iaru":
            self.fixed = (str(itu_zone(call, country)), NUMBER)
        else:  # WPX, WAG ohne DOK
            self.fixed = None

    def next(self):
        if self.fixed is not None:
            return self.fixed
        value = (_cut_serial(self.serial), NUMBER)
        self.serial += 1
        return value


def _pick_contest_call(kind: str, exclude, countries, hq_probability: float):
    """Wie _pick_call; im IARU HF Contest ist es mit `hq_probability` eine
    HQ-Station."""
    if kind == "iaru" and random.random() < hq_probability:
        free = [c for c in IARU_HQ_STATIONS if c not in exclude]
        if free:
            call = random.choice(free)
            return call, _country_of(call)
    return _pick_call(exclude, countries)


def _generate_contest(kind: str, count: int) -> Qso:
    # WAG: DL arbeitet alle; ARRL DX: der Rest der Welt arbeitet W/VE.
    run_countries = {"wag": {"DL"}, "arrldx": {c.key for c in COUNTRIES} - {"W"}}.get(kind)
    caller_countries = {"arrldx": {"W"}}.get(kind)
    test = "WAG" if kind == "wag" else "TEST"

    run, run_country = _pick_contest_call(kind, (), run_countries, IARU_HQ_RUN_PROBABILITY)
    run_exchange = _Exchange(kind, run, run_country, random.randint(1, 600))
    used = {run}
    txs = []

    def send(station, text):
        # Folgt z. B. auf „TU“ direkt ein neuer CQ-Ruf, ist das ein Durchgang.
        if txs and txs[-1][0] == station:
            txs[-1] = (station, f"{txs[-1][1]} {text}")
        else:
            txs.append((station, text))
    # Wechselt der Austausch der Run-Station (Seriennummer), wird er nicht abgefragt.
    rows = [("Run-Station", ((run, TEXT), run_exchange.fixed))]

    extra_calls, pileups = [], []
    for i in range(count):
        station = i + 1
        call, country = _pick_contest_call(kind, used, caller_countries, IARU_HQ_CALLER_PROBABILITY)
        used.add(call)
        exchange, exchange_kind = _Exchange(kind, call, country, random.randint(1, 1500)).next()

        if i == 0 or random.random() < 0.35:
            send(0, random.choice([
                f"CQ {test} {run} {run}", f"CQ {run} {run} {test}", f"CQ {test} {run}", f"{test} {run}",
            ]))
        send(station, call if random.random() < 0.7 else f"{call} {call}")
        if random.random() < PILEUP_PROBABILITY:
            others = []
            for _ in range(random.randint(*PILEUP_EXTRA_CALLERS)):
                other, _ = _pick_contest_call(kind, used, caller_countries, IARU_HQ_CALLER_PROBABILITY)
                used.add(other)
                extra_calls.append(other)
                others.append((count + len(extra_calls), other if random.random() < 0.6 else f"{other} {other}",
                               round(random.uniform(0.0, 0.5), 2)))
            pileups.append((len(txs) - 1, tuple(others)))
        if len(call) >= 4 and random.random() < 0.2:
            # Nur einen Teil des Rufzeichens aufgenommen: Rückfrage.
            send(0, f"{call[:random.randint(3, len(call) - 1)]}?")
            send(station, f"{call} {call}")
        send(0, f"{call} {_contest_rst()} {run_exchange.next()[0]}")
        if random.random() < 0.15:
            send(station, f"{_contest_rst()} {exchange}")
            send(0, random.choice(["AGN?", "NR?", "?"]))
            send(station, f"{exchange} {exchange}")
        else:
            send(station, random.choice([
                f"TU {_contest_rst()} {exchange}", f"{_contest_rst()} {exchange}", f"R {_contest_rst()} {exchange}",
            ]))
        send(0, random.choice(["TU", f"TU {run}", f"TU {run}", f"TU {run} {test}", "R TU"]))
        rows.append((f"QSO {station}", ((call, TEXT), (exchange, exchange_kind))))

    _check(txs)
    return Qso(
        kind=kind, calls=(run, *(cells[0][0] for _, cells in rows[1:]), *extra_calls),
        pileups=tuple(pileups),
        transmissions=tuple(txs), quiz_columns=("Rufzeichen", "Austausch"), quiz_rows=tuple(rows),
    )


# --- Für den aktiven Contest-Modus -----------------------------------------------
def cut_number(number: int) -> str:
    """Seriennummer dreistellig mit T für führende Nullen (7 -> TT7), wie
    Contest-Software sie sendet; ab 100 unverändert."""
    return str(number) if number >= 100 else f"{number:03d}".replace("0", "T", 3 - len(str(number)))


def contest_test_word(kind: str) -> str:
    return "WAG" if kind == "wag" else "TEST"


def uses_serial(kind: str, my_call: str) -> bool:
    """Sendet man in diesem Contest eine laufende Nummer statt eines festen
    Austauschs?"""
    country = _country_of(my_call)
    return kind == "wpx" or (kind == "wag" and (country is None or country.key != "DL"))


def default_my_exchange(kind: str, my_call: str) -> str:
    """Vorschlag für den eigenen Austausch; leer, wenn er sich nicht aus dem
    Rufzeichen ableiten lässt (z. B. DOK im WAG) oder eine Nummer ist."""
    country = _country_of(my_call)
    if uses_serial(kind, my_call) or country is None:
        return ""
    if kind == "cqww":
        return str(cq_zone(my_call, country))
    if kind == "iaru":
        return IARU_HQ_STATIONS.get(my_call) or str(itu_zone(my_call, country))
    if kind == "arrldx":
        return US_STATES[_district(my_call)][0] if country.key == "W" else "100"
    return ""  # WAG in DL: DOK


def contest_caller(kind: str, my_call: str, exclude):
    """Ein Anrufer für die eigene Run-Station: (Rufzeichen, Austausch, Art des
    Austauschs für den Vergleich)."""
    my_country = _country_of(my_call)
    countries = None
    if kind == "arrldx":
        # W/VE arbeiten den Rest der Welt und umgekehrt.
        countries = ({c.key for c in COUNTRIES} - {"W"}) if my_country and my_country.key == "W" else {"W"}
    call, country = _pick_contest_call(kind, set(exclude) | {my_call}, countries, IARU_HQ_CALLER_PROBABILITY)
    exchange, exchange_kind = _Exchange(kind, call, country, random.randint(1, 1500)).next()
    return call, exchange, exchange_kind
