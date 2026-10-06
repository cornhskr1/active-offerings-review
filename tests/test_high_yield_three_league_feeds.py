"""High-yield league conversion batch for Egypt, Saudi Arabia, and New Zealand."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class HighYieldThreeLeagueFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
        }
        cls.sources = {}
        for filename in (
            "soccer-caf-domestic-sources.json",
            "soccer-afc-domestic-sources.json",
            "soccer-ofc-domestic-sources.json",
        ):
            for source in json.loads((DATA / filename).read_text())["sources"]:
                cls.sources[source["id"]] = source

    def test_two_verified_team_schedules_are_configured(self):
        expected = {
            "soccer-egypt-egyptian-premier-league-men":
                ("caf-soccer-egypt-egyptian-premier-league-men", "official-egypt-premier-scope"),
            "soccer-saudi-arabia-first-division-league-men":
                ("soccer-afc-saudi-arabia-first-division-league-men", "official-saudi-first-division-scope"),
        }
        for key, (source_id, source_type) in expected.items():
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual(source_type, self.sources[source_id]["source_type"])
                self.assertEqual("partial", self.sources[source_id]["coverage_status"])

    def test_nz_remains_a_gap_until_draw_and_reserve_scope_are_verified(self):
        self.assertEqual("ADAPTER_GAP", self.inventory["soccer-new-zealand-new-zealand-national-league-men"]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
