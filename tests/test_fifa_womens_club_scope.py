import json
import unittest
import tempfile
from pathlib import Path
from scripts.publisher_access_policy import permission_hold_reason
from scripts.apply_catalog_source_corrections import apply_fifa_correction

DATA = Path(__file__).resolve().parents[1] / 'data'


class FifaWomensClubScopeTests(unittest.TestCase):
    def test_lagging_publication_overlay_cannot_restore_wrong_competition(self):
        sid = 'soccer-fifa-womens-club-world-cup'
        config = json.loads((DATA/'soccer-international-sources.json').read_text())
        wrong = {'source_id': sid, 'name': 'Auckland at Naegohyang'}
        other = {'source_id': 'unrelated', 'name': 'Preserved fixture', 'collection_paused': True}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'data').mkdir()
            def save(name, value):
                (root/'data'/name).write_text(json.dumps(value))
            save('soccer-international-sources.json', config)
            save('global-schedule.json', {'events': [wrong, other], 'event_count': 2,
                'sources': [{'id': sid, 'source_type': 'espn-daily'}, {'id': 'unrelated', 'stale': True}],
                'coverage_gaps': [{'area': 'Soccer', 'competitions': ['Charity Shield', 'Charity Shield']}]})
            save('competition-identity-registry.json', {'competitions': [
                {'identity_key': 'soccer-international-fifa-club-world-cup-women', 'source_ids': [sid], 'events': [wrong], 'participants': ['Auckland']}]})
            apply_fifa_correction(root)
            corrected = json.loads((root/'data/global-schedule.json').read_text())
            self.assertEqual([other], corrected['events'])
            self.assertEqual({'id': 'unrelated', 'stale': True}, corrected['sources'][1])
            self.assertEqual('coverage-gap', corrected['sources'][0]['source_type'])
            self.assertEqual(3, len(corrected['coverage_gaps'][0]['competitions']))
            before = (root/'data/global-schedule.json').read_bytes()
            apply_fifa_correction(root)
            self.assertEqual(before, (root/'data/global-schedule.json').read_bytes())

    def test_club_world_cup_never_uses_champions_cup_fixture_source(self):
        source_id = 'soccer-fifa-womens-club-world-cup'
        read = lambda f: json.loads((DATA / f).read_text())
        source = next(x for x in read('soccer-international-sources.json')['sources'] if x['id'] == source_id)
        self.assertEqual('coverage-gap', source['source_type'])
        self.assertEqual('pending', source['coverage_status'])
        self.assertNotIn('champions_cup', source['endpoint'])
        self.assertTrue(permission_hold_reason(source['retired_mapping']['endpoint']))
        schedule = read('global-schedule.json')
        self.assertFalse(any(x.get('source_id') == source_id for x in schedule['events']))
        identity = next(x for x in read('competition-identity-registry.json')['competitions'] if source_id in x['source_ids'])
        self.assertEqual([], identity['events'])
        self.assertEqual([], identity['participants'])
        leaves = [e for s in read('catalog-season-map.json')['sports'] for g in s.get('groups', []) for p in g.get('events', []) for e in (p.get('coverage_children') or [p])]
        event = next(x for x in leaves if x.get('source_id') == source_id)
        self.assertEqual('FIFA Club World Cup | Women', event['label'])
        self.assertEqual(('2028-01-05', '2028-01-30'), (event['season_start_date'], event['season_end_date']))
        self.assertTrue(event['season_window_complete'])
        self.assertFalse(event.get('season_hold'))
        self.assertEqual(735, len(leaves))
