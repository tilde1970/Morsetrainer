"""Teilnehmerseite: Verbindung zum Trainer und Suche im lokalen Netz.

Verbindungsaufbau, Lesen und Senden laufen in eigenen Threads; die
Oberfläche holt die Ereignisse mit poll() ab:
    ("welcome", session, version)  angenommen; version: die des Trainers (oder None)
    ("reject", reason, version)    abgelehnt (protocol.REJECT_REASONS)
    ("error", text)        Verbindung kam nicht zustande
    ("message", message, t)  Nachricht vom Trainer (start, item, replay, close,
                           end); t = Eingang (time.time()), unabhängig davon,
                           wann die Oberfläche abholt
    ("closed",)            Verbindung beendet (vom Trainer oder abgerissen)"""
import json
import queue
import socket
import threading
import time

from morsetrainer.net import protocol

CONNECT_TIMEOUT_S = 5.0
# So lange wird auf Antworten auf die Suche gewartet.
DISCOVER_TIMEOUT_S = 1.0


class TraineeClient:
    def __init__(self):
        self.events = queue.Queue()
        self.outbox = queue.Queue()
        self.sock = None
        self.closing = False
        self.stopped = threading.Event()

    def connect(self, host: str, port: int, name: str, pin: str, version=None) -> None:
        """Baut die Verbindung im Hintergrund auf; das Ergebnis kommt als
        Ereignis. `version`: eigene Programmversion (für den Trainer)."""
        threading.Thread(target=self._run, args=(host, port, name, pin, version), daemon=True).start()

    def _run(self, host, port, name, pin, version) -> None:
        try:
            sock = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_S)
        except OSError as exc:
            self.events.put(("error", str(exc)))
            return
        if self.closing:
            _close(sock)
            return
        self.sock = sock
        protocol.enable_keepalive(sock)
        reader = protocol.LineReader(sock)
        welcomed = False
        try:
            sock.sendall(protocol.encode({"type": "hello", "proto": protocol.PROTOCOL_VERSION,
                                          "name": name, "pin": pin, "version": version, "heartbeat": True}))
            reply = reader.read()
            if reply is None:
                self.events.put(("error", "closed"))
                return
            if reply["type"] == "reject":
                self.events.put(("reject", reply.get("reason"), _version(reply)))
                return
            if reply["type"] != "welcome":
                self.events.put(("error", reply["type"]))
                return
            # Trainer mit Lebenszeichen: kommt so lange gar nichts, ist er weg.
            heartbeat = reply.get("heartbeat") is True
            sock.settimeout(protocol.HEARTBEAT_TIMEOUT_S if heartbeat else None)
            welcomed = True
            self.events.put(("welcome", str(reply.get("session", "")), _version(reply)))
            threading.Thread(target=self._write_loop, args=(sock,), daemon=True).start()
            if heartbeat:
                threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            while True:
                message = reader.read()
                if message is None:
                    break
                if message["type"] != "ping":
                    self.events.put(("message", message, time.time()))
        except (OSError, protocol.ProtocolError) as exc:
            if not welcomed:
                self.events.put(("error", str(exc)))
        finally:
            self.stopped.set()
            self.outbox.put(None)
            _close(sock)
            if welcomed:
                self.events.put(("closed",))

    def _write_loop(self, sock) -> None:
        while True:
            data = self.outbox.get()
            if data is None:
                return
            try:
                sock.sendall(data)
            except OSError:
                _close(sock)
                return

    def _heartbeat_loop(self) -> None:
        while not self.stopped.wait(protocol.HEARTBEAT_INTERVAL_S):
            self.send(protocol.PING)

    def send(self, message: dict) -> None:
        self.outbox.put(protocol.encode(message))

    def close(self) -> None:
        self.closing = True
        self.stopped.set()
        self.outbox.put(None)
        if self.sock is not None:
            _close(self.sock)

    def poll(self):
        events = []
        while True:
            try:
                events.append(self.events.get_nowait())
            except queue.Empty:
                return events


def discover(timeout: float = DISCOVER_TIMEOUT_S, port: int = protocol.DISCOVERY_PORT):
    """Sucht Trainer im lokalen Netz: [(Sitzungsname, Host, Port)], jede
    Adresse einmal. Blockiert `timeout` Sekunden (im Thread aufrufen)."""
    found = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Broadcast erreicht den eigenen Rechner nicht überall; localhost
        # zusätzlich, damit Trainer und Teilnehmer auf einem Rechner (zum
        # Ausprobieren) sich finden.
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                sock.sendto(protocol.DISCOVER_QUERY, (target, port))
            except OSError:
                pass
        end = time.monotonic() + timeout
        while (remaining := end - time.monotonic()) > 0:
            sock.settimeout(remaining)
            try:
                data, (host, _) = sock.recvfrom(1024)
                reply = json.loads(data.decode("utf-8"))
                session, tcp_port = str(reply["session"]), int(reply["port"])
            except socket.timeout:
                break
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                continue
            found.setdefault((host, tcp_port), session)
    finally:
        sock.close()
    # Derselbe Rechner über localhost und seine Netzadresse: nur einmal.
    local = protocol.local_address()
    for host, tcp_port in list(found):
        if host.startswith("127.") and (local, tcp_port) in found:
            del found[(host, tcp_port)]
    return sorted((session, host, tcp_port) for (host, tcp_port), session in found.items())

def _version(reply: dict):
    version = reply.get("version")
    return version[:20] if isinstance(version, str) else None


def _close(sock) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
