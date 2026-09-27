"""Japanese and Korean senior calendars remain tied to exact editions."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class EastAsiaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Japan", "Korea"} for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_eight_distinct_sources_without_synthetic_recurring_dates(self):
        self.assertEqual(8, len(self.events))
        self.assertEqual(8, len({e["source_id"] for e in self.events.values()}))
        for e in self.events.values():
            self.assertNotIn("season_start", e)
            self.assertNotIn("season_end", e)
            self.assertTrue(self.sources[e["source_id"]]["official_schedule_url"].startswith("https://"))

    def test_japan_transition_and_separate_cups(self):
        dates = {
            "soccer-japan-j1-league-men": ("2026-08-07", "2027-06-06"),
            "soccer-japan-j2-league-men": ("2026-08-08", "2027-06-06"),
            "soccer-japan-emperor-s-cup-men": ("2026-08-19", "2027-01-01"),
            "soccer-korea-korean-fa-cup-men": ("2026-06-20", "2027-06-05"),
        }
        for key, pair in dates.items():
            e = self.events[key]
            self.assertEqual(pair, (e["season_start_date"], e["season_end_date"]))
            self.assertEqual("DATED_WINDOW", self.inventory[key]["season_state"])
        self.assertIn("transition", self.events["soccer-japan-j1-league-men"]["season_basis"])
        levain = self.events["soccer-japan-j-league-cup-men"]
        self.assertEqual("2026-09-02", levain["season_start_date"])
        self.assertFalse(levain["season_window_complete"])
        self.assertNotIn("season_end_date", levain)
        self.assertTrue(self.events["soccer-japan-japanese-super-cup-men"]["season_hold"])
        self.assertNotIn("season_start_date", self.events["soccer-japan-japanese-super-cup-men"])

    def test_korean_leagues_include_final_phases_but_tie_scope_remains_open(self):
        for key in ("soccer-korea-k-league-1-men", "soccer-korea-k-league-2-men"):
            e = self.events[key]
            self.assertEqual(("2026-02-28", "2026-12-06"), (e["season_start_date"], e["season_end_date"]))
            self.assertFalse(e["season_window_complete"])
            self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        self.assertIn("lower-tier", self.events["soccer-korea-korean-fa-cup-men"]["season_basis"])

    def test_configured_j1_adapter_and_other_gaps_are_preserved(self):
        j1 = self.sources[self.events["soccer-japan-j1-league-men"]["source_id"]]
        self.assertEqual(("espn-daily", "complete"), (j1["source_type"], j1["coverage_status"]))
        self.assertTrue(j1["endpoint"].endswith("jpn.1/scoreboard"))
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory["soccer-japan-j1-league-men"]["coverage_state"])
        for key in ("soccer-japan-j2-league-men", "soccer-japan-j-league-cup-men"):
            self.assertEqual("jleague-fixtures", self.sources[self.events[key]["source_id"]]["source_type"])
            self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
        for key in set(self.events) - {"soccer-japan-j1-league-men", "soccer-japan-j2-league-men", "soccer-japan-j-league-cup-men"}:
            self.assertEqual("coverage-gap", self.sources[self.events[key]["source_id"]]["source_type"])
            self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
