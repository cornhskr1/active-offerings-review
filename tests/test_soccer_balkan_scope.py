"""Balkan federation-family scope for Bosnia and Herzegovina, Montenegro, Kosovo, and Serbia."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"Bosnia and Herzegovina", "Montenegro", "Kosovo", "Serbia"}


class BalkanScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(
            sport for sport in json.loads((DATA / "catalog-season-map.json").read_text())["sports"]
            if sport["sport"] == "Soccer"
        )
        cls.events = {
            event["key"]: event
            for group in soccer["groups"] if group.get("country") in COUNTRIES
            for event in group["events"]
        }
        cls.sources = {
            source["id"]: source
            for source in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]
        }
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
            if row["sport"] == "Soccer"
        }

    def test_family_contains_eleven_distinct_approved_identities(self):
        self.assertEqual(11, len(self.events))
        self.assertEqual(11, len({event["source_id"] for event in self.events.values()}))

    def test_montenegro_top_flight_has_scoped_exact_round_adapter(self):
        key = "soccer-montenegro-montenegrin-first-league-men"
        source = self.sources[self.events[key]["source_id"]]
        self.assertEqual("official-fscg-cfl-round", source["source_type"])
        self.assertEqual("partial", source["coverage_status"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        self.assertFalse(self.events[key]["season_window_complete"])

    def test_serbian_league_keeps_untimed_future_rounds_as_windows_only(self):
        key = "soccer-serbia-serbian-superliga-men"
        source = self.sources[self.events[key]["source_id"]]
        self.assertEqual("official-event-window", source["source_type"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
        self.assertEqual(
            [("2026-10-10", "2026-10-10"), ("2026-10-17", "2026-10-17")],
            [(event["start_date"], event["end_date"]) for event in source["official_events"]],
        )

    def test_bosnia_top_flight_has_dynamic_official_adapter(self):
        key = "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men"
        source = self.sources[self.events[key]["source_id"]]
        self.assertEqual("official-bih-wwin-fixtures", source["source_type"])
        self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])

    def test_bosnia_supercup_stays_held_after_newer_postponement(self):
        key = "soccer-bosnia-and-herzegovina-bosnian-super-cup-men"
        event = self.events[key]
        self.assertTrue(event["season_hold"])
        self.assertIn("postponed", event["hold_reason"].lower())
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])

    def test_other_unverified_balkan_competitions_remain_fail_closed(self):
        changed = {
            "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men",
            "soccer-montenegro-montenegrin-first-league-men",
            "soccer-serbia-serbian-superliga-men",
        }
        for key, event in self.events.items():
            if key in changed:
                continue
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
                source = self.sources[event["source_id"]]
                self.assertEqual("coverage-gap", source["source_type"])

    def test_league_openings_do_not_fabricate_final_rounds(self):
        for key in (
            "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men",
            "soccer-montenegro-montenegrin-first-league-men",
            "soccer-kosovo-superleague-of-kosovo-superliga-e-kosov-s-men",
            "soccer-serbia-serbian-superliga-men",
        ):
            with self.subTest(key=key):
                self.assertFalse(self.events[key]["season_window_complete"])
                self.assertNotIn("season_end_date", self.events[key])


if __name__ == "__main__":
    unittest.main()
