import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_MODEL = "combined-approval-separate-competitions"


def soccer_combined_parents(season_map):
    soccer = next(sport for sport in season_map["sports"] if sport["sport"] == "Soccer")
    return [
        event
        for group in soccer.get("groups", [])
        for event in group.get("events", [])
        if "Men and Women" in event.get("catalog_event", "")
    ]


class CompetitionIdentityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build from the current inputs without rewriting a tracked file in the
        # checkout. GitHub workflows must remain clean before their rebase.
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            (isolated / "scripts").mkdir()
            (isolated / "data").mkdir()
            shutil.copy2(ROOT / "scripts" / "build_competition_identity_registry.py",
                         isolated / "scripts" / "build_competition_identity_registry.py")
            for name in ("global-schedule.json", "catalog-season-map.json", "catalog-live.json"):
                shutil.copy2(ROOT / "data" / name, isolated / "data" / name)
            subprocess.run(
                [sys.executable, str(isolated / "scripts" / "build_competition_identity_registry.py")],
                check=True,
            )
            cls.registry = json.loads(
                (isolated / "data" / "competition-identity-registry.json").read_text(encoding="utf-8")
            )
        cls.season_map = json.loads(
            (ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8")
        )

    def test_registry_covers_catalog_mappings_and_observed_participants(self):
        expected = set()
        for sport in self.season_map["sports"]:
            for group in sport.get("groups", []):
                for event in group.get("events", []):
                    children = event.get("coverage_children") or []
                    if children:
                        expected.update((sport["sport"], child["label"]) for child in children)
                    elif event.get("catalog_event"):
                        expected.add((sport["sport"], event["catalog_event"]))
        actual = {(item["sport"], item["league"]) for item in self.registry["competitions"]}
        self.assertLessEqual(expected, actual)

        nfl = next(
            item
            for item in self.registry["competitions"]
            if item["sport"] == "Football" and item["league"] == "NFL"
        )
        self.assertIn("Buffalo Bills", nfl["participants"])
        self.assertIn("Las Vegas Raiders", nfl["participants"])
        self.assertTrue(self.registry["coverage_gaps"])

        self.assertIn(("Soccer", "Serie A | Men"), actual)
        self.assertIn(("Soccer", "Serie A | Women"), actual)
        self.assertNotIn(("Soccer", "Serie A | Men and Women"), actual)

    def test_every_combined_soccer_approval_has_isolated_operational_identities(self):
        parents = soccer_combined_parents(self.season_map)

        self.assertEqual(22, len(parents))
        child_keys = []
        child_source_ids = []
        for parent in parents:
            self.assertEqual(IDENTITY_MODEL, parent.get("identity_model"))
            self.assertNotIn("source_id", parent)
            self.assertNotIn("source_ids", parent)
            children = parent.get("coverage_children") or []
            self.assertEqual(2, len(children))
            base = parent["catalog_event"].replace(" | Men and Women", "")
            self.assertEqual(
                {f"{base} | Men", f"{base} | Women"},
                {child["label"] for child in children},
            )
            self.assertTrue(all(child.get("key") and child.get("source_id") for child in children))
            child_keys.extend(child["key"] for child in children)
            child_source_ids.extend(child["source_id"] for child in children)

        self.assertEqual(len(child_keys), len(set(child_keys)))
        self.assertEqual(len(child_source_ids), len(set(child_source_ids)))

    def test_combined_soccer_parents_are_not_schedulable_registry_entries(self):
        soccer_leagues = {
            item["league"] for item in self.registry["competitions"] if item["sport"] == "Soccer"
        }
        for parent in soccer_combined_parents(self.season_map):
            self.assertNotIn(parent["catalog_event"], soccer_leagues)
            self.assertLessEqual(
                {child["label"] for child in parent["coverage_children"]},
                soccer_leagues,
            )

    def test_combined_soccer_children_point_to_exact_source_identities(self):
        configured = {}
        source_paths = [
            ROOT / "data" / "global-schedule-sources.json",
            *sorted((ROOT / "data").glob("soccer-*-sources.json")),
        ]
        for path in source_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for source in payload.get("sources", []):
                self.assertNotIn(source["id"], configured)
                configured[source["id"]] = source

        for parent in soccer_combined_parents(self.season_map):
            for child in parent["coverage_children"]:
                source = configured[child["source_id"]]
                self.assertEqual("Soccer", source["sport"])
                self.assertEqual(child["label"], source["league"])
                self.assertIn(parent["catalog_event"], source.get("catalog_terms", []))


if __name__ == "__main__":
    unittest.main()
