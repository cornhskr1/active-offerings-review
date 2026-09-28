"""Slovak and Slovenian senior competitions retain distinct calendar evidence."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class SlovakiaSloveniaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Slovakia", "Slovenia"} for e in g["events"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_five_independent_sources_and_one_partial_league_adapter(self):
        self.assertEqual(5, len(self.events))
        self.assertEqual(5, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            expected = "ADAPTER_CONFIGURED" if key == "soccer-slovenia-slovenian-prvaliga-men" else "ADAPTER_GAP"
            self.assertEqual(expected, self.inventory[key]["coverage_state"])
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_slovak_league_and_early_cup_match(self):
        league = self.events["soccer-slovakia-slovak-first-football-league-slovak-1-liga-men"]
        cup = self.events["soccer-slovakia-slovak-cup-men"]
        self.assertEqual(("2026-07-25", "2027-05-15"), (league["season_start_date"], league["season_end_date"]))
        self.assertEqual(("2026-07-14", "2027-05-01"), (cup["season_start_date"], cup["season_end_date"]))

    def test_slovenian_partial_windows_and_senior_hold(self):
        league = self.events["soccer-slovenia-slovenian-prvaliga-men"]
        cup = self.events["soccer-slovenia-slovenian-football-cup-men"]
        supercup = self.events["soccer-slovenia-slovenian-super-cup-men"]
        self.assertEqual("2026-07-17", league["season_start_date"])
        for event in (league, cup):
            self.assertFalse(event["season_window_complete"])
            self.assertEqual("PARTIAL_WINDOW", self.inventory[event["key"]]["season_state"])
        self.assertTrue(supercup["season_hold"])
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[supercup["key"]]["season_state"])
        self.assertNotIn("season_start_date", supercup)


if __name__ == "__main__":
    unittest.main()
