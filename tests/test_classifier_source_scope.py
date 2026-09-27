"""Configured classifier parents retain exact catalog child identity and limits."""

import json
import unittest
from pathlib import Path

from scripts.audit_priority2_coverage import configured_scope_owners


DATA = Path(__file__).resolve().parents[1] / "data"


class ClassifierSourceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((DATA / "global-schedule-sources.json").read_text())
        cls.schedule = json.loads((DATA / "global-schedule.json").read_text())
        cls.inventory = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        cls.rows = {r["identity_key"]: r for r in cls.inventory["identities"]}

    def test_all_classified_children_have_exact_catalog_identities(self):
        owners = configured_scope_owners(self.config["sources"])
        keys = {(r["sport"], s["id"]) for r in self.inventory["identities"] for s in r["sources"]}
        self.assertTrue(set(owners).issubset(keys))
        self.assertNotIn("SOURCE_SCOPE_REVIEW", self.inventory["summary"]["coverage_states"])
        self.assertEqual(731, len(self.rows))
        for (sport, child), parent in owners.items():
            if parent["id"] == child:
                continue  # Already configured directly; no derived scope required.
            row = next(r for r in self.rows.values() if r["sport"] == sport and any(s["id"] == child for s in r["sources"]))
            source = next(s for s in row["sources"] if s["id"] == child)
            self.assertEqual(parent["id"], source["configured_source_id"])
            self.assertEqual(parent.get("source_type", "adapter"), source["type"])
            if parent.get("source_type") == "official-event-window":
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
            elif parent.get("source_type") == "coverage-gap":
                self.assertEqual("ADAPTER_GAP", row["coverage_state"])
            else:
                self.assertEqual("ADAPTER_CONFIGURED", row["coverage_state"])

    def test_parent_refresh_does_not_count_unrelated_child_events(self):
        cycling = self.rows["cycling-cadel-evans"]["sources"][0]
        self.assertTrue(cycling["refresh_ok"])
        self.assertEqual(0, cycling["events_in_window"])
        self.assertEqual("cycling-uci-calendar", cycling["configured_source_id"])
        self.assertGreater(next(s["events"] for s in self.schedule["sources"] if s["id"] == "cycling-uci-calendar"), 0)
        simulation = self.rows["esports-gt-sports-league"]
        self.assertEqual("ADAPTER_GAP", simulation["coverage_state"])
        self.assertEqual("esports-simulation-calendar", simulation["sources"][0]["configured_source_id"])

    def test_unknown_scope_and_ambiguous_ownership_fail_closed(self):
        self.assertNotIn(("Cycling", "cycling-unapproved-tour"), configured_scope_owners(self.config["sources"]))
        with self.assertRaisesRegex(ValueError, "Ambiguous configured source scope"):
            configured_scope_owners([
                {"sport": "Cycling", "id": "a", "scope_source_ids": ["race"]},
                {"sport": "Cycling", "id": "b", "scope_source_ids": ["race"]},
            ])


if __name__ == "__main__":
    unittest.main()
