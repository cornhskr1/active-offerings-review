"""Regression guard for the five-identity basketball publisher conversion batch."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class BasketballPublisherBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        cls.rows = {row["identity_key"]: row for row in cls.inventory["identities"]}
        cls.sources = {
            source["id"]: source
            for source in json.loads((DATA / "global-schedule-sources.json").read_text())["sources"]
        }

    def test_five_basketball_identities_remain_configured(self):
        expected = {
            "basketball-fiba-3x3-world-cup-men",
            "basketball-fiba-3x3-world-cup-women",
            "basketball-fiba-world-cup-men",
            "basketball-fiba-world-cup-women",
            "basketball-cl-lnb",
        }
        for key in expected:
            with self.subTest(key=key):
                self.assertEqual("ADAPTER_CONFIGURED", self.rows[key]["coverage_state"])
                sid = self.rows[key]["sources"][0]["id"]
                self.assertEqual("official-publisher-basketball-fixtures", self.sources[sid]["source_type"])
                self.assertEqual("partial", self.sources[sid]["coverage_status"])

    def test_copa_chile_stays_visible_as_a_real_gap(self):
        copa = self.rows["basketball-cl-copa"]
        self.assertEqual("ADAPTER_GAP", copa["coverage_state"])
        self.assertEqual("coverage-gap", self.sources["chile-copa"]["source_type"])

    def test_batch_improvement_is_cumulative_not_exact(self):
        states = self.inventory["summary"]["coverage_states"]
        self.assertGreaterEqual(states["ADAPTER_CONFIGURED"], 357)
        self.assertLessEqual(states["ADAPTER_GAP"], 175)
        self.assertLessEqual(self.inventory["by_sport"]["Basketball"]["adapter_gaps"], 1)


if __name__ == "__main__":
    unittest.main()
