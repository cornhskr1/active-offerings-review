"""AFC catalog order: Australia child divisions and Bangladesh competition holds."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class AustraliaBangladeshScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.groups = {g["country"]: g for g in soccer["groups"] if g.get("country") in {"Australia", "Bangladesh"}}
        cls.children = {c["key"]: c for e in cls.groups["Australia"]["events"] for c in e["coverage_children"]}
        cls.bangladesh = {e["key"]: e for e in cls.groups["Bangladesh"]["events"]}
        cls.sources = {s["id"]: s for s in json.loads((DATA / "soccer-afc-domestic-sources.json").read_text())["sources"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_eight_exact_children_and_events(self):
        self.assertEqual(4, len(self.children))
        self.assertEqual(4, len(self.bangladesh))
        events = [*self.children.values(), *self.bangladesh.values()]
        self.assertEqual(8, len({e["source_id"] for e in events}))
        for e in events:
            self.assertNotIn("season_start", e)
            self.assertNotIn("season_end", e)

    def test_separate_aleague_dates_and_configured_adapters(self):
        pairs = {
            "soccer-australia-a-league-men": ("2026-10-16", "2027-06-06", "aus.1/scoreboard"),
            "soccer-australia-a-league-women": ("2026-10-18", "2027-05-16", "aus.w.1/scoreboard"),
        }
        for key, (start, end, endpoint) in pairs.items():
            child = self.children[key]
            source = self.sources[child["source_id"]]
            self.assertEqual((start, end), (child["season_start_date"], child["season_end_date"]))
            self.assertTrue(source["endpoint"].endswith(endpoint))
            self.assertEqual("espn-daily", source["source_type"])
            self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])

    def test_cups_do_not_inherit_each_others_calendar(self):
        men = self.children["soccer-australia-australia-cup-men"]
        women = self.children["soccer-australia-australia-cup-women"]
        self.assertFalse(men["season_window_complete"])
        self.assertEqual("2026-10-10", men["season_end_date"])
        self.assertEqual("PARTIAL_WINDOW", self.inventory[men["key"]]["season_state"])
        self.assertTrue(women["season_hold"])
        self.assertNotIn("season_end_date", women)
        self.assertEqual("DOCUMENTED_HOLD", self.inventory[women["key"]]["season_state"])

    def test_bangladesh_2026_27_plans_do_not_create_dates(self):
        for key, event in self.bangladesh.items():
            self.assertTrue(event["season_hold"])
            self.assertNotIn("season_start_date", event)
            self.assertEqual("DOCUMENTED_HOLD", self.inventory[key]["season_state"])
            self.assertEqual("ADAPTER_GAP", self.inventory[key]["coverage_state"])
        self.assertIn("Bangladesh Football League", self.bangladesh["soccer-bangladesh-bangladesh-premier-league-men"]["season_basis"])


if __name__ == "__main__":
    unittest.main()
