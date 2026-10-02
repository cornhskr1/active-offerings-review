import json
import unittest
from pathlib import Path

from scripts.build_catalog_change_queue import build_queue

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class CricketCatalog101MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((DATA / "catalog-live.json").read_text(encoding="utf-8"))
        cls.season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        cls.official = json.loads((DATA / "catalog-official-sources.json").read_text(encoding="utf-8"))
        cls.schedule = json.loads((DATA / "global-schedule-sources.json").read_text(encoding="utf-8"))

    def test_both_10_1_26_cricket_additions_are_explicitly_mapped(self):
        cricket = next(sport for sport in self.season["sports"] if sport["sport"] == "Cricket")
        self.assertEqual("9 approved competitions · 9 mapped", cricket["summary_label"])

        live_lines = next(section for section in self.catalog["sections"] if section["sport"] == "Cricket")["lines"]
        self.assertEqual(live_lines, cricket["catalog_snapshot_lines"])

        events = {
            event["catalog_event"]: event
            for group in cricket["groups"]
            for event in group.get("events", [])
        }
        odi = events["One Day International (ODI) | Men"]
        world_cup = events["ICC Men’s Cricket World Cup | Men"]

        self.assertTrue(odi["nonseasonal"])
        self.assertEqual("cricket-int-odi", odi["source_id"])
        self.assertNotIn("season_start", odi)
        self.assertNotIn("season_end", odi)
        self.assertNotIn("season_start_date", odi)
        self.assertNotIn("season_end_date", odi)

        self.assertEqual(("2027-10-02", "2027-11-21"),
                         (world_cup["season_start_date"], world_cup["season_end_date"]))
        self.assertEqual("cricket-int-world-cup", world_cup["source_id"])
        self.assertNotIn("season_start", world_cup)
        self.assertNotIn("season_end", world_cup)

    def test_official_icc_sources_are_recorded_without_inventing_schedule_coverage(self):
        events = {event["key"]: event for event in self.official["events"]}
        self.assertEqual("verified", events["cricket-int-odi"]["status"])
        self.assertEqual("International Cricket Council", events["cricket-int-odi"]["governing_body"])
        self.assertIn("fixtures-results", events["cricket-int-odi"]["official_url"])

        self.assertEqual("verified", events["cricket-int-world-cup"]["status"])
        self.assertEqual("International Cricket Council", events["cricket-int-world-cup"]["governing_body"])
        self.assertIn("cricket-world-cup-2027", events["cricket-int-world-cup"]["official_url"])

    def test_schedule_coverage_distinguishes_odi_gap_from_world_cup_window(self):
        sources = {source["id"]: source for source in self.schedule["sources"]}

        odi = sources["cricket-int-odi"]
        self.assertEqual("coverage-gap", odi["source_type"])
        self.assertEqual("missing", odi["coverage_status"])
        self.assertIn("fixtures-results", odi["official_schedule_url"])
        self.assertNotIn("official_events", odi)

        world_cup = sources["cricket-int-world-cup"]
        self.assertEqual("official-event-window", world_cup["source_type"])
        self.assertEqual("published-event-window", world_cup["coverage_status"])
        self.assertEqual("published-window", world_cup["endpoint_validation"])
        self.assertEqual([("2027-10-02", "2027-11-21")], [
            (event["start_date"], event["end_date"]) for event in world_cup["official_events"]
        ])

    def test_current_catalog_change_queue_rebuilds_to_zero(self):
        result = build_queue(self.catalog, self.season, self.official, self.schedule)
        self.assertEqual(0, result["summary"]["open_total"])
        self.assertEqual(0, result["summary"]["catalog_additions"])
        self.assertEqual([], result["open_items"])


if __name__ == "__main__":
    unittest.main()
