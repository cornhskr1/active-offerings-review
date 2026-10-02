from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "refresh-catalog-change-queue.yml").read_text(encoding="utf-8")


class CatalogChangeQueueWorkflowTests(unittest.TestCase):
    def test_queue_refresh_uses_focused_validation(self):
        self.assertNotIn("python3 -m unittest discover -s tests -v", WORKFLOW)
        self.assertIn("test_build_catalog_change_queue.py", WORKFLOW)
        self.assertIn("test_cricket_catalog_additions.py", WORKFLOW)
        self.assertIn("test_catalog_change_queue_workflow.py", WORKFLOW)
        self.assertIn("python3 scripts/build_catalog_change_queue.py", WORKFLOW)

    def test_mapping_and_source_files_trigger_queue_rebuild(self):
        for path in (
            "data/catalog-live.json",
            "data/catalog-season-map.json",
            "data/catalog-official-sources.json",
            "data/global-schedule-sources.json",
        ):
            self.assertIn(path, WORKFLOW)

    def test_queue_output_is_committed(self):
        self.assertIn("git add data/catalog-change-queue.json", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
