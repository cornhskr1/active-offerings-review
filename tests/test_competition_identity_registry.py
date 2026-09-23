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
            for name in ("global-schedule.json", "global-schedule-sources.json", "catalog-season-map.json", "catalog-live.json", "competition-alias-crosswalk.json"):
                shutil.copy2(ROOT / "data" / name, isolated / "data" / name)
            subprocess.run(
                [sys.executable, str(isolated / "scripts" / "build_competition_identity_registry.py"), "--audit"],
                check=True,
            )
            cls.registry = json.loads(
                (isolated / "data" / "competition-identity-registry.json").read_text(encoding="utf-8")
            )
            cls.alias_audit = json.loads(
                (isolated / "data" / "competition-alias-audit.json").read_text(encoding="utf-8")
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
            if item["sport"] == "Football" and item["league"] == "National Football League (NFL)"
        )
        self.assertIn("Buffalo Bills", nfl["participants"])
        self.assertIn("Las Vegas Raiders", nfl["participants"])
        self.assertTrue(self.registry["coverage_gaps"])

        afl = next(item for item in self.registry["competitions"] if item["sport"] == "Aussie Rules")
        self.assertEqual("Australian Football League (AFL)", afl["league"])
        self.assertIn({"name": "AFL", "source_id": "afl"}, afl["source_labels"])
        self.assertEqual(1, len([item for item in self.registry["competitions"] if item["sport"] == "Aussie Rules"]))

        self.assertIn(("Soccer", "Serie A | Men"), actual)
        self.assertIn(("Soccer", "Serie A | Women"), actual)
        self.assertNotIn(("Soccer", "Serie A | Men and Women"), actual)

    def test_every_catalog_sport_has_a_source_identity_audit(self):
        self.assertEqual([block["sport"] for block in self.season_map["sports"]],
                         [block["sport"] for block in self.alias_audit["sports"]])
        by_sport = {block["sport"]: block for block in self.alias_audit["sports"]}
        self.assertEqual([], by_sport["Aussie Rules"]["schedule_only_labels"])
        self.assertEqual([], by_sport["Soccer"]["schedule_only_labels"])
        self.assertTrue(any(row["source_id"] == "rugby-rfl" and len(row["catalog_targets"]) > 1
                            for row in by_sport["Rugby"]["shared_sources_for_review"]))

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

    def test_reviewed_aliases_resolve_only_to_catalog_identities(self):
        competitions = {
            (item["sport"], item.get("identity_key")): item
            for item in self.registry["competitions"] if item.get("identity_key")
        }
        crosswalk = json.loads((ROOT / "data" / "competition-alias-crosswalk.json").read_text(encoding="utf-8"))
        for row in crosswalk["reviewed_aliases"]:
            with self.subTest(alias=row["alias"]):
                identity = (competitions[(row["sport"], row["identity_key"])] if row.get("identity_key") else
                            next(item for item in self.registry["competitions"] if item["sport"] == row["sport"] and item["league"] == row["catalog_identity"]))
                self.assertIn(row["alias"], [alias["name"] for alias in identity["aliases"]])
                if row.get("identity_key"):
                    self.assertIn(" | ", identity["league"])
        self.assertEqual(crosswalk["review_queue"], self.registry["alias_review_queue"])
        self.assertFalse(any(alias["name"] == "AFC Women's Champions League"
                             for item in self.registry["competitions"]
                             for alias in item.get("aliases", [])))
        womens_series = "FIBA 3x3 Women’s Series"
        self.assertTrue(any(row.get("observed_official_name") == womens_series
                            and row["catalog_identity"] == "FIBA 3x3 World Tour | Women"
                            for row in self.registry["alias_review_queue"]))
        self.assertFalse(any(alias["name"] == womens_series
                             for item in self.registry["competitions"]
                             for alias in item.get("aliases", [])))

    def test_baseball_draft_alias_does_not_claim_major_league(self):
        baseball = {item["league"]: item for item in self.registry["competitions"]
                    if item["sport"] == "Baseball"}
        self.assertIn("MLB Draft", [alias["name"] for alias in baseball["Draft"]["aliases"]])
        self.assertNotIn("MLB Draft", [alias["name"] for alias in baseball["Major League Baseball (MLB)"]["aliases"]])
        self.assertEqual("MLB", baseball["Major League Baseball (MLB)"]["aliases"][0]["name"])

    def test_alias_collision_with_other_division_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            (isolated / "scripts").mkdir()
            (isolated / "data").mkdir()
            shutil.copy2(ROOT / "scripts" / "build_competition_identity_registry.py",
                         isolated / "scripts" / "build_competition_identity_registry.py")
            for name in ("global-schedule.json", "global-schedule-sources.json", "catalog-season-map.json", "catalog-live.json"):
                shutil.copy2(ROOT / "data" / name, isolated / "data" / name)
            crosswalk = json.loads((ROOT / "data" / "competition-alias-crosswalk.json").read_text(encoding="utf-8"))
            crosswalk["reviewed_aliases"][0]["alias"] = "AFC Asian Cup | Men"
            (isolated / "data" / "competition-alias-crosswalk.json").write_text(json.dumps(crosswalk))
            result = subprocess.run(
                [sys.executable, str(isolated / "scripts" / "build_competition_identity_registry.py")],
                capture_output=True, text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("Alias collides with another competition", result.stderr)


if __name__ == "__main__":
    unittest.main()
