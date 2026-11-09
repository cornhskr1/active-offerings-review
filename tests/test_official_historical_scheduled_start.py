"""Reduced captured preview nodes and synthetic HTTP/cache tests; no live requests."""
from copy import deepcopy
from pathlib import Path
import hashlib
import sys
import unittest
from unittest.mock import patch
from scripts import official_historical_scheduled_start as timing
from scripts.official_historical_school_result import SPECS, collect_result, collect_results

ROOT = Path(__file__).parent / 'fixtures'
NOW = '2026-11-09T14:00:00Z'
BODIES = [(ROOT / ('nebraska-' + name + '-scheduled-preview.html')).read_text() for name in ('football','volleyball')]
RESULTS = [(ROOT / name).read_text() for name in ('nebraska-illinois-result-20261109.html','nebraska-oregon-result-20261109.html')]
class Response:
    status_code = 200
    def __init__(self,text='',content=b''): self.text=text; self.content=content

class HistoricalStartTests(unittest.TestCase):
    def setup_result(self,i=1):
        spec=SPECS[i]
        original={**spec['expected'],'uid':spec['uid'],'source_id':spec['calendar_source_id'],'status':spec['original_statuses'][0],'time_unknown':True}
        rows,status,cache=collect_result([original],{},NOW,lambda *a,**k:Response(RESULTS[i]),spec)
        return spec,original,rows[0],status,cache

    def test_exact_preview_facts_and_zone_rollover(self):
        for i,spec in enumerate(SPECS):
            self.assertIn(timing.TIMING_SPECS[spec['event_id']]['source_time'],timing.parse_preview(BODIES[i],spec))
            self.assertEqual(timing.identity(spec)['start_time'],('2026-11-07T01:00:00+00:00','2026-11-08T03:00:00+00:00')[i])

    def test_wrong_year_program_teams_date_zone_missing_time_and_duplicate(self):
        mutations=[ [('Football','Volleyball'),('2026','2025'),('November 02','November 03'),('Illinois','Rutgers'),('Champaign, Ill.','Lincoln, Neb.'),('7 p.m. CT','7 p.m. PT'),('7 p.m. CT','7 p.m.'),('7 p.m. CT','TBA'),(timing.PDF_URL,timing.PDF_URL+'?other=1')], [('Volleyball','Football'),('2026','2025'),('November 05','November 04'),('Saturday, Nov. 7','Saturday, Nov. 8'),('Nebraska at No. 12 Oregon','Oregon at No. 12 Nebraska'),('9 p.m. CT','9 p.m. PT'),('9 p.m. CT','9 p.m.'),('9 p.m. CT','TBA')]]
        for i,spec in enumerate(SPECS):
            for old,new in mutations[i]:
                with self.subTest(sport=spec['expected']['sport'],old=old),self.assertRaises(ValueError):timing.parse_preview(BODIES[i].replace(old,new),spec)
            with self.assertRaises(ValueError):timing.parse_preview(BODIES[i]+BODIES[i],spec)
            for word in ('Canceled','Cancelled','Postponed','Suspended','Abandoned'):
                with self.assertRaises(ValueError):timing.parse_preview(BODIES[i]+'<p>'+word+'</p>',spec)

    def test_oregon_time_cannot_come_from_washington_or_script(self):
        body=BODIES[1]
        for bad in (body.replace('<strong>First Serve: </strong>9 p.m. CT<br />',''),body.replace('9 p.m. CT','TBA').replace('5:30 p.m. CT','9 p.m. CT'),body.replace('<strong>First Serve: </strong>9 p.m. CT<br />','').replace('Sunday, Nov. 8','Sunday, November 8').replace('5:30 p.m. CT','9 p.m. CT'),body.replace('9 p.m. CT','TBA')+'<script>First Serve: 9 p.m. CT</script>',body.replace('9 p.m. CT','9 p.m. CT First Serve: 5:30 p.m. CT')):
            with self.assertRaises(ValueError):timing.parse_preview(bad,SPECS[1])

    def test_pdf_byte_pin_redirect_and_size_guards(self):
        raw=b'%PDF-1.7 synthetic pin mechanism fixture, not official sporting evidence';calls=[]
        def get(url,**kwargs):calls.append((url,kwargs));return Response(content=raw)
        self.assertEqual(timing.PDF_SHA256,'b64c9ed82e4985c013dc47fd48fc59086745cf60a3d3abef9ef14d91db21546e')
        with self.assertRaises(ValueError):timing.fetch_football_notes(get)
        with patch.object(timing,'PDF_SHA256',hashlib.sha256(raw).hexdigest()):
            self.assertEqual(timing.fetch_football_notes(get),(timing.PDF_DATE_EVIDENCE,hashlib.sha256(raw).hexdigest()))
            for changed in (raw+b'altered date',raw+b'altered year',raw+b'altered teams',b'not PDF',b'%PDF-'+b'x'*10_000_001):
                with self.assertRaises(ValueError):timing.fetch_football_notes(lambda *a,**k:Response(content=changed))
        self.assertTrue(all(u==timing.PDF_URL and k['allow_redirects'] is False for u,k in calls))
        response=Response(content=raw);response.status_code=302
        with self.assertRaises(ValueError):timing.fetch_football_notes(lambda *a,**k:response)

    def test_independent_cache_and_truthful_fetch_timestamps(self):
        spec,original,row,status,cache=self.setup_result();before=deepcopy((original,row,status,cache));calls=[]
        def get(*a,**k):calls.append(1);return Response(BODIES[1])
        evidence,saved=timing.collect_scheduled_start(row,status,{},NOW,get,spec)
        self.assertTrue(evidence['ok']);self.assertEqual(len(calls),1);self.assertEqual((original,row,status,cache),before)
        self.assertTrue(row['date_only']);self.assertTrue(row['time_unknown']);self.assertIsNone(row['start_time'])
        again,unchanged=timing.collect_scheduled_start(row,status,saved,'2026-11-10T14:00:00Z',get,spec)
        self.assertEqual(len(calls),1);self.assertEqual(again['status'],'cached');self.assertEqual(again['fetched_at'],evidence['fetched_at']);self.assertEqual(saved,unchanged)
        status={**status,'fetched_at':'2026-11-12T14:00:00Z','next_fetch_at':'2026-11-15T02:00:00Z'}
        failed,retry=timing.collect_scheduled_start(row,status,saved,'2026-11-12T14:00:00Z',lambda *a,**k:Response('bad'),spec)
        self.assertFalse(failed['ok']);self.assertEqual(failed['fetched_at'],evidence['fetched_at']);self.assertEqual(failed['next_fetch_at'],evidence['next_fetch_at']);self.assertEqual(row,before[1])
        def trap(*a,**k):raise AssertionError('No fetch during retry TTL')
        failed2,retry2=timing.collect_scheduled_start(row,status,retry,'2026-11-13T14:00:00Z',trap,spec)
        self.assertFalse(failed2['ok']);self.assertEqual(retry,retry2)

    def test_first_failure_retries_without_fabricated_observation(self):
        spec,_,row,status,_=self.setup_result();calls=[]
        def get(*a,**k):calls.append(1);return Response('bad')
        evidence,saved=timing.collect_scheduled_start(row,status,{},NOW,get,spec)
        self.assertIsNone(evidence);self.assertNotIn('evidence',saved);self.assertNotIn('fetched_at',saved)
        evidence,again=timing.collect_scheduled_start(row,status,saved,'2026-11-10T14:00:00Z',get,spec)
        self.assertIsNone(evidence);self.assertEqual(len(calls),1);self.assertEqual(saved,again)

    def test_unhealthy_future_wrong_or_expired_result_never_collects(self):
        spec,_,row,status,_=self.setup_result()
        def trap(*a,**k):raise AssertionError('Ineligible timing fetch')
        for key,value in [('source_stale',True),('status','CANCELLED'),('date','2025-11-07'),('sport','Football'),('opponent','Washington'),('location','Lincoln, Neb.'),('historical_calendar_uid','wrong')]:
            evidence,_=timing.collect_scheduled_start({**row,key:value},status,{},NOW,trap,spec);self.assertIsNone(evidence)
        for key,value in [('ok',False),('status','stale'),('sport','Football'),('fetched_at','2026-11-10T14:00:00Z'),('fetched_at','2026-11-07T04:00:00Z'),('next_fetch_at',NOW)]:
            evidence,_=timing.collect_scheduled_start(row,{**status,key:value},{},NOW,trap,spec);self.assertIsNone(evidence)
        evidence,_=timing.collect_scheduled_start(row,status,{},'2027-02-06T14:00:00Z',trap,spec);self.assertIsNone(evidence)

    def test_future_or_corrupt_timing_cache_never_promoted(self):
        spec,_,row,status,_=self.setup_result();evidence,saved=timing.collect_scheduled_start(row,status,{},NOW,lambda *a,**k:Response(BODIES[1]),spec)
        for key,value in [('fetched_at','2026-11-10T14:00:00Z'),('next_fetch_at','2026-12-10T14:00:00Z'),('date','2025-11-07'),('sport','Football'),('source_url','https://example.org'),('timezone','UTC')]:
            failed,_=timing.collect_scheduled_start(row,status,{'evidence':{**evidence,key:value}},NOW,lambda *a,**k:Response('bad'),spec);self.assertIsNone(failed)

    def test_combined_collection_preserves_originals_and_location_on_timing_failure(self):
        originals=[self.setup_result(i)[1] for i in (0,1)];before=deepcopy(originals)
        def get(url,**kwargs):
            for i,spec in enumerate(SPECS):
                if url==spec['url']:return Response(RESULTS[i])
                if url==timing.TIMING_SPECS[spec['event_id']]['source_url']:return Response(BODIES[i])
            raise AssertionError('Unexpected URL '+url)
        with patch.object(sys.modules[collect_results.__globals__['collect_scheduled_start'].__module__],'fetch_football_notes',return_value=(timing.PDF_DATE_EVIDENCE,timing.PDF_SHA256)):
            rows,statuses,cache=collect_results(originals,{},NOW,get)
        self.assertEqual(originals,before);self.assertEqual(len(rows),2);self.assertTrue(all(r['scheduled_start_evidence']['ok'] for r in rows))
        self.assertTrue(all(r['start_time'] is None and r['time_unknown'] for r in rows));self.assertTrue(all('scheduled_start_evidence' not in c['events'][0] for c in cache.values()))
        rows,statuses,_=collect_results(originals,{},NOW,lambda url,**k:Response(RESULTS[0] if url==SPECS[0]['url'] else RESULTS[1] if url==SPECS[1]['url'] else 'unavailable'))
        self.assertEqual(len(rows),2);self.assertTrue(all(s['ok'] for s in statuses));self.assertTrue(all('scheduled_start_evidence' not in r for r in rows))
        for bad in ([originals[0],originals[0]],[{**originals[0],'status':'CANCELLED'}]):
            rows,_,_=collect_results(bad,{},NOW,get);self.assertEqual(rows,[])

    def test_malformed_optional_cache_never_aborts_location(self):
        spec,original,row,status,cache=self.setup_result()
        for corrupt in (['corrupt-cache'],'corrupt-cache',27,True):
            with self.subTest(cache=corrupt):
                previous=deepcopy(cache);previous['scheduled_start']=corrupt
                rows,statuses,saved=collect_results([original],{spec['source_id']:previous},NOW,lambda *a,**k:Response('bad'))
                self.assertEqual(len(rows),1);self.assertTrue(next(s for s in statuses if s['id']==spec['source_id'])['ok'])
                self.assertNotIn('scheduled_start_evidence',rows[0])
