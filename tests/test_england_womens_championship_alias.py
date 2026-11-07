import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


class EnglandWomensAliasTests(unittest.TestCase):
    def test_shared_partial_calendar_preserves_original_identities_and_one_feed(self):
        code = """
const fs=require('fs'),C=require('./assets/catalog-workspace.js');
const load=n=>JSON.parse(fs.readFileSync('data/'+n+'.json'));
const rows=C.build({catalog:load('catalog-live'),seasonMap:load('catalog-season-map'),identities:load('competition-identity-registry'),sources:load('global-schedule').sources,today:'2026-11-06'});
console.log(JSON.stringify(C.identityRows(rows,load('competition-identity-registry'),'2026-11-06',load('global-schedule').sources).filter(x=>['soccer-england-super-league-2-women','soccer-england-the-championship-women','soccer-england-the-championship-men'].includes(x.id))));
"""
        result = subprocess.run(['node', '-e', code], cwd=ROOT, check=True, capture_output=True, text=True)
        displayed = {r['id']: r for r in json.loads(result.stdout)}
        self.assertEqual(3, len(displayed))
        legacy_display = displayed['soccer-england-the-championship-women']
        self.assertEqual('unknown', legacy_display['status'])
        self.assertIn('Women’s Super League 2 (WSL2)', [a['name'] for a in legacy_display['aliases']])
        self.assertNotIn('Women’s Super League 2 (WSL2)', [a['name'] for a in displayed['soccer-england-the-championship-men']['aliases']])
        m = json.loads((DATA/'catalog-season-map.json').read_text())
        rows = {e['key']: e for s in m['sports'] for g in s.get('groups', []) for p in g.get('events', []) for e in (p.get('coverage_children') or [p])}
        current = rows['soccer-england-super-league-2-women']
        legacy = rows['soccer-england-the-championship-women']
        self.assertEqual('Super League 2 | Women', current['catalog_event'])
        self.assertEqual('The Championship | Women', legacy['label'])
        self.assertEqual('Formerly Women’s Championship', current['display_aliases'][0]['name'])
        self.assertEqual('Women’s Super League 2 (WSL2)', legacy['display_aliases'][0]['name'])
        for row in (current, legacy):
            self.assertEqual('2026-09-04', row['season_start_date'])
            self.assertFalse(row['season_window_complete'])
            self.assertFalse(row.get('season_end_date'))
            self.assertFalse(row.get('season_hold'))
        self.assertEqual(current['key'], legacy['calendar_identity_key'])
        sources = json.loads((DATA/'soccer-uefa-domestic-sources.json').read_text())['sources']
        source = next(s for s in sources if s['id'] == current['source_id'])
        alias = next(s for s in sources if s['id'] == legacy['source_id'])
        self.assertEqual('official-wsl2-fixtures', source['source_type'])
        self.assertEqual('coverage-gap', alias['source_type'])
        self.assertEqual('pending', alias['coverage_status'])
        self.assertEqual(735, len(rows))
