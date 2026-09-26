"""England soccer sources must preserve competition and gender scope."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class EnglandSoccerScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season_map = json.loads((DATA / "catalog-season-map.json").read_text())
        cls.sources = {
            item["id"]: item
            for item in json.loads(
                (DATA / "soccer-uefa-domestic-sources.json").read_text()
            )["sources"]
            if item.get("region") == "England"
        }
        cls.inventory = {
            item["league"]: item
            for item in json.loads(
                (DATA / "priority2-coverage-inventory.json").read_text()
            )["identities"]
            if item["sport"] == "Soccer"
        }
        soccer = next(
            sport for sport in cls.season_map["sports"] if sport["sport"] == "Soccer"
        )
        cls.england = next(
            group for group in soccer["groups"] if group.get("country") == "England"
        )

    def test_players_cup_has_a_scoped_daily_adapter(self):
        source = self.sources["uefa-soccer-england-players-cup-women"]
        self.assertEqual("espn-daily", source["source_type"])
        self.assertTrue(source["endpoint"].endswith("/eng.w.league_cup/scoreboard"))
        self.assertEqual(["Players Cup | Women"], source["catalog_terms"])
        self.assertEqual(
            "https://www.wslfootball.com/fixtures/players-cup",
            source["official_schedule_url"],
        )

    def test_community_shield_is_an_exact_completed_window(self):
        source = self.sources["uefa-soccer-england-fa-community-shield-men"]
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual(
            [("2026-08-16", "2026-08-16")],
            [
                (event["start_date"], event["end_date"])
                for event in source["official_events"]
            ],
        )
        event = next(
            item
            for item in self.england["events"]
            if item["catalog_event"] == "FA Community Shield | Men"
        )
        self.assertEqual("2026-08-16", event["season_start_date"])
        self.assertEqual("2026-08-16", event["season_end_date"])
        self.assertEqual(
            "OFFICIAL_WINDOW_ONLY",
            self.inventory["FA Community Shield | Men"]["coverage_state"],
        )

    def test_england_has_no_pending_date_identity(self):
        england_source_ids = {*self.sources, "epl"}
        rows = [
            item
            for item in self.inventory.values()
            if any(source["id"] in england_source_ids for source in item["sources"])
        ]
        self.assertEqual(13, len(rows))
        self.assertFalse(
            [item["league"] for item in rows if item["season_state"] == "PENDING_DATES"]
        )
        self.assertEqual(
            "ADAPTER_CONFIGURED",
            self.inventory["Players Cup | Women"]["coverage_state"],
        )

    def test_wsl2_and_legacy_championship_label_do_not_share_an_adapter(self):
        current = self.sources["uefa-soccer-england-super-league-2-women"]
        legacy = self.sources["uefa-soccer-england-championship-women"]
        self.assertEqual("coverage-gap", current["source_type"])
        self.assertEqual("coverage-gap", legacy["source_type"])
        self.assertEqual(
            "https://www.wslfootball.com/fixtures/wsl2",
            current["official_schedule_url"],
        )
        self.assertEqual(current["official_schedule_url"], legacy["official_schedule_url"])
        self.assertIn("same current competition", legacy["source_note"])
        self.assertIn("must not create a second fixture stream", legacy["source_note"])

    def test_split_children_retain_independent_authority_pages(self):
        expected = {
            "uefa-soccer-england-championship-men": "https://www.efl.com/matches/",
            "uefa-soccer-england-championship-women": "https://www.wslfootball.com/fixtures/wsl2",
            "uefa-soccer-england-fa-cup-men": "https://www.thefa.com/competitions/thefacup/round-dates",
            "uefa-soccer-england-fa-cup-women": "https://www.thefa.com/competitions/the-womens-fa-cup/round-dates",
        }
        for source_id, url in expected.items():
            with self.subTest(source_id=source_id):
                self.assertEqual(url, self.sources[source_id]["official_schedule_url"])


if __name__ == "__main__":
    unittest.main()
