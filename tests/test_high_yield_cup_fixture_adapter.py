import unittest

from scripts.high_yield_cup_fixture_adapter import parse_fixtures


def source(source_id, league, region):
    return {
        "id": source_id,
        "sport": "Soccer",
        "league": league,
        "region": region,
        "catalog_terms": [league],
        "endpoint": "https://example.test",
    }


class HighYieldCupFixtureAdapterTests(unittest.TestCase):
    def test_fai_semifinals_are_exact_and_timed(self):
        page = """<html><body>Club Orange Men's FAI Cup Semi-Finals Bohemians Waterford 19:45
        Galway United Derry City 15:00</body></html>"""
        events = parse_fixtures(page, source("uefa-soccer-ireland-fai-cup-men", "FAI Cup | Men", "Ireland"))
        self.assertEqual(2, len(events))
        self.assertEqual("Waterford at Bohemians", events[0]["name"])
        self.assertEqual("2026-10-09T18:45:00Z", events[0]["start_time"])

    def test_swiss_round_has_sixteen_matches(self):
        teams = " ".join([
            "FC Stade-Lausanne-Ouchy Etoile Carouge FC",
            "FC Rapperswil-Jona FC St. Gallen 1879", "FC Rotkreuz Servette FC",
            "FC Stade Nyonnais SA FC Basel 1893", "FC Köniz SC Brühl SG",
            "FC Bulle FC Wil 1900", "SC Cham FC Sion",
            "FC Grenchen 15 Grasshopper Club Zürich", "FC Winterthur FC Luzern",
            "BSC Old Boys Yverdon Sport FC", "Pully Football FC Lugano",
            "FC Winkeln SG 1 FC Lausanne-Sport", "FC Langenthal Neuchâtel Xamax",
            "FC Aarau FC Zürich", "AC Taverne BSC Young Boys",
            "FC Schaffhausen FC Thun Berner Oberland",
        ])
        page = f"<html><body>Schweizer Cup 1/16 {teams} 19:00 20:00 20:15 16:00 17:00 18:00 14:00 15:00</body></html>"
        events = parse_fixtures(page, source("uefa-soccer-switzerland-swiss-cup-men", "Swiss Cup | Men", "Switzerland"))
        self.assertEqual(16, len(events))

    def test_wrong_scope_fails_closed(self):
        bad = source("uefa-soccer-ireland-fai-cup-men", "League of Ireland Premier Division | Men", "Ireland")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_fixtures("<html><body>Club Orange Men's FAI Cup Semi-Finals Bohemians</body></html>", bad)


if __name__ == "__main__":
    unittest.main()
