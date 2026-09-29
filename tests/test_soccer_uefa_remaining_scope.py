"""Israeli, Luxembourgish, and Maltese senior calendars retain edition scope."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
COUNTRIES = {"Israel", "Luxembourg", "Malta"}


class RemainingUefaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in COUNTRIES for e in g["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_ten_distinct_senior_sources(self):
        self.assertEqual(10, len(self.events))
        self.assertEqual(10, len({e["source_id"] for e in self.events.values()}))
        for e in self.events.values():
            self.assertNotIn("season_start", e)
            self.assertNotIn("season_end", e)

    def test_leagues_and_multi_match_cups_keep_open_ends(self):
        starts = {
            "soccer-israel-israeli-premier-league-ligat-ha-al-men": "August 22",
            "soccer-israel-israel-state-cup-men": "August 25",
            "soccer-israel-toto-cup-men": "July 25",
            "soccer-luxembourg-national-division-bgl-ligue-men": "August 2",
            "soccer-malta-maltese-premier-league-men": "August 14",
        }
        for key, date in starts.items():
            e = self.events[key]
            self.assertIn(date, e["season_window"])
            self.assertFalse(e["season_window_complete"])
            self.assertNotIn("season_end_date", e)
            self.assertEqual("PARTIAL_WINDOW", self.inventory[key]["season_state"])
            if key == "soccer-luxembourg-national-division-bgl-ligue-men":
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-flf-bgl-next-round", self.sources[e["source_id"]]["source_type"])
            elif key == "soccer-israel-israeli-premier-league-ligat-ha-al-men":
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("espn-daily", self.sources[e["source_id"]]["source_type"])
                self.assertTrue(self.sources[e["source_id"]]["endpoint"].endswith("isr.1/scoreboard"))
            elif key == "soccer-malta-maltese-premier-league-men":
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-malta-ticket-fixtures", self.sources[e["source_id"]]["source_type"])
            else:
                self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
        self.assertIn("separately scoped", self.events["soccer-israel-toto-cup-men"]["season_basis"])

    def test_unverified_editions_are_held_and_futsal_is_distinct(self):
        for key in ("soccer-luxembourg-luxembourg-cup-men", "soccer-luxembourg-luxembourg-super-cup-men", "soccer-malta-maltese-fa-trophy-men"):
            e = self.events[key]
            self.assertTrue(e["season_hold"])
            self.assertNotIn("season_start_date", e)
            self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
        self.assertIn("Futsal", self.events["soccer-luxembourg-luxembourg-super-cup-men"]["season_basis"])

    def test_two_completed_senior_super_cups_have_single_event_windows(self):
        for key, day in (("soccer-israel-israel-super-cup-men", "2026-07-16"), ("soccer-malta-maltese-super-cup-men", "2026-09-07")):
            e = self.events[key]
            source = self.sources[e["source_id"]]
            self.assertEqual((day, day), (e["season_start_date"], e["season_end_date"]))
            self.assertEqual("official-event-window", source["source_type"])
            self.assertEqual((day, day), (source["official_events"][0]["start_date"], source["official_events"][0]["end_date"]))
            self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[key]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
