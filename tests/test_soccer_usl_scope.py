"""The two USL competitions have distinct live feeds and preserve catalog limits."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SoccerUslScopeTests(unittest.TestCase):
    def test_cup_and_womens_league_do_not_share_a_feed(self):
        config = json.loads((ROOT / "data" / "soccer-concacaf-domestic-sources.json").read_text())
        sources = {source["id"]: source for source in config["sources"]}
        cup = sources["concacaf-soccer-united-states-usl-cup-men"]
        women = sources["concacaf-soccer-united-states-usl-super-league-women"]
        self.assertEqual("espn-daily", cup["source_type"])
        self.assertEqual("espn-daily", women["source_type"])
        self.assertTrue(cup["endpoint"].endswith("/usa.usl.l1.cup/scoreboard"))
        self.assertTrue(women["endpoint"].endswith("/usa.w.usl.1/scoreboard"))
        self.assertNotEqual(cup["endpoint"], women["endpoint"])

    def test_current_season_windows_and_no_props_survive(self):
        mapping = json.loads((ROOT / "data" / "catalog-season-map.json").read_text())
        soccer = next(sport for sport in mapping["sports"] if sport["sport"] == "Soccer")
        rows = {event["key"]: event for group in soccer["groups"] for event in group["events"]}
        for key, dates in (
            ("soccer-united-states-usl-cup-men", ("2026-04-25", "2026-10-04")),
            ("soccer-united-states-usl-super-league-women", ("2026-08-15", "2026-12-12")),
        ):
            with self.subTest(key=key):
                self.assertEqual(dates, (rows[key]["season_start_date"],
                                         rows[key]["season_end_date"]))
                self.assertIn("NO PROPOSITION WAGERS", rows[key]["restrictions"])


if __name__ == "__main__":
    unittest.main()
