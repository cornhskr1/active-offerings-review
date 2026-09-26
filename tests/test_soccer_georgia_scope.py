"""Georgian top division, cup qualifiers, and four-team Super Cup are distinct."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class GeorgiaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        group = next(g for g in soccer["groups"] if g.get("country") == "Georgia")
        cls.events = {e["key"]: e for e in group["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_league_and_cup_scope_stays_partial(self):
        self.assertEqual(3, len(self.events))
        self.assertEqual(3, len({e["source_id"] for e in self.events.values()}))
        league = self.events["soccer-georgia-erovnuli-liga-men"]
        cup = self.events["soccer-georgia-georgian-cup-men"]
        self.assertEqual(("2026-02-28", "2026-12-06"), (league["season_start_date"], league["season_end_date"]))
        self.assertFalse(league["season_window_complete"])
        self.assertIn("May 24", cup["season_window"])
        self.assertFalse(cup["season_window_complete"])
        self.assertNotIn("season_end_date", cup)
        for event in (league, cup):
            self.assertEqual("PARTIAL_WINDOW", self.inventory[event["key"]]["season_state"])
            self.assertEqual("ADAPTER_GAP", self.inventory[event["key"]]["coverage_state"])

    def test_super_cup_window_includes_semifinals(self):
        key = "soccer-georgia-georgian-super-cup-men"
        event = self.events[key]
        source = self.sources[event["source_id"]]
        self.assertEqual(("2026-06-27", "2026-07-01"), (event["season_start_date"], event["season_end_date"]))
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual(("2026-06-27", "2026-07-01"), (source["official_events"][0]["start_date"], source["official_events"][0]["end_date"]))


if __name__ == "__main__":
    unittest.main()
