"""Offline proofs for a newer deployment waiting behind the current Pages lock."""
import hashlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_odds_deploy_safety as safety


class PendingDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.current = dict(id=10, workflow_id=99, run_number=10, run_attempt=1,
                            path=safety.WORKFLOW_PATH, head_branch='main',
                            repository={'full_name': safety.REPOSITORY},
                            head_repository={'full_name': safety.REPOSITORY},
                            head_sha='a' * 40, event='workflow_run',
                            status='in_progress', conclusion=None)
        self.pending = dict(self.current, id=11, run_number=11, head_sha='b' * 40, status='pending')
        self.anchor = dict(self.current, id=9, run_number=9, status='completed',
                           conclusion='success', updated_at='2026-10-19T00:00:00Z')
        self.empty = {'total_count': 0, 'jobs': []}
        self.workflow = dict(type='file', path=safety.WORKFLOW_PATH, sha=safety.SERIALIZED_WORKFLOW_BLOB)
        self.ref = safety.REPOSITORY + '/' + safety.WORKFLOW_PATH + '@refs/heads/main'

    def prove(self, current=None, pending=None, jobs=None, workflow=None, get_run=None, sha=None, ref=None):
        current = self.current if current is None else current
        pending = self.pending if pending is None else pending
        return safety.serialized_pending_runs(
            current, [self.anchor, current, pending],
            get_run or (lambda n: current if n == current['id'] else pending),
            jobs or (lambda n: self.empty), workflow or (lambda sha: self.workflow),
            current['head_sha'] if sha is None else sha, self.ref if ref is None else ref)

    def test_audited_pin_matches_actual_workflow_contract(self):
        raw = (ROOT / safety.WORKFLOW_PATH).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        self.assertEqual(blob, safety.SERIALIZED_WORKFLOW_BLOB,
                         'Review the workflow-wide Pages lock before updating its proof pin')
        self.assertIn(b'\nconcurrency:\n  group: pages\n  cancel-in-progress: false\n', raw)

    def test_newer_pending_without_jobs_does_not_poison_successful_history(self):
        runs = [self.anchor, self.current, self.pending]
        self.assertFalse(safety.permitted(self.current, runs))
        proof = self.prove()
        self.assertEqual(proof, {11})
        self.assertTrue(safety.permitted(self.current, runs, pending_runs=proof))
        for event in ('push', 'schedule', 'workflow_dispatch', 'workflow_run'):
            self.assertEqual(self.prove(pending=dict(self.pending, event=event)), {11})

    def test_waiting_proof_does_not_clear_real_failure_or_replace_anchor(self):
        proof = self.prove()
        failed = dict(self.anchor, id=8, conclusion='failure', updated_at='2026-10-19T01:00:00Z')
        self.assertFalse(safety.permitted(self.current, [self.pending], pending_runs=proof))
        self.assertFalse(safety.permitted(self.current, [self.anchor, failed, self.pending], pending_runs=proof))
        for status in ('in_progress', 'waiting', 'requested', 'unknown', 'completed'):
            self.assertFalse(safety.permitted(self.current, [self.anchor, dict(self.pending, status=status)], pending_runs=proof))

    def test_unknown_old_rerun_or_wrong_identity_is_never_proved(self):
        changes = [dict(run_number=9), dict(run_number=10), dict(run_number=True),
                   dict(run_number='11'), dict(run_attempt=2), dict(run_attempt=True),
                   dict(run_attempt='1'), dict(id='11'), dict(workflow_id=98),
                   dict(path='other.yml'), dict(head_branch='other'),
                   dict(repository={'full_name': 'other/repo'}),
                   dict(head_repository={'full_name': 'other/repo'}),
                   dict(head_sha='main'), dict(head_sha=None), dict(event='pull_request'),
                   dict(conclusion='success'), dict(status='in_progress'), dict(status='waiting')]
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(self.prove(pending=dict(self.pending, **change)), set())
        for change in (dict(run_attempt=2), dict(status='completed'), dict(conclusion='cancelled'),
                       dict(head_repository=None), dict(event='pull_request')):
            with self.subTest(current=change):
                self.assertEqual(self.prove(current=dict(self.current, **change)), set())

    def test_no_jobs_must_be_exact_not_missing_truncated_or_started(self):
        for payload in (None, [], {}, {'total_count': False, 'jobs': []},
                        {'total_count': '0', 'jobs': []}, {'total_count': 0.0, 'jobs': []},
                        {'total_count': 1, 'jobs': []}, {'total_count': 101, 'jobs': []},
                        {'total_count': 0, 'jobs': [{}]}, {'total_count': 0, 'jobs': None},
                        {'total_count': 1, 'jobs': [{'status': 'in_progress'}]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.prove(jobs=lambda n: payload), set())
        def unavailable(n):
            raise OSError('synthetic GitHub outage')
        with self.assertRaises(OSError):
            self.prove(jobs=unavailable)

    def test_missing_conclusion_and_boolean_identity_are_not_proof(self):
        pending = dict(self.pending)
        del pending['conclusion']
        self.assertEqual(self.prove(pending=pending), set())
        current = dict(self.current)
        del current['conclusion']
        self.assertEqual(self.prove(current=current), set())
        for field in ('id', 'workflow_id', 'run_number', 'run_attempt'):
            for value in (True, False, '1', None):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.prove(pending=dict(self.pending, **{field: value})), set())
                    self.assertEqual(self.prove(current=dict(self.current, **{field: value})), set())

    def test_completed_only_history_does_not_require_the_workflow_pin(self):
        def forbidden(*args):
            raise AssertionError('No pending run needs proof')
        self.assertEqual(safety.serialized_pending_runs(
            self.current, [self.anchor], forbidden, forbidden, forbidden, None, None), set())

    def test_both_immutable_execution_workflows_must_share_audited_lock(self):
        self.assertEqual(self.prove(sha='c' * 40), set())
        self.assertEqual(self.prove(ref=self.ref.replace('main', 'other')), set())
        for bad_sha in (self.current['head_sha'], self.pending['head_sha']):
            def changed(sha):
                return dict(self.workflow, sha='c' * 40) if sha == bad_sha else self.workflow
            self.assertEqual(self.prove(workflow=changed), set())
        for payload in (None, {}, dict(self.workflow, type='symlink'), dict(self.workflow, path='other.yml')):
            self.assertEqual(self.prove(workflow=lambda sha: payload), set())

    def test_started_or_rerun_between_jobs_and_run_recheck_remains_blocked(self):
        for change in (dict(status='in_progress'), dict(run_attempt=2), dict(head_sha='c' * 40),
                       dict(status='completed', conclusion='failure'), dict(repository=None)):
            def moved(n):
                return self.current if n == 10 else dict(self.pending, **change)
            with self.subTest(change=change):
                self.assertEqual(self.prove(get_run=moved), set())
        # A pending slot replaced before our recheck never acquired the same lock.
        self.assertEqual(self.prove(get_run=lambda n: self.current if n == 10 else
                                   dict(self.pending, status='completed', conclusion='cancelled')), {11})

    def test_current_lock_holder_is_rechecked_after_successor_proof(self):
        for change in (dict(status='completed', conclusion='cancelled'), dict(run_attempt=2),
                       dict(head_sha='c' * 40), dict(workflow_id=98)):
            self.assertEqual(self.prove(get_run=lambda n: dict(self.current, **change) if n == 10 else self.pending), set())

    def test_main_uses_pinned_attempt_and_commit_endpoints_before_permitting(self):
        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19]
        published = {'total_count': 1, 'jobs': [dict(run_id=9, run_attempt=1,
            head_branch='main', name='deploy', status='completed', conclusion='success',
            steps=[dict(number=n, name=name, status='completed', conclusion='success')
                   for n, name in zip(numbers, safety.DEPLOY_STEPS)])]}
        calls = []
        fixture = self
        class GitHub:
            def open(self, request, timeout):
                path = request.full_url.split(safety.REPOSITORY)[1]
                calls.append(path)
                if path == '/actions/runs/10':
                    payload = fixture.current
                elif path == '/actions/runs/11':
                    payload = fixture.pending
                elif path == '/actions/workflows/99/runs?per_page=100&page=1':
                    payload = {'total_count': 3, 'workflow_runs': [fixture.anchor, fixture.current, fixture.pending]}
                elif path == '/actions/runs/11/attempts/1/jobs?per_page=100':
                    payload = fixture.empty
                elif path == '/actions/runs/9/attempts/1/jobs?per_page=100':
                    payload = published
                elif path in ('/contents/' + safety.WORKFLOW_PATH + '?ref=' + sha
                              for sha in (fixture.current['head_sha'], fixture.pending['head_sha'])):
                    payload = fixture.workflow
                else:
                    raise AssertionError('Unpinned or unexpected endpoint: ' + path)
                return io.BytesIO(json.dumps(payload).encode())
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            'GITHUB_REPOSITORY': safety.REPOSITORY, 'GH_TOKEN': 'synthetic-test-token',
            'GITHUB_RUN_ID': '10', 'GITHUB_EVENT_NAME': 'workflow_run',
            'GITHUB_WORKFLOW_SHA': self.current['head_sha'], 'GITHUB_WORKFLOW_REF': self.ref,
            'RESUME_AFTER_REVIEW': 'false', 'RUNNER_TEMP': temp,
        }), patch.object(safety.urllib.request, 'build_opener', return_value=GitHub()):
            safety.main()
            proof = json.loads((pathlib.Path(temp) / 'odds-recovery-proof.json').read_text())
            self.assertEqual(proof['anchor_run_id'], 9)
        self.assertEqual(calls.count('/actions/runs/10'), 2)
        self.assertLess(calls.index('/actions/runs/11/attempts/1/jobs?per_page=100'),
                        calls.index('/actions/runs/11'))
        self.assertLess(calls.index('/actions/runs/11'), len(calls) - 1 - calls[::-1].index('/actions/runs/10'))


if __name__ == '__main__':
    unittest.main()
