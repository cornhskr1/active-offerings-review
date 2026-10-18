"""Exercise the actual collector branch without importing its network-running module."""
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
TEXT = (ROOT / 'scripts/refresh_global_schedule.py').read_text()
START = TEXT.index('    if source.get("source_type") in ("official-european-basketball-fixtures"')
END = TEXT.index('    if source.get("source_type")=="official-auf-fixtures":', START)
COLLECTOR = 'for source in configured:\n' + TEXT[START:END]

class BasketballCollectorTests(unittest.TestCase):
    def run_branch(self, fixtures, complete=True, european=False):
        source = {'id':'test', 'source_type': 'official-european-basketball-fixtures' if european else 'official-fiba-report-fixtures',
                  'endpoint':'https://example.invalid', 'coverage_end':'2027-01-13'}
        namespace = {
            'configured':[source], 'datetime':dt, 'HEADERS':{}, 'TZ':ZoneInfo('America/Chicago'),
            'NOW_UTC':dt.datetime(2026,10,18,14,tzinfo=dt.timezone.utc),
            'TODAY':dt.date(2026,10,18), 'END':dt.date(2026,10,25),
            'events':[], 'seen':set(), 'source_status':[], 'count':0, 'errors':[],
            'fetch_fiba_report_fixtures':lambda *args:(fixtures,{'review_window_complete':complete}),
            'validate_european_basketball_window':lambda *args:None,
            'parse_european_basketball_fixtures':lambda *args:fixtures,
            'requests':SimpleNamespace(get=lambda *args,**kwargs:SimpleNamespace(
                raise_for_status=lambda:None,json=lambda:{'total':224})),
        }
        exec(compile(COLLECTOR,'basketball-collector','exec'),namespace)
        return namespace['events'],namespace['source_status'][0]

    def test_literal_date_is_preserved_and_utc_is_filtered_in_central_time(self):
        fixtures=[{'id':'date','start_time':'2026-10-18','date_only':True},
                  {'id':'past','start_time':'2026-10-18T13:00:00Z'},
                  {'id':'next','start_time':'2026-10-26T03:00:00Z'},
                  {'id':'outside','start_time':'2026-10-26T06:00:00Z'}]
        events,status=self.run_branch(fixtures)
        self.assertEqual(['date','next'],[e['id'] for e in events])
        self.assertEqual('2026-10-18',events[0]['start_time'])
        self.assertTrue(status['ok'])

    def test_incomplete_report_publishes_no_partial_fixtures(self):
        events,status=self.run_branch([{'id':'a','start_time':'2026-10-20T15:00:00Z'}],False)
        self.assertFalse(status['ok']); self.assertEqual([],events)
        self.assertEqual(0,status['events'])

    def test_late_invalid_time_cannot_leak_preceding_good_fixture(self):
        for invalid in ('2026-10-21T15:00:00','unresolved'):
            events,status=self.run_branch([{'id':'a','start_time':'2026-10-20T15:00:00Z'},
                                           {'id':'b','start_time':invalid}])
            self.assertFalse(status['ok']); self.assertEqual([],events)
            self.assertEqual(0,status['events'])

    def test_published_total_is_not_remaining_unplayed_count(self):
        events,status=self.run_branch([{'id':'a','start_time':'2026-10-20T15:00:00Z'}],european=True)
        self.assertTrue(status['ok']);self.assertEqual(224,status['published_fixtures'])
        self.assertEqual(1,status['remaining_unplayed_fixtures'])
