"""FAW and FSF senior calendars, the withdrawn cup, and the single super cup."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class WalesFaroeScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Wales", "Faroe Islands"} for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_six_independent_competitions(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])
            self.assertEqual("2026-09-26", event["last_verified"])

    def test_faw_playoff_and_qualifying_bounds(self):
        league = self.events["soccer-wales-cymru-premier-men"]
        cup = self.events["soccer-wales-welsh-cup-men"]
        self.assertEqual(("2026-07-31", "2027-05-09"), (league["season_start_date"], league["season_end_date"]))
        self.assertEqual(("2026-07-24", "2027-04-18"), (cup["season_start_date"], cup["season_end_date"]))
        self.assertIn("play-off", league["season_basis"])

    def test_withdrawn_welsh_league_cup_held(self):
        key = "soccer-wales-welsh-league-cup-men"
        self.assertTrue(self.events[key]["season_hold"])
        self.assertNotIn("season_start_date", self.events[key])
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])

    def test_fsf_renaming_and_senior_cup_scope(self):
        league = self.events["soccer-faroe-islands-faroe-islands-premier-league-men"]
        cup = self.events["soccer-faroe-islands-faroe-islands-cup-men"]
        self.assertEqual(("2026-03-06", "2026-10-31"), (league["season_start_date"], league["season_end_date"]))
        self.assertIn("Meistaradeildin", league["season_basis"])
        self.assertEqual(("2026-04-15", "2026-09-05"), (cup["season_start_date"], cup["season_end_date"]))

    def test_super_cup_is_one_completed_official_event(self):
        key = "soccer-faroe-islands-faroe-islands-super-cup-men"
        event = self.events[key]
        source = self.sources[event["source_id"]]
        self.assertEqual(("2026-02-28", "2026-02-28"), (event["season_start_date"], event["season_end_date"]))
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual(1, len(source["official_events"]))
        self.assertEqual("2026-02-28", source["official_events"][0]["start_date"])


if __name__ == "__main__":
    unittest.main()
