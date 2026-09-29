"""France and Portugal soccer sources retain country and competition scope."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class FrancePortugalSoccerScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(
            sport
            for sport in json.loads((DATA / "catalog-season-map.json").read_text())["sports"]
            if sport["sport"] == "Soccer"
        )
        cls.events = {
            event["key"]: event
            for group in soccer["groups"]
            if group.get("country") in {"France", "Portugal"}
            for event in group["events"]
        }
        cls.sources = {
            item["id"]: item
            for item in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]
            if item.get("region") in {"France", "Portugal"}
        }
        cls.inventory = {
            item["identity_key"]: item
            for item in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
            if item["sport"] == "Soccer"
        }

    def test_completed_super_cups_have_separate_official_windows(self):
        dates = {
            "soccer-france-troph-e-des-champions-men": "2026-08-16",
            "soccer-portugal-superta-a-c-ndido-de-oliveira-men": "2026-08-01",
            "soccer-portugal-superta-a-feminina-women": "2026-09-06",
        }
        for key, date in dates.items():
            with self.subTest(key=key):
                event = self.events[key]
                source = self.sources[event["source_id"]]
                self.assertEqual((date, date), (event["season_start_date"], event["season_end_date"]))
                self.assertEqual("official-event-window", source["source_type"])
                self.assertEqual(date, source["official_events"][0]["start_date"])
                self.assertEqual(date, source["official_events"][0]["end_date"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])

    def test_french_womens_divisions_and_cup_do_not_share_a_fixture_adapter(self):
        expected = {
            "soccer-france-premi-re-ligue-women": ("2026-09-05", "2027-06-05", "ADAPTER_CONFIGURED", "16277"),
            "soccer-france-seconde-ligue-women": ("2026-09-06", "2027-05-09", "ADAPTER_GAP", "17085"),
            "soccer-france-coup-lffp-women": ("2026-08-22", "2027-04-10", "ADAPTER_GAP", "17085"),
        }
        for key, (start, end, coverage, notice) in expected.items():
            with self.subTest(key=key):
                event = self.events[key]
                source = self.sources[event["source_id"]]
                self.assertEqual((start, end), (event["season_start_date"], event["season_end_date"]))
                self.assertEqual(coverage, self.inventory[key]["coverage_state"])
                self.assertIn(f"fff.fr/article/{notice}", source["official_schedule_url"])

    def test_portuguese_professional_competitions_stay_distinct(self):
        league = self.events["soccer-portugal-liga-portugal-2-men"]
        cup = self.events["soccer-portugal-ta-a-da-liga-men"]
        self.assertEqual("2026-08-09", league["season_start_date"])
        self.assertEqual("2027-05-16", league["season_end_date"])
        self.assertEqual("2026-10-27", cup["season_start_date"])
        self.assertEqual("2027-01-09", cup["season_end_date"])
        self.assertNotEqual(league["source_id"], cup["source_id"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[league["key"]]["coverage_state"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[cup["key"]]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
