"""Apply the reviewed FIFA identity correction after a validated saved overlay.

This is an offline publication correction, not collection or approval expansion.
Snapshot manifests must be built after this transformation.
"""
import json
from pathlib import Path


def apply_fifa_correction(root):
    root = Path(root)
    config = root / 'data/soccer-international-sources.json'
    if not config.exists():
        return
    sid = 'soccer-fifa-womens-club-world-cup'
    source = next((s for s in json.loads(config.read_text())['sources'] if s['id'] == sid), None)
    if not source or source.get('source_type') != 'coverage-gap' or not source.get('retired_mapping'):
        return
    path = root / 'data/global-schedule.json'
    if path.exists():
        data = json.loads(path.read_text())
        data['events'] = [e for e in data.get('events', []) if e.get('source_id') != sid]
        data['event_count'] = len(data['events'])
        data['sources'] = [({**source, 'approved_catalog': True, 'ok': True, 'events': 0,
                            'coverage_complete': False, 'checked_at': None,
                            'note': 'No fixture adapter. Retired Champions Cup observations excluded; no collection performed.'}
                           if s.get('id') == sid else s) for s in data.get('sources', [])]
        for gap in data.get('coverage_gaps', []):
            if gap.get('area') == 'Soccer' and source['league'] not in gap.get('competitions', []):
                gap['competitions'] = sorted(gap.get('competitions', []) + [source['league']])
                gap['note'] = f"{len(gap['competitions'])} approved competitions still lack a dependable automated adapter."
        path.write_text(json.dumps(data, indent=2) + '\n')
    path = root / 'data/competition-identity-registry.json'
    if path.exists():
        data = json.loads(path.read_text())
        for row in data.get('competitions', []):
            if row.get('identity_key') == 'soccer-international-fifa-club-world-cup-women':
                row.update(events=[], participants=[], participant_coverage='NOT AVAILABLE')
        data['event_count'] = sum(len(row.get('events', [])) for row in data.get('competitions', []))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
