"""NCAA men's and women's water polo must resolve separately."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class NCAAWaterPoloDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def test_legal_parent_and_operational_children(self):
        sport = next(item for item in self.season["sports"] if item["sport"] == "NCAA Water Polo")
        approval = next(event for group in sport["groups"] for event in group["events"])
        self.assertEqual("Division I Water Polo | Men and Women", approval["catalog_event"])
        self.assertEqual("combined-approval-separate-competitions", approval["identity_model"])
        self.assertNotIn("source_id", approval)
        self.assertNotIn("source_ids", approval)
        children = approval["coverage_children"]
        self.assertEqual(
            {"Division I Water Polo | Men", "Division I Water Polo | Women"},
            {child["label"] for child in children},
        )
        self.assertEqual(2, len({child["key"] for child in children}))
        by_label={child["label"]:child for child in children}
        self.assertEqual("ncaa-water-polo-di-men",by_label["Division I Water Polo | Men"]["source_id"])
        self.assertNotIn("source_id",by_label["Division I Water Polo | Women"])
        self.assertTrue(all(child["season_hold"] for child in children))

    def test_combined_parent_cannot_be_scheduled(self):
        sport = next(item for item in self.season["sports"] if item["sport"] == "NCAA Water Polo")
        approval = next(event for group in sport["groups"] for event in group["events"])
        registry = {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "NCAA Water Polo"
        }
        self.assertNotIn(approval["catalog_event"], registry)
        for child in approval["coverage_children"]:
            self.assertEqual(child["key"], registry[child["label"]]["identity_key"])
            linked=registry[child["label"]]["source_ids"]
            if child["label"] == "Division I Water Polo | Women":
                self.assertEqual([],linked)
            else:
                # Generated registry may precede normal post-merge publication.
                self.assertIn(linked, [[], ["ncaa-water-polo-di-men"]])


if __name__ == "__main__":
    unittest.main()
