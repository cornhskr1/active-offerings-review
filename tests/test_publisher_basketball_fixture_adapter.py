import unittest

from scripts.publisher_basketball_fixture_adapter import (
    parse_fiba_3x3_usa_slice,
    parse_fiba_mens_world_cup_slice,
    parse_fiba_womens_world_cup_finals,
    parse_lnb_chile_home,
)


class PublisherBasketballFixtureAdapterTests(unittest.TestCase):
    def test_fiba_3x3_men_and_women_share_verified_publication(self):
        page = """<html><body>
        FIBA 3x3 World Cup 2026 USA announce rosters
        men Latvia 1:20 p.m. ET Czechia 3:10 p.m. ET Mongolia 1:20 p.m. ET Poland 3:35 p.m. ET
        women Hungary 12:55 p.m. ET Australia 2:45 p.m. ET Mongolia 12:30 p.m. ET Spain 2:20 p.m. ET
        </body></html>"""
        base = {"sport":"Basketball","region":"International","endpoint":"https://example.test"}
        men = parse_fiba_3x3_usa_slice(page, {
            **base, "id":"basketball-fiba-3x3-world-cup-men", "league":"FIBA 3x3 World Cup | Men"
        })
        women = parse_fiba_3x3_usa_slice(page, {
            **base, "id":"basketball-fiba-3x3-world-cup-women", "league":"FIBA 3x3 World Cup | Women"
        })
        self.assertEqual(4, len(men))
        self.assertEqual(4, len(women))
        self.assertEqual("2026-06-02T17:20:00Z", men[0]["start_time"])
        self.assertEqual("2026-06-02T16:55:00Z", women[0]["start_time"])

    def test_fiba_mens_world_cup_scoped_americas_slice(self):
        page = """<html><body>
        FIBA Basketball World Cup 2027 Americas Qualifiers
        August 27 CHI vs. USA 19:10
        August 31 USA vs. COL 19:00
        </body></html>"""
        source = {
            "id":"basketball-fiba-world-cup-men","sport":"Basketball",
            "league":"FIBA Basketball World Cup | Men","region":"International",
            "endpoint":"https://example.test"
        }
        events = parse_fiba_mens_world_cup_slice(page, source)
        self.assertEqual(2, len(events))
        self.assertEqual("USA at Chile", events[0]["name"])
        self.assertEqual("Colombia at USA", events[1]["name"])

    def test_fiba_womens_world_cup_final_phase(self):
        page = """<html><body>
        FIBA Women's Basketball World Cup 2026 Final set
        September 13 Third-Place game - Germany v Spain - 16:30 Local Time
        Final - France v USA - 20:00 Local Time
        </body></html>"""
        source = {
            "id":"basketball-fiba-world-cup-women","sport":"Basketball",
            "league":"FIBA Basketball World Cup | Women","region":"International",
            "endpoint":"https://example.test"
        }
        events = parse_fiba_womens_world_cup_finals(page, source)
        self.assertEqual(2, len(events))
        self.assertEqual("2026-09-13T14:30:00Z", events[0]["start_time"])
        self.assertEqual("2026-09-13T18:00:00Z", events[1]["start_time"])

    def test_lnb_homepage_parses_current_timed_cards(self):
        page = """<html><body>
        Liga Nacional de Básquetbol de Chile
        LIGA CHERY MIÉ, 30-09 · 23:00 PUE 0 ESO 0
        LIGA CHERY JUE, 01-10 · 00:30 LEO 0 CDV 0
        </body></html>"""
        source = {
            "id":"chile-lnb","sport":"Basketball",
            "league":"Liga Nacional de Basquetbol de Chile (LNB) | Men",
            "region":"Chile","endpoint":"https://lnbchile.com/"
        }
        events = parse_lnb_chile_home(page, source)
        self.assertEqual(2, len(events))
        self.assertEqual("2026-09-30T23:00:00Z", events[0]["start_time"])
        self.assertEqual("ESO at PUE", events[0]["name"])


if __name__ == "__main__":
    unittest.main()
