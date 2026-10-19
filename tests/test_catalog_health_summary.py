"""Browser/CommonJS pure catalog health contract and adverse evidence tests."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'assets/catalog-health-summary.js'


def build(**changes):
    data = dict(coverage={'identities': [{'identity_key': 'a', 'sport': 'Ball', 'league': 'A', 'sources': [{'id': 'feed'}]}]},
                global_={'window_start': '2026-10-19', 'window_end': '2026-10-26', 'sources': [dict(id='feed', endpoint='https://api.vendor.test/fixtures', ok=True, checked_at='2026-10-19T09:00:00Z')], 'events': []},
                now='2026-10-19T10:00:00Z', windowStart='2026-10-19', windowEnd='2026-10-26')
    data.update(changes)
    data['global'] = data.pop('global_')
    result = subprocess.run(['node', '-e', f'const x=JSON.parse(require("fs").readFileSync(0,"utf8")); const before=JSON.stringify(x);const result=require({json.dumps(str(MODULE))}).build(x);if(before!==JSON.stringify(x))throw Error("Mutated input");console.log(JSON.stringify(result));'], input=json.dumps(data), text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def event(**changes):
    e = dict(id='event1', source_id='feed', name='Home vs Away', start_time='2026-10-20T14:00:00Z')
    e.update(changes)
    return e


def schedule(events=(), **source):
    s = dict(id='feed', endpoint='https://api.vendor.test/fixtures', ok=True, checked_at='2026-10-19T09:00:00Z')
    s.update(source)
    return dict(window_start='2026-10-19', window_end='2026-10-26', sources=[s], events=list(events))


class CatalogHealthTests(unittest.TestCase):
    def test_empty_current_is_not_offseason(self):
        r = build()
        self.assertEqual(r['rows'][0]['state'], 'healthy_empty')
        self.assertEqual(r['totals']['fresh_events'], 0)
        self.assertNotIn('offseason', r['rows'][0])

    def test_unique_denominator_and_provider_family(self):
        a = {'identity_key': 'a', 'sources': [{'id': 'feed'}]}
        r = build(coverage={'identities': [a, a, {'identity_key': 'b', 'sources': [{'id': 'feed'}]}]})
        self.assertEqual(r['totals']['identities'], 2)
        self.assertEqual(r['totals']['connected_provider_families'], 1)
        self.assertEqual(r['providerFamilies'][0]['name'], 'api.vendor.test')

    def test_fresh_and_stale_source_flags(self):
        for flags in ({'stale': True}, {'source_stale': True}, {'collection_paused': True}):
            r = build(global_=schedule([event(**flags)]))
            self.assertEqual(r['rows'][0]['state'], 'stale')
        r = build(global_=schedule([event()]))
        self.assertEqual(r['totals']['fresh_events'], 1)

    def test_retired_and_permission_held_never_working(self):
        for flags in ({'endpoint': 'https://site.api.espn.com/fixtures'}, {'access_status': 'permission_required'}, {'collection_paused': True}):
            r = build(global_=schedule([event()], **flags))
            self.assertEqual(r['totals']['fresh_events'], 0)
            self.assertEqual(r['totals']['mapped'], 0)
            self.assertEqual(r['totals']['connected_provider_families'], 0)
            self.assertEqual(r['rows'][0]['state'], 'stale')

    def test_unapproved_source_cannot_contribute(self):
        r = build(global_=schedule([event()], approved_catalog=False))
        self.assertEqual(r['totals']['mapped'], 0)
        self.assertEqual(r['totals']['fresh_events'] + r['totals']['stale_events'], 0)

    def test_exact_scoped_provider_health_without_broadcast(self):
        c = {'identities': [{'identity_key': k, 'sources': [{'id': k}]} for k in ('a', 'b')]}
        g = schedule([event(source_id='a', source_endpoint='https://api.vendor.test/game')])
        g['sources'][0]['scope_source_ids'] = ['a', 'b']
        g['sources'].append(dict(id='a', source_type='official-event-window', ok=True))
        r = build(coverage=c, global_=g)
        self.assertEqual(r['totals']['fresh_events'], 1)
        self.assertEqual(r['rows'][0]['fresh_event_count'], 1)
        self.assertEqual(r['rows'][1]['fresh_event_count'], 0)

    def test_stale_timestamp_not_rescued_by_generated(self):
        g = schedule([event()], checked_at='2026-10-17T10:00:00Z')
        g['generated_at'] = '2026-10-19T09:59:00Z'
        self.assertEqual(build(global_=g)['rows'][0]['state'], 'stale')

    def test_unknown_future_clock_fails_closed(self):
        for stamp in ('invalid', '2026-10-20T10:00:00Z'):
            self.assertEqual(build(global_=schedule([event()], checked_at=stamp))['totals']['fresh_events'], 0)

    def test_shared_source_is_not_all_children(self):
        coverage = {'identities': [{'identity_key': k, 'sources': [{'id': 'feed'}]} for k in ('a', 'b')]}
        r = build(coverage=coverage, global_=schedule([event()]))
        self.assertEqual(r['totals']['fresh_events'], 0)
        self.assertEqual(r['diagnostics']['unassigned_events'], 1)
        r = build(coverage=coverage, global_=schedule([event(catalog_identity_key='b')]))
        self.assertEqual(r['totals']['fresh'], 1)
        self.assertEqual(r['rows'][1]['fresh_event_count'], 1)

    def test_exact_key_requires_source_link(self):
        r = build(global_=schedule([event(catalog_identity_key='a', source_id='other')]))
        self.assertEqual(r['totals']['fresh_events'], 0)

    def test_date_only_and_reference_are_not_fixture_coverage(self):
        for g in (schedule([event(reference_only=True)]), schedule([event()], source_type='official-event-window')):
            r = build(global_=g)
            self.assertEqual(r['totals']['fresh_events'], 0)
            self.assertEqual(r['rows'][0]['state'], 'reference_only')

    def test_date_only_named_fixture_preserves_literal_day(self):
        r = build(global_=schedule([event(date_only=True, start_time='2026-10-19')]))
        self.assertEqual(r['totals']['fresh_events'], 1)
        self.assertEqual(r['totals']['date_only_events'], 1)

    def test_chicago_window_boundaries_and_inactive_events(self):
        r = build(global_=schedule([event(start_time='2026-10-19T01:00:00Z'), event(id='late', start_time='2026-10-27T02:00:00Z')]))
        self.assertEqual(r['totals']['fresh_events'], 1)
        for status in ('COMPLETED', 'CANCELLED', 'POSTPONED', 'REMOVED'):
            self.assertEqual(build(global_=schedule([event(status=status)]))['totals']['fresh_events'], 0)

    def test_unhealthy_configured_family_not_working(self):
        r = build(global_=schedule(ok=False))
        self.assertEqual(r['totals']['connected_provider_families'], 0)
        self.assertEqual(r['totals']['configured_provider_families'], 1)

    def test_window_filter_and_empty_window_coverage(self):
        r = build(global_=schedule([event(start_time='2026-10-27T12:00:00Z')]))
        self.assertEqual(r['totals']['fresh_events'], 0)
        g = schedule();g['window_end'] = '2026-10-25'
        self.assertEqual(build(global_=g)['rows'][0]['state'], 'inactive_unknown')

    def test_odds_exact_mapping_and_three_hour_ttl(self):
        m = {'mappings': [{'provider_key': 'key', 'catalog_identity_key': 'a'}]}
        for stamp,state in [('2026-10-19T08:00:00Z','fresh'),('2026-10-19T06:00:00Z','stale')]:
            o = dict(sources=[dict(provider_key='key', status='ok', observed_at=stamp)], events=[event(provider_key='key', catalog_identity_key='a', observed_at=stamp)])
            r = build(global_=schedule(), oddsMap=m, oddsEvents=o)
            self.assertEqual(r['rows'][0]['state'], state)
        o['events'][0]['provider_key'] = 'unknown'
        self.assertEqual(build(oddsMap=m, oddsEvents=o)['totals']['fresh_events'], 0)

    def test_exact_cross_provider_dedup_but_not_doubleheaders(self):
        m = {'mappings': [{'provider_key': 'key', 'catalog_identity_key': 'a'}]}
        o = dict(sources=[dict(provider_key='key', status='ok', observed_at='2026-10-19T08:00:00Z')], events=[event(provider_key='key', catalog_identity_key='a', observed_at='2026-10-19T08:00:00Z')])
        r = build(global_=schedule([event()]), oddsMap=m, oddsEvents=o)
        self.assertEqual(r['totals']['fresh_events'], 1)
        r = build(global_=schedule([event(), event(id='game2')]), oddsMap=m, oddsEvents=o)
        self.assertEqual(r['totals']['fresh_events'], 3)

    def test_global_name_and_odds_participants_exact_dedup(self):
        m = {'mappings': [{'provider_key': 'key', 'catalog_identity_key': 'a'}]}
        o = dict(sources=[dict(provider_key='key', status='ok', observed_at='2026-10-19T08:00:00Z')], events=[event(provider_key='key', catalog_identity_key='a', participants=['Away', 'Home'], observed_at='2026-10-19T08:00:00Z')])
        for name in ('Away at Home', 'Home vs Away', 'Away vs. Home'):
            r = build(global_=schedule([event(name=name)]), oddsMap=m, oddsEvents=o)
            self.assertEqual(r['totals']['fresh_events'], 1)
        for name in ('Away FC at Home', 'Away at Home at Other'):
            r = build(global_=schedule([event(name=name)]), oddsMap=m, oddsEvents=o)
            self.assertEqual(r['totals']['fresh_events'], 2)
        r = build(global_=schedule([event(name='Away at Home'), event(id='game2', name='Away at Home')]), oddsMap=m, oddsEvents=o)
        self.assertEqual(r['totals']['fresh_events'], 3)

    def test_scoped_index_matches_linear_reference_on_retained_data(self):
        # Keep the prior per-event scan as a behavioral oracle for this optimization.
        script = r"""
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(process.argv[1],'utf8');
const needle='const scoped=scopedSources.get(event.source_id)?.get(host(event.source_endpoint))||[];';
if(!source.includes(needle))throw Error('Update optimization oracle for changed implementation');
const linear=source.replace(needle,'const scoped=[...sourceMap.values()].filter(s=>fixtureSource(s)&&list(s.scope_source_ids).includes(event.source_id)&&[host(s.endpoint),host(s.official_schedule_url)].includes(host(event.source_endpoint)));');
const sandbox={module:{exports:{}},URL,Intl};vm.runInNewContext(linear,sandbox);
const read=name=>JSON.parse(fs.readFileSync(process.argv[2]+'/data/'+name));
const input={coverage:read('priority2-coverage-inventory.json'),global:read('global-schedule.json'),oddsMap:read('odds-api-catalog-mappings.json'),now:'2026-10-19T10:00:00Z'};
const actual=require(process.argv[1]).build(input),expected=sandbox.module.exports.build(input);
if(JSON.stringify(actual)!==JSON.stringify(expected))throw Error('Indexed lookup changed result');
// Same build function must observe changed timestamps, not retain cross-build health.
input.now='2026-10-22T10:00:00Z';
if(require(process.argv[1]).build(input).totals.fresh_events!==0)throw Error('Cached freshness escaped build');
"""
        subprocess.run(['node', '-e', script, str(MODULE), str(ROOT)], check=True, capture_output=True, text=True)

    def test_scoped_index_preserves_ambiguity_and_domain_matching(self):
        c = {'identities': [{'identity_key': 'a', 'sources': [{'id': 'child'}]}]}
        g = schedule([event(source_id='child', source_endpoint='https://api.vendor.test/game')], scope_source_ids=['child'])
        g['sources'].append(dict(g['sources'][0], id='second'))
        r = build(coverage=c, global_=g)
        self.assertEqual(r['totals']['fresh_events'], 0)
        g['sources'][1]['endpoint'] = 'https://different.test/fixtures'
        self.assertEqual(build(coverage=c, global_=g)['totals']['fresh_events'], 1)

    def test_totals_partition_real_retained_data(self):
        read = lambda name: json.loads((ROOT / 'data' / name).read_text())
        r = build(coverage=read('priority2-coverage-inventory.json'), global_=read('global-schedule.json'), oddsMap=read('odds-api-catalog-mappings.json'))
        self.assertEqual(r['totals']['identities'], 733)
        self.assertEqual(sum(r['totals'][k] for k in ['fresh', 'stale', 'healthy_empty', 'inactive_unknown', 'unmapped', 'reference_only']), 733)
        self.assertEqual(r['totals']['mapped'] + r['totals']['not_mapped'], 733)
        self.assertFalse(any('espn.com' in f['name'] for f in r['providerFamilies']))


if __name__ == '__main__':
    unittest.main()
