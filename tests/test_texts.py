"""Morse-Tabelle, QSO-/Contest-Texte und der Antwortvergleich der Abfrage."""
import random
import unittest

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)
import morse
import qso_text
from qso_quiz import is_correct, normalize
from run_mode import call_matches


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
        for length, count in enumerate(qso_text.CONTEST_QSO_COUNTS):
            qso = qso_text.generate_qso("cqww", length)
            self.assertEqual(len(qso.quiz_rows), count + 1)  # + Run-Station

    def test_pileup_callers_are_extra_stations(self):
        seen = False
        for _ in range(100):
            qso = qso_text.generate_qso("wpx", qso_text.LENGTH_LONG)
            worked = len(qso.quiz_rows)  # Run-Station + gearbeitete Anrufer
            for tx_index, others in qso.pileups:
                seen = True
                self.assertNotEqual(qso.transmissions[tx_index][0], 0, "Pile-up gehört zu einem Anruf")
                for station, _, delay in others:
                    self.assertGreaterEqual(station, worked)
                    self.assertGreaterEqual(delay, 0)
        self.assertTrue(seen, "in 100 Runs kein einziger Pile-up")

    def test_zones(self):
        dl = qso_text._country_of("DL4YM")
        w6 = qso_text._country_of("W6ABC")
        ua9 = qso_text._country_of("UA9XX")
        self.assertEqual(qso_text.cq_zone("DL4YM", dl), 14)
        self.assertEqual(qso_text.itu_zone("DL4YM", dl), 28)
        self.assertEqual(qso_text.cq_zone("W6ABC", w6), 3)
        self.assertEqual(qso_text.itu_zone("W6ABC", w6), 6)
        self.assertEqual(qso_text.cq_zone("UA9XX", ua9), 17)

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
            self.assertEqual(qso_text._country_of(call).key, "W")
            call, _, _ = qso_text.contest_caller("arrldx", "W1AW", set())
            self.assertNotEqual(qso_text._country_of(call).key, "W")


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