#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_tennis_risk_snapshot", ROOT / "scripts" / "build_tennis_risk_snapshot.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TennisRiskSnapshotTests(unittest.TestCase):
    def test_merges_registry_and_cache_without_publishing_dob(self):
        registry = {
            "generated_at": "2026-09-20T00:00:00Z",
            "verified_u18": [{
                "name": "Álex Junior", "aliases": ["A. Junior"], "age": 17,
                "source": "Official profile", "source_url": "https://example.test/player"
            }],
        }
        cache = {
            "generated_at": "2026-09-21T00:00:00Z",
            "records": {
                "alex junior": {
                    "name": "Alex Junior", "age_status": "VERIFIED U18",
                    "dob": "2009-01-01", "evidence": "Verified age 17"
                }
            },
        }
        out = MOD.build_snapshot(registry, cache, "2026-09-21T01:00:00Z")
        self.assertEqual(out["summary"]["verified_u18_identities"], 1)
        self.assertIn("A. Junior", out["entries"][0]["aliases"])
        self.assertNotIn("dob", out["entries"][0])
        self.assertEqual(out["entries"][0]["age_status"], "VERIFIED U18")

    def test_duplicate_alias_is_blocked_as_ambiguous(self):
        registry = {"verified_u18": [
            {"name": "Alex One", "aliases": ["A. One"]},
            {"name": "Avery One", "aliases": ["A. One"]},
        ]}
        out = MOD.build_snapshot(registry, {}, "2026-09-21T01:00:00Z")
        self.assertIn("a one", out["ambiguous_aliases"])

    def test_snapshot_id_is_stable_across_generation_times(self):
        registry = {"verified_u18": [{"name": "Alex Junior", "age": 17}]}
        first = MOD.build_snapshot(registry, {}, "2026-09-21T01:00:00Z")
        second = MOD.build_snapshot(registry, {}, "2026-09-22T01:00:00Z")
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])


if __name__ == "__main__":
    unittest.main()
