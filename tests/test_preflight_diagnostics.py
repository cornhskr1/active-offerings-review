"""Failure receipts must explain the block without exposing secrets or retrying."""
import copy
import datetime as dt
import json
import unittest

from scripts import api_sports_nba_preflight as nba, sharp_api_preflight as sharp
from scripts.preflight_diagnostics import ERRORS
from tests.test_api_sports_nba_preflight import payload as nba_payload, SOURCE as NBA_SOURCE
from tests.test_sharp_api_preflight import payload as sharp_payload, account, SOURCE as SHARP_SOURCE, NOW, KEY


class Response:
    status_code = 200

    def __init__(self, payload, headers, invalid_json=False):
        self.payload, self.headers, self.invalid_json = payload, headers, invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError(KEY + ' PRIVATE BODY')
        return copy.deepcopy(self.payload)


class Diagnostics(unittest.TestCase):
    def run_provider(self, provider, *, payload=None, headers=None, previous=None,
                     now=NOW, invalid_json=False, transport=False, event_failure=False):
        calls = []
        def get(url, **kwargs):
            calls.append((url, kwargs))
            if transport:
                raise RuntimeError(KEY + ' PRIVATE BODY')
            acct = url.endswith('/account')
            normal_headers = ({'x-ratelimit-requests-limit': '100', 'x-ratelimit-requests-remaining': '99'}
                              if provider is nba else {'X-RateLimit-Limit': '12', 'X-RateLimit-Remaining': '10'})
            default = account() if acct else nba_payload() if provider is nba else sharp_payload()
            fail_here = not event_failure or not acct
            return Response(payload if payload is not None and not acct else default,
                            headers if headers is not None and fail_here else normal_headers,
                            invalid_json and fail_here)
        source = NBA_SOURCE if provider is nba else SHARP_SOURCE
        before = copy.deepcopy(previous)
        result = provider.collect(source, previous or {}, now, KEY, get)
        self.assertEqual(previous, before)
        self.assertNotIn(KEY, json.dumps(result))
        self.assertNotIn('PRIVATE BODY', json.dumps(result))
        self.assertFalse(result['ok']); self.assertEqual(result['events'], 0)
        self.assertFalse(result['coverage_complete']); self.assertTrue(result['review_required'])
        self.assertLessEqual(len(calls), 1 if provider is nba else 2)
        return result, calls

    def assert_cause(self, result, stage, code):
        self.assertEqual(result['preflight_diagnostic'], {'version': 1, 'stage': stage, 'code': code})
        self.assertEqual(result['errors'], [ERRORS[code]])
        self.assertNotIn('preflight_evidence', result)
        self.assertIsNone(result['checked_at'])

    def test_daily_nba_quota_failures_are_distinguishable_and_never_use_minute_quota(self):
        for headers, code in [
            ({'X-RateLimit-Limit': '10', 'X-RateLimit-Remaining': '9'}, 'quota_headers_missing'),
            ({'x-ratelimit-requests-limit': KEY, 'x-ratelimit-requests-remaining': '99'}, 'quota_headers_malformed'),
            ({'x-ratelimit-requests-limit': '²', 'x-ratelimit-requests-remaining': '1'}, 'quota_headers_malformed'),
            ({'x-ratelimit-requests-limit': '7500', 'x-ratelimit-requests-remaining': '7499'}, 'quota_limit_outside_free_range'),
            ({'x-ratelimit-requests-limit': '100', 'x-ratelimit-requests-remaining': '100'}, 'quota_remaining_inconsistent'),
            ({'x-ratelimit-requests-limit': '9' * 5000, 'x-ratelimit-requests-remaining': '99'}, 'quota_limit_outside_free_range'),
        ]:
            with self.subTest(code=code):
                r, calls = self.run_provider(nba, headers=headers)
                self.assert_cause(r, 'schedule_quota', code); self.assertEqual(len(calls), 1)
                self.assertNotIn('quota_limit', r)

    def test_sharp_quota_failure_identifies_account_or_events_without_extra_calls(self):
        for events in (False, True):
            r, calls = self.run_provider(sharp, headers={}, event_failure=events)
            self.assert_cause(r, 'schedule_quota' if events else 'account_quota', 'quota_headers_missing')
            self.assertEqual(len(calls), 2 if events else 1)

    def test_transport_and_json_exceptions_are_distinct_without_raw_text(self):
        for provider in (nba, sharp):
            prefix = 'schedule' if provider is nba else 'account'
            r, _ = self.run_provider(provider, transport=True)
            self.assert_cause(r, prefix + '_request', 'transport_failed')
            r, _ = self.run_provider(provider, invalid_json=True)
            self.assert_cause(r, prefix + '_json', 'json_invalid')
        r, calls = self.run_provider(sharp, invalid_json=True, event_failure=True)
        self.assert_cause(r, 'schedule_json', 'json_invalid'); self.assertEqual(len(calls), 2)

    def test_sharp_rejected_fields_explain_the_stop_without_echoing_values(self):
        for field, value, code in [
            ('id', 'https://' + KEY, 'sharp_identity_ambiguous'),
            ('league', KEY, 'sharp_scope_changed'),
            ('home_team', KEY, 'sharp_participant_unverified'),
            ('season_type', KEY, 'sharp_phase_unrecognized'),
            ('start_time', KEY, 'sharp_start_invalid'),
            ('start_time', '2020-01-01T00:00:00Z', 'sharp_date_outside_bounds'),
            ('id', KEY, 'sharp_credential_reflected'),
        ]:
            with self.subTest(field=field, code=code):
                p = sharp_payload(); p['data'][0][field] = value
                r, calls = self.run_provider(sharp, payload=p)
                stage = 'credential_check' if code == 'sharp_credential_reflected' else 'schedule_validation'
                self.assert_cause(r, stage, code); self.assertEqual(len(calls), 2)

    def test_sharp_page_and_update_failures_are_distinct(self):
        for change, code in [
            (lambda p: p['pagination'].update(count=99), 'sharp_page_mismatch'),
            (lambda p: p['pagination'].update(has_more=True), 'sharp_page_state_changed'),
            (lambda p: p.update(updated_at=KEY), 'sharp_updated_invalid'),
            (lambda p: p.update(updated_at='2020-01-01T00:00:00Z'), 'sharp_updated_stale'),
            (lambda p: p.update(errors={'message': KEY}), 'sharp_provider_rejected'),
            (lambda p: p.update(data=[None]), 'sharp_row_invalid'),
        ]:
            p = sharp_payload(); change(p)
            r, _ = self.run_provider(sharp, payload=p)
            self.assert_cause(r, 'schedule_validation', code)

    def test_nba_query_and_participant_failures_are_distinct(self):
        for change, code in [
            (lambda p: p.update(errors={'message': KEY}), 'nba_provider_rejected'),
            (lambda p: p.update(parameters={'season': KEY}), 'nba_query_changed'),
            (lambda p: p['response'][0].update(season=2025), 'nba_identity_changed'),
            (lambda p: p['response'][0].update(date={'start': KEY}), 'nba_start_invalid'),
            (lambda p: p['response'][0]['teams']['home'].update(name=KEY), 'nba_participant_unverified'),
        ]:
            p = nba_payload(); change(p)
            r, _ = self.run_provider(nba, payload=p)
            self.assert_cause(r, 'schedule_validation', code)

    def test_empty_results_stay_unavailable_and_do_not_establish_out_of_season(self):
        for provider, p, code in (
            (nba, {**nba_payload(), 'results': 0, 'response': []}, 'nba_rows_empty'),
            (sharp, {**sharp_payload(), 'data': [], 'meta': {'store': {'reason': KEY}}}, 'sharp_rows_empty'),
        ):
            r, _ = self.run_provider(provider, payload=p)
            self.assert_cause(r, 'schedule_validation', code)
            self.assertNotIn('season_status', r)

    def test_failure_is_preserved_through_cooldown_and_clock_rollback(self):
        for provider in (nba, sharp):
            failed, _ = self.run_provider(provider, headers={})
            for now in (NOW - dt.timedelta(hours=1), NOW, NOW + dt.timedelta(hours=23, minutes=59)):
                r, calls = self.run_provider(provider, previous=failed, now=now)
                self.assertEqual(calls, []); self.assertEqual(r['requests_this_run'], 0)
                for field in ('errors', 'preflight_diagnostic', 'api_attempted_at', 'checked_at'):
                    self.assertEqual(r[field], failed[field])
            # A permitted later success must not inherit the old failure.
            p = nba_payload() if provider is nba else sharp_payload()
            if provider is nba:
                p['response'][0]['date']['start'] = '2026-11-04T01:30:00Z'
            else:
                p['updated_at'] = (NOW + dt.timedelta(hours=24)).isoformat()
                p['data'][0]['start_time'] = '2026-11-04T01:30:00Z'
            r, calls = self.run_provider(provider, payload=p, previous=failed, now=NOW + dt.timedelta(hours=24))
            self.assertEqual(len(calls), 1 if provider is nba else 2)
            self.assertNotIn('preflight_diagnostic', r)
            self.assertIn('preflight_evidence', r)

    def test_legacy_live_failures_survive_cooldown_without_guessing_their_causes(self):
        for provider, code in ((nba, 'legacy_nba_quota_unverified'), (sharp, 'legacy_sharp_validation_failed')):
            previous = {'api_attempted_at': NOW.isoformat(), 'errors': [ERRORS[code]], 'api_http_status': 200}
            r, calls = self.run_provider(provider, previous=previous)
            self.assert_cause(r, 'legacy', code); self.assertEqual(calls, [])

    def test_untrusted_saved_diagnostics_are_not_copied(self):
        for diagnostic in (
            {'version': 1, 'stage': KEY, 'code': 'json_invalid'},
            {'version': 1, 'stage': 'schedule_json', 'code': KEY},
            {'version': 1, 'stage': [], 'code': {}},
            {'version': True, 'stage': 'schedule_json', 'code': 'json_invalid'},
            {'version': 2, 'stage': 'schedule_json', 'code': 'json_invalid'},
        ):
            for provider in (nba, sharp):
                previous = {'api_attempted_at': NOW.isoformat(), 'preflight_diagnostic': diagnostic, 'errors': [KEY]}
                r, calls = self.run_provider(provider, previous=previous)
                self.assertNotIn('preflight_diagnostic', r); self.assertEqual(calls, [])

    def test_unexpected_shapes_fail_closed_without_exception_contents(self):
        p = nba_payload(); p['response'][0]['teams'] = [KEY]
        r, _ = self.run_provider(nba, payload=p)
        self.assert_cause(r, 'schedule_validation', 'validation_unexpected')
        p = sharp_payload(); p['data'][0]['league'] = [KEY]
        r, _ = self.run_provider(sharp, payload=p)
        self.assert_cause(r, 'schedule_validation', 'validation_unexpected')

    def test_valid_receipt_roundtrip_and_zero_remaining_keep_existing_behavior(self):
        for provider, headers in (
            (nba, {'X-RateLimit-Requests-Limit': '100', 'X-RateLimit-Requests-Remaining': '0'}),
            (sharp, {'x-ratelimit-limit': '12', 'x-ratelimit-remaining': '0'}),
        ):
            first, _ = self.run_provider(provider, headers=headers, event_failure=provider is sharp)
            self.assertIn('preflight_evidence', first)
            self.assertNotIn('preflight_diagnostic', first)
            r, calls = self.run_provider(provider, previous=first)
            self.assertEqual(calls, []); self.assertEqual(r['preflight_evidence'], first['preflight_evidence'])

    def test_sharp_exhausted_account_allowance_stops_before_event_request(self):
        r, calls = self.run_provider(sharp, headers={'X-RateLimit-Limit': '12', 'X-RateLimit-Remaining': '0'})
        self.assert_cause(r, 'account_quota', 'quota_exhausted')
        self.assertEqual(len(calls), 1)
