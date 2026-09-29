import unittest

from scripts.fscg_cfl_fixture_adapter import parse_round


SOURCE = {
    "id": "uefa-soccer-montenegro-montenegrin-first-league-men",
    "sport": "Soccer",
    "league": "Montenegrin First League | Men",
    "region": "Montenegro",
    "catalog_terms": ["Montenegrin First League | Men"],
    "endpoint": "https://fscg.me/takmicenja/meridianbet-1-cfl/",
}


def page():
    return """<html><body>
    <h1>Meridianbet 1. CFL</h1><p>2026/27</p><h2>10. kolo</h2>
    <p>10.10.2026.17:00 SRC Topolica Mornar - Jezero</p>
    <p>10.10.2026.17:00 Stadion Velika plaža Otrant-Olympic - OFK Mladost Lob.bet</p>
    <p>10.10.2026.17:00 Stadion pod Vrmcem Bokelj sbbet - Petrovac</p>
    <p>10.10.2026.17:00 Gradski stadion Budućnost - Sutjeska</p>
    <p>10.10.2026.17:00 Stadion FK Arsenal Arsenal - Dečić</p>
    </body></html>""".encode()


class FscgCflAdapterTests(unittest.TestCase):
    def test_exact_round_is_scoped_and_timed(self):
        events = parse_round(page(), SOURCE)
        self.assertEqual(5, len(events))
        self.assertEqual("Jezero at Mornar", events[0]["name"])
        self.assertEqual("2026-10-10T15:00:00Z", events[0]["start_time"])
        self.assertEqual("ROUND 10", events[0]["season_stage"])

    def test_changed_pairing_fails_closed(self):
        changed = page().replace(b"Mornar - Jezero", b"Mornar - Petrovac", 1)
        with self.assertRaisesRegex(ValueError, "fixture changed"):
            parse_round(changed, SOURCE)

    def test_wrong_catalog_scope_fails_closed(self):
        bad = dict(SOURCE, league="Montenegrin Cup | Men")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_round(page(), bad)


if __name__ == "__main__":
    unittest.main()
