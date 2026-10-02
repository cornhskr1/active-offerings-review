from pathlib import Path
import json
import unittest

from scripts.build_catalog_change_queue import build_queue


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class CricketCatalogAdditionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((DATA / "catalog-live.json").read_text(encoding="utf-8"))
        cls.season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        cls.official = json.loads((DATA / "catalog-official-sources.json").read_text(encoding="utf-8"))
        cls.schedule = json.loads((DATA / "global-schedule-sources.json").read_text(encoding="utf-8"))
        cls.cricket = next(sport for sport in cls.season["sports"] if sport["sport"] == "Cricket")
        cls.icc_group = next(
            group for group in cls.cricket["groups"]
            if group["governing_body"] == "International Cricket Council"
        )
        cls.events = {event["key"]: event for event in cls.icc_group["events"]}
        cls.official_events = {event["key"]: event for event in cls.official["events"]}
        cls.schedule_sources = {source["id"]: source for source in cls.schedule["sources"]}

    def test_cricket_snapshot_matches_10_1_26_catalog(self):
        section = next(section for section in self.catalog["sections"] if section["sport"] == "Cricket")
        self.assertEqual(section["lines"], self.cricket["catalog_snapshot_lines"])
        self.assertEqual("9 approved competitions · 9 mapped", self.cricket["summary_label"])
        self.assertEqual("complete", self.cricket["mapping_status"])

    def test_odi_is_mapped_as_nonseasonal_format_without_invented_dates(self):
        event = self.events["cricket-int-odi"]
        self.assertEqual("One Day International (ODI) | Men", event["catalog_event"])
        self.assertTrue(event["nonseasonal"])
        self.assertEqual("cricket-int-odi", event["source_id"])
        self.assertNotIn("season_start", event)
        self.assertNotIn("season_end", event)
        self.assertNotIn("season_start_date", event)
        self.assertNotIn("season_end_date", event)
        self.assertIn("no single annual season", event["season_window"])

        source = self.schedule_sources["cricket-int-odi"]
        self.assertEqual("coverage-gap", source["source_type"])
        self.assertEqual("missing", source["coverage_status"])
        self.assertEqual(["One Day International (ODI) | Men"], source["catalog_terms"])
        self.assertIn("icc-cricket.com/fixtures-results", source["official_schedule_url"])

        official = self.official_events["cricket-int-odi"]
        self.assertEqual("verified", official["status"])
        self.assertEqual("official-competition-source", official["basis"])

    def test_mens_cricket_world_cup_uses_exact_published_2027_window(self):
        event = self.events["cricket-int-world-cup"]
        self.assertEqual("ICC Men’s Cricket World Cup | Men", event["catalog_event"])
        self.assertEqual("2027-10-02", event["season_start_date"])
        self.assertEqual("2027-11-21", event["season_end_date"])
        self.assertEqual("cricket-int-world-cup", event["source_id"])
        self.assertNotIn("season_start", event)
        self.assertNotIn("season_end", event)

        source = self.schedule_sources["cricket-int-world-cup"]
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual("published-window", source["endpoint_validation"])
        self.assertEqual("published-event-window", source["coverage_status"])
        self.assertEqual(["ICC Men’s Cricket World Cup | Men"], source["catalog_terms"])
        self.assertEqual(1, len(source["official_events"]))
        window = source["official_events"][0]
        self.assertEqual(("2027-10-02", "2027-11-21"), (window["start_date"], window["end_date"]))
        self.assertEqual("South Africa / Zimbabwe / Namibia", window["location"])

        official = self.official_events["cricket-int-world-cup"]
        self.assertEqual("verified", official["status"])
        self.assertIn("icc-cricket-world-cup-2027", official["official_url"])

    def test_completed_mapping_clears_current_catalog_change_queue(self):
        result = build_queue(self.catalog, self.season, self.official, self.schedule)
        self.assertEqual(0, result["summary"]["open_total"], result["open_items"])
        self.assertEqual(0, result["summary"]["catalog_additions"])
        self.assertEqual(0, result["summary"]["blocked_from_review_today"])
        self.assertEqual([], result["open_items"])


if __name__ == "__main__":
    unittest.main()
