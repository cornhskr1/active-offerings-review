"""Official season bounds and fail-closed source scope for Belgium and Scotland."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class BelgiumScotlandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / 'catalog-season-map.json').read_text())['sports'] if s['sport'] == 'Soccer')
        cls.events = {e['key']: e for g in soccer['groups'] if g.get('country') in {'Belgium', 'Scotland'} for e in g['events']}
        cls.sources = {s['id']: s for f in ('global-schedule-sources.json', 'soccer-uefa-domestic-sources.json') for s in json.loads((DATA / f).read_text())['sources']}
        cls.inventory = {r['identity_key']: r for r in json.loads((DATA / 'priority2-coverage-inventory.json').read_text())['identities']}

    def test_ten_country_identities_and_dated_scottish_competitions(self):
        self.assertEqual(10, len(self.events))
        expected = {
            'soccer-scotland-scottish-premiership-men': ('2026-07-31', '2027-05-23'),
            'soccer-scotland-scottish-championship-men': ('2026-07-31', '2027-04-30'),
            'soccer-scotland-scottish-cup-men': ('2026-08-01', '2027-05-22'),
            'soccer-scotland-scottish-league-cup-men': ('2026-07-11', '2026-12-13'),
            'soccer-scotland-challenge-cup-men': ('2026-08-11', '2027-04-04'),
        }
        for key, dates in expected.items():
            with self.subTest(key=key):
                self.assertEqual(dates, tuple(self.events[key][f'season_{part}_date'] for part in ('start', 'end')))
                self.assertEqual('ADAPTER_CONFIGURED', self.inventory[key]['coverage_state'])
        championship = 'soccer-scotland-scottish-championship-men'
        self.assertFalse(self.events[championship]['season_window_complete'])
        self.assertEqual('PARTIAL_WINDOW', self.inventory[championship]['season_state'])

    def test_discontinued_belgian_championship_playoffs_do_not_inherit_top_division(self):
        league = self.events['soccer-belgium-belgian-pro-league-men']
        playoffs = self.events['soccer-belgium-championship-playoffs-i-and-ii-men']
        self.assertEqual(('2026-08-07', '2027-05-23'), (league['season_start_date'], league['season_end_date']))
        self.assertTrue(playoffs['season_hold'])
        self.assertNotEqual(league['source_id'], playoffs['source_id'])
        self.assertEqual('coverage-gap', self.sources[playoffs['source_id']]['source_type'])
        self.assertEqual('DOCUMENTED_HOLD', self.inventory[playoffs['key']]['season_state'])
        challenger = self.events['soccer-belgium-challenger-pro-league-men']
        self.assertEqual(('2026-08-14', '2027-05-22'), (challenger['season_start_date'], challenger['season_end_date']))
        self.assertEqual('ADAPTER_CONFIGURED', self.inventory[challenger['key']]['coverage_state'])
        self.assertEqual('partial', self.sources[challenger['source_id']]['coverage_status'])
        cup = self.events['soccer-belgium-belgian-cup-beker-van-belgi-men']
        self.assertNotIn('season_hold', cup)
        self.assertEqual('OFFICIAL_WINDOW_ONLY', self.inventory[cup['key']]['coverage_state'])
        self.assertEqual('PARTIAL_WINDOW', self.inventory[cup['key']]['season_state'])
        self.assertEqual('ADAPTER_GAP', self.inventory[playoffs['key']]['coverage_state'])

    def test_belgian_supercup_is_only_a_single_official_window(self):
        key = 'soccer-belgium-belgian-super-cup-men'
        event = self.events[key]
        source = self.sources[event['source_id']]
        self.assertEqual('official-event-window', source['source_type'])
        self.assertEqual('OFFICIAL_WINDOW_ONLY', self.inventory[key]['coverage_state'])
        self.assertEqual(('2026-07-31', '2026-07-31'),
                         (source['official_events'][0]['start_date'], source['official_events'][0]['end_date']))
        self.assertNotIn('2027', source['official_events'][0]['name'])


if __name__ == '__main__':
    unittest.main()
