"""Central European league, cup, and Supercup boundaries stay distinct."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class PolandCzechScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / 'catalog-season-map.json').read_text())['sports'] if s['sport'] == 'Soccer')
        cls.events = {e['key']: e for g in soccer['groups'] if g.get('country') in {'Poland', 'Czech Republic'} for e in g['events']}
        cls.sources = {s['id']: s for s in json.loads((DATA / 'soccer-uefa-domestic-sources.json').read_text())['sources']}
        cls.inventory = {r['identity_key']: r for r in json.loads((DATA / 'priority2-coverage-inventory.json').read_text())['identities']}

    def test_six_independent_identities(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e['source_id'] for e in self.events.values()}))
        for key, e in self.events.items():
            with self.subTest(key=key):
                self.assertIn(e['source_id'], self.sources)

    def test_czech_qualification_and_preliminary_rounds(self):
        for key in ('soccer-czech-republic-czech-first-league-men', 'soccer-czech-republic-czech-national-football-league-men'):
            with self.subTest(key=key):
                self.assertEqual('2027-06-06', self.events[key]['season_end_date'])
                self.assertEqual('PARTIAL_WINDOW', self.inventory[key]['season_state'])
        cup = self.events['soccer-czech-republic-czech-cup-men']
        self.assertEqual(('2026-07-24', '2027-05-12'), (cup['season_start_date'], cup['season_end_date']))

    def test_polish_cup_and_completed_supercup(self):
        cup = self.events['soccer-poland-polish-cup-men']
        self.assertEqual(('2026-08-05', '2027-05-02'), (cup['season_start_date'], cup['season_end_date']))
        self.assertEqual('PARTIAL_WINDOW', self.inventory[cup['key']]['season_state'])
        supercup = self.events['soccer-poland-polish-super-cup-men']
        self.assertEqual('2026-07-16', supercup['season_start_date'])
        self.assertEqual('OFFICIAL_WINDOW_ONLY', self.inventory[supercup['key']]['coverage_state'])
        source = self.sources[supercup['source_id']]
        self.assertEqual([('2026-07-16', '2026-07-16')], [(e['start_date'], e['end_date']) for e in source['official_events']])


if __name__ == '__main__':
    unittest.main()
