import copy
import datetime as dt
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import uefa_domestic_adapter as u
FIX = ROOT/'tests/fixtures/uefa_domestic_20261018'
NOW = dt.datetime(2026,10,18,21,tzinfo=dt.timezone.utc)
START, END = dt.date(2026,10,18), dt.date(2026,10,25)


class UefaTests(unittest.TestCase):
    def setUp(self):
        # Offline fake-client contract tests only; production defaults stay disabled.
        access = patch.dict(u.AUTOMATED_ACCESS, {"enabled": True})
        access.start(); self.addCleanup(access.stop)
        self.spec = next(s for s in u.SCOPES.values() if s['competition_id']=='1079')
        self.source = u.source_config(self.spec['id'])
        self.rows=json.loads((FIX/'1079-matches.json').read_text())
        self.directory=json.loads((FIX/'ARM-directory.json').read_text())

    def parse(self):
        return u.parse_matches(self.rows,self.directory,self.source,NOW,START,END)

    def first(self):
        return next(x for x in self.rows if x['kickOffTime']['date']=='2026-10-23')

    def test_three_league_live_capture_counts(self):
        for comp,country,count in [('1079','ARM',5),('1029','BUL',3),('1088','KOS',2)]:
            spec=next(s for s in u.SCOPES.values() if s['competition_id']==comp)
            rows,proof=u.parse_matches(json.loads((FIX/(comp+'-matches.json')).read_text()),json.loads((FIX/(country+'-directory.json')).read_text()),u.source_config(spec['id']),NOW,START,END)
            self.assertEqual(count,len(rows));self.assertFalse(proof['coverage_complete']);self.assertFalse(proof['review_window_complete'])
            self.assertTrue(all(x['start_time'].endswith('Z') for x in rows))

    def test_exact_source_scope(self):
        for key,val in [('region','Elsewhere'),('league','Cup'),('catalog_terms',[]),('coverage_complete',True),('endpoint','https://example.com'),('source_type','other')]:
            old=self.source.copy();self.source[key]=val
            with self.assertRaises(ValueError):self.parse()
            self.source=old

    def test_competition_identity_gates(self):
        for key,val in [('id','999'),('countryCode','BUL'),('age','YOUTH'),('sex','FEMALE'),('sportsType','FUTSAL'),('tier','SECOND'),('type','CUP'),('teamCategory','NATIONAL'),('region','INTERNATIONAL')]:
            old=copy.deepcopy(self.rows);self.first()['competition'][key]=val
            with self.assertRaises(ValueError):self.parse()
            self.rows=old

    def test_directory_missing_duplicate_changed(self):
        saved=copy.deepcopy(self.directory)
        for value in [[],saved+saved,{},[{'id':'1079'}]]:
            self.directory=value
            with self.assertRaises(ValueError):self.parse()

    def test_edition_and_missing_status(self):
        self.first()['seasonYear']='2028'
        with self.assertRaises(ValueError):self.parse()
        self.first()['seasonYear']='2027';del self.first()['status']
        rows,p=self.parse();self.assertEqual(4,len(rows));self.assertGreater(p['non_upcoming_holds'],0)

    def test_completed_postponed_scored_rows_hold(self):
        saved=copy.deepcopy(self.rows)
        for status in ['FINISHED','LIVE','POSTPONED','CANCELLED','UNKNOWN']:
            self.rows=copy.deepcopy(saved);self.first()['status']=status
            self.assertEqual(4,len(self.parse()[0]))
        self.rows=copy.deepcopy(saved);self.first()['score']={'total':{'home':0,'away':0}}
        self.assertEqual(4,len(self.parse()[0]))

    def test_unknown_names_ids_reserves_placeholders_hold(self):
        saved=copy.deepcopy(self.rows)
        for change in [{'id':'unknown'},{'internationalName':'Van II'},{'internationalName':'Van renamed'},{'isPlaceHolder':True}]:
            self.rows=copy.deepcopy(saved);self.first()['homeTeam'].update(change)
            self.assertEqual(4,len(self.parse()[0]))
        self.rows=copy.deepcopy(saved);del self.first()['homeTeam']['isPlaceHolder']
        self.assertEqual(4,len(self.parse()[0]))

    def test_missing_and_identical_opponent_fails(self):
        self.first()['awayTeam']['id']=self.first()['homeTeam']['id']
        with self.assertRaises(ValueError):self.parse()
        del self.first()['homeTeam']['id']
        with self.assertRaises(ValueError):self.parse()

    def test_utc_malformed_missing_offset_date_conflict(self):
        saved=copy.deepcopy(self.rows)
        for value in ['2026-10-23T15:00:00','2026-10-23','2026-10-23T15:00:00+03:00','2026-10-24T15:00:00Z','2026-13-23T15:00:00Z']:
            self.rows=copy.deepcopy(saved);self.first()['kickOffTime']['dateTime']=value
            with self.assertRaises(ValueError):self.parse()

    def test_midnight_and_missing_time_are_holds_not_guesses(self):
        for value in [None,'2026-10-23T00:00:00Z']:
            self.first()['kickOffTime']['dateTime']=value
            rows,p=self.parse();self.assertEqual(4,len(rows));self.assertEqual(1,p['untimed_holds'])

    def test_duplicate_consistency(self):
        self.rows.append(copy.deepcopy(self.first()));self.assertEqual(5,len(self.parse()[0]))
        self.rows[-1]['status']='FINISHED'
        with self.assertRaises(ValueError):self.parse()

    def test_empty_success_is_explicit_partial_not_complete(self):
        self.rows=[];rows,p=self.parse();self.assertEqual([],rows);self.assertFalse(p['coverage_complete'])
        self.rows={}
        with self.assertRaises(ValueError):self.parse()

    def test_candidates_not_all_connected(self):
        configs=json.loads((ROOT/'data/soccer-uefa-domestic-sources.json').read_text())['sources']
        self.assertEqual(15,len(u.SCOPES))
        for s in u.SCOPES.values():
            configured=next(x for x in configs if x['id']==s['id'])
            if s['enabled']:self.assertEqual(u.SOURCE_TYPE,configured['source_type'])
            else:
                self.assertEqual('coverage-gap',configured['source_type'])
                with self.assertRaises(ValueError):u.source_config(s['id'])

    def test_workflow_trigger_and_queue(self):
        t=(ROOT/'.github/workflows/refresh-global-schedule.yml').read_text()
        for x in ['scripts/uefa_domestic_adapter.py','data/uefa-reviewed-scopes.json','  queue: max','  cancel-in-progress: false']:self.assertIn(x,t)

    def test_four_cup_subsets_are_future_only_and_bounded(self):
        for comp,country,count in [('5081','GEO',2),('5046','POL',2),('5045','NOR',3),('5049','ROU',4)]:
            spec=next(s for s in u.SCOPES.values() if s['competition_id']==comp)
            payload=json.loads((FIX/(comp+'-matches.json')).read_text())
            directory=json.loads((FIX/(country+'-directory.json')).read_text())
            source=u.source_config(spec['id'])
            self.assertEqual([],u.parse_matches(payload,directory,source,NOW,START,END)[0])
            events,proof=u.parse_matches(payload,directory,source,NOW,START,dt.date(2026,11,15))
            self.assertEqual(count,len(events));self.assertFalse(proof['coverage_complete'])
            self.assertTrue(all(x['season_stage']==spec['phase'] for x in events))
            review=next(iter(spec['reviewed_pairs']))
            row=next(x for x in payload if x['id']==review)
            row['id']='unreviewed-same-teams'
            self.assertEqual(count-1,len(u.parse_matches(payload,directory,source,NOW,START,dt.date(2026,11,15))[0]))

    def test_league_team_allowlists_have_retained_current_edition_witnesses(self):
        for spec in u.SCOPES.values():
            if spec['type']!='LEAGUE':continue
            witnesses=json.loads((FIX/(spec['country']+'-membership.json')).read_text())
            teams={}
            for row in witnesses:
                u.validate_competition(row['competition'],spec)
                self.assertEqual(spec['season'],row['seasonYear'])
                teams.update({row[k]['id']:row[k]['internationalName'] for k in ['homeTeam','awayTeam']})
            self.assertEqual(spec['teams'],teams)

    def test_reviewed_cup_participants_have_exact_first_tier_witnesses(self):
        for spec in u.SCOPES.values():
            if not spec['enabled'] or spec['type']!='CUP':continue
            witnesses=json.loads((FIX/(spec['country']+'-membership.json')).read_text())
            teams={}
            for row in witnesses:
                c=row['competition']
                self.assertEqual('FIRST',c['tier']);self.assertEqual('MALE',c['sex']);self.assertEqual('ADULT',c['age']);self.assertEqual('FOOTBALL',c['sportsType'])
                self.assertEqual(spec['proof']['membership_competition_id'],c['id'])
                self.assertEqual(spec['proof']['membership_season'],row['seasonYear'])
                teams.update({row[k]['id']:row[k]['internationalName'] for k in ['homeTeam','awayTeam']})
            for ident,name in spec['teams'].items():self.assertEqual(name,teams[ident])
            self.assertTrue(spec['proof']['phase_source_urls'])
            self.assertFalse(spec['proof']['age_clearance'])

    def test_cup_date_change_does_not_reapprove_fixture(self):
        spec=next(s for s in u.SCOPES.values() if s['competition_id']=='5081')
        rows=json.loads((FIX/'5081-matches.json').read_text());row=rows[0]
        row['kickOffTime']={'date':'2026-10-30','dateTime':'2026-10-30T16:00:00Z'}
        events,p=u.parse_matches(rows,json.loads((FIX/'GEO-directory.json').read_text()),u.source_config(spec['id']),NOW,START,dt.date(2026,11,15))
        self.assertEqual(1,len(events));self.assertEqual(1,p['unreviewed_cup_phase_holds'])

    def response(self,data,status=200):
        return SimpleNamespace(status_code=status,json=lambda:data,raise_for_status=lambda:None)

    def test_pagination_and_terminal_short_page(self):
        calls=[]
        def get(url,**kw):
            calls.append(kw)
            return self.response([{'id':str(i)} for i in range(kw['params']['offset'],kw['params']['offset']+2)] if len(calls)==1 else [])
        rows,pages=u.ProviderClient(get).pages('matches',{'competitionId':'1079'},2)
        self.assertEqual(2,len(rows));self.assertEqual(2,pages);self.assertEqual([0,2],[x['params']['offset'] for x in calls]);self.assertTrue(all(x['allow_redirects'] is False for x in calls))
        self.assertTrue(all('headers' not in x for x in calls))

    def test_live_pagination_evidence_matches_publisher_contract(self):
        p=json.loads((FIX/'pagination-proof.json').read_text())
        self.assertEqual([0,100],[x['offset'] for x in p['pages']])
        self.assertEqual([100,98],[len(x['ids']) for x in p['pages']])
        self.assertEqual(198,len({i for x in p['pages'] for i in x['ids']}))
        contract=(FIX/'publisher-match-query.js').read_text()
        self.assertIn('offset:a.offset,limit:a.limit',contract)
        self.assertIn('"v2/matches"',contract)

    def test_repeated_pages_and_bound_fail_atomically(self):
        with self.assertRaises(ValueError):u.ProviderClient(lambda *a,**k:self.response([{'id':'same'}])).pages('matches',{},1)
        n=[0]
        def get(*a,**k):n[0]+=1;return self.response([{'id':str(n[0])}])
        with self.assertRaises(ValueError):u.ProviderClient(get).pages('matches',{},1)

    def test_denial_redirect_rate_limit_stop_entire_family(self):
        for status in [401,403,429,302]:
            calls=[]
            def get(*a,**k):calls.append(a);return self.response([],status)
            client=u.ProviderClient(get)
            for _ in range(2):
                with self.assertRaises(ValueError):client.page('matches',{})
            self.assertEqual(1,len(calls))

    def test_fetch_window_covers_chicago_and_has_no_completeness_claim(self):
        calls=[]
        def get(url,**kw):calls.append((url,kw));return self.response(self.directory if url.endswith('competitions') else self.rows)
        rows,p=u.ProviderClient(get).fetch(self.source,NOW,START,END)
        self.assertEqual(5,len(rows));self.assertEqual('2026-10-26',calls[1][1]['params']['toDate']);self.assertFalse(p['coverage_complete'])
        with self.assertRaises(ValueError):u.ProviderClient(get).fetch(self.source,NOW.replace(year=2028),START,END)


class PermissionHoldTests(unittest.TestCase):
    def test_default_hold_makes_zero_requests_for_all_seven_sources(self):
        self.assertIs(False, u.AUTOMATED_ACCESS['enabled'])
        calls=[]
        client=u.ProviderClient(get=lambda *a,**k:calls.append((a,k)))
        enabled=[s for s in u.SCOPES.values() if s['enabled']]
        self.assertEqual(7,len(enabled))
        for spec in enabled:
            source=u.source_config(spec['id'])
            self.assertEqual('permission_required',source['access_status'])
            self.assertFalse(source['coverage_complete'])
            with self.assertRaisesRegex(ValueError,'Permission required'):
                client.fetch(source,NOW,START,END)
        for invoke in (lambda:client.page('matches',{}),lambda:client.pages('matches',{},100)):
            with self.assertRaisesRegex(ValueError,'Permission required'):invoke()
        self.assertEqual([],calls)

    def test_missing_or_non_boolean_grant_fails_closed(self):
        for config in ({},{'enabled':'true'},{'enabled':1}):
            with patch.dict(u.AUTOMATED_ACCESS,config,clear=True):
                with self.assertRaisesRegex(ValueError,'Permission required'):
                    u.require_automated_access()


class CollectorTests(unittest.TestCase):
    def branch(self,fixtures):
        text=(ROOT/'scripts/refresh_global_schedule.py').read_text();a=text.index('    if source.get("source_type") == "official-uefa-domestic-reviewed":');b=text.index('    if source.get("source_type") in ("official-zpl-transitional-calendars"',a)
        source=u.source_config(next(s['id'] for s in u.SCOPES.values() if s['competition_id']=='1079'))
        ns={'configured':[source],'datetime':dt,'TODAY':START,'END':END,'NOW_UTC':NOW,'TZ':ZoneInfo('America/Chicago'),'events':[],'seen':set(),'source_status':[], 'UEFA_DOMESTIC_CLIENT':SimpleNamespace(fetch=lambda *a:(fixtures,{'coverage_complete':False}))}
        exec('for source in configured:\n    errors=[]\n    count=0\n'+text[a:b],ns)
        return ns

    def test_collector_late_failure_rolls_back_events_and_seen(self):
        good={'id':'one','start_time':'2026-10-23T15:00:00Z'}
        ns=self.branch([good,{'id':'bad','start_time':'invalid'}]);self.assertEqual([],ns['events']);self.assertEqual(set(),ns['seen']);self.assertFalse(ns['source_status'][0]['ok'])
        ns=self.branch([good]);self.assertEqual([good],ns['events']);self.assertTrue(ns['source_status'][0]['ok']);self.assertFalse(ns['source_status'][0]['coverage_complete'])

if __name__=='__main__':unittest.main()
