"""Croatian and Serbian competition dates do not imply unverified finals."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class CroatiaSerbiaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / 'catalog-season-map.json').read_text())['sports'] if s['sport'] == 'Soccer')
        cls.events = {e['key']: e for g in soccer['groups'] if g.get('country') in {'Croatia', 'Serbia'} for e in g['events']}
        cls.inventory = {r['identity_key']: r for r in json.loads((DATA / 'priority2-coverage-inventory.json').read_text())['identities']}

    def test_five_independent_sources(self):
        self.assertEqual(5, len(self.events))
        self.assertEqual(5, len({e['source_id'] for e in self.events.values()}))
        self.assertEqual(('2026-07-31', '2027-05-23'), (
            self.events['soccer-croatia-croatian-football-league-supersport-hnl-men']['season_start_date'],
            self.events['soccer-croatia-croatian-football-league-supersport-hnl-men']['season_end_date']))

    def test_no_fabricated_supercup_or_cup_final(self):
        key = 'soccer-croatia-croatian-super-cup-men'
        self.assertTrue(self.events[key]['season_hold'])
        self.assertEqual('DOCUMENTED_HOLD', self.inventory[key]['season_state'])
        self.assertNotIn('season_end_date', self.events[key])
        for key in ('soccer-croatia-croatian-cup-men', 'soccer-serbia-serbian-cup-men', 'soccer-serbia-serbian-superliga-men'):
            with self.subTest(key=key):
                self.assertFalse(self.events[key]['season_window_complete'])
                self.assertNotIn('season_end_date', self.events[key])
                self.assertEqual('PARTIAL_WINDOW', self.inventory[key]['season_state'])


if __name__ == '__main__':
    unittest.main()
