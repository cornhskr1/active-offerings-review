"""Separate Balkan senior calendars and fail closed on unverified editions."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"Bosnia and Herzegovina", "Montenegro", "Kosovo"}


class BalkanScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in COUNTRIES for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_nine_identities_keep_independent_missing_adapters(self):
        self.assertEqual(9, len(self.events))
        self.assertEqual(9, len({e["source_id"] for e in self.events.values()}))
        for event in self.events.values():
            source = self.sources[event["source_id"]]
            self.assertEqual("coverage-gap", source["source_type"])
            self.assertEqual("ADAPTER_GAP", self.inventory[event["key"]]["coverage_state"])
            self.assertNotIn("season_start", event)
            self.assertNotIn("season_end", event)

    def test_league_openings_do_not_fabricate_final_rounds(self):
        openings = {
            "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men": "August 8",
            "soccer-montenegro-montenegrin-first-league-men": "August 1",
            "soccer-kosovo-superleague-of-kosovo-superliga-e-kosov-s-men": "August 14",
        }
        for key, opening in openings.items():
            event = self.events[key]
            self.assertIn(opening, event["season_window"])
            self.assertFalse(event["season_window_complete"])
            self.assertNotIn("season_end_date", event)
            self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])

    def test_cups_and_super_cups_await_current_edition_evidence(self):
        for key, event in self.events.items():
            if key in (
                "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men",
                "soccer-montenegro-montenegrin-first-league-men",
                "soccer-kosovo-superleague-of-kosovo-superliga-e-kosov-s-men",
            ):
                continue
            self.assertTrue(event["season_hold"], key)
            self.assertNotIn("season_status", event)
            self.assertNotIn("season_start_date", event)
            self.assertNotIn("season_end_date", event)
            self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertIn("postponed", self.events["soccer-bosnia-and-herzegovina-bosnian-super-cup-men"]["hold_reason"].lower())


if __name__ == "__main__":
    unittest.main()
