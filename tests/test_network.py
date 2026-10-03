"""Tests für den Netzwerkmodus: Protokoll, Auswertung beim Trainer, echte
Verbindungen über localhost und ein ganzer Durchgang Trainer ↔ Teilnehmer
im Reiter (mit Tk-Fenster, ohne Ton; ohne Anzeige übersprungen)."""
import socket
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import stats
from morsetrainer.net import client as net_client
from morsetrainer.net import protocol, scoreboard
from morsetrainer.net.scoreboard import (
    Scoreboard, evaluate, solution_cells, solution_columns, solution_rows, solution_text,
)
from morsetrainer.net.server import TrainerServer


def wait_for(condition, timeout=3.0, pump=None):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pump is not None:
            pump()
        if condition():
            return True
        time.sleep(0.02)
    return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


class ProtocolTest(unittest.TestCase):
    def test_parse_address(self):
        self.assertEqual(protocol.parse_address(" 192.168.1.20 "), ("192.168.1.20", protocol.DEFAULT_PORT))
        self.assertEqual(protocol.parse_address("pc:7400"), ("pc", 7400))
        for bad in ("", "pc:", ":7400", "pc:x", "pc:70000"):
            self.assertIsNone(protocol.parse_address(bad), bad)

    def test_clean_name(self):
        self.assertEqual(protocol.clean_name("  DL4YM\n"), "DL4YM")
        self.assertEqual(protocol.clean_name("A" * 50), "A" * protocol.NAME_MAX)
        self.assertEqual(protocol.clean_name(None), "")

    def test_decode_rejects_garbage(self):
        for line in (b"{", b"[]", b'{"n": 1}', b"\xff"):
            with self.assertRaises(protocol.ProtocolError):
                protocol.decode(line)
        self.assertEqual(protocol.decode(protocol.encode({"type": "end"}).strip()), {"type": "end"})


class ScoreboardTest(unittest.TestCase):
    def test_evaluate_ignores_case_and_spaces(self):
        result = evaluate("CQ DE DL4YM", "cq de dl4ym")
        self.assertTrue(result.correct)
        self.assertEqual((result.correct_chars, result.total), (9, 9))

    def test_missing_and_extra_characters_count_once(self):
        self.assertEqual(evaluate("KMRSU", "KRSU").correct_chars, 4)
        self.assertEqual(evaluate("KMR", "KMRX").correct_chars, 2)

    def test_record_only_first_answer_of_present_participants(self):
        board = Scoreboard()
        board.add_item(1, "KMR", {"A"})
        self.assertIsNone(board.record("B", 1, "KMR"))   # beim Senden nicht dabei
        self.assertIsNone(board.record("A", 2, "KMR"))   # unbekannte Nummer
        self.assertIsNotNone(board.record("A", 1, "KMS", 0.8))
        self.assertIsNone(board.record("A", 1, "KMR"))   # nur die erste Antwort zählt
        self.assertFalse(board.answers["A"][1].correct)

    def test_oversized_answer_is_cut(self):
        # Ein fremdes Programm im Netz soll die Oberfläche nicht einfrieren.
        board = Scoreboard()
        board.add_item(1, "KMR", {"A", "B"})
        self.assertEqual(len(board.record("A", 1, "X" * 60000).typed), scoreboard.TYPED_MAX)
        self.assertEqual(board.record_paper("B", 1, ["KMR"]).typed, "")

    def test_unanswered_counts_as_missed_but_not_as_confusion(self):
        board = Scoreboard()
        board.add_item(1, "KMR", {"A", "B"})
        board.add_item(2, "UR", {"A", "B"})
        board.record("A", 1, "KMS", 1.0)
        board.record("A", 2, "UR", 0.5)
        board.record("B", 2, "UR", "kaputt")
        self.assertEqual(board.summary("A")["chars_correct"], 4)
        self.assertEqual(board.summary("B"), {"items": 2, "answered": 1, "correct_items": 1, "fluent_items": 0, "chars_correct": 2,
                                              "chars_total": 5, "latency": None})
        self.assertAlmostEqual(board.accuracy(), 6 / 10)
        self.assertEqual(board.confusions(), [("R", "S", 1)])

    def test_weak_chars_need_enough_samples(self):
        board = Scoreboard()
        for n in range(1, 4):
            board.add_item(n, "KM", {"A"})
            board.record("A", n, "KS" if n < 3 else "KM")
        self.assertEqual(board.weak_chars(), [("M", 1 - 1 / 3, 3)])
        board.add_item(4, "X", {"A"})
        board.record("A", 4, "")
        self.assertNotIn("X", [ch for ch, _, _ in board.weak_chars()])
        # Mit zwei Teilnehmern braucht die Gruppe doppelt so viele Exemplare,
        # der Einzelne nicht.
        board.add_participant("B")
        self.assertEqual(board.weak_chars(), [])
        self.assertEqual(board.weak_chars(name="A"), [("M", 1 - 1 / 3, 3)])

    def test_confusions_per_participant(self):
        board = Scoreboard()
        board.add_item(1, "SH", {"A", "B"})
        board.record("A", 1, "HH")
        board.record("B", 1, "SS")
        self.assertEqual(board.confusions(name="A"), [("S", "H", 1)])
        self.assertEqual(len(board.confusions()), 2)

    def test_tempo_advice_uses_only_the_current_tempo(self):
        board = Scoreboard()
        for n in range(1, 11):  # 10 × 5 Zeichen bei 20/10, alle flüssig
            board.add_item(n, "KMRSU", {"A"}, 20, 10)
            board.record("A", n, "KMRSU", 0.5)
        self.assertEqual(board.tempo_advice(), ((20, 10), 1.0, 1))
        board.add_item(11, "KMRSU", {"A"}, 20, 11)
        self.assertIsNone(board.tempo_advice())  # neues Tempo, noch zu wenig
        for n in range(12, 22):
            board.add_item(n, "KMRSU", {"A"}, 20, 11)
            board.record("A", n, "KMRSU" if n % 3 else "KMRS", 0.5)
        (_, share, step) = board.tempo_advice()
        self.assertLess(share, 0.75)
        self.assertEqual(step, -1)

    def test_fluent_needs_first_hearing_and_answer_window(self):
        board = Scoreboard()
        board.add_item(1, "KMR", {"A", "B", "C", "D"})
        board.record("A", 1, "KMR", 1.0)
        board.record("B", 1, "KMR", 8.0)   # Zeitfenster für 3 Zeichen: 3,3 s
        board.record("C", 1, "KMR")         # Zeit unbekannt
        board.mark_replayed(1)
        board.record("D", 1, "KMR", 0.5)    # erst nach der Wiederholung
        answers = {name: board.answers[name][1] for name in "ABCD"}
        self.assertEqual([r.fluent for r in answers.values()], [True, False, False, False])
        self.assertTrue(answers["B"].slow)
        self.assertTrue(answers["D"].replayed)
        self.assertFalse(answers["A"].replayed)
        self.assertEqual(board.fluency(), 1 / 4)
        self.assertEqual(board.summary("D")["correct_items"], 1)
        self.assertIn(";KMR ~ (8,0 s)", board.csv_text(("N", "%", "ok", "fl", "s", "e", "w")))

    def test_paper_counts_without_timing(self):
        board = Scoreboard()
        for n in range(1, 11):
            board.add_item(n, "KMRSU", {"A"}, 20, 10)
            board.record("A", n, "KMRSU", 0.5)
        board.mark_replayed(3)
        # Bogen ohne Rechner: leere Zeile = verpasst, derselbe Name ersetzt.
        self.assertTrue(board.add_paper("P", {1: "KMRSU", 2: "KMRSS", 3: "kmrsu"}))
        self.assertTrue(board.add_paper("P", {1: "KMRSU", 2: "KMRSS", 3: "KMRSU", 4: ""}))
        data = board.summary("P")
        self.assertEqual((data["items"], data["correct_items"], data["fluent_items"]), (10, 2, 0))
        self.assertIsNone(data["latency"])
        self.assertTrue(board.answers["P"][3].replayed)
        self.assertNotIn(4, board.answers["P"])
        self.assertEqual(board.confusions(name="P"), [("U", "S", 1)])
        # Flüssig und Tempo-Empfehlung nur aus den Antworten am Rechner.
        self.assertEqual(board.fluency(), 1.0)
        self.assertEqual(board.tempo_advice(), ((20, 10), 1.0, 1))
        self.assertLess(board.accuracy(), 1.0)
        # Wer am Rechner geantwortet hat, bekommt keinen Papierbogen.
        self.assertFalse(board.add_paper("A", {1: "KMRSU"}))
        self.assertIsNone(board.record_paper("A", 1, "KMRSU"))
        self.assertIsNone(board.record_paper("P", 99, "KMRSU"))
        line = board.csv_text(("N", "%", "ok", "fl", "s", "e", "w")).splitlines()[2]
        self.assertTrue(line.startswith("P;28;2/10;–;;"), line)
        self.assertIn(";KMRSU;KMRSS ✗;KMRSU;", line)

    def test_answer_sheet(self):
        from morsetrainer.core import answer_sheet
        self.assertEqual(answer_sheet.pages(3, 2, rows=2), [[[1, 2], [3]]])
        self.assertEqual(answer_sheet.pages(5, 1, rows=2), [[[1, 2]], [[3, 4]], [[5]]])
        page = answer_sheet.answer_sheet_html(60, 5, title="Kurs <1>", details="Gruppen · 20 WPM",
                                              labels={"hint": "Lücke lassen"})
        self.assertIn("Kurs &lt;1&gt;", page)
        self.assertEqual(page.count('class="page"'), 1)  # 3 Spalten × 25 Zeilen
        self.assertEqual(page.count('class="row"'), 60)
        self.assertEqual(page.count('class="box"'), 300)
        self.assertEqual(page.count("<h1>"), 1)
        page = answer_sheet.answer_sheet_html(60, None)
        self.assertEqual(page.count('class="page"'), 2)  # freie Linien: 2 Spalten
        self.assertEqual(page.count("<h1>"), 1)  # Kopf nur auf Seite 1

    def test_csv_has_one_column_per_sequence(self):
        board = Scoreboard()
        board.add_item(1, "KMR", {"A"}, 20, 10)
        board.add_participant("B")
        board.add_item(2, "UR", {"A", "B"}, 20, None)
        board.mark_replayed(2)
        board.record("A", 1, "KMR", 1.25)
        board.record("B", 2, "US")
        lines = board.csv_text(("Name", "%", "ok", "fl", "s", "e", "w")).splitlines()
        self.assertEqual(lines[0], "Name;%;ok;fl;s;e;w;1: KMR (20/10 WPM);2: UR (20 WPM) ↻")
        self.assertEqual(lines[1], "A;60;1/2;1/2;1,2;;;KMR (1,2 s);")
        self.assertEqual(lines[2], "B;50;0/1;0/1;;R→S 1×;;–;US ✗")

    def test_solution_is_numbered_down_the_columns(self):
        board = Scoreboard()
        for n, text in enumerate(("KMR", "UR", "CQ DE DL4YM", "S", "H+"), start=1):
            board.add_item(n, text, set())
        board.mark_replayed(2)
        cells = solution_cells(board)
        self.assertEqual(cells[1], (2, "2. UR ↻"))
        self.assertEqual(cells[4], (5, "5. H+"))
        rows = solution_rows(cells, 2)
        self.assertEqual([[n for n, _ in row] for row in rows], [[1, 4], [2, 5], [3]])
        self.assertEqual(solution_text(cells, 2).splitlines(),
                         ["1. KMR" + " " * 12 + "4. S", "2. UR ↻" + " " * 11 + "5. H+", "3. CQ DE DL4YM"])
        self.assertEqual(solution_rows([], 3), [])
        # Zehn Zeilen je Spalte, höchstens fünf Spalten; Nummern rechtsbündig.
        self.assertEqual([solution_columns(count) for count in (0, 1, 10, 11, 25, 200)], [1, 1, 1, 2, 3, 5])
        board.add_item(10, "K", set())
        self.assertEqual(solution_cells(board)[0][1], " 1. KMR")


class StreamTest(unittest.TestCase):
    """Kontinuierlicher Durchgang: Zeitachse und Auswertung (net/stream.py)."""

    def setUp(self):
        from morsetrainer.net import stream
        self.stream = stream
        self.entries, self.seconds = stream.timeline(["KMR", "SU"], 20)

    def keys(self, delays):
        """Tastenzeiten: je gesendetes Zeichen Tonende + Verzögerung."""
        return [100.0 + end + delay for (_, end, _), delay in zip(self.entries, delays)]

    def test_timeline_has_word_gap_between_groups(self):
        chars = [(char, group) for char, _, group in self.entries]
        self.assertEqual(chars, [("K", 0), ("M", 0), ("R", 0), ("S", 1), ("U", 1)])
        ends = [end for _, end, _ in self.entries]
        self.assertEqual(ends, sorted(ends))
        self.assertGreater(ends[3] - ends[2], ends[2] - ends[1])  # Wortpause
        self.assertGreater(self.seconds, ends[-1])

    def test_groups_fill_the_duration(self):
        from morsetrainer.modes.content import ItemSource
        groups = self.stream.make_groups(ItemSource("groups", "KMRSU", 5), 30, 20)
        self.assertTrue(all(len(group) == 5 for group in groups))
        self.assertGreaterEqual(self.stream.timeline(groups, 20)[1], 30)
        self.assertLess(self.stream.timeline(groups[:-1], 20)[1], 30)

    def test_evaluate_per_group_with_timing(self):
        chars, groups = self.stream.evaluate(self.entries, 100.0, "KMRSU", self.keys([0.5] * 5))
        self.assertEqual(groups, {0: ("KMR", 0.5), 1: ("SU", 0.5)})
        self.assertTrue(all(correct for _, _, correct, _ in chars))

    def test_guessed_or_missing_keys_do_not_count(self):
        # S vor seinem Ton getippt (vorausgeraten), U fehlt.
        chars, groups = self.stream.evaluate(self.entries, 100.0, "KMXS", self.keys([0.5, 0.5, 0.5, -1.0]))
        self.assertEqual(groups[0], ("KMX", 0.5))
        self.assertEqual(groups[1], ("", None))
        self.assertEqual([correct for _, _, correct, _ in chars], [True, True, False, False, False])

    def test_player_mixes_band_conditions_under_everything(self):
        import contextlib
        import numpy as np
        from morsetrainer.core import band

        written = []

        class FakeStream:
            latency = 0.0

            def write(self, block):
                written.append(np.array(block))

        with mock.patch.object(self.stream.audio, "output_stream", lambda: contextlib.nullcontext(FakeStream())):
            before = time.time()
            player = self.stream.Player(["KMR", "SU"], 20, 600, None, band.preset_conditions("light", 600))
            player.thread.join(timeout=5)
        self.assertIsNone(player.error)
        # Rauschen schon im Vorlauf und in der Wortpause, der Ton beginnt danach.
        self.assertGreater(np.abs(written[0]).max(), 0)
        self.assertGreaterEqual(player.start - before, band.PRESET_LEAD_SECONDS[0])
        audio = np.concatenate(written)
        gap_start = int((band.PRESET_LEAD_SECONDS[0] + self.entries[2][1] + 0.05) * 48000)
        self.assertGreater(np.abs(audio[gap_start:gap_start + 2000]).max(), 0)

    def test_stop_drops_groups_not_yet_started(self):
        stopped = 100.0 + self.entries[2][1] + 0.1  # nach R, vor S
        _, groups = self.stream.evaluate(self.entries, 100.0, "KMR", self.keys([0.05] * 3), stopped_at=stopped)
        self.assertEqual(list(groups), [0])
        self.assertEqual(self.stream.kept_groups(self.entries, 100.0, stopped), {0})


class ConnectionTest(unittest.TestCase):
    def setUp(self):
        self.server = TrainerServer("Kurs", "4711")
        self.server.start(0)
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.server.stop()

    def join(self, name, pin="4711"):
        client = net_client.TraineeClient()
        client.connect("127.0.0.1", self.server.port, name, pin)
        self.clients.append(client)
        events = []
        self.assertTrue(wait_for(lambda: events.extend(client.poll()) or events))
        return client, events[0]

    def server_events(self, count):
        events = []
        self.assertTrue(wait_for(lambda: events.extend(self.server.poll()) or len(events) >= count))
        return events

    def test_admission(self):
        _, event = self.join("DL4YM")
        self.assertEqual(event, ("welcome", "Kurs", None))
        self.assertEqual(self.join("DK1AB", pin="0000")[1], ("reject", "pin", None))
        self.assertEqual(self.join("DL4YM")[1], ("reject", "name", None))
        self.assertEqual(self.join("  ")[1], ("reject", "name", None))
        self.assertEqual(self.server_events(1), [("join", "DL4YM")])
        self.assertEqual(self.server.names(), ["DL4YM"])

    def test_wrong_protocol_version_is_rejected(self):
        with socket.create_connection(("127.0.0.1", self.server.port)) as sock:
            sock.sendall(protocol.encode({"type": "hello", "proto": 99, "name": "DL4YM", "pin": "4711"}))
            sock.settimeout(2)
            self.assertEqual(protocol.LineReader(sock).read(), {"type": "reject", "reason": "proto", "version": None})

    def test_broadcast_answer_and_reconnect(self):
        first, _ = self.join("DL4YM")
        second, _ = self.join("DK1AB")
        self.server_events(2)
        self.server.broadcast({"type": "item", "n": 1, "text": "KMR"})
        for client in (first, second):
            events = []
            self.assertTrue(wait_for(lambda: events.extend(client.poll()) or events))
            self.assertEqual(events[0][:2], ("message", {"type": "item", "n": 1, "text": "KMR"}))
        first.send({"type": "answer", "n": 1, "typed": "KMR", "latency": 0.5})
        self.assertEqual(self.server_events(1), [("answer", "DL4YM", {"type": "answer", "n": 1, "typed": "KMR",
                                                                     "latency": 0.5})])
        first.close()
        self.assertEqual(self.server_events(1), [("leave", "DL4YM")])
        # Nach dem Abriss darf derselbe Name wieder rein.
        self.assertEqual(self.join("DL4YM")[1], ("welcome", "Kurs", None))

    def test_client_notices_when_trainer_stops(self):
        client, _ = self.join("DL4YM")
        self.server.stop()
        events = []
        self.assertTrue(wait_for(lambda: events.extend(client.poll()) or ("closed",) in events))

    def test_unreachable_trainer_reports_error(self):
        client = net_client.TraineeClient()
        client.connect("127.0.0.1", free_port(), "DL4YM", "4711")
        events = []
        self.assertTrue(wait_for(lambda: events.extend(client.poll()) or events))
        self.assertEqual(events[0][0], "error")

    def test_connections_use_keepalive(self):
        # Abgerissene Verbindungen (WLAN weg) fallen so nach etwa einer halben Minute auf.
        client, _ = self.join("DL4YM")
        self.assertTrue(wait_for(lambda: client.sock is not None))
        conn = self.server.connections["DL4YM"]
        for sock in (client.sock, conn.sock):
            self.assertTrue(sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE))
            if hasattr(socket, "TCP_KEEPIDLE"):
                self.assertEqual(sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE), protocol.KEEPALIVE_IDLE_S)

    def test_garbage_does_not_crash_the_server(self):
        with socket.create_connection(("127.0.0.1", self.server.port)) as sock:
            sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
            sock.settimeout(2)
            self.assertEqual(sock.recv(100), b"")  # Verbindung zu
        self.assertEqual(self.join("DL4YM")[1], ("welcome", "Kurs", None))


class NetworkTabTest(unittest.TestCase):
    """Trainer und Teilnehmer als zwei Reiter in einem Fenster."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(stats, "STATS_DIR", directory),
            mock.patch.object(stats, "ALL_TIME_FILE", directory / "all_time.json"),
            mock.patch.object(stats, "RESET_FILE", directory / "reset.json"),
            mock.patch.object(stats, "RESULTS_FILE", directory / "results.jsonl"),
        ]
        for patch in self.patches:
            patch.start()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("keine Anzeige")
        self.root.withdraw()
        from morsetrainer.modes.network_mode import TRAINER, NetworkModeFrame
        self.charset = tk.StringVar(value="KMRSU")
        self.wpm, self.freq = tk.IntVar(value=20), tk.IntVar(value=600)
        self.stops = []
        self.practice = []
        self.tempo_steps = []

        def make(role):
            frame = NetworkModeFrame(ttk_frame(self.root), self.charset, self.wpm, self.freq, tk.BooleanVar(),
                                     lambda: None, lambda: None, lambda: self.stops.append(role),
                                     practice_start=lambda: self.practice.append((role, "start")),
                                     practice_stop=lambda: self.practice.append((role, "stop")),
                                     adjust_tempo=lambda d: self.tempo_steps.append(d) or ("20 WPM", "21 WPM"))
            frame.role_var.set(role)
            frame._show_role()
            frame.signs_var.set(False)  # sonst kommt die erste Sequenz erst nach VVV =
            return frame
        self.trainer = make(TRAINER)
        self.trainee = make("trainee")

    def tearDown(self):
        if hasattr(self, "root"):
            self.trainee.on_close()
            self.trainer.on_close()
            self.root.destroy()
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def pump(self):
        self.root.update()

    def connect(self):
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        self.assertIsNotNone(self.trainer.server)
        self.trainee.name_var.set("DL4YM")
        self.trainee.pin_var.set(self.trainer.server.pin)
        self.trainee.address_var.set(f"127.0.0.1:{self.trainer.port_var.get()}")
        self.trainee.connect()
        self.assertTrue(wait_for(lambda: self.trainee.connected and "DL4YM" in self.trainer.board.names,
                                 pump=self.pump))

    def test_run_with_own_text(self):
        self.connect()
        self.assertTrue(self.trainee.running)
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", "cq de dl4ym\n\nKMR\n")
        self.trainer.start_run()
        self.assertEqual(self.trainer.planned, 2)
        self.assertTrue(wait_for(lambda: self.trainee.current is not None, pump=self.pump))
        self.assertEqual(self.trainee.current["text"], "CQ DE DL4YM")
        self.assertEqual(self.trainee.current["wpm"], 20)

        # Während des Tons Enter: gewertet wird erst danach.
        self.trainee.input_var.set("CQ DE DL4YM")
        self.trainee.playing = True
        self.trainee.on_submit()
        self.assertFalse(self.trainee.answered)
        self.trainee._playback_done()
        self.assertTrue(self.trainee.answered)
        # Alle haben geantwortet: Sequenz zu, die Tabelle zeigt es.
        self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
        self.assertTrue(self.trainer.board.answers["DL4YM"][1].correct)
        self.assertIn("✓ CQDEDL4YM", self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"][2])

        self.trainer.advance()
        self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
        # So viele Zeichen wie gesendet: fertig ohne Enter.
        self.trainee.playing = False
        self.trainee.input_var.set("KMS")
        self.pump()
        self.assertTrue(self.trainee.answered)
        self.assertIn("gesendet", self.trainee.diff_var.get())
        self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
        self.trainer.advance()  # zwei von zwei gesendet: Ende
        self.assertFalse(self.trainer.run_active)
        self.assertTrue(wait_for(lambda: self.trainee.session_stats is None, pump=self.pump))
        self.assertIn("1 von 2", self.trainee.trainee_status_var.get())
        self.assertEqual(self.trainer.board.confusions(), [("R", "S", 1)])
        self.assertIn("Gruppe: 92", self.trainer.group_var.get())
        self.assertTrue(list(Path(self.tmp.name).glob("20*-network.jsonl")))

        self.trainer.export_csv()
        exported = list(Path(self.tmp.name).glob("*-netzwerk.csv"))
        self.assertEqual(len(exported), 1)
        self.assertIn("DL4YM;92;1/2", exported[0].read_text(encoding="utf-8-sig"))

    def start_custom(self, text):
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", text)
        self.trainer.start_run()
        self.assertTrue(wait_for(lambda: self.trainee.current is not None, pump=self.pump))
        self.trainee.playing = False

    def test_replay_for_all_is_not_fluent(self):
        self.connect()
        self.start_custom("KMR\n")
        self.trainer.replay_for_all()
        self.assertTrue(wait_for(lambda: self.trainee.replayed, pump=self.pump))
        self.trainee.playing = False
        self.trainee.input_var.set("KMR")
        self.trainee.on_submit()
        self.assertIn("mit Wiederholung", self.trainee.feedback_var.get())
        self.assertTrue(wait_for(lambda: "DL4YM" in self.trainer.board.answered(1), pump=self.pump))
        result = self.trainer.board.answers["DL4YM"][1]
        self.assertTrue(result.correct and result.replayed and not result.fluent)
        self.assertIn("(wiederholt)", self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"][2])
        # Eigene Statistik: richtig, aber mit angenommener (doppelter) Latenz.
        rounds = self.trainee.session_stats.rounds
        self.assertTrue(all(r["correct"] and r.get("latency_assumed") for r in rounds))

    def test_answer_sent_before_replay_counts_as_first_hearing(self):
        self.connect()
        self.start_custom("KMR\n")
        self.trainee.input_var.set("KMR")
        self.trainee.on_submit()
        time.sleep(0.2)  # angekommen, aber noch nicht abgeholt
        self.trainer.replay_for_all()
        self.assertFalse(self.trainer.board.answers["DL4YM"][1].replayed)

    def test_latency_per_character_from_keystrokes(self):
        self.connect()
        self.start_custom("KM\n")
        now = time.time()
        # Ton schon vorbei: K endete vor 1,0 s, M vor 0,5 s.
        self.trainee.play_start = now - 2.0
        self.trainee.tone_starts, self.trainee.tone_ends = [now - 2.0, now - 1.2], [now - 1.5, now - 0.5]
        self.trainee.tone_end = now - 0.5
        self.trainee.input_var.set("K")
        self.trainee.key_times = [now - 1.3]
        self.trainee.input_var.set("KM")
        self.trainee.key_times[1] = now - 0.2
        self.trainee.on_submit()
        latencies = [r["latency_s"] for r in self.trainee.session_stats.rounds]
        self.assertAlmostEqual(latencies[0], 0.2, places=1)
        self.assertAlmostEqual(latencies[1], 0.3, places=1)
        self.assertTrue(self.trainee.last_result.fluent)

    def test_slow_answer_is_marked(self):
        self.connect()
        self.start_custom("KM\n")
        self.trainee.tone_end = time.time() - 10
        self.trainee.input_var.set("KM")
        self.trainee.on_submit()
        self.assertIn("zu langsam", self.trainee.feedback_var.get())
        self.assertTrue(wait_for(lambda: "DL4YM" in self.trainer.board.answered(1), pump=self.pump))
        self.assertTrue(self.trainer.board.answers["DL4YM"][1].slow)

    def test_solution_is_played_after_a_mistake(self):
        from morsetrainer.core import audio
        self.connect()
        self.trainer.auto_var.set(False)
        self.start_custom("KM\nUR\n")
        with mock.patch.object(audio, "play") as play:
            self.trainee.input_var.set("KS")
            self.trainee.on_submit()
            self.assertTrue(wait_for(lambda: play.called, pump=self.pump))
        self.assertIn("Lösung", self.trainee.trainee_status_var.get())
        self.assertEqual(str(self.trainee.entry.cget("state")), "disabled")
        # Richtig und flüssig: nichts vorspielen.
        self.trainer.advance()
        self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
        self.trainee.playing = False
        with mock.patch.object(audio, "play") as play:
            self.trainee.input_var.set("UR")
            self.trainee.on_submit()
            self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
            self.pump()
            self.assertFalse(play.called)

    def test_practice_time_counts_only_during_a_run(self):
        self.connect()
        self.assertEqual(self.practice, [])
        self.start_custom("KM\n")
        self.assertEqual(self.practice, [("trainee", "start")])
        self.trainer.stop_run()
        self.assertTrue(wait_for(lambda: ("trainee", "stop") in self.practice, pump=self.pump))
        self.assertTrue(self.trainee.running)  # Reiter bleiben gesperrt, solange verbunden

    def test_trainer_led_run_counts_for_club_award_only(self):
        from morsetrainer.core import awards
        closed = []
        self.trainer.session_closed = lambda: closed.append(True)
        self.connect()
        self.start_custom("KM\n")
        self.trainer.stop_run()
        led = list(stats._read_jsonl(stats.RESULTS_FILE))
        self.assertEqual([(r["mode"], r["role"], r["participants"]) for r in led], [("network", "trainer", 1)])
        self.assertNotIn(("trainer", "start"), self.practice)  # keine Übungszeit
        self.assertFalse(any(e.get("mode") == "network" and e["total"] == 0 for e in stats.load_history()))
        self.assertGreaterEqual(led[0]["duration_s"], 0)
        trainer_only = awards.load_data()
        trainer_only.sessions = []  # ohne die Sitzungsdatei des Teilnehmers
        self.assertFalse(awards._club(trainer_only))  # kürzer als 10 Minuten
        with mock.patch.object(awards, "CLUB_MIN_S", 0):
            self.assertTrue(awards.level_dates(awards._club(trainer_only), (1,))[0])
        self.trainer.close_session()
        self.assertEqual(closed, [True])

    def test_trainer_alone_is_no_club_night(self):
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", "KM\n")
        self.trainer.start_run()
        self.trainer.stop_run()
        self.assertEqual(list(stats._read_jsonl(stats.RESULTS_FILE)), [])

    def test_function_keys_only_for_the_trainer(self):
        self.connect()
        self.trainee.on_function_key("F5")  # Teilnehmer: nichts
        self.assertFalse(self.trainer.run_active)
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", "KM\nUR\n")
        self.trainer.on_function_key("F5")
        self.assertTrue(self.trainer.run_active)
        self.trainer.on_function_key("F6")
        self.assertIn(1, self.trainer.board.replayed)
        self.trainer.on_function_key("F7")
        self.assertEqual(self.trainer.item["n"], 2)
        self.trainer.on_function_key("F5")
        self.assertFalse(self.trainer.run_active)

    def test_details_of_the_selected_participant(self):
        self.connect()
        self.start_custom("SH\n")
        self.trainee.input_var.set("HH")
        self.trainee.on_submit()
        self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
        self.assertIn("anklicken", self.trainer.detail_var.get())
        self.trainer.tree.selection_set(self.trainer.tree.get_children()[0])
        self.pump()
        self.assertIn("DL4YM: Fehler S→H 1×", self.trainer.detail_var.get())

    def test_qso_plain_text_comes_in_sections_per_qso(self):
        from morsetrainer.core.morse import MORSE_CODE
        from morsetrainer.modes.content import QSO_SECTION_ENDS
        self.trainer.content_var.set("QSO-Klartext")
        self.assertEqual(self.trainer.count_var.get(), 1)
        self.assertEqual(self.trainer.count_label.cget("text"), "Anzahl QSOs:")
        self.charset.set("".join(MORSE_CODE))
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        self.trainer.start_run()
        self.assertTrue(self.trainer.run_active)
        # Ein ganzes QSO, Abschnitt für Abschnitt bis =, K, AR, KN, SK oder BK.
        sections = [self.trainer.item["text"]] + self.trainer.custom_items
        self.assertEqual(self.trainer.planned, len(sections))
        self.assertGreater(len(sections), 10)
        self.assertTrue(sections[0].startswith("CQ "))
        self.assertTrue(all(text.split()[-1] in QSO_SECTION_ENDS for text in sections[:-1]))
        self.trainer.stop_run()
        # Bis Stop: nach dem QSO kommt das nächste.
        self.trainer.count_var.set(0)
        self.trainer.start_run()
        self.trainer.custom_items = []
        self.trainer.next_item()
        self.assertTrue(self.trainer.item["text"].startswith("CQ "))
        self.trainer.stop_run()
        # Zurück zu Gruppen: wieder Sequenzen.
        self.trainer.content_var.set("Gruppen")
        self.assertEqual(self.trainer.count_var.get(), 20)
        self.assertEqual(self.trainer.count_label.cget("text"), "Anzahl Sequenzen:")

    def test_continuous_run(self):
        import contextlib
        from morsetrainer.modes import network_mode

        class FakeStream:
            latency = 0.0

            def write(self, block):
                pass

        self.connect()
        self.trainer.flow_var.set(network_mode.CONTINUOUS)
        self.trainer._show_flow_options()
        self.assertEqual(str(self.trainer.count_spin.cget("state")), "disabled")
        with mock.patch.object(network_mode.net_stream, "make_groups", lambda *args: ["KMR", "SU"]), \
                mock.patch.object(network_mode.net_stream, "FINISH_GRACE_SECONDS", 0), \
                mock.patch.object(network_mode.net_stream.audio, "output_stream",
                                  lambda: contextlib.nullcontext(FakeStream())):
            self.trainer.start_run()
            self.assertTrue(self.trainer.hiding)
            self.assertEqual(sorted(self.trainer.board.items.values()), ["KMR", "SU"])
            self.assertTrue(wait_for(lambda: self.trainee.stream is not None, pump=self.pump))
            self.assertIsNone(self.trainee.current)
            # Mitschreiben, ohne Enter: jede Taste kurz nach ihrem Ton.
            entries, start = self.trainee.stream["entries"], self.trainee.stream["player"].start
            typed = ""
            for char, end, _ in entries:
                self.assertTrue(wait_for(lambda: time.time() >= start + end + 0.1, pump=self.pump))
                typed += "X" if char == "U" else char
                self.trainee.input_var.set(typed)
            self.assertTrue(wait_for(lambda: not self.trainer.run_active, timeout=5, pump=self.pump))
            self.assertTrue(wait_for(lambda: len(self.trainer.board.answers["DL4YM"]) == 2, pump=self.pump))
        answers = self.trainer.board.answers["DL4YM"]
        self.assertTrue(answers[1].correct)
        self.assertEqual(answers[2].typed, "SX")
        self.assertIn("1 von 2 Gruppen richtig", self.trainee.feedback_var.get())
        self.assertEqual(len(self.trainee.results_tree.get_children()), 2)
        self.assertEqual(self.trainer.board.confusions(), [("U", "X", 1)])

    def test_tempo_advice_can_be_applied(self):
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        board = self.trainer.board
        for n in range(1, 11):
            board.add_item(n, "KMRSU", {"A"}, 20, None)
            board.record("A", n, "KMRSU", 0.5)
        self.trainer._refresh_table()
        self.assertIn("Tempo kann steigen", self.trainer.advice_var.get())
        self.assertEqual(self.trainer.advice_button.winfo_manager(), "pack")
        self.trainer.apply_advice()
        self.assertEqual(self.tempo_steps, [1])
        # Zeigt die Kopfleiste schon ein anderes Tempo, gibt es keinen Knopf.
        self.wpm.set(25)
        self.trainer._refresh_table()
        self.assertEqual(self.trainer.advice_button.winfo_manager(), "")

    def test_table_can_be_detached_and_brought_back(self):
        self.connect()
        self.start_custom("SH\nKM\n")
        self.trainee.input_var.set("HH")
        self.trainee.on_submit()
        self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
        self.trainer.tree.selection_set(self.trainer.tree.get_children()[0])
        self.pump()
        self.trainer.detach_table()
        window = self.trainer.table_window
        self.assertIsNotNone(window)
        self.assertEqual(self.trainer.tree.winfo_toplevel(), window)
        self.assertEqual(self.trainer._selected_name(), "DL4YM")  # Auswahl bleibt
        self.assertIn("DL4YM", self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"])
        # Tastenkürzel wirken auch im eigenen Fenster.
        window.focus_force()
        self.pump()
        window.event_generate("<Key>", keysym="F7", when="now")
        self.pump()
        self.assertEqual(self.trainer.item["n"], 2)
        self.trainer.attach_table()
        self.assertIsNone(self.trainer.table_window)
        self.assertFalse(window.winfo_exists())
        self.assertEqual(self.trainer.tree.winfo_toplevel(), self.root)
        self.assertEqual(self.trainer._selected_name(), "DL4YM")

    def test_table_grows_with_participants(self):
        from morsetrainer.modes.network_mode import TABLE_ROWS
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        for i in range(20):
            self.trainer.board.add_participant(f"DL{i}ABC")
            self.trainer._refresh_table()
            expected = min(max(i + 1, TABLE_ROWS[0]), TABLE_ROWS[1])
            self.assertEqual(int(self.trainer.tree.cget("height")), expected)

    def test_phrases_and_qso_text_are_offered(self):
        from morsetrainer.modes.network_mode import CONTENTS
        self.assertEqual(CONTENTS["Wendungen"], "phrases")
        self.assertEqual(CONTENTS["QSO-Klartext"], "qso")

    def test_time_up_submits_what_was_typed(self):
        self.connect()
        self.trainer.content_var.set("Gruppen")
        self.trainer.start_run()
        self.assertTrue(wait_for(lambda: self.trainee.current is not None, pump=self.pump))
        text = self.trainee.current["text"]
        self.trainee.input_var.set(text[:2])
        self.trainer.deadline = time.time() - 1  # Antwortzeit um
        self.assertTrue(wait_for(lambda: self.trainee.answered, pump=self.pump))
        self.assertTrue(wait_for(lambda: "DL4YM" in self.trainer.board.answered(1), pump=self.pump))
        self.assertEqual(self.trainer.board.answers["DL4YM"][1].typed, text[:2])

    def test_trainer_leaving_disconnects_trainee(self):
        self.connect()
        self.trainer.close_session()
        self.assertTrue(wait_for(lambda: self.trainee.client is None, pump=self.pump))
        self.assertIn("beendet", self.trainee.trainee_status_var.get())
        self.assertEqual(self.stops, ["trainee"])
        self.assertFalse(self.trainee.running)

    def start_paced(self, text):
        from morsetrainer.modes.network_mode import PACED
        self.trainer.flow_var.set(PACED)
        self.trainer._show_flow_options()
        self.start_custom(text)

    def test_paced_run_reveals_nothing_until_the_end(self):
        from morsetrainer.core import audio
        self.connect()
        self.trainer.pause_var.set(1)
        self.start_paced("KM\nUR\n")
        self.assertTrue(self.trainee.current["paced"])
        self.assertEqual(self.trainer.trainer_status_var.get(), "Nr. 1 von 2")
        self.assertFalse(self.trainer.custom_frame.winfo_ismapped())  # eigener Text verrät alles
        self.trainee.input_var.set("KS")
        self.trainee.on_submit()
        self.assertEqual(self.trainee.feedback_var.get(), "Nr. 1 notiert")
        self.assertEqual(self.trainee.diff_var.get(), "")
        self.assertEqual(self.trainee.history_var.get(), "")
        self.assertTrue(wait_for(lambda: "DL4YM" in self.trainer.board.answered(1), pump=self.pump))
        # Alle digitalen haben geantwortet, aber auf Papier wird noch geschrieben.
        self.assertTrue(self.trainer.item_open)
        values = self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"]
        self.assertEqual([str(v) for v in values[2:]], ["eingegangen", "", "", ""])
        self.assertEqual(self.trainer.group_var.get(), "")
        self.assertIn("nach dem Durchgang", self.trainer.detail_var.get())
        # Frist um: gleich die nächste, ohne Lösung beim Teilnehmer.
        with mock.patch.object(audio, "play") as play:
            self.trainer.deadline = time.time()
            self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
            self.assertEqual(play.call_count, 1)  # nur die neue Sequenz, keine Lösung
        self.assertEqual(self.trainee.feedback_var.get(), "")
        self.trainer.replay_for_all()  # F6 bleibt, wird in der Auflösung markiert
        self.assertTrue(wait_for(lambda: self.trainee.replayed, pump=self.pump))
        self.trainee.playing = False
        self.trainee.input_var.set("UR")
        self.trainee.on_submit()
        self.trainer.deadline = time.time()
        self.assertTrue(wait_for(lambda: not self.trainer.run_active, pump=self.pump))
        self.assertTrue(wait_for(lambda: self.trainee.session_stats is None, pump=self.pump))
        # Am Ende: Liste mit Lösungen, der erste Fehler ist markiert, anhörbar.
        tree = self.trainee.results_tree
        self.assertTrue(self.trainee.results_card.winfo_ismapped())
        self.assertEqual([tree.item(row)["values"][1:] for row in tree.get_children()],
                         [["KM", "KS", "✗"], ["UR", "UR", "✓ ↻"]])
        self.assertEqual(tree.selection(), ("1",))
        self.assertIn("KM≠KS", self.trainee.history_var.get())
        with mock.patch.object(audio, "play") as play:
            self.trainee.play_result()
            self.assertEqual(play.call_count, 1)
        self.assertIn("Auflösung", self.trainer.trainer_status_var.get())
        self.assertTrue(self.trainer.custom_frame.winfo_ismapped())
        self.assertIn("✓ UR", self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"][2])
        self.assertIn("Gruppe:", self.trainer.group_var.get())

    def test_paper_trainee_types_in_the_copy_at_the_end(self):
        from morsetrainer.core import audio
        self.trainee.paper_var.set(True)
        self.connect()
        self.trainer.pause_var.set(1)
        with mock.patch.object(audio, "play"):
            self.start_paced("KM\nUR\n")
            self.assertTrue(self.trainee.current["paper"])
            self.assertEqual(str(self.trainee.entry.cget("state")), "disabled")
            self.assertEqual(str(self.trainee.paper_check.cget("state")), "disabled")
            self.trainer.replay_for_all()
            self.assertTrue(wait_for(lambda: self.trainee.current["replayed"], pump=self.pump))
            self.trainer.deadline = time.time()
            self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
            self.trainer.deadline = time.time()
            self.assertTrue(wait_for(lambda: not self.trainer.run_active, pump=self.pump))
            self.assertTrue(wait_for(lambda: self.trainee.paper_card.winfo_ismapped(), pump=self.pump))
        self.assertEqual(self.trainer.board.answers["DL4YM"], {})  # nichts während des Durchgangs
        self.assertIn("Mitschrift ab", self.trainee.trainee_status_var.get())
        self.assertEqual(sorted(self.trainee.trainee_sheet.entries), [1, 2])
        self.trainee.trainee_sheet.entries[1].insert(0, "km")
        self.trainee.submit_paper()
        self.assertTrue(wait_for(lambda: 1 in self.trainer.board.answers["DL4YM"], pump=self.pump))
        self.pump()
        self.assertIn("DL4YM", self.trainer.board.paper)
        self.assertNotIn(2, self.trainer.board.answers["DL4YM"])  # leer = verpasst
        values = self.trainer.tree.item(self.trainer.tree.get_children()[0])["values"]
        self.assertEqual(str(values[4]), "Papier")
        tree = self.trainee.results_tree
        self.assertEqual([tree.item(row)["values"][1:] for row in tree.get_children()],
                         [["KM", "KM", "✓ ↻"], ["UR", "–", "✗"]])
        self.assertIn("1 von 2", self.trainee.trainee_status_var.get())
        self.assertEqual(str(self.trainee.paper_check.cget("state")), "normal")
        # Eigene Statistik: im Verlauf, aber nicht in der Zeichenstatistik.
        logs = list(Path(self.tmp.name).glob("20*-network.jsonl"))
        self.assertEqual(len(logs), 1)
        self.assertIn('"char_stats": false', logs[0].read_text(encoding="utf-8"))
        self.assertFalse((Path(self.tmp.name) / "all_time.json").exists())

    def test_trainer_enters_paper_sheets(self):
        self.connect()
        self.trainer.pause_var.set(1)
        self.start_paced("KM\nUR\n")
        self.assertEqual(str(self.trainer.paper_button.cget("state")), "disabled")
        self.trainee.input_var.set("KM")
        self.pump()
        self.trainer.deadline = time.time()
        self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
        self.trainer.deadline = time.time()
        self.assertTrue(wait_for(lambda: not self.trainer.run_active, pump=self.pump))
        self.trainer.enter_paper()
        self.assertIsNotNone(self.trainer.paper_window)
        sheet = self.trainer.paper_sheet
        self.trainer.paper_name_var.set("DL4YM")  # hat am Rechner geantwortet
        self.trainer.apply_paper()
        self.assertIn("schon am Rechner", self.trainer.paper_note_var.get())
        self.trainer.paper_name_var.set("DK1AB")
        sheet.entries[1].insert(0, "KM")
        sheet.entries[2].insert(0, "UK")
        self.trainer.apply_paper()
        self.assertIn("1 von 2", self.trainer.paper_note_var.get())
        self.assertEqual(sheet.values(), {1: "", 2: ""})
        self.assertEqual(self.trainer.board.names, ["DL4YM", "DK1AB"])
        values = self.trainer.tree.item(self.trainer.tree.get_children()[1])["values"]
        self.assertEqual([str(v) for v in values[3:]], ["75% (1/2)", "Papier", ""])
        self.trainer.close_paper()
        self.assertIsNone(self.trainer.paper_window)

    def test_answer_sheet_opens_in_the_browser(self):
        from morsetrainer.modes import network_mode
        self.trainer.content_var.set("Gruppen")
        self.trainer.count_var.set(30)
        with mock.patch.object(network_mode, "open_in_editor") as opened:
            self.trainer.print_answer_sheet()
        path = Path(self.tmp.name) / "antwortbogen.html"
        opened.assert_called_once_with(path)
        page = path.read_text(encoding="utf-8")
        self.assertEqual(page.count('class="row"'), 30)
        self.assertEqual(page.count('class="box"'), 150)
        self.assertIn("Gruppen · 20 WPM", page)

    def test_speaker_mode_keeps_trainees_silent(self):
        from morsetrainer.core import audio
        self.connect()
        self.trainer.speaker_var.set(True)
        self.trainer._show_speaker_options()
        self.assertTrue(self.trainer.listen_var.get())
        self.assertEqual(str(self.trainer.listen_check.cget("state")), "disabled")
        self.trainer.auto_var.set(False)
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", "KM\nUR\n")
        with mock.patch.object(audio, "play") as play:
            self.trainer.start_run()
            self.assertEqual(play.call_count, 1)  # nur der Lautsprecher des Trainers
            self.assertTrue(wait_for(lambda: self.trainee.current is not None, pump=self.pump))
            self.assertEqual(play.call_count, 1)
        current = self.trainee.current
        self.assertTrue(current["silent"])
        self.assertIn("Lautsprecher", self.trainee.trainee_status_var.get())
        # Zeitbasis ist der Eingang der Nachricht, nicht das Abholen.
        self.assertAlmostEqual(self.trainee.play_start, current["received"] + audio_latency(), places=3)
        self.assertLess(current["received"], time.time())
        self.trainee.playing = False
        # Falsch: Die Lösung kommt einmal für alle über den Lautsprecher.
        with mock.patch.object(audio, "play") as play:
            self.trainee.input_var.set("KS")
            self.trainee.on_submit()
            self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
            self.assertTrue(wait_for(lambda: "Lösung" in self.trainee.trainee_status_var.get(), pump=self.pump))
            self.assertEqual(play.call_count, 1)
        # Richtig und flüssig: keine Lösung, auch nicht am Lautsprecher.
        with mock.patch.object(audio, "play") as play:
            self.trainer.advance()
            self.assertTrue(wait_for(lambda: self.trainee.current["n"] == 2, pump=self.pump))
            self.trainee.playing = False
            self.trainee.tone_end = time.time()
            self.trainee.input_var.set("UR")
            self.trainee.on_submit()
            self.assertTrue(wait_for(lambda: not self.trainer.item_open, pump=self.pump))
            self.pump()
            self.assertEqual(play.call_count, 1)  # nur die Sequenz selbst
        data = self.trainer.settings()
        self.assertTrue(data["speaker"])
        self.trainee.restore_settings(data)
        self.assertEqual(str(self.trainee.listen_check.cget("state")), "disabled")

    def test_start_and_end_signs(self):
        from morsetrainer.core import audio
        from morsetrainer.core.morse import END_TEXT, START_TEXT
        from morsetrainer.modes import network_mode
        from morsetrainer.modes.sequence_mode import BAND_LABELS
        self.connect()
        self.wpm.set(40)
        self.trainer.signs_var.set(True)
        self.trainer.listen_var.set(True)
        self.trainer.band_var.set(next(label for label, preset in BAND_LABELS.items() if preset))
        self.trainer.content_var.set("Eigener Text")
        self.trainer.custom_text.insert("1.0", "KM\n")
        with mock.patch.object(audio, "play_quietly") as quietly, mock.patch.object(audio, "play"), \
                mock.patch.object(network_mode, "build_text", wraps=network_mode.build_text) as built:
            self.trainer.start_run()
            self.assertIsNone(self.trainer.item)  # erst VVV =, dann die erste Sequenz
            self.assertIn(START_TEXT, self.trainer.trainer_status_var.get())
            self.assertTrue(wait_for(lambda: quietly.call_count == 2, pump=self.pump))  # Trainer und Teilnehmer
            self.assertIn(START_TEXT, self.trainee.trainee_status_var.get())
            self.assertTrue(all(call.args[0] == START_TEXT + " " for call in built.call_args_list))
            self.assertIsNone(self.trainee.current)
            self.assertTrue(wait_for(lambda: self.trainee.current is not None, pump=self.pump))
            built.reset_mock()
            self.trainer.stop_run()
            self.assertTrue(wait_for(lambda: quietly.call_count == 4, pump=self.pump))
            self.assertEqual([call.args[0] for call in built.call_args_list if call.args[0] == END_TEXT],
                             [END_TEXT, END_TEXT])
        # Ton nur über den Lautsprecher: Die Teilnehmer bleiben auch bei VVV = still.
        self.trainer.speaker_var.set(True)
        with mock.patch.object(audio, "play_quietly") as quietly, mock.patch.object(audio, "play"):
            self.trainer.start_run()
            self.assertTrue(wait_for(lambda: "Achtung" in self.trainee.trainee_status_var.get(), pump=self.pump))
            self.assertTrue(wait_for(lambda: "Lautsprecher" in self.trainee.trainee_status_var.get(),
                                     pump=self.pump))
            self.assertEqual(quietly.call_count, 1)
        # F7 während VVV =: die erste Sequenz kommt sofort, nicht doppelt.
        self.trainer.stop_run()
        self.trainer.speaker_var.set(False)
        self.trainer.band_var.set("aus")
        with mock.patch.object(audio, "play_quietly"), mock.patch.object(audio, "play"):
            self.trainer.custom_text.insert("1.0", "UR\n")
            self.trainer.start_run()
            self.trainer.advance()
            self.assertEqual(self.trainer.item_n, 1)
            intro_over = time.time() + audio_latency() + network_mode.sequence_seconds(START_TEXT + " ", 40, None, None)
            wait_for(lambda: time.time() > intro_over + 0.3, pump=self.pump)
            self.assertEqual(self.trainer.item_n, 1)
        self.assertTrue(self.trainer.settings()["signs"])

    def test_paced_options(self):
        from morsetrainer.modes.network_mode import PACED, WAIT
        self.assertEqual(str(self.trainer.answer_spin.cget("state")), "normal")
        self.assertFalse(self.trainer.listen_var.get())
        self.trainer.flow_var.set(PACED)
        self.trainer._on_flow_change()
        # Papier-Teilnehmer hören über den Lautsprecher des Trainers.
        self.assertTrue(self.trainer.listen_var.get())
        self.assertEqual(str(self.trainer.answer_spin.cget("state")), "disabled")
        self.assertEqual(str(self.trainer.solution_check.cget("state")), "disabled")
        # Die Schreibpause folgt dem Inhalt: Einzelzeichen sind schnell notiert.
        self.trainer.content_var.set("Einzelzeichen")
        self.assertEqual(self.trainer.pause_var.get(), 2)
        self.trainer.content_var.set("QSO-Klartext")
        self.assertEqual(self.trainer.pause_var.get(), 5)
        self.trainer.pause_var.set(7)
        data = self.trainer.settings()
        self.assertEqual((data["flow"], data["pause_s"]), (PACED, 7))
        self.trainee.restore_settings(data)
        self.assertEqual(self.trainee.pause_var.get(), 7)
        self.assertEqual(str(self.trainee.auto_check.cget("state")), "disabled")
        self.trainee.listen_var.set(False)
        self.trainee.restore_settings({"flow": PACED})  # Wiederherstellen ändert nichts daran
        self.assertFalse(self.trainee.listen_var.get())
        self.trainee.restore_settings({"flow": WAIT, "pause_s": 99})
        self.assertEqual(str(self.trainee.auto_check.cget("state")), "normal")
        self.assertEqual(self.trainee.pause_var.get(), 7)

    def test_solution_window(self):
        from morsetrainer.core import audio
        self.connect()
        self.trainer.pause_var.set(1)
        self.start_paced("KM\nUR\nS\n")
        self.trainer.show_solution()
        window = self.trainer.solution_window
        self.pump()
        self.assertEqual(self.trainer.solution_number_var.get(), "Nr. 1 von 3")
        self.assertFalse(self.trainer.solution_list.winfo_ismapped())
        self.trainer.advance()
        self.assertEqual(self.trainer.solution_number_var.get(), "Nr. 2 von 3")
        self.trainer.stop_run()
        self.pump()
        self.assertTrue(self.trainer.solution_list.winfo_ismapped())
        self.assertEqual(self.trainer.solution_text_widget.get("1.0", "end").splitlines()[:2], ["1. KM", "2. UR"])
        self.trainer.copy_solution()
        self.assertEqual(self.root.clipboard_get(), "1. KM\n2. UR")
        with mock.patch.object(audio, "play") as play:
            for key in ("Down", "Down", "space"):  # der erste Pfeil markiert Nr. 1
                window.event_generate("<Key>", keysym=key, when="now")
            self.assertEqual(self.trainer.solution_selected, 2)
            self.assertEqual(play.call_count, 1)
        size = self.trainer.solution_font.cget("size")
        self.trainer.zoom_solution(1)
        self.assertGreater(self.trainer.solution_font.cget("size"), size)
        self.trainer.close_solution()
        self.assertIsNone(self.trainer.solution_window)
        self.assertFalse(window.winfo_exists())

    def test_wrong_pin_is_shown(self):
        self.trainer.port_var.set(free_port())
        self.trainer.open_session()
        self.trainee.name_var.set("DL4YM")
        self.trainee.pin_var.set("x")
        self.trainee.address_var.set(f"127.0.0.1:{self.trainer.port_var.get()}")
        self.trainee.connect()
        self.assertTrue(wait_for(lambda: self.trainee.client is None, pump=self.pump))
        self.assertEqual(self.trainee.trainee_status_var.get(), "Abgelehnt: PIN falsch.")
        self.assertEqual(self.stops, [])

    def test_newer_trainer_offers_an_update(self):
        self.trainer.version, self.trainee.version = "2.16", "2.15"
        self.trainee.updater = mock.Mock()
        self.connect()
        offer = self.trainee.updater.offer
        self.assertTrue(wait_for(lambda: offer.called, pump=self.pump))
        version, intro, show, prepare, failed = offer.call_args[0]
        self.assertEqual(version, "2.16")
        self.assertIn("Der Trainer nutzt Version 2.16, du hast 2.15.", intro)
        # Ja: erst trennen, nach dem Neustart mit derselben PIN wieder verbinden.
        pin = self.trainee.pin_var.get()
        self.assertEqual(prepare(), ["--join", pin])
        self.assertIsNone(self.trainee.client)
        self.assertEqual(str(self.trainee.connect_button.cget("state")), "disabled")
        failed()
        self.assertEqual(str(self.trainee.connect_button.cget("state")), "normal")
        # Auch wer abgelehnt wird, erfährt die Version des Trainers.
        offer.reset_mock()
        self.trainee.pin_var.set("nope")
        self.trainee.connect()
        self.assertTrue(wait_for(lambda: offer.called, pump=self.pump))
        self.assertIn("PIN", self.trainee.trainee_status_var.get())
        # Nach dem Neustart: Reiter als Teilnehmer, gespeicherter Name und Adresse.
        self.trainee.role_var.set("trainer")
        self.trainee._show_role()
        self.trainee.rejoin(pin)
        self.assertTrue(wait_for(lambda: self.trainee.connected, pump=self.pump))
        self.assertEqual(self.trainee.role_var.get(), "trainee")

    def test_settings_round_trip(self):
        self.trainer.content_var.set("Rufzeichen")
        self.trainer.count_var.set(30)
        self.trainer.custom_text.insert("1.0", "CQ\nTEST")
        data = self.trainer.settings()
        self.trainee.restore_settings(data)
        self.assertEqual(self.trainee.settings(), data)
        self.trainee.restore_settings({"port": 80, "count": "x", "role": "boss"})
        self.assertEqual(self.trainee.port_var.get(), data["port"])


def audio_latency():
    from morsetrainer.core.morse import AUDIO_LATENCY
    return AUDIO_LATENCY


def ttk_frame(root):
    from tkinter import ttk
    frame = ttk.Frame(root)
    frame.pack()
    return frame


if __name__ == "__main__":
    unittest.main()
