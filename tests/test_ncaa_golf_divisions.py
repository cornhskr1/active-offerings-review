"""NCAA Division I men's and women's golf must remain distinct identities."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class NCAAGolfDivisionIdentityTests(unittest.TestCase):
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
            item for item in self.season["sports"] if item["sport"] == "NCAA Golf"
        )
        return next(
            event
            for group in sport["groups"]
            for event in group["events"]
            if event["catalog_event"] == "Division I Golf | Men and Women"
        )

    def test_combined_approval_has_two_distinct_children(self):
        approval = self.approval()
        self.assertEqual(
            "combined-approval-separate-competitions",
            approval.get("identity_model"),
        )
        self.assertNotIn("source_id", approval)
        self.assertNotIn("source_ids", approval)
        children = approval.get("coverage_children") or []
        self.assertEqual(2, len(children))
        self.assertEqual(
            {"Division I Golf | Men", "Division I Golf | Women"},
            {child["label"] for child in children},
        )
        self.assertEqual(2, len({child["key"] for child in children}))
        self.assertEqual(
            {"ncaa-golf-di-men", "ncaa-golf-di-women"},
            {child.get("source_id") for child in children},
        )

    def test_combined_parent_is_not_a_schedulable_registry_entry(self):
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "NCAA Golf"
        }
        approval = self.approval()
        self.assertNotIn(approval["catalog_event"], registry)
        for child in approval["coverage_children"]:
            self.assertIn(child["label"], registry)
            self.assertEqual(child["key"], registry[child["label"]]["identity_key"])
            self.assertEqual([child["source_id"]], registry[child["label"]]["source_ids"])


if __name__ == "__main__":
    unittest.main()
