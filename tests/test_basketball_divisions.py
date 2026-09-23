"""Combined approvals must not collapse distinct basketball competitions."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class BasketballDivisionIdentityTests(unittest.TestCase):
    def test_combined_approvals_have_distinct_coverage(self):
        season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        basketball = next(s for s in season["sports"] if s["sport"] == "Basketball")
        combined = [event for group in basketball["groups"] for event in group["events"]
                    if event["catalog_event"].endswith(" | Men and Women")]
        self.assertEqual(13, len(combined))
        for approval in combined:
            self.assertEqual("combined-approval-separate-competitions", approval["identity_model"])
            children = approval["coverage_children"]
            self.assertEqual(["Men", "Women"], [c["label"].rsplit(" | ", 1)[1] for c in children])
            self.assertEqual(2, len({c["key"] for c in children}))
            for child in children:
                self.assertNotIn("season_status", child)
                self.assertNotIn("season_start", child)
                self.assertNotIn("season_end", child)
                if child.get("source_id"):
                    self.assertEqual(child["key"], child["source_id"])
                    self.assertIn("season_start_date", child)
                    self.assertIn("season_end_date", child)

    def test_existing_wnba_identity_is_not_duplicated(self):
        season = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
        basketball = next(s for s in season["sports"] if s["sport"] == "Basketball")
        labels = [event["catalog_event"] for group in basketball["groups"] for event in group["events"]]
        self.assertEqual(1, labels.count("Women’s National Basketball Association (WNBA) | Women"))


if __name__ == "__main__":
    unittest.main()
