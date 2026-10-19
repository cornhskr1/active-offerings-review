import copy
import json
from pathlib import Path
import unittest
from datetime import datetime, timezone
from scripts.official_school_calendar import collect_school_calendar, parse_calendar, discover_calendar, date_value, clean_opponent

ROOT=Path(__file__).resolve().parents[1]
SOURCES=json.loads((ROOT/'data/official-school-calendar-sources.json').read_text())['sources']
SOURCE=next(s for s in SOURCES if s['id']=='official-nebraska-football')
NOW='2026-10-19T00:00:00+00:00'

def event(uid='one',start='DTSTART;VALUE=DATE:20261031',extra='',summary='Football -  Nebraska vs. Example'):
    return f'BEGIN:VEVENT\nUID:{uid}\n{start}\nSUMMARY:{summary}\nLOCATION:Lincoln\\, Neb.\n{extra}\nEND:VEVENT\n'
def calendar(events=None):
    return 'BEGIN:VCALENDAR\nVERSION:2.0\nX-PUBLISHED-TTL:PT3600M\n'+(event() if events is None else events)+'END:VCALENDAR\n'
class Response:
    status_code=200
    def __init__(self,body):self.text=body

def graph_page(sid=1943,season=274,title='2026-27',conflict=False):
    nodes=[]
    def add(v):
        index=len(nodes);nodes.append(None)
        if isinstance(v,dict):nodes[index]={k:add(x) for k,x in v.items()}
        elif isinstance(v,list):nodes[index]=[add(x) for x in v]
        else:nodes[index]=v
        return index
    add([{'id':18,'title':"Men's Basketball",'gender':'m','scheduleId':sid},
         {'scheduleId':sid+1 if conflict else sid,'seasonTitle':title,'isCurrent':True,'globalSportNameSlug':'mens-basketball','seasonId':season}])
    return '<script id="__NUXT_DATA__">'+json.dumps(nodes)+'</script>'
class CalendarTests(unittest.TestCase):
    def test_exact_inventory(self):
        self.assertEqual(len(SOURCES),16);self.assertEqual(len({s['id'] for s in SOURCES}),16)
        self.assertEqual(sum(s['sport']=='Football' for s in SOURCES),1)
    def test_minimal_date_only_and_ttl(self):
        rows,meta=parse_calendar(calendar(event(extra='DESCRIPTION:must not retain\nURL:https://example.test/logo.png')),SOURCE,'rolling')
        self.assertEqual(meta['ttl_seconds'],216000);self.assertTrue(rows[0]['date_only']);self.assertIsNone(rows[0]['start_time'])
        self.assertEqual(rows[0]['site'],'UNKNOWN');self.assertNotIn('must not retain',json.dumps(rows));self.assertNotIn('logo.png',json.dumps(rows))
        self.assertEqual(rows[0]['source_url'],SOURCE['schedule_url'])
    def test_time_and_dst(self):
        day,start,_,unknown=date_value({'TZID':'America/Chicago'},'20261024T190000')
        self.assertEqual(start,'2026-10-25T00:00:00+00:00');self.assertEqual(day,'2026-10-24');self.assertFalse(unknown)
        for value in ['20261101T013000','20260308T023000']:
            self.assertTrue(date_value({'TZID':'America/Chicago'},value)[3])
        self.assertTrue(date_value({},'20261024T190000')[3])
        self.assertTrue(date_value({'TZID':'Unknown/Place'},'20261024T190000')[3])
    def test_cache_ttl_no_request(self):
        first=collect_school_calendar(SOURCE,{},NOW,lambda *a,**k:Response(calendar()))
        def trap(*a,**k):raise AssertionError('request before TTL')
        second=collect_school_calendar(SOURCE,first['cache'],'2026-10-21T11:59:59Z',trap)
        self.assertEqual(second['source_status']['status'],'cached');self.assertEqual(first['cache'],second['cache'])
    def test_failed_empty_and_malformed_keep_last_good(self):
        first=collect_school_calendar(SOURCE,{},NOW,lambda *a,**k:Response(calendar()))
        for body in [calendar(''),'not ICS',calendar(event(extra='RRULE:FREQ=DAILY'))]:
            result=collect_school_calendar(SOURCE,first['cache'],'2026-10-22T00:00:00Z',lambda *a,**k:Response(body))
            self.assertFalse(result['source_status']['ok']);self.assertTrue(result['events'][0]['source_stale']);self.assertEqual(result['cache']['events'],first['cache']['events']);self.assertEqual(result['cache']['fetched_at'],first['cache']['fetched_at'])
    def test_update_cancel_remove(self):
        first=collect_school_calendar(SOURCE,{},NOW,lambda *a,**k:Response(calendar(event()+event('two'))))
        result=collect_school_calendar(SOURCE,first['cache'],'2026-10-22T00:00:00Z',lambda *a,**k:Response(calendar(event(start='DTSTART:20261101T000000Z',extra='STATUS:CANCELLED\nSEQUENCE:1'))))
        by={r['uid']:r for r in result['events']}
        self.assertEqual(by['one']['status'],'CANCELLED');self.assertEqual(by['one']['sequence'],1)
        self.assertEqual(by['two']['status'],'REMOVED');self.assertEqual(result['source_status']['removed_uids'],['two'])
    def test_conflicting_uid_and_sequence(self):
        with self.assertRaises(ValueError):parse_calendar(calendar(event()+event(start='DTSTART;VALUE=DATE:20261102')),SOURCE,'rolling')
        first=collect_school_calendar(SOURCE,{},NOW,lambda *a,**k:Response(calendar(event(extra='SEQUENCE:2'))))
        result=collect_school_calendar(SOURCE,first['cache'],'2026-10-22T00:00:00Z',lambda *a,**k:Response(calendar()))
        self.assertFalse(result['source_status']['ok'])
    def test_dynamic_season_routes(self):
        source=SOURCES[0]
        url,season=discover_calendar(graph_page(),source)
        self.assertIn('scheduleId=1943',url);self.assertEqual(season,'274:1943:2026-27')
        url,season=discover_calendar(graph_page(2000,280,'2027-28'),source)
        self.assertIn('scheduleId=2000',url);self.assertEqual(season,'280:2000:2027-28')
        with self.assertRaises(ValueError):discover_calendar(graph_page(conflict=True),source)
    def test_rollover_retains_prior_future_not_removed(self):
        source=SOURCES[0];prior={'source_id':source['id'],'season_id':'old','events':[{'uid':'old','date':'2027-01-01','status':'CONFIRMED','season_id':'old'}]}
        def get(url,**kwargs):return Response(graph_page() if '/sports/' in url else calendar(event(summary="Creighton University Men's Basketball vs Example")))
        result=collect_school_calendar(source,prior,NOW,get)
        self.assertTrue(result['source_status']['ok']);old=next(r for r in result['events'] if r['uid']=='old')
        self.assertTrue(old['source_stale']);self.assertEqual(old['status'],'CONFIRMED');self.assertEqual(result['source_status']['removed_uids'],[])
        again=collect_school_calendar(source,result['cache'],'2026-10-22T00:00:00Z',get)
        old=next(r for r in again['events'] if r['uid']=='old')
        self.assertEqual(old['status'],'CONFIRMED');self.assertEqual(again['source_status']['removed_uids'],[])
    def test_summary_cancel_and_other_school_exclusion(self):
        source={**SOURCES[0],'calendar_url':'https://gocreighton.com/example.ics'}
        rows,_=parse_calendar(calendar(event(summary="CANCELLED Creighton University Men's Basketball vs Example")),source,'season')
        self.assertEqual(rows[0]['status'],'CANCELLED')
        softball=next(s for s in SOURCES if s['id']=='official-nebraska-softball')
        rows,meta=parse_calendar(calendar(event(summary='Softball -  Other University vs. Example')),softball,'rolling')
        self.assertEqual(rows,[]);self.assertEqual(meta['excluded_non_school_events'],1)
    def test_explicit_result_not_inferred_from_clock(self):
        source={**SOURCES[0],'calendar_url':'https://gocreighton.com/example.ics'}
        for marker,status in [('W','COMPLETED'),('L','COMPLETED'),('T','COMPLETED'),('N','CONFIRMED')]:
            rows,_=parse_calendar(calendar(event(summary=f"[{marker}] Creighton University Men's Basketball vs Example")),source,'season')
            self.assertEqual(rows[0]['status'],status)
    def test_exact_promotion_suffixes_only(self):
        self.assertEqual(clean_opponent('Concordia (Neb.)- Exhibition | Free To Attend'),('Concordia (Neb.)','exhibition'))
        self.assertEqual(clean_opponent('North Dakota- Pink Out | Rally Towel Giveaway'),('North Dakota',None))
        self.assertEqual(clean_opponent('North Dakota- Time changed from 1 p.m. CT'),('North Dakota',None))
        self.assertEqual(clean_opponent('Wisconsin - Milwaukee'),('Wisconsin - Milwaukee',None))
        self.assertEqual(clean_opponent('Gardner-Webb'),('Gardner-Webb',None))
    def test_no_naive_now_or_redirect(self):
        with self.assertRaises(ValueError):collect_school_calendar(SOURCE,{},datetime(2026,10,19),lambda *a,**k:None)
        def get(*args,**kwargs):
            self.assertFalse(kwargs['allow_redirects']);r=Response('');r.status_code=302;return r
        result=collect_school_calendar(SOURCE,{},NOW,get);self.assertFalse(result['source_status']['ok'])
    def test_failure_retry_also_honors_sixty_hours(self):
        first=collect_school_calendar(SOURCE,{},NOW,lambda *a,**k:Response('bad'))
        def trap(*a,**k):raise AssertionError('early retry')
        second=collect_school_calendar(SOURCE,first['cache'],'2026-10-21T11:59:59Z',trap)
        self.assertFalse(second['source_status']['ok']);self.assertEqual(second['cache'],first['cache'])
        self.assertNotIn('early retry',second['source_status']['reason'])
    def test_held_endpoint_not_requested(self):
        source={**SOURCE,'calendar_url':'https://www.espn.com/held'}
        def trap(*a,**k):raise AssertionError('held endpoint dispatched')
        result=collect_school_calendar(source,{},NOW,trap)
        self.assertFalse(result['source_status']['ok']);self.assertNotIn('dispatched',result['source_status']['reason'])
if __name__=='__main__':unittest.main()
