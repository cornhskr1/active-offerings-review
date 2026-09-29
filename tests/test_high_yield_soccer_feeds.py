"""High-yield configured-feed batch stays scoped to four approved league identities."""

import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


class HighYieldSoccerFeedsTests(unittest.TestCase):
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

    def test_four_gap_identities_are_now_configured(self):
        expected = {
            "soccer-finland-veikkausliiga-men": ("uefa-soccer-finland-veikkausliiga-men", "espn-daily"),
            "soccer-israel-israeli-premier-league-ligat-ha-al-men": (
                "uefa-soccer-israel-israeli-premier-league-ligat-ha-al-men", "espn-daily"
            ),
            "soccer-korea-k-league-1-men": ("soccer-afc-korea-k-league-1-men", "official-kleague-next-fixture"),
            "soccer-korea-k-league-2-men": ("soccer-afc-korea-k-league-2-men", "official-kleague-next-fixture"),
        }
        for key, (source_id, source_type) in expected.items():
            with self.subTest(key=key):
                row = self.inventory[key]
                self.assertEqual("ADAPTER_CONFIGURED", row["coverage_state"])
                self.assertEqual(source_id, row["sources"][0]["id"])
                self.assertEqual(source_type, self.sources[source_id]["source_type"])

    def test_daily_feeds_fail_closed_on_review_window_fetch_errors(self):
        for source_id, slug in (
            ("uefa-soccer-finland-veikkausliiga-men", "fin.1"),
            ("uefa-soccer-israel-israeli-premier-league-ligat-ha-al-men", "isr.1"),
        ):
            with self.subTest(source_id=source_id):
                source = self.sources[source_id]
                self.assertTrue(source["endpoint"].endswith(f"{slug}/scoreboard"))
                self.assertTrue(source["espn_require_all_days"])
                self.assertEqual("partial", source["coverage_status"])

    def test_priority2_summary_moves_by_exactly_four(self):
        data = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        self.assertEqual(343, data["summary"]["coverage_states"]["ADAPTER_CONFIGURED"])
        self.assertEqual(189, data["summary"]["coverage_states"]["ADAPTER_GAP"])
        self.assertEqual(154, data["by_sport"]["Soccer"]["adapter_gaps"])


if __name__ == "__main__":
    unittest.main()
