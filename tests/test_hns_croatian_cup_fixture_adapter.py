import copy
import datetime
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from lxml import html

from scripts.hns_croatian_cup_fixture_adapter import (
    ENDPOINT, SOURCE_ID, fetch_fixtures, parse_fixtures, source_config,
)


FIXTURE = Path(__file__).parent / 'fixtures/hns-croatian-cup-20261018.html'
PAGE = FIXTURE.read_bytes()
NOW = datetime.datetime(2026, 10, 18, 16, tzinfo=datetime.timezone.utc)


def rows(doc):
    return doc.xpath('//div[@class="block current_results"]//li[@data-match]')


def unplayed(doc):
    return [row for row in rows(doc) if row.xpath('string(.//div[@class="res1"])') == '-']


def changed(mutate):
    doc = html.fromstring(PAGE.decode('utf-8'))
    mutate(doc)
    return html.tostring(doc, encoding='utf-8')


def set_club(row, name, side='club1'):
    link = row.xpath(f'.//div[@class="{side}"]/a')[0]
    link.text = name
    link.xpath('.//img')[0].set('alt', name)


def response(page=PAGE, url=ENDPOINT, error=None):
    def status():
        if error:
            raise error
    return SimpleNamespace(content=page, url=url, raise_for_status=status)


class HnsCroatianCupTests(unittest.TestCase):
    def test_exact_publisher_pairings_and_counts(self):
        events, proof = parse_fixtures(PAGE, source_config())
        self.assertEqual(proof['published_fixtures'], 40)
        self.assertEqual(proof['completed_fixtures_excluded'], 33)
        self.assertEqual(proof['preliminary_fixtures_excluded'], 16)
        self.assertEqual(proof['published_unplayed_fixtures'], 7)
        self.assertEqual(proof['published_phase_pairings'], {'1/8 finala': 7})
        self.assertEqual(len({e['id'] for e in events}), 7)
        self.assertEqual({(e['start_time'], e['name']) for e in events}, {
            ('2026-10-20', 'HNK Rijeka at NK Karlovac 1919'),
            ('2026-10-28', 'NK Lokomotiva (Z) at NK Varaždin'),
            ('2026-11-03', 'NK Slaven Belupo at NK Mladost Ždralovi'),
            ('2026-11-03', 'NK Neretva at NK Istra 1961'),
            ('2026-11-14', 'HNK Gorica s.d.d. at NK BSK Bijelo Brdo'),
            ('2026-11-14', 'HNK Segesta at NK Rudeš'),
            ('2026-12-02', 'HNK Hajduk at NK Slavonija Požega'),
        })
        self.assertTrue(all(e['source_id'] == SOURCE_ID and e['season_stage'] == 'ROUND OF 16' for e in events))

    def test_minimized_capture_and_source_provenance(self):
        proof = json.loads(FIXTURE.with_suffix('.source.json').read_text())
        self.assertEqual(proof['http_status'], 200)
        self.assertEqual(proof['source_url'], ENDPOINT)
        self.assertEqual(proof['sha256'], hashlib.sha256(PAGE).hexdigest())
        self.assertEqual(proof['retained_bytes'], len(PAGE))
        self.assertLess(len(PAGE), 60000)
        self.assertNotIn(b'/igraci/', PAGE)
        self.assertNotIn(b'<script', PAGE)
        self.assertNotIn(b'/igraci/', PAGE)

    def test_date_only_no_timezone_or_age_clearance(self):
        events, proof = parse_fixtures(PAGE, source_config())
        self.assertEqual(proof['published_clocks_without_verified_timezone'], 7)
        self.assertEqual(proof['coverage_status'], 'partial')
        self.assertFalse(proof['review_window_complete'])
        self.assertEqual(proof['participant_age_coverage'], 'unverified')
        self.assertEqual(proof['professional_status_coverage'], 'not established by schedule')
        self.assertTrue(all(e['date_only'] and len(e['start_time']) == 10 for e in events))
        self.assertTrue(all(e['participant_review_required'] for e in events))
        self.assertEqual(events[0]['published_kickoff_text'], '18:00')
        self.assertIn('timezone unverified', events[0]['status_detail'])

    def test_fetch_returns_all_future_not_only_current_window(self):
        calls = []
        def get(url, **kwargs):
            calls.append((url, kwargs))
            return response()
        events, evidence = fetch_fixtures(source_config(), NOW, get)
        self.assertEqual(calls, [(ENDPOINT, {'timeout': 30})])
        self.assertEqual(len(events), 7)
        self.assertEqual(evidence['future_confirmed_fixtures'], 7)
        self.assertEqual(evidence['past_unresolved_fixtures_held'], 0)
        current = [e for e in events if '2026-10-18' <= e['start_time'] <= '2026-10-25']
        self.assertEqual([e['name'] for e in current], ['HNK Rijeka at NK Karlovac 1919'])
        future = [e for e in events if e['start_time'] > '2026-10-25']
        self.assertEqual(len(future), 6)

    def test_fetch_holds_past_unresolved_using_review_day_not_utc_midnight(self):
        day_after = NOW.replace(day=21)
        events, proof = fetch_fixtures(source_config(), day_after, lambda *a, **k: response())
        self.assertEqual((len(events), proof['past_unresolved_fixtures_held']), (6, 1))
        # Still Oct 20 in America/Chicago: the date-only Oct 20 card stays.
        near_midnight = day_after.replace(hour=1)
        events, _ = fetch_fixtures(source_config(), near_midnight, lambda *a, **k: response())
        self.assertEqual(len(events), 7)
        with self.assertRaisesRegex(ValueError, 'stale publication is not offseason'):
            fetch_fixtures(source_config(), NOW.replace(month=12, day=3), lambda *a, **k: response())

    def test_aware_timestamp_required_before_fetch(self):
        def no_fetch(*a, **k):
            self.fail('Invalid timestamp must not fetch')
        for now in (NOW.replace(tzinfo=None), NOW.date(), None):
            with self.subTest(now=now), self.assertRaisesRegex(ValueError, 'aware'):
                fetch_fixtures(source_config(), now, no_fetch)

    def test_source_identity_is_exact_and_checked_before_fetch(self):
        alternatives = {
            'id': 'uefa-soccer-croatia-croatian-first-league-men', 'sport': 'Football',
            'league': 'Croatian Cup | Women', 'region': 'Slovenia',
            'catalog_terms': ['Croatian Cup | Men', 'Croatian Cup | Women'],
            'endpoint': ENDPOINT.replace('114492931', '114137140'),
            'source_type': 'other', 'coverage_status': 'complete',
        }
        for key, value in alternatives.items():
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'catalog scope'):
                parse_fixtures(PAGE, {**source_config(), key: value})

    def test_competition_edition_authority_changes_fail_closed(self):
        mutations = [
            lambda d: setattr(d.xpath('//title')[0], 'text', 'SuperSport HNL'),
            lambda d: setattr(d.xpath('//h1')[0], 'text', 'HNK U19'),
            lambda d: setattr(d.xpath('//h2')[0], 'text', '2025/2026'),
            lambda d: d.xpath('//select[@id="season"]/option[@selected]')[0].set('value', '2025/2026'),
            lambda d: setattr(d.xpath('//select[@id="season"]/option[@selected]')[0], 'text', '2025/26'),
            lambda d: d.xpath('//select[@id="oid"]/option[@selected]')[0].set('value', '2'),
            lambda d: d.xpath('//select[@id="cid"]/option')[0].set('value', ENDPOINT.replace('114492931', '22')),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_date_required_explicit_valid_and_in_edition(self):
        for value in ('', '20.10.26. 18:00', '31.02.2027. 18:00', '20.10.2025. 18:00',
                      '20.10.2026. 25:00', '20.10.2026. TBD', '20.10.2026. 18:00 CET'):
            def mutate(doc):
                unplayed(doc)[0].xpath('.//div[@class="date"]')[0].text = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_missing_clock_is_allowed_without_inventing_midnight(self):
        def mutate(doc):
            unplayed(doc)[0].xpath('.//div[@class="date"]')[0].text = '20.10.2026.'
        events, proof = parse_fixtures(changed(mutate), source_config())
        self.assertEqual(events[0]['start_time'], '2026-10-20')
        self.assertIsNone(events[0]['published_kickoff_text'])
        self.assertEqual(proof['published_clocks_without_verified_timezone'], 6)

    def test_stable_id_survives_schedule_change(self):
        original, _ = parse_fixtures(PAGE, source_config())
        def mutate(doc):
            unplayed(doc)[0].xpath('.//div[@class="date"]')[0].text = '21.10.2026. 12:30'
        revised, _ = parse_fixtures(changed(mutate), source_config())
        self.assertEqual(original[0]['id'], revised[0]['id'])
        self.assertEqual(revised[0]['start_time'], '2026-10-21')

    def test_malformed_scores_and_unplayed_status_fail(self):
        for value in ('0', '', 'P', 'TBD'):
            def mutate(doc):
                unplayed(doc)[0].xpath('.//div[@class="res1"]')[0].text = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'result status'):
                parse_fixtures(changed(mutate), source_config())
        for attribute, value in (('class', 'row postponed'), ('data-status', 'cancelled')):
            def mutate(doc):
                unplayed(doc)[0].set(attribute, value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())
        def result_flag(doc):
            unplayed(doc)[0].xpath('.//div[@class="result"]')[0].set('class', 'result postponed')
        with self.assertRaises(ValueError):
            parse_fixtures(changed(result_flag), source_config())

    def test_completed_zero_zero_is_not_upcoming(self):
        def mutate(doc):
            r = unplayed(doc)[0]
            for side in ('res1', 'res2'):
                r.xpath(f'.//div[@class="{side}"]')[0].text = '0'
        events, proof = parse_fixtures(changed(mutate), source_config())
        self.assertEqual((len(events), proof['completed_fixtures_excluded']), (6, 34))

    def test_preliminary_unplayed_cannot_be_promoted(self):
        def mutate(doc):
            clone = copy.deepcopy(unplayed(doc)[0])
            clone.set('data-round', '10002')
            clone.set('data-match', '999')
            rows(doc)[0].addprevious(clone)
        events, proof = parse_fixtures(changed(mutate), source_config())
        self.assertEqual(len(events), 7)
        self.assertEqual(proof['preliminary_fixtures_excluded'], 17)
        self.assertEqual(proof['published_unplayed_fixtures'], 8)

    def test_placeholder_youth_reserve_and_amateur_are_visible_holds(self):
        cases = [('TBD', 'unresolved_pairings_held'), ('Pobjednik A/B', 'unresolved_pairings_held'),
                 ('NK Club U19', 'age_or_reserve_fixtures_held'), ('NK Club II', 'age_or_reserve_fixtures_held'),
                 ('NK Club B', 'age_or_reserve_fixtures_held'), ('Juniori', 'age_or_reserve_fixtures_held'),
                 ('Amater Club', 'amateur_scope_held')]
        for name, field in cases:
            with self.subTest(name=name):
                events, proof = parse_fixtures(changed(lambda d: set_club(unplayed(d)[0], name)), source_config())
                self.assertEqual((len(events), proof[field]), (6, 1))

    def test_opponent_missing_or_identity_disagreement_fails(self):
        mutations = [
            lambda d: set_club(unplayed(d)[0], ''),
            lambda d: unplayed(d)[0].xpath('.//div[@class="club1"]')[0].set('data-id', '0'),
            lambda d: unplayed(d)[0].xpath('.//div[@class="club1"]/a')[0].set('href', '/klubovi/555/other/'),
            lambda d: unplayed(d)[0].xpath('.//div[@class="club1"]//img')[0].set('alt', 'Other'),
            lambda d: set_club(unplayed(d)[0], 'HNK Rijeka'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_duplicate_identity_pairing_or_changed_round_fails(self):
        def duplicate(doc, new_id=False):
            row = unplayed(doc)[0]
            clone = copy.deepcopy(row)
            if new_id:
                clone.set('data-match', '999')
            row.addnext(clone)
        for mutate in (duplicate, lambda d: duplicate(d, True),
                       lambda d: unplayed(d)[0].set('data-round', '10003'),
                       lambda d: unplayed(d)[0].set('data-round', '10099')):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_nested_row_cannot_be_silently_dropped(self):
        def mutate(doc):
            row = unplayed(doc)[0]
            wrapper = html.Element('div')
            row.addnext(wrapper)
            wrapper.append(row)
        with self.assertRaisesRegex(ValueError, 'layout'):
            parse_fixtures(changed(mutate), source_config())

    def test_foreign_matchlist_is_not_competition_evidence(self):
        def mutate(doc):
            outside = html.Element('div')
            outside.set('class', 'block current_results')
            clone = copy.deepcopy(unplayed(doc)[0]); clone.set('data-match', '999')
            outside.append(clone); doc.xpath('//body')[0].append(outside)
        events, _ = parse_fixtures(changed(mutate), source_config())
        self.assertEqual(len(events), 7)

    def test_no_admissible_future_fixtures_is_not_healthy_empty(self):
        def mutate(doc):
            for row in unplayed(doc):
                set_club(row, 'TBD ' + row.get('data-match'))
        with self.assertRaisesRegex(ValueError, 'no admissible current/future'):
            fetch_fixtures(source_config(), NOW, lambda *a, **k: response(changed(mutate)))

    def test_completed_only_is_failure_not_offseason(self):
        def mutate(doc):
            for row in unplayed(doc):
                row.getparent().remove(row)
        with self.assertRaisesRegex(ValueError, 'absence is not offseason'):
            parse_fixtures(changed(mutate), source_config())

    def test_fetch_fails_on_http_error_redirect_and_login_page(self):
        for resp in (response(error=RuntimeError('HTTP 403')), response(url='https://example.com/'),
                     response(page=b'<html><title>Sign in</title></html>')):
            with self.subTest(resp=resp), self.assertRaises((ValueError, RuntimeError)):
                fetch_fixtures(source_config(), NOW, lambda *a, **k: resp)

    def test_late_invalid_row_fails_atomically(self):
        def mutate(doc):
            unplayed(doc)[-1].xpath('.//div[@class="date"]')[0].text = 'TBD'
        with self.assertRaises(ValueError):
            fetch_fixtures(source_config(), NOW, lambda *a, **k: response(changed(mutate)))


if __name__ == '__main__':
    unittest.main()
