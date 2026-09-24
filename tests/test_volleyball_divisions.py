"""Combined Volleyball approvals must not collapse distinct competitions."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class VolleyballDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def combined_approvals(self):
        sport = next(
            item for item in self.season["sports"]
            if item["sport"] == "Volleyball"
        )
        return [
            event
            for group in sport["groups"]
            for event in group["events"]
            if event["catalog_event"].endswith(" | Men and Women")
        ]

    def test_all_nine_approvals_have_distinct_operational_children(self):
        combined = self.combined_approvals()
        self.assertEqual(9, len(combined))

        child_keys = []
        for approval in combined:
            self.assertEqual(
                "combined-approval-separate-competitions",
                approval.get("identity_model"),
            )
            self.assertNotIn("source_id", approval)
            self.assertNotIn("source_ids", approval)
            children = approval.get("coverage_children") or []
            self.assertEqual(2, len(children))
            base = approval["catalog_event"].removesuffix(" | Men and Women")
            self.assertEqual(
                {f"{base} | Men", f"{base} | Women"},
                {child["label"] for child in children},
            )
            self.assertTrue(all(not child.get("source_id") for child in children))
            child_keys.extend(child["key"] for child in children)

        self.assertEqual(18, len(child_keys))
        self.assertEqual(len(child_keys), len(set(child_keys)))

    def test_combined_parents_are_not_schedulable_registry_entries(self):
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "Volleyball"
        }
        for parent in self.combined_approvals():
            self.assertNotIn(parent["catalog_event"], registry)
            for child in parent["coverage_children"]:
                self.assertIn(child["label"], registry)
                self.assertEqual(
                    child["key"],
                    registry[child["label"]]["identity_key"],
                )


if __name__ == "__main__":
    unittest.main()
