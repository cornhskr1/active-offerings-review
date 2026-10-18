"""Exercise the actual collector branch without importing its network-running module."""
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
TEXT = (ROOT / 'scripts/refresh_global_schedule.py').read_text()
START = TEXT.index('    if source.get("source_type") in ("official-zpl-transitional-calendars"')
END = TEXT.index('    if source.get("source_type") in ("official-european-basketball-fixtures"', START)
COLLECTOR = 'for source in configured:\n' + TEXT[START:END]

class SoccerCollectorTests(unittest.TestCase):
    def run_branch(self, fixtures, czech=False):
        source = {'id':'test', 'source_type': 'official-czech-cup-fixtures' if czech else 'official-zpl-transitional-calendars',
                  'endpoint':'https://example.invalid', 'coverage_end':'2027-01-13'}
        namespace = {
            'configured':[source], 'datetime':dt, 'HEADERS':{}, 'TZ':ZoneInfo('America/Chicago'),
            'NOW_UTC':dt.datetime(2026,10,18,14,tzinfo=dt.timezone.utc),
            'TODAY':dt.date(2026,10,18), 'END':dt.date(2026,10,25),
            'events':[], 'seen':set(), 'source_status':[], 'count':0, 'errors':[],
            'fetch_zambia_fixtures':lambda *args:(fixtures,{'coverage_status':'partial'}),
            'parse_czech_cup_fixtures':lambda content,source:(fixtures,{'coverage_status':'partial'}),
            'requests':SimpleNamespace(get=lambda *args,**kwargs:SimpleNamespace(
                raise_for_status=lambda:None,content=b'UTF-8 source')),
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


    def test_date_only_czech_fixture_keeps_literal_date(self):
        events,status=self.run_branch([{'id':'date','start_time':'2026-10-18','date_only':True}],czech=True)
        self.assertEqual('2026-10-18',events[0]['start_time'])
        self.assertTrue(status['ok']);self.assertEqual('partial',status['coverage_status'])

    def test_valid_future_publication_outside_window_is_healthy_empty_not_offseason(self):
        events,status=self.run_branch([{'id':'later','start_time':'2026-10-27','date_only':True}],czech=True)
        self.assertEqual([],events);self.assertTrue(status['ok'])
        self.assertEqual('partial',status['coverage_status'])
        self.assertNotIn('offseason',str(status).lower())

    def test_late_invalid_time_cannot_leak_preceding_good_fixture(self):
        for invalid in ('2026-10-21T15:00:00','unresolved'):
            events,status=self.run_branch([{'id':'a','start_time':'2026-10-20T15:00:00Z'},
                                           {'id':'b','start_time':invalid}])
            self.assertFalse(status['ok']);self.assertEqual([],events)
            self.assertEqual(0,status['events'])

    def test_duplicates_do_not_double_count(self):
        event={'id':'a','start_time':'2026-10-20T15:00:00Z'}
        events,status=self.run_branch([event,event])
        self.assertEqual(1,len(events));self.assertEqual(1,status['events'])
