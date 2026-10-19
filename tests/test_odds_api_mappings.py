"""Exact catalog scope for offline-only provider snapshot imports."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class OddsApiMappingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'data/odds-api-catalog-mappings.json').read_text())
        self.rows = self.config['mappings']
        registry = json.loads((ROOT / 'data/competition-identity-registry.json').read_text())
        self.catalog = {row['identity_key']: row for row in registry['competitions']}

    def test_exact_unique_identity_scope(self):
        self.assertEqual(self.config['provider'], 'The Odds API')
        self.assertEqual(len(self.rows), 85)
        self.assertEqual(len({row['provider_key'] for row in self.rows}), 85)
        self.assertEqual(len({row['catalog_identity_key'] for row in self.rows}), 85)
        for row in self.rows:
            catalog = self.catalog[row['catalog_identity_key']]
            self.assertEqual(row['sport'], catalog['sport'])
            self.assertEqual(row['league'], catalog['league'])
            self.assertFalse(row['coverage_complete'])
            self.assertEqual(row['region'], '')

    def test_conditional_futures_and_generic_tours_excluded(self):
        keys = {row['provider_key'] for row in self.rows}
        for key in ('americanfootball_ncaaf', 'basketball_ncaab', 'basketball_wncaab',
                    'boxing_boxing', 'mma_mixed_martial_arts', 'cricket_test_match',
                    'soccer_japan_j_league', 'soccer_belgium_first_div',
                    'soccer_league_of_ireland', 'tennis_atp_paris_masters',
                    'americanfootball_nfl_super_bowl_winner'):
            self.assertNotIn(key, keys)
        self.assertTrue(all('winner' not in key for key in keys))

    def test_config_has_no_access_material(self):
        text = json.dumps(self.config).lower()
        for forbidden in ('apikey', 'api_key', 'authorization', 'bearer', 'bookmakers'):
            self.assertNotIn(forbidden, text)

if __name__ == '__main__':
    unittest.main()
