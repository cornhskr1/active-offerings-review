"""Dynamic league conversion batch for Azerbaijan, Bosnia-Herzegovina, and Malta."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class DynamicLeagueFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = {
            row["identity_key"]: row
            for row in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]
        }
        cls.sources = {
            source["id"]: source
            for source in json.loads((DATA / "soccer-uefa-domestic-sources.json").read_text())["sources"]
        }

    def test_three_more_leagues_are_configured(self):
        expected = {
            "soccer-azerbaijan-azerbaijan-premier-league-apl-men":
                ("uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men", "official-affa-latest-round"),
            "soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men":
                ("uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men", "official-bih-wwin-fixtures"),
            "soccer-malta-maltese-premier-league-men":
                ("uefa-soccer-malta-maltese-premier-league-men", "official-malta-ticket-fixtures"),
        }
        for key, (source_id, source_type) in expected.items():
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.inventory[key]["coverage_state"])
                self.assertEqual(source_type, self.sources[source_id]["source_type"])
                self.assertEqual("partial", self.sources[source_id]["coverage_status"])

    def test_summary_moves_to_352(self):
        data = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        self.assertEqual(352, data["summary"]["coverage_states"]["ADAPTER_CONFIGURED"])
        self.assertEqual(180, data["summary"]["coverage_states"]["ADAPTER_GAP"])
        self.assertEqual(145, data["by_sport"]["Soccer"]["adapter_gaps"])


if __name__ == "__main__":
    unittest.main()
