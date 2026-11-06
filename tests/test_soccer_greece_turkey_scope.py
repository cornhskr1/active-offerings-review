"""Keep Greek and Turkish senior calendars distinct and qualified."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class GreeceTurkeyScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Greece", "Turkey"} for e in g["events"]}
        cls.inventory = {r["identity_key"]: r for r in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_five_distinct_sources_and_restrictions(self):
        self.assertEqual(5, len(self.events))
        self.assertEqual(5, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(["NO PROPOSITION WAGERS"] if "turkey" in key else [], event["restrictions"])
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_verified_bounds_and_visible_uncertainty(self):
        cup = self.events["soccer-greece-greek-cup-men"]
        self.assertEqual(("2026-08-11", "2027-05-27"), (cup["season_start_date"], cup["season_end_date"]))
        league = self.events["soccer-turkey-s-per-lig-men"]
        self.assertEqual(("2026-08-14", "2027-05-23"), (league["season_start_date"], league["season_end_date"]))
        for key in ("soccer-greece-super-league-men", "soccer-turkey-turkish-cup-men"):
            with self.subTest(key=key):
                self.assertFalse(self.events[key]["season_window_complete"])
                self.assertNotIn("season_end_date", self.events[key])
                self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        key = "soccer-turkey-turkish-super-cup-men"
        super_cup = self.events[key]
        self.assertFalse(super_cup.get("season_hold", False))
        self.assertTrue(super_cup["season_window_complete"])
        self.assertEqual(("2027-01-04", "2027-01-09"),
                         (super_cup["season_start_date"], super_cup["season_end_date"]))
        self.assertIn("2026 edition", super_cup["season_edition"])
        self.assertTrue(super_cup["season_source_url"].startswith("https://www.tff.org/"))
        # The historical fixture inventory is not refreshed by calendar research.
        self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
