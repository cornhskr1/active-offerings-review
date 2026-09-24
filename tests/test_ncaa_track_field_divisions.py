"""NCAA indoor and outdoor track and field have separate division identities."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
EVENTS = (
    "Division I Indoor Track and Field | Men and Women",
    "Division I Outdoor Track and Field | Men and Women",
)


class NCAATrackFieldIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def test_legal_parents_have_four_unique_children(self):
        sport = next(item for item in self.season["sports"] if item["sport"] == "NCAA Track and Field")
        approvals = {
            item["catalog_event"]: item
            for group in sport["groups"]
            for item in group["events"]
        }
        self.assertEqual(set(EVENTS), set(approvals))
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "NCAA Track and Field"
        }
        keys = set()
        for name in EVENTS:
            approval = approvals[name]
            self.assertEqual("combined-approval-separate-competitions", approval.get("identity_model"))
            self.assertNotIn("source_id", approval)
            self.assertNotIn("source_ids", approval)
            self.assertNotIn(name, registry)
            children = approval["coverage_children"]
            self.assertEqual(
                {name.replace("Men and Women", division) for division in ("Men", "Women")},
                {child["label"] for child in children},
            )
            self.assertEqual(2, len(children))
            for child in children:
                self.assertNotIn(child["key"], keys)
                keys.add(child["key"])
                self.assertNotIn("source_id", child)
                self.assertEqual(child["key"], registry[child["label"]]["identity_key"])
                self.assertEqual([], registry[child["label"]]["source_ids"])
        self.assertEqual(4, len(keys))


if __name__ == "__main__":
    unittest.main()
