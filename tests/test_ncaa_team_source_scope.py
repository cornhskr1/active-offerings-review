"""Partial team feeds cannot expand the exact catalog children or championship scope."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
IDS={'ncaa-water-polo-di-men':('NCAA Water Polo','Division I Water Polo | Men'),
     'ncaa-ice-hockey-di-women':('NCAA Ice Hockey','Division I Ice Hockey | Women')}
class NcaaTeamScopeTests(unittest.TestCase):
    def test_exact_partial_sources(self):
        sources=json.loads((ROOT/'data/global-schedule-sources.json').read_text())['sources']
        selected=[s for s in sources if s.get('source_type')=='official-ncaa-reviewed-team-fixtures']
        self.assertEqual(set(IDS),{s['id'] for s in selected})
        for s in selected:
            self.assertEqual(IDS[s['id']],(s['sport'],s['league']))
            self.assertEqual([s['league']],s['catalog_terms'])
            self.assertEqual('partial',s['coverage_status'])
            self.assertIs(False,s['coverage_complete'])
    def test_championship_holds_remain(self):
        def walk(value):
            if isinstance(value,dict):
                yield value
                for child in value.values():yield from walk(child)
            elif isinstance(value,list):
                for child in value:yield from walk(child)
        tree=json.loads((ROOT/'data/catalog-season-map.json').read_text())
        rows={r['key']:r for r in walk(tree) if r.get('key') in IDS}
        self.assertEqual(set(IDS),set(rows))
        for key,row in rows.items():
            self.assertTrue(row['season_hold'])
            self.assertEqual(key,row['source_id'])
            self.assertTrue(row['partial_regular_season_source'])
            self.assertIn('National Collegiate',row['hold_reason'])
