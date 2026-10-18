import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import shutil
import unittest
from unittest.mock import patch
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import publisher_access_policy as p

class PublisherPolicyTests(unittest.TestCase):
    def test_exact_domains_and_subdomains_not_school_substrings(self):
        for host in ['site.api.espn.com','sports.core.api.espn.com','sdataprod.ncaa.com','www.ncaa.com','www.itftennis.com','www.usta.com','reports.fiba.basketball','worldtour.fiba3x3.com','faw.cymru']:
            self.assertIn('Permission required',p.permission_hold_reason('https://'+host+'/'))
        for host in ['espn.com.example.org','smumustangs.com','huskers.com','gocreighton.com','omahamavs.com','www.atptour.com','www.wtatennis.com','ncaa.org']:
            self.assertIsNone(p.permission_hold_reason('https://'+host+'/'))

    def test_requests_send_trap_blocks_held_and_redirected_destinations(self):
        import requests
        old=requests.sessions.Session.send
        try:
            with patch.object(requests.sessions.Session,'send',return_value='allowed') as dispatch:
                p.install_network_guards()
                session=requests.Session()
                for url in ['https://site.api.espn.com/a','https://reports.fiba.basketball/a']:
                    request=requests.Request('GET',url).prepare()
                    with self.assertRaises(PermissionError):session.send(request)
                self.assertEqual(0,dispatch.call_count)
                self.assertEqual('allowed',session.send(requests.Request('GET','https://huskers.com/').prepare()))
                self.assertEqual(1,dispatch.call_count)
        finally:requests.sessions.Session.send=old

    def test_urllib_dispatch_trap_blocks_redirect_destination(self):
        old=urllib.request.OpenerDirector.open
        try:
            with patch.object(urllib.request.OpenerDirector,'open',return_value='allowed') as dispatch:
                p.install_network_guards()
                opener=urllib.request.build_opener()
                for url in ['https://www.itftennis.com/','https://www.usta.com/']:
                    with self.assertRaises(PermissionError):opener.open(urllib.request.Request(url))
                self.assertEqual(0,dispatch.call_count)
                self.assertEqual('allowed',opener.open('https://gocreighton.com/'))
        finally:urllib.request.OpenerDirector.open=old

    def test_real_requests_redirect_recursion_never_dispatches_held_host(self):
        import requests
        from requests.adapters import BaseAdapter
        calls=[]
        class RedirectAdapter(BaseAdapter):
            def send(self,request,**kwargs):
                calls.append(request.url)
                response=requests.Response();response.status_code=302
                response.headers['Location']='https://site.api.espn.com/held'
                response.url=request.url;response.request=request;response._content=b''
                return response
            def close(self):pass
        p.install_network_guards()
        session=requests.Session();session.mount('https://',RedirectAdapter())
        with self.assertRaises(PermissionError):session.get('https://allowed.example/start')
        self.assertEqual(['https://allowed.example/start'],calls)

    def test_real_urllib_redirect_recursion_never_dispatches_held_host(self):
        import io
        from email.message import Message
        from urllib.response import addinfourl
        calls=[]
        class RedirectHandler(urllib.request.BaseHandler):
            handler_order=100
            def http_open(self,request):
                calls.append(request.full_url)
                headers=Message();headers['Location']='http://www.itftennis.com/held'
                response=addinfourl(io.BytesIO(b''),headers,request.full_url,302)
                response.msg='Found'
                return response
        p.install_network_guards()
        opener=urllib.request.build_opener(RedirectHandler())
        with self.assertRaises(PermissionError):opener.open('http://allowed.example/start')
        self.assertEqual(['http://allowed.example/start'],calls)

    def test_paused_snapshot_preserves_observations_and_original_time(self):
        original={'generated_at':'2026-10-17T01:00:00Z','events':[{'id':'old','age_risk':True,'checked_at':'old'}], 'sources':[{'id':'x','ok':True,'checked_at':'old'}],'teams':[{'id':'team','athletes':[{'dob':'2009-01-01'}]}]}
        before=copy.deepcopy(original)
        saved=p.paused_snapshot(original,'Permission required',dt.datetime(2026,10,18,tzinfo=dt.timezone.utc))
        self.assertEqual(before,original);self.assertEqual(original['generated_at'],saved['generated_at'])
        self.assertEqual(original['teams'],saved['teams']);self.assertEqual('old',saved['events'][0]['checked_at'])
        self.assertTrue(saved['events'][0]['age_risk']);self.assertTrue(saved['stale']);self.assertFalse(saved['sources'][0]['ok'])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.json';path.write_text(json.dumps(original))
            self.assertTrue(p.preserve_snapshot_on_hold(path,'https://sdataprod.ncaa.com/'))
            self.assertEqual(original['generated_at'],json.loads(path.read_text())['generated_at'])

    def test_retained_routed_source_events_are_not_freshened(self):
        source={'id':'atp','endpoint':'https://site.api.espn.com/tennis','name_routing':[{'source_id':'tennis-wimbledon-men'}]}
        previous={'events':[{'id':'a','source_id':'atp'},{'id':'b','source_id':'tennis-wimbledon-men','source_endpoint':source['endpoint']},{'id':'c','source_id':'other'}]}
        retained=p.retained_source_events(previous,source,'Permission required')
        self.assertEqual(['a','b'],[e['id'] for e in retained]);self.assertTrue(all(e['stale'] for e in retained));self.assertNotIn('stale',previous['events'][0])

    def test_reference_link_does_not_pause_allowed_endpoint(self):
        self.assertIsNone(p.source_permission_hold_reason({'source_type':'official-event-window','endpoint':'https://www.ncaa.org/calendar','official_schedule_url':'https://www.ncaa.com/games'}))
        self.assertIsNone(p.source_permission_hold_reason({'source_type':'coverage-gap','official_schedule_url':'https://www.fiba.basketball/'}))
        self.assertIsNone(p.source_permission_hold_reason({'source_type':'official-event-window','endpoint_validation':'published-window','endpoint':'https://worldtour.fiba3x3.com/2026/calendar'}))
        self.assertIsNotNone(p.source_permission_hold_reason({'source_type':'tennis-intelligence','official_schedule_url':'https://www.itftennis.com/'}))

    def test_shared_endpoint_does_not_duplicate_other_sources(self):
        prior={'events':[{'id':'one','source_id':'ncaa-football-fbs','source_endpoint':'https://site.api.espn.com/football'}]}
        result=[]
        for ident in ('ncaa-football','ncaa-football-fbs','ncaa-football-fcs'):
            result.extend(p.retained_source_events(prior,{'id':ident,'endpoint':'https://site.api.espn.com/football'},'Permission required'))
        self.assertEqual(['one'],[r['id'] for r in result])

    def test_dedicated_snapshot_scripts_preserve_saved_payloads_offline(self):
        for script,filename in [('refresh_ncaa_basketball','ncaa-basketball.json'),('refresh_ncaa_basketball_di_map','ncaa-basketball-di-map.json'),('refresh_ncaa_basketball_rosters','ncaa-basketball-rosters.json')]:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'scripts').mkdir();(root/'data').mkdir()
                for name in (script,'publisher_access_policy'):
                    shutil.copy(ROOT/'scripts'/f'{name}.py',root/'scripts'/f'{name}.py')
                saved={'generated_at':'2026-10-17T00:00:00Z','events':[{'id':'event','u18_risk':True}], 'teams':[{'id':'team','athletes':[{'name':'Saved Person'}]}]}
                path=root/'data'/filename;path.write_text(json.dumps(saved))
                subprocess.run([sys.executable,str(root/'scripts'/f'{script}.py')],check=True,capture_output=True)
                result=json.loads(path.read_text())
                self.assertEqual(saved['generated_at'],result['generated_at'])
                self.assertEqual(saved['teams'],result['teams']);self.assertEqual('event',result['events'][0]['id'])
                self.assertTrue(result['events'][0]['u18_risk']);self.assertTrue(result['collection_paused'])

    def test_global_hold_preserves_saved_calendar_and_no_requests(self):
        text=(ROOT/'scripts/refresh_global_schedule.py').read_text()
        a=text.index('    hold_reason=source_permission_hold_reason(source)')
        b=text.index('    count=0',a)
        ns={'sources':[{'id':'golf-pga','endpoint':'https://site.api.espn.com/golf'}],
            'previous_schedule':{'events':[{'id':'one','source_id':'golf-pga'}],
                'tour_calendars':[{'source_id':'golf-pga','events':[{'event_id':'future'}]}],
                'sources':[{'id':'golf-pga','checked_at':'original','published_fixtures':25}]},
            'events':[],'tour_calendars':[],'source_status':[],'NOW_UTC':dt.datetime.now(dt.timezone.utc),
            'deepcopy':copy.deepcopy,'source_permission_hold_reason':p.source_permission_hold_reason,
            'retained_source_events':p.retained_source_events}
        exec('for source in sources:\n'+text[a:b],ns)
        self.assertEqual('future',ns['tour_calendars'][0]['events'][0]['event_id'])
        self.assertTrue(ns['tour_calendars'][0]['source_stale'])
        self.assertEqual('original',ns['source_status'][0]['checked_at'])
        self.assertEqual(25,ns['source_status'][0]['published_fixtures'])
        self.assertFalse(ns['source_status'][0]['ok'])

    def test_actual_entrypoints_install_dispatch_guard(self):
        names=['refresh_global_schedule','refresh_public_data','refresh_ncaa_football','refresh_ncaa_basketball','refresh_ncaa_basketball_di_map','refresh_ncaa_basketball_rosters','research_ncaa_basketball_ages','refresh_nebraska_collegiate','refresh_nebraska_collegiate_futures']
        for name in names:self.assertIn('install_network_guards()', (ROOT/'scripts'/f'{name}.py').read_text())
        for name in ['refresh_ncaa_basketball','refresh_ncaa_basketball_di_map','refresh_ncaa_basketball_rosters']:
            text=(ROOT/'scripts'/f'{name}.py').read_text();self.assertLess(text.index('preserve_snapshot_on_hold(DATA'),text.index('requests.get('))
        self.assertIn('publisherCollectionHold',(ROOT/'index.html').read_text())

if __name__=='__main__':unittest.main()
