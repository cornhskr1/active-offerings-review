from copy import deepcopy
from pathlib import Path
import unittest
from scripts.official_historical_school_result import parse_result, collect_result, EXPECTED, UID, SOURCE_ID, SPECS, collect_results

BODY = (Path(__file__).parent/'fixtures/nebraska-illinois-result-20261109.html').read_text()
NOW = '2026-11-09T07:00:00Z'
class Response:
    status_code = 200
    def __init__(self, text): self.text = text
class HistoricalResultTests(unittest.TestCase):
    def prior(self):
        return {**EXPECTED, 'uid': UID, 'status': 'REMOVED', 'source_stale': True,
                'source_id': 'official-nebraska-football'}
    def test_exact_completed_fact_no_score_or_clock_inferred(self):
        row = parse_result(BODY)
        self.assertEqual(row['status'], 'COMPLETED')
        self.assertEqual(row['historical_calendar_uid'], UID)
        self.assertEqual(row['source_id'], SOURCE_ID)
        self.assertNotIn('score', row)
        self.assertIsNone(row['start_time'])
    def test_drift_duplicates_cancellations_and_unfinished_fail(self):
        for old, new in [('Football 2026', 'Football 2027'), ('Nov 6', 'Nov 7'),
                         ('Illinois', 'Oregon'), ('Champaign, Ill.', 'Lincoln, Neb.'),
                         ('Away', 'Home'), (' L ', ' N '), ('Loss', 'Canceled'),
                         ('21839', '21840')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                parse_result(BODY.replace(old, new))
        with self.assertRaises(ValueError): parse_result(BODY + BODY)
    def test_suspended_abandoned_results_never_become_completed_evidence(self):
        for spec, fixture in zip(SPECS, ('nebraska-illinois-result-20261109.html',
                                       'nebraska-oregon-result-20261109.html')):
            body = (Path(__file__).parent/'fixtures'/fixture).read_text()
            prior = {**spec['expected'], 'uid': spec['uid'],
                     'source_id': spec['calendar_source_id'], 'status': spec['original_statuses'][0]}
            for marker in ('Suspended', 'SUSPEND', 'Suspension', 'Abandoned',
                           'ABANDON', 'Abandonment', 'Cancelled', 'Canceled',
                           'Cancellation', 'Postponed', 'Postponement'):
                bad = body.replace('<div class="schedule-event-item">',
                                   '<div class="schedule-event-item"><span>' + marker + '</span>')
                with self.subTest(source=spec['source_id'], marker=marker):
                    with self.assertRaises(ValueError): parse_result(bad, spec)
                    rows, status, cache = collect_result([prior], {}, NOW,
                                                        lambda *a, **k: Response(bad), spec)
                    self.assertFalse(status['ok'])
                    self.assertEqual(rows, [])
                    self.assertNotIn('fetched_at', cache)

    def test_provenance_cache_and_removed_record_untouched(self):
        old = self.prior(); before = deepcopy(old)
        rows, status, cache = collect_result([old], {}, NOW, lambda *a, **k: Response(BODY))
        self.assertEqual(old, before)
        self.assertTrue(status['ok'])
        self.assertEqual(rows[0]['historical_calendar_source_id'], old['source_id'])
        def trap(*a, **k): raise AssertionError('Request before TTL')
        again, state, saved = collect_result([old], cache, '2026-11-10T07:00:00Z', trap)
        self.assertEqual(saved, cache); self.assertTrue(state['ok'])
        failed, state, saved = collect_result([old], cache, '2026-11-12T07:00:00Z', lambda *a, **k: Response('bad'))
        self.assertFalse(state['ok']); self.assertTrue(failed[0]['source_stale'])
        self.assertEqual(saved['fetched_at'], cache['fetched_at'])
    def test_reconciliation_failures_never_fetch(self):
        def trap(*a, **k): raise AssertionError('Ineligible event fetched')
        for key, value in [('status','CANCELLED'), ('status','CONFIRMED'), ('sport','Volleyball'),
                           ('date','2026-11-07'), ('source_id','other'), ('location','Lincoln, Neb.')]:
            rows, state, _ = collect_result([{**self.prior(), key:value}], {}, NOW, trap)
            self.assertFalse(state['ok']); self.assertEqual(rows, [])
        for old in ([], [self.prior(), self.prior()]):
            rows, state, _ = collect_result(old, {}, NOW, trap)
            self.assertEqual(rows, [])
        for now in ('2026-11-06T07:00:00Z', '2027-02-05T07:00:00Z'):
            rows, state, _ = collect_result([self.prior()], {}, now, trap)
            self.assertEqual(rows, [])

    def test_oregon_exact_reviewed_result_and_full_venue_provenance(self):
        body = (Path(__file__).parent/'fixtures/nebraska-oregon-result-20261109.html').read_text()
        spec = SPECS[1]
        row = parse_result(body, spec)
        self.assertEqual(row['sport'], 'Volleyball')
        self.assertEqual(row['location'], 'Eugene, Ore.')
        self.assertEqual(row['official_result_location'], 'Eugene, Ore. / Matthew Knight Arena')
        prior = {**spec['expected'], 'uid': spec['uid'], 'source_id': spec['calendar_source_id'], 'status': 'CONFIRMED'}
        before = deepcopy(prior)
        rows, status, cache = collect_result([prior], {}, NOW, lambda *a, **k: Response(body), spec)
        self.assertTrue(status['ok']); self.assertEqual(rows[0]['status'], 'COMPLETED')
        self.assertEqual(prior, before)
        for bad in ('Eugene, Ore. / Other Arena', 'Lincoln, Neb.'):
            with self.assertRaises(ValueError): parse_result(body.replace(spec['official_location'], bad), spec)
        with self.assertRaises(ValueError): parse_result(body, SPECS[0])

    def test_oregon_rolling_removal_preserves_separate_historical_verification(self):
        spec = SPECS[1]
        body = (Path(__file__).parent/'fixtures/nebraska-oregon-result-20261109.html').read_text()
        prior = {**spec['expected'], 'uid': spec['uid'],
                 'source_id': spec['calendar_source_id'], 'status': 'CONFIRMED'}
        rows, state, saved = collect_result([prior], {}, NOW, lambda *a, **k: Response(body), spec)
        self.assertTrue(state['ok'])
        def trap(*a, **k): raise AssertionError('No request during retained TTL or ineligible status')
        for status in ('SCHEDULED', 'REMOVED'):
            changed = {**prior, 'status': status, 'source_stale': status == 'REMOVED'}
            before = deepcopy(changed)
            carried, state, cache = collect_result([changed], saved, '2026-11-10T07:00:00Z', trap, spec)
            self.assertTrue(state['ok']); self.assertEqual(len(carried), 1)
            self.assertEqual(carried[0]['uid'], rows[0]['uid'])
            self.assertEqual(carried[0]['fetched_at'], rows[0]['fetched_at'])
            self.assertEqual(changed, before)
        for status in ('CANCELLED', 'CANCELED', 'POSTPONED', 'SUSPENDED', 'ABANDONED', 'COMPLETED'):
            carried, state, cache = collect_result([{**prior, 'status': status}], saved,
                                                   '2026-11-10T07:00:00Z', trap, spec)
            self.assertEqual(carried, []); self.assertFalse(state['ok'])
            if status == 'COMPLETED': self.assertEqual(cache, {})
