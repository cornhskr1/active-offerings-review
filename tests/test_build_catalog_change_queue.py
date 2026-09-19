import unittest

from scripts.build_catalog_change_queue import build_queue


def catalog(lines):
    return {
        "generated_at": "2026-09-19T00:00:00+00:00",
        "source_label": "Test catalog",
        "menu_version": "9.19.26",
        "sha256": "test",
        "sections": [{"sport": "Soccer", "lines": lines}],
    }


def season_map(snapshot):
    return {
        "sports": [
            {
                "sport": "Soccer",
                "catalog_snapshot_lines": snapshot,
                "groups": [
                    {
                        "country": "United States",
                        "governing_body": "United States Soccer Federation",
                        "events": [
                            {
                                "key": "soccer-existing",
                                "catalog_event": "Existing League | Men",
                                "source_id": "soccer-existing",
                            }
                        ],
                    }
                ],
            }
        ]
    }


class CatalogQueueTests(unittest.TestCase):
    def build(self, current, snapshot):
        return build_queue(
            catalog(current),
            season_map(snapshot),
            {},
            {},
        )

    def test_new_catalog_entry_is_blocked(self):
        result = self.build(
            ["United States", "Existing League | Men", "New League | Women"],
            ["United States", "Existing League | Men"],
        )
        self.assertEqual(result["summary"]["catalog_additions"], 1)
        item = result["open_items"][0]
        self.assertFalse(item["publishable"])
        self.assertFalse(item["review_today_eligible"])
        self.assertEqual(item["publication_gate"], "BLOCKED")

    def test_removed_entry_requires_deactivation_review(self):
        result = self.build(
            ["United States"],
            ["United States", "Existing League | Men"],
        )
        self.assertEqual(result["summary"]["catalog_removals"], 1)
        codes = {row["code"] for row in result["open_items"][0]["missing_setup"]}
        self.assertIn("schedule-deactivation", codes)

    def test_similar_restriction_wording_is_a_change(self):
        result = self.build(
            ["Existing League | Men - NO PLAYER PROPOSITION WAGERS"],
            ["Existing League | Men - NO PROPOSITION WAGERS"],
        )
        self.assertEqual(result["summary"]["catalog_changes"], 1)
        self.assertEqual(result["summary"]["catalog_additions"], 0)
        self.assertEqual(result["summary"]["catalog_removals"], 0)


if __name__ == "__main__":
    unittest.main()
