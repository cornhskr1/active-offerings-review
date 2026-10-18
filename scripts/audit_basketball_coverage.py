#!/usr/bin/env python3
"""Reconcile every basketball identity without equating linkage with coverage."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(inventory, config, publication):
    configured = {s['id']: s for s in config['sources']}
    published = {s['id']: s for s in publication.get('sources', [])}
    rows = []
    for identity in inventory['identities']:
        if identity['sport'] != 'Basketball':
            continue
        sources = []
        for link in identity.get('sources', []):
            sid = link['id']
            spec, result = configured.get(sid, {}), published.get(sid, {})
            same_adapter = bool(result) and all(spec.get(key) == result.get(key) for key in
                ('source_type', 'endpoint', 'catalog_terms', 'competition_code', 'season_code'))
            sources.append({
                'source_id': sid, 'source_type': spec.get('source_type'),
                'official_schedule_url': spec.get('official_schedule_url'),
                'endpoint': spec.get('endpoint'),
                'coverage_status': spec.get('coverage_status', 'not reported'),
                'scope_note': spec.get('source_note', ''),
                'schedule_scope': spec.get('schedule_scope', 'See source scope note'),
                'coverage_start': spec.get('coverage_start'), 'coverage_end': spec.get('coverage_end'),
                'report_generated_at': result.get('report_generated_at') if same_adapter else None,
                'fixture_coverage_end': result.get('fixture_coverage_end') if same_adapter else None,
                'review_window_complete': result.get('review_window_complete') if same_adapter else None,
                'unresolved_published_rows': result.get('unresolved_published_rows') if same_adapter else None,
                'coverage_note': result.get('coverage_note') if same_adapter else None,
                'normal_publication_matches_adapter': same_adapter,
                'checked_at': result.get('checked_at'),
                'refresh_ok': result.get('ok') if same_adapter else None,
                'events_in_window': result.get('events', 0) if same_adapter else 0,
                'errors': result.get('errors', []) if same_adapter else [],
                'postponed_fixtures_held': result.get('postponed_fixtures_held', 0) if same_adapter else 0,
            })
        linkage = identity['coverage_state']
        failures = [s for s in sources if s['refresh_ok'] is False]
        if identity.get('season_state') == 'DOCUMENTED_HOLD':
            state, action = 'SCOPE_HOLD', 'Resolve the recorded competition/scope hold using official evidence; do not substitute a similarly named competition.'
        elif failures:
            state, action = 'SOURCE_BLOCKED_OR_FAILED', 'Resolve the recorded source failure by provider family, or retain a visible manual check. A failed source is not a missing catalog identity.'
        elif linkage == 'ADAPTER_CONFIGURED':
            if not sources or any(s['refresh_ok'] is not True for s in sources):
                state, action = 'NORMAL_PUBLICATION_PENDING', 'Verify a normal runner publication for the current adapter before claiming working coverage.'
            elif sum(s['events_in_window'] for s in sources):
                state, action = 'FIXTURES_PUBLISHED', 'Verify current offerings and missing phases; published fixtures alone do not establish full-season or participant coverage.'
            else:
                state, action = 'NO_CURRENT_FIXTURES', 'Check official current/next-phase dates; a healthy empty review window is not proof of either complete coverage or a missing connection.'
        elif linkage == 'OFFICIAL_WINDOW_ONLY':
            state, action = 'CALENDAR_ONLY', 'Connect exact fixtures or retain a dated event-specific review process; a season window is not a game schedule.'
        else:
            state, action = 'FIXTURE_CONNECTION_MISSING', 'Discover a supported official fixture source for this exact identity; retain the gap until verified.'
        rows.append({
            'identity_key': identity['identity_key'], 'league': identity['league'],
            'approval_parent': identity['approval_parent'], 'kind': identity['kind'],
            'linkage_state': linkage, 'operational_state': state,
            'season_state': identity['season_state'], 'season_window': identity.get('season_window'),
            'hold_reason': identity.get('hold_reason'), 'sources': sources,
            'next_action': action,
        })
    keys = [row['identity_key'] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate basketball identity in coverage inventory')
    return {
        'schema_version': 1, 'sport': 'Basketball',
        'catalog_menu_version': inventory.get('catalog_menu_version'),
        'schedule_generated_at': publication.get('generated_at'),
        'window_start': publication.get('window_start'), 'window_end': publication.get('window_end'),
        'scope_note': 'Competition and event identities, including separate divisions; not a count of distinct leagues. NCAA Basketball is separate. Linkage, source health and full-phase coverage are different measures. No status grants wagering approval.',
        'summary': {'identities': len(rows), 'linkage_states': dict(sorted(Counter(r['linkage_state'] for r in rows).items())),
                    'operational_states': dict(sorted(Counter(r['operational_state'] for r in rows).items()))},
        'identities': rows,
    }



def render_markdown(report):
    labels = {'FIXTURES_PUBLISHED': 'Fixtures published in this window',
        'NO_CURRENT_FIXTURES': 'Source checked; no current fixtures',
        'NORMAL_PUBLICATION_PENDING': 'New connection; normal verification pending',
        'SOURCE_BLOCKED_OR_FAILED': 'Source blocked or failed', 'CALENDAR_ONLY': 'Calendar only',
        'SCOPE_HOLD': 'Competition/scope hold', 'FIXTURE_CONNECTION_MISSING': 'Fixture connection missing'}
    clean = lambda value: str(value or '').replace('|', r'\|').replace('\n', ' ')
    lines = ['# Basketball operational coverage', '',
        f"Catalog {report['catalog_menu_version']} · published schedule {report['schedule_generated_at']}",
        f"Review dates: {report['window_start']} through {report['window_end']} (Central Time).", '',
        report['scope_note'], '',
        'Configured connections are not a completion percentage. Published fixtures only establish the stated review window and source scope, not all rounds or future seasons.', '',
        '| Current state | Identities |', '|---|---:|']
    lines += [f"| {labels[state]} | {count} |" for state, count in report['summary']['operational_states'].items()]
    lines += ['', '| Competition / event | Current state | Source scope / next action |', '|---|---|---|']
    for row in report['identities']:
        scopes = '; '.join(sorted(set(s['coverage_status'] for s in row['sources'])))
        detail = row.get('hold_reason') or scopes or row['next_action']
        lines.append(f"| {clean(row['league'])} | {labels[row['operational_state']]} | {clean(detail)} |")
    lines += ['', 'Detailed source URLs, checks, errors and next actions: [machine-readable register](data/basketball-coverage-acceptance.json).',
        'Source failures remain unresolved until verified. Calendar windows and documented holds are not completed fixture coverage.', '']
    return '\n'.join(lines)

def main():
    read = lambda name: json.loads((ROOT / 'data' / name).read_text())
    result = build(read('priority2-coverage-inventory.json'), read('global-schedule-sources.json'), read('global-schedule.json'))
    (ROOT / 'data/basketball-coverage-acceptance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'BASKETBALL_COVERAGE_STATUS.md').write_text(render_markdown(result))
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
