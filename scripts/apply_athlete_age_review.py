#!/usr/bin/env python3
"""Apply an explicitly reviewed evidence file. Never fetch or infer birth dates.

Usage: python scripts/apply_athlete_age_review.py path/to/review_rows.json
The source review is 84 input rows, 82 identities, checked on 2026-10-14.
This operation preserves legacy last_verified values and raw review provenance.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

from athlete_age_evidence import identity, merge_records, name_key, partition_registry

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REVIEW_ID = 'official-age-review-2026-10-14'
CHECKED = '2026-10-14'


def build_review(rows, original_records):
    grouped = {}
    for row in rows:
        assert row['evidence_checked_date'] == CHECKED
        grouped.setdefault(row['canonical_person'], []).append(row)
    result = {}
    for canonical, group in grouped.items():
        row = next((x for x in group if x['name'] == canonical), group[0])
        status = {'Official full DOB verified': 'verified_dob',
                  'Official DOB conflict': 'conflicting_dob',
                  'Official age only': 'age_only'}[row['dob_evidence_status']]
        primary = {'url': row['source_url'], 'title': row['source_title'],
                   'publication_date': row['source_publication_date'], 'evidence': row['evidence']}
        sources = [primary]
        for url in filter(None, row.get('supporting_source_urls', '').split('; ')):
            sources.append({'url': url, 'title': 'Supporting official evidence',
                            'publication_date': None, 'evidence': row['notes']})
        evidence = {'status': status, 'checked_at': CHECKED, 'sources': sources,
                    'review': {'id': REVIEW_ID, 'input_names': [x['name'] for x in group],
                               'notes': row['notes'], 'input_records': [{key: item.get(key) for key in
                                   ('name', 'recorded_dob', 'recorded_age', 'recorded_birth_year',
                                    'original_last_verified')} for item in group]}}
        if status == 'verified_dob':
            evidence['dob'] = row['verified_dob']
        elif status == 'conflicting_dob':
            # The review explicitly attributes July 24 to Angers, July 25 to FFF.
            assert canonical == 'Jules Bouffandeau'
            evidence['candidate_dobs'] = [
                {'dob': '2009-07-24', 'source_urls': [row['source_url']]},
                {'dob': '2009-07-25', 'source_urls': row['supporting_source_urls'].split('; ')}]
        elif status == 'age_only':
            evidence['observed_age'] = row['age_as_of_2026_10_14']
            evidence['observed_on'] = CHECKED
        names = {name_key(x['name']) for x in group}
        originals = [x for x in original_records if name_key(x.get('name') or x.get('athlete')) in names]
        player_ids = {identity(x) for x in originals if identity(x).startswith('itf:')}
        urls = [x.get('source_url') or x.get('profile_url') for x in originals]
        urls += re.findall(r'https://www\.itftennis\.com/en/players/[^\s]+', row['notes'])
        for url in urls:
            key = identity({'source_url': str(url or '').rstrip('.')})
            if key.startswith('itf:'):
                player_ids.add(key)
        assert len(player_ids) <= 1, (canonical, player_ids)
        item = {'name': canonical, 'canonical_name': canonical, 'sport': row['sport'],
                'age_evidence': evidence, 'dob': row['verified_dob'] if status == 'verified_dob' else None,
                'age': row['age_as_of_2026_10_14'] if status == 'verified_dob' else None,
                'age_as_of': CHECKED if status == 'verified_dob' else None,
                'birth_year': int(row['verified_dob'][:4]) if status == 'verified_dob' else None,
                'age_status': ('VERIFIED U18' if row['age_as_of_2026_10_14'] < 18 else 'VERIFIED 18+')
                              if status == 'verified_dob' else 'TARGETED REVIEW',
                'evidence': row['evidence']}
        aliases = [x['name'] for x in group if x['name'] != canonical]
        if aliases:
            item['aliases'] = aliases
        if player_ids:
            item['official_player_id'] = next(iter(player_ids))
        profile = next((str(url).rstrip('.') for url in urls if identity({'source_url': url}).startswith('itf:')), None)
        if profile:
            item['profile_url'] = profile
        result[canonical] = item
    return result


def apply_record(record, reviews):
    original_name = record.get('name') or record.get('athlete')
    review = next((item for item in reviews.values() if name_key(original_name) in
                   {name_key(x) for x in [item['name'], *(item.get('aliases') or [])]}), None)
    if review is None:
        return deepcopy(record)
    out = deepcopy(record)
    for field, value in review.items():
        if field not in ('name', 'sport', 'aliases'):
            out[field] = deepcopy(value)
    out['athlete' if 'athlete' in out else 'name'] = review['name']
    aliases = set(record.get('aliases') or []) | set(review.get('aliases') or [])
    if original_name != review['name']:
        aliases.add(original_name)
    if aliases:
        out['aliases'] = sorted(aliases, key=str.lower)
    if 'status' in out:
        out['status'] = out['age_status']
    if 'age_label' in out:
        out['age_label'] = str(out['age']) if out['age'] is not None else 'DOB review needed'
    # Preserve the identity profile; DOB evidence URLs live in age_evidence.sources.
    if not out.get('source_url'):
        out['source_url'] = review.get('profile_url') or review['age_evidence']['sources'][0]['url']
    return out


def main(path):
    rows = [{key: value for key, value in row.items() if key != 'reference_identity_digest'}
            for row in json.loads(Path(path).read_text())]
    docs = {name: json.loads((DATA / (name + '.json')).read_text()) for name in
            ('known-u18', 'tennis-known-u18', 'tennis-u18-registry', 'tennis-age-cache')}
    registry = docs['tennis-u18-registry']
    originals = [*docs['known-u18']['records'], *docs['tennis-known-u18']['records'],
                 *(registry.get('records') or registry['verified_u18']),
                 *docs['tennis-age-cache']['records'].values()]
    reviews = build_review(rows, originals)
    for name in ('known-u18', 'tennis-known-u18'):
        docs[name]['records'] = [apply_record(x, reviews) for x in docs[name]['records']]
        docs[name]['age_evidence_review'] = {'id': REVIEW_ID, 'checked_at': CHECKED}
    durable = [apply_record(x, reviews) for x in (registry.get('records') or registry['verified_u18'])]
    durable, current, targeted = partition_registry(durable, CHECKED)
    registry.update({'schema_version': 2, 'records': durable, 'verified_u18': current,
                     'junior_targeted_candidates': targeted,
                     'age_evidence_review': {'id': REVIEW_ID, 'checked_at': CHECKED}})
    registry['summary'].update({'unique_verified_u18': len(current), 'durable_athletes': len(durable),
                                'historical_adults': sum(x['age_status'] == 'VERIFIED 18+' for x in durable),
                                'targeted_identity_reviews': len(targeted)})
    cache = {key: apply_record(value, reviews) for key, value in docs['tennis-age-cache']['records'].items()}
    # Add missing reviewed tennis identities; do not fabricate a last_verified date.
    for record in durable:
        if record.get('age_evidence') and name_key(record['name']) not in cache:
            cache[name_key(record['name'])] = deepcopy(record)
    # Collapse duplicate IDs to a single canonical entry, retaining matching aliases.
    unreviewed = {key: value for key, value in cache.items() if not value.get('age_evidence')}
    reviewed_cache = merge_records([value for value in cache.values() if value.get('age_evidence')])
    docs['tennis-age-cache']['records'] = {**unreviewed, **{name_key(x['name']): x for x in reviewed_cache}}
    docs['tennis-age-cache']['age_evidence_review'] = {'id': REVIEW_ID, 'checked_at': CHECKED}
    for name, doc in docs.items():
        (DATA / (name + '.json')).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    artifact = {'schema_version': 1, 'id': REVIEW_ID, 'checked_at': CHECKED,
                'input_rows': len(rows), 'unique_athletes': len(reviews), 'input_records': rows,
                'records': list(reviews.values())}
    (DATA / 'athlete-age-evidence-review.json').write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed_input_rows': len(rows), 'reviewed_unique_athletes': len(reviews),
                      'tennis_durable': len(durable), 'tennis_current_view': len(current),
                      'tennis_targeted': len(targeted), 'cache_records': len(docs['tennis-age-cache']['records'])}))


if __name__ == '__main__':
    main(sys.argv[1])
