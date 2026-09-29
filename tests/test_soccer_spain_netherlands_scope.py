"""Country and gender boundaries for the Spanish and Dutch soccer calendar batch."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class SpainNetherlandsScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(
            sport for sport in json.loads((DATA / "catalog-season-map.json").read_text())["sports"]
            if sport["sport"] == "Soccer"
        )
        cls.events = {
            event["key"]: event
            for group in soccer["groups"] if group.get("country") in {"Spain", "Netherlands"}
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

    def test_twelve_distinct_country_identities_have_dated_bounds(self):
        expected = {
            "soccer-spain-copa-del-rey-men": ("2026-09-26", "2027-04-24"),
            "soccer-spain-supercopa-de-espa-a-men": ("2027-02-02", "2027-02-06"),
            "soccer-spain-primera-federaci-n-femenina-women": ("2026-09-12", "2027-06-06"),
            "soccer-spain-copa-de-la-reina-women": ("2026-09-09", "2027-05-15"),
            "soccer-spain-supercopa-de-espa-a-femenina-women": ("2027-01-19", "2027-01-24"),
            "soccer-spain-laliga-men": ("2026-08-15", "2027-05-30"),
            "soccer-spain-segunda-divisi-n-men": ("2026-08-14", "2027-06-20"),
            "soccer-spain-liga-f-women": ("2026-08-29", "2027-05-23"),
            "soccer-netherlands-eredivisie-men": ("2026-08-07", "2027-05-23"),
            "soccer-netherlands-eerste-divisie-men": ("2026-08-07", "2027-05-14"),
            "soccer-netherlands-knvb-beker-dutch-cup-men": ("2026-09-01", "2027-04-18"),
            "soccer-netherlands-johan-cruyff-shield-dutch-super-cup-men": ("2026-08-02", "2026-08-02"),
        }
        self.assertEqual(set(expected), set(self.events))
        for key, dates in expected.items():
            with self.subTest(key=key):
                event = self.events[key]
                self.assertEqual(dates, (event["season_start_date"], event["season_end_date"]))
                self.assertEqual("DATED_WINDOW", self.inventory[key]["season_state"])
                self.assertIn(event["source_id"], self.sources)

    def test_supercups_and_womens_second_tier_keep_separate_scope(self):
        men = "soccer-spain-supercopa-de-espa-a-men"
        women = "soccer-spain-supercopa-de-espa-a-femenina-women"
        primera = "soccer-spain-primera-federaci-n-femenina-women"

        self.assertEqual("official-rfef-supercopa-2027", self.sources[self.events[men]["source_id"]]["source_type"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[men]["coverage_state"])

        self.assertEqual("official-event-window", self.sources[self.events[women]["source_id"]]["source_type"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[women]["coverage_state"])

        self.assertEqual("official-event-window", self.sources[self.events[primera]["source_id"]]["source_type"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[primera]["coverage_state"])

        self.assertNotEqual(self.events[men]["source_id"], self.events[women]["source_id"])

    def test_dutch_shield_is_completed_window_only(self):
        key = "soccer-netherlands-johan-cruyff-shield-dutch-super-cup-men"
        source = self.sources[self.events[key]["source_id"]]
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual(("2026-08-02", "2026-08-02"),
                         (source["official_events"][0]["start_date"], source["official_events"][0]["end_date"]))


if __name__ == "__main__":
    unittest.main()
