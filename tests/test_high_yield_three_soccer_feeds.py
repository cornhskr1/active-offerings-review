"""Three-source high-yield soccer conversion batch."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class HighYieldThreeFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
        }
        cls.sources = {}
        for filename in (
            "soccer-uefa-domestic-sources.json",
            "soccer-concacaf-domestic-sources.json",
            "soccer-afc-domestic-sources.json",
        ):
            for source in json.loads((DATA / filename).read_text())["sources"]:
                cls.sources[source["id"]] = source

    def test_three_more_gaps_are_configured(self):
        expected = {
            "soccer-austria-2-liga-men": "uefa-soccer-austria-2-liga-men",
            "soccer-canada-canadian-premier-league-men": "concacaf-soccer-canada-canadian-premier-league-men",
            "soccer-united-arab-emirates-uae-pro-league-men": "soccer-afc-united-arab-emirates-uae-pro-league-men",
        }
        for key, source_id in expected.items():
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual("official-uae-adnoc-fixtures" if source_id=="soccer-afc-united-arab-emirates-uae-pro-league-men" else "official-high-yield-soccer-fixtures", self.sources[source_id]["source_type"])
                self.assertEqual("partial", self.sources[source_id]["coverage_status"])

    def test_summary_moves_to_346(self):
        data = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        self.assertGreaterEqual(data["summary"]["coverage_states"]["ADAPTER_CONFIGURED"], 346)
        self.assertLessEqual(data["summary"]["coverage_states"]["ADAPTER_GAP"], 186)
        self.assertLessEqual(data["by_sport"]["Soccer"]["adapter_gaps"], 151)


if __name__ == "__main__":
    unittest.main()
