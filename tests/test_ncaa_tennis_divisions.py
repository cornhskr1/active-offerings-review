"""NCAA Division I men's and women's tennis require distinct identities."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class NCAATennisDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def approval(self):
        sport = next(
            item for item in self.season["sports"] if item["sport"] == "NCAA Tennis"
        )
        return next(
            event
            for group in sport["groups"]
            for event in group["events"]
            if event["catalog_event"] == "Division I Tennis | Men and Women"
        )

    def test_legal_parent_has_two_distinct_children(self):
        approval = self.approval()
        self.assertEqual(
            "combined-approval-separate-competitions",
            approval.get("identity_model"),
        )
        self.assertNotIn("source_id", approval)
        self.assertNotIn("source_ids", approval)
        children = approval.get("coverage_children") or []
        self.assertEqual(
            {"Division I Tennis | Men", "Division I Tennis | Women"},
            {child["label"] for child in children},
        )
        self.assertEqual(2, len({child["key"] for child in children}))
        self.assertTrue(all(not child.get("source_id") for child in children))

    def test_parent_is_not_schedulable_and_children_are_distinct(self):
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "NCAA Tennis"
        }
        approval = self.approval()
        self.assertNotIn(approval["catalog_event"], registry)
        for child in approval["coverage_children"]:
            self.assertIn(child["label"], registry)
            self.assertEqual(child["key"], registry[child["label"]]["identity_key"])
            self.assertEqual([], registry[child["label"]]["source_ids"])


if __name__ == "__main__":
    unittest.main()
