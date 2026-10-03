"""Trainerseite: nimmt Teilnehmer an (Name + PIN), verteilt Nachrichten an
alle und reicht Eingänge über eine Queue an die Oberfläche weiter.

Jede Verbindung hat einen eigenen Lese-Thread; die Oberfläche (Tk) holt
die Ereignisse mit poll() ab und ruft nie blockierend ins Netz:
    ("join", name)            angemeldet
    ("leave", name)           Verbindung weg
    ("answer", name, message) Antwort eines Teilnehmers
    ("paper", name, message)  abgetippte Zeile vom Papier

Ein Teilnehmer, dessen Verbindung abgerissen ist, kann sich unter
demselben Namen wieder anmelden. Solange die alte Verbindung steht, ist
der Name für andere Rechner vergeben; vom selben Rechner (gleiche
Adresse) ersetzt die neue Anmeldung die alte sofort. Eine stillschweigend
abgerissene Verbindung (WLAN weg) fällt nach protocol.HEARTBEAT_TIMEOUT_S
ohne Lebenszeichen auf, bei älteren Teilnehmer-Versionen über das
TCP-Keepalive (protocol.enable_keepalive)."""
import json
import queue
import socket
import threading

from morsetrainer.net import protocol

# So lange darf die Anmeldung nach dem Verbindungsaufbau dauern.
HELLO_TIMEOUT_S = 5.0
# Warten auf neue Verbindungen und Suchanfragen in solchen Schritten, damit
# stop() die Threads zuverlässig beendet (ein geschlossener Socket weckt
# ein blockiertes accept() nicht auf jedem System).
IDLE_TIMEOUT_S = 0.5


class Connection:
    """Ein Teilnehmer. Gesendet wird aus einem eigenen Thread, damit ein
    hängender Rechner weder die Oberfläche noch die anderen aufhält."""

    def __init__(self, sock, heartbeat=False):
        self.sock = sock
        self.host = _peer_host(sock)
        self.heartbeat = heartbeat  # Teilnehmer schickt Lebenszeichen (protocol.PING)
        self.outbox = queue.Queue()
        threading.Thread(target=self._write_loop, daemon=True).start()

    def send(self, message: dict) -> None:
        self.outbox.put(protocol.encode(message))

    def close(self) -> None:
        self.outbox.put(None)
        _close(self.sock)

    def _write_loop(self) -> None:
        while True:
            data = self.outbox.get()
            if data is None:
                return
            try:
                self.sock.sendall(data)
            except OSError:
                _close(self.sock)  # der Lese-Thread merkt es und meldet "leave"
                return


class TrainerServer:
    def __init__(self, session: str, pin: str, version=None):
        self.session = session
        self.pin = pin
        self.version = version  # Programmversion, geht mit welcome/reject an die Teilnehmer
        self.events = queue.Queue()
        self.connections = {}  # Name -> Connection
        self.lock = threading.Lock()
        self.listener = None
        self.discovery = None
        self.running = False
        self.stopped = threading.Event()
        self.port = None

    # --- Starten und Beenden ----------------------------------------------------
    def start(self, port: int = protocol.DEFAULT_PORT) -> None:
        """Öffnet den Port (OSError, wenn belegt) und die Suche per UDP.
        Port 0 wählt einen freien (für Tests)."""
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("", port))
            listener.listen()
        except OSError:
            listener.close()
            raise
        self.listener = listener
        self.port = listener.getsockname()[1]
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        self._start_discovery()

    def _start_discovery(self) -> None:
        """Antwortet auf die Suche der Teilnehmer. Ist der Port belegt (etwa
        zweiter Trainer auf demselben Rechner), geht es ohne: Teilnehmer
        geben dann die Adresse von Hand ein."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", protocol.DISCOVERY_PORT))
        except OSError:
            sock.close()
            return
        self.discovery = sock
        threading.Thread(target=self._discovery_loop, args=(sock,), daemon=True).start()

    def stop(self) -> None:
        self.running = False
        self.stopped.set()
        for sock in (self.listener, self.discovery):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self.listener = self.discovery = None
        with self.lock:
            connections = list(self.connections.values())
            self.connections.clear()
        for conn in connections:
            conn.close()

    # --- Threads ------------------------------------------------------------------
    def _accept_loop(self) -> None:
        listener = self.listener
        listener.settimeout(IDLE_TIMEOUT_S)
        while self.running:
            try:
                sock, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            sock.settimeout(None)
            protocol.enable_keepalive(sock)
            threading.Thread(target=self._serve, args=(sock,), daemon=True).start()

    def _heartbeat_loop(self) -> None:
        """Lebenszeichen an alle, die selbst welche schicken."""
        while not self.stopped.wait(protocol.HEARTBEAT_INTERVAL_S):
            with self.lock:
                connections = [conn for conn in self.connections.values() if conn.heartbeat]
            for conn in connections:
                conn.send(protocol.PING)

    def _discovery_loop(self, sock) -> None:
        reply = json.dumps({"session": self.session, "port": self.port}).encode("utf-8")
        sock.settimeout(IDLE_TIMEOUT_S)
        while self.running:
            try:
                data, addr = sock.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                return
            if data.strip() == protocol.DISCOVER_QUERY:
                try:
                    sock.sendto(reply, addr)
                except OSError:
                    pass

    def _serve(self, sock) -> None:
        name = conn = None
        try:
            sock.settimeout(HELLO_TIMEOUT_S)
            reader = protocol.LineReader(sock)
            hello = reader.read()
            if hello is None or hello.get("type") != "hello":
                return
            # Mit Lebenszeichen: kommt so lange gar nichts, ist der Teilnehmer weg.
            heartbeat = hello.get("heartbeat") is True
            sock.settimeout(protocol.HEARTBEAT_TIMEOUT_S if heartbeat else None)
            reason, name = self._check(hello)
            replaced = None
            if reason is None:
                with self.lock:
                    old = self.connections.get(name)
                    if not self.running or old is not None and (old.host is None or old.host != _peer_host(sock)):
                        reason = "name"
                    else:
                        # Derselbe Name vom selben Rechner: Die alte Verbindung ist
                        # abgerissen, ohne dass es schon auffiel (WLAN kurz weg).
                        replaced = old
                        conn = self.connections[name] = Connection(sock, heartbeat)
            if replaced is not None:
                replaced.close()  # ihr Lese-Thread meldet kein "leave", der Name ist ja wieder da
            if reason is not None:
                sock.sendall(protocol.encode({"type": "reject", "reason": reason, "version": self.version}))
                return
            conn.send({"type": "welcome", "session": self.session, "version": self.version,
                       "heartbeat": heartbeat})
            self.events.put(("join", name))
            while self.running:
                message = reader.read()
                if message is None:
                    break
                if message["type"] in ("answer", "paper"):
                    self.events.put((message["type"], name, message))
        except (OSError, protocol.ProtocolError):
            pass
        finally:
            mine = False
            if conn is not None:
                with self.lock:
                    mine = self.connections.get(name) is conn
                    if mine:
                        del self.connections[name]
                conn.close()
            else:
                _close(sock)
            if mine:
                self.events.put(("leave", name))

    def _check(self, hello: dict):
        """(Ablehnungsgrund oder None, bereinigter Name)."""
        name = protocol.clean_name(hello.get("name"))
        if hello.get("proto") != protocol.PROTOCOL_VERSION:
            return "proto", name
        if str(hello.get("pin", "")).strip() != self.pin:
            return "pin", name
        if not name:
            return "name", name
        return None, name

    # --- Für die Oberfläche -------------------------------------------------------
    def names(self) -> list:
        with self.lock:
            return list(self.connections)

    def broadcast(self, message: dict) -> None:
        with self.lock:
            connections = list(self.connections.values())
        for conn in connections:
            conn.send(message)

    def poll(self):
        """Alle bisher eingegangenen Ereignisse, ohne zu warten."""
        events = []
        while True:
            try:
                events.append(self.events.get_nowait())
            except queue.Empty:
                return events



def _peer_host(sock):
    try:
        return sock.getpeername()[0]
    except OSError:
        return None


def _close(sock) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
