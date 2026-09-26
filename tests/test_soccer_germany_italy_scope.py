"""German and Italian soccer dates and sources must retain division scope."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class GermanyItalySoccerScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(
            sport for sport in json.loads((DATA / "catalog-season-map.json").read_text())["sports"]
            if sport["sport"] == "Soccer"
        )
        cls.events = {}
        for group in soccer["groups"]:
            if group.get("country") not in {"Germany", "Italy"}:
                continue
            for event in group["events"]:
                for child in event.get("coverage_children", [event]):
                    cls.events[child["key"]] = child
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

    def test_german_womens_calendar_does_not_inherit_mens_adapter(self):
        expected = {
            "soccer-germany-frauen-bundesliga-women": ("2026-08-21", "2027-05-23"),
            "soccer-germany-dfb-pokal-frauen-women": ("2026-08-15", "2027-05-17"),
        }
        for key, dates in expected.items():
            with self.subTest(key=key):
                event = self.events[key]
                source = self.sources[event["source_id"]]
                self.assertEqual(dates, (event["season_start_date"], event["season_end_date"]))
                self.assertEqual("coverage-gap", source["source_type"])
                self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
                self.assertIn("dfb.de", source["official_schedule_url"])

    def test_german_supercup_is_the_completed_mens_event(self):
        key = "soccer-germany-dfl-supercup-men"
        event = self.events[key]
        source = self.sources[event["source_id"]]
        self.assertEqual(("2026-08-22", "2026-08-22"),
                         (event["season_start_date"], event["season_end_date"]))
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual("Franz Beckenbauer Supercup 2026", source["official_events"][0]["name"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])

    def test_italian_mens_and_womens_sources_are_separate(self):
        pairs = (
            ("soccer-italy-serie-a-men", "soccer-italy-serie-a-women"),
            ("soccer-italy-coppa-italia-men", "soccer-italy-coppa-italia-women"),
            ("soccer-italy-supercoppa-italiana-men", "soccer-italy-supercoppa-italiana-women"),
        )
        for men, women in pairs:
            with self.subTest(men=men):
                self.assertNotEqual(self.events[men]["source_id"], self.events[women]["source_id"])
                self.assertEqual("ADAPTER_GAP", self.inventory[women]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", self.inventory[pairs[2][0]]["coverage_state"])
        self.assertEqual("2026-08-08", self.events[pairs[1][0]]["season_start_date"])
        self.assertEqual("2027-05-19", self.events[pairs[1][0]]["season_end_date"])


if __name__ == "__main__":
    unittest.main()
