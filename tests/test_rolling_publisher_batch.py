"""Shared advancement and fail-closed publication contract across six feeds."""
import datetime as dt
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rolling_publisher_batch import stage_timed_fixtures

TEXT = (ROOT / 'scripts/refresh_global_schedule.py').read_text()
KINDS = {
    'basketball-ar-lnb': 'official-arg-lnb-fixtures',
    'volleyball-italy-superlega': 'official-italy-volleyball-fixtures',
    'conmebol-soccer-uruguay-campeonato-femenino-women': 'official-auf-fixtures',
    'conmebol-soccer-uruguay-copa-uruguay-men': 'official-auf-fixtures',
    'combat-pfl-mena': 'official-pfl-event-calendar',
    'combat-pfl-africa': 'official-pfl-event-calendar',
}
NOW = dt.datetime(2026, 10, 18, 17, tzinfo=dt.timezone.utc)


def run_branch(source_id, rows, fetch_error=False):
    kind = KINDS[source_id]
    start = TEXT.index(f'    if source.get("source_type")=="{kind}":')
    end = TEXT.index('        continue\n    if ', start) + len('        continue\n')
    def get(*args, **kwargs):
        if fetch_error:
            raise RuntimeError('Publisher unavailable; no bypass')
        return SimpleNamespace(text='page', content=b'page', raise_for_status=lambda: None)
    def detail(page, card):
        row = rows[card['index']]
        if row.get('invalid'):
            raise ValueError('Publisher identity or date ambiguous')
        return {'title': row['id'], 'date': dt.date.fromisoformat(row['start_time'][:10]),
                'location': '', 'url': card['url']}
    ns = {'configured': [{'id': source_id, 'source_type': kind, 'endpoint': 'https://example.test/',
                         'league': 'Approved exact league', 'coverage_status': 'partial'}],
          'requests': SimpleNamespace(get=get, exceptions=SimpleNamespace(Timeout=TimeoutError)),
          'HEADERS': {}, 'datetime': dt, 'NOW_UTC': NOW, 'TODAY': NOW.date(),
          'END': dt.date(2026, 10, 25), 'TZ': ZoneInfo('America/Chicago'),
          'events': [], 'seen': set(), 'source_status': [], 'errors': [], 'count': 0,
          'stage_timed_fixtures': stage_timed_fixtures,
          'parse_arg_lnb_fixtures': lambda *a: rows, 'parse_superlega': lambda *a: rows,
          'parse_serie_a1': lambda *a: rows, 'parse_auf_fixtures': lambda *a, **kw: (rows, len(rows), 4),
          'PFL_EVENT_CACHE': {},
          'pfl_upcoming_links': lambda *a: [{'source_id': source_id, 'index': i,
              'url': f'https://pflmma.com/event/{i}'} for i in range(len(rows))],
          'pfl_verified_event': detail,
          'tournament_window_event': lambda source, sid, league, title, first, last, location, url:
              {'id': title, 'source_id': sid, 'start_time': first.isoformat()+'T05:00:00Z'}}
    exec(compile('for source in configured:\n'+TEXT[start:end], 'rolling-collector', 'exec'), ns)
    return ns['events'], ns['source_status'][0], ns['seen']


class RollingPublisherBatchTests(unittest.TestCase):
    def row(self, sid, ident='a', time='2026-10-24T16:30:00Z'):
        return {'id': ident, 'source_id': sid, 'start_time': time}

    def test_all_six_late_failure_is_atomic(self):
        for sid in KINDS:
            with self.subTest(source=sid):
                rows = [self.row(sid), {**self.row(sid, 'b', 'invalid'), 'invalid': True}]
                events, status, seen = run_branch(sid, rows)
                self.assertEqual([], events)
                self.assertEqual(set(), seen)
                self.assertFalse(status['ok'])
                self.assertEqual(0, status['events'])
                self.assertEqual('partial', status['coverage_status'])

    def test_all_six_fetch_denial_stays_explicit(self):
        for sid in KINDS:
            with self.subTest(source=sid):
                events, status, seen = run_branch(sid, [], fetch_error=True)
                self.assertEqual([], events)
                self.assertFalse(status['ok'])
                self.assertIn('unavailable', status['errors'][0])

    def test_timed_families_advance_window_and_deduplicate(self):
        for sid in list(KINDS)[:4]:
            with self.subTest(source=sid):
                future = self.row(sid, 'new-round', '2026-10-26T01:00:00Z')
                rows = [self.row(sid, 'elapsed', '2026-10-18T16:00:00Z'), future, future,
                        self.row(sid, 'outside', '2026-10-26T06:00:00Z')]
                events, status, _ = run_branch(sid, rows)
                self.assertEqual(['new-round'], [e['id'] for e in events])
                self.assertTrue(status['ok'])

    def test_timed_families_reject_wrong_source_naive_date_and_conflicting_duplicates(self):
        for sid in list(KINDS)[:4]:
            for bad in [self.row('another-competition'), self.row(sid, time='2026-10-24T16:30:00'),
                        {**self.row(sid), 'date_only': True}, {**self.row(sid), 'name': 'conflict'}]:
                with self.subTest(source=sid, bad=bad):
                    events, status, _ = run_branch(sid, [self.row(sid), bad])
                    self.assertEqual([], events)
                    self.assertFalse(status['ok'])

    def test_pfl_date_only_review_restrictions_survive(self):
        for sid in list(KINDS)[4:]:
            events, status, _ = run_branch(sid, [self.row(sid)])
            self.assertTrue(status['ok'])
            self.assertTrue(events[0]['date_only'])
            self.assertTrue(events[0]['requires_bout_review'])
            self.assertIn('participant ages need review', events[0]['status_detail'])


if __name__ == '__main__':
    unittest.main()
