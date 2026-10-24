from tests.retired_workflow_policy import historical_workflow_path
import copy
import datetime as dt
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import nz_national_league_adapter as nz
FIXTURES = ROOT / 'tests/fixtures/nz_20261018'


class NZChampionshipTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((FIXTURES / 'dates.json').read_text())
        self.meta = json.loads((FIXTURES / 'metadata.json').read_text())
        self.source = nz.source_config()
        self.today = dt.date(2026, 10, 18)

    def parse(self):
        return nz.parse_fixtures(self.data, self.meta, self.source, self.today)

    def future(self):
        return next(r for r in self.data['Fixtures'] if r['Id'] == 7111090)

    def test_live_capture_exact_counts_and_date_only(self):
        rows, proof = self.parse()
        self.assertEqual(35, len(rows))
        self.assertEqual(5, sum('2026-10-18' <= r['start_time'] <= '2026-10-25' for r in rows))
        self.assertEqual(55, proof['published_named_fixtures'])
        self.assertEqual(11, proof['placeholder_or_bye_holds'])
        self.assertEqual(20, proof['completed_or_live_skipped'])
        self.assertEqual(4, proof['out_of_scope_records'])
        self.assertFalse(proof['review_window_complete'])
        self.assertFalse(proof['coverage_complete'])
        self.assertFalse(self.source['coverage_complete'])
        self.assertTrue(all(r['date_only'] and len(r['start_time']) == 10 for r in rows))
        self.assertEqual('2026-12-06', max(r['start_time'] for r in rows))
        self.assertEqual('partial', proof['coverage_status'])

    def test_normal_refresh_trigger_preserves_queue(self):
        text = historical_workflow_path('refresh-global-schedule.yml').read_text()
        self.assertIn('      - scripts/nz_national_league_adapter.py', text)
        self.assertIn('  queue: max', text)
        self.assertIn('  cancel-in-progress: false', text)

    def test_scope_and_edition_fail_closed(self):
        for key, value in [('region','Australia'), ('league','Chatham Cup | Men'), ('endpoint','https://example.com'), ('coverage_status','complete'), ('coverage_complete',True)]:
            with self.subTest(key=key):
                source = copy.deepcopy(self.source); source[key] = value
                with self.assertRaises(ValueError): nz.parse_fixtures(self.data,self.meta,source,self.today)
        self.meta['Competitions'][0]['Name'] = "Dettol Men's National League 2027"
        with self.assertRaises(ValueError): self.parse()

    def test_unknown_and_other_scope_excluded(self):
        for changes, hold in [({'AwayTeamId':9},'unknown_team_holds'),
                              ({'AwayOrganisationId':9},'unknown_team_holds'),
                              ({'AwayTeamName':'Unknown'},'unknown_team_holds'),
                              ({'AwayTeamId':None},'placeholder_or_bye_holds'),
                              ({'AwayTeamName':'BYE'},'placeholder_or_bye_holds'),
                              ({'SectionId':267766},'out_of_scope_records'),
                              ({'GradeId':705174},'out_of_scope_records'),
                              ({'CompId':14997},'out_of_scope_records'),
                              ({'RoundName':'FINAL'},'unreviewed_stage_holds')]:
            with self.subTest(changes=changes):
                saved=copy.deepcopy(self.data); self.future().update(changes)
                rows,proof=self.parse();self.assertEqual(34,len(rows));self.assertGreater(proof[hold],0)
                self.data=saved

    def test_results_and_nonconfirmed_never_published(self):
        for changes in ({'HomeScore':'0'}, {'AwayScore':'0'}, {'CustomScoreDisplay':'0:0'}, {'InGame':True}, {'ResultStatus':1}, {'Status':3}, {'StatusName':'Postponed'}):
            with self.subTest(changes=changes):
                saved=copy.deepcopy(self.data);self.future().update(changes)
                self.assertEqual(34,len(self.parse()[0]));self.data=saved

    def test_missing_and_invalid_date_evidence_atomic_failure(self):
        for changes in ({'From':'2027-10-23T19:15:00'}, {'From':'2026-10-23'}, {'From':'2026-13-23T19:15:00'}, {'To':'2026-10-23T19:00:00'}, {'From':'2026-10-23T19:15:00Z'}):
            saved=copy.deepcopy(self.data);self.future().update(changes)
            with self.assertRaises(ValueError):self.parse()
            self.data=saved
        del self.future()['HomeScore']
        with self.assertRaises(ValueError):self.parse()

    def test_duplicate_handling(self):
        self.data['Fixtures'].append(copy.deepcopy(self.future()))
        self.assertEqual(35,len(self.parse()[0]))
        self.data['Fixtures'][-1]['From']='2026-10-24T19:15:00'
        with self.assertRaises(ValueError):self.parse()

    def test_empty_and_schema_fail_closed(self):
        for rows in ([],None,['bad']):
            self.data['Fixtures']=rows
            with self.assertRaises(ValueError):self.parse()

    def test_widget_and_fetch_are_exact_read_queries(self):
        page=(FIXTURES/'page.html').read_bytes();nz.validate_widget(page)
        with self.assertRaises(ValueError):nz.validate_widget(page.replace(b'35',b'36'))
        calls=[]
        def response(content=None,data=None):
            return SimpleNamespace(content=content,json=lambda:data,raise_for_status=lambda:None)
        def post(url,**kwargs):
            calls.append((url,kwargs['json']))
            return response(data=self.meta if url.endswith('metadata/') else self.data)
        rows,_=nz.fetch_fixtures(self.source,self.today,get=lambda *a,**k:response(content=page),post=post)
        self.assertEqual(35,len(rows));self.assertEqual(['13413'],calls[0][1]);self.assertEqual(nz.QUERY,calls[1][1])
        with self.assertRaises(ValueError):nz.fetch_fixtures(self.source,dt.date(2027,1,1))

    def test_past_dates_are_held_not_rolled_forward(self):
        self.today=dt.date(2026,12,7)
        rows,proof=self.parse();self.assertEqual([],rows);self.assertEqual(35,proof['past_unresolved_holds'])


class NZCollectorTests(unittest.TestCase):
    def branch(self, fixtures):
        text=(ROOT/'scripts/refresh_global_schedule.py').read_text()
        a=text.index('    if source.get("source_type") in ("official-zpl-transitional-calendars"')
        b=text.index('    if source.get("source_type") in ("official-european-basketball-fixtures"',a)
        ns={'configured':[nz.source_config()], 'datetime':dt, 'TODAY':dt.date(2026,10,18), 'END':dt.date(2026,10,25),
            'NOW_UTC':dt.datetime(2026,10,18,tzinfo=dt.timezone.utc),'events':[], 'seen':set(), 'source_status':[], 'count':0, 'errors':[],
            'fetch_nz_championship_fixtures':lambda *a:(fixtures,{'coverage_status':'partial','review_window_complete':False})}
        exec('for source in configured:\n'+text[a:b],ns)
        return ns

    def test_literal_window_and_empty_are_not_offseason(self):
        ns=self.branch([{'id':'a','start_time':'2026-10-25','date_only':True},{'id':'b','start_time':'2026-10-26','date_only':True}])
        self.assertEqual(['a'],[x['id'] for x in ns['events']]);self.assertTrue(ns['source_status'][0]['ok'])
        self.assertIs(ns['source_status'][0]['coverage_complete'], False)
        ns=self.branch([]);self.assertTrue(ns['source_status'][0]['ok']);self.assertFalse(ns['source_status'][0]['review_window_complete'])
        self.assertNotIn('offseason',str(ns['source_status']).lower())

    def test_late_failure_rolls_back_events_and_seen(self):
        ns=self.branch([{'id':'a','start_time':'2026-10-20','date_only':True},{'id':'b','start_time':'invalid','date_only':True}])
        self.assertEqual([],ns['events']);self.assertEqual(set(),ns['seen']);self.assertFalse(ns['source_status'][0]['ok'])

    def test_duplicate_deduplication(self):
        e={'id':'a','start_time':'2026-10-20','date_only':True};ns=self.branch([e,e]);self.assertEqual(1,len(ns['events']))
