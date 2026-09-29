"""Azerbaijan cup qualifiers must not disappear behind the top-flight calendar."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class AzerbaijanScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        group = next(g for g in soccer["groups"] if g.get("country") == "Azerbaijan")
        cls.events = {e["key"]: e for e in group["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_distinct_league_and_cup_sources(self):
        self.assertEqual(2, len(self.events))
        self.assertEqual(2, len({e["source_id"] for e in self.events.values()}))
        league = self.events["soccer-azerbaijan-azerbaijan-premier-league-apl-men"]
        cup = self.events["soccer-azerbaijan-azerbaijan-cup-men"]
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[league["key"]]["coverage_state"])
        self.assertEqual("official-affa-latest-round", self.sources[league["source_id"]]["source_type"])
        self.assertEqual("ADAPTER_GAP", self.inventory[cup["key"]]["coverage_state"])
        self.assertEqual("coverage-gap", self.sources[cup["source_id"]]["source_type"])

    def test_cup_includes_lower_tier_qualifiers(self):
        cup = self.events["soccer-azerbaijan-azerbaijan-cup-men"]
        self.assertEqual(("2026-10-07", "2027-05-12"), (cup["season_start_date"], cup["season_end_date"]))
        self.assertIn("eligibility", cup["season_basis"])
        self.assertEqual("DATED_WINDOW", self.inventory[cup["key"]]["season_state"])

    def test_league_final_not_invented(self):
        league = self.events["soccer-azerbaijan-azerbaijan-premier-league-apl-men"]
        self.assertFalse(league["season_window_complete"])
        self.assertNotIn("season_end_date", league)
        self.assertEqual("PARTIAL_WINDOW", self.inventory[league["key"]]["season_state"])


if __name__ == "__main__":
    unittest.main()
