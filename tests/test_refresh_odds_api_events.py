import copy
import datetime as dt
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.refresh_odds_api_events import collect_events, Response, ORIGIN, provider_get

CONFIG=json.loads((Path(__file__).resolve().parents[1]/'data/odds-api-catalog-mappings.json').read_text())
NOW=dt.datetime(2026,10,19,2,tzinfo=dt.timezone.utc)
KEY='americanfootball_nfl'

def event(id='sample',start='2026-10-20T20:00:00Z'):
    return {'id':id,'sport_key':KEY,'away_team':'Away Team','home_team':'Home Team','commence_time':start,
            'bookmakers':[{'apiKey':'DO-NOT-PERSIST','price':100}], 'venue':'not authoritative'}

class FakeResponse:
    def __init__(self,body,status=200,headers=None):
        self.body=body;self.status_code=status;self.headers={'x-requests-last':'0'} if headers is None else headers
        self.reads=0;self.closed=False
    def json(self):self.reads+=1;return self.body
    def close(self):self.closed=True

class Transport:
    def __init__(self,responses):self.responses=list(responses);self.calls=[]
    def __call__(self,url,params,timeout,allow_redirects):
        self.calls.append((url,dict(params),timeout,allow_redirects))
        if not self.responses:raise AssertionError('unexpected request')
        result=self.responses.pop(0)
        if isinstance(result,Exception):raise result
        return result

def directory(keys=(KEY,)):
    return FakeResponse([{'key':key,'active':True} for key in keys])
def run(transport,previous=None,now=NOW,key='TEST-ONLY-SECRET'):
    return collect_events(CONFIG,previous or {},now,key,transport)

class CollectorTests(unittest.TestCase):
    def test_routes_are_only_directory_and_events_and_secret_not_output(self):
        t=Transport([directory(),FakeResponse([event()])]);out=run(t)
        self.assertEqual([c[0] for c in t.calls],[ORIGIN+'/v4/sports/',ORIGIN+'/v4/sports/'+KEY+'/events'])
        self.assertTrue(all(c[3] is False for c in t.calls))
        self.assertEqual(len(out['events']),1);self.assertEqual(out['events'][0]['status'],'UNKNOWN')
        serialized=json.dumps(out)
        for value in ['TEST-ONLY-SECRET','DO-NOT-PERSIST','bookmakers','not authoritative','apiKey']:
            self.assertNotIn(value,serialized)
        self.assertFalse(out['events'][0]['source_stale'])
        health=next(x for x in out['sources'] if x['provider_key']==KEY)
        self.assertEqual(health['event_count'],1);self.assertEqual(health['last_attempt_at'],'2026-10-19T02:00:00Z')

    def test_three_hour_gate_and_failed_attempt_cooldown(self):
        out=run(Transport([directory(),FakeResponse([event()])]))
        t=Transport([]);again=run(t,out,NOW+dt.timedelta(hours=2,minutes=59))
        self.assertEqual(t.calls,[]);self.assertEqual(again['events'][0]['observed_at'],out['events'][0]['observed_at'])
        t=Transport([directory(),FakeResponse([],500)])
        failed=run(t,out,NOW+dt.timedelta(hours=3));self.assertTrue(failed['events'][0]['source_stale'])
        t=Transport([]);run(t,failed,NOW+dt.timedelta(hours=4));self.assertEqual(t.calls,[])

    def test_missing_positive_noninteger_cost_stops_before_body(self):
        for headers in ({},{'x-requests-last':'1'},{'x-requests-last':'0.0'},{'x-requests-last':'-0'}):
            with self.subTest(headers=headers):
                r=FakeResponse([event()],headers=headers);t=Transport([directory(),r]);out=run(t)
                self.assertEqual(r.reads,0);self.assertTrue(out['collector_state']['halted'])
                t2=Transport([]);again=run(t2,out,NOW+dt.timedelta(days=4));self.assertEqual(t2.calls,[])
                self.assertTrue(again['coverage']['collection_halted'])

    def test_directory_cost_guard_prevents_all_events(self):
        r=FakeResponse([],headers={});t=Transport([r]);out=run(t)
        self.assertEqual(len(t.calls),1);self.assertEqual(r.reads,0);self.assertTrue(out['coverage']['collection_halted'])

    def test_auth_hold_persists_without_reading_body(self):
        for status in (401,403):
            r=FakeResponse({'secret':'bad'},status);t=Transport([r]);out=run(t)
            self.assertEqual(r.reads,0);self.assertTrue(out['coverage']['collection_halted'])
            t2=Transport([]);run(t2,out,NOW+dt.timedelta(hours=30));self.assertEqual(t2.calls,[])

    def test_family_stops_after_first_event_denial(self):
        keys=[KEY,'basketball_nba'];r=FakeResponse([],403);t=Transport([directory(keys),r]);out=run(t)
        self.assertEqual(len(t.calls),2);self.assertTrue(out['coverage']['collection_halted'])

    def test_429_cooldown_no_immediate_retries(self):
        r=FakeResponse([],429,{'x-requests-last':'0','retry-after':'14400'});t=Transport([directory(),r]);out=run(t)
        self.assertEqual(r.reads,0);self.assertEqual(len(t.calls),2)
        t2=Transport([]);run(t2,out,NOW+dt.timedelta(hours=3));self.assertEqual(t2.calls,[])
        self.assertFalse(out['coverage']['collection_halted'])

    def test_redirect_is_not_followed(self):
        r=FakeResponse([],302,{'x-requests-last':'0','Location':'https://other.invalid/?secret=x'})
        out=run(Transport([r]));self.assertTrue(out['coverage']['collection_halted']);self.assertEqual(r.reads,0)
        self.assertNotIn('other.invalid',json.dumps(out))

    def test_exception_never_echoed_and_uncertain_request_holds(self):
        out=run(Transport([RuntimeError('https://api.the-odds-api.com/?apiKey=TEST-ONLY-SECRET')]))
        self.assertNotIn('TEST-ONLY-SECRET',json.dumps(out));self.assertTrue(out['coverage']['collection_halted'])
        self.assertEqual(out['coverage']['requests_this_run'],1)

    def test_missing_key_preserves_stale_last_good_no_request(self):
        prior=run(Transport([directory(),FakeResponse([event()])]))
        t=Transport([]);out=run(t,prior,NOW+dt.timedelta(hours=3),key=None)
        self.assertEqual(t.calls,[]);self.assertEqual(len(out['events']),1);self.assertTrue(out['events'][0]['source_stale'])
        self.assertEqual(out['coverage']['stop_reason'],'credential_not_configured')

    def test_omission_not_cancellation_and_original_age_preserved(self):
        prior=run(Transport([directory(),FakeResponse([event()])]))
        out=run(Transport([directory(),FakeResponse([])]),prior,NOW+dt.timedelta(hours=3))
        self.assertEqual(len(out['events']),1);self.assertEqual(out['events'][0]['status'],'UNKNOWN')
        self.assertEqual(out['events'][0]['observed_at'],'2026-10-19T02:00:00Z');self.assertTrue(out['events'][0]['source_stale'])

    def test_window_uses_central_midnight_through_plus_seven_days(self):
        rows=[event('before','2026-10-18T04:59:59Z'),event('first','2026-10-18T05:00:00Z'),
              event('last','2026-10-26T04:59:59Z'),event('after','2026-10-26T05:00:00Z')]
        out=run(Transport([directory(),FakeResponse(rows)]))
        self.assertEqual([e['provider_event_id'] for e in out['events']],['first','last'])
        self.assertEqual(out['window_start'],'2026-10-18');self.assertEqual(out['window_end'],'2026-10-25')

    def test_inactive_key_not_fetched_no_offseason_claim(self):
        t=Transport([FakeResponse([{'key':KEY,'active':False}])]);out=run(t)
        self.assertEqual(len(t.calls),1);self.assertEqual(out['events'],[])
        h=next(x for x in out['sources'] if x['provider_key']==KEY)
        self.assertEqual(h['status'],'not_active_in_directory');self.assertIn('does not establish offseason',h['reason'])

    def test_unknown_directory_keys_never_routed(self):
        t=Transport([directory(('americanfootball_ncaaf','unknown_key'))]);out=run(t)
        self.assertEqual(len(t.calls),1);self.assertEqual(out['events'],[])

    def test_prior_control_metadata_is_allowlisted(self):
        prior={'collector_state':{'halted':True,'secret':'TEST-ONLY-SECRET','stop_reason':'apiKey=TEST-ONLY-SECRET',
               'directory':{'status':'ok','sports':{'evil?key=SECRET':True},'body':'TEST-ONLY-SECRET'},
               'sources':{KEY:{'reason':'TEST-ONLY-SECRET','status':'failed','url':'TEST-ONLY-SECRET'}}}}
        out=run(Transport([]),prior);self.assertNotIn('TEST-ONLY-SECRET',json.dumps(out));self.assertNotIn('evil',json.dumps(out))

    def test_bad_control_timestamp_fails_closed(self):
        prior={'collector_state':{'directory':{'next_fetch_at':'garbage'}}}
        t=Transport([]);out=run(t,prior);self.assertEqual(t.calls,[]);self.assertTrue(out['coverage']['collection_halted'])

    def test_bad_payload_retains_last_good(self):
        prior=run(Transport([directory(),FakeResponse([event()])]))
        bad=event();bad['commence_time']='2026-10-20'
        out=run(Transport([directory(),FakeResponse([bad])]),prior,NOW+dt.timedelta(hours=3))
        self.assertEqual(len(out['events']),1);self.assertTrue(out['events'][0]['source_stale'])

    def test_aware_clock_and_exact_mapping_count_required(self):
        with self.assertRaises(ValueError):run(Transport([]),now=NOW.replace(tzinfo=None))
        bad=copy.deepcopy(CONFIG);bad['mappings'].pop()
        with self.assertRaises(ValueError):collect_events(bad,{},NOW,'x',Transport([]))

    def test_response_body_bounded(self):
        class Raw:
            code=200;headers={}
            def read(self,n):return b'x'*n
            def close(self):pass
        with self.assertRaises(ValueError):Response(Raw()).json()

    def test_nonempty_prior_requires_complete_versioned_control_state(self):
        prior=run(Transport([directory(),FakeResponse([event()])]))
        for control in (None,{},[],{'schema_version':1,'sources':{}},
                        {'schema_version':1,'sources':{},'directory':{},'halted':None}):
            bad=copy.deepcopy(prior)
            if control is None:bad.pop('collector_state')
            else:bad['collector_state']=control
            t=Transport([]);out=run(t,bad,NOW+dt.timedelta(hours=4))
            self.assertEqual(t.calls,[]);self.assertTrue(out['coverage']['collection_halted'])
            self.assertEqual(len(out['events']),1);self.assertTrue(out['events'][0]['source_stale'])

    def test_corrupt_existing_source_records_never_dispatch(self):
        prior=run(Transport([directory(),FakeResponse([event()])]))
        mutations=[lambda s:s['sources'].__setitem__(KEY,None),
                   lambda s:s['sources'].__setitem__(KEY,'broken'),
                   lambda s:s['sources'][KEY].pop('next_fetch_at'),
                   lambda s:s['sources'][KEY].pop('last_attempt_at'),
                   lambda s:s['sources'][KEY].pop('observed_at'),
                   lambda s:s['sources'][KEY].pop('last_request_credits'),
                   lambda s:s['sources'][KEY].__setitem__('next_fetch_at',s['sources'][KEY]['last_attempt_at']),
                   lambda s:s['sources'][KEY].__setitem__('observed_at','2030-01-01T00:00:00Z'),
                   lambda s:s['sources'][KEY].__setitem__('last_request_credits','0'),
                   lambda s:s['sources'][KEY].__setitem__('last_request_credits',-1),
                   lambda s:s['sources'].pop(KEY),
                   lambda s:s['directory'].__setitem__('last_attempt_at','bad'),
                   lambda s:s.__setitem__('directory',None)]
        for mutate in mutations:
            bad=copy.deepcopy(prior);mutate(bad['collector_state'])
            t=Transport([]);out=run(t,bad,NOW+dt.timedelta(hours=4))
            self.assertEqual(t.calls,[]);self.assertTrue(out['coverage']['collection_halted'])

    def test_only_explicit_empty_object_bootstraps(self):
        for prior in (None,[],False,'',{'cache':{}},{'events':[]}):
            t=Transport([]);out=collect_events(CONFIG,prior,NOW,'TEST-ONLY-SECRET',t)
            self.assertEqual(t.calls,[]);self.assertTrue(out['coverage']['collection_halted'])

    def test_dst_window_uses_calendar_days_not_fixed_utc_duration(self):
        now=dt.datetime(2026,11,1,5,30,tzinfo=dt.timezone.utc)
        rows=[event('first','2026-11-01T05:00:00Z'),event('last','2026-11-09T05:59:59Z'),event('after','2026-11-09T06:00:00Z')]
        out=run(Transport([directory(),FakeResponse(rows)]),now=now)
        self.assertEqual([e['provider_event_id'] for e in out['events']],['first','last'])

    def test_corrupt_halt_and_previous_nonzero_cost_fail_closed(self):
        for state in ({'halted':'false'}, {'directory':{'last_request_credits':1}}):
            t=Transport([]);out=run(t,{'collector_state':state})
            self.assertEqual(t.calls,[]);self.assertTrue(out['coverage']['collection_halted'])

    def test_paid_endpoint_literal_is_absent_from_collector(self):
        import scripts.refresh_odds_api_events as module
        self.assertNotIn('/odds',Path(module.__file__).read_text())

    def test_default_transport_rejects_odds_routes_before_network(self):
        with patch('scripts.refresh_odds_api_events.build_opener',side_effect=AssertionError('network')):
            with self.assertRaises(ValueError):provider_get(ORIGIN+'/v4/sports/americanfootball_nfl/odds',{'apiKey':'x'})
            with self.assertRaises(ValueError):provider_get('https://other.invalid/v4/sports/',{'apiKey':'x'})

if __name__=='__main__':unittest.main()
