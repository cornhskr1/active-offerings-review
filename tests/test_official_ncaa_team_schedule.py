"""Compact synthetic graphs exercise the exact reviewed NCAA slices."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from official_ncaa_team_schedule import SPECS, parse_fixtures

START, END = dt.date(2026, 10, 18), dt.date(2026, 10, 25)
TIMES = {14405: ("2026-10-23T18:00:00", "2026-10-24T01:00:00Z", "6 P.M."),
         14406: ("2026-10-25T12:00:00", "2026-10-25T19:00:00Z", "12 P.M."),
         16677: ("2026-10-23T18:00:00", "2026-10-23T23:00:00Z", "6 p.m."),
         16678: ("2026-10-24T14:00:00", "2026-10-24T19:00:00Z", "2 p.m.")}


def fixture(key="ncaa-water-polo-di-men"):
    spec = SPECS[key]
    source = {"id": key, **{k: spec[k] for k in ("endpoint", "sport", "league")}}
    source.update(source_type="official-ncaa-reviewed-team-fixtures", region="United States",
                  catalog_terms=[spec["league"]], coverage_status="partial", coverage_complete=False)
    records = []
    for game, (opponent, name) in spec["games"].items():
        local, utc, time = TIMES[game]
        records.append({"id": game, "start_date": local, "start_date_utc": utc,
            "time": time, "opponent": {"id": opponent, "title": name},
            "sport": {"id": spec["sport_id"], "title": spec["publisher_sport"],
                      "shortname": spec["shortname"], "gender": spec["gender"]},
            "location_indicator": "H", "location": "Verified home venue",
            "status": "A", "game_state_display": "SCHEDULED",
            "is_tdb": False, "is_all_day": False, "tournament": ""})
    return source, records


def page(source, records):
    graph = []
    def add(value):
        index = len(graph)
        graph.append(None)
        if isinstance(value, dict):
            graph[index] = {k: add(v) for k, v in value.items()}
        elif isinstance(value, list):
            graph[index] = [add(v) for v in value]
        else:
            graph[index] = value
        return index
    add({"title": SPECS[source["id"]]["title"], "records": records})
    return '<script type="application/json" id="__NUXT_DATA__">' + json.dumps(graph) + '</script>'


class ExactNcaaTeamScheduleTests(unittest.TestCase):
    def parse(self, source, rows, start=START, end=END):
        return parse_fixtures(page(source, rows), source, start, end)

    def test_both_identities_four_literal_utc_events(self):
        for key in SPECS:
            source, rows = fixture(key)
            events, held = self.parse(source, rows)
            self.assertEqual(2, len(events))
            self.assertEqual(0, held)
            self.assertEqual([r['start_date_utc'] for r in rows], [e['start_time'] for e in events])
            self.assertTrue(all(e['league'] == source['league'] for e in events))

    def test_central_day_not_utc_day(self):
        source, rows = fixture()
        events, _ = self.parse(source, rows, dt.date(2026, 10, 23), dt.date(2026, 10, 23))
        self.assertEqual(['ncaa-water-polo-di-men:14405'], [e['id'] for e in events])

    def test_unverified_mixed_division_alumni_placeholder_held(self):
        source, rows = fixture()
        for number, name in [(999, 'Division II opponent'), (998, 'Alumni'), (997, 'TBD')]:
            row = copy.deepcopy(rows[0]); row['id'] = number; row['opponent']['title'] = name
            rows.append(row)
        events, held = self.parse(source, rows)
        self.assertEqual((2, 3), (len(events), held))

    def test_duplicate_identical_and_raw_copy_deduplicated(self):
        source, rows = fixture(); raw = copy.deepcopy(rows[0])
        raw['date'] = raw.pop('start_date'); raw.pop('start_date_utc'); raw.pop('sport')
        rows.extend([copy.deepcopy(rows[0]), raw])
        self.assertEqual(2, len(self.parse(source, rows)[0]))

    def test_conflicting_duplicate_fails(self):
        source, rows = fixture(); changed = copy.deepcopy(rows[0]); changed['status'] = 'I'
        with self.assertRaises(ValueError): self.parse(source, rows + [changed])

    def test_exact_identity_and_participants_fail_closed(self):
        for field, value in [('gender','f'), ('id',99), ('title','Other sport'), ('shortname','other')]:
            source, rows = fixture(); rows[0]['sport'][field] = value
            with self.assertRaises(ValueError): self.parse(source, rows)
        for mutate in [lambda r:r['opponent'].update(id=99),
                       lambda r:r['opponent'].update(title='Unknown'),
                       lambda r:r.update(location_indicator='A')]:
            source, rows=fixture(); mutate(rows[0])
            with self.assertRaises(ValueError):self.parse(source,rows)

    def test_partial_exact_source_contract_required(self):
        source,rows=fixture();html=page(source,rows)
        for key,value in [('source_type','official-ncaa-division-one'),('region','World'),
                          ('catalog_terms',[source['league'],'National Collegiate']),
                          ('coverage_status','complete'),('coverage_complete',True),
                          ('coverage_complete',None)]:
            with self.assertRaises(ValueError):
                parse_fixtures(html,{**source,key:value},START,END)

    def test_changed_source_or_season_rejected(self):
        source, rows = fixture(); html = page(source, rows)
        for k in ['endpoint', 'league', 'sport']:
            changed = {**source, k: 'wrong'}
            with self.assertRaises(ValueError):parse_fixtures(html, changed, START, END)
        with self.assertRaises(ValueError):parse_fixtures(html.replace('2026 Men', '2027 Men'),source,START,END)

    def test_utc_missing_unzoned_or_contradictory_rejected(self):
        for utc in [None, '2026-10-24T01:00:00', '2026-10-24T02:00:00Z']:
            source, rows = fixture()
            if utc is None:rows[0].pop('start_date_utc')
            else:rows[0]['start_date_utc']=utc
            with self.assertRaises(ValueError):self.parse(source,rows)

    def test_all_day_aliases_must_agree(self):
        source,rows=fixture();rows[0]['allday']=True
        with self.assertRaises(ValueError):self.parse(source,rows)
        rows[0]['allday']=False
        self.assertEqual(2,len(self.parse(source,rows)[0]))
        for row in rows:
            row.pop('is_all_day',None);row.pop('allday',None)
        self.assertEqual(2,len(self.parse(source,rows)[0]))

    def test_timed_record_requires_sport(self):
        source,rows=fixture();rows[0].pop('sport')
        with self.assertRaises(ValueError):self.parse(source,rows)

    def test_cyclic_and_out_of_range_references_fail_closed(self):
        source,rows=fixture();html=page(source,rows)
        # id references are read only from schedule-shaped records.
        for reference in [999999, 0]:
            broken = '<script id="__NUXT_DATA__">' + json.dumps([
                {'id':reference,'date':1,'opponent':2}, '2026-10-23T18:00:00', {},
                SPECS[source['id']]['title']]) + '</script>'
            with self.assertRaises(ValueError):parse_fixtures(broken,source,START,END)

    def test_missing_reviewed_game_rejected(self):
        source,rows=fixture()
        with self.assertRaises(ValueError):self.parse(source, rows[:1])

    def test_completed_inactive_tbd_allday_held(self):
        for field,value in [('game_state_display','FINAL'),('status','I'),('is_tdb',True),('is_all_day',True),('tournament','Unverified tournament'),('type','E'),('neutralHometeam',True)]:
            source,rows=fixture();rows[0][field]=value
            events,held=self.parse(source,rows)
            self.assertEqual((1,1),(len(events),held))

    def test_all_completed_and_expired_not_healthy_zero(self):
        source,rows=fixture()
        for row in rows:row['game_state_display']='FINAL'
        with self.assertRaises(ValueError):self.parse(source,rows)
        source,rows=fixture()
        with self.assertRaises(ValueError):self.parse(source,rows,dt.date(2026,10,26),dt.date(2026,11,2))

    def test_reschedule_keeps_publisher_identity(self):
        source,rows=fixture();before=self.parse(source,rows)[0][0]['id']
        rows[0].update(start_date='2026-10-23T19:00:00',start_date_utc='2026-10-24T02:00:00Z',time='7 P.M.')
        self.assertEqual(before,self.parse(source,rows)[0][0]['id'])

    def test_missing_or_multiple_payload_rejected(self):
        source,rows=fixture();html=page(source,rows)
        for text in ['',html+html]:
            with self.assertRaises(ValueError):parse_fixtures(text,source,START,END)

if __name__ == '__main__': unittest.main()
