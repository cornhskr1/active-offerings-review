"""The shared collector must keep exact SARU scope and atomic failures."""
import datetime
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SaruCollectorIntegrationTests(unittest.TestCase):
    def run_block(self, collect):
        source = next(s for s in json.loads((ROOT / 'data/global-schedule-sources.json').read_text())['sources'] if s['id'] == 'rugby-usa')
        refresh = (ROOT / 'scripts/refresh_global_schedule.py').read_text()
        start = refresh.index('    if source.get("source_type")=="saru-exact-matches":')
        end = refresh.index('    if source.get("source_type")=="saru-matches":', start)
        namespace = dict(configured=[source], collect_saru_exact=collect,
            requests=SimpleNamespace(get=lambda *args, **kwargs: None),
            TODAY=datetime.date(2026, 10, 18), END=datetime.date(2026, 10, 25),
            NOW_UTC=datetime.datetime(2026, 10, 18, 16, tzinfo=datetime.timezone.utc),
            events=[], seen=set(), source_status=[], count=0, errors=[])
        exec(compile('for source in configured:\n' + refresh[start:end], 'saru-collector', 'exec'), namespace)
        return namespace

    def test_evidence_and_partial_limits_reach_publication(self):
        event = dict(id='verified', source_id='rugby-usa', league='Women’s USA Rugby Events | Women')
        n = self.run_block(lambda *args: ([event], {'requests_succeeded': 1, 'rows_returned': 6}))
        self.assertEqual(n['events'], [event])
        status = n['source_status'][0]
        self.assertTrue(status['ok'])
        self.assertEqual(status['events'], 1)
        self.assertEqual(status['rows_returned'], 6)
        self.assertEqual(status['coverage_status'], 'partial')
        self.assertFalse(status['coverage_complete'])

    def test_collection_failure_never_publishes_candidates(self):
        def fail(*args):
            raise ValueError('second page failed')
        n = self.run_block(fail)
        self.assertEqual(n['events'], [])
        self.assertFalse(n['source_status'][0]['ok'])
        self.assertEqual(n['source_status'][0]['events'], 0)
        self.assertIn('second page failed', n['source_status'][0]['errors'])

    def test_exact_catalog_sources_and_unresolved_varsity_preserved(self):
        sources = {s['id']: s for s in json.loads((ROOT / 'data/global-schedule-sources.json').read_text())['sources']}
        for key, league in [('rugby-usa', 'Women’s USA Rugby Events | Women'), ('rugby-saru-currie-first', 'Currie Cup | Men')]:
            self.assertEqual(sources[key]['catalog_terms'], [league])
            self.assertEqual(sources[key]['coverage_status'], 'partial')
            self.assertFalse(sources[key]['coverage_complete'])
        self.assertEqual(sources['rugby-saru']['source_type'], 'coverage-gap')
        self.assertNotIn('Currie Cup | Men', sources['rugby-saru']['catalog_terms'])
        self.assertEqual(sources['rugby-saru-currie-premier']['source_type'], 'saru-matches')
        seasons = json.loads((ROOT / 'data/catalog-season-map.json').read_text())
        rows = [e for s in seasons['sports'] for g in s.get('groups', []) for e in g.get('events', [])]
        currie = next(e for e in rows if e.get('key') == 'rugby-za-currie-cup')
        self.assertNotIn('source_id', currie)
        self.assertNotIn('season_start', currie)
        self.assertNotIn('season_end', currie)
        self.assertEqual(currie['season_start_date'], '2026-06-13')
        self.assertEqual(currie['season_end_date'], '2026-09-12')
        self.assertFalse(currie['season_window_complete'])
        self.assertEqual(set(currie['source_ids']), {'rugby-saru-currie-premier', 'rugby-saru-currie-first'})
        usa = next(e for e in rows if e.get('key') == 'rugby-us-womens-events')
        self.assertFalse(usa['season_window_complete'])
        self.assertEqual(usa['season_end_date'], '2026-10-30')
        self.assertEqual(usa['restrictions'], [])


if __name__ == '__main__':
    unittest.main()
