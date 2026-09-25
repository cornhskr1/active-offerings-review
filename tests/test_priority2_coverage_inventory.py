"""The Priority 2 inventory keeps legal identities and schedule evidence separate."""

import json
import unittest
from pathlib import Path

from sys import path as sys_path


ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402


class Priority2CoverageInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = build()
        cls.rows = {(row["sport"], row["league"]): row for row in cls.inventory["identities"]}

    def test_split_parent_does_not_become_a_schedule_identity(self):
        self.assertNotIn(("NCAA Water Polo", "Division I Water Polo | Men and Women"), self.rows)
        for division in ("Men", "Women"):
            row = self.rows[("NCAA Water Polo", f"Division I Water Polo | {division}")]
            self.assertEqual("split-child", row["kind"])
            self.assertEqual("NO_LINKED_SOURCE", row["coverage_state"])
            self.assertEqual("PENDING_DATES", row["season_state"])
            self.assertEqual([], row["sources"])

    def test_official_window_and_gap_do_not_pretend_to_be_fixture_adapters(self):
        row = self.rows[("Basketball", "FIBA Basketball World Cup | Men")]
        self.assertEqual("ADAPTER_GAP", row["coverage_state"])
        self.assertEqual("PARTIAL_WINDOW", row["season_state"])
        self.assertEqual("coverage-gap", row["sources"][0]["type"])
        afl = self.rows[("Aussie Rules", "Australian Football League (AFL)")]
        self.assertEqual("ADAPTER_CONFIGURED", afl["coverage_state"])

    def test_chile_league_and_cup_keep_distinct_schedule_gaps(self):
        expected = {
            "Liga Nacional de Basquetbol de Chile (LNB) | Men": "chile-lnb",
            "Copa Chile | Men": "chile-copa",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("ADAPTER_GAP", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])

    def test_unconfigured_reference_and_schedule_only_names_remain_visible(self):
        cycling = self.rows[("Cycling", "Cadel Evans Great Ocean Road Race")]
        self.assertEqual("SOURCE_SCOPE_REVIEW", cycling["coverage_state"])
        self.assertEqual(
            [{"sport": "Football", "league": "NCAA Football"}, {"sport": "Volleyball", "league": "NCAA Volleyball"}],
            self.inventory["summary"]["schedule_only_not_independent_approvals"],
        )
        self.assertEqual(len(self.rows), self.inventory["summary"]["catalog_operational_identities"])


if __name__ == "__main__":
    unittest.main()
