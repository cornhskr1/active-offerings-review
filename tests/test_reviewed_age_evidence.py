"""Regression contract for the 2026-10-14 evidence correction and safe refresh."""
import ast
from copy import deepcopy
import datetime
import json
from pathlib import Path
import re
import unittest

from scripts.athlete_age_evidence import (
    age_on, age_status_on, identity, merge_records, merge_refresh_record,
    name_key, partition_registry, update_cache, index_records,
)
from scripts.build_tennis_review import build_review

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def load(name):
    return json.loads((DATA / (name + '.json')).read_text())


def reviewed(name='Jordan Lee', dob='2010-05-04', player_id='itf:800699673'):
    return {'name': name, 'canonical_name': name, 'official_player_id': player_id,
            'aliases': ['J. lee'], 'dob': dob, 'age': 16, 'age_status': 'VERIFIED U18',
            'age_evidence': {'status': 'verified_dob', 'dob': dob, 'checked_at': '2026-10-14',
                             'sources': [{'url': 'https://www.itftennis.com/review.pdf'}],
                             'review': {'id': 'official-age-review-2026-10-14'}}}


class ReviewedDataTests(unittest.TestCase):
    def test_every_review_row_has_consistent_corrected_evidence(self):
        artifact = load('athlete-age-evidence-review')
        self.assertEqual(artifact['input_rows'], 84)
        self.assertEqual(artifact['unique_athletes'], 82)
        self.assertEqual(len(artifact['input_records']), 84)
        canonical = {row['name']: row for row in artifact['records']}
        self.assertEqual(len(canonical), 82)
        self.assertNotIn('reference_identity_digest', json.dumps(artifact))
        evidence_counts = {}
        for original in artifact['input_records']:
            row = canonical[original['canonical_person']]
            evidence = row['age_evidence']
            self.assertIn(original['name'], evidence['review']['input_names'])
            self.assertEqual(evidence['checked_at'], '2026-10-14')
            self.assertIn(original['source_url'], [s['url'] for s in evidence['sources']])
            if original['verified_dob']:
                self.assertEqual(evidence['status'], 'verified_dob')
                self.assertEqual(evidence['dob'], original['verified_dob'])
            else:
                self.assertNotIn('dob', evidence)
                self.assertIsNone(row['dob'])
        for row in canonical.values():
            status = row['age_evidence']['status']
            evidence_counts[status] = evidence_counts.get(status, 0) + 1
        self.assertEqual(evidence_counts, {'verified_dob': 80, 'age_only': 1, 'conflicting_dob': 1})

    def test_all_general_identities_and_adults_are_retained(self):
        rows = load('known-u18')['records']
        self.assertEqual(len(rows), 64)
        self.assertTrue(all(row.get('age_evidence') for row in rows))
        shaw = next(r for r in rows if r['athlete'] == 'Alexander Shaw')
        self.assertEqual(shaw['dob'], '2008-04-03')
        self.assertEqual(shaw['age_status'], 'VERIFIED 18+')
        self.assertEqual(age_status_on(shaw, '2026-04-02'), 'VERIFIED U18')
        self.assertEqual(age_status_on(shaw, '2026-04-03'), 'VERIFIED 18+')
        self.assertTrue(all('last_verified' not in row for row in rows))

    def test_tennis_canonical_ids_aliases_and_historical_adults(self):
        registry = load('tennis-u18-registry')
        self.assertEqual(len(registry['records']), 39)
        ids = [identity(r) for r in registry['records']]
        self.assertEqual(len(set(ids)), len(ids))
        for player_id, canonical, alias, dob in (
            ('itf:800699673', 'Jordan Lee', 'J. lee', '2010-05-04'),
            ('itf:800732018', 'Michael Antonius', 'M. antonius', '2010-01-01')):
            row = next(r for r in registry['records'] if identity(r) == player_id)
            self.assertEqual(row['name'], canonical)
            self.assertEqual(row['dob'], dob)
            self.assertIn(alias, row['aliases'])
        adults = [r for r in registry['records'] if age_status_on(r, '2026-10-14') == 'VERIFIED 18+']
        self.assertEqual(len(adults), 8)
        self.assertFalse({identity(x) for x in adults} & {identity(x) for x in registry['verified_u18']})

    def test_conflict_and_age_only_stay_uncertain(self):
        conflict = next(r for r in load('known-u18')['records'] if r['athlete'] == 'Jules Bouffandeau')
        self.assertEqual(conflict['age_evidence']['status'], 'conflicting_dob')
        self.assertEqual({x['dob'] for x in conflict['age_evidence']['candidate_dobs']}, {'2009-07-24', '2009-07-25'})
        self.assertIsNone(conflict['dob'])
        latak = next(r for r in load('tennis-u18-registry')['records'] if r['name'] == 'Marcel Latak')
        self.assertEqual(latak['age_evidence']['status'], 'age_only')
        self.assertIsNone(latak['dob'])
        self.assertIsNone(latak['birth_year'])
        for row in (conflict, latak):
            self.assertEqual(age_status_on(row, '2026-10-14'), 'TARGETED REVIEW')

    def test_reviewed_tennis_cache_matches_registry_without_false_verification(self):
        cache = load('tennis-age-cache')['records']
        for record in load('tennis-u18-registry')['records']:
            if record.get('age_evidence'):
                cached = cache[name_key(record['name'])]
                self.assertEqual(cached['dob'], record['dob'])
                self.assertEqual(cached['age_evidence'], record['age_evidence'])
        self.assertEqual(cache['anastasija cvetkovic']['last_verified'], '2026-09-14T07:31:39.689922+00:00')
        self.assertNotIn('last_verified', cache['jordan lee'])


class RefreshPreservationTests(unittest.TestCase):
    def test_age_only_refresh_does_not_clobber_review_or_identity(self):
        previous = reviewed()
        previous['last_verified'] = '2026-09-09T00:00:00Z'
        incoming = {'name': 'J. Lee', 'official_player_id': 'itf:800699673',
                    'age': 17, 'dob': None, 'birth_year': 2009, 'age_status': 'VERIFIED U18',
                    'source_url': 'https://www.itftennis.com/new-ranking',
                    'last_verified': '2027-01-01T00:00:00Z'}
        result = merge_refresh_record(previous, incoming)
        for key in ('name', 'official_player_id', 'age_evidence', 'dob', 'age', 'last_verified'):
            self.assertEqual(result[key], previous[key])
        self.assertIn('J. lee', result['aliases'])
        self.assertEqual(previous, {**previous})

    def test_failed_refresh_cannot_erase_review_or_invent_verification_date(self):
        previous = reviewed()
        result = merge_refresh_record(previous, {'name': 'Jordan Lee', 'dob': None,
                'age_status': 'UNRESOLVED', 'last_verified': '2030-01-01'})
        self.assertEqual(result['dob'], previous['dob'])
        self.assertNotIn('last_verified', result)

    def test_alias_cache_refresh_keeps_canonical_record_and_review(self):
        previous = reviewed()
        cache = {'jordan lee': deepcopy(previous)}
        result = update_cache(cache, {'name': 'J. lee', 'source_url':
            'https://www.itftennis.com/en/players/jordan-lee/800699673/usa/jt/s/',
            'dob': None, 'age': 17})
        self.assertEqual(result['name'], 'Jordan Lee')
        self.assertEqual(cache['jordan lee']['dob'], '2010-05-04')
        self.assertEqual(len(cache), 1)

    def test_cache_alias_match_cannot_cross_conflicting_official_ids(self):
        adult = reviewed('Adult Reviewed Player', '2000-01-01', 'itf:800111111')
        adult['aliases'] = ['A. Player']
        young = {'name': 'A. Player', 'official_player_id': 'itf:800222222',
                 'age_status': 'VERIFIED U18', 'age': 17}
        for records in ({'adult reviewed player': deepcopy(adult)},
                        {'a player': deepcopy(adult)}):
            result = update_cache(records, deepcopy(young))
            self.assertEqual(result['official_player_id'], 'itf:800222222')
            self.assertNotIn('age_evidence', result)
            adults = [x for x in records.values() if identity(x) == 'itf:800111111']
            self.assertTrue(adults)
            self.assertEqual(adults[0]['age_evidence'], adult['age_evidence'])
        reverse = {'a player': deepcopy(young)}
        update_cache(reverse, deepcopy(adult))
        self.assertEqual(reverse['a player']['official_player_id'], 'itf:800222222')
        self.assertTrue(any(identity(x) == 'itf:800111111' for x in reverse.values()))

    def test_cache_shared_alias_without_official_id_remains_ambiguous(self):
        adult = reviewed('Adult Player', '2000-01-01', 'itf:800111111')
        young = reviewed('Young Player', '2010-01-01', 'itf:800222222')
        adult['aliases'] = young['aliases'] = ['A. Player']
        for rows in ([adult, young], [young, adult]):
            cache = {name_key(row['name']): deepcopy(row) for row in rows}
            result = update_cache(cache, {'name': 'A. Player', 'age': 16})
            self.assertNotIn('official_player_id', result)
            self.assertIsNone(result['dob'])
            self.assertEqual(result['age_evidence']['status'], 'unknown')
            self.assertEqual(result['age_status'], 'TARGETED REVIEW')
            self.assertEqual(result['identity_candidates'], ['itf:800111111', 'itf:800222222'])
            self.assertEqual(cache['adult player']['dob'], adult['dob'])
            self.assertEqual(cache['young player']['dob'], young['dob'])

    def test_registry_refresh_preserves_history_when_rankings_omit_athlete(self):
        previous = reviewed('Former Junior', '2008-10-14', 'itf:800000001')
        records, current, targeted = partition_registry([previous], '2026-10-14')
        self.assertEqual(len(records), 1)
        self.assertEqual(current, [])
        self.assertEqual(targeted, [])
        self.assertEqual(records[0]['age_evidence'], previous['age_evidence'])
        self.assertEqual(age_status_on(records[0], '2026-10-13'), 'VERIFIED U18')

    def test_verified_dob_wins_over_new_ranking_and_changed_source_url(self):
        previous = reviewed()
        refreshed = {'name': 'J. lee', 'source_url': 'https://www.itftennis.com/en/players/jordan-lee/800699673/usa/jt/s/',
                     'age': 17, 'birth_year': 2009, 'age_status': 'VERIFIED U18'}
        result = merge_records([refreshed, previous])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Jordan Lee')
        self.assertEqual(result[0]['dob'], '2010-05-04')

    def test_review_conflicts_dominate_in_both_input_orders(self):
        verified = reviewed(dob='2008-10-15')
        conflict = deepcopy(verified)
        conflict['age_evidence'].pop('dob')
        conflict['age_evidence'].update({'status': 'conflicting_dob', 'candidate_dobs': [
            {'dob': '2008-10-15', 'source_urls': ['https://www.itftennis.com/one.pdf']},
            {'dob': '2008-10-16', 'source_urls': ['https://www.itftennis.com/two.pdf']}]})
        differing = reviewed(dob='2009-10-15')
        for other in (conflict, differing):
            for rows in ([verified, other], [other, verified]):
                result = merge_records(rows)[0]
                self.assertEqual(result['age_evidence']['status'], 'conflicting_dob')
                self.assertIsNone(result['dob'])
                self.assertNotIn('dob', result['age_evidence'])
                self.assertEqual(age_status_on(result, '2026-10-15'), 'TARGETED REVIEW')
                self.assertEqual(len(result['age_evidence']['candidate_dobs']), 2)
                self.assertTrue(result['age_evidence']['sources'])

    def test_distinct_official_ids_never_merge_on_name_alone(self):
        one, two = reviewed(), reviewed(player_id='itf:800000002')
        self.assertEqual(len(merge_records([one, two])), 2)

    def test_alias_index_preserves_ambiguous_ids_in_both_orders(self):
        adult = reviewed('Adult Player', '2000-01-01', 'itf:800111111')
        young = reviewed('Young Player', '2010-01-01', 'itf:800222222')
        adult['aliases'] = young['aliases'] = ['A. Player']
        for rows in ([adult, young], [young, adult]):
            result = index_records(rows)['a player']
            self.assertEqual(age_status_on(result, '2026-10-14'), 'TARGETED REVIEW')
            self.assertEqual(result['identity_candidates'], ['itf:800111111', 'itf:800222222'])

    def test_leap_day_invalid_date_and_prebirth_are_conservative(self):
        row = reviewed(dob='2008-02-29')
        self.assertIsNone(age_on(row, '2026-02-28'))
        self.assertEqual(age_status_on(row, '2026-02-28'), 'TARGETED REVIEW')
        self.assertEqual(age_on(row, '2026-03-01'), 18)
        for day in ('2026-02-30', 'not-a-date', None, '2000-01-01'):
            self.assertIsNone(age_on(row, day))
            self.assertEqual(age_status_on(row, day), 'TARGETED REVIEW')


class ReviewedFeedTests(unittest.TestCase):
    def build(self, record, event_date, cache=None):
        return build_review({'tournaments': [{'id': 't1', 'tour_id': 'itf-men', 'tour': 'ITF',
              'tournament': 'Test', 'start_date': event_date, 'end_date': event_date,
              'participant_field_type': 'ACTIVE_DRAW', 'participants': [{'name': 'J. lee'}]}]},
              {'records': [record]},
              {'sports': [{'sport': 'Tennis', 'groups': [{'events': [{'source_id': 'itf'}]}]}]},
              {'tour_approval_map': {'itf-men': 'itf'}, 'active_field_types': ['ACTIVE_DRAW']}, cache)

    def test_event_birthday_controls_alert_even_if_stored_age_is_stale(self):
        row = reviewed(dob='2008-10-14')
        self.assertEqual(self.build(row, '2026-10-13')['alerts'][0]['severity'], 'RED')
        self.assertEqual(self.build(row, '2026-10-14')['alerts'], [])

    def test_uncertain_record_stays_amber(self):
        row = reviewed()
        row['age_evidence'] = {'status': 'age_only', 'checked_at': '2026-10-14', 'review': {'id': 'test'}}
        row['dob'] = None
        self.assertEqual(self.build(row, '2026-10-14')['alerts'][0]['severity'], 'AMBER')

    def test_reviewed_adult_cache_overrides_stale_registry_across_alias(self):
        stale = {'name': 'J. lee', 'age': 17, 'age_status': 'VERIFIED U18',
                 'official_player_id': 'itf:800699673'}
        cache = {'records': {'jordan lee': reviewed(dob='2008-10-14')}}
        self.assertEqual(self.build(stale, '2026-10-14', cache)['alerts'], [])


class ParserRegressionTests(unittest.TestCase):
    def test_explicit_dob_precedes_displayed_age(self):
        for filename in ('refresh_tennis_intelligence.py', 'refresh_tennis_age_scan.py'):
            path = ROOT / 'scripts' / filename
            tree = ast.parse(path.read_text())
            wanted = {'age_from_dob', 'date_value', 'parse_age_evidence', 'extract_age_from_json'}
            functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
            namespace = {'datetime': datetime, 're': re}
            exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
            result = namespace['parse_age_evidence']('Age: 17 Date of Birth: 2007-08-01', datetime.date(2026, 10, 14))
            self.assertEqual(result[:2], (19, '2007-08-01'), filename)
            if 'extract_age_from_json' in namespace:
                result = namespace['extract_age_from_json']({'age': 17, 'dateOfBirth': '2007-08-01'}, datetime.date(2026, 10, 14))
                self.assertEqual(result[:2], (19, '2007-08-01'))


if __name__ == '__main__':
    unittest.main()
