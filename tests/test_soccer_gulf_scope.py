"""Gulf senior soccer editions keep separate calendars and adapter states."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"Saudi Arabia", "Qatar", "United Arab Emirates"}


class GulfScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in COUNTRIES for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_distinct_senior_sources_have_no_synthetic_recurring_dates(self):
        self.assertEqual(10, len(self.events))
        self.assertEqual(10, len({e["source_id"] for e in self.events.values()}))
        for e in self.events.values():
            self.assertNotIn("season_start", e)
            self.assertNotIn("season_end", e)
            self.assertTrue(self.sources[e["source_id"]]["official_schedule_url"].startswith("https://"))

    def test_confirmed_full_windows_and_rescheduled_qatar_edition(self):
        windows = {
            "soccer-saudi-arabia-saudi-pro-league-men": ("2026-08-13", "2027-05-29"),
            "soccer-saudi-arabia-saudi-super-cup-men": ("2026-12-19", "2026-12-23"),
            "soccer-qatar-qatar-cup-men": ("2026-09-01", "2026-12-11"),
        }
        for key, dates in windows.items():
            e = self.events[key]
            self.assertEqual(dates, (e["season_start_date"], e["season_end_date"]))
            self.assertEqual("DATED_WINDOW", self.inventory[key]["season_state"])
        self.assertIn("rescheduled edition originally announced for 2025–26", self.events["soccer-qatar-qatar-cup-men"]["season_basis"])
        self.assertEqual("ADAPTER_GAP", self.inventory["soccer-qatar-qatar-cup-men"]["coverage_state"])
        cup = self.sources[self.events["soccer-qatar-qatar-cup-men"]["source_id"]]
        self.assertEqual("https://www.qsl.qa/en/qatar-cup-fixtures-results", cup["official_schedule_url"])
        self.assertIn("TBD for kickoff", cup["source_note"])
        self.assertIn("Al Sadd and Al Rayyan", self.events["soccer-qatar-qatar-cup-men"]["season_basis"])
        self.assertFalse(any("QSL 2" in e["catalog_event"] for e in self.events.values()))

    def test_partial_boundaries_and_uae_super_cup_hold(self):
        partial = set(self.events) - {
            "soccer-saudi-arabia-saudi-pro-league-men",
            "soccer-saudi-arabia-saudi-super-cup-men",
            "soccer-qatar-qatar-cup-men",
            "soccer-united-arab-emirates-uae-super-cup-men",
        }
        self.assertEqual(6, len(partial))
        for key in partial:
            e = self.events[key]
            self.assertFalse(e["season_window_complete"])
            self.assertNotIn("season_end_date", e)
            self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        key = "soccer-united-arab-emirates-uae-super-cup-men"
        self.assertTrue(self.events[key]["season_hold"])
        self.assertNotIn("season_start_date", self.events[key])
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertIn("UAE–Qatar", self.events[key]["season_basis"])

    def test_configured_saudi_espn_endpoints_are_preserved(self):
        for key, suffix in (
            ("soccer-saudi-arabia-saudi-pro-league-men", "ksa.1/scoreboard"),
            ("soccer-saudi-arabia-king-cup-men", "ksa.kings.cup/scoreboard"),
        ):
            source = self.sources[self.events[key]["source_id"]]
            self.assertEqual("espn-daily", source["source_type"])
            self.assertEqual("complete", source["coverage_status"])
            self.assertTrue(source["endpoint"].endswith(suffix))
            self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
        qsl_source = self.sources[self.events["soccer-qatar-qsl-cup-men"]["source_id"]]
        self.assertEqual("official-qsl-cup-fixtures", qsl_source["source_type"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory["soccer-qatar-qsl-cup-men"]["coverage_state"])
        league_source = self.sources[self.events["soccer-qatar-qatar-stars-league-men"]["source_id"]]
        self.assertEqual("official-qsl-stars-fixtures", league_source["source_type"])
        self.assertEqual("partial", league_source["coverage_status"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory["soccer-qatar-qatar-stars-league-men"]["coverage_state"])
        first_div = "soccer-saudi-arabia-first-division-league-men"
        self.assertEqual("official-saudi-first-division-scope", self.sources[self.events[first_div]["source_id"]]["source_type"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[first_div]["coverage_state"])
        uae = "soccer-united-arab-emirates-uae-pro-league-men"
        self.assertEqual("official-high-yield-soccer-fixtures", self.sources[self.events[uae]["source_id"]]["source_type"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[uae]["coverage_state"])
        for key in set(self.events) - {
            "soccer-saudi-arabia-saudi-pro-league-men", "soccer-saudi-arabia-king-cup-men",
            "soccer-qatar-qsl-cup-men", "soccer-qatar-qatar-stars-league-men", first_div, uae,
        }:
            self.assertEqual("coverage-gap", self.sources[self.events[key]["source_id"]]["source_type"])


if __name__ == "__main__":
    unittest.main()
