"""Romanian and Bulgarian dates retain competition and source boundaries."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class RomaniaBulgariaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Romania", "Bulgaria"} for e in g["events"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_six_independent_sources(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_cup_and_league_scope(self):
        cup = self.events["soccer-romania-cupa-rom-niei-men"]
        self.assertEqual(("2026-07-08", "2027-05-12"), (cup["season_start_date"], cup["season_end_date"]))
        league = self.events["soccer-romania-liga-i-men"]
        self.assertEqual("2026-07-17", league["season_start_date"])
        for key in ("soccer-romania-liga-i-men", "soccer-bulgaria-bulgarian-first-professional-league-parva-liga-men", "soccer-bulgaria-bulgarian-cup-men"):
            with self.subTest(key=key):
                self.assertFalse(self.events[key]["season_window_complete"])
                self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])

    def test_completed_super_cups_are_single_events(self):
        for key, date in (("soccer-romania-supercupa-rom-niei-men", "2026-07-12"), ("soccer-bulgaria-bulgarian-supercup-men", "2026-09-09")):
            with self.subTest(key=key):
                event = self.events[key]
                self.assertEqual((date, date), (event["season_start_date"], event["season_end_date"]))
                row = self.inventory[key]
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual("official-event-window", row["sources"][0]["type"])


if __name__ == "__main__":
    unittest.main()
