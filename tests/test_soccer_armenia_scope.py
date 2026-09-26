"""Armenian senior cup preliminaries and the completed Super Cup stay distinct."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class ArmeniaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        group = next(g for g in soccer["groups"] if g.get("country") == "Armenia")
        cls.events = {e["key"]: e for e in group["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_league_and_cup_remain_partial_with_separate_gaps(self):
        self.assertEqual(3, len(self.events))
        self.assertEqual(3, len({e["source_id"] for e in self.events.values()}))
        for key in ("soccer-armenia-armenian-premier-league-men", "soccer-armenia-armenian-cup-men"):
            event = self.events[key]
            self.assertFalse(event["season_window_complete"])
            self.assertNotIn("season_end_date", event)
            self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
            self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
        self.assertIn("July 31", self.events["soccer-armenia-armenian-premier-league-men"]["season_window"])
        self.assertIn("August 24", self.events["soccer-armenia-armenian-cup-men"]["season_window"])

    def test_completed_super_cup_has_only_one_official_event(self):
        key = "soccer-armenia-armenian-super-cup-men"
        event = self.events[key]
        source = self.sources[event["source_id"]]
        self.assertEqual(("2026-03-12", "2026-03-12"), (event["season_start_date"], event["season_end_date"]))
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual(1, len(source["official_events"]))
        self.assertEqual(key.replace("soccer-", "uefa-soccer-"), source["official_events"][0]["source_id"])


if __name__ == "__main__":
    unittest.main()
