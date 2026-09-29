"""Provider-family boundaries for Belgium, Netherlands, and Luxembourg soccer."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class BeneluxScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(
            sport for sport in json.loads((DATA / "catalog-season-map.json").read_text())["sports"]
            if sport["sport"] == "Soccer"
        )
        cls.events = {
            event["key"]: event
            for group in soccer["groups"] if group.get("country") in {"Belgium", "Netherlands", "Luxembourg"}
            for event in group["events"]
        }
        cls.sources = {
            source["id"]: source
            for filename in ("global-schedule-sources.json", "soccer-uefa-domestic-sources.json")
            for source in json.loads((DATA / filename).read_text())["sources"]
        }
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
            if row["sport"] == "Soccer"
        }

    def test_family_contains_twelve_distinct_approved_identities(self):
        keys = {key for key in self.events if key.startswith(("soccer-belgium-", "soccer-netherlands-", "soccer-luxembourg-"))}
        self.assertEqual(12, len(keys))

    def test_belgian_cup_uses_published_round_windows_not_invented_fixtures(self):
        key = "soccer-belgium-belgian-cup-beker-van-belgi-men"
        source = self.sources[self.events[key]["source_id"]]
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        windows = [(row["start_date"], row["end_date"]) for row in source["official_events"]]
        self.assertEqual(
            [
                ("2026-09-26", "2026-09-27"),
                ("2026-10-16", "2026-10-18"),
                ("2026-12-04", "2026-12-06"),
                ("2027-02-02", "2027-02-04"),
                ("2027-03-02", "2027-03-04"),
                ("2027-04-20", "2027-04-22"),
            ],
            windows,
        )

    def test_belgian_championship_playoffs_remain_a_documented_hold(self):
        key = "soccer-belgium-championship-playoffs-i-and-ii-men"
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
        self.assertTrue(self.events[key]["season_hold"])

    def test_dutch_feeds_and_completed_shield_keep_separate_scope(self):
        for key in (
            "soccer-netherlands-eredivisie-men",
            "soccer-netherlands-eerste-divisie-men",
            "soccer-netherlands-knvb-beker-dutch-cup-men",
        ):
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
        shield = "soccer-netherlands-johan-cruyff-shield-dutch-super-cup-men"
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[shield]["coverage_state"])

    def test_luxembourg_unresolved_cups_do_not_borrow_bgl_ligue(self):
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory["soccer-luxembourg-national-division-bgl-ligue-men"]["coverage_state"])
        for key in (
            "soccer-luxembourg-luxembourg-cup-men",
            "soccer-luxembourg-luxembourg-super-cup-men",
        ):
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
                self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])


if __name__ == "__main__":
    unittest.main()
