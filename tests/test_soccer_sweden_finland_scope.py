"""Nordic cup editions and league qualification remain separately scoped."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class SwedenFinlandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / 'catalog-season-map.json').read_text())['sports'] if s['sport'] == 'Soccer')
        groups = [g for g in soccer['groups'] if g.get('country') in {'Sweden', 'Finland'}]
        cls.events = {e['key']: e for g in groups for e in g['events']}
        cls.children = {c['key']: c for c in cls.events['soccer-sweden-svenska-cupen-men-and-women']['coverage_children']}
        cls.inventory = {r['identity_key']: r for r in json.loads((DATA / 'priority2-coverage-inventory.json').read_text())['identities']}

    def test_finnish_cups_do_not_inherit_league_dates(self):
        for key, bounds in {
            'soccer-finland-finnish-cup-men': ('2026-02-06', '2026-09-05'),
            'soccer-finland-finnish-league-cup-men': ('2026-01-16', '2026-03-21'),
        }.items():
            with self.subTest(key=key):
                item = self.events[key]
                self.assertEqual(bounds, (item['season_start_date'], item['season_end_date']))
                self.assertEqual('DATED_WINDOW', self.inventory[key]['season_state'])
                self.assertEqual('ADAPTER_GAP', self.inventory[key]['coverage_state'])

    def test_swedish_cup_children_cross_into_next_year_without_guessing_final(self):
        self.assertEqual({'soccer-sweden-svenska-cupen-men', 'soccer-sweden-svenska-cupen-women'}, set(self.children))
        starts = {'soccer-sweden-svenska-cupen-men': '2026-06-02', 'soccer-sweden-svenska-cupen-women': '2026-05-19'}
        for key, start in starts.items():
            with self.subTest(key=key):
                item = self.children[key]
                self.assertEqual(start, item['season_start_date'])
                self.assertNotIn('season_end_date', item)
                self.assertFalse(item['season_window_complete'])
                self.assertEqual('PARTIAL_WINDOW', self.inventory[key]['season_state'])
                self.assertEqual('ADAPTER_GAP', self.inventory[key]['coverage_state'])
        self.assertNotEqual(self.children['soccer-sweden-svenska-cupen-men']['source_id'], self.children['soccer-sweden-svenska-cupen-women']['source_id'])

    def test_league_qualification_is_not_hidden_in_regular_season(self):
        for key in ('soccer-finland-veikkausliiga-men', 'soccer-sweden-allsvenskan-men', 'soccer-sweden-superettan-men'):
            with self.subTest(key=key):
                self.assertFalse(self.events[key]['season_window_complete'])
                self.assertEqual('PARTIAL_WINDOW', self.inventory[key]['season_state'])


if __name__ == '__main__':
    unittest.main()
