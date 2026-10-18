"""Chile's official page identity must not be mistaken for fixture coverage.

The 2026-10-18 public calendars are client-side shells. Keep the documented
gap until a supported public fixture source replaces these reviewed sources.
These tests perform no network requests and never use the protected backend.
"""

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_basketball_coverage import build


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/chile_basketball_source_evidence_2026.json"


class ChileBasketballSourceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read = lambda filename: json.loads((ROOT / "data" / filename).read_text())
        cls.config = read("global-schedule-sources.json")
        cls.inventory = read("priority2-coverage-inventory.json")
        cls.official = read("catalog-official-sources.json")
        cls.evidence = json.loads(FIXTURE.read_text())
        cls.source_ids = {row["source_id"] for row in cls.evidence["calendars"]}

    def test_manual_links_are_competition_specific(self):
        sources = {row["id"]: row for row in self.config["sources"]}
        for row in self.evidence["calendars"]:
            with self.subTest(source=row["source_id"]):
                self.assertEqual(row["url"], sources[row["source_id"]]["official_schedule_url"])
        copa = next(row for row in self.official["events"] if row["key"] == "basketball-cl-copa")
        self.assertEqual("https://lnbchile.com/copa-chile/calendario", copa["official_url"])

    def test_public_shells_remain_explicit_gaps_without_backend_endpoints(self):
        sources = {row["id"]: row for row in self.config["sources"]}
        for row in self.evidence["calendars"]:
            with self.subTest(source=row["source_id"]):
                source = sources[row["source_id"]]
                self.assertEqual("Basketball", source["sport"])
                self.assertEqual("coverage-gap", source["source_type"])
                self.assertEqual("missing", source["coverage_status"])
                self.assertFalse(source.get("endpoint"))
                self.assertEqual(0, row["match_links"])
                self.assertEqual(0, row["embedded_scheduled_at_fields"])

    def test_green_gap_refresh_never_means_healthy_empty_fixture_coverage(self):
        # The existing collector marks a recorded coverage-gap as ok=True.
        # That means the gap was recorded, not that any schedule was fetched.
        publication = {"sources": [
            {**source, "ok": True, "events": 0}
            for source in self.config["sources"] if source["id"] in self.source_ids
        ]}
        report = build(self.inventory, self.config, publication)
        rows = [row for row in report["identities"]
                if any(source["source_id"] in self.source_ids for source in row["sources"])]
        self.assertEqual({row["identity_key"] for row in self.evidence["calendars"]},
                         {row["identity_key"] for row in rows})
        for row in rows:
            with self.subTest(identity=row["identity_key"]):
                self.assertEqual("ADAPTER_GAP", row["linkage_state"])
                self.assertEqual("FIXTURE_CONNECTION_MISSING", row["operational_state"])
                self.assertEqual(0, sum(source["events_in_window"] for source in row["sources"]))

    def test_old_adapter_success_cannot_fill_current_chile_gap(self):
        publication = {"sources": [
            {**copy.deepcopy(source), "source_type": "obsolete-homepage-fixtures",
             "ok": True, "events": 12}
            for source in self.config["sources"] if source["id"] in self.source_ids
        ]}
        report = build(self.inventory, self.config, publication)
        for row in report["identities"]:
            for source in row["sources"]:
                if source["source_id"] in self.source_ids:
                    self.assertFalse(source["normal_publication_matches_adapter"])
                    self.assertIsNone(source["refresh_ok"])
                    self.assertEqual(0, source["events_in_window"])
                    self.assertEqual("FIXTURE_CONNECTION_MISSING", row["operational_state"])


if __name__ == "__main__":
    unittest.main()
