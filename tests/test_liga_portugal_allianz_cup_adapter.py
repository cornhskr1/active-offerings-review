import unittest

from scripts.liga_portugal_allianz_cup_adapter import parse_quarterfinals


SOURCE = {
    "id": "uefa-soccer-portugal-ta-a-da-liga-men",
    "sport": "Soccer",
    "league": "Taça da Liga | Men",
    "region": "Portugal",
    "catalog_terms": ["Taça da Liga | Men"],
    "endpoint": "https://www.ligaportugal.pt/competition/914/allianz-cup/round/20262027",
}


def page():
    return """<html><body>
    <h1>Allianz Cup</h1><div>Época: 2026-2027</div><h2>Quartos-de-Final</h2>
    <div>SCP 20h15 CSM</div>
    <div>FCP 20h30 AVFC</div>
    <div>SCB 18h45 FCF</div>
    <div>SLB 20h45 GVFC</div>
    </body></html>""".encode()


class AllianzCupAdapterTests(unittest.TestCase):
    def test_exact_quarterfinals_are_scoped_and_timed(self):
        events = parse_quarterfinals(page(), SOURCE)
        self.assertEqual(4, len(events))
        self.assertEqual("Marítimo M. at Sporting CP", events[0]["name"])
        self.assertEqual("2026-10-27T20:15:00Z", events[0]["start_time"])

    def test_changed_pairing_fails_closed(self):
        changed = page().replace(b"SCP 20h15 CSM", b"SCP 20h15 GVFC")
        with self.assertRaisesRegex(ValueError, "quarterfinal changed"):
            parse_quarterfinals(changed, SOURCE)

    def test_wrong_catalog_scope_fails_closed(self):
        bad = dict(SOURCE, league="Liga Portugal 2 | Men")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_quarterfinals(page(), bad)


if __name__ == "__main__":
    unittest.main()
