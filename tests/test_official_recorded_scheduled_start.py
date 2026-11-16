"""Synthetic timing articles and result identities; no report or patron data."""
from copy import deepcopy
import unittest
from scripts import official_recorded_scheduled_start as t
NOW = '2026-11-16T12:00:00Z'
MSU = '<div>Football September 14, 2026</div><h1>Huskers-Michigan State Football Kickoff Time Set</h1><p>Nebraska’s Big Ten opener at Michigan State on Saturday, Sept. 26, will kickoff at 4 p.m. (CT).</p>'
WASHINGTON = '<div>Volleyball November 05, 2026</div><h1>VB Preview: at No. 12 Oregon &amp; No. 18 Washington</h1><p>Saturday, Nov. 7 - No. 1 Nebraska at No. 12 Oregon<br>First Serve: 9 p.m. CT<br>Radio: example</p><p>Sunday, Nov. 8 - No. 1 Nebraska at No. 18 Washington<br>First Serve: 5:30 p.m. CT<br>Radio: example</p>'
class Response:
    status_code = 200
    def __init__(self, text): self.text = text

def row(event_id):
    s=t.SPECS[event_id]
    return dict(id=f"official-nebraska-{s['program']}:result:{event_id}",uid='official-result-'+event_id,
        publisher_event_id=event_id,source_id=f"official-nebraska-{s['program']}",
        source_url=f"https://huskers.com/sports/{s['program']}/schedule",season_id='official-result:2026',school='Nebraska',
        **{k:s[k] for k in ('sport','opponent','date','location')},site='AWAY',status='COMPLETED',
        evidence_kind='recorded-official-school-result',archive_latest_kind='published',archive_conflict_fields=[],observation_id='a'*64)

class RecordedTimingTests(unittest.TestCase):
    def test_exact_times_separate_cache_and_unchanged_history(self):
        h={'events':[row('21843'),row('25155')]};before=deepcopy(h);calls=[]
        def get(url,**kwargs):
            calls.append((url,kwargs));return Response(MSU if 'kickoff' in url else WASHINGTON)
        evidence,cache=t.collect_starts(h,{},NOW,get)
        self.assertEqual(len(evidence),2);self.assertEqual(h,before)
        self.assertEqual([e['start_time'] for e in evidence],['2026-09-26T21:00:00+00:00','2026-11-08T23:30:00+00:00'])
        self.assertTrue(all(e['actual_start_verified'] is False and e['start_time_kind']=='scheduled' for e in evidence))
        self.assertTrue(all('historical_calendar_uid' not in e for e in evidence))
        again,unchanged=t.collect_starts(h,cache,'2026-11-17T12:00:00Z',get)
        self.assertEqual(len(calls),2);self.assertEqual(cache,unchanged);self.assertTrue(all(e['status']=='cached' for e in again))
        self.assertTrue(all(k['allow_redirects'] is False for _,k in calls))

    def test_wrong_identity_duplicate_and_conflict_do_not_fetch(self):
        def trap(*a,**k): raise AssertionError('must not fetch')
        for key,value in [('sport','Men\'s Volleyball'),('date','2025-11-08'),('opponent','Oregon'),('site','HOME'),('location','Lincoln, Neb.'),('source_id','other'),('observation_id','bad'),('archive_conflict_fields',['score']),('archive_latest_kind','removed')]:
            bad={**row('25155'),key:value};self.assertEqual(t.collect_starts({'events':[bad]}, {},NOW,trap)[0],[])
        self.assertEqual(t.collect_starts({'events':[row('25155'),row('25155')]},{},NOW,trap)[0],[])

    def test_wrong_program_year_date_time_timezone_duplicates_and_cancel(self):
        for event_id,body,changes in [('21843',MSU,[('Football','Volleyball'),('2026','2025'),('Sept. 26','Sept. 27'),('Michigan State on','Illinois on'),('4 p.m. (CT)','4 p.m. (PT)')]),('25155',WASHINGTON,[('Volleyball','Football'),('2026','2025'),('Sunday, Nov. 8','Sunday, Nov. 9'),('5:30 p.m. CT','TBA'),('5:30 p.m. CT','5:30 p.m. PT')])]:
            for old,new in changes:
                with self.subTest(old=old),self.assertRaises(ValueError):t.parse_preview(body.replace(old,new),event_id)
            for bad in [body+body,body+'<p>Postponed</p>',body+'<p>Cancelled</p>']:
                with self.assertRaises(ValueError):t.parse_preview(bad,event_id)
        with self.assertRaises(ValueError):t.parse_preview(WASHINGTON.replace('5:30 p.m. CT','TBA').replace('9 p.m. CT','5:30 p.m. CT'),'25155')
        with self.assertRaises(ValueError):t.parse_preview(WASHINGTON.replace('5:30 p.m. CT','TBA')+'<script>First Serve: 5:30 p.m. CT</script>','25155')

    def test_failed_expired_future_or_corrupt_evidence_stays_missing_and_cooldown_retained(self):
        h={'events':[row('21843')]};e,c=t.collect_starts(h,{},NOW,lambda *a,**k:Response(MSU))
        for key,value in [('fetched_at','2026-11-20T00:00:00Z'),('next_fetch_at',NOW),('next_fetch_at','2027-01-01T00:00:00Z'),('result_observation_id','b'*64),('actual_start_verified',True),('source_sha256','bad')]:
            bad=deepcopy(c);bad['21843']['evidence'][key]=value
            missing,_=t.collect_starts(h,bad,NOW,lambda *a,**k:Response('unavailable'));self.assertEqual(missing,[])
        missing,retry=t.collect_starts(h,c,'2026-11-19T12:00:00Z',lambda *a,**k:Response('unavailable'));self.assertEqual(missing,[])
        def trap(*a,**k):raise AssertionError('cooldown')
        self.assertEqual(t.collect_starts(h,retry,'2026-11-20T12:00:00Z',trap)[0],[])
        response=Response(MSU);response.status_code=301
        self.assertEqual(t.collect_starts(h,{},NOW,lambda *a,**k:response)[0],[])
