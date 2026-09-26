"""Lithuanian senior calendars and one-event scope."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class LithuaniaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") == "Lithuania" for e in g["events"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_three_independent_competitions(self):
        self.assertEqual(3, len(self.events))
        self.assertEqual(3, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_league_qualification_and_cup_final_revision(self):
        league = self.events["soccer-lithuania-a-lyga-men"]
        cup = self.events["soccer-lithuania-lithuanian-football-cup-men"]
        self.assertEqual(("2026-02-21", "2026-11-07"), (league["season_start_date"], league["season_end_date"]))
        self.assertFalse(league["season_window_complete"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[league["key"]]["season_state"])
        self.assertEqual(("2026-04-01", "2026-10-11"), (cup["season_start_date"], cup["season_end_date"]))

    def test_senior_supercup_single_event(self):
        event = self.events["soccer-lithuania-lithuanian-super-cup-men"]
        self.assertEqual(("2026-02-16", "2026-02-16"), (event["season_start_date"], event["season_end_date"]))
        row = self.inventory[event["key"]]
        self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
        self.assertEqual("official-event-window", row["sources"][0]["type"])


if __name__ == "__main__":
    unittest.main()
