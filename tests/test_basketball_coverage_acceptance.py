import copy
import json
import unittest
from pathlib import Path
from scripts.audit_basketball_coverage import build, render_markdown

ROOT = Path(__file__).resolve().parents[1]

class BasketballAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {'identities': [{'sport': 'Basketball', 'identity_key': 'bb', 'league': 'League',
            'approval_parent': 'League', 'kind': 'catalog', 'coverage_state': 'ADAPTER_CONFIGURED',
            'season_state': 'DATED_WINDOW', 'sources': [{'id': 'source'}]}]}
        self.config = {'sources': [{'id': 'source', 'source_type': 'exact-fixture', 'coverage_status': 'partial'}]}
        self.publication = {'sources': [{'id': 'source', 'source_type': 'exact-fixture', 'ok': True, 'events': 2}]}

    def state(self):
        return build(self.inventory, self.config, self.publication)['identities'][0]

    def test_all_89_current_identities_accounted_for_once(self):
        read = lambda name: json.loads((ROOT / 'data' / name).read_text())
        inv = read('priority2-coverage-inventory.json')
        report = build(inv, read('global-schedule-sources.json'), read('global-schedule.json'))
        expected = {r['identity_key'] for r in inv['identities'] if r['sport'] == 'Basketball'}
        self.assertEqual(89, len(expected))
        self.assertEqual(expected, {r['identity_key'] for r in report['identities']})
        self.assertEqual(89, sum(report['summary']['operational_states'].values()))

    def test_partial_published_fixture_is_not_full_coverage(self):
        row = self.state()
        self.assertEqual('FIXTURES_PUBLISHED', row['operational_state'])
        self.assertEqual('partial', row['sources'][0]['coverage_status'])
        self.assertIn('do not establish full-season', row['next_action'])

    def test_new_adapter_requires_matching_normal_publication(self):
        self.publication['sources'][0]['source_type'] = 'old-adapter'
        self.assertEqual('NORMAL_PUBLICATION_PENDING', self.state()['operational_state'])
        self.assertIsNone(self.state()['sources'][0]['refresh_ok'])

    def test_changed_endpoint_cannot_inherit_previous_success(self):
        self.config['sources'][0]['endpoint'] = 'https://example.org/new-season'
        self.publication['sources'][0]['endpoint'] = 'https://example.org/old-season'
        self.assertEqual('NORMAL_PUBLICATION_PENDING', self.state()['operational_state'])

    def test_failures_calendar_only_empty_and_scope_hold_remain_distinct(self):
        self.publication['sources'][0].update(ok=False, errors=['403'])
        self.assertEqual('SOURCE_BLOCKED_OR_FAILED', self.state()['operational_state'])
        self.publication['sources'][0].update(ok=True, events=0)
        self.assertEqual('NO_CURRENT_FIXTURES', self.state()['operational_state'])
        self.inventory['identities'][0]['coverage_state'] = 'OFFICIAL_WINDOW_ONLY'
        self.assertEqual('CALENDAR_ONLY', self.state()['operational_state'])
        self.inventory['identities'][0]['season_state'] = 'DOCUMENTED_HOLD'
        self.assertEqual('SCOPE_HOLD', self.state()['operational_state'])

    def test_duplicate_identity_fails(self):
        self.inventory['identities'].append(copy.deepcopy(self.inventory['identities'][0]))
        with self.assertRaises(ValueError): self.state()

    def test_readable_report_exposes_access_hold_with_retained_observations(self):
        self.publication['sources'][0].update(ok=False, events=43,
            errors=['Permission required: collection paused; saved observations are not fresh.'])
        report = build(self.inventory, self.config, self.publication)
        text = render_markdown(report)
        self.assertIn('source: Permission required: collection paused; saved observations are not fresh.', text)
        self.assertIn(report['identities'][0]['next_action'], text)
        self.assertNotIn('| League | Source blocked or failed | partial |', text)
        self.assertNotIn('43', text)

    def test_readable_report_keeps_all_failed_sources_and_escapes_errors(self):
        self.config['sources'].append({'id': 'other', 'source_type': 'exact-fixture'})
        self.inventory['identities'][0]['sources'].append({'id': 'other'})
        self.publication['sources'][0].update(ok=False, errors=['Pairing | identity changed\nCheck scope'])
        self.publication['sources'].append({'id': 'other', 'source_type': 'exact-fixture',
            'ok': False, 'errors': []})
        text = render_markdown(build(self.inventory, self.config, self.publication))
        self.assertIn('source: Pairing \\| identity changed Check scope', text)
        self.assertIn('other: Refresh failed; no error detail reported.', text)

    def test_readable_report_preserves_healthy_scope_and_documented_hold(self):
        self.publication['sources'][0]['errors'] = ['Previous failure']
        text = render_markdown(build(self.inventory, self.config, self.publication))
        self.assertIn('| League | Fixtures published in this window | partial |', text)
        self.assertNotIn('Previous failure', text)
        self.inventory['identities'][0].update(season_state='DOCUMENTED_HOLD', hold_reason='Exact identity unresolved')
        self.publication['sources'][0]['ok'] = False
        text = render_markdown(build(self.inventory, self.config, self.publication))
        self.assertIn('| League | Competition/scope hold | Exact identity unresolved |', text)
