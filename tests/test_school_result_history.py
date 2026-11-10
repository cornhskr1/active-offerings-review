import copy
from datetime import date
from pathlib import Path
import json
import unittest
from scripts.school_result_history import capture_result_history, normalized_result
from scripts.school_event_history import project_history, validate
from scripts.refresh_official_school_calendars import classify_location
from scripts.official_school_results import collect_program_results
from tests.test_official_school_results import config, page, event
from tests.test_official_school_calendar import Response

STAMP='2026-11-09T12:00:00Z'

class ResultHistoryTests(unittest.TestCase):
    def collect(self, old=None, body=None, when=STAMP):
        return collect_program_results(config(), old or {}, when,
            lambda *a, **k: Response(page(event() if body is None else body)))

    def calendar(self, **kwargs):
        return {'uid':'calendar-one', 'source_id':config()['id'], 'school':'Nebraska',
                'sport':'Football','date':'2026-11-06','opponent':'Illinois',
                'location':'Champaign, Ill.', 'status':'REMOVED', **kwargs}

    def test_generic_result_archived_without_hardcoded_adapter_or_start(self):
        result=self.collect(body=event(number='99999'))
        cache=capture_result_history(config(), {}, {}, result, [self.calendar()])
        projection=project_history({config()['id']:cache},date(2026,11,9),classify_location)
        row=projection['events'][0]
        self.assertEqual(row['evidence_kind'],'recorded-official-school-result')
        self.assertEqual(row['publisher_event_id'],'99999')
        self.assertEqual(row['calendar_link_status'],'exact')
        self.assertEqual(row['historical_calendar_uid'],'calendar-one')
        self.assertEqual(row['site_color'],'green')
        self.assertFalse(row['actual_venue_verified']);self.assertIsNone(row['start_time'])
        self.assertEqual(row['observations'][0]['origin'],'validated-official-result')
        validate(cache['event_history'],config()['id'])

    def test_appended_venue_detail_is_not_conflict_but_other_city_is(self):
        result=self.collect(body=event(location='Champaign, Ill. / Memorial Stadium'))
        exact=normalized_result(result['events'][0],config(),[self.calendar()])
        self.assertEqual(exact['calendar_link_status'],'exact')
        for calendar_row in (self.calendar(location='Lincoln, Neb.'), self.calendar(status='CANCELLED')):
            conflict=normalized_result(result['events'][0],config(),[calendar_row])
            self.assertEqual(conflict['calendar_link_status'],'conflict')
        self.assertEqual(normalized_result(result['events'][0],config(),[self.calendar(),self.calendar(uid='another')])['calendar_link_status'],'ambiguous')

    def test_disappearing_result_tombstone_not_cancellation(self):
        first=self.collect();cache=capture_result_history(config(),{}, {},first,[self.calendar()])
        empty=self.collect(first['cache'],event(result=None), '2026-11-12T12:00:00Z')
        updated=capture_result_history(config(),cache,first['cache'],empty,[self.calendar()])
        records=updated['event_history']['observations']
        self.assertEqual(len(records),2);self.assertEqual(records[-1]['kind'],'removed')
        projection=project_history({config()['id']:updated},date(2026,11,12),classify_location)
        self.assertEqual(projection['events'][0]['archive_latest_kind'],'removed')
        self.assertIn('status',projection['events'][0]['archive_conflict_fields'])

    def test_refresh_failure_and_ttl_do_not_retimestamp_archive(self):
        first=self.collect();cache=capture_result_history(config(),{}, {},first,[self.calendar()])
        second=self.collect(first['cache'],when='2026-11-10T12:00:00Z')
        updated=capture_result_history(config(),cache,first['cache'],second,[self.calendar()])
        self.assertEqual(cache['event_history'],updated['event_history'])
        failed=collect_program_results(config(),first['cache'],'2026-11-12T12:00:00Z',lambda *a,**k: (_ for _ in ()).throw(ValueError('network unavailable')))
        updated=capture_result_history(config(),cache,first['cache'],failed,[self.calendar()])
        self.assertEqual(cache['event_history'],updated['event_history'])
        self.assertEqual(updated['history_capture']['capture_status'],'recording')

    def test_explicit_conflicting_result_holds_historical_use(self):
        first=self.collect();cache=capture_result_history(config(),{}, {},first,[self.calendar()])
        conflict=self.collect(first['cache'],event()+'<div class="schedule-event-item">bad identity</div>','2026-11-12T12:00:00Z')
        self.assertTrue(conflict['source_status']['integrity_hold'])
        updated=capture_result_history(config(),cache,first['cache'],conflict,[self.calendar()])
        self.assertEqual(updated['history_capture']['capture_status'],'degraded')

    def test_source_calendar_cache_timestamp_not_changed_by_result_fetch(self):
        original={'fetched_at':'2026-10-01T00:00:00Z','next_fetch_at':'2026-10-04T00:00:00Z','events':[]}
        result=self.collect();cache=capture_result_history(config(),original,{},result,[self.calendar()])
        self.assertEqual(cache['fetched_at'],original['fetched_at'])
        self.assertEqual(cache['next_fetch_at'],original['next_fetch_at'])
        self.assertEqual(cache['events'],[])

    def test_full_snapshot_collects_generic_results_without_special_adapters(self):
        from unittest.mock import patch
        from datetime import datetime, timezone
        from scripts import refresh_official_school_calendars as refresh
        root=Path(__file__).resolve().parents[1]
        sources=json.loads((root/'data/official-school-calendar-sources.json').read_text())
        def calendar_collect(source, previous, now, get):
            return {'events': [], 'source_status': {'id':source['id'],'ok':True,'status':'cached'},
                    'cache':copy.deepcopy(previous)}
        calls=[]
        def get(url,**kwargs):
            calls.append(url)
            if url.endswith('/football/schedule'):
                return Response(page(event(number='99999')))
            if url.endswith('/volleyball/schedule'):
                return Response(page(event(number='99998',opponent='Another Program',result='3-0 W Win',location='Seattle, WA'),sport='Volleyball'))
            raise ValueError('Synthetic source unavailable')
        with patch.object(refresh,'collect_school_calendar',side_effect=calendar_collect), patch.object(refresh,'collect_results',return_value=([],[],{})):
            output,saved=refresh.build_snapshot(sources,{}, {},datetime(2026,11,9,12,tzinfo=timezone.utc),get)
            rows=output['event_history']['events']
            self.assertEqual({r['publisher_event_id'] for r in rows},{'99999','99998'})
            self.assertEqual(output['historical_events'],[])
            self.assertEqual(len(output['official_result_sources']),6)
            first_observations=copy.deepcopy(rows)
            again,_=refresh.build_snapshot(sources,output,saved,datetime(2026,11,10,12,tzinfo=timezone.utc),lambda *a,**k: self.fail('TTL fetch'))
            self.assertEqual(first_observations,again['event_history']['events'])
        self.assertEqual(len(calls),6)

    def test_link_survives_calendar_rollover_but_changed_date_is_conflict(self):
        first=self.collect();cache=capture_result_history(config(),{}, {},first,[self.calendar()])
        second=self.collect(first['cache'],when='2026-11-12T12:00:00Z')
        retained=capture_result_history(config(),cache,first['cache'],second,[])
        self.assertEqual(retained['event_history'],cache['event_history'])
        changed=capture_result_history(config(),cache,first['cache'],second,[self.calendar(date='2026-11-07')])
        self.assertEqual(changed['event_history']['observations'][-1]['facts']['calendar_link_status'],'conflict')

    def test_reviewed_cache_seed_preserves_original_time_and_later_general_identity(self):
        from scripts.school_result_history import seed_reviewed_result, REVIEWED_SEED_OBSERVED_AT
        from scripts.official_historical_school_result import parse_result, SPECS
        spec=SPECS[0];root=Path(__file__).resolve().parents[1]
        old=parse_result((root/'tests/fixtures/nebraska-illinois-result-20261109.html').read_text(),spec)
        old.update(fetched_at=REVIEWED_SEED_OBSERVED_AT,next_fetch_at='2026-11-12T06:45:36.631287+00:00')
        saved={spec['source_id']:{'events':[old],'fetched_at':old['fetched_at'],'next_fetch_at':old['next_fetch_at']}}
        calendar_row=self.calendar(uid=spec['uid'],site='AWAY')
        source=config()
        seeded=seed_reviewed_result(source,{},saved,'2026-11-10T00:00:00Z',[calendar_row])
        observation=seeded['event_history']['observations'][0]
        self.assertEqual(observation['origin'],'reviewed-result-cache')
        self.assertEqual(observation['observed_at'],REVIEWED_SEED_OBSERVED_AT)
        self.assertNotIn('result',observation['facts']);self.assertNotIn('score',observation['facts'])
        self.assertEqual(observation['facts']['original_event_id'],old['id'])
        self.assertEqual(seeded,seed_reviewed_result(source,seeded,saved,'2026-11-10T12:00:00Z',[calendar_row]))
        real=self.collect(when='2026-11-12T12:00:00Z')
        fresh=capture_result_history(source,seeded,{},real,[calendar_row])
        chain=fresh['event_history']['observations']
        self.assertEqual(len(chain),2);self.assertEqual(chain[0]['event_key'],chain[1]['event_key'])
        self.assertEqual(chain[1]['previous_observation_id'],chain[0]['observation_id'])
        self.assertEqual(chain[0],observation)
        for mutate in ('failure','changed','expired'):
            bad=copy.deepcopy(saved)
            if mutate=='failure':bad[spec['source_id']]['retry_after']='2026-11-12T12:00:00Z'
            if mutate=='changed':bad[spec['source_id']]['events'][0]['location']='Lincoln, Neb.'
            now='2026-11-13T00:00:00Z' if mutate=='expired' else '2026-11-10T00:00:00Z'
            self.assertEqual(seed_reviewed_result(source,{},bad,now,[calendar_row]),{})
