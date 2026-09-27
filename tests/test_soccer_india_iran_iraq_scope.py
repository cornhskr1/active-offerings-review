"""The next AFC country block keeps nine competition windows and sources distinct."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"India", "Iran", "Iraq"}


class IndiaIranIraqScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in COUNTRIES for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_all_nine_distinct_and_no_recurring_assumption(self):
        self.assertEqual(9, len(self.events))
        self.assertEqual(9, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertNotIn("season_start", event)
            self.assertNotIn("season_end", event)
            self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
            self.assertEqual("coverage-gap", self.sources[event["source_id"]]["source_type"])

    def test_isl_revised_kickoff_and_iranian_cups_are_held(self):
        held = {
            "soccer-india-indian-super-league-men",
            "soccer-india-super-cup-men",
            "soccer-iran-hazfi-cup-men",
            "soccer-iran-iranian-super-cup-men",
        }
        for key in held:
            self.assertTrue(self.events[key]["season_hold"])
            self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
            self.assertNotIn("season_start_date", self.events[key])
        self.assertIn("superseded", self.events["soccer-india-indian-super-league-men"]["season_basis"])

    def test_durand_and_two_iraqi_cups_have_separate_exact_windows(self):
        dates = {
            "soccer-india-durand-cup-men": ("2026-07-25", "2026-08-23"),
            "soccer-iraq-iraq-fa-cup-men": ("2026-12-13", "2027-05-14"),
            "soccer-iraq-iraqi-super-cup-men": ("2026-12-14", "2026-12-18"),
        }
        for key, window in dates.items():
            e = self.events[key]
            self.assertEqual(window, (e["season_start_date"], e["season_end_date"]))
            self.assertEqual("DATED_WINDOW", self.inventory[key]["season_state"])
        self.assertIn("four-team", self.events["soccer-iraq-iraqi-super-cup-men"]["season_basis"])

    def test_premier_is_not_stars_and_iran_league_end_is_open(self):
        iraq = self.events["soccer-iraq-iraqi-premier-league-men"]
        iran = self.events["soccer-iran-persian-gulf-pro-league-men"]
        self.assertEqual("2026-09-11", iraq["season_start_date"])
        self.assertIn("distinct from the top-tier Iraq Stars League", iraq["season_basis"])
        for e in (iraq, iran):
            self.assertFalse(e["season_window_complete"])
            self.assertNotIn("season_end_date", e)
            self.assertEqual("PARTIAL_WINDOW", self.inventory[e["key"]]["season_state"])


if __name__ == "__main__":
    unittest.main()
