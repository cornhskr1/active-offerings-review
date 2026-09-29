import unittest

from scripts.svff_womens_cup_adapter import parse_current_fixtures


SOURCE = {
    "id": "uefa-soccer-sweden-svenska-cupen-women",
    "sport": "Soccer",
    "league": "Svenska Cupen | Women",
    "region": "Sweden",
    "endpoint": "https://www.svenskfotboll.se/svenskacupen/",
}


def page():
    cards = [
        "29 SEP. Svenska Cupen 2026/27 omg. 1-3 Linköping FC - IFK Norrköping FK 19:00 Bilbörsen Arena",
        "29 SEP. Svenska Cupen 2026/27 omg. 1-3 Jitex BK - Vittsjö GIK 19:00 Åbyvallen 1 Konstgräs",
        "30 SEP. Svenska Cupen 2026/27 omg. 1-3 Sunnanå SK - Piteå IF DFF 19:00 Electrolux Home Arena",
        "30 SEP. Svenska Cupen 2026/27 omg. 1-3 Örebro SK FK - Eskilstuna United DFF 19:00 Behrn Arena",
        "30 SEP. Svenska Cupen 2026/27 omg. 1-3 Älvsjö AIK FF - Djurgården 20:00 Älvsjö IP 1",
    ]
    return ("<h1>Svenska Cupen</h1><h2>Svenska Cupen 2026/27</h2><h3>Dam</h3>"
            "<p>Omgång 3: spelas 22 september-1 oktober</p>"
            + "".join(f"<a>{x}</a>" for x in cards)).encode()


class SvffWomensCupAdapterTests(unittest.TestCase):
    def test_current_exact_cards_are_scoped_and_timed(self):
        events = parse_current_fixtures(page(), SOURCE)
        self.assertEqual(5, len(events))
        self.assertEqual("IFK Norrköping FK at Linköping FC", events[0]["name"])
        self.assertEqual("2026-09-29T17:00:00Z", events[0]["start_time"])

    def test_mens_or_old_phase_is_not_borrowed(self):
        changed = page().replace(b"29 SEP.", b"17 SEP.", 1)
        events = parse_current_fixtures(changed, SOURCE)
        self.assertEqual(4, len(events))

    def test_wrong_child_scope_fails_closed(self):
        bad = dict(SOURCE, league="Svenska Cupen | Men")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_current_fixtures(page(), bad)


if __name__ == "__main__":
    unittest.main()
