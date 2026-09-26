"""Table Tennis identities must follow the real competition structure."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class TableTennisDivisionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season = json.loads(
            (DATA / "catalog-season-map.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text(encoding="utf-8")
        )

    def season_events(self):
        sport = next(
            item for item in self.season["sports"]
            if item["sport"] == "Table Tennis"
        )
        return {
            event["key"]: event
            for group in sport["groups"]
            for event in group["events"]
        }

    def registry_events(self):
        return {
            item["league"]: item
            for item in self.registry["competitions"]
            if item["sport"] == "Table Tennis"
        }

    def test_wtt_has_distinct_operational_children(self):
        wtt = self.season_events()["table-tennis-wtt"]
        self.assertEqual(
            "combined-approval-separate-competitions",
            wtt.get("identity_model"),
        )
        self.assertNotIn("source_id", wtt)
        self.assertNotIn("source_ids", wtt)
        children = wtt.get("coverage_children") or []
        self.assertEqual(2, len(children))
        self.assertEqual(
            {"World Table Tennis (WTT) | Men", "World Table Tennis (WTT) | Women"},
            {child["label"] for child in children},
        )
        self.assertEqual(
            {"table-tennis-wtt-men", "table-tennis-wtt-women"},
            {child.get("source_id") for child in children},
        )

        registry = self.registry_events()
        self.assertNotIn("World Table Tennis (WTT) | Men and Women", registry)
        for child in children:
            self.assertEqual(
                child["key"],
                registry[child["label"]]["identity_key"],
            )
            self.assertEqual([child["key"]], registry[child["label"]]["source_ids"])

    def test_mltt_remains_one_mixed_gender_team_competition(self):
        mltt = self.season_events()["table-tennis-mltt"]
        self.assertEqual(
            "single-mixed-gender-competition",
            mltt.get("identity_model"),
        )
        self.assertEqual("table-tennis-mltt", mltt.get("source_id"))
        self.assertNotIn("coverage_children", mltt)
        self.assertEqual("https://www.mltt.com/about-us", mltt["identity_evidence_url"])

        registry = self.registry_events()
        league = "Major League Table Tennis (MLTT) | Men and Women"
        self.assertIn(league, registry)
        self.assertEqual(["table-tennis-mltt"], registry[league]["source_ids"])
        self.assertFalse(any(
            name in registry
            for name in (
                "Major League Table Tennis (MLTT) | Men",
                "Major League Table Tennis (MLTT) | Women",
            )
        ))


if __name__ == "__main__":
    unittest.main()
