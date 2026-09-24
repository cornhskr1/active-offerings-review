"""Combined Rugby approvals must not collapse distinct competitions."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
IDENTITY_MODEL = "combined-approval-separate-competitions"


class RugbyDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )
        cls.aliases = json.loads(
            (DATA / "competition-alias-crosswalk.json").read_text(encoding="utf-8")
        )

    def test_combined_approvals_have_distinct_operational_children(self):
        rugby = next(s for s in self.season["sports"] if s["sport"] == "Rugby")
        combined = [
            event
            for group in rugby["groups"]
            for event in group["events"]
            if event["catalog_event"].endswith(" | Men and Women")
        ]
        self.assertEqual(5, len(combined))

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
            self.assertEqual(
                {"Men", "Women"},
                {child["label"].rsplit(" | ", 1)[1] for child in children},
            )
            self.assertTrue(all(child.get("key") for child in children))
            self.assertTrue(all(not child.get("source_id") for child in children))
            child_keys.extend(child["key"] for child in children)

        self.assertEqual(len(child_keys), len(set(child_keys)))

    def test_combined_parents_are_not_schedulable_registry_entries(self):
        rugby = next(s for s in self.season["sports"] if s["sport"] == "Rugby")
        combined = [
            event
            for group in rugby["groups"]
            for event in group["events"]
            if event["catalog_event"].endswith(" | Men and Women")
        ]
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "Rugby"
        }
        for parent in combined:
            self.assertNotIn(parent["catalog_event"], registry)
            for child in parent["coverage_children"]:
                self.assertIn(child["label"], registry)
                self.assertEqual(child["key"], registry[child["label"]]["identity_key"])

    def test_aliases_target_children_or_remain_in_review(self):
        combined = {
            "SVNS | Men and Women",
            "Six Nations Rugby | Men and Women",
            "Premier Rugby Sevens (PR7s) | Men and Women",
            "Rugby Americas North Championship | Men and Women",
            "Rugby Americas North Sevens | Men and Women",
        }
        reviewed = [
            row for row in self.aliases["reviewed_aliases"]
            if row["sport"] == "Rugby"
        ]
        self.assertFalse(any(row.get("catalog_identity") in combined for row in reviewed))

        by_alias = {row["alias"]: row for row in reviewed}
        self.assertEqual(
            "rugby-intl-six-nations-men",
            by_alias["Guinness Men’s Six Nations"]["identity_key"],
        )
        self.assertEqual(
            "rugby-intl-six-nations-women",
            by_alias["Guinness Women’s Six Nations"]["identity_key"],
        )

        held = {
            row.get("observed_official_name")
            for row in self.aliases["review_queue"]
            if row["sport"] == "Rugby"
        }
        self.assertTrue({
            "HSBC SVNS",
            "HSBC SVNS Series",
            "Six Nations Rugby",
            "Premier Rugby Sevens",
            "PR7s",
            "RAN Sevens",
        } <= held)


if __name__ == "__main__":
    unittest.main()
