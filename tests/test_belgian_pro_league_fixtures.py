import json
import unittest

from scripts.belgian_pro_league_fixtures import COMPETITION_ID, EDITION_ID, parse_challenger_round


SOURCE = {"id": "uefa-soccer-belgium-challenger-pro-league-men", "sport": "Soccer",
          "league": "Challenger Pro League | Men", "region": "Belgium",
          "catalog_terms": ["Challenger Pro League | Men"]}


def page():
    rows = []
    for i in range(7):
        rows.append({"id": f"00000000-0000-0000-0000-{i:012x}", "slug": f"fixture-{i}",
                     "competition": {"id": COMPETITION_ID}, "edition": {"id": EDITION_ID},
                     "gameweek": {"week": 7}, "homeTeam": {"name": "Club NXT" if i == 0 else f"Home {i}"},
                     "awayTeam": {"name": f"Away {i}"}, "date": "2026-10-10",
                     "time": "2026-10-10T14:00:00Z"})
    data = {"props": {"pageProps": {"data": {"page": {"grids": [
        {"areas": [{"modules": [{"subtype": "football_competition_match",
                              "data": {"gameweek": {"week": 7}, "matches": rows}}]}]}]}}}}}
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(data) + '</script>'


class BelgianFixturesTests(unittest.TestCase):
    def test_reserve_squad_held_from_exact_regular_round(self):
        events, held, total = parse_challenger_round(page(), SOURCE)
        self.assertEqual((len(events), held, total), (6, 1, 7))
        self.assertTrue(all("Club NXT" not in e["name"] for e in events))
        self.assertEqual("2026-10-10T14:00:00Z", events[0]["start_time"])

    def test_changed_edition_or_missing_match_blocks_round(self):
        with self.assertRaisesRegex(ValueError, "edition"):
            parse_challenger_round(page().replace(EDITION_ID, "other-edition", 1), SOURCE)
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_challenger_round(page(), {**SOURCE, "catalog_terms": ["Other"]})


if __name__ == "__main__":
    unittest.main()
