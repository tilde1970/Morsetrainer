import re
import unittest

from morsetrainer.core import qso_text as q


class CountryTableTest(unittest.TestCase):
    def test_keys_unique(self):
        keys = [c.key for c in q.COUNTRIES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_sample_prefixes_map_back_to_own_country(self):
        for country in q.COUNTRIES:
            for prefix in country.sample_prefixes:
                call = prefix + ("1" if prefix[-1].isalpha() else "") + "ABC"
                self.assertIs(q._country_of(call), country, call)

    def test_every_country_has_itu_zone_and_data(self):
        for country in q.COUNTRIES:
            self.assertIn(country.key, q.ITU_ZONES)
            self.assertTrue(country.names and country.qths)
            self.assertTrue(all(n == n.upper() for n in country.names), country.key)

    def test_known_calls(self):
        for call, key in (("YO3ABC", "YO"), ("YT1AB", "YU"), ("HB3YZZ", "HB"), ("HB9AA", "HB"),
                          ("LZ1AB", "LZ"), ("GW4ABC", "GW"), ("PZ5X", None), ("4O3A", None), ("TM1A", "F"), ("LW2A", "LU"), ("GS4A", "GM"), ("GI4A", "GI"), ("VT2A", "VU"), ("ZK1A", "ZL"), ("CT1ABC", "CT"), ("CF3ABC", "VE"), ("HK1A", "HK"), ("JY4A", None),
                          ("VE3XYZ", "VE"), ("VY1AA", "VE"), ("XE1A", "XE"), ("BY1RX", "BY"),
                          ("BV2A", "BV"), ("BD7A", "BY"), ("VU2A", "VU"), ("4X6TU", "4X"), ("EW1A", "EW"),
                          ("UN7A", "UN"), ("TF3A", "TF"), ("Z32A", "Z3"), ("CO8A", "CO"),
                          ("HI3A", "HI"), ("6Y5A", "6Y"), ("TI2A", "TI"), ("5N1A", "5N"), ("9G5A", "9G"), ("6W1A", "6W"), ("TJ1A", "TJ"),
                          ("TU5A", "TU"), ("OA4A", "OA"), ("YV5A", "YV"), ("9M2A", "9M"), ("S21A", "S2"),
                          ("5Y4A", "5Z"), ("S31A", "S2"), ("E73A", "E7")):
            country = q._country_of(call)
            self.assertEqual(country.key if country else None, key, call)

    def test_austrian_qth_follows_call_digit(self):
        oe = q._country_of("OE3ABC")
        for digit, cities in oe.qths_by_district.items():
            for _ in range(20):
                self.assertIn(q._qth_for(f"OE{digit}ABC", oe), cities)
        self.assertIn(q._qth_for("OE0ABC", oe), oe.qths)

    def test_canada_province_and_zones(self):
        ve = q._country_of("VE3ABC")
        self.assertEqual(q._province("VE3ABC"), ("ON",))
        self.assertEqual(q._province("VO1AA"), ("NL",))
        self.assertEqual(q._province("VY2AA"), ("PE",))
        self.assertEqual((q.cq_zone("VE7AA", ve), q.cq_zone("VE3AA", ve), q.cq_zone("VY1AA", ve)), (3, 4, 1))
        for digit in "0123456789":
            self.assertIsInstance(q.itu_zone(f"VE{digit}AA", ve), int)

    def test_arrldx_north_america_exchange(self):
        for call, kind in (("VE6AA", q.TEXT), ("W1AA", q.TEXT), ("DL1AA", q.NUMBER)):
            exchange = q._Exchange("arrldx", call, q._country_of(call), 1)
            self.assertEqual(exchange.fixed[1], kind, call)
        self.assertEqual(q._Exchange("arrldx", "VE6AA", q._country_of("VE6AA"), 1).fixed[0], "AB")

    def test_prefix_patterns_do_not_overlap(self):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        patterns = [re.compile(c.pattern) for c in q.COUNTRIES]
        for a in alphabet:
            for b in alphabet:
                for digit in "05":
                    call = f"{a}{b}{digit}AB"
                    hits = [c.key for c, rx in zip(q.COUNTRIES, patterns) if rx.match(call)]
                    self.assertLessEqual(len(hits), 1, (call, hits))

    def test_arrl_dx_side_of_us_and_canadian_territories(self):
        for call, dx in (("W1AW", False), ("K6AA", False), ("KH6AA", True), ("AL7AA", True),
                         ("KP4AA", True), ("KG4AA", True), ("NH2A", True), ("VE3AA", False),
                         ("CY9AA", True), ("CY0AA", True), ("DL1AA", True)):
            self.assertEqual(q._arrl_dx(call, q._country_of(call)), dx, call)
        self.assertEqual(q._Exchange("arrldx", "KP4AA", q._country_of("KP4AA"), 1).fixed[1], q.NUMBER)

    def test_territory_zones(self):
        w = q._country_of("W1AA")
        for call, cq, itu in (("KH6AA", 31, 61), ("KH2AA", 27, 64), ("KH8AA", 32, 62), ("KP4AA", 8, 11),
                              ("AL7AA", 1, 1), ("KL2AA", 1, 1), ("W1AA", 5, 8)):
            self.assertEqual((q.cq_zone(call, w), q.itu_zone(call, w)), (cq, itu), call)

    def test_australia_russia_ontario_zones(self):
        vk, ua, ve = (q._country_of(c) for c in ("VK2AA", "UA3AA", "VE3AA"))
        self.assertEqual([(q.cq_zone(f"VK{d}AA", vk), q.itu_zone(f"VK{d}AA", vk)) for d in "2468"],
                         [(30, 59), (30, 55), (29, 58), (29, 55)])
        self.assertEqual((q.cq_zone("UA2AA", ua), q.cq_zone("UA3AA", ua)), (15, 16))
        self.assertEqual(q.cq_zone("VE3AA", ve), 4)

    def test_canadian_special_prefixes(self):
        ve = q._country_of("VE3AA")
        self.assertEqual((q._province("VO1AA"), q._province("VO2AA")), (("NL",), ("LB",)))
        self.assertIn(q._qth_for("VY1AA", ve), ("WHITEHORSE", "DAWSON"))
        self.assertIn(q._qth_for("VO2AA", ve), ("LABRADOR CITY", "GOOSE BAY"))

    def test_generated_digits_stay_in_valid_districts(self):
        for key, bad in (("VE", "0"), ("VK", "09"), ("OE", "0"), ("YV", "0"), ("9M", "0168")):
            country = next(c for c in q.COUNTRIES if c.key == key)
            for _ in range(200):
                self.assertNotIn(q._district(q._generated_call(country)), bad)

    def test_every_country_has_position_and_activity_sane(self):
        for country in q.COUNTRIES:
            lat, lon = q.POSITION[country.key]
            self.assertTrue(-90 <= lat <= 90 and -180 <= lon <= 180, country.key)
        self.assertFalse(set(q.ACTIVITY) - {c.key for c in q.COUNTRIES})
        for key in q.POSITION_BY_DISTRICT:
            self.assertIn(key[:-1], q.POSITION)

    def test_locator_position(self):
        lat, lon = q.locator_position("JO41")
        self.assertEqual((lat, lon), (51.5, 9.0))
        lat, lon = q.locator_position("jo41ab")
        self.assertAlmostEqual(lat, 51.0 + 1 / 24 + 1 / 48)
        self.assertAlmostEqual(lon, 8.0 + 1 / 24)
        self.assertEqual(q.locator_position("AA00"), (-89.5, -179.0))
        for bad in ("", "JO4", "JO41A", "SO41", "JO41ay", "1O41", "JO4x", "JO41ab1"):
            self.assertIsNone(q.locator_position(bad), bad)
        self.assertTrue(q.set_station_locator(""))
        self.assertFalse(q.set_station_locator("XX"))

    def test_distance(self):
        self.assertAlmostEqual(q._distance_km((51.0, 10.0), (51.0, 10.0)), 0, places=3)
        self.assertAlmostEqual(q._distance_km((0, 0), (0, 90)), 10007.5, delta=2)
        self.assertAlmostEqual(q._distance_km((51.0, 10.0), (35.7, 139.7)), 9000, delta=300)

    def _share(self, home, keys, n=3000):
        calls = [q._pick_call(home=home)[0] for _ in range(n)]
        return sum(q._country_of(c).key in keys for c in calls) / n

    @staticmethod
    def _weight_share(home, keys):
        """Anteil der Länder `keys` an den Gewichten (ohne Zufall)."""
        country, position = q._home_position(home)
        weights = q._country_weights(q.COUNTRIES, country, position)
        return sum(w for c, w in zip(q.COUNTRIES, weights) if c.key in keys) / sum(weights)

    EUROPE = {"DL", "F", "GM", "G", "GI", "GW", "I", "EA", "PA", "ON", "OE", "HB", "SP", "OK", "OZ", "SM", "LA",
              "OH", "UR", "UA", "HA", "OM", "YL", "LY", "ES", "EI", "CT", "9A", "S5", "YO", "YU", "LZ", "SV",
              "LX", "JW", "EW", "Z3", "TF", "E7"}
    ASIA = {"JA", "VU", "BY", "4X", "UN", "HL", "HS", "BV", "HZ", "XV", "TA"}
    OCEANIA = {"VK", "ZL", "YB", "DU"}
    AMERICA = {"W", "VE", "XE", "CO", "HI", "6Y", "TI"}
    SOUTH_AMERICA = {"PY", "CE", "LU", "HK"}

    def test_generated_calls_follow_home_location(self):
        saved = q._call_pool, dict(q._filtered_pools), q._station_position
        q._call_pool, q._filtered_pools, q._station_position = [], {}, None
        try:
            share = self._share
            # Aus Deutschland überwiegt Europa, aus Japan Asien, aus Australien Ozeanien.
            self.assertGreater(share("DL4YM", self.EUROPE), 0.6)
            self.assertGreater(share("JA1AA", self.ASIA), share("JA1AA", self.EUROPE))
            self.assertGreater(share("VK2AA", self.OCEANIA), share("DL4YM", self.OCEANIA) * 5)
            self.assertGreater(share("PY2AA", self.SOUTH_AMERICA), share("DL4YM", self.SOUTH_AMERICA) * 5)
            # Westküste der USA hört mehr Asien als die Ostküste, Mittelamerika mehr Südamerika.
            self.assertGreater(self._weight_share("W6AA", self.ASIA | self.OCEANIA),
                               self._weight_share("W1AW", self.ASIA | self.OCEANIA) * 1.15)
            self.assertGreater(share("XE1AA", self.SOUTH_AMERICA), share("DL4YM", self.SOUTH_AMERICA) * 1.5)
            # Israel, Türkei, Indien und Kasachstan hören mehr Asien als Deutschland.
            for home in ("4X6TU", "TA1AA", "VU2AA", "UN7AA"):
                self.assertGreater(self._weight_share(home, self.ASIA),
                                   self._weight_share("DL4YM", self.ASIA) * 1.25, home)
            # Island liegt zwischen Europa und Nordamerika.
            self.assertGreater(share("TF3AA", self.AMERICA), share("DL4YM", self.AMERICA) * 1.3)
            # Ohne erkanntes Rufzeichen zählt nur die Aktivität: W ist das häufigste Land.
            calls = [q._pick_call(home="")[0] for _ in range(3000)]
            top = max(set(q._country_of(c).key for c in calls),
                      key=lambda k: sum(q._country_of(c).key == k for c in calls))
            self.assertEqual(top, "W")
        finally:
            q._call_pool, q._filtered_pools, q._station_position = saved

    def test_locator_overrides_call_country(self):
        saved = q._call_pool, dict(q._filtered_pools), q._station_position, q._station_call
        q._call_pool, q._filtered_pools = [], {}
        try:
            # Rufzeichen ohne bekanntes Land (Emirate) und kein Locator: neutral.
            q.set_station_call("A61AA")
            q.set_station_locator("")
            neutral = self._share("", self.ASIA, 4000)
            # Mit Locator in Japan (PM95) überwiegt Asien.
            q.set_station_locator("PM95")
            with_locator = self._share("", self.ASIA, 4000)
            self.assertGreater(with_locator, neutral * 1.5)
            # Ein anderes Rufzeichen (Contest) nimmt den Locator nicht mit.
            self.assertLess(self._share("DL1AA", self.ASIA, 4000), with_locator / 2)
        finally:
            q._call_pool, q._filtered_pools, q._station_position, q._station_call = saved

    def test_pool_picks_country_by_home_location(self):
        saved = q._call_pool, dict(q._filtered_pools)
        dl, ja = q._country_of("DL1AA"), q._country_of("JA1AA")
        q._call_pool, q._filtered_pools = [("DL1AA", dl), ("JA1AA", ja)], {}
        try:
            picks = [q._pick_call(home="DL4YM")[0] for _ in range(2000)]
            self.assertGreater(picks.count("DL1AA"), picks.count("JA1AA") * 3)
        finally:
            q._call_pool, q._filtered_pools = saved[0], saved[1]


if __name__ == "__main__":
    unittest.main()
