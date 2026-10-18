"""Provider-wide safety and completeness checks; all payloads here are synthetic."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import requests
from thesportsdb_fixture_adapter import BASE, PublicClient, collect, parse_event

UTC = dt.timezone.utc
TZ = ZoneInfo('America/Chicago')
FIRST, LAST = dt.date(2026, 10, 18), dt.date(2026, 10, 25)
NOW = dt.datetime(2026, 10, 18, 12, tzinfo=UTC)
SOURCE = {'id':'test-league', 'source_type':'thesportsdb', 'league_id':'4478',
          'sport':'Basketball', 'league':'Synthetic league', 'region':'Test',
          'endpoint':BASE+'eventsnextleague.php'}
EVENT = {'idEvent':'123456', 'idLeague':'4478', 'strSport':'Basketball',
         'strHomeTeam':'Home', 'strAwayTeam':'Away', 'strTimestamp':'2026-10-18T16:10:00',
         'strSeason':'2026-2027', 'strStatus':'NS', 'intRound':'5'}


def response(status=200, data=None, headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.json.return_value = {'events':None} if data is None else data
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(f'{status} response')
    return result


class FixtureTests(unittest.TestCase):
    def test_exact_named_utc_fixture_and_offsets(self):
        parsed = parse_event(SOURCE, EVENT)
        self.assertEqual('Away at Home', parsed['name'])
        self.assertEqual('2026-10-18T16:10:00Z', parsed['start_time'])
        self.assertEqual('partial', parsed['coverage_status'])
        for timestamp in ('2026-10-18T16:10:00Z', '2026-10-18T19:10:00+03:00'):
            self.assertEqual(parsed, parse_event(SOURCE, {**EVENT,'strTimestamp':timestamp}))

    def test_explicit_utc_date_and_time_fallback(self):
        event = {**EVENT, 'strTimestamp':None, 'dateEvent':'2026-10-18', 'strTime':'16:10'}
        self.assertEqual('2026-10-18T16:10:00Z', parse_event(SOURCE,event)['start_time'])

    def test_identity_opponents_season_and_time_fail_closed(self):
        for changes in ({'idLeague':'other'}, {'strSport':'Soccer'}, {'idEvent':''},
                        {'strHomeTeam':'TBD'}, {'strAwayTeam':''}, {'strHomeTeam':'Away'},
                        {'strTimestamp':None}, {'strTimestamp':'2026-10-18'},
                        {'strTimestamp':'1697670000'}, {'strTimestamp':'2026-10-18T00:00:00'},
                        {'strTimestamp':'2026-10-18T99:00:00'}, {'strSeason':'2024-2025'},
                        {'strSeason':'2026-2028'}, {'strSeason':None}, {'intRound':'400'},
                        {'intRound':'500'}, {'strEvent':'League preseason'},
                        {'strStatus':'TBD'}, {'strStatus':'POST'}, {'strStatus':'CANC'},
                        {'strPostponed':'yes'}, {'strStatus':'INTR'}, {'strStatus':'INT'}, {'strStatus':'Q1'}, {'strStatus':'P1'}, {'strStatus':'IN1'}, {'strStatus':'unknown'}, {'strStatus':None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_event(SOURCE, {**EVENT, **changes})

    def test_limited_and_empty_results_are_not_complete_or_offseason(self):
        for rows in ([EVENT], [], None):
            client=Mock();client.json.return_value={'events':rows}
            events, report=collect(SOURCE,FIRST,LAST,TZ,NOW,client)
            self.assertTrue(report['ok'])
            self.assertFalse(report['coverage_complete'])
            self.assertEqual('partial',report['coverage_status'])
            self.assertIn('not evidence of offseason',report['coverage_warning'])
            self.assertEqual(1,report['provider_free_result_limit'])

    def test_stale_completed_outside_window_and_invalid_rows(self):
        client=Mock();client.json.return_value={'events':[
            {**EVENT,'idEvent':'1','strTimestamp':'2026-09-18T16:10:00'},
            {**EVENT,'idEvent':'2','strTimestamp':'2026-10-26T16:10:00'},
            {**EVENT,'idEvent':'3','strStatus':'FT'},
            {**EVENT,'idEvent':'4','strTimestamp':'2026-10-18T11:00:00'},
            {**EVENT,'idEvent':'5','strHomeTeam':'TBD'}, EVENT]}
        events, report=collect(SOURCE,FIRST,LAST,TZ,NOW,client)
        self.assertEqual(['123456'],[e['id'] for e in events])
        self.assertFalse(report['ok']);self.assertEqual(1,report['fixtures_held'])

    def test_daily_league_filter_utc_boundary_and_partial_failure(self):
        source={**SOURCE,'source_type':'thesportsdb-day','endpoint':BASE+'eventsday.php'}
        client=Mock()
        def payload(endpoint,query):
            self.assertEqual('4478',query['l'])
            if query['d']=='2026-10-20':raise requests.Timeout('day unavailable')
            if query['d']=='2026-10-26':return {'events':[{**EVENT,'strTimestamp':'2026-10-26T03:00:00Z'}]}
            return {'events':None}
        client.json.side_effect=payload
        events, report=collect(source,FIRST,LAST,TZ,NOW,client)
        self.assertEqual(9,client.json.call_count)
        self.assertEqual(1,len(events)) # Oct25 10pm Chicago, not missed
        self.assertFalse(report['ok']);self.assertEqual(8,report['requests_succeeded'])
        self.assertEqual(3,report['provider_free_result_limit'])

    def test_daily_wrong_league_or_wrong_query_date_not_admitted(self):
        source={**SOURCE,'source_type':'thesportsdb-day','endpoint':BASE+'eventsday.php'}
        client=Mock();client.json.return_value={'events':[{**EVENT,'idLeague':'999'}]}
        events, report=collect(source,FIRST,FIRST,TZ,NOW,client)
        self.assertFalse(report['ok']);self.assertEqual([],events)
        client.json.return_value={'events':[{**EVENT,'strTimestamp':'2026-10-25T16:00:00'}]}
        self.assertEqual([],collect(source,FIRST,FIRST,TZ,NOW,client)[0])

    def test_dst_fallback_and_first_day_utc_spill_are_filtered(self):
        source={**SOURCE,'source_type':'thesportsdb-day','endpoint':BASE+'eventsday.php'}
        first=last=dt.date(2026,11,1)
        client=Mock()
        def payload(endpoint,query):
            times = ['2026-11-01T04:59:00Z','2026-11-01T05:00:00Z',
                     '2026-11-01T06:30:00Z','2026-11-01T07:30:00Z'] if query['d']=='2026-11-01' else [
                     '2026-11-02T05:59:00Z','2026-11-02T06:00:00Z']
            return {'events':[{**EVENT,'idEvent':str(i+100 if query['d']=='2026-11-01' else i+200),
                              'strTimestamp':timestamp} for i,timestamp in enumerate(times)]}
        client.json.side_effect=payload
        events,report=collect(source,first,last,TZ,dt.datetime(2026,10,31,tzinfo=UTC),client)
        self.assertTrue(report['ok'])
        self.assertEqual(['101','102','103','200'],[e['id'] for e in events])
        self.assertEqual(2,client.json.call_count)

    def test_conflicting_duplicate_does_not_keep_first_value(self):
        client=Mock();client.json.return_value={'events':[EVENT,{**EVENT,'strAwayTeam':'Different'}]}
        events, report=collect(SOURCE,FIRST,LAST,TZ,NOW,client)
        self.assertFalse(report['ok']);self.assertEqual([],events)


class PublicClientTests(unittest.TestCase):
    def test_access_denial_once_and_no_retry_later_in_run(self):
        for code in (401,403):
            get=Mock(return_value=response(code));client=PublicClient(get,get_sleep:=Mock())
            with self.assertRaises(requests.HTTPError):client.json(SOURCE['endpoint'],{'id':'4478'})
            with self.assertRaisesRegex(RuntimeError,'no further requests'):client.json(SOURCE['endpoint'],{'id':'4423'})
            self.assertEqual(1,get.call_count)

    def test_current_public_route_only_no_redirect_or_alternate_key(self):
        get=Mock(return_value=response(302));client=PublicClient(get,Mock())
        for url in (SOURCE['endpoint'].replace('/123/','/3/'),SOURCE['endpoint'].replace('www.','api.'),SOURCE['endpoint']+'?key=123'):
            with self.assertRaises(ValueError):client.json(url,{})
        self.assertEqual(0,get.call_count)
        with self.assertRaisesRegex(RuntimeError,'redirected'):client.json(SOURCE['endpoint'],{})
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_429_waits_full_reset_and_honors_long_retry_after(self):
        sleep=Mock();get=Mock(side_effect=[response(429,headers={'Retry-After':'90'}),response()])
        self.assertEqual({'events':None},PublicClient(get,sleep).json(SOURCE['endpoint'],{}))
        self.assertIn(unittest.mock.call(90),sleep.call_args_list)
        get=Mock(return_value=response(429,headers={'Retry-After':'300'}))
        with self.assertRaisesRegex(RuntimeError,'retry budget'):PublicClient(get,Mock()).json(SOURCE['endpoint'],{})
        self.assertEqual(1,get.call_count)

    def test_http_date_retry_after_never_retries_early(self):
        get=Mock(return_value=response(429,headers={"Retry-After":"Sun, 18 Oct 2026 20:00:00 GMT"}))
        with self.assertRaisesRegex(RuntimeError,"no early retry"):
            PublicClient(get,Mock()).json(SOURCE["endpoint"],{})
        self.assertEqual(1,get.call_count)

    def test_rate_limit_budget_stops_all_later_days_and_methods(self):
        for replies in ([response(429,headers={"Retry-After":"300"})], [response(429,headers={"Retry-After":"Sun, 18 Oct 2026 20:00:00 GMT"})], [response(429)]*3):
            get=Mock(side_effect=replies);client=PublicClient(get,Mock())
            with self.assertRaises(Exception):client.json(SOURCE["endpoint"],{})
            with self.assertRaisesRegex(RuntimeError,"no further requests"):
                client.json(BASE+"eventsday.php",{"d":"2026-10-18","l":"4478"})
            self.assertEqual(len(replies),get.call_count)
            source={**SOURCE,"source_type":"thesportsdb-day","endpoint":BASE+"eventsday.php"}
            _, report=collect(source,FIRST,LAST,TZ,NOW,client)
            self.assertEqual(0,report["requests_succeeded"])
            self.assertEqual(len(replies),get.call_count)

    def test_transient_errors_bounded_and_bad_payload_fails(self):
        get=Mock(side_effect=[requests.Timeout('timeout'),response(503),response()])
        self.assertEqual({'events':None},PublicClient(get,Mock()).json(SOURCE['endpoint'],{}))
        self.assertEqual(3,get.call_count)
        for data in ({},[],{'events':{}},{'events':'error'}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                PublicClient(Mock(return_value=response(data=data)),Mock()).json(SOURCE['endpoint'],{})

    def test_config_exact_27_sources_no_basketball_regression(self):
        config=json.loads((ROOT/'data/global-schedule-sources.json').read_text())['sources']
        sources=[s for s in config if s.get('source_type','').startswith('thesportsdb') and s['id']!='israeli-basketball']
        self.assertEqual(27,len(sources))
        self.assertEqual(15,sum(s['sport']=='Basketball' for s in sources))
        for source in sources:
            self.assertTrue(source['endpoint'].startswith(BASE))
            self.assertEqual('partial',source['coverage_status'])
        by_id={s['id']:s for s in config}
        for key in ('basketball-euroleague','eurocup-basketball','fiba-bcl','basketball-fiba-euroleague-women'):
            if key in by_id:self.assertFalse(by_id[key]['source_type'].startswith('thesportsdb'))
        self.assertIn('/3/',by_id['israeli-basketball']['endpoint'])


if __name__=='__main__':unittest.main()
