import unittest

from scripts.high_yield_soccer_fixture_adapter import parse_fixtures


def source(source_id, league, region):
    return {
        "id": source_id,
        "sport": "Soccer",
        "league": league,
        "region": region,
        "catalog_terms": [league],
        "endpoint": "https://example.test",
    }


class HighYieldFixtureAdapterTests(unittest.TestCase):
    def test_uae_homepage_cannot_supply_league_fixtures(self):
        with self.assertRaisesRegex(ValueError,'source identity not configured'):
            parse_fixtures('<html>ADNOC Pro League View all fixtures United Hatta 17:15</html>',
                source('soccer-afc-united-arab-emirates-uae-pro-league-men','UAE Pro League | Men','United Arab Emirates'))

    def test_cpl_current_slice_is_timed(self):
        page = """<html><body>Canadian Premier League OneSoccer Atlético Ottawa Cavalry FC 19:00
        Inter Toronto Cavalry FC 13:00 Forge FC Halifax Wanderers 16:00 FC Supra Pacific FC 19:00</body></html>"""
        events = parse_fixtures(
            page,
            source("concacaf-soccer-canada-canadian-premier-league-men", "Canadian Premier League | Men", "Canada"),
        )
        self.assertEqual(4, len(events))
        self.assertEqual("2026-09-30T23:00:00Z", events[0]["start_time"])

    def test_wrong_scope_fails_closed(self):
        bad = source("concacaf-soccer-canada-canadian-premier-league-men", "Canadian Cup | Men", "Canada")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_fixtures("<html><body>Canadian Premier League OneSoccer</body></html>", bad)


if __name__ == "__main__":
    unittest.main()
