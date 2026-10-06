from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "update-catalog.yml").read_text(encoding="utf-8")


class CatalogRefreshWorkflowTests(unittest.TestCase):
    def test_catalog_poll_runs_once_daily(self):
        match = re.search(r'cron:\s*"([^"]+)"', WORKFLOW)
        self.assertIsNotNone(match)
        cron = match.group(1)
        self.assertEqual(cron, "23 13 * * *")
        self.assertNotIn("*/", cron)

    def test_catalog_refresh_uses_focused_validation_not_full_repository_suite(self):
        self.assertIn("test_build_catalog_change_queue.py", WORKFLOW)
        self.assertIn("test_dashboard_scope.py", WORKFLOW)
        self.assertNotIn("python3 -m unittest discover -s tests -v", WORKFLOW)



    def test_catalog_refresh_rebuilds_registry_after_catalog_commit(self):
        catalog_commit = WORKFLOW.index("- name: Commit current catalog data")
        registry_build = WORKFLOW.index("- name: Rebuild catalog-aligned competition registry")
        registry_verify = WORKFLOW.index("- name: Verify catalog-aligned competition registry")
        registry_commit = WORKFLOW.index("- name: Commit catalog-aligned competition registry")
        self.assertLess(catalog_commit, registry_build)
        self.assertLess(registry_build, registry_verify)
        self.assertLess(registry_verify, registry_commit)
        self.assertIn("scripts/build_competition_identity_registry.py", WORKFLOW)
        self.assertIn("tests.test_competition_identity_registry", WORKFLOW)
        self.assertIn("tests.test_basketball_divisions", WORKFLOW)
        self.assertIn("data/competition-identity-registry.json", WORKFLOW)

    def test_catalog_bot_does_not_rely_on_a_second_push_workflow(self):
        self.assertIn("Align competition identity registry to current catalog", WORKFLOW)
        self.assertIn('"tests/test_catalog_refresh_workflow.py"', WORKFLOW)

    def test_workflow_change_triggers_one_immediate_refresh_after_merge(self):
        self.assertIn("push:", WORKFLOW)
        self.assertIn('".github/workflows/update-catalog.yml"', WORKFLOW)
        self.assertIn('"scripts/update_catalog.py"', WORKFLOW)


if __name__ == "__main__":
    unittest.main()
