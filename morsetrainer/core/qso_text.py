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
import math
import random
import re
from dataclasses import dataclass, field
from datetime import datetime

from morsetrainer.modes.callsign_mode import load_callsigns
from morsetrainer.core.morse import BK, KN, MORSE_CODE, SK
from morsetrainer.i18n import N_, tr

# Kurz: nur Rapport/Name/QTH; Normal: + Rig, Leistung, Wetter;
# Lang: + Antenne, Alter, lizenziert seit, QSL-Info.
# Im Contest bestimmt die Länge die Anzahl der QSOs im Run.
LENGTH_SHORT, LENGTH_NORMAL, LENGTH_LONG = 0, 1, 2
# QSOs je Contest-Run und Länge; zufällig aus der Spanne, damit man die
# Anzahl (eine Kopfhör-Frage) nicht aus der Einstellung ablesen kann.
CONTEST_QSO_RANGES = ((2, 4), (4, 6), (7, 9))
# Anteil der Anrufe, bei denen weitere Stationen gleichzeitig rufen, und
# wie viele.
PILEUP_PROBABILITY = 0.45  # Stufe „oft“; Standard sind keine Pile-ups
PILEUP_EXTRA_CALLERS = (1, 2)

RAGCHEW = "ragchew"
# Beschriftungen deutsch (so auch gespeichert); übersetzt wird die Anzeige.
QSO_TYPES = {
    RAGCHEW: N_("Normales QSO"),
    "cqww": N_("Contest: CQ WW (Zone)"),
    "wpx": N_("Contest: CQ WPX (Nummer)"),
    "wag": N_("Contest: WAG (DOK)"),
    "arrldx": N_("Contest: ARRL DX (Staat/Leistung)"),
    "iaru": N_("Contest: IARU HF (ITU-Zone/HQ)"),
}
# Im Reiter Contest ohne den Vorsatz „Contest:“ (steht schon davor).
CONTEST_NAMES = {
    "cqww": N_("CQ WW (Zone)"),
    "wpx": N_("CQ WPX (Nummer)"),
    "wag": N_("WAG (DOK)"),
    "arrldx": N_("ARRL DX (Staat/Leistung)"),
    "iaru": N_("IARU HF (ITU-Zone/HQ)"),
}

# Arten, wie ein Abfragefeld verglichen wird (siehe qso_mode.normalize).
TEXT, RST, NUMBER = "text", "rst", "number"
# DOK (WAG): „A5“ und „A05“ sind derselbe; Leistung: „100W“ und „100“.
DOK, POWER = "dok", "power"


@dataclass(frozen=True)
class Country:
    """Ein Land für erzeugte QSOs: Rufzeichenmuster, Präfixe für erfundene
    Rufzeichen, CQ-Zone sowie Namen und QTHs zur Auswahl."""
    key: str
    pattern: str            # Regex auf den Rufzeichenanfang
    sample_prefixes: tuple  # für erzeugte Rufzeichen, wenn callsigns.scp fehlt
    zone: int               # CQ-Zone (je Ziffer in USA, Kanada, Russland, Australien, siehe cq_zone);
                            # bei Mexiko, China, Brasilien, Kasachstan u. a. nur eine Näherung für das ganze Land
    names: tuple
    qths: tuple
    # QTHs je Rufzeichenziffer, wo die Ziffer das Bundesland festlegt (OE);
    # fehlt die Ziffer hier, gelten `qths`.
    qths_by_district: dict = field(default=None, hash=False, compare=False)
    # Ziffern, die für erzeugte Rufzeichen infrage kommen (VK0/VK9 und VE0 sind andere Gebiete).
    digits: str = "0123456789"


COUNTRIES = [
    Country("DL", r"D[A-R][0-9]", ("DL", "DK", "DJ", "DO", "DF", "DG"), 14,
            ("HANS", "PETER", "KLAUS", "UWE", "JENS", "FRANK", "MICHAEL", "ANDREAS", "THOMAS",
             "WOLFGANG", "JUERGEN", "STEFAN", "SABINE", "ANJA", "DIRK", "HOLGER"),
            ("BERLIN", "HAMBURG", "MUENCHEN", "KOELN", "OELDE", "MUENSTER", "DRESDEN", "LEIPZIG",
             "BREMEN", "HANNOVER", "STUTTGART", "KIEL", "ROSTOCK", "BIELEFELD", "KASSEL", "ERFURT")),
    Country("F", r"(F|T[HMOPQVX]|H[W-Y])[0-9]", ("F",), 14,
            ("JEAN", "PIERRE", "MICHEL", "ALAIN", "PHILIPPE", "PATRICK", "BERNARD"),
            ("PARIS", "LYON", "MARSEILLE", "TOULOUSE", "NANTES", "BORDEAUX", "LILLE", "DIJON")),
    Country("GM", r"(G[MS]|M[MS]|2[MA])[0-9]", ("GM", "MM", "GS"), 14,
            ("ANGUS", "IAN", "JOHN", "DOUGLAS", "ALAN"),
            ("EDINBURGH", "GLASGOW", "ABERDEEN", "DUNDEE", "INVERNESS")),
    Country("G", r"(G|M|2E)[0-9]", ("G", "M"), 14,
            ("JOHN", "DAVID", "PAUL", "MIKE", "STEVE", "CHRIS", "RICHARD", "PETE"),
            ("LONDON", "LEEDS", "YORK", "BRISTOL", "LEICESTER", "OXFORD", "NORWICH", "EXETER")),
    Country("I", r"I[A-Z]?[0-9]", ("I", "IK", "IZ", "IW"), 15,
            ("MARCO", "LUCA", "GIOVANNI", "PAOLO", "FRANCO", "GIUSEPPE"),
            ("ROMA", "MILANO", "TORINO", "NAPOLI", "BOLOGNA", "FIRENZE", "GENOVA")),
    Country("EA", r"(E[A-H]|A[M-O])[0-9]", ("EA", "EB", "EC"), 14,
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
            ("WIEN", "GRAZ", "LINZ", "SALZBURG", "INNSBRUCK", "KLAGENFURT"),
            # OE1 Wien, 2 Salzburg, 3 Niederösterreich, 4 Burgenland, 5 Oberösterreich,
            # 6 Steiermark, 7 Tirol, 8 Kärnten, 9 Vorarlberg.
            {"1": ("WIEN",), "2": ("SALZBURG", "HALLEIN"),
             "3": ("ST POELTEN", "WIENER NEUSTADT", "KREMS", "AMSTETTEN"),
             "4": ("EISENSTADT", "OBERWART"), "5": ("LINZ", "WELS", "STEYR"),
             "6": ("GRAZ", "LEOBEN", "KAPFENBERG"), "7": ("INNSBRUCK", "KUFSTEIN", "LIENZ"),
             "8": ("KLAGENFURT", "VILLACH", "SPITTAL"), "9": ("BREGENZ", "DORNBIRN", "FELDKIRCH")},
            digits="123456789"),
    Country("HB", r"(HB[039]|HE[0-9])", ("HB9",), 14,
            ("URS", "BEAT", "MARKUS", "RETO", "HANSRUEDI"),
            ("ZUERICH", "BERN", "BASEL", "LUZERN", "CHUR")),
    Country("SP", r"(S[N-R]|3Z|HF)[0-9]", ("SP", "SQ", "SO"), 15,
            ("PIOTR", "TOMASZ", "KRZYSZTOF", "MAREK", "JANUSZ"),
            ("WARSZAWA", "KRAKOW", "GDANSK", "POZNAN", "WROCLAW", "LODZ")),
    Country("OK", r"O[KL][0-9]", ("OK", "OL"), 15,
            ("JIRI", "PAVEL", "JAN", "PETR", "KAREL"),
            ("PRAHA", "BRNO", "OSTRAVA", "PLZEN", "OLOMOUC")),
    Country("OZ", r"(OZ|OU|OV|5[PQ])[0-9]", ("OZ",), 14,
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
    Country("JA", r"(J[A-S]|[78][J-N])[0-9]", ("JA", "JH", "JR", "JE"), 25,
            ("HIRO", "TAKA", "KEN", "YOSHI", "MASA"),
            ("TOKYO", "OSAKA", "NAGOYA", "SAPPORO", "KYOTO", "SENDAI")),
    Country("UR", r"(U[R-Z]|EM|EN|EO)[0-9]", ("UR", "UT", "UW", "EM"), 16,
            ("ANDRIY", "SERHIY", "OLEKSANDR", "YURIY", "VOLODYMYR"),
            ("KYIV", "KHARKIV", "ODESA", "LVIV", "DNIPRO")),
    Country("UA", r"(R[A-Z]?|U[A-I])[0-9]", ("RA", "UA", "RN", "RX"), 16,
            ("SERGEI", "ALEX", "VLAD", "IGOR", "YURI", "OLEG"),
            ("MOSKVA", "KAZAN", "SAMARA", "OMSK", "NOVOSIBIRSK", "SOCHI")),
    Country("ZS", r"(Z[R-U]|H5|S[48]|V9)[0-9]", ("ZS", "ZR"), 38,
            ("JOHANN", "PIETER", "JAN", "JOHAN", "FRANS"),
            ("JOHANNESBURG", "CAPE TOWN", "DURBAN", "PRETORIA", "PORT ELIZABETH")),
    Country("VK", r"(V[H-N]|AX)[0-9]", ("VK", "VH", "VL"), 30,
            ("JOHN", "PETER", "DAVID", "MICHAEL", "ANDREW"),
            ("SYDNEY", "MELBOURNE", "BRISBANE", "PERTH", "ADELAIDE"),
            {"1": ("CANBERRA",), "2": ("SYDNEY", "NEWCASTLE"), "3": ("MELBOURNE", "GEELONG"),
             "4": ("BRISBANE", "CAIRNS"), "5": ("ADELAIDE",), "6": ("PERTH", "BUNBURY"),
             "7": ("HOBART", "LAUNCESTON"), "8": ("DARWIN",)}, digits="12345678"),
    Country("ZL", r"Z[K-M][0-9]", ("ZL", "ZM"), 32,
            ("GRAHAM", "PETER", "JOHN", "DAVID", "ROSS"),
            ("AUCKLAND", "WELLINGTON", "CHRISTCHURCH", "DUNEDIN", "HAMILTON")),
    Country("PY", r"(P[P-Y]|Z[V-Z])[0-9]", ("PY", "PU", "PT", "PP"), 11,
            ("CARLOS", "JOSE", "PAULO", "LUIZ", "MARCOS", "RAFAEL", "BRUNO"),
            ("SAO PAULO", "RIO DE JANEIRO", "BRASILIA", "SALVADOR", "BELO HORIZONTE",
             "RECIFE", "CURITIBA", "FORTALEZA", "MANAUS", "PORTO ALEGRE")),
    Country("CE", r"(C[A-E]|XQ|XR|3G)[0-9]", ("CE", "CA", "CB", "CD", "XQ", "XR"), 12,
            ("JUAN", "CARLOS", "PEDRO", "JOSE", "LUIS", "RODRIGO", "MATIAS", "FELIPE"),
            ("SANTIAGO", "VALPARAISO", "CONCEPCION", "LA SERENA", "ANTOFAGASTA",
             "VALDIVIA", "TEMUCO", "IQUIQUE", "PUERTO MONTT")),
    Country("HA", r"H[AG][0-9]", ("HA", "HG"), 15,
            ("ZOLTAN", "LASZLO", "GYULA", "ISTVAN", "PETER", "FERENC"),
            ("BUDAPEST", "DEBRECEN", "SZEGED", "MISKOLC", "PECS", "GYOR")),
    Country("OM", r"OM[0-9]", ("OM",), 15,
            ("MILAN", "JOZEF", "LADISLAV", "PETER", "STEFAN"),
            ("BRATISLAVA", "KOSICE", "ZILINA", "NITRA", "BANSKA BYSTRICA")),
    Country("YL", r"YL[0-9]", ("YL",), 15,
            ("JANIS", "ANDRIS", "GUNARS", "PETERIS", "VILNIS"),
            ("RIGA", "DAUGAVPILS", "LIEPAJA", "JELGAVA", "VENTSPILS")),
    Country("LY", r"LY[0-9]", ("LY",), 15,
            ("JONAS", "ANTANAS", "PETRAS", "VIDAS", "GIEDRIUS"),
            ("VILNIUS", "KAUNAS", "KLAIPEDA", "SIAULIAI", "PANEVEZYS")),
    Country("ES", r"ES[0-9]", ("ES",), 15,
            ("JAAN", "PEEP", "MARGUS", "TIIT", "ANDRES"),
            ("TALLINN", "TARTU", "PARNU", "NARVA", "KARDLA")),
    Country("GI", r"(G|M|2)I[0-9]", ("GI", "MI"), 14,
            ("SEAMUS", "IAN", "STEPHEN", "DAVID", "PADRAIG"),
            ("BELFAST", "DERRY", "LISBURN", "NEWRY", "BANGOR")),
    Country("EI", r"E[I-J][0-9]", ("EI", "EJ"), 14,
            ("SEAN", "PATRICK", "MICHAEL", "LIAM", "DECLAN", "BRENDAN"),
            ("DUBLIN", "CORK", "LIMERICK", "GALWAY", "WATERFORD", "SLIGO")),
    Country("GW", r"(G|M|2)[CW][0-9]", ("GW", "MW", "GC"), 14,
            ("DYLAN", "OWEN", "RHYS", "GARETH", "EVAN"),
            ("CARDIFF", "SWANSEA", "NEWPORT", "BANGOR", "ABERYSTWYTH")),
    Country("TA", r"T[A-C][0-9]", ("TA", "TC"), 20,
            ("MEHMET", "AHMET", "MUSTAFA", "ALI", "HASAN", "OSMAN"),
            ("ANKARA", "ISTANBUL", "IZMIR", "ADANA", "BURSA", "ANTALYA")),
    Country("CT", r"C[Q-U][0-9]", ("CT", "CS"), 14,
            ("JOAO", "ANTONIO", "MANUEL", "FERNANDO", "JOAQUIM"),
            ("LISBOA", "PORTO", "BRAGA", "COIMBRA", "FARO", "AVEIRO")),
    Country("9A", r"9A[0-9]", ("9A",), 15,
            ("IVAN", "MARKO", "ZORAN", "DAMIR", "GORAN"),
            ("ZAGREB", "SPLIT", "RIJEKA", "OSIJEK", "ZADAR")),
    Country("S5", r"S5[0-9]", ("S51", "S52", "S53", "S57"), 15,
            ("JANEZ", "MATJAZ", "FRANCE", "BOJAN", "TOMAZ"),
            ("LJUBLJANA", "MARIBOR", "CELJE", "KRANJ", "KOPER")),
    Country("YO", r"Y[O-R][0-9]", ("YO", "YR"), 20,
            ("ION", "VASILE", "GHEORGHE", "MIHAI", "ANDREI"),
            ("BUCURESTI", "CLUJ", "TIMISOARA", "IASI", "BRASOV", "CRAIOVA")),
    Country("YU", r"Y[TU][0-9]", ("YT", "YU"), 15,
            ("MILAN", "ZORAN", "GORAN", "DRAGAN", "NEBOJSA"),
            ("BEOGRAD", "NOVI SAD", "NIS", "KRAGUJEVAC", "SUBOTICA")),
    Country("LZ", r"LZ[0-9]", ("LZ",), 20,
            ("GEORGI", "IVAN", "DIMITAR", "PETAR", "NIKOLAY"),
            ("SOFIA", "PLOVDIV", "VARNA", "BURGAS", "RUSE")),
    Country("SV", r"(S[V-Z]|J4)[0-9]", ("SV", "SZ"), 20,
            ("NIKOS", "GIORGOS", "KOSTAS", "DIMITRIS", "YANNIS"),
            ("ATHINA", "THESSALONIKI", "PATRA", "HERAKLION", "VOLOS")),
    Country("LX", r"LX[0-9]", ("LX",), 14,
            ("MARC", "JEAN", "ROMAIN", "PAUL", "CLAUDE"),
            ("LUXEMBOURG", "ESCH", "DIFFERDANGE", "DUDELANGE", "ETTELBRUCK")),
    Country("LU", r"(L[O-W]|A[YZ])[0-9]", ("LU", "LW"), 13,
            ("JUAN", "CARLOS", "ROBERTO", "JORGE", "DIEGO", "MARCELO"),
            ("BUENOS AIRES", "CORDOBA", "ROSARIO", "MENDOZA", "LA PLATA")),
    Country("HK", r"(H[JK]|5[JK])[0-9]", ("HK", "HJ"), 9,
            ("CARLOS", "ANDRES", "JUAN", "LUIS", "MAURICIO"),
            ("BOGOTA", "MEDELLIN", "CALI", "BARRANQUILLA", "CARTAGENA")),
    Country("JW", r"JW[0-9]", ("JW",), 40,
            ("OLAV", "EINAR", "ARNE", "SVEIN", "GEIR"),
            ("LONGYEARBYEN", "NY ALESUND")),
    Country("VE", r"(V[A-G]|VO|V[XY]|C[F-K]|C[YZ]|X[J-O])[0-9]", ("VE", "VA"), 5,
            ("JOHN", "MIKE", "DAVE", "JEAN", "PIERRE", "ANDRE", "BRIAN", "GORD"),
            ("TORONTO", "OTTAWA", "MONTREAL", "VANCOUVER", "CALGARY", "WINNIPEG", "HALIFAX"),
            {"1": ("HALIFAX", "SYDNEY"), "2": ("MONTREAL", "QUEBEC", "GATINEAU"),
             "3": ("TORONTO", "OTTAWA", "LONDON", "HAMILTON"), "4": ("WINNIPEG", "BRANDON"),
             "5": ("REGINA", "SASKATOON"), "6": ("CALGARY", "EDMONTON"),
             "7": ("VANCOUVER", "VICTORIA", "KELOWNA"), "8": ("YELLOWKNIFE",),
             "9": ("FREDERICTON", "SAINT JOHN", "MONCTON")}, digits="123456789"),
    Country("XE", r"(X[A-I]|4[A-C]|6[D-J])[0-9]", ("XE", "XA", "XB", "4A"), 6,
            ("JOSE", "JUAN", "CARLOS", "LUIS", "MIGUEL", "ARMANDO"),
            ("CIUDAD DE MEXICO", "GUADALAJARA", "MONTERREY", "PUEBLA", "TIJUANA", "MERIDA")),
    Country("CO", r"(C[LMO]|T4)[0-9]", ("CO", "CM", "CL"), 8,
            ("JOSE", "PEDRO", "ORLANDO", "RAUL", "ARMANDO"),
            ("LA HABANA", "SANTIAGO", "HOLGUIN", "CAMAGUEY", "MATANZAS")),
    Country("HI", r"HI[0-9]", ("HI",), 8,
            ("JUAN", "PEDRO", "MIGUEL", "RAFAEL", "LUIS"),
            ("SANTO DOMINGO", "SANTIAGO", "PUERTO PLATA", "LA ROMANA", "PUNTA CANA")),
    Country("6Y", r"6Y[0-9]", ("6Y",), 8,
            ("DEVON", "ROY", "WINSTON", "COURTNEY", "ANDREW"),
            ("KINGSTON", "MONTEGO BAY", "OCHO RIOS", "MANDEVILLE", "NEGRIL")),
    Country("TI", r"T[IE][0-9]", ("TI", "TE"), 7,
            ("JOSE", "LUIS", "CARLOS", "MARIO", "ALVARO"),
            ("SAN JOSE", "CARTAGO", "HEREDIA", "LIMON", "ALAJUELA")),
    Country("4X", r"4[XZ][0-9]", ("4X", "4Z"), 20,
            ("YOSSI", "DAVID", "AVI", "MOSHE", "ELI"),
            ("TEL AVIV", "HAIFA", "JERUSALEM", "BEER SHEVA", "NETANYA")),
    Country("VU", r"(V[T-W]|A[T-W]|8[T-Y])[0-9]", ("VU", "AT"), 22,
            ("RAJ", "ANIL", "SUNIL", "VIJAY", "ASHOK"),
            ("DELHI", "MUMBAI", "CHENNAI", "KOLKATA", "BANGALORE", "PUNE")),
    Country("BY", r"B[A-LR-TYZ][0-9]", ("BY", "BD", "BG", "BA"), 24,
            ("LEI", "WEI", "JUN", "TAO", "MING"),
            ("BEIJING", "SHANGHAI", "GUANGZHOU", "CHENGDU", "WUHAN")),
    Country("EW", r"E[U-W][0-9]", ("EW", "EU"), 16,
            ("SERGEI", "ANDREI", "VIKTOR", "VLADIMIR", "DMITRY"),
            ("MINSK", "GOMEL", "BREST", "GRODNO", "VITEBSK")),
    Country("UN", r"U[N-Q][0-9]", ("UN", "UP", "UQ"), 17,
            ("SERGEY", "ALEXANDR", "ERLAN", "ASKAR", "TALGAT"),
            ("ALMATY", "ASTANA", "KARAGANDA", "SHYMKENT", "AKTAU")),
    Country("TF", r"TF[0-9]", ("TF",), 40,
            ("JON", "GUDMUNDUR", "SIGURDUR", "OLAFUR", "MAGNUS"),
            ("REYKJAVIK", "AKUREYRI", "KEFLAVIK", "HAFNARFJORDUR", "EGILSSTADIR")),
    Country("Z3", r"Z3[0-9]", ("Z31", "Z32", "Z33"), 15,
            ("GORAN", "ZORAN", "VLADIMIR", "ALEKSANDAR", "IGOR"),
            ("SKOPJE", "BITOLA", "OHRID", "KUMANOVO", "TETOVO")),
    Country("HL", r"(HL|D[ST]|D[7-9]|6[K-N])[0-9]", ("HL", "DS"), 25,
            ("MINSU", "JIHO", "SUNG", "HYUN", "JUN"),
            ("SEOUL", "BUSAN", "INCHEON", "DAEGU", "DAEJEON")),
    Country("HS", r"(HS|E2)[0-9]", ("HS", "E21"), 26,
            ("SOMCHAI", "SOMSAK", "PRASERT", "ANAN", "WICHAI"),
            ("BANGKOK", "CHIANG MAI", "PHUKET", "KHON KAEN", "PATTAYA")),
    Country("BV", r"B[M-QU-X][0-9]", ("BV", "BX", "BU"), 24,
            ("WEI", "MING", "KUO", "LIN", "CHEN"),
            ("TAIPEI", "TAICHUNG", "KAOHSIUNG", "TAINAN", "HSINCHU")),
    Country("YB", r"(Y[B-H]|P[K-O]|[78][A-I])[0-9]", ("YB", "YC", "YD", "PK"), 28,
            ("BUDI", "AGUS", "HENDRA", "JOKO", "WAHYU"),
            ("JAKARTA", "SURABAYA", "BANDUNG", "MEDAN", "SEMARANG")),
    Country("DU", r"(D[U-Z]|4[D-I])[0-9]", ("DU", "DV", "4F"), 27,
            ("JOSE", "RICARDO", "ROMEO", "ARNEL", "RENATO"),
            ("MANILA", "CEBU", "DAVAO", "BAGUIO", "ILOILO")),
    Country("XV", r"(XV|3W)[0-9]", ("XV", "3W"), 26,
            ("NAM", "HUNG", "TUAN", "MINH", "DUC"),
            ("HANOI", "DANANG", "HAIPHONG", "HUE", "CAN THO")),
    Country("HZ", r"(HZ|[78]Z)[0-9]", ("HZ", "7Z"), 21,
            ("ABDULLAH", "MOHAMMED", "KHALID", "FAHD", "SAAD"),
            ("RIYADH", "JEDDAH", "DAMMAM", "MAKKAH", "TABUK")),
    Country("CN", r"(CN|5[C-G])[0-9]", ("CN", "5C"), 33,
            ("MOHAMED", "AHMED", "HASSAN", "YOUSSEF", "KARIM"),
            ("CASABLANCA", "RABAT", "MARRAKECH", "FES", "TANGER")),
    Country("SU", r"(SU|SS|6[AB])[0-9]", ("SU",), 34,
            ("AHMED", "MOHAMED", "MAHMOUD", "MOSTAFA", "KHALED"),
            ("CAIRO", "ALEXANDRIA", "GIZA", "LUXOR", "ASWAN")),
    Country("5Z", r"5[YZ][0-9]", ("5Z", "5Y"), 37,
            ("JOHN", "PETER", "JAMES", "DAVID", "JOSEPH"),
            ("NAIROBI", "MOMBASA", "KISUMU", "NAKURU", "ELDORET")),
    Country("5N", r"5[NO][0-9]", ("5N", "5O"), 35,
            ("ADEBAYO", "EMEKA", "CHIDI", "TUNDE", "IBRAHIM"),
            ("LAGOS", "ABUJA", "IBADAN", "KANO", "PORT HARCOURT")),
    Country("9G", r"9G[0-9]", ("9G",), 35,
            ("KOFI", "KWAME", "KWESI", "YAW", "EBENEZER"),
            ("ACCRA", "KUMASI", "TAMALE", "TAKORADI", "CAPE COAST")),
    Country("6W", r"6[VW][0-9]", ("6W", "6V"), 35,
            ("MAMADOU", "IBRAHIMA", "CHEIKH", "MOUSSA", "OUSMANE"),
            ("DAKAR", "THIES", "SAINT LOUIS", "KAOLACK", "ZIGUINCHOR")),
    Country("TJ", r"TJ[0-9]", ("TJ",), 36,
            ("PAUL", "JEAN", "EMMANUEL", "FRANCOIS", "SAMUEL"),
            ("DOUALA", "YAOUNDE", "GAROUA", "BAFOUSSAM", "BAMENDA")),
    Country("TU", r"TU[0-9]", ("TU",), 35,
            ("KOUASSI", "YAO", "KONE", "JEAN", "SERGE"),
            ("ABIDJAN", "YAMOUSSOUKRO", "BOUAKE", "SAN PEDRO", "KORHOGO")),
    Country("OA", r"(O[A-C]|4T)[0-9]", ("OA", "OB"), 10,
            ("LUIS", "CARLOS", "JORGE", "MIGUEL", "ANGEL"),
            ("LIMA", "AREQUIPA", "CUSCO", "TRUJILLO", "PIURA")),
    Country("YV", r"(Y[V-Y]|4M)[0-9]", ("YV", "YW"), 9,
            ("JOSE", "LUIS", "CARLOS", "JESUS", "ALEJANDRO"),
            ("CARACAS", "MARACAIBO", "VALENCIA", "BARQUISIMETO", "MERIDA"),
            digits="123456789"),  # 0 ist Aves Island
    Country("9M", r"9[MW][0-9]", ("9M", "9W"), 28,
            ("AHMAD", "ABDUL", "MOHD", "ROSLAN", "HASSAN"),
            ("KUALA LUMPUR", "GEORGE TOWN", "JOHOR BAHRU", "IPOH", "MALACCA"),
            digits="2345"),  # 0 ist Spratly, 6 und 8 sind Ost-Malaysia
    Country("S2", r"S[23][0-9]", ("S21", "S22", "S23", "S31"), 22,
            ("RAHMAN", "KARIM", "HASAN", "ALAM", "ISLAM"),
            ("DHAKA", "CHITTAGONG", "KHULNA", "SYLHET", "RAJSHAHI")),
    Country("E7", r"E7[0-9]", ("E71", "E72", "E73"), 15,
            ("EMIR", "SAMIR", "ADMIR", "NEDIM", "DZEMAL"),
            ("SARAJEVO", "BANJA LUKA", "TUZLA", "MOSTAR", "ZENICA")),
]

RIGS = ("IC7300", "IC7610", "IC705", "IC7851", "FT991", "FTDX10", "FTDX101", "FT817", "FT710",
        "K3", "K4", "KX2", "KX3", "TS590", "TS890", "FLEX6600", "HOMEBREW")
POWERS = ("5W", "10W", "50W", "100W", "100W", "100W", "400W", "750W")
# Nennleistung der Geräte, soweit sie unter 100 W liegt; mehr als sie senden
# QRP-Geräte nicht (400 W und 750 W gibt es nur mit Endstufe an den übrigen).
RIG_MAX_WATTS = {"FT817": 5, "IC705": 10, "KX2": 10, "KX3": 15}


def rig_and_power() -> tuple:
    """Zufälliges Gerät und eine dazu mögliche Leistung."""
    rig = random.choice(RIGS)
    cap = RIG_MAX_WATTS.get(rig)
    powers = [pwr for pwr in POWERS if cap is None or int(pwr[:-1]) <= cap]
    return rig, random.choice(powers)


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
# Kanada sendet seine Provinz (nach Rufzeichenbezirk; VO, VY eigens, siehe _province).
CA_PROVINCES = {
    "1": ("NS",), "2": ("QC",), "3": ("ON",), "4": ("MB",), "5": ("SK",), "6": ("AB",),
    "7": ("BC",), "8": ("NT",), "9": ("NB",),
}
ARRL_POWERS = ("KW", "KW", "1TT", "1TT", "5TT", "4TT", "100", "5T")
# IARU HF: ITU-Zonen (für USA/Russland je nach Ziffer, siehe itu_zone).
ITU_ZONES = {
    "DL": 28, "F": 27, "GM": 27, "G": 27, "I": 28, "EA": 37, "PA": 27, "ON": 27, "OE": 28, "HB": 28,
    "SP": 28, "OK": 28, "OZ": 18, "SM": 18, "LA": 18, "OH": 18, "W": 8, "JA": 45, "UA": 29,
    "UR": 29, "ZS": 57, "VK": 59, "ZL": 60, "PY": 15, "CE": 14, "HA": 28, "OM": 28, "YL": 29,
    "LY": 29, "ES": 29, "EI": 27, "GW": 27, "TA": 39, "CT": 37, "9A": 28, "S5": 28, "YO": 28,
    "YU": 28, "LZ": 28, "SV": 28, "LX": 27, "LU": 14, "HK": 12, "JW": 18,
    "XE": 10, "CO": 11, "HI": 11, "6Y": 11, "TI": 11, "4X": 39, "VU": 41, "BY": 44, "EW": 29,
    "UN": 30, "TF": 17, "Z3": 28, "GI": 27,
    "HL": 44, "HS": 49, "BV": 44, "YB": 54, "DU": 50, "XV": 49, "HZ": 39, "CN": 37, "SU": 38, "5Z": 48, "5N": 46, "9G": 46, "6W": 46,
    "TJ": 47, "TU": 46, "OA": 12, "YV": 12, "9M": 54, "S2": 41, "E7": 28,
    "VE": 4,  # Fallback; die Zone richtet sich nach Bezirk, siehe itu_zone
}
# Grobe weltweite Aktivität je Land (relativ); nicht aufgeführte Länder zählen 2.
# Geschätzt nach den Logzahlen des CQ WW CW 2025 (cqww.com/publiclogs) und der
# Größe der Amateurfunkszene; Afrika und Asien sind darin schwach vertreten.
ACTIVITY = {
    "W": 110, "DL": 16, "JA": 25, "UA": 20, "I": 10, "F": 8, "G": 8, "EA": 8, "SP": 7, "PA": 6,
    "OK": 6, "UR": 6, "PY": 6, "VE": 6, "ON": 5, "SM": 5, "HA": 5, "VK": 5, "OE": 4, "HB": 4,
    "OZ": 4, "OH": 4, "LA": 4, "YO": 4, "LU": 4, "9A": 3, "S5": 3, "LZ": 3, "SV": 3, "CT": 3,
    "ZL": 3, "ZS": 3, "XE": 3, "TA": 3, "YU": 3, "OM": 3, "LY": 3, "ES": 3, "BY": 6, "GM": 4, "VU": 3, "LX": 1,
    "TF": 1, "JW": 1, "GW": 1, "GI": 1, "HI": 1, "6Y": 1, "TI": 1, "Z3": 1, "HL": 5, "HS": 3,
    "BV": 3, "YB": 3, "DU": 3, "XV": 2, "HZ": 2, "CN": 2, "SU": 2, "5Z": 1, "5N": 1, "9G": 1, "6W": 1,
    "TJ": 1, "TU": 1, "OA": 2, "YV": 2, "9M": 2, "S2": 1, "E7": 3,
}
# Referenzpunkt je Land (Breite, Länge in Grad; meist die Hauptstadt) für die
# Entfernung zum eigenen Standort. Wo die Ziffer des Rufzeichens den Ort
# bestimmt, gilt POSITION_BY_DISTRICT (Schlüssel Land + Ziffer).
POSITION = {
    "DL": (51.0, 10.0), "F": (47.0, 2.5), "GM": (56.8, -4.2), "G": (52.5, -1.5), "GI": (54.6, -6.0),
    "GW": (52.3, -3.7), "I": (42.5, 12.5), "EA": (40.0, -3.7), "PA": (52.2, 5.3), "ON": (50.6, 4.7),
    "OE": (47.5, 14.0), "HB": (46.9, 8.2), "SP": (52.0, 19.5), "OK": (49.8, 15.5), "OZ": (56.0, 10.0),
    "SM": (60.0, 16.0), "LA": (61.0, 9.0), "OH": (62.0, 26.0), "W": (39.0, -98.0), "JA": (36.0, 138.0),
    "UR": (49.0, 31.5), "UA": (55.7, 37.6), "ZS": (-29.0, 25.0), "VK": (-25.0, 134.0),
    "ZL": (-41.0, 174.0), "PY": (-15.8, -47.9), "CE": (-33.4, -70.7), "HA": (47.5, 19.0),
    "OM": (48.7, 19.5), "YL": (56.9, 24.1), "LY": (55.0, 24.0), "ES": (58.8, 25.5), "EI": (53.3, -7.5),
    "TA": (39.9, 32.9), "CT": (39.5, -8.0), "9A": (45.8, 16.0), "S5": (46.1, 14.8), "YO": (45.9, 25.0),
    "YU": (44.0, 20.9), "LZ": (42.7, 25.5), "SV": (38.0, 23.7), "LX": (49.8, 6.1), "LU": (-34.6, -58.4),
    "HK": (4.6, -74.1), "JW": (78.2, 15.6), "VE": (50.0, -95.0), "XE": (19.4, -99.1), "CO": (23.1, -82.4),
    "HI": (18.5, -69.9), "6Y": (18.0, -76.8), "TI": (9.9, -84.1), "4X": (31.8, 35.2), "VU": (28.6, 77.2),
    "BY": (39.9, 116.4), "EW": (53.9, 27.6), "UN": (51.2, 71.4), "TF": (64.1, -21.9), "Z3": (42.0, 21.4),
    "HL": (37.6, 127.0), "HS": (13.8, 100.5), "BV": (25.0, 121.5), "YB": (-6.2, 106.8),
    "DU": (14.6, 121.0), "XV": (21.0, 105.8), "HZ": (24.7, 46.7), "CN": (33.6, -7.6), "SU": (30.0, 31.2),
    "5Z": (-1.3, 36.8), "E7": (43.9, 18.4), "5N": (9.1, 7.4), "9G": (5.6, -0.2), "6W": (14.7, -17.5), "TJ": (3.9, 11.5),
    "TU": (6.8, -5.3), "OA": (-12.0, -77.0), "YV": (10.5, -66.9), "9M": (3.1, 101.7), "S2": (23.8, 90.4),
}
POSITION_BY_DISTRICT = {
    "W1": (42.4, -71.1), "W2": (40.7, -74.0), "W3": (40.0, -75.2), "W4": (33.7, -84.4),
    "W5": (32.8, -97.0), "W6": (34.0, -118.2), "W7": (43.0, -114.0), "W8": (41.5, -83.0),
    "W9": (41.9, -87.6), "W0": (40.0, -97.0),
    "VE1": (44.6, -63.6), "VE2": (45.5, -73.6), "VE3": (43.7, -79.4), "VE4": (49.9, -97.1),
    "VE5": (52.1, -106.7), "VE6": (51.0, -114.1), "VE7": (49.3, -123.1), "VE8": (62.5, -114.4),
    "VE9": (45.9, -66.6),
    "VK2": (-33.9, 151.2), "VK3": (-37.8, 145.0), "VK4": (-27.5, 153.0), "VK5": (-34.9, 138.6),
    "VK6": (-32.0, 116.0), "VK7": (-42.9, 147.3), "VK8": (-12.5, 130.8), "VK1": (-35.3, 149.1),
    "UA2": (54.7, 20.5), "UA9": (56.8, 60.6), "UA0": (56.0, 93.0),
}
# Wie schnell die Stationen mit der Entfernung seltener werden, bei besten
# Bandbedingungen: Gewicht FLOOR + (1 - FLOOR) / (1 + (d / KM) ** POWER). Das
# Mindestgewicht FLOOR hält auch ferne Länder hörbar.
PROXIMITY_KM = 7000
PROXIMITY_POWER = 3
PROXIMITY_FLOOR = 0.15
# Anteil der Stationen mit Zusatz hinter dem Rufzeichen (nur wenn das „/“ gelernt
# ist, siehe `slash`): portable (/P) häufiger als mobil (/M). /MM gibt es nicht:
# Orte und Zonen passen nicht zu einem Schiff.
# Zusatz hinter dem CQ im normalen QSO: meist keiner, manchmal „DX“ (wer ein
# weiteres Land sucht).
CQ_TAGS = ("", "", "", " DX")
SLASH_SUFFIXES = (("/P", 0.07), ("/M", 0.03))
# Das eigene Land zählt so viel mehr: die meisten QSOs laufen im Inland.
HOME_BOOST = 3
# HQ-Stationen der IARU-Mitgliedsverbände senden statt der Zone das
# Verbandskürzel (Auswahl).
IARU_HQ_STATIONS = {
    "DA0HQ": "DARC", "TM0HQ": "REF", "HB9HQ": "USKA", "S50HQ": "ZRS", "9A0HQ": "HRS",
    "OE0HQ": "OEVSV", "OH1HQ": "SRAL", "OZ1HQ": "EDR", "SK9HQ": "SSA", "SN0HQ": "PZK",
    "HG0HQ": "MRASZ", "LZ0HQ": "BFRA", "YT0HQ": "SRS", "ED0HQ": "URE", "OP0HQ": "UBA", "EI0HQ": "IRTS",
}
IARU_HQ_RUN_PROBABILITY = 0.25
IARU_HQ_CALLER_PROBABILITY = 0.1
# Buchstaben, mit denen DOKs beginnen (Distrikte des DARC).
DOK_LETTERS = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
# Nicht-Mitglieder in DL geben im WAG „NM“ statt eines DOK.
WAG_NM_PROBABILITY = 0.1


@dataclass(frozen=True)
class Station:
    """Eine erfundene Station mit allem, was in einem normalen QSO vorkommen kann."""
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
    """Ein erzeugtes QSO oder ein Contest-Run: die Durchgänge der Stationen
    samt allem, was der QSO-Reiter für Abfrage und Kopfhör-Fragen braucht."""
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
    # Inhaltsfragen fürs Kopfhören: ((Frage, (Erwartet, Art)), …); daraus
    # werden nach dem QSO einige zufällig gestellt.
    facts: tuple = ()

    @property
    def is_contest(self) -> bool:
        """Ist es ein Contest-Run (und kein normales QSO)?"""
        return self.kind != RAGCHEW

    def text(self) -> str:
        """Der ganze gesendete Text, alle Durchgänge hintereinander."""
        return " ".join(text for _, text in self.transmissions)


_call_pool = None  # [(Rufzeichen, Country)], beim ersten Gebrauch geladen
# Nach Länderauswahl gefilterte Teile von _call_pool (Schlüssel: frozenset
# der Länder-Keys, None = alle), damit nicht jedes Rufzeichen die ganze
# Liste neu filtert.
_filtered_pools = {}

# Alle Länder-Muster in einem Regex, je als benannte Gruppe c<Index>. Die
# Alternativen werden der Reihe nach probiert, es gewinnt also wie bei
# einer Schleife über COUNTRIES das erste passende Land.
_COUNTRY_RE = re.compile("|".join(f"(?P<c{i}>{country.pattern})" for i, country in enumerate(COUNTRIES)))


def _country_of(call: str):
    match = _COUNTRY_RE.match(call)
    return COUNTRIES[int(match.lastgroup[1:])] if match else None


def _load_pool():
    global _call_pool
    if _call_pool is None:
        calls, _release = load_callsigns()
        _call_pool = [(c, country) for c in calls if "/" not in c and (country := _country_of(c))]
    return _call_pool


def _pool_for(countries):
    key = frozenset(countries) if countries is not None else None
    pool = _filtered_pools.get(key)
    if pool is None:
        pool = [(c, k) for c, k in _load_pool() if key is None or k.key in key]
        _filtered_pools[key] = pool
    return pool


def _generated_call(country: Country) -> str:
    prefix = random.choice(country.sample_prefixes)
    suffix_len = random.choices([1, 2, 3], weights=[1, 4, 5])[0]
    suffix = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(suffix_len))
    digit = "" if prefix[-1].isdigit() else random.choice(country.digits)
    return f"{prefix}{digit}{suffix}"


_station_call = ""        # eigenes Rufzeichen aus den Einstellungen
_station_position = None  # (Breite, Länge) aus dem Locator in den Einstellungen


def set_station_call(call: str):
    """Merkt sich das eigene Rufzeichen; danach richtet sich, aus welchen
    Weltgegenden die erzeugten Stationen stammen."""
    global _station_call
    _station_call = call.strip().upper()


def set_station_locator(locator: str) -> bool:
    """Merkt sich den Standort aus dem Locator; er geht dem Land des
    Rufzeichens vor. Ein leerer Locator löscht ihn, ein ungültiger auch (False)."""
    global _station_position
    _station_position = locator_position(locator)
    return _station_position is not None or not locator.strip()


def locator_position(locator: str):
    """Mitte des Maidenhead-Feldes (4 oder 6 Zeichen, z. B. JO41 oder JO41ab)
    als (Breite, Länge) in Grad; None, wenn es kein Locator ist."""
    match = re.fullmatch(r"([A-R]{2})([0-9]{2})([A-X]{2})?", locator.strip().upper())
    if not match:
        return None
    field_, square, sub = match.groups()
    lon = (ord(field_[0]) - 65) * 20 - 180 + int(square[0]) * 2
    lat = (ord(field_[1]) - 65) * 10 - 90 + int(square[1])
    if sub:
        return lat + (ord(sub[1]) - 65) / 24 + 1 / 48, lon + (ord(sub[0]) - 65) / 12 + 1 / 24
    return lat + 0.5, lon + 1.0


def _distance_km(a: tuple, b: tuple) -> float:
    """Entfernung zweier Punkte (Breite, Länge) auf der Erdkugel."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _home_position(home_call: str):
    """(Land, (Breite, Länge)) des eigenen Standorts: der Locator aus den
    Einstellungen, solange `home_call` das eigene Rufzeichen ist (oder fehlt),
    sonst der Referenzpunkt des Rufzeichen-Landes. (None, None), wenn beides
    nicht zu bestimmen ist."""
    call = home_call or _station_call
    country = _country_of(call) if call else None
    if _station_position and call == _station_call:
        return country, _station_position
    if country is None:
        return None, None
    return country, POSITION_BY_DISTRICT.get(country.key + _district(call)) or POSITION[country.key]


def _country_weights(countries: list, home_country, position) -> list:
    """Gewicht je Land für den Standort `position`: ACTIVITY, mit der
    Entfernung abnehmend, das eigene Land mit HOME_BOOST. Ohne Standort
    (None) zählt nur ACTIVITY."""
    weights = []
    for k in countries:
        weight = ACTIVITY.get(k.key, 2) * (HOME_BOOST if k is home_country else 1)
        if position is not None:
            near = 1 / (1 + (_distance_km(position, POSITION[k.key]) / PROXIMITY_KM) ** PROXIMITY_POWER)
            weight *= PROXIMITY_FLOOR + (1 - PROXIMITY_FLOOR) * near
        weights.append(weight)
    return weights


def _pool_by_country(countries) -> dict:
    """Die Rufzeichen aus `_pool_for`, nach Land-Schlüssel gruppiert:
    {Schlüssel: (Land, [Rufzeichen])}."""
    cache_key = ("by_country", frozenset(countries) if countries is not None else None)
    grouped = _filtered_pools.get(cache_key)
    if grouped is None:
        grouped = {}
        for call, country in _pool_for(countries):
            grouped.setdefault(country.key, (country, []))[1].append(call)
        _filtered_pools[cache_key] = grouped
    return grouped


def _with_suffix(call: str) -> str:
    """`call` mit Zusatz /P oder /M, gewürfelt nach SLASH_SUFFIXES."""
    roll = random.random()
    for suffix, share in SLASH_SUFFIXES:
        if roll < share:
            return call + suffix
        roll -= share
    return call


def _pick_call(exclude=(), countries=None, arrl_dx=None, home="", slash=False):
    """Zufälliges Rufzeichen, optional nur aus bestimmten Ländern (Keys); mit
    `arrl_dx` nur DX- (True) oder nur W/VE-Stationen (False) im Sinne des ARRL DX.
    Das Land wird nach dem Standort `home` (sonst dem eigenen Rufzeichen aus den
    Einstellungen) gezogen, dann ein Rufzeichen daraus. Mit `slash` tragen
    einige Rufzeichen den Zusatz /P oder /M."""
    by_country = _pool_by_country(countries)
    if by_country:
        pool_countries = [country for country, _ in by_country.values()]
    else:
        pool_countries = [k for k in COUNTRIES if countries is None or k.key in countries]
    weights = _country_weights(pool_countries, *_home_position(home))
    while True:
        country = random.choices(pool_countries, weights)[0]
        call = random.choice(by_country[country.key][1]) if by_country else _generated_call(country)
        if slash:
            call = _with_suffix(call)
        if call not in exclude and call.split("/")[0] not in exclude \
                and (arrl_dx is None or _arrl_dx(call, country) == arrl_dx):
            return call, country


def _district(call: str) -> str:
    return next((ch for ch in call if ch.isdigit()), "1")


def _province(call: str) -> tuple:
    """Provinz(en) einer kanadischen Station: VO1 ist Neufundland, VO2 Labrador,
    VY1 Yukon, VY2 Prince Edward Island, VY0 Nunavut, sonst nach der Ziffer."""
    if call.startswith("VO"):
        return ("LB",) if _district(call) == "2" else ("NL",)
    if call.startswith("VY"):
        return {"1": ("YT",), "2": ("PE",), "0": ("NU",)}.get(_district(call), ("NU",))
    return CA_PROVINCES.get(_district(call), CA_PROVINCES["3"])


# Gebiete mit US-Rufzeichen, die im ARRL DX als DX zählen: Hawaii und andere
# Pazifikgebiete (KH, AH, NH, WH), Alaska (KL, AL, NL, WL), Puerto Rico und
# Jungferninseln (KP, NP, WP), Guantanamo (KG4), Guam (KG6).
_US_TERRITORY = re.compile(r"(?:[KNWA][HL]|[KNW]P|KG[46])")


def _arrl_dx(call: str, country: Country) -> bool:
    """Zählt die Station im ARRL DX als DX (und nicht als W/VE)? Außer den
    Ländern gehören dazu die US-Gebiete sowie CY0 und CY9 (Sable, St. Paul)."""
    if country.key == "W":
        return bool(_US_TERRITORY.match(call))
    if country.key == "VE":
        return call.startswith(("CY0", "CY9"))
    return True


def _us_territory_zones(call: str):
    """(CQ-Zone, ITU-Zone) für US-Gebiete, sonst None."""
    if not _US_TERRITORY.match(call):
        return None
    if call[1] == "L":
        return 1, 1  # Alaska, bei jeder Ziffer
    if call[1] == "P" or call.startswith("KG4"):
        return 8, 11  # Puerto Rico, Jungferninseln, Guantanamo
    if call.startswith("KG6"):
        return 27, 64
    return {"2": (27, 64), "0": (27, 64), "8": (32, 62), "9": (31, 65)}.get(_district(call), (31, 61))


# Inselgebiete mit eigener Zone: Rufzeichenanfang -> (CQ-Zone, ITU-Zone) nach cty.dat.
_ISLAND_ZONES = (
    (("EA8", "EB8", "EC8", "ED8", "EE8", "EF8", "EG8", "EH8", "AM8", "AN8", "AO8"), (33, 36)),  # Kanaren
    (("EA9", "EB9", "EC9", "ED9", "EE9", "EF9", "EG9", "EH9", "AM9", "AN9", "AO9"), (33, 37)),  # Ceuta, Melilla
    (("CQ2", "CQ3", "CQ9", "CR3", "CR9", "CS3", "CS9", "CT3", "CT9"), (33, 36)),  # Madeira
    (("CQ1", "CQ8", "CR1", "CR2", "CR8", "CS4", "CS8", "CT8", "CU"), (14, 36)),  # Azoren
    (("IG9", "IH9"), (33, 37)),  # Italien in Afrika
)


def _island_zones(call: str):
    """(CQ-Zone, ITU-Zone) für Inselgebiete mit eigener Zone, sonst None."""
    for prefixes, zones in _ISLAND_ZONES:
        if call.startswith(prefixes):
            return zones
    return None


def cq_zone(call: str, country: Country) -> int:
    """CQ-Zone der Station `call`; in USA, Kanada, Russland und Australien nach
    der Ziffer im Rufzeichen (US-Gebiete eigens), Inselgebiete nach Präfix.
    Für große Länder ist es eine Näherung: Die Ziffer sagt nicht, in welchem
    Bundesstaat die Station sitzt."""
    district = _district(call)
    if island := _island_zones(call):
        return island[0]
    if country.key == "W":
        if territory := _us_territory_zones(call):
            return territory[0]
        # Zone 4 umfasst auch W8 (außer West Virginia, dem kleineren Teil).
        return {"6": 3, "7": 3, "5": 4, "8": 4, "9": 4, "0": 4}.get(district, 5)
    if country.key == "UA":
        # Ziffer 2 ist Kaliningrad.
        return {"2": 15, "8": 17, "9": 17, "0": 18}.get(district, 16)
    if country.key == "VE":
        if call.startswith("VY"):
            return 1 if district == "1" else 5 if district == "2" else 2
        if call.startswith("VO"):
            return 2 if district == "2" else 5  # Labrador, sonst Neufundland
        return {"8": 1, "7": 3, "3": 4, "4": 4, "5": 4, "6": 4}.get(district, 5)
    if country.key == "VK":
        return 29 if district in "68" else 30
    return country.zone


def itu_zone(call: str, country: Country) -> int:
    """ITU-Zone der Station `call`; in USA, Kanada, Russland und Australien nach
    der Ziffer im Rufzeichen (US-Gebiete eigens), Inselgebiete nach Präfix."""
    district = _district(call)
    if island := _island_zones(call):
        return island[1]
    if country.key == "W":
        if territory := _us_territory_zones(call):
            return territory[1]
        # IL, IN und WI (W9) liegen überwiegend östlich von 90° W, in Zone 8.
        return {"6": 6, "7": 6, "5": 7, "0": 7}.get(district, 8)
    if country.key == "UA":
        return {"8": 30, "9": 30, "0": 32}.get(district, 29)
    if country.key == "VK":
        return {"4": 55, "8": 55, "6": 58}.get(district, 59)
    if country.key == "VE":
        if call.startswith(("VO", "VY2")):
            return 9
        if call.startswith("VY"):
            return 2 if district == "1" else 4
        return {"7": 2, "8": 3, "4": 3, "5": 3, "6": 3, "2": 4, "3": 4}.get(district, 9)
    return ITU_ZONES[country.key]


def _qth_for(call: str, country: Country) -> str:
    """Zufälliger Ort des Landes; wo die Ziffer das Bundesland bestimmt, aus diesem."""
    if country.key == "VE" and call.startswith(("VO", "VY")):
        return random.choice({"VO1": ("ST JOHNS", "CORNER BROOK"), "VO2": ("LABRADOR CITY", "GOOSE BAY"),
                              "VY1": ("WHITEHORSE", "DAWSON"), "VY2": ("CHARLOTTETOWN", "SUMMERSIDE"),
                              "VY0": ("IQALUIT", "RANKIN INLET")}.get(call[:3], country.qths))
    by_district = country.qths_by_district
    return random.choice((by_district and by_district.get(_district(call))) or country.qths)


def _make_station(exclude=(), slash=False) -> Station:
    call, country = _pick_call(exclude, slash=slash)
    wx = random.choice(WEATHER)
    temp = random.randint(0, 3) if wx == "SNOW" else random.randint(5, 30)
    age = random.randint(18, 85)
    licensed = random.randint(max(datetime.now().year - (age - 14), 1950), datetime.now().year - 1)
    rig, pwr = rig_and_power()
    return Station(
        call=call, name=random.choice(country.names), qth=_qth_for(call, country),
        rig=rig, pwr=pwr, ant=random.choice(ANTENNAS),
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


def generate_qso(kind: str = RAGCHEW, length: int = LENGTH_NORMAL, pileup_probability: float = 0.0,
                 slash: bool = False, dup: bool = False) -> Qso:
    """`pileup_probability`: Anteil der Anrufe im Contest, bei denen weitere
    Stationen gleichzeitig rufen (0 = keine Pile-ups). `slash`: einige
    Rufzeichen tragen /P oder /M; nur sinnvoll, wenn das „/“ gelernt ist
    (siehe `knows_slash`). `dup`: im Contest ruft einmal eine Station, die schon
    im Log steht, noch einmal an und bekommt „DUP“ (siehe `knows_dup`)."""
    if kind == RAGCHEW:
        return _generate_ragchew(length, slash)
    return _generate_contest(kind, random.randint(*CONTEST_QSO_RANGES[length]), pileup_probability, slash, dup)


def knows_dup(charset: str) -> bool:
    """Sind D, U und P gelernt, sodass „DUP“ im Contest zumutbar ist?"""
    return set("DUP") <= set(charset.upper())


def knows_slash(charset: str) -> bool:
    """Ist in den gelernten Zeichen der Schrägstrich, sodass Rufzeichen mit
    /P oder /M zumutbar sind?"""
    return "/" in charset


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


def _generate_ragchew(length: int, slash: bool = False) -> Qso:
    """Normales QSO zwischen zwei erfundenen Stationen; `length` bestimmt, was
    alles ausgetauscht wird (siehe LENGTH_*). Mit Abfrage und Kopfhör-Fragen."""
    a = _make_station(slash=slash)
    b = _make_station(exclude={a.call}, slash=slash)
    rst_a, rst_b = _pick_rst(), _pick_rst()
    greet = _greeting()

    txs = [
        (0, f"{_repeat('CQ', random.choice([2, 3]))}{random.choice(CQ_TAGS)} DE "
            f"{_repeat(a.call, random.choice([2, 3]))} K"),
        (1, f"{a.call} DE {_repeat(b.call, 2)} K"),
    ]

    opening = "TNX FER CALL" if length == LENGTH_SHORT else f"{greet} DR OM ES TNX FER CALL"
    tx = [f"{b.call} DE {a.call}", opening, "=",
          f"UR RST {rst_a} {rst_a}", "=", f"NAME {_repeat(a.name, 2)}", "=", f"QTH {_repeat(a.qth, 2)}", "=",
          "HW?", f"{b.call} DE {a.call} {_over()}"]
    txs.append((0, " ".join(tx)))

    tx = [f"{a.call} DE {b.call} R", f"{greet} {a.name} TNX FER RPRT", "=",
          f"UR RST {rst_b} {rst_b}", "=", f"NAME {_repeat(b.name, 2)}", "=", f"QTH {_repeat(b.qth, 2)}", "="]
    tx += _station_info(b, length)
    if length == LENGTH_SHORT:
        tx += ["TNX QSO 73 ES GL", SK, f"{a.call} DE {b.call}"]
    else:
        if length >= LENGTH_LONG:
            tx += ["QSL VIA BURO", "="]
        tx += ["HW?", f"{a.call} DE {b.call} {_over()}"]
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
    # Fragen nach der Rolle, nicht nach dem Rufzeichen: sonst verriete
    # „Name von DL1ABC“ die Antwort auf „Rufzeichen der CQ-Station“.
    facts = []
    stations = ((a, rst_a, tr("der CQ-Station"), tr("die CQ-Station")),
                (b, rst_b, tr("der antwortenden Station"), tr("die antwortende Station")))
    for st, rst, of, subject in stations:
        facts += [
            (tr("Rufzeichen {of}").format(of=of), (st.call, TEXT)),
            (tr("Name {of}").format(of=of), (st.name, TEXT)),
            (tr("QTH {of}").format(of=of), (st.qth, TEXT)),
            (tr("Rapport, den {subject} gab").format(subject=subject), (rst, RST)),
        ]
    # Rig, Leistung, Wetter gibt es erst ab normaler Länge (dann von beiden).
    for st, _, of, subject in stations if length >= LENGTH_NORMAL else ():
        facts += [
            (tr("Rig {of}").format(of=of), (st.rig, TEXT)),
            (tr("Leistung {of}").format(of=of), (st.pwr, POWER)),
            (tr("Wetter {of}").format(of=of), (st.wx.split()[0], TEXT)),
        ]
        if length >= LENGTH_LONG:
            facts += [
                (tr("Antenne {of}").format(of=of), (st.ant, TEXT)),
                (tr("Alter des OPs {of}").format(of=of), (str(st.age), NUMBER)),
                (tr("Lizenzjahr des OPs {of}").format(of=of), (str(st.licensed), NUMBER)),
            ]
    return Qso(
        kind=RAGCHEW, calls=(a.call, b.call), transmissions=tuple(txs), facts=tuple(facts),
        quiz_columns=(tr("Station 1 (CQ)"), tr("Station 2")),
        quiz_rows=(
            (tr("Rufzeichen"), ((a.call, TEXT), (b.call, TEXT))),
            (tr("Name"), ((a.name, TEXT), (b.name, TEXT))),
            (tr("QTH"), ((a.qth, TEXT), (b.qth, TEXT))),
            (tr("Rapport (gibt)"), ((rst_a, RST), (rst_b, RST))),
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
            dok = ("NM" if random.random() < WAG_NM_PROBABILITY
                   else f"{random.choice(DOK_LETTERS)}{random.randint(1, 60):02d}")
            self.fixed = (dok, DOK)
        elif kind == "cqww":
            self.fixed = (str(cq_zone(call, country)), NUMBER)
        elif kind == "arrldx" and not _arrl_dx(call, country):
            states = US_STATES[_district(call)] if country.key == "W" else _province(call)
            self.fixed = (random.choice(states), TEXT)
        elif kind == "arrldx":
            self.fixed = (random.choice(ARRL_POWERS), NUMBER)
        elif kind == "iaru" and call in IARU_HQ_STATIONS:
            self.fixed = (IARU_HQ_STATIONS[call], TEXT)
        elif kind == "iaru":
            self.fixed = (str(itu_zone(call, country)), NUMBER)
        else:  # WPX, WAG ohne DOK
            self.fixed = None

    def next(self):
        """Nächster Austausch als (Text, Art): fester Wert (Zone, DOK, Bundesstaat,
        Leistung) oder die nächste Seriennummer."""
        if self.fixed is not None:
            return self.fixed
        value = (_cut_serial(self.serial), NUMBER)
        self.serial += 1
        return value


def _pick_contest_call(kind: str, exclude, countries, hq_probability: float, arrl_dx=None, home="",
                       slash=False):
    """Wie _pick_call; im IARU HF Contest ist es mit `hq_probability` eine
    HQ-Station."""
    if kind == "iaru" and random.random() < hq_probability:
        free = [c for c in IARU_HQ_STATIONS if c not in exclude]
        if free:
            call = random.choice(free)
            return call, _country_of(call)
    return _pick_call(exclude, countries, arrl_dx, home, slash)


def _cq_calls(kind: str, run: str, test: str) -> list:
    """Wie eine Run-Station CQ ruft; „CQ DX“ nur dort, wo man es hört."""
    calls = [f"CQ {test} {run} {run}", f"CQ {run} {run} {test}", f"CQ {test} {run}", f"{test} {run}",
             f"CQ CQ {test} DE {run} {run}", f"{run} {test}"]
    if kind in ("cqww", "wpx"):
        calls.append(f"CQ DX {test} {run}")
    return calls


# Ein Dupe (zweites Rufen einer schon geloggten Station) kommt frühestens nach
# DUP_AFTER_QSOS QSOs, höchstens einmal je Run.
DUP_PROBABILITY = 0.08
DUP_AFTER_QSOS = 3


def _generate_contest(kind: str, count: int, pileup_probability: float = 0.0, slash: bool = False,
                      dup: bool = False) -> Qso:
    # WAG: DL arbeitet alle; ARRL DX: der Rest der Welt arbeitet W/VE.
    """Contest-Run der Art `kind` mit `count` QSOs; mit `pileup_probability`
    rufen bei einem Teil der Anrufe weitere Stationen gleichzeitig. Mit Abfrage
    der Rufzeichen und des Austauschs."""
    run_countries = {"wag": {"DL"}}.get(kind)
    # ARRL DX: Run-Station ist DX, die Anrufer sind W/VE.
    run_dx, caller_dx = (True, False) if kind == "arrldx" else (None, None)
    test = "WAG" if kind == "wag" else "TEST"

    run, run_country = _pick_contest_call(kind, (), run_countries, IARU_HQ_RUN_PROBABILITY, run_dx, slash=slash)
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
    rows = [(tr("Run-Station"), ((run, TEXT), run_exchange.fixed))]

    extra_calls, pileups = [], []
    dup_call, cq_next = None, False
    for i in range(count):
        station = i + 1
        call, country = _pick_contest_call(kind, used, None, IARU_HQ_CALLER_PROBABILITY, caller_dx, slash=slash)
        used.add(call)
        exchange, exchange_kind = _Exchange(kind, call, country, random.randint(1, 1500)).next()

        if i == 0 or cq_next or random.random() < 0.35:
            send(0, random.choice(_cq_calls(kind, run, test)))
            cq_next = False
        send(station, call if random.random() < 0.7 else f"{call} {call}")
        if random.random() < pileup_probability:
            others = []
            for _ in range(random.randint(*PILEUP_EXTRA_CALLERS)):
                other, _ = _pick_contest_call(kind, used, None, IARU_HQ_CALLER_PROBABILITY, caller_dx, slash=slash)
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
        if dup and dup_call is None and i + 1 >= DUP_AFTER_QSOS and random.random() < DUP_PROBABILITY:
            # Eine Station aus dem Log ruft noch einmal: Run-Station sagt DUP, kein neues QSO.
            again = random.randrange(1, station)
            dup_call = rows[again][1][0][0]
            send(again, dup_call if random.random() < 0.7 else f"{dup_call} {dup_call}")
            send(0, f"{dup_call} DUP")
            send(again, random.choice(["OK", "R", "TU"]))
            cq_next = True

    _check(txs)
    facts = [(tr("Rufzeichen der Run-Station"), (run, TEXT)),
             (tr("Wie viele QSOs hat die Run-Station geloggt?"), (str(count), NUMBER))]
    facts += [(tr("Austausch von {call}").format(call=cells[0][0]), cells[1]) for _, cells in rows[1:]]
    if dup_call is not None:
        facts.append((tr("Welche Station hat noch einmal gerufen und „DUP“ bekommen?"), (dup_call, TEXT)))
    return Qso(
        kind=kind, calls=(run, *(cells[0][0] for _, cells in rows[1:]), *extra_calls), facts=tuple(facts),
        pileups=tuple(pileups),
        transmissions=tuple(txs), quiz_columns=(tr("Rufzeichen"), tr("Austausch")), quiz_rows=tuple(rows),
    )


# --- Für den aktiven Contest-Modus -----------------------------------------------
def cut_number(number: int) -> str:
    """Seriennummer dreistellig mit T für führende Nullen (7 -> TT7), wie
    Contest-Software sie sendet; ab 100 unverändert."""
    return str(number) if number >= 100 else f"{number:03d}".replace("0", "T", 3 - len(str(number)))


def contest_test_word(kind: str) -> str:
    """Wort im CQ-Ruf des Contests: „WAG“ im WAG, sonst „TEST“."""
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
        if _arrl_dx(my_call, country):
            return "100"
        return US_STATES[_district(my_call)][0] if country.key == "W" else _province(my_call)[0]
    return ""  # WAG in DL: DOK


def contest_caller(kind: str, my_call: str, exclude, slash: bool = False):
    """Ein Anrufer für die eigene Run-Station: (Rufzeichen, Austausch, Art des
    Austauschs für den Vergleich)."""
    my_country = _country_of(my_call)
    countries = None
    arrl_dx = None
    if kind == "arrldx":
        # W/VE arbeiten den Rest der Welt und umgekehrt.
        arrl_dx = bool(my_country) and not _arrl_dx(my_call, my_country)
    elif kind == "wag" and not (my_country and my_country.key == "DL"):
        # Im WAG arbeiten Nicht-DL-Stationen nur DL.
        countries = {"DL"}
    call, country = _pick_contest_call(kind, set(exclude) | {my_call}, countries, IARU_HQ_CALLER_PROBABILITY, arrl_dx,
                                         my_call, slash)
    exchange, exchange_kind = _Exchange(kind, call, country, random.randint(1, 1500)).next()
    return call, exchange, exchange_kind
