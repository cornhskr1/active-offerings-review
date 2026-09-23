import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class DivisionScheduleEvidenceTests(unittest.TestCase):
    def test_official_windows_keep_divisions_and_fixture_coverage_separate(self):
        season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        sources = {row["id"]: row for row in json.loads(
            (DATA / "global-schedule-sources.json").read_text(encoding="utf-8")
        )["sources"]}
        expected = {
            "basketball-fiba-world-cup-men": ("2027-08-27", "2027-09-12", "Basketball"),
            "basketball-fiba-world-cup-women": ("2026-09-04", "2026-09-13", "Basketball"),
            "basketball-fiba-3x3-world-cup-men": ("2026-06-01", "2026-06-07", "Basketball"),
            "basketball-fiba-3x3-world-cup-women": ("2026-06-01", "2026-06-07", "Basketball"),
            "soccer-italy-serie-a-women": ("2026-09-26", "2027-05-16", "Soccer"),
            "soccer-italy-coppa-italia-women": ("2026-08-29", "2027-05-23", "Soccer"),
            "soccer-italy-supercoppa-italiana-women": ("2027-01-09", "2027-01-10", "Soccer"),
        }
        children = {child["key"]: child for sport in season["sports"]
                    for group in sport.get("groups", [])
                    for event in group.get("events", [])
                    for child in event.get("coverage_children", [])}
        for key, (start, end, sport) in expected.items():
            with self.subTest(key=key):
                child = children[key]
                self.assertEqual((start, end),
                                 (child["season_start_date"], child["season_end_date"]))
                source = sources[child["source_id"]]
                self.assertEqual((sport, child["label"]), (source["sport"], source["league"]))
                self.assertEqual("coverage-gap", source["source_type"])
                self.assertEqual("missing", source["coverage_status"])
                self.assertTrue(source["official_schedule_url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
