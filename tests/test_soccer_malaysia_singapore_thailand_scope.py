"""The third AFC country block preserves competition and shared-match scope."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"Malaysia", "Singapore", "Thailand"}


class MalaysiaSingaporeThailandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in COUNTRIES for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {e["identity_key"]: e for e in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_ten_distinct_sources_without_recurring_month_assumptions(self):
        self.assertEqual(10, len(self.events))
        self.assertEqual(10, len({e["source_id"] for e in self.events.values()}))
        for key, e in self.events.items():
            self.assertNotIn("season_start", e)
            self.assertNotIn("season_end", e)
            self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
            self.assertEqual("coverage-gap", self.sources[e["source_id"]]["source_type"])

    def test_malaysia_shield_shares_one_league_fixture(self):
        league = self.events["soccer-malaysia-malaysia-super-league-men"]
        shield = self.events["soccer-malaysia-charity-shield-men"]
        self.assertEqual(league["season_start_date"], shield["season_start_date"])
        self.assertEqual(shield["season_start_date"], shield["season_end_date"])
        self.assertIn("same physical match", shield["season_basis"])
        self.assertIn("league points", shield["season_basis"])
        self.assertEqual("2027-05-30", self.events["soccer-malaysia-malaysia-cup-men"]["season_end_date"])
        self.assertEqual("2027-01-16", self.events["soccer-malaysia-malaysia-fa-cup-men"]["season_end_date"])

    def test_singapore_cup_hold_and_shield_separate(self):
        cup = self.events["soccer-singapore-singapore-cup-men"]
        self.assertTrue(cup["season_hold"])
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[cup["key"]]["season_state"])
        league = self.events["soccer-singapore-singapore-premier-league-men"]
        shield = self.events["soccer-singapore-community-shield-men"]
        self.assertEqual("2026-09-11", league["season_start_date"])
        self.assertEqual("2027-05-16", league["season_end_date"])
        self.assertEqual("2026-09-06", shield["season_start_date"])

    def test_thai_cups_have_confirmed_qualifying_not_final_dates(self):
        league = self.events["soccer-thailand-thai-league-1-men"]
        self.assertEqual(("2026-09-04", "2027-05-30"), (league["season_start_date"], league["season_end_date"]))
        for suffix, start in (("thai-fa-cup-men", "2026-09-22"), ("thai-league-cup-men", "2026-09-05")):
            e = self.events["soccer-thailand-" + suffix]
            self.assertEqual(start, e["season_start_date"])
            self.assertNotIn("season_end_date", e)
            self.assertFalse(e["season_window_complete"])
            self.assertEqual("PARTIAL_WINDOW", self.inventory[e["key"]]["season_state"])


if __name__ == "__main__":
    unittest.main()
