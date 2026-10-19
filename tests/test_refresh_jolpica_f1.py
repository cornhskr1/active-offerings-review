"""Offline transport, persistence, history, and single-publisher regressions."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import refresh_jolpica_f1 as refresh
import check_jolpica_refresh_safety as safety

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        trap = patch('socket.socket.connect', side_effect=AssertionError('network forbidden'))
        trap.start()
        self.addCleanup(trap.stop)


class TransportTests(OfflineTests):
    def response(self, body=b'{"synthetic": true}', status=200, headers=None):
        response = Mock(status=status, headers=headers or {})
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        return response, opener

    def test_only_exact_approved_url_and_request_shape(self):
        response, opener = self.response()
        result = refresh.provider_get(refresh.ENDPOINT, opener=opener)
        request = opener.open.call_args.args[0]
        self.assertEqual(refresh.ENDPOINT, request.full_url)
        self.assertEqual('GET', request.get_method())
        self.assertIsNone(request.data)
        self.assertEqual('application/json', request.get_header('Accept'))
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual({'timeout': 30}, opener.open.call_args.kwargs)
        self.assertEqual({'synthetic': True}, result['payload'])
        response.read.assert_called_once_with(refresh.MAX_BYTES + 1)
        for url in (refresh.ENDPOINT + '&extra=1', refresh.ENDPOINT.replace('https:', 'http:'),
                    'https://example.invalid/', refresh.ENDPOINT + '#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                refresh.provider_get(url, opener=opener)
        self.assertEqual(1, opener.open.call_count)

    def test_redirect_and_body_limit_overrides_rejected_before_open(self):
        opener = Mock()
        for args in ({'allow_redirects': True}, {'allow_redirects': None},
                     {'max_bytes': refresh.MAX_BYTES + 1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                refresh.provider_get(refresh.ENDPOINT, opener=opener, **args)
        opener.open.assert_not_called()

    def test_default_opener_installs_redirect_refusal(self):
        response, opener = self.response()
        with patch.object(refresh.urllib.request, 'build_opener', return_value=opener) as build:
            refresh.provider_get(refresh.ENDPOINT)
        self.assertIsInstance(build.call_args.args[0], refresh.NoRedirect)
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code), self.assertRaises(urllib.error.HTTPError):
                refresh.NoRedirect().redirect_request(
                    urllib.request.Request(refresh.ENDPOINT), None, code, 'Redirect', {},
                    'https://example.invalid/redirect')

    def test_body_limit_is_bounded_and_oversize_not_parsed(self):
        response, opener = self.response(body=b'x' * (refresh.MAX_BYTES + 1))
        result = refresh.provider_get(refresh.ENDPOINT, opener=opener)
        response.read.assert_called_once_with(refresh.MAX_BYTES + 1)
        self.assertEqual(refresh.MAX_BYTES + 1, result['body_bytes'])
        self.assertNotIn('payload', result)

    def test_non_200_never_reads_body_and_preserves_retry_after(self):
        for status in (201, 301, 401, 403, 429, 503):
            for retry in ('3600', 'Tue, 20 Oct 2026 12:00:00 GMT'):
                with self.subTest(status=status, retry=retry):
                    response, opener = self.response(status=status, headers={'Retry-After': retry})
                    result = refresh.provider_get(refresh.ENDPOINT, opener=opener)
                    response.read.assert_not_called()
                    self.assertEqual({'status_code': status, 'headers': {'Retry-After': retry},
                                      'body_bytes': 0}, result)

    def test_http_error_body_is_not_read_and_is_closed(self):
        body = Mock(wraps=io.BytesIO(b'private error body'))
        error = urllib.error.HTTPError(refresh.ENDPOINT, 429, 'limited', {'Retry-After': '90000'}, body)
        opener = Mock()
        opener.open.side_effect = error
        result = refresh.provider_get(refresh.ENDPOINT, opener=opener)
        body.read.assert_not_called()
        body.close.assert_called_once()
        self.assertEqual({'status_code': 429, 'headers': {'Retry-After': '90000'}, 'body_bytes': 0}, result)

    def test_invalid_json_not_returned_as_payload(self):
        _, opener = self.response(body=b'not json')
        with self.assertRaises(json.JSONDecodeError):
            refresh.provider_get(refresh.ENDPOINT, opener=opener)


class PersistenceTests(OfflineTests):
    def test_complete_output_replaces_previous_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'isolated.json'
            old = {'synthetic_previous': True}
            new = {'events': [], 'collector_state': {'halted': True}}
            path.write_text(json.dumps(old))
            real_replace = refresh.os.replace
            def inspect_replace(source, destination):
                self.assertEqual(path.parent, Path(source).parent)
                self.assertEqual(old, json.loads(path.read_text()))
                self.assertEqual(new, json.loads(Path(source).read_text()))
                real_replace(source, destination)
            get = Mock()
            with patch.object(refresh, 'collect_schedule', return_value=new) as collect, \
                    patch.object(refresh.os, 'replace', side_effect=inspect_replace) as replace:
                self.assertEqual(new, refresh.refresh(path, path, now=NOW, get=get))
            collect.assert_called_once_with(old, NOW, get=get)
            replace.assert_called_once()
            self.assertEqual(new, json.loads(path.read_text()))
            self.assertEqual([path], list(Path(directory).iterdir()))

    def test_write_or_replace_failure_preserves_original_and_removes_temp(self):
        for operation in ('dump', 'replace'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'isolated.json'
                original = '{"events": []}\n'
                path.write_text(original)
                target = refresh.json if operation == 'dump' else refresh.os
                with patch.object(refresh, 'collect_schedule', return_value={'events': []}), \
                        patch.object(target, operation, side_effect=OSError('synthetic failure')):
                    with self.assertRaises(OSError):
                        refresh.refresh(path, path, now=NOW, get=Mock())
                self.assertEqual(original, path.read_text())
                self.assertEqual([path], list(Path(directory).iterdir()))

    def test_missing_corrupt_or_invalid_cache_fails_before_provider(self):
        for content in (None, '{bad json', 'null', '[]', '{"collector_state": {"halted": true}}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                previous = Path(directory) / 'previous.json'
                output = Path(directory) / 'output.json'
                if content is not None:
                    previous.write_text(content)
                output.write_text('preserve this')
                get = Mock(side_effect=AssertionError('provider must not be called'))
                with self.assertRaises((FileNotFoundError, ValueError, TypeError)):
                    refresh.refresh(previous, output, now=NOW, get=get)
                get.assert_not_called()
                self.assertEqual('preserve this', output.read_text())
                self.assertFalse(list(Path(directory).glob('.jolpica-*')))


class HistoryTests(OfflineTests):
    def current(self, **updates):
        value = dict(id=100, workflow_id=77, path=safety.PATH, head_branch='main',
                     run_attempt=1, run_number=10)
        value.update(updates)
        return value

    def prior(self, **updates):
        value = dict(id=99, workflow_id=77, path=safety.PATH, head_branch='main',
                     run_number=9, run_attempt=1, status='completed', conclusion='success',
                     updated_at='2026-10-19T10:00:00Z')
        value.update(updates)
        return value

    def allowed(self, runs, resume=False, **current):
        return safety.permitted(self.current(**current), runs, resume=resume, now=NOW)

    def test_non_fifo_latest_completion_not_run_number_or_id_controls(self):
        earlier_success = self.prior(id=99, run_number=9)
        later_failure = self.prior(id=80, run_number=8, conclusion='failure', updated_at='2026-10-19T11:00:00Z')
        for runs in ([earlier_success, later_failure], [later_failure, earlier_success]):
            self.assertFalse(self.allowed(runs))
        later_failure['conclusion'] = 'success'
        earlier_success['conclusion'] = 'failure'
        self.assertTrue(self.allowed([earlier_success, later_failure]))

    def test_failed_cancelled_unknown_and_tied_completions_fail_closed(self):
        for conclusion in ('failure', 'cancelled', 'timed_out', 'skipped', None):
            with self.subTest(conclusion=conclusion):
                failed = self.prior(conclusion=conclusion)
                self.assertFalse(self.allowed([failed]))
                self.assertFalse(self.allowed([self.prior(id=98), failed]))

    def test_in_progress_never_bypassed_even_by_manual_resume(self):
        for status in ('in_progress', 'waiting', 'pending', None):
            with self.subTest(status=status):
                self.assertFalse(self.allowed([self.prior(status=status)], resume=True))
        self.assertTrue(self.allowed([self.prior(), self.prior(id=101, status='queued')]))

    def test_rerun_blocked_even_with_manual_resume(self):
        for resume in (False, True):
            self.assertFalse(self.allowed([self.prior()], resume=resume, run_attempt=2))

    def test_new_manual_resume_can_clear_completed_failure_only(self):
        self.assertTrue(self.allowed([self.prior(conclusion='failure')], resume=True))
        self.assertTrue(self.allowed([self.prior(conclusion='cancelled')], resume=True))
        self.assertFalse(self.allowed([], resume=True))
        self.assertTrue(self.allowed([], run_number=1))

    def test_main_manual_resume_requires_new_dispatch_and_explicit_input(self):
        current = self.current(repository={'full_name': safety.REPOSITORY})
        for event, value, expected in (('workflow_dispatch', 'true', True),
                                       ('workflow_dispatch', 'false', False),
                                       ('schedule', 'true', False),
                                       ('push', 'true', False)):
            with self.subTest(event=event, value=value):
                response = Mock()
                response.read.return_value = json.dumps(current).encode()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                opener = Mock()
                opener.open.return_value = response
                environment = {'GITHUB_REPOSITORY': safety.REPOSITORY,
                               'GITHUB_RUN_ID': '100', 'GH_TOKEN': 'synthetic-not-a-credential',
                               'GITHUB_EVENT_NAME': event, 'RESUME_AFTER_REVIEW': value}
                with patch.dict(safety.os.environ, environment, clear=True), \
                        patch.object(safety.urllib.request, 'build_opener', return_value=opener), \
                        patch.object(safety, 'stable_runs', return_value=[self.prior()]), \
                        patch.object(safety, 'permitted', return_value=True) as permitted:
                    safety.main()
                self.assertIs(expected, permitted.call_args.args[2])
                opener.open.assert_called_once()
                self.assertEqual('https://api.github.com/repos/' + safety.REPOSITORY + '/actions/runs/100',
                                 opener.open.call_args.args[0].full_url)

    def test_missing_mismatched_or_invalid_history_fails_closed(self):
        for runs in (None, {}, [None], [self.prior(workflow_id=78)],
                     [self.prior(head_branch='other')], [self.prior(id=True)],
                     [self.prior(updated_at='invalid')], [self.prior(updated_at='2026-10-19T10:00:00')],
                     [self.prior(updated_at='2026-10-20T10:00:00Z')]):
            with self.subTest(runs=runs):
                self.assertFalse(self.allowed(runs, resume=True))
        for updates in ({'path': 'other.yml'}, {'head_branch': 'other'}, {'id': True},
                        {'workflow_id': True}, {'run_attempt': None}):
            with self.subTest(updates=updates):
                self.assertFalse(self.allowed([self.prior()], **updates))


class WorkflowTests(unittest.TestCase):
    def test_single_pages_publisher_is_unchanged(self):
        workflows = ROOT / '.github' / 'workflows'
        publishers = [p.name for p in workflows.glob('*.yml')
                      if re.search(r'uses:\s*actions/deploy-pages@', p.read_text())]
        self.assertEqual(['deploy-pages.yml'], publishers)
        text = (workflows / 'deploy-pages.yml').read_text()
        self.assertIn('- Refresh Licensed F1 Schedule', text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", text)

    def test_source_workflow_serializes_and_commits_only_isolated_data(self):
        text = (ROOT / safety.PATH).read_text()
        self.assertIn('group: active-offerings-data', text)
        self.assertIn('queue: max', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertNotIn('cancel-in-progress: true', text)
        self.assertNotIn('pages: write', text)
        self.assertNotIn('id-token: write', text)
        self.assertNotIn('actions/deploy-pages', text)
        self.assertNotIn('actions/upload-pages-artifact', text)
        self.assertEqual(['data/jolpica-f1-events.json'], re.findall(r'^\s+git add (.+)$', text, re.M))
        self.assertIn('--previous data/jolpica-f1-events.json --output data/jolpica-f1-events.json', text)
        self.assertIn('contents: write', text)
        self.assertIn('actions: read', text)
        self.assertIn('default: false', text)
        steps = ['git reset --hard origin/main', 'python scripts/check_jolpica_refresh_safety.py',
                 'python scripts/refresh_jolpica_f1.py', 'git add data/jolpica-f1-events.json',
                 'git commit ', 'git rebase origin/main', 'git push origin HEAD:main']
        positions = [text.index(step) for step in steps]
        self.assertEqual(sorted(positions), positions)
        self.assertNotIn('--force', text)
        self.assertNotIn('secrets.', text)
        self.assertNotRegex(text, r'(?i)(gh run cancel|/cancel|cancel-workflow)')


if __name__ == '__main__':
    unittest.main()
