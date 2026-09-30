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
from morsetrainer.net import protocol
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
                                     set_koch_tempo=lambda: self.wpm.set(20),
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
        self.trainee.playing = False
        self.trainee.input_var.set("KMS")
        self.trainee.on_submit()
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

    def test_slow_character_speed_hint(self):
        self.wpm.set(12)
        self.assertIn("12 WPM", self.trainer.tempo_hint_var.get())
        self.wpm.set(20)
        self.assertEqual(self.trainer.tempo_hint.winfo_manager(), "")

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
