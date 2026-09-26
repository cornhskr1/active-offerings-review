"""Irish and Icelandic phases, cup starts, and senior single events."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class IrelandIcelandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Ireland", "Iceland"} for e in g["events"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_six_independent_sources(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_phase_and_nonleague_scope(self):
        iceland = self.events["soccer-iceland-besta-deild-karla-rvalsdeild-men"]
        ireland = self.events["soccer-ireland-league-of-ireland-premier-division-men"]
        cup = self.events["soccer-ireland-fai-cup-men"]
        self.assertEqual(("2026-04-11", "2026-10-24"), (iceland["season_start_date"], iceland["season_end_date"]))
        self.assertEqual("2026-11-08", ireland["season_end_date"])
        self.assertFalse(ireland["season_window_complete"])
        self.assertEqual("2026-05-10", cup["season_start_date"])

    def test_c_division_hold_and_senior_single_events(self):
        c = self.events["soccer-iceland-league-cup-c-men"]
        self.assertTrue(c["season_hold"])
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[c["key"]]["season_state"])
        for key, date in (("soccer-iceland-super-cup-men", "2026-03-29"), ("soccer-ireland-president-s-cup-men", "2026-01-31")):
            event = self.events[key]
            self.assertEqual((date, date), (event["season_start_date"], event["season_end_date"]))
            self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
