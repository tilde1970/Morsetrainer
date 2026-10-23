"""Morse-Tabelle, QSO-/Contest-Texte und der Antwortvergleich der Abfrage."""
import random
import unittest

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
from morsetrainer.core import morse
from morsetrainer.core import qso_text
from morsetrainer.modes.qso_quiz import is_correct, normalize
from morsetrainer.modes.run_mode import call_matches


class MorseTest(unittest.TestCase):
    def test_prosigns_have_codes_and_display_names(self):
        for placeholder, name in morse.PROSIGNS.items():
            self.assertIn(placeholder, morse.MORSE_CODE)
        self.assertEqual(morse.MORSE_CODE[morse.SK], "...-.-")
        self.assertEqual(morse.MORSE_CODE[morse.KN], "-.--.")
        self.assertEqual(morse.display_text("73 * E E"), "73 <SK> E E")

    def test_chirp_keeps_length(self):
        plain = morse.build_samples("K", 20, 600)
        chirpy = morse.build_samples("K", 20, 600, chirp=(50, 0.02))
        self.assertEqual(len(plain), len(chirpy))
        self.assertFalse((plain == chirpy).all())

    def test_build_text_is_float32_and_in_range(self):
        samples = morse.build_text("CQ DE DL4YM", 25, 700)
        self.assertEqual(samples.dtype.name, "float32")
        self.assertLessEqual(abs(samples).max(), 1.0)


class QsoTextTest(unittest.TestCase):
    def setUp(self):
        random.seed(1234)

    def test_all_kinds_and_lengths_generate_valid_qsos(self):
        for kind in qso_text.QSO_TYPES:
            for length in (qso_text.LENGTH_SHORT, qso_text.LENGTH_NORMAL, qso_text.LENGTH_LONG):
                for _ in range(15):
                    qso = qso_text.generate_qso(kind, length)
                    with self.subTest(kind=kind, length=length):
                        self.assertEqual(len(set(qso.calls)), len(qso.calls), "Rufzeichen doppelt")
                        for station, text in qso.transmissions:
                            self.assertLess(station, len(qso.calls))
                            self.assertTrue(all(ch == " " or ch in morse.MORSE_CODE for ch in text), text)
                        full_text = qso.text()
                        for label, cells in qso.quiz_rows:
                            for cell in cells:
                                if cell is not None:
                                    self.assertIn(cell[0], full_text, f"{label}: {cell[0]} nie gesendet")

    def test_contest_qso_count_follows_length(self):
        for length, (low, high) in enumerate(qso_text.CONTEST_QSO_RANGES):
            for _ in range(10):
                qso = qso_text.generate_qso("cqww", length)
                self.assertTrue(low + 1 <= len(qso.quiz_rows) <= high + 1)  # + Run-Station

    def test_pileup_callers_are_extra_stations(self):
        seen = False
        for _ in range(100):
            qso = qso_text.generate_qso("wpx", qso_text.LENGTH_LONG, qso_text.PILEUP_PROBABILITY)
            worked = len(qso.quiz_rows)  # Run-Station + gearbeitete Anrufer
            for tx_index, others in qso.pileups:
                seen = True
                self.assertNotEqual(qso.transmissions[tx_index][0], 0, "Pile-up gehört zu einem Anruf")
                for station, _, delay in others:
                    self.assertGreaterEqual(station, worked)
                    self.assertGreaterEqual(delay, 0)
        self.assertTrue(seen, "in 100 Runs kein einziger Pile-up")

    def test_wag_non_dl_only_gets_dl_callers(self):
        for _ in range(30):
            call, _, _ = qso_text.contest_caller("wag", "G3XYZ", set())
            self.assertEqual(qso_text._country_of(call).key, "DL")

    def test_no_pileups_by_default(self):
        for _ in range(30):
            self.assertEqual(qso_text.generate_qso("wpx", qso_text.LENGTH_LONG).pileups, ())

    def test_facts_are_actually_sent(self):
        for kind in ("ragchew", "cqww", "wag"):
            for length in range(len(qso_text.CONTEST_QSO_RANGES)):
                qso = qso_text.generate_qso(kind, length)
                self.assertGreaterEqual(len(qso.facts), 3)
                text = qso.text()
                for question, (expected, fact_kind) in qso.facts:
                    if "Wie viele" in question:
                        continue
                    self.assertIn(expected.rstrip("W"), text, question)
                    # Keine Frage nennt ein Rufzeichen, nach dem eine andere fragt.
                    if kind == "ragchew":
                        self.assertFalse(any(call in question for call in qso.calls), question)

    def test_zones(self):
        dl = qso_text._country_of("DL4YM")
        w6 = qso_text._country_of("W6ABC")
        ua9 = qso_text._country_of("UA9XX")
        self.assertEqual(qso_text.cq_zone("DL4YM", dl), 14)
        self.assertEqual(qso_text.itu_zone("DL4YM", dl), 28)
        self.assertEqual(qso_text.cq_zone("W6ABC", w6), 3)
        self.assertEqual(qso_text.itu_zone("W6ABC", w6), 6)
        self.assertEqual(qso_text.cq_zone("UA9XX", ua9), 17)
        w8 = qso_text._country_of("W8ABC")
        self.assertEqual(qso_text.cq_zone("W8ABC", w8), 4)  # OH, MI
        self.assertEqual(qso_text.itu_zone("W9ABC", qso_text._country_of("W9ABC")), 8)  # IL, IN, WI

    def test_wag_non_members_send_nm(self):
        from unittest import mock
        dl = qso_text._country_of("DL4YM")
        with mock.patch.object(qso_text.random, "random", lambda: 0.0):
            self.assertEqual(qso_text._Exchange("wag", "DL4YM", dl, 1).fixed[0], "NM")
        from morsetrainer.modes.qso_quiz import normalize
        self.assertEqual(normalize("nm", qso_text.DOK), normalize("NM", qso_text.DOK))

    def test_cut_number(self):
        self.assertEqual(qso_text.cut_number(7), "TT7")
        self.assertEqual(qso_text.cut_number(42), "T42")
        self.assertEqual(qso_text.cut_number(123), "123")

    def test_my_exchange_defaults(self):
        self.assertEqual(qso_text.default_my_exchange("cqww", "DL4YM"), "14")
        self.assertEqual(qso_text.default_my_exchange("iaru", "DL4YM"), "28")
        self.assertEqual(qso_text.default_my_exchange("iaru", "DA0HQ"), "DARC")
        self.assertEqual(qso_text.default_my_exchange("wag", "DL4YM"), "")  # DOK muss man selbst eintragen
        self.assertTrue(qso_text.uses_serial("wpx", "DL4YM"))
        self.assertTrue(qso_text.uses_serial("wag", "F5ABC"))
        self.assertFalse(qso_text.uses_serial("wag", "DL4YM"))

    def test_arrldx_callers_are_on_the_other_side(self):
        for _ in range(30):
            call, _, _ = qso_text.contest_caller("arrldx", "DL4YM", set())
            self.assertFalse(qso_text._arrl_dx(call, qso_text._country_of(call)), call)
            call, _, _ = qso_text.contest_caller("arrldx", "W1AW", set())
            self.assertTrue(qso_text._arrl_dx(call, qso_text._country_of(call)), call)


class SlashAndCqVariantsTest(unittest.TestCase):
    """Rufzeichen mit /P und /M kommen nur, wenn das „/“ gelernt ist; die CQ-Rufe
    sind abwechslungsreicher."""

    def setUp(self):
        random.seed(99)

    def _calls(self, slash, kinds=None, n=60):
        calls = []
        for kind in kinds or qso_text.QSO_TYPES:
            for _ in range(n):
                calls += qso_text.generate_qso(kind, qso_text.LENGTH_NORMAL, 0.5, slash=slash).calls
        return calls

    def test_knows_slash_follows_the_learned_characters(self):
        self.assertFalse(qso_text.knows_slash("KMURESNAPTLWI.JZ=FOY,VG5"))
        self.assertTrue(qso_text.knows_slash("KMURESNAPTLWI.JZ=FOY,VG5/"))

    def test_no_slash_calls_without_the_slash_learned(self):
        self.assertFalse([c for c in self._calls(False) if "/" in c])

    def test_slash_calls_when_learned_are_portable_or_mobile_only(self):
        suffixed = [c for c in self._calls(True) if "/" in c]
        self.assertTrue(suffixed)
        self.assertEqual({c.split("/")[1] for c in suffixed} - {"P", "M"}, set())
        for call in suffixed:
            self.assertIsNotNone(qso_text._country_of(call), call)

    def test_slash_calls_keep_the_exchange_and_zones_of_their_country(self):
        for call, kind, expected in (("W1AW/P", "arrldx", "TEXT"), ("DL1ABC/P", "cqww", "NUMBER")):
            exchange = qso_text._Exchange(kind, call, qso_text._country_of(call), 1)
            self.assertEqual(exchange.fixed[1], getattr(qso_text, expected))
        self.assertEqual(qso_text.cq_zone("DL1ABC/M", qso_text._country_of("DL1ABC")), 14)

    def test_contest_caller_can_carry_a_suffix(self):
        callers = [qso_text.contest_caller("cqww", "DL4YM", set(), slash=True)[0] for _ in range(300)]
        self.assertTrue([c for c in callers if "/" in c])
        callers = [qso_text.contest_caller("cqww", "DL4YM", set())[0] for _ in range(300)]
        self.assertFalse([c for c in callers if "/" in c])

    def test_contest_cq_calls_vary_and_cq_dx_only_where_it_is_used(self):
        seen = {}
        for kind in qso_text.QSO_TYPES:
            if kind == qso_text.RAGCHEW:
                continue
            texts = set()
            for _ in range(60):
                qso = qso_text.generate_qso(kind, qso_text.LENGTH_LONG)
                texts |= {text for station, text in qso.transmissions if station == 0 and "CQ" in text.split()[:2]}
            seen[kind] = texts
            self.assertGreaterEqual(len({" ".join(w for w in t.split() if len(w) < 6 and w != "DE") for t in texts}), 2)
        for kind in ("cqww", "wpx"):
            self.assertTrue(any(t.startswith("CQ DX ") for t in seen[kind]), kind)
        for kind in ("wag", "arrldx", "iaru"):
            self.assertFalse(any("CQ DX" in t for t in seen[kind]), kind)

    def test_ragchew_cq_sometimes_asks_for_dx(self):
        firsts = [qso_text.generate_qso(qso_text.RAGCHEW, qso_text.LENGTH_SHORT).transmissions[0][1]
                  for _ in range(200)]
        self.assertTrue(any(" DX DE " in f for f in firsts))
        self.assertTrue(any(" DX DE " not in f for f in firsts))
        self.assertTrue(all(f.startswith("CQ CQ") and " DE " in f and f.endswith(" K") for f in firsts))


class ZoneTest(unittest.TestCase):
    @staticmethod
    def zones(call, key):
        country = next(c for c in qso_text.COUNTRIES if c.key == key)
        return qso_text.cq_zone(call, country), qso_text.itu_zone(call, country)

    def test_islands_have_their_own_zones(self):
        # Nach cty.dat (country-files.com)
        self.assertEqual(self.zones("EA8ABC", "EA"), (33, 36))  # Kanaren
        self.assertEqual(self.zones("EA9XY", "EA"), (33, 37))  # Ceuta, Melilla
        self.assertEqual(self.zones("CT3AB", "CT"), (33, 36))  # Madeira
        self.assertEqual(self.zones("CU2AA", "CT"), (14, 36))  # Azoren
        self.assertEqual(self.zones("IG9A", "I"), (33, 37))  # Italien in Afrika
        self.assertEqual(self.zones("EA4X", "EA"), (14, 37))  # Festland unverändert

    def test_asiatic_russia_and_labrador(self):
        self.assertEqual(self.zones("RA8A", "UA"), (17, 30))
        self.assertEqual(self.zones("RA3A", "UA"), (16, 29))
        self.assertEqual(self.zones("VO2AB", "VE")[0], 2)
        self.assertEqual(self.zones("VO1AB", "VE")[0], 5)

    def test_iaru_headquarters_use_current_callsign(self):
        self.assertIn("9A0HQ", qso_text.IARU_HQ_STATIONS)
        self.assertNotIn("9A1HQ", qso_text.IARU_HQ_STATIONS)
        # Nicht unter den HQ-Stationen 2025: Tschechien und Litauen
        self.assertNotIn("OL9HQ", qso_text.IARU_HQ_STATIONS)
        self.assertNotIn("LY0HQ", qso_text.IARU_HQ_STATIONS)

    def test_every_headquarters_call_belongs_to_a_known_country(self):
        for call in qso_text.IARU_HQ_STATIONS:
            self.assertIsNotNone(qso_text._country_of(call), call)

    def test_ragchew_has_no_ar_before_the_final_call(self):
        random.seed(5)
        for _ in range(30):
            text = qso_text.generate_qso(qso_text.RAGCHEW, qso_text.LENGTH_LONG)
            for _, sent in text.transmissions:
                self.assertNotIn(" + ", f" {sent} ")


class FrequencyRangeTest(unittest.TestCase):
    def test_frequencies_lie_in_the_cw_segments(self):
        # IARU Region 1, Stand Juni 2016: Telegrafieteile
        from morsetrainer.modes import content
        cw = ((3500, 3580), (7000, 7040), (10100, 10130), (14000, 14070), (18068, 18095),
              (21000, 21070), (24890, 24915), (28000, 28070))
        for low, high in content.BAND_RANGES_KHZ:
            self.assertTrue(any(a <= low and high <= b for a, b in cw), (low, high))

    def test_no_unofficial_suffix(self):
        from morsetrainer.modes import callsign_mode
        self.assertNotIn("/QRP", callsign_mode.SUFFIXES)


class DupTest(unittest.TestCase):
    """Im Contest ruft ab und zu eine schon geloggte Station noch einmal und
    bekommt „DUP“; das ist kein neues QSO."""

    def setUp(self):
        random.seed(7)

    def _runs(self, dup, n=150, kinds=("cqww", "wpx", "wag", "arrldx", "iaru")):
        return [qso_text.generate_qso(kind, qso_text.LENGTH_LONG, 0.3, dup=dup) for kind in kinds for _ in range(n)]

    def test_knows_dup_needs_d_u_and_p(self):
        self.assertFalse(qso_text.knows_dup("KMURESNAPTLWI.JZ=FOY,VG5/Q92H38B?47C1"))
        self.assertTrue(qso_text.knows_dup("KMURESNAPTLWI.JZ=FOY,VG5/Q92H38B?47C1D"))
        self.assertTrue(qso_text.knows_dup("dup"))

    def test_no_dup_unless_learned(self):
        for qso in self._runs(False):
            self.assertFalse(any("DUP" in text for _, text in qso.transmissions))
            self.assertNotIn("DUP", " ".join(q for q, _ in qso.facts))

    def test_dup_is_a_second_call_of_a_logged_station_and_no_new_row(self):
        seen = 0
        for qso in self._runs(True):
            dups = [i for i, (_, text) in enumerate(qso.transmissions) if text.endswith(" DUP")]
            if not dups:
                continue
            seen += 1
            self.assertEqual(len(dups), 1, "höchstens einmal je Run")
            i = dups[0]
            call = qso.transmissions[i][1].split()[0]
            caller, calling = qso.transmissions[i - 1]
            self.assertEqual(qso.calls[caller], call)
            self.assertEqual(calling.split()[0], call)
            logged = [cells[0][0] for _, cells in qso.quiz_rows[1:]]
            self.assertEqual(len(logged), len(set(logged)), "der Dupe ist keine zweite Zeile")
            self.assertIn(call, logged)
            self.assertGreaterEqual(logged.index(call) + 1, 1)
            self.assertGreaterEqual(len(logged), qso_text.DUP_AFTER_QSOS)
            # Die Station antwortet kurz, dann ruft die Run-Station wieder CQ.
            self.assertEqual(qso.transmissions[i + 1][0], caller)
            if i + 2 < len(qso.transmissions):
                station, cq = qso.transmissions[i + 2]
                self.assertEqual(station, 0)
                self.assertIn(qso.calls[0], cq)
                self.assertTrue("TEST" in cq or "WAG" in cq, cq)
            self.assertIn(call, [answer for question, (answer, _) in qso.facts if "DUP" in question])
        self.assertGreater(seen, 100)

    def test_ragchew_never_has_dup(self):
        for _ in range(100):
            qso = qso_text.generate_qso(qso_text.RAGCHEW, qso_text.LENGTH_LONG, dup=True)
            self.assertFalse(any("DUP" in text for _, text in qso.transmissions))


class QuizCompareTest(unittest.TestCase):
    def test_text_ignores_case_spaces_and_umlauts(self):
        self.assertTrue(is_correct("Münster", "MUENSTER", qso_text.TEXT))
        self.assertTrue(is_correct(" dl4 ym ", "DL4YM", qso_text.TEXT))
        self.assertFalse(is_correct("DL4YN", "DL4YM", qso_text.TEXT))

    def test_rst_and_numbers_accept_cut_numbers(self):
        self.assertTrue(is_correct("5nn", "599", qso_text.RST))
        self.assertTrue(is_correct("7", "TT7", qso_text.NUMBER))
        self.assertTrue(is_correct("5NN 14", "14", qso_text.NUMBER))
        self.assertTrue(is_correct("599 014", "14", qso_text.NUMBER))
        self.assertTrue(is_correct("1000", "KW", qso_text.NUMBER))
        self.assertTrue(is_correct("100", "1TT", qso_text.NUMBER))
        self.assertFalse(is_correct("15", "14", qso_text.NUMBER))

    def test_text_is_not_treated_as_number(self):
        # DOK „N53“ darf nicht zu „953“ werden.
        self.assertEqual(normalize("n53", qso_text.TEXT), "N53")


class CallMatchTest(unittest.TestCase):
    def test_exact_similar_and_query(self):
        self.assertEqual(call_matches("DL4YM", "DL4YM"), "exact")
        self.assertEqual(call_matches("DL4YN", "DL4YM"), "similar")
        self.assertEqual(call_matches("DL4?", "DL4YM"), "similar")
        self.assertEqual(call_matches("?4Y", "DL4YM"), "similar")
        self.assertEqual(call_matches("F5ABC", "DL4YM"), "")
        self.assertEqual(call_matches("D?", "DL4YM"), "")  # zu wenig, um jemanden zu meinen


if __name__ == "__main__":
    unittest.main()