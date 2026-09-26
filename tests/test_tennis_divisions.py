"""Tennis identities must follow the real competition structure."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
MIXED_KEY = "tennis-united-cup"


class TennisDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def season_events(self):
        sport = next(item for item in self.season["sports"] if item["sport"] == "Tennis")
        return {
            event["key"]: event
            for group in sport["groups"]
            for event in group["events"]
        }

    def registry_events(self):
        return {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "Tennis"
        }

    def test_seven_approvals_have_distinct_operational_children(self):
        combined = [
            event
            for event in self.season_events().values()
            if event["catalog_event"].endswith(" | Men and Women")
            and event["key"] != MIXED_KEY
        ]
        self.assertEqual(7, len(combined))

        child_keys = []
        registry = self.registry_events()
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
            self.assertNotIn(approval["catalog_event"], registry)
            for child in children:
                self.assertEqual(child["key"], child.get("source_id"))
                self.assertEqual(
                    child["key"],
                    registry[child["label"]]["identity_key"],
                )
                self.assertEqual([child["key"]], registry[child["label"]]["source_ids"])
                child_keys.append(child["key"])

        self.assertEqual(14, len(child_keys))
        self.assertEqual(len(child_keys), len(set(child_keys)))

    def test_tennis_watch_division_source_ids_match_catalog_children(self):
        config = json.loads((DATA / "tennis-v2-config.json").read_text(encoding="utf-8"))
        expected = {
            "itf-men": "tennis-itf-world-tour-men",
            "itf-women": "tennis-itf-world-tour-women",
            "utr-men": "tennis-utr-pro-tour-men",
            "utr-women": "tennis-utr-pro-tour-women",
        }
        registry = self.registry_events()
        for tour, source in expected.items():
            with self.subTest(tour=tour):
                self.assertEqual(source, config["tour_approval_map"][tour])
                self.assertEqual([source], registry[next(
                    child["label"] for parent in self.season_events().values()
                    for child in parent.get("coverage_children", []) if child["key"] == source
                )]["source_ids"])

    def test_united_cup_remains_one_mixed_team_competition(self):
        united_cup = self.season_events()[MIXED_KEY]
        self.assertEqual(
            "single-mixed-gender-competition",
            united_cup.get("identity_model"),
        )
        self.assertEqual("tennis-united-cup", united_cup.get("source_id"))
        self.assertNotIn("coverage_children", united_cup)
        self.assertEqual(
            "https://www.unitedcup.com/en/about/overview",
            united_cup["identity_evidence_url"],
        )

        registry = self.registry_events()
        league = "United Cup | Men and Women"
        self.assertIn(league, registry)
        self.assertEqual(["tennis-united-cup"], registry[league]["source_ids"])
        self.assertNotIn("United Cup | Men", registry)
        self.assertNotIn("United Cup | Women", registry)


if __name__ == "__main__":
    unittest.main()
