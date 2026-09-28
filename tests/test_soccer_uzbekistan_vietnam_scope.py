"""The final AFC domestic block keeps each senior competition's calendar separate."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class UzbekistanVietnamScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Uzbekistan", "Vietnam"} for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {e["identity_key"]: e for e in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_distinct_sources_and_no_generic_recurring_months(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertNotIn("season_start", event)
            self.assertNotIn("season_end", event)
            if key == "soccer-vietnam-v-league-1-men":
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-vpf-vleague-fixtures", self.sources[event["source_id"]]["source_type"])
                self.assertEqual("partial", self.sources[event["source_id"]]["coverage_status"])
            elif key == "soccer-uzbekistan-uzbekistan-super-league-men":
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-pfl-uz-superleague-fixtures", self.sources[event["source_id"]]["source_type"])
                self.assertEqual("partial", self.sources[event["source_id"]]["coverage_status"])
            else:
                self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
                self.assertEqual("coverage-gap", self.sources[event["source_id"]]["source_type"])

    def test_uzbekistan_cup_qualifying_does_not_invent_final(self):
        cup = self.events["soccer-uzbekistan-uzbekistan-cup-men"]
        self.assertEqual("2026-03-22", cup["season_start_date"])
        self.assertNotIn("season_end_date", cup)
        self.assertFalse(cup["season_window_complete"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[cup["key"]]["season_state"])
        self.assertEqual("2026-03-15", self.events["soccer-uzbekistan-uzbekistan-super-cup-men"]["season_start_date"])

    def test_vietnam_edition_boundaries_and_lower_division_cup(self):
        league = self.events["soccer-vietnam-v-league-1-men"]
        cup = self.events["soccer-vietnam-vietnamese-cup-men"]
        shield = self.events["soccer-vietnam-vietnamese-super-cup-men"]
        self.assertEqual(("2026-09-04", "2027-05-22"), (league["season_start_date"], league["season_end_date"]))
        self.assertEqual(("2026-09-18", "2027-05-30"), (cup["season_start_date"], cup["season_end_date"]))
        self.assertIn("V.League 2", cup["season_basis"])
        self.assertEqual("2026-08-30", shield["season_start_date"])
        self.assertIn("2025–26", shield["season_basis"])


if __name__ == "__main__":
    unittest.main()
