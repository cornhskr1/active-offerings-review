"""Exact authenticated readiness profile; unknown histories remain blocking."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_odds_deploy_safety as safety


class ReadyProfileTests(unittest.TestCase):
    def setUp(self):
        evidence = json.loads((ROOT / 'tests/fixtures/odds_ready_publication_43713372688.json').read_text())
        self.run = evidence['run']
        self.payload = evidence['payload']

    def reject(self, payload, run=None):
        run = run or self.run
        self.assertFalse(safety.successful_publication(run, payload))
        self.assertFalse(safety.precollection_failure(run, payload))

    def test_authenticated_success_and_exact_numbers(self):
        steps = self.payload['jobs'][0]['steps']
        self.assertEqual([s['number'] for s in steps], list(range(1, 11)) + [19, 20, 21])
        self.assertEqual([s['name'] for s in steps], safety.READY_RECOVERY_STEPS)
        self.assertTrue(safety.successful_publication(self.run, self.payload))
        self.assertEqual(steps[5]['conclusion'], 'skipped')
        fresh = copy.deepcopy(self.payload)
        fresh['jobs'][0]['steps'][5]['conclusion'] = 'success'
        self.assertTrue(safety.successful_publication(self.run, fresh))

    def test_all_existing_exact_profiles_remain_compatible(self):
        for profile in (safety.DEPLOY_STEPS, safety.RECOVERY_STEPS,
                        safety.LEGACY_PINNED_RECOVERY_STEPS, safety.PINNED_RECOVERY_STEPS):
            p = copy.deepcopy(self.payload)
            p['jobs'][0]['steps'] = [dict(name=name, number=n, status='completed', conclusion='success')
                for name, n in zip(profile, list(range(1, 10)) + [17, 18, 19])]
            with self.subTest(profile=profile):
                self.assertTrue(safety.successful_publication(self.run, p))
                failed = dict(self.run, conclusion='failure')
                p['jobs'][0]['conclusion'] = 'failure'
                for i, step in enumerate(p['jobs'][0]['steps']):
                    step['conclusion'] = 'success' if i < 3 or i > 8 else ('failure' if i == 3 else 'skipped')
                self.assertTrue(safety.precollection_failure(failed, p))

    def test_unknown_step_identity_order_number_or_status_is_rejected(self):
        for i in range(13):
            for key, value in (('name', 'unknown'), ('number', 100 + i), ('status', 'in_progress')):
                p = copy.deepcopy(self.payload)
                p['jobs'][0]['steps'][i][key] = value
                with self.subTest(index=i, key=key):
                    self.reject(p)
        p = copy.deepcopy(self.payload)
        for step, number in zip(p['jobs'][0]['steps'][-3:], [18, 19, 20]):
            step['number'] = number
        self.reject(p)
        for mutation in ('missing', 'extra', 'nondict', 'reordered', 'mixed_pin'):
            p = copy.deepcopy(self.payload); steps = p['jobs'][0]['steps']
            if mutation == 'missing': steps.pop(8)
            elif mutation == 'extra': steps.append(dict(steps[-1]))
            elif mutation == 'nondict': steps[8] = None
            elif mutation == 'reordered': steps[8], steps[9] = steps[9], steps[8]
            else: steps[2]['name'] = safety.LEGACY_PINNED_RECOVERY_STEPS[2]
            with self.subTest(mutation=mutation): self.reject(p)

    def test_malformed_or_wrong_job_and_attempt_are_rejected(self):
        for payload in (None, {}, {'total_count': 0, 'jobs': []},
                        {'total_count': 2, 'jobs': self.payload['jobs']},
                        {'total_count': 1, 'jobs': [None]},
                        {'total_count': 1, 'jobs': self.payload['jobs'] * 2}):
            self.reject(payload)
        for key, value in (('run_id', 1), ('run_attempt', 2), ('head_branch', 'other'),
                           ('name', 'other'), ('status', 'in_progress'), ('conclusion', 'failure'),
                           ('steps', None)):
            p = copy.deepcopy(self.payload); p['jobs'][0][key] = value
            with self.subTest(key=key): self.reject(p)
        self.reject(self.payload, dict(self.run, run_attempt=2))
        self.reject(self.payload, dict(self.run, status='in_progress'))

    def test_only_guard_or_stage_failure_can_be_precollection(self):
        for failed_index in range(13):
            run = dict(self.run, conclusion='failure')
            p = copy.deepcopy(self.payload); job = p['jobs'][0]; job['conclusion'] = 'failure'
            for i, step in enumerate(job['steps']):
                step['conclusion'] = 'success' if i < failed_index or i >= 10 else 'skipped'
            job['steps'][failed_index]['conclusion'] = 'failure'
            with self.subTest(failed_index=failed_index):
                self.assertFalse(safety.successful_publication(run, p))
                self.assertEqual(safety.precollection_failure(run, p), failed_index in (3, 4))
        for outcome in ('failure', 'skipped', 'cancelled', 'neutral', None):
            p = copy.deepcopy(self.payload); p['jobs'][0]['steps'][8]['conclusion'] = outcome
            self.reject(p)

    def test_current_workflow_matches_authenticated_action_identities(self):
        raw = (ROOT / safety.WORKFLOW_PATH).read_text()
        for index in (2, 6, 7, 9):
            self.assertIn('uses: ' + self.payload['jobs'][0]['steps'][index]['name'].removeprefix('Run '), raw)
        self.assertIn('name: Verify exact Pages artifact is ready', raw)
        self.assertIn('uses: ./.github/actions/wait-pages-artifact', raw)


if __name__ == '__main__':
    unittest.main()
