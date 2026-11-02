import ast
import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from scripts.sharp_api_preflight import collect, inspect_events, BASE, SOURCE_ID, PARAMS
NOW = dt.datetime(2026, 11, 2, 4, tzinfo=dt.timezone.utc)
KEY = "synthetic-private-sharp-key"
SOURCE = {"id": SOURCE_ID, "source_type": SOURCE_ID, "endpoint": BASE + "/events", "coverage_status": "pending-fixture-review"}

def payload():
    return {"data": [{"id": "nba_bos_lal_20261103", "uuid": "12345678abcdef90", "league": "nba", "sport": "basketball", "home_team": "Boston Celtics", "away_team": "Los Angeles Lakers", "start_time": "2026-11-03T01:30:00Z", "season_type": "Regular Season", "status": "upcoming", "is_live": False, "personnel": "DO NOT RETAIN", "books": ["DO NOT RETAIN"], "external_ids": {"key": KEY}}], "pagination": {"limit": 200, "offset": 0, "count": 1, "total": 1, "has_more": False, "next_offset": None}, "updated_at": NOW.isoformat()}

class Response:
    status_code = 200
    headers = {"X-RateLimit-Limit": "12", "X-RateLimit-Remaining": "10"}
    def __init__(self, data): self.data = data
    def json(self): return self.data

def account():
    return {"data": {"key_id": KEY, "tier": "free", "features": ["schedule", "odds"], "rate_limit": {"requests_per_minute": 12, "max_books": 2}}}

class Preflight(unittest.TestCase):
    def run_check(self, event=None, acct=None, previous=None, key=KEY, source=None, now=NOW, statuses=None, headers=None):
        calls = []
        def get(url, **kwargs):
            calls.append((url, kwargs))
            response = Response(copy.deepcopy((acct or account()) if url.endswith('/account') else (event or payload())))
            if statuses: response.status_code = statuses[len(calls) - 1]
            if headers is not None: response.headers = headers
            return response
        result = collect(source or SOURCE, previous or {}, now, key, get)
        self.assertNotIn(KEY, json.dumps(result)); self.assertNotIn('DO NOT RETAIN', json.dumps(result))
        return result, calls

    def test_two_requests_only_schedule_evidence_never_events(self):
        r, calls = self.run_check()
        self.assertEqual(len(calls), 2); self.assertFalse(r['ok']); self.assertEqual(r['events'], 0)
        self.assertTrue(r['review_required']); self.assertFalse(r['coverage_complete'])
        self.assertEqual(r['preflight_evidence']['league_counts'], {'nba': 1, 'nfl': 0})
        self.assertEqual(calls[1][1]['params'], PARAMS)
        for url, kw in calls:
            self.assertTrue(url.startswith(BASE + '/')); self.assertFalse(kw['allow_redirects']); self.assertEqual(kw['timeout'], 25)
            self.assertEqual(kw['headers'], {'X-API-Key': KEY}); self.assertNotIn(KEY, url)

    def test_missing_secret_changed_configuration_and_bad_clock_no_network(self):
        for key in ('', ' key ', 'key\nvalue'):
            self.assertEqual(self.run_check(key=key)[1], [])
        for field, val in [('endpoint', 'https://foreign.test/events'), ('coverage_status', 'active'), ('source_type', 'unknown')]:
            self.assertEqual(self.run_check(source={**SOURCE, field: val})[1], [])
        with self.assertRaises(ValueError): self.run_check(now=NOW.replace(tzinfo=None))

    def test_saved_receipt_suppresses_and_preserves_observation_date(self):
        first, _ = self.run_check()
        for now in (NOW, NOW - dt.timedelta(hours=1), NOW + dt.timedelta(hours=23, minutes=59)):
            r, calls = self.run_check(previous=first, now=now)
            self.assertEqual(calls, []); self.assertEqual(r['checked_at'], first['checked_at'])
            self.assertEqual(r['preflight_evidence'], first['preflight_evidence'])
        self.assertEqual(len(self.run_check(previous=first, now=NOW + dt.timedelta(hours=24))[1]), 2)
        self.assertEqual(self.run_check(previous={'api_attempted_at': 'bad'})[1], [])

    def test_paid_or_wrong_feature_account_stops_before_events(self):
        for field, val in [('tier', 'pro'), ('features', ['odds']), ('rate_limit', {'requests_per_minute': 12, 'max_books': 25})]:
            a = account(); a['data'][field] = val
            r, calls = self.run_check(acct=a); self.assertEqual(len(calls), 1); self.assertNotIn('preflight_evidence', r)

    def test_access_redirect_quota_no_retry_or_secret_in_errors(self):
        for status in (302, 401, 403, 429, 500):
            r, calls = self.run_check(statuses=[status]); self.assertEqual(len(calls), 1); self.assertNotIn('preflight_evidence', r)
            r, calls = self.run_check(statuses=[200, status]); self.assertEqual(len(calls), 2); self.assertNotIn('preflight_evidence', r)
        for headers in ({}, {'X-RateLimit-Limit': '300', 'X-RateLimit-Remaining': '299'}, {'X-RateLimit-Limit': '12', 'X-RateLimit-Remaining': '12'}):
            r, calls = self.run_check(headers=headers); self.assertEqual(len(calls), 1); self.assertNotIn('preflight_evidence', r)
        def fail(*a, **kw): raise RuntimeError(KEY + ' raw-error-body')
        r = collect(SOURCE, {}, NOW, KEY, fail)
        self.assertEqual(r['requests_this_run'], 1); self.assertNotIn(KEY, json.dumps(r)); self.assertNotIn('raw-error-body', json.dumps(r))

    def test_changed_scope_identity_and_dates_reject_entire_evidence(self):
        cases = []
        for field, val in [('league', 'ncaab'), ('sport', 'tennis'), ('home_team', 'Under 18 Club'), ('status', 'live'), ('is_live', True), ('season_type', 'postseason'), ('start_time', '2026-11-03T01:30:00'), ('id', 'https://foreign.test'), ('uuid', None), ('start_time', '2025-11-03T01:30:00Z')]:
            x = payload(); x['data'][0][field] = val; cases.append(x)
        x = payload(); x['data'] *= 2; x['pagination'].update(count=2, total=2); cases.append(x)
        x = payload(); x['data'][0]['away_team'] = x['data'][0]['home_team']; cases.append(x)
        x = payload(); x['data'][0]['id'] = KEY; cases.append(x)
        for x in cases:
            r, calls = self.run_check(event=x); self.assertNotIn('preflight_evidence', r); self.assertEqual(len(calls), 2)

    def test_partial_page_is_explicit_and_never_follows_next_offset(self):
        x = payload(); x['pagination'].update(total=300, has_more=True, next_offset=200)
        r, calls = self.run_check(event=x)
        self.assertFalse(r['preflight_evidence']['sample_complete']); self.assertEqual(len(calls), 2)
        for field, val in [('count', 2), ('has_more', True), ('offset', 1), ('total', 0), ('next_offset', 200)]:
            x = payload(); x['pagination'][field] = val
            with self.assertRaises(ValueError): inspect_events(x, NOW)
        for stamp in ('2020-11-02T03:00:00Z', '2027-11-02T03:00:00Z'):
            x = payload(); x['updated_at'] = stamp
            with self.assertRaises(ValueError): inspect_events(x, NOW)

    def test_unknown_nfl_phase_preserved_as_unknown_and_input_not_mutated(self):
        x = payload(); x['data'][0].update(league='nfl', sport='football', home_team='Chicago Bears', away_team='Seattle Seahawks')
        del x['data'][0]['season_type']; before = copy.deepcopy(x)
        r = inspect_events(x, NOW)
        self.assertEqual(x, before); self.assertIsNone(r['schedule_preview'][0]['season_type'])
        self.assertEqual(r['phase_counts'], {'nfl:unknown': 1})

    def test_actual_driver_branch_only_adds_pending_diagnostic(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'scripts/refresh_global_schedule.py').read_text())
        branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == "source.get('source_type') == 'sharp-api-events-preflight'")
        calls = []
        class Requests:
            @staticmethod
            def get(url, **kwargs):
                calls.append(url); return Response(account() if url.endswith('/account') else payload())
        class OS:
            class environ:
                @staticmethod
                def get(name, default): return KEY if name == 'SHARP_API_KEY' else default
        env = {'source': SOURCE, 'previous_schedule': {'sources': []}, 'source_status': [], 'NOW_UTC': NOW, 'os': OS, 'requests': Requests, 'collect_sharp_api_preflight': collect, 'events': []}
        exec(compile(ast.Module(body=branch.body[:-1], type_ignores=[]), 'driver', 'exec'), env)
        self.assertEqual(len(calls), 2); self.assertEqual(env['events'], []); self.assertFalse(env['source_status'][0]['ok'])

    def test_config_has_no_usable_catalog_route(self):
        d = json.loads((Path(__file__).resolve().parents[1] / 'data/global-schedule-sources.json').read_text())
        s = next(x for x in d['sources'] if x['id'] == SOURCE_ID)
        self.assertEqual(s['coverage_status'], 'pending-fixture-review'); self.assertNotIn('scope_source_ids', s)
        self.assertEqual(s['endpoint'], BASE + '/events')
