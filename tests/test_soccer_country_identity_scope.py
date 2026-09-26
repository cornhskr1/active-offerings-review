"""Same-named Soccer competitions must remain country-specific identities."""

import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class SoccerCountryIdentityScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season_map = json.loads((DATA / "catalog-season-map.json").read_text())
        cls.registry = json.loads(
            (DATA / "competition-identity-registry.json").read_text()
        )
        cls.inventory = json.loads(
            (DATA / "priority2-coverage-inventory.json").read_text()
        )

    def test_every_soccer_catalog_key_has_one_registry_and_inventory_identity(self):
        soccer = next(
            sport for sport in self.season_map["sports"] if sport["sport"] == "Soccer"
        )
        expected = []
        for group in soccer["groups"]:
            for event in group["events"]:
                expected.extend(event.get("coverage_children") or [event])
        expected_keys = {item["key"] for item in expected}
        registry_rows = [
            item for item in self.registry["competitions"] if item["sport"] == "Soccer"
        ]
        inventory_rows = [
            item for item in self.inventory["identities"] if item["sport"] == "Soccer"
        ]

        self.assertEqual(353, len(expected))
        self.assertEqual(expected_keys, {item["identity_key"] for item in registry_rows})
        self.assertEqual(expected_keys, {item["identity_key"] for item in inventory_rows})
        self.assertEqual(353, self.inventory["by_sport"]["Soccer"]["identities"])

    def test_duplicate_labels_keep_country_specific_source_ids(self):
        expected_counts = {
            "Challenge Cup | Men": 2,
            "Primera División | Men": 2,
            "Ligue 1 | Men": 2,
            "Liga Nacional | Men": 2,
            "Super Cup | Men": 2,
            "President’s Cup | Men": 3,
            "Charity Shield | Men": 2,
            "Segunda División | Men": 2,
        }
        rows = defaultdict(list)
        for item in self.inventory["identities"]:
            if item["sport"] == "Soccer" and item["league"] in expected_counts:
                rows[item["league"]].append(item)

        self.assertEqual(expected_counts, {label: len(items) for label, items in rows.items()})
        for label, items in rows.items():
            with self.subTest(label=label):
                source_sets = [frozenset(source["id"] for source in item["sources"]) for item in items]
                self.assertTrue(all(source_sets))
                self.assertEqual(len(source_sets), len(set(source_sets)))

        ligue_1 = {item["identity_key"]: item for item in rows["Ligue 1 | Men"]}
        self.assertEqual(
            ["ligue1"],
            [source["id"] for source in ligue_1["soccer-france-ligue-1-men"]["sources"]],
        )
        self.assertEqual(
            ["caf-soccer-ivory-coast-ligue-1-men"],
            [
                source["id"]
                for source in ligue_1["soccer-ivory-coast-ligue-1-men"]["sources"]
            ],
        )

    def test_operational_keys_are_unique_systemwide(self):
        keys = [
            (item["sport"], item["identity_key"])
            for item in self.inventory["identities"]
        ]
        self.assertEqual([], [key for key, count in Counter(keys).items() if count > 1])
        self.assertEqual(731, len(keys))


if __name__ == "__main__":
    unittest.main()
