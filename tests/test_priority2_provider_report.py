"""Provider batches include only unresolved, exact catalog identities."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_priority2_exceptions import provider_cohorts, source_config  # noqa: E402
from audit_priority2_coverage import build  # noqa: E402


class ProviderCohortTests(unittest.TestCase):
    def test_nz_rugby_shared_cohort_dissolves_after_second_adapter(self):
        groups = provider_cohorts(build(), source_config())
        self.assertFalse(any(group["provider"] == "provincial.rugby" for group in groups))
        rows = {row["identity_key"]: row for row in build()["identities"]}
        self.assertEqual("ADAPTER_GAP", rows["rugby-nz-heartland"]["coverage_state"])
        self.assertEqual("ADAPTER_CONFIGURED", rows["rugby-nz-farah-palmer"]["coverage_state"])

    def test_configured_and_window_only_rows_cannot_enter_gap_report(self):
        rows = [
            {"sport": "Golf", "identity_key": "golf-event", "league": "Event",
             "coverage_state": "OFFICIAL_WINDOW_ONLY", "sources": [{"id": "x", "type": "official-event-window"}]},
            {"sport": "Rugby", "identity_key": "rugby-ready", "league": "Ready",
             "coverage_state": "ADAPTER_CONFIGURED", "sources": [{"id": "x", "type": "adapter"}]},
            {"sport": "Rugby", "identity_key": "rugby-gap", "league": "Gap",
             "coverage_state": "ADAPTER_GAP", "sources": [{"id": "x", "type": "coverage-gap"}]},
        ]
        configured = {("Rugby", "x"): {"official_schedule_url": "https://www.example.org/draw"}}
        groups = provider_cohorts({"identities": rows}, configured, min_identities=1)
        self.assertEqual(["rugby-gap"], [row["identity_key"] for group in groups
                                          for row in group["identities"]])
        self.assertEqual([], provider_cohorts({"identities": rows}, configured))


if __name__ == "__main__":
    unittest.main()
