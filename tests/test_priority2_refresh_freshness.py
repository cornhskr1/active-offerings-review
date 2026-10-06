"""Normal publication must rebuild and commit coverage from the same schedule."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoveragePublicationTests(unittest.TestCase):
    def test_inventory_is_rebuilt_after_schedule_and_identity_registry(self):
        workflow = (ROOT / '.github/workflows/refresh-global-schedule.yml').read_text()
        self.assertLess(workflow.index('run: python3 scripts/refresh_global_schedule.py'), workflow.index('run: python3 scripts/build_competition_identity_registry.py'))
        self.assertLess(workflow.index('run: python3 scripts/build_competition_identity_registry.py'), workflow.index('run: python3 scripts/audit_priority2_coverage.py'))
        self.assertLess(workflow.index('run: python3 scripts/audit_priority2_coverage.py'), workflow.index('git add data/global-schedule.json'))
        self.assertIn('git add data/global-schedule.json data/competition-identity-registry.json data/priority2-coverage-inventory.json', workflow)


if __name__ == '__main__':
    unittest.main()
