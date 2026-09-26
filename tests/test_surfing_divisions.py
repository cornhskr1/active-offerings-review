"""Combined Surfing approvals must not collapse distinct competitions."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
IDENTITY_MODEL = "combined-approval-separate-competitions"


class SurfingDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def test_combined_approvals_have_distinct_operational_children(self):
        surfing = next(s for s in self.season["sports"] if s["sport"] == "Surfing")
        combined = [
            event
            for group in surfing["groups"]
            for event in group["events"]
            if event["catalog_event"].endswith(" | Men and Women")
        ]
        self.assertEqual(3, len(combined))

        child_keys = []
        for approval in combined:
            self.assertEqual(IDENTITY_MODEL, approval.get("identity_model"))
            self.assertNotIn("source_id", approval)
            self.assertNotIn("source_ids", approval)
            children = approval.get("coverage_children") or []
            self.assertEqual(2, len(children))
            base = approval["catalog_event"].removesuffix(" | Men and Women")
            self.assertEqual(
                {f"{base} | Men", f"{base} | Women"},
                {child["label"] for child in children},
            )
            self.assertTrue(all(child.get("key") for child in children))
            if approval["key"] == "surfing-wsl-big-wave":
                self.assertTrue(all(not child.get("source_id") for child in children))
                self.assertTrue(all(child.get("season_hold") for child in children))
            else:
                self.assertTrue(all(child.get("source_id") == child["key"] for child in children))
            child_keys.extend(child["key"] for child in children)

        self.assertEqual(len(child_keys), len(set(child_keys)))

    def test_combined_parents_are_not_schedulable_registry_entries(self):
        surfing = next(s for s in self.season["sports"] if s["sport"] == "Surfing")
        combined = [
            event
            for group in surfing["groups"]
            for event in group["events"]
            if event["catalog_event"].endswith(" | Men and Women")
        ]
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "Surfing"
        }
        for parent in combined:
            self.assertNotIn(parent["catalog_event"], registry)
            for child in parent["coverage_children"]:
                self.assertIn(child["label"], registry)
                self.assertEqual(child["key"], registry[child["label"]]["identity_key"])


if __name__ == "__main__":
    unittest.main()
