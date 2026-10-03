"""Nachrichten zwischen Trainer und Teilnehmern: je Zeile ein JSON-Objekt
(UTF-8) mit dem Schlüssel "type".

Teilnehmer -> Trainer:
    hello   {"proto", "name", "pin", "version"}
                                              erste Nachricht, sonst Abbruch
    answer  {"n", "typed", "latency", "replayed"}
    paper   {"n", "typed"}                    nach dem Durchgang vom Papier
                                              abgetippte Zeile (ohne Zeit)

Trainer -> Teilnehmer:
    welcome {"session", "version"}            angenommen
    reject  {"reason", "version"}             abgelehnt (REJECT_REASONS), danach zu

"version" ist die Programmversion (z. B. "2.16"), unabhängig vom
Protokoll: Ist die des Trainers neuer, bietet der Teilnehmer ein Update an
(net/update.py) – auch dann, wenn er wegen des Protokolls abgelehnt wird.
    start   {"kind", "charset", "wpm", "fw", "signs", "band", "silent"}
                                              ein Durchgang beginnt; "signs": VVV =
                                              spielen, die erste Sequenz kommt danach
    item    {"n", "text", "wpm", "fw", "band", "paced", "silent"}
                                              abspielen und abfragen; "paced":
                                              fester Takt, Lösungen erst am Ende;
                                              "silent": Ton kommt vom Lautsprecher
                                              des Trainers, nicht selbst abspielen
    stream  {"groups", "wpm", "fw", "band", "silent"}
                                              kontinuierlich: alle Gruppen (Nr. 1, 2, …)
                                              ohne Pause abspielen, fortlaufend
                                              mitschreiben; am Ende je Gruppe eine
                                              answer (net/stream.py)
    replay  {"n"}                             dasselbe noch einmal abspielen
    close   {"n", "solution", "reveal"}       Zeit um, Eingabe schließen;
                                              "reveal": Lösung jetzt zeigen
    end     {"signs", "wpm", "band", "silent"}
                                              Durchgang zu Ende; "signs": + spielen

Gefunden wird ein Trainer per UDP-Broadcast: DISCOVER_QUERY an
DISCOVERY_PORT, die Antwort ist ein JSON-Objekt {"session", "port"}."""
import json
import socket

PROTOCOL_VERSION = 4
DEFAULT_PORT = 7373
DISCOVERY_PORT = 7374
DISCOVER_QUERY = b"MORSETRAINER?"
# Längere Zeilen sind kein Morsetrainer (oder kaputt): Verbindung trennen.
MAX_LINE = 65536
NAME_MAX = 20
TEXT_MAX = 200

REJECT_REASONS = ("proto", "pin", "name")
# Abgerissene Verbindungen (WLAN weg, Rechner im Ruhezustand) erkennen:
# Nach so vielen Sekunden Stille fragt das Betriebssystem nach, dann alle
# KEEPALIVE_INTERVAL_S, und gibt nach KEEPALIVE_COUNT Fehlversuchen auf
# (etwa 25 s). Ohne das blieben der Name eines verschwundenen Teilnehmers
# bis zu einer Viertelstunde belegt und ein Teilnehmer ohne Trainer hängen.
KEEPALIVE_IDLE_S = 10
KEEPALIVE_INTERVAL_S = 5
KEEPALIVE_COUNT = 3


class ProtocolError(Exception):
    pass


def encode(message: dict) -> bytes:
    return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")


def decode(line: bytes) -> dict:
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError(str(exc)) from exc
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ProtocolError("keine Nachricht")
    return message


class LineReader:
    """Liest ganze Zeilen aus einem Socket. read() gibt die nächste
    Nachricht zurück oder None, wenn die Gegenseite zugemacht hat."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b""

    def read(self):
        while b"\n" not in self.buffer:
            if len(self.buffer) > MAX_LINE:
                raise ProtocolError("Zeile zu lang")
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return decode(line)


def enable_keepalive(sock: socket.socket) -> None:
    """TCP-Keepalive mit kurzen Abständen; was das System nicht kennt, bleibt
    beim Standard."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except OSError:
        return
    if hasattr(socket, "SIO_KEEPALIVE_VALS"):  # Windows
        try:
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, KEEPALIVE_IDLE_S * 1000, KEEPALIVE_INTERVAL_S * 1000))
        except (OSError, ValueError):
            pass
        return
    # TCP_KEEPIDLE unter Linux, TCP_KEEPALIVE unter macOS
    idle = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
    for option, value in ((idle, KEEPALIVE_IDLE_S),
                          (getattr(socket, "TCP_KEEPINTVL", None), KEEPALIVE_INTERVAL_S),
                          (getattr(socket, "TCP_KEEPCNT", None), KEEPALIVE_COUNT)):
        if option is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, option, value)
            except OSError:
                pass


def clean_name(name) -> str:
    """Anzeigename eines Teilnehmers: getrimmt, ohne Steuerzeichen, gekürzt."""
    if not isinstance(name, str):
        return ""
    return "".join(ch for ch in name if ch.isprintable()).strip()[:NAME_MAX]


def local_address() -> str:
    """IP-Adresse dieses Rechners im lokalen Netz (zum Ablesen für die
    Teilnehmer). Der UDP-"Connect" schickt nichts, er wählt nur die
    Schnittstelle aus, über die es ins Netz ginge."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def parse_address(text: str):
    """"host" oder "host:port" -> (host, port); None, wenn unbrauchbar."""
    text = text.strip()
    if not text:
        return None
    host, sep, port = text.rpartition(":")
    if not sep:
        return text, DEFAULT_PORT
    if not host or not port.isdigit() or not 0 < int(port) < 65536:
        return None
    return host, int(port)
