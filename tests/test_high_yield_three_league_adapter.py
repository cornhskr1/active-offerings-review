import unittest

from scripts.high_yield_three_league_adapter import (
    parse_egypt_fixture,
    parse_saudi_fixture,
    parse_nz_fixtures,
)


class HighYieldThreeLeagueAdapterTests(unittest.TestCase):
    def test_egypt_scoped_fixture_is_timed(self):
        source = {
            "id":"caf-soccer-egypt-egyptian-premier-league-men",
            "sport":"Soccer","league":"Egyptian Premier League | Men","region":"Egypt",
            "catalog_terms":["Egyptian Premier League | Men"],"endpoint":"https://example.test"
        }
        page = """<html><body>المصري القناة الجولة 6 الأحد 11 أكتوبر 2026 05:00</body></html>"""
        events = parse_egypt_fixture(page, source)
        self.assertEqual(1, len(events))
        self.assertEqual("2026-10-11T14:00:00Z", events[0]["start_time"])

    def test_saudi_scoped_fixture_is_timed(self):
        source = {
            "id":"soccer-afc-saudi-arabia-first-division-league-men",
            "sport":"Soccer","league":"First Division League | Men","region":"Saudi Arabia",
            "catalog_terms":["First Division League | Men"],"endpoint":"https://example.test"
        }
        page = """<html><body>First Division League Wednesday 14-10-2026 18:30 Al Jandal Al Okhdood</body></html>"""
        events = parse_saudi_fixture(page, source)
        self.assertEqual(1, len(events))
        self.assertEqual("2026-10-14T15:30:00Z", events[0]["start_time"])

    def test_nz_widget_parses_mens_fixture(self):
        source = {
            "id":"ofc-soccer-new-zealand-national-league-men",
            "sport":"Soccer","league":"New Zealand National League | Men","region":"New Zealand",
            "catalog_terms":["New Zealand National League | Men"],"endpoint":"https://example.test"
        }
        page = """<html><body><h1>Dettol Men's National League 2026</h1>
        <div>03/10/2026 2:30 PM Auckland City FC vs Auckland United FC</div></body></html>"""
        events = parse_nz_fixtures(page, source)
        self.assertEqual(1, len(events))
        self.assertEqual("Auckland United FC at Auckland City FC", events[0]["name"])

    def test_wrong_scope_fails_closed(self):
        source = {
            "id":"soccer-afc-saudi-arabia-first-division-league-men",
            "sport":"Soccer","league":"Saudi Pro League | Men","region":"Saudi Arabia",
            "catalog_terms":["Saudi Pro League | Men"],"endpoint":"https://example.test"
        }
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_saudi_fixture("<html><body>First Division League</body></html>", source)


if __name__ == "__main__":
    unittest.main()
