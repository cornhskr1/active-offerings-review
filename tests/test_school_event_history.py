import copy
import json
import unittest
import sys
from contextlib import ExitStack
from datetime import date
from unittest.mock import patch
from scripts.school_event_history import capture_history, project_history, update_history, validate
from scripts.refresh_official_school_calendars import classify_location
from tests.test_official_school_calendar import SOURCE, Response, calendar, event, NOW
from scripts.official_school_calendar import collect_school_calendar


class HistoryTests(unittest.TestCase):
    def collect(self, old=None, when=NOW, body=None):
        return collect_school_calendar(SOURCE, old or {}, when, lambda *a, **k: Response(calendar(body)))

    def test_independent_date_dedup_and_expired_fetch(self):
        first = self.collect()
        second = self.collect(first['cache'], '2026-10-22T00:00:00Z')
        self.assertEqual(first['cache']['event_history'], second['cache']['event_history'])
        failed = collect_school_calendar(SOURCE, second['cache'], '2026-10-30T00:00:00Z', lambda *a, **k: (_ for _ in ()).throw(ValueError('failure')))
        self.assertEqual(second['cache']['event_history'], failed['cache']['event_history'])
        self.assertFalse(failed['source_status']['ok'])

    def test_changes_cancellation_and_removal_all_survive(self):
        first = self.collect(body=event() + event(uid='two'))
        second = self.collect(first['cache'], '2026-10-22T00:00:00Z', event(extra='SEQUENCE:1\nSTATUS:CANCELLED').replace('Lincoln\\, Neb.', 'Ames\\, Iowa'))
        history = second['cache']['event_history']
        self.assertEqual(len(history['observations']), 4)
        kinds = [r['kind'] for r in history['observations']]
        self.assertIn('removed', kinds)
        changed = history['observations'][2]
        self.assertIn('location', changed['changed_fields'])
        self.assertEqual(changed['facts']['status'], 'CANCELLED')
        self.assertFalse(changed['actual_venue_verified'])
        validate(history, SOURCE['id'])
        third = self.collect(second['cache'], '2026-10-25T00:00:00Z', event(extra='SEQUENCE:1\nSTATUS:CANCELLED').replace('Lincoln\\, Neb.', 'Ames\\, Iowa'))
        self.assertEqual(history, third['cache']['event_history'])

    def test_rollover_retains_completed_past_row(self):
        first = self.collect()
        prior = copy.deepcopy(first['cache'])
        old = prior['events'][0]
        old.update(season_id='old-season', status='COMPLETED', date='2026-09-01')
        prior.pop('event_history')
        new = self.collect(prior, '2026-10-22T00:00:00Z')
        history = new['cache']['event_history']
        old_records = [o for o in history['observations'] if o['facts']['season_id'] == 'old-season']
        self.assertEqual(len(old_records), 2)
        self.assertEqual(old_records[0]['origin'], 'legacy-cache')
        self.assertEqual(old_records[0]['observed_at'], first['cache']['fetched_at'])
        self.assertEqual(old_records[-1]['kind'], 'season-no-longer-current')
        self.assertEqual(old_records[-1]['facts']['status'], 'COMPLETED')

    def test_window_keeps_complete_chain_after_date_change(self):
        first = self.collect()
        second = self.collect(first['cache'], '2026-10-22T00:00:00Z', event(start='DTSTART;VALUE=DATE:20270131', extra='SEQUENCE:1'))
        projection = project_history({SOURCE['id']: second['cache']}, date(2026, 11, 9), classify_location)
        self.assertEqual(len(projection['events']), 1)
        row = projection['events'][0]
        self.assertEqual(row['date'], '2027-01-31')
        self.assertIn('date', row['archive_conflict_fields'])
        self.assertEqual(len(row['observations']), 2)
        validate({'contract': 'school-calendar-observations/v1', 'observations': row['observations']}, SOURCE['id'])

    def test_budget_pauses_capture_without_losing_ledger_or_live_rows(self):
        first = self.collect()
        with ExitStack() as stack:
            for name in ('scripts.school_event_history', 'school_event_history'):
                if name in sys.modules:
                    stack.enter_context(patch.object(sys.modules[name], 'MAX_SOURCE_HISTORY_BYTES', 1))
            second = self.collect(first['cache'], '2026-10-22T00:00:00Z', event(extra='SEQUENCE:1').replace('Lincoln\\, Neb.', 'Ames\\, Iowa'))
        self.assertTrue(second['source_status']['ok'])
        self.assertEqual(first['cache']['event_history'], second['cache']['event_history'])
        self.assertEqual(second['cache']['events'][0]['sequence'], 1)
        self.assertEqual(second['cache']['history_capture']['capture_status'], 'degraded')
        third = self.collect(second['cache'], '2026-10-25T00:00:00Z', event(extra='SEQUENCE:1'))
        self.assertEqual(third['cache']['history_capture']['capture_status'], 'degraded')

    def test_untrusted_extra_fields_not_copied(self):
        first = self.collect()
        old = first['cache'];old.pop('event_history')
        old['events'][0].update(operator_report='private', description='private', player='private')
        result = self.collect(old, '2026-10-20T00:00:00Z')
        self.assertNotIn('private', json.dumps(result['cache']['event_history']))

    def test_corrupt_history_fail_closed_but_live_collection_continues(self):
        first = self.collect()
        first['cache']['event_history']['observations'][0]['facts']['location'] = 'tampered'
        result = self.collect(first['cache'], '2026-10-22T00:00:00Z')
        self.assertTrue(result['source_status']['ok'])
        self.assertEqual(result['cache']['history_capture']['capture_status'], 'degraded')
        projection = project_history({SOURCE['id']: result['cache']}, date(2026, 11, 9), classify_location)
        self.assertEqual(projection['events'], [])
        self.assertEqual(projection['sources'][0]['capture_status'], 'degraded')

    def test_unknown_legacy_identity_is_degraded_not_invented(self):
        old = {'source_id': SOURCE['id'], 'events': [{'uid':'old','date':'2026-10-01'}]}
        result = self.collect(old)
        self.assertEqual(result['cache']['history_capture']['capture_status'], 'recording')
        self.assertEqual(result['cache']['history_capture']['legacy_gap_count'], 1)
        self.assertTrue(all(o['facts']['uid'] != 'old' for o in result['cache']['event_history']['observations']))

    def test_metadata_only_refresh_does_not_churn_historical_facts(self):
        first = self.collect()
        second = self.collect(first['cache'], '2026-10-22T00:00:00Z', event(extra='SEQUENCE:100\nDTSTAMP:20261022T000000Z'))
        self.assertEqual(first['cache']['event_history'], second['cache']['event_history'])
        self.assertEqual(second['cache']['events'][0]['sequence'], 100)

    def test_missing_intermediate_time_does_not_hide_conflicting_known_times(self):
        first = self.collect(body=event(start='DTSTART:20261031T190000Z'))
        second = self.collect(first['cache'], '2026-10-22T00:00:00Z', event(extra='SEQUENCE:1'))
        third = self.collect(second['cache'], '2026-10-25T00:00:00Z', event(start='DTSTART:20261031T200000Z', extra='SEQUENCE:2'))
        projection = project_history({SOURCE['id']:third['cache']}, date(2026,11,9), classify_location)
        self.assertIn('start_time', projection['events'][0]['archive_conflict_fields'])

    def test_all_state_names_and_ap_aliases_require_single_jurisdiction(self):
        from scripts.refresh_official_school_calendars import STATE_NAMES, STATE_AP
        for code, name in STATE_NAMES.items():
            for label in (code, name, STATE_AP.get(code, code)):
                row = classify_location({'location':'City, '+label+' / Arena'})
                self.assertEqual(row['site_color'], 'red' if code == 'NE' else 'green', label)
        self.assertEqual(classify_location({'location':'Town, Iowa, Kansas'})['site_color'],'amber')
        self.assertEqual(classify_location({'location':'Nebraska / Iowa'})['site_color'],'amber')
        self.assertEqual(classify_location({'location':'Town, Neb., Iowa'})['site_color'],'amber')
        self.assertEqual(classify_location({'location':'Memorial Stadium', 'site':'HOME'})['site_color'],'amber')

    def test_initial_capture_above_old_budget_fits_bounded_allowance(self):
        from scripts.school_event_history import update_history, MAX_SOURCE_HISTORY_BYTES
        self.assertEqual(MAX_SOURCE_HISTORY_BYTES, 200000)
        first = self.collect()
        old = copy.deepcopy(first['cache']); old.pop('event_history'); old.pop('history_capture')
        template = old['events'][0]
        old['events'] = [{**template, 'uid':str(i), 'location':template['location'] + 'x'*300} for i in range(56)]
        result = {'events':copy.deepcopy(old['events']), 'cache':copy.deepcopy(old),
                  'source_status':{'ok':True,'status':'current','fetched_at':'2026-10-22T00:00:00+00:00'}}
        candidate = update_history(old, result, SOURCE['id'])
        encoded = json.dumps(candidate, indent=2, ensure_ascii=False)
        size = len(encoded.encode()) + 6 * (encoded.count('\n')+1)
        self.assertGreater(size, 180000); self.assertLessEqual(size, 200000)
        saved = capture_history(old, result, SOURCE['id'])['cache']
        self.assertEqual(saved['history_capture']['capture_status'], 'recording')
        self.assertEqual(len(saved['event_history']['observations']), 112)

    def test_reviewed_budget_recovery_requires_every_pin_and_never_changes_live_rows(self):
        from scripts import school_event_history as history
        current = self.collect()['cache']
        current['events'][0]['provider_updated_at'] = '2026-10-19T00:00:01+00:00'
        current['event_history'] = {'contract':history.CONTRACT,'observations':[]}
        current['history_capture'] = {'source_id':SOURCE['id'],'capture_status':'degraded',
            'reason':'History capture unavailable or budget reached; prior history retained without eviction',
            'observation_count':0,'legacy_gap_count':0}
        facts = [history.facts_for(current['events'][0],SOURCE['id'])]
        original = [{**facts[0], 'provider_updated_at':'2026-10-18T00:00:01+00:00'}]
        pin = {'source_id':SOURCE['id'],'rows':1,'old_fetched_at':'2026-10-18T00:00:00+00:00',
            'current_fetched_at':current['fetched_at'],'current_next_fetch_at':current['next_fetch_at'],
            'current_provider_updated_at':facts[0]['provider_updated_at'],
            'old_provider_updated_at':original[0]['provider_updated_at'],
            'current_facts_sha256':history.digest(facts),'old_facts_sha256':history.digest(original)}
        before = copy.deepcopy(current)
        with patch.object(history,'OMAHA_BUDGET_RECOVERY',pin):
            recovered = history.recover_reviewed_budget_failure(current,SOURCE['id'])
            self.assertEqual(current,before)
            self.assertEqual(recovered['events'],before['events'])
            self.assertEqual(recovered['fetched_at'],before['fetched_at'])
            self.assertEqual(recovered['next_fetch_at'],before['next_fetch_at'])
            self.assertEqual(recovered['history_capture']['capture_status'],'recording')
            self.assertEqual([o['observed_at'] for o in recovered['event_history']['observations']],
                [pin['old_fetched_at'],pin['current_fetched_at']])
            self.assertEqual(history.recover_reviewed_budget_failure(recovered,SOURCE['id']),recovered)
            for field in ('location','provider_updated_at'):
                bad = copy.deepcopy(current);bad['events'][0][field]='changed'
                self.assertEqual(history.recover_reviewed_budget_failure(bad,SOURCE['id']),bad)
            bad=copy.deepcopy(current);bad['history_capture']['reason']='Another genuine capture gap'
            self.assertEqual(history.recover_reviewed_budget_failure(bad,SOURCE['id']),bad)
            bad=copy.deepcopy(current);bad['fetched_at']='2026-10-20T00:00:00+00:00'
            self.assertEqual(history.recover_reviewed_budget_failure(bad,SOURCE['id']),bad)
            with patch.dict(pin,{'old_facts_sha256':'0'*64}):
                self.assertEqual(history.recover_reviewed_budget_failure(current,SOURCE['id']),current)
