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

    def test_three_more_leagues_are_configured(self):
        expected = {
            "soccer-egypt-egyptian-premier-league-men":
                ("caf-soccer-egypt-egyptian-premier-league-men", "official-egypt-premier-scope"),
            "soccer-saudi-arabia-first-division-league-men":
                ("soccer-afc-saudi-arabia-first-division-league-men", "official-saudi-first-division-scope"),
            "soccer-new-zealand-new-zealand-national-league-men":
                ("ofc-soccer-new-zealand-national-league-men", "official-nz-national-league-fixtures"),
        }
        for key, (source_id, source_type) in expected.items():
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual(source_type, self.sources[source_id]["source_type"])
                self.assertEqual("partial", self.sources[source_id]["coverage_status"])

    def test_summary_moves_to_355(self):
        data = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        self.assertEqual(355, data["summary"]["coverage_states"]["ADAPTER_CONFIGURED"])
        self.assertEqual(177, data["summary"]["coverage_states"]["ADAPTER_GAP"])
        self.assertEqual(142, data["by_sport"]["Soccer"]["adapter_gaps"])


if __name__ == "__main__":
    unittest.main()
