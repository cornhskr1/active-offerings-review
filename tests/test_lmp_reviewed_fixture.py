"""Captured official day proof and bounds; no provider requests in tests."""
import copy
import ast
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lmp_reviewed_fixture import collect, parse, URL

SOURCE = next(s for s in json.loads((ROOT / 'data/global-schedule-sources.json').read_text())['sources'] if s['id'] == 'lmp')
FIRST, LAST = dt.date(2026, 11, 1), dt.date(2026, 11, 8)
NOW = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)


def payload():
    return json.loads((ROOT / 'tests/fixtures/lmp_reviewed_nov1_2026.json').read_text())


class ReviewedLmpTests(unittest.TestCase):
    def revised_payload(self):
        return json.loads((ROOT / 'tests/fixtures/lmp_held_clock_nov1_2026.json').read_text())

    def test_revised_held_clock_keeps_identical_one_game_and_six_holds(self):
        now = dt.datetime(2026,11,1,21,15,tzinfo=dt.timezone.utc)
        actual = parse(self.revised_payload(), SOURCE, FIRST, LAST, now)
        self.assertEqual(parse(payload(),SOURCE,FIRST,LAST,now),actual)
        self.assertEqual(['lmp-2026-27-850500'],[r['id'] for r in actual[0]])
        self.assertEqual(6,actual[1]['fixtures_held'])
        self.assertEqual(actual,parse({'response':list(reversed(self.revised_payload()['response']))},SOURCE,FIRST,LAST,now))

    def test_revised_proof_not_retroactive_or_renewed(self):
        for now,first,last in ((NOW,FIRST,LAST),
                (dt.datetime(2026,11,1,21,13,59,tzinfo=dt.timezone.utc),FIRST,LAST),
                (dt.datetime(2026,11,2,6,tzinfo=dt.timezone.utc),FIRST+dt.timedelta(days=1),LAST+dt.timedelta(days=1)),
                (NOW.replace(tzinfo=None),FIRST,LAST)):
            with self.subTest(now=now),self.assertRaises(ValueError):
                parse(self.revised_payload(),SOURCE,first,last,now)

    def test_revised_held_identity_and_all_clocks_still_required(self):
        now=dt.datetime(2026,11,1,21,15,tzinfo=dt.timezone.utc)
        changes={'id':'other','awayTeamId':1,'stadium':'other','gameStatus':1,'awayRuns':1,
                 'season':'2027','gameType':'P','utcFullDate':'2026-11-02 02:01:00',
                 'localFullDate':'2026-11-01 18:00:00','spFullDate':'2026-11-02 00:00:00',
                 'gameDate':'2026-11-02','gameTimeH':'18:00:00'}
        for field,value in changes.items():
            revised=self.revised_payload()
            next(r for r in revised['response'] if r['boxScore']==850497)[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):parse(revised,SOURCE,FIRST,LAST,now)
        for game in (850500,850503):
            revised=self.revised_payload();row=next(r for r in revised['response'] if r['boxScore']==game)
            row.update(utcFullDate='2026-11-02 02:00:00',spFullDate='2026-11-02 02:00:00',
                       localFullDate='2026-11-01 20:00:00',gameTimeH='20:00:00')
            with self.subTest(game=game),self.assertRaises(ValueError):parse(revised,SOURCE,FIRST,LAST,now)

    def test_revised_held_identity_cannot_be_dropped_or_merged(self):
        now=dt.datetime(2026,11,1,21,15,tzinfo=dt.timezone.utc);revised=self.revised_payload()
        for rows in ([r for r in revised['response'] if r['boxScore']!=850497],
                     revised['response']+[next(r for r in revised['response'] if r['boxScore']==850497)]):
            with self.assertRaises(ValueError):parse({'response':rows},SOURCE,FIRST,LAST,now)

    def run_parse(self, data):
        return parse(data, SOURCE, FIRST, LAST, NOW)

    def test_exact_one_game_with_six_explicit_holds(self):
        rows, report = self.run_parse(payload())
        self.assertEqual(['lmp-2026-27-850500'], [r['id'] for r in rows])
        self.assertEqual('2026-11-02T00:05:00Z', rows[0]['start_time'])
        self.assertEqual('Charros de Jalisco at Tomateros de Culiacán', rows[0]['name'])
        self.assertEqual('Estadio Juan Ley Fong', rows[0]['location'])
        self.assertEqual(6, report['fixtures_held'])
        self.assertFalse(report['coverage_complete'])
        self.assertEqual(rows, self.run_parse({'response':list(reversed(payload()['response']))})[0])

    def test_every_day_identity_required_no_collapse_extra_or_missing(self):
        base = payload()
        for rows in (base['response'][:-1], base['response']+[base['response'][0]],
                     base['response'][:-1]+[base['response'][0]], []):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                self.run_parse({'response':rows})
        changed = payload();changed['response'][0]['boxScore'] = 900001
        with self.assertRaises(ValueError):self.run_parse(changed)

    def test_changed_pairing_venue_edition_phase_state_or_identity_fails_entire_day(self):
        changes = {'id':'other', 'awayTeamId':1, 'homeTeamId':2, 'awayTeam':'TBD',
                   'homeTeamShort':'Under 18', 'stadium':'', 'season':'2027', 'league_id':133,
                   'sport_id':18, 'gameType':'P', 'gameStatus':1, 'awayRuns':1, 'homeRuns':1}
        # Corrupt both the reviewed game and a held doubleheader: neither may
        # produce partial success by silently dropping a malformed row.
        for index in (0,6):
            for field,value in changes.items():
                changed=payload();changed['response'][index][field]=value
                with self.subTest(index=index,field=field), self.assertRaises(ValueError):self.run_parse(changed)

    def test_missing_naive_changed_clock_fields_and_date_fail(self):
        for field in ('utcFullDate','localFullDate','spFullDate','gameDate','gameTimeH'):
            for value in (None, '', '2026-11-01 00:00:00', '2026-11-02T00:05:00Z'):
                changed=payload();changed['response'][-1][field]=value
                with self.subTest(field=field,value=value), self.assertRaises(ValueError):self.run_parse(changed)

    def test_expired_or_extended_window_naive_clock_source_or_caps_no_request(self):
        cases = [(SOURCE,FIRST+dt.timedelta(days=1),LAST,NOW), (SOURCE,FIRST,LAST+dt.timedelta(days=1),NOW),
                 (SOURCE,FIRST,LAST,NOW.replace(tzinfo=None)),
                 ({**SOURCE,'endpoint':URL+'?other=1'},FIRST,LAST,NOW),
                 ({**SOURCE,'max_events_per_run':2},FIRST,LAST,NOW),
                 ({**SOURCE,'max_requests_per_run':2},FIRST,LAST,NOW),
                 ({**SOURCE,'catalog_terms':['Other']},FIRST,LAST,NOW)]
        for args in cases:
            get=Mock()
            with self.subTest(args=args[1:]), self.assertRaises(ValueError):collect(*args,get,{})
            get.assert_not_called()

    def test_public_get_once_no_redirect_retry_or_vendor_and_no_past_emission(self):
        response=Mock(status_code=200);response.json.return_value=payload();get=Mock(return_value=response)
        rows, _=collect(SOURCE,FIRST,LAST,NOW,get,{'User-Agent':'test'})
        self.assertEqual(1,len(rows));get.assert_called_once_with(URL,headers={'User-Agent':'test'},timeout=30,allow_redirects=False)
        for status in (302,401,403,500):
            get=Mock(return_value=Mock(status_code=status))
            with self.subTest(status=status),self.assertRaises(ValueError):collect(SOURCE,FIRST,LAST,NOW,get,{})
            self.assertEqual(1,get.call_count)
        # Before Central midnight the next day, the pinned game has started.
        rows, report=parse(payload(),SOURCE,FIRST,LAST,dt.datetime(2026,11,2,0,6,tzinfo=dt.timezone.utc))
        self.assertEqual([],rows);self.assertFalse(report['coverage_complete'])

    def test_actual_collector_branch_emits_nothing_after_access_or_semantic_failure(self):
        tree=ast.parse((ROOT/'scripts/refresh_global_schedule.py').read_text())
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.If)
                  and ast.unparse(n.test)=='source.get(\'source_type\') == \'official-lmp-reviewed-fixture\'')
        wrapper=ast.Module(body=[ast.For(target=ast.Name(id='source',ctx=ast.Store()),
                    iter=ast.List(elts=[ast.Name(id='configured_source',ctx=ast.Load())],ctx=ast.Load()),
                    body=[node],orelse=[])],type_ignores=[])
        program=compile(ast.fix_missing_locations(wrapper),'<actual LMP collector branch>','exec')
        damaged=payload();damaged['response'][0]['gameStatus']=1
        for status,data,expected in [(200,payload(),1),(200,self.revised_payload(),1),(200,damaged,0),(302,payload(),0),(403,payload(),0)]:
            response=Mock(status_code=status);response.json.return_value=data;get=Mock(return_value=response)
            context=dict(configured_source=copy.deepcopy(SOURCE),collect_lmp_reviewed=collect,TODAY=FIRST,
                         END=LAST,NOW_UTC=dt.datetime(2026,11,1,21,15,tzinfo=dt.timezone.utc),requests=SimpleNamespace(get=get),HEADERS={},
                         events=[],seen=set(),source_status=[],count=0)
            exec(program,context)
            self.assertEqual(expected,len(context['events']));self.assertEqual(1,get.call_count)
            self.assertEqual(bool(expected),context['source_status'][0]['ok'])


if __name__ == '__main__':unittest.main()
