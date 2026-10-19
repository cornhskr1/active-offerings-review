"""Synthetic, offline regressions for the inactive Jolpica race-only adapter.

No retained provider payloads, live HTTP, activation, or catalog writes are used.
The real-sample replay and UI integration are separate acceptance evidence.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import jolpica_f1_schedule as adapter

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def race(**updates):
    row = {
        'season': '2026', 'round': '20', 'raceName': 'Synthetic Grand Prix',
        'date': '2026-10-23', 'time': '19:00:00Z',
        'Circuit': {'circuitId': 'synthetic', 'circuitName': 'Synthetic Circuit',
                    'Location': {'locality': 'Example City', 'country': 'Example Country'}},
    }
    row.update(updates)
    return row


def payload(*rows, season='2026'):
    rows = list(rows) if rows else [race()]
    return {'MRData': {'series': 'f1', 'offset': '0', 'limit': '100',
                       'total': str(len(rows)),
                       'RaceTable': {'season': season, 'Races': rows}}}


def response(data=None, code=200, **updates):
    result = {'status_code': code, 'headers': {}, 'payload': data or payload(), 'body_bytes': 1000}
    result.update(updates)
    return result


class JolpicaScheduleTests(unittest.TestCase):
    def setUp(self):
        # Even an accidental default HTTP implementation cannot reach a provider.
        self.socket_trap = patch('socket.socket.connect', side_effect=AssertionError('network forbidden'))
        self.http_trap = patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden'))
        self.socket_trap.start()
        self.http_trap.start()
        self.addCleanup(self.socket_trap.stop)
        self.addCleanup(self.http_trap.stop)

    def normalize(self, data=None, now=NOW, observed=None, window=None):
        start, end = window or adapter.review_window(now)
        return adapter.normalize_races(data or payload(), observed or now, start, end, now=now)

    def collect(self, data=None, previous=None, now=NOW, **updates):
        transport = Mock(return_value=response(data, **updates))
        result = adapter.collect_schedule(previous or {}, now, get=transport)
        transport.assert_called_once_with(adapter.ENDPOINT, timeout=30, allow_redirects=False,
                                          max_bytes=adapter.MAX_BYTES)
        return result

    def test_race_sessions_never_become_events(self):
        row = race(**{name: {'date': '2026-10-22', 'time': '12:00:00Z'}
                      for name in ('FirstPractice', 'SecondPractice', 'ThirdPractice',
                                   'Qualifying', 'Sprint', 'SprintQualifying')})
        result = self.normalize(payload(row))
        self.assertEqual(1, len(result['events']))
        self.assertEqual('Synthetic Grand Prix', result['events'][0]['name'])
        self.assertEqual(1, result['source_health']['season_rows'])

    def test_explicit_utc_and_central_dst_transition(self):
        now = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        rows = [race(round='1', date='2026-11-01', time='06:30:00Z'),
                race(round='2', date='2026-11-01', time='07:30:00Z')]
        events = self.normalize(payload(*rows), now=now)['events']
        local = [adapter.aware(e['start_time']).astimezone(ZoneInfo('America/Chicago')) for e in events]
        self.assertEqual([1, 1], [d.hour for d in local])
        self.assertEqual([timedelta(hours=-5), timedelta(hours=-6)], [d.utcoffset() for d in local])
        self.assertEqual([0, 1], [d.fold for d in local])

    def test_naive_timestamps_rejected(self):
        for kwargs in ({'observed_at': NOW.replace(tzinfo=None)},
                       {'window_start': NOW.replace(tzinfo=None)},
                       {'window_end': NOW.replace(tzinfo=None)}, {'now': NOW.replace(tzinfo=None)}):
            args = dict(payload=payload(), observed_at=NOW, window_start=NOW,
                        window_end=NOW + timedelta(days=8), now=NOW)
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                adapter.normalize_races(**args)

    def test_date_only_has_no_midnight_guess(self):
        row = race()
        del row['time']
        event = self.normalize(payload(row))['events'][0]
        self.assertTrue(event['date_only'])
        self.assertIsNone(event['start_time'])
        self.assertEqual('2026-10-23', event['date'])

    def test_invalid_dates_times_and_windows_fail_closed(self):
        for update in ({'date': '2026-02-30'}, {'date': '2026-1-23'},
                       {'time': '25:00:00Z'}, {'time': '19:00:00'},
                       {'time': '19:00:00-05:00'}, {'time': ''}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.normalize(payload(race(**update)))
        with self.assertRaises(ValueError):
            self.normalize(window=(NOW, NOW))

    def test_future_observation_rejected(self):
        with self.assertRaises(ValueError):
            self.normalize(observed=NOW + timedelta(seconds=1))

    def test_unknown_age_entrants_status_and_update_not_invented(self):
        event = self.normalize()['events'][0]
        self.assertEqual('UNKNOWN', event['status'])
        self.assertIsNone(event['source_updated_at'])
        self.assertFalse(event['coverage_complete'])
        for key in ('entrants', 'participants', 'age', 'adult_clearance', 'u18_warning', 'state'):
            self.assertNotIn(key, event)
        self.assertEqual('Example Country', event['country'])
        self.assertEqual('Example City', event['locality'])

    def test_empty_truncated_malformed_payloads_preserve_last_good(self):
        previous = self.collect()
        empty = payload()
        empty['MRData']['RaceTable']['Races'] = []
        empty['MRData']['total'] = '0'
        truncated = payload()
        truncated['MRData']['total'] = '2'
        malformed = payload()
        malformed['MRData']['RaceTable']['Races'] = [None]
        for data in (empty, truncated, malformed, {'broken': True}):
            with self.subTest(data=data):
                result = self.collect(data, previous=previous, now=NOW + timedelta(days=1))
                self.assertEqual(previous['events'][0]['id'], result['events'][0]['id'])
                self.assertEqual(previous['events'][0]['observed_at'], result['events'][0]['observed_at'])
                self.assertTrue(result['events'][0]['source_stale'])
                self.assertEqual('UNKNOWN', result['events'][0]['status'])
                self.assertEqual('stale', result['source_health']['status'])
        self.assertFalse(previous['events'][0]['source_stale'])

    def test_identical_duplicates_dedupe(self):
        self.assertEqual(1, len(self.normalize(payload(race(), race()))['events']))

    def test_conflicting_round_records_fail_closed(self):
        other = race()
        other['Circuit']['circuitId'] = 'different'
        for row in (other, race(date='2026-10-24'), race(raceName='Changed Name')):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.normalize(payload(race(), row))

    def test_reschedule_stable_identity_updates_without_completed_status(self):
        previous = self.collect()
        result = self.collect(payload(race(date='2026-10-24')), previous, NOW + timedelta(days=1))
        self.assertEqual(1, len(result['events']))
        self.assertEqual(previous['events'][0]['id'], result['events'][0]['id'])
        self.assertEqual('2026-10-24', result['events'][0]['date'])
        self.assertEqual('UNKNOWN', result['events'][0]['status'])
        self.assertFalse(result['events'][0]['source_stale'])

    def test_changed_circuit_across_updates_is_review_conflict(self):
        previous = self.collect()
        row = race()
        row['Circuit']['circuitId'] = 'new_circuit'
        result = self.collect(payload(row), previous, NOW + timedelta(days=1))
        self.assertEqual('identity_conflict', result['source_health']['reason'])
        self.assertEqual(previous['events'][0]['id'], result['events'][0]['id'])
        self.assertTrue(result['events'][0]['source_stale'])

    def test_omission_does_not_cancel_prior_future_race(self):
        previous = self.collect()
        result = self.collect(payload(race(round='21')), previous, NOW + timedelta(days=1))
        self.assertEqual(2, len(result['events']))
        old = next(e for e in result['events'] if e['round'] == 20)
        self.assertTrue(old['source_stale'])
        self.assertEqual('UNKNOWN', old['status'])

    def test_season_rollover_preserves_prior_future_rows_stale(self):
        before = datetime(2026, 12, 30, 12, tzinfo=timezone.utc)
        previous = self.collect(payload(race(date='2026-12-31', time='23:00:00Z')), now=before)
        result = self.collect(payload(race(season='2027', round='1', date='2027-01-03'), season='2027'),
                              previous, before + timedelta(days=1))
        self.assertEqual(adapter.SOURCE, result['source_id'])
        self.assertEqual({'2026', '2027'}, {e['season'] for e in result['events']})
        self.assertTrue(next(e for e in result['events'] if e['season'] == '2026')['source_stale'])

    def test_old_season_response_is_not_fresh_current_year_availability(self):
        now = datetime(2027, 1, 1, 12, tzinfo=timezone.utc)
        result = self.collect(payload(race(date='2026-12-01')), now=now)
        self.assertIn(result['source_health']['status'], ('stale', 'paused', 'unknown'))
        self.assertNotEqual('race_schedule_only', result['source_health']['reason'])

    def test_only_exact_f1_identity_and_allowlisted_fields(self):
        row = race(url='https://unrelated.invalid', image='https://unrelated.invalid/img',
                   catalog_identity_key='other', status='COMPLETED', entrants=['invented'])
        event = self.normalize(payload(row))['events'][0]
        self.assertEqual(adapter.IDENTITY, event['catalog_identity_key'])
        self.assertEqual(adapter.ENDPOINT, event['source_url'])
        for key in ('url', 'image', 'entrants'):
            self.assertNotIn(key, event)
        wrong_series = payload()
        wrong_series['MRData']['series'] = 'f2'
        with self.assertRaises(ValueError):
            self.normalize(wrong_series)

    def test_license_notice_survives_fresh_cached_and_failed_updates(self):
        fresh = self.collect()
        cached = adapter.collect_schedule(fresh, NOW + timedelta(hours=1), get=Mock(side_effect=AssertionError))
        failed = self.collect(previous=fresh, now=NOW + timedelta(days=1), code=500)
        for result in (fresh, cached, failed):
            self.assertEqual('CC-BY-NC-SA-4.0', result['license']['id'])
            for key in ('attribution', 'source_url', 'url', 'terms_url', 'changes', 'notice'):
                self.assertTrue(result['license'][key])
            self.assertEqual('isolated_jolpica_f1_only', result['dataset_scope'])
            for event in result['events']:
                self.assertEqual(result['license']['id'], event['license_id'])

    def test_parser_is_pure_and_does_not_mutate_inputs_or_license(self):
        data = payload()
        snapshot = deepcopy(data)
        result = self.normalize(data)
        self.assertEqual(snapshot, data)
        result['license']['id'] = 'changed'
        self.assertEqual('CC-BY-NC-SA-4.0', adapter.LICENSE['id'])

    def test_no_default_transport_or_activation(self):
        with self.assertRaisesRegex(ValueError, 'transport_not_configured'):
            adapter.collect_schedule({}, NOW)

    def test_daily_cache_retains_original_observation(self):
        previous = self.collect()
        trap = Mock(side_effect=AssertionError('unexpected poll'))
        cached = adapter.collect_schedule(previous, NOW + timedelta(hours=23), get=trap)
        trap.assert_not_called()
        self.assertEqual(previous['events'], cached['events'])
        self.assertEqual(previous['collector_state'], cached['collector_state'])
        self.assertIsNot(previous, cached)
        self.assertEqual(adapter.stamp(NOW), cached['events'][0]['observed_at'])
        self.collect(previous=previous, now=NOW + timedelta(hours=24))

    def test_denial_redirect_halt_never_tries_an_alternate_route(self):
        for code in (301, 302, 307, 401, 403):
            with self.subTest(code=code):
                denied = self.collect(code=code)
                self.assertTrue(denied['collector_state']['halted'])
                trap = Mock(side_effect=AssertionError('retry after denial'))
                result = adapter.collect_schedule(denied, NOW + timedelta(days=10), get=trap)
                trap.assert_not_called()
                self.assertEqual(denied['collector_state'], result['collector_state'])
                self.assertEqual('paused', result['source_health']['status'])

    def test_rate_limit_and_error_cooldown(self):
        for code in (429, 500, 503):
            with self.subTest(code=code):
                failed = self.collect(code=code)
                trap = Mock(side_effect=AssertionError('early retry'))
                adapter.collect_schedule(failed, NOW + timedelta(hours=23), get=trap)
                trap.assert_not_called()
                self.assertFalse(failed['collector_state']['halted'])
                self.collect(previous=failed, now=NOW + timedelta(hours=24))

    def test_transport_exception_and_size_limits_fail_closed(self):
        previous = self.collect()
        for size in (-1, adapter.MAX_BYTES + 1, True, None):
            with self.subTest(size=size):
                result = self.collect(previous=previous, now=NOW + timedelta(days=1), body_bytes=size)
                self.assertEqual('response_size_hold', result['source_health']['reason'])
                self.assertTrue(result['events'][0]['source_stale'])
        transport = Mock(side_effect=TimeoutError('synthetic timeout'))
        result = adapter.collect_schedule(previous, NOW + timedelta(days=1), get=transport)
        self.assertEqual(1, transport.call_count)
        self.assertEqual('invalid_or_unavailable_schedule', result['source_health']['reason'])
        self.assertTrue(result['events'][0]['source_stale'])

    def test_invalid_pagination_mixed_season_and_oversize_rejected(self):
        cases = []
        for key, value in (('offset', '1'), ('total', '2')):
            data = payload()
            data['MRData'][key] = value
            cases.append(data)
        cases.extend([payload(race(season='2025')), payload(*[race(round=str(n + 1)) for n in range(101)])])
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.normalize(data)

    def test_reschedule_outside_window_does_not_retain_old_date(self):
        previous = self.collect()
        result = self.collect(payload(race(date='2026-11-10')), previous, NOW + timedelta(days=1))
        self.assertEqual([], result['events'])
        self.assertEqual('partial', result['source_health']['status'])

    def test_retry_after_longer_than_daily_cooldown(self):
        failed = self.collect(code=429, headers={'Retry-After': '172800'})
        self.assertEqual(adapter.stamp(NOW + timedelta(days=2)), failed['collector_state']['next_fetch_at'])
        trap = Mock(side_effect=AssertionError('Retry-After must be honored'))
        adapter.collect_schedule(failed, NOW + timedelta(hours=47), get=trap)
        trap.assert_not_called()
        self.collect(previous=failed, now=NOW + timedelta(days=2))

    def test_cached_view_expires_past_rows_without_new_observation(self):
        previous = self.collect(payload(race(date='2026-10-19', time='19:00:00Z')))
        trap = Mock(side_effect=AssertionError('cache must not poll'))
        result = adapter.collect_schedule(previous, NOW + timedelta(hours=23), get=trap)
        trap.assert_not_called()
        self.assertEqual([], result['events'])
        self.assertEqual(previous['observed_at'], result['observed_at'])
        self.assertEqual(1, len(previous['events']))

    def test_cached_extra_provider_metadata_is_stripped(self):
        previous = self.collect()
        previous['image'] = 'https://unrelated.invalid'
        previous['events'][0]['entrants'] = ['invented']
        previous['events'][0]['image'] = 'https://unrelated.invalid'
        trap = Mock(side_effect=AssertionError('cache must not poll'))
        result = adapter.collect_schedule(previous, NOW + timedelta(hours=1), get=trap)
        trap.assert_not_called()
        self.assertNotIn('image', result)
        self.assertNotIn('image', result['events'][0])
        self.assertNotIn('entrants', result['events'][0])

    def test_invalid_cached_identity_or_future_observation_blocks_transport(self):
        for change in ('identity', 'observed', 'cooldown', 'license', 'status'):
            previous = self.collect()
            if change == 'identity':
                previous['events'][0]['catalog_identity_key'] = 'other'
            elif change == 'observed':
                previous['events'][0]['observed_at'] = adapter.stamp(NOW + timedelta(days=2))
            elif change == 'cooldown':
                previous['collector_state']['next_fetch_at'] = adapter.stamp(NOW)
            elif change == 'status':
                previous['events'][0]['status'] = 'COMPLETED'
            else:
                previous['license']['id'] = 'proprietary'
            trap = Mock(side_effect=AssertionError('invalid cache must not poll'))
            with self.subTest(change=change), self.assertRaises(ValueError):
                adapter.collect_schedule(previous, NOW + timedelta(days=1), get=trap)
            trap.assert_not_called()


if __name__ == '__main__':
    unittest.main()


class SeasonConsistencyTests(unittest.TestCase):
    def test_contradictory_season_date_rejected(self):
        now = datetime(2026, 12, 31, 12, tzinfo=timezone.utc)
        start, end = adapter.review_window(now)
        with self.assertRaisesRegex(ValueError, 'season_date_conflict'):
            adapter.normalize_races(payload(race(date='2027-01-02')), now, start, end)
