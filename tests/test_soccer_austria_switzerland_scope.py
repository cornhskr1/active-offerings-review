"""Official Austrian and Swiss calendars retain their competition-specific boundaries."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class AustriaSwitzerlandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / 'catalog-season-map.json').read_text())['sports'] if s['sport'] == 'Soccer')
        cls.events = {e['key']: e for g in soccer['groups'] if g.get('country') in {'Austria', 'Switzerland'} for e in g['events']}
        cls.inventory = {r['identity_key']: r for r in json.loads((DATA / 'priority2-coverage-inventory.json').read_text())['identities']}
        cls.sources = {x['id']: x for x in json.loads((DATA / 'soccer-uefa-domestic-sources.json').read_text())['sources']}

    def test_eight_distinct_identities_and_scoped_dates(self):
        self.assertEqual(8, len(self.events))
        bounds = {
            'soccer-austria-austrian-bundesliga-men': ('2026-07-31', '2027-05-30', 'PARTIAL_WINDOW'),
            'soccer-austria-2-liga-men': ('2026-07-31', '2027-05-30', 'DATED_WINDOW'),
            'soccer-austria-austrian-cup-men': ('2026-07-24', '2027-05-01', 'DATED_WINDOW'),
            'soccer-switzerland-swiss-super-league-men': ('2026-07-25', '2027-05-30', 'PARTIAL_WINDOW'),
            'soccer-switzerland-swiss-challenge-league-men': ('2026-07-24', '2027-05-28', 'PARTIAL_WINDOW'),
            'soccer-switzerland-swiss-cup-men': ('2026-08-14', '2027-06-06', 'DATED_WINDOW'),
        }
        for key, (start, end, state) in bounds.items():
            with self.subTest(key=key):
                event = self.events[key]
                self.assertEqual((start, end), (event['season_start_date'], event['season_end_date']))
                self.assertEqual(state, self.inventory[key]['season_state'])
                self.assertIn(event['source_id'], self.sources)

    def test_womens_competitions_do_not_inherit_mens_windows(self):
        for key in ('soccer-austria-austrian-frauen-bundesliga-women', 'soccer-austria-fb-frauen-cup-women'):
            with self.subTest(key=key):
                event = self.events[key]
                self.assertTrue(event['season_hold'])
                self.assertEqual('DOCUMENTED_HOLD', self.inventory[key]['season_state'])
                self.assertEqual('ADAPTER_GAP', self.inventory[key]['coverage_state'])
        self.assertNotEqual(self.events['soccer-austria-austrian-cup-men']['source_id'],
                            self.events['soccer-austria-fb-frauen-cup-women']['source_id'])

    def test_swiss_cup_uses_federation_source_not_league_calendar(self):
        cup = self.sources[self.events['soccer-switzerland-swiss-cup-men']['source_id']]
        league = self.sources[self.events['soccer-switzerland-swiss-super-league-men']['source_id']]
        self.assertIn('football.ch', cup['official_schedule_url'])
        self.assertIn('sfl.ch', league['official_schedule_url'])
        self.assertNotEqual(cup['official_schedule_url'], league['official_schedule_url'])


if __name__ == '__main__':
    unittest.main()
