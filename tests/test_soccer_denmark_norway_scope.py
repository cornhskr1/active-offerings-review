"""Danish and Norwegian league/cup calendars do not cross edition boundaries."""
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


class DenmarkNorwayScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA/'catalog-season-map.json').read_text())['sports'] if s['sport']=='Soccer')
        cls.events = {e['key']:e for g in soccer['groups'] if g.get('country') in {'Denmark','Norway'} for e in g['events']}
        cls.inventory = {r['identity_key']:r for r in json.loads((DATA/'priority2-coverage-inventory.json').read_text())['identities']}
        cls.sources = {x['id']:x for x in json.loads((DATA/'soccer-uefa-domestic-sources.json').read_text())['sources']}

    def test_six_distinct_identities_and_edition_bounds(self):
        self.assertEqual(6,len(self.events))
        bounds={
            'soccer-denmark-danish-superliga-men':('2026-07-24','2027-06-03','PARTIAL_WINDOW'),
            'soccer-denmark-danish-1st-division-men':('2026-07-24','2027-06-06','DATED_WINDOW'),
            'soccer-denmark-danish-cup-men':('2026-08-05','2027-05-06','PARTIAL_WINDOW'),
            'soccer-norway-eliteserien-men':('2026-03-14','2026-12-21','PARTIAL_WINDOW'),
            'soccer-norway-obos-ligaen-men':('2026-04-05','2026-12-21','PARTIAL_WINDOW'),
        }
        for key,(start,end,state) in bounds.items():
            with self.subTest(key=key):
                e=self.events[key]
                self.assertEqual((start,end),(e['season_start_date'],e['season_end_date']))
                self.assertEqual(state,self.inventory[key]['season_state'])
                if key == 'soccer-denmark-danish-superliga-men':
                    self.assertEqual('denmark',e['source_id'])
                else:
                    self.assertIn(e['source_id'],self.sources)

    def test_norwegian_cup_stays_in_2027_edition_hold(self):
        key='soccer-norway-norwegian-cup-men'
        e=self.events[key]
        self.assertTrue(e['season_hold'])
        self.assertIn('2027 edition',e['season_window'])
        self.assertNotIn('season_end_date',e)
        self.assertEqual('DOCUMENTED_HOLD',self.inventory[key]['season_state'])
        self.assertEqual('ADAPTER_GAP',self.inventory[key]['coverage_state'])
        self.assertNotEqual(e['source_id'],self.events['soccer-norway-eliteserien-men']['source_id'])

    def test_danish_cup_source_is_separate_from_league(self):
        cup=self.events['soccer-denmark-danish-cup-men']
        self.assertNotEqual(cup['source_id'],self.events['soccer-denmark-danish-superliga-men']['source_id'])
        self.assertIn('datoplan-for',self.sources[cup['source_id']]['official_schedule_url'])


if __name__=='__main__':unittest.main()
