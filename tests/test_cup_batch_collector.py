"""Exercise the actual three-cup collector branch without running other sources."""
import datetime as dt
from pathlib import Path
import unittest
TEXT=(Path(__file__).parents[1]/'scripts/refresh_global_schedule.py').read_text()
START=TEXT.index('    if source.get("source_type") in ("official-lff-cup-fixtures"')
END=TEXT.index('    if source.get("source_type") in ("official-zpl-transitional-calendars"',START)
CODE='for source in configured:\n'+TEXT[START:END]
TYPES=['official-lff-cup-fixtures','official-hns-croatian-cup-fixtures','official-mfl-fa-semifinal-fixtures']
class CupCollectorTests(unittest.TestCase):
    def run_branch(self,fixtures,source_type):
        def fetch(*args):return fixtures,{'coverage_status':'partial','published_fixtures':len(fixtures),'review_window_complete':False}
        ns={'configured':[{'id':'test','source_type':source_type}],'datetime':dt,'NOW_UTC':dt.datetime(2026,10,18,16,tzinfo=dt.timezone.utc),
            'TODAY':dt.date(2026,10,18),'END':dt.date(2026,10,25),'events':[],'seen':set(),'source_status':[],'errors':[],'count':0,
            'fetch_baltic_cup_fixtures':fetch,'fetch_croatian_cup_fixtures':fetch,'fetch_mfl_fa_semifinals':fetch}
        exec(compile(CODE,'cup-collector','exec'),ns);return ns['events'],ns['source_status'][0]
    def test_all_three_preserve_literal_date_and_window(self):
        rows=[{'id':str(i),'start_time':date,'date_only':True} for i,date in enumerate(['2026-10-17','2026-10-18','2026-10-25','2026-10-26'])]
        for kind in TYPES:
            with self.subTest(kind=kind):
                events,status=self.run_branch(rows,kind);self.assertEqual(['2026-10-18','2026-10-25'],[e['start_time'] for e in events]);self.assertTrue(status['ok']);self.assertEqual('partial',status['coverage_status'])
    def test_future_only_is_healthy_empty_but_partial(self):
        events,status=self.run_branch([{'id':'a','start_time':'2026-11-20','date_only':True}],TYPES[0])
        self.assertEqual([],events);self.assertTrue(status['ok']);self.assertFalse(status['review_window_complete']);self.assertEqual(1,status['published_fixtures'])
    def test_malformed_later_record_cannot_leak_good_rows(self):
        good={'id':'a','start_time':'2026-10-20','date_only':True}
        for bad in [{'id':'b','start_time':'unknown','date_only':True},{'id':'b','start_time':'2026-10-21T12:00:00Z'}]:
            for kind in TYPES:
                with self.subTest(kind=kind,bad=bad):
                    events,status=self.run_branch([good,bad],kind);self.assertEqual([],events);self.assertFalse(status['ok']);self.assertEqual(0,status['events'])
    def test_duplicate_does_not_double_count(self):
        row={'id':'a','start_time':'2026-10-20','date_only':True};events,status=self.run_branch([row,row],TYPES[0]);self.assertEqual(1,len(events))
