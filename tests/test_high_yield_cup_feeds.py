"""High-yield cup conversion batch for Japan, Ireland, and Switzerland."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class HighYieldCupFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
        }
        cls.sources = {}
        for filename in ("soccer-uefa-domestic-sources.json", "soccer-afc-domestic-sources.json"):
            for source in json.loads((DATA / filename).read_text())["sources"]:
                cls.sources[source["id"]] = source

    def test_three_cup_gaps_are_now_configured(self):
        expected = {
            "soccer-japan-emperor-s-cup-men": "soccer-afc-japan-emperors-cup-men",
            "soccer-ireland-fai-cup-men": "uefa-soccer-ireland-fai-cup-men",
            "soccer-switzerland-swiss-cup-men": "uefa-soccer-switzerland-swiss-cup-men",
        }
        for key, source_id in expected.items():
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-high-yield-cup-fixtures", self.sources[source_id]["source_type"])
                self.assertEqual("partial", self.sources[source_id]["coverage_status"])

    def test_summary_moves_to_349(self):
        data = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        self.assertGreaterEqual(data["summary"]["coverage_states"]["ADAPTER_CONFIGURED"], 349)
        self.assertLessEqual(data["summary"]["coverage_states"]["ADAPTER_GAP"], 183)
        self.assertLessEqual(data["by_sport"]["Soccer"]["adapter_gaps"], 148)


if __name__ == "__main__":
    unittest.main()
