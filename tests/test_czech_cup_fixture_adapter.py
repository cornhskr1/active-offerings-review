import copy
import datetime
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from lxml import html

from scripts.czech_cup_fixture_adapter import parse_fixtures, source_config


FIXTURE = Path(__file__).parent / 'fixtures/czech-cup-20261018.html'
PAGE = FIXTURE.read_bytes()


def upcoming(doc):
    return doc.xpath('//div[@class="content schedule"]/h2[text()="Rozpis zápasů"]/following-sibling::div[@class="item"]')


def changed(mutate):
    doc = html.fromstring(PAGE.decode('utf-8'))
    mutate(doc)
    return html.tostring(doc, encoding='utf-8')


class CzechCupFixtureTests(unittest.TestCase):
    def test_current_publisher_fixture_and_source_proof(self):
        events, evidence = parse_fixtures(PAGE, source_config())
        self.assertEqual((len(events), evidence['published_unplayed_fixtures'],
                          evidence['completed_fixtures_excluded']), (8, 8, 141))
        self.assertEqual(evidence['published_phase_pairings'], {'3.kolo': 1, 'Osmifinále': 7})
        self.assertEqual(evidence['coverage_status'], 'partial')
        self.assertFalse(evidence['review_window_complete'])
        self.assertEqual(evidence['participant_age_coverage'], 'unverified')
        self.assertEqual(evidence['professional_status_coverage'], 'not established by schedule')
        self.assertTrue(all(event['participant_review_required'] for event in events))
        self.assertEqual(len({event['id'] for event in events}), 8)
        expected = {
            ('FC Slovan Liberec', 'FK Teplice', '2026-10-27'),
            ('SK Slavia Praha', 'FC Zbrojovka Brno', '2026-10-27'),
            ('FC Vysočina Jihlava', 'FC Viktoria Plzeň', '2026-10-28'),
            ('1. SK Prostějov', 'FC Hradec Králové', '2026-10-28'),
            ('FK Mladá Boleslav', 'Bohemians Praha 1905', '2026-10-28'),
            ('1.FC Slovácko', 'FK Pardubice', '2026-10-28'),
            ('AC Sparta Praha', 'FC Baník Ostrava', '2026-10-28'),
            ('SK Artis Brno', 'FK Jablonec', '2026-11-11'),
        }
        self.assertEqual({(event['name'].split(' at ')[1], event['name'].split(' at ')[0], event['start_time'])
                          for event in events}, expected)
        proof = json.loads(FIXTURE.with_suffix('.source.json').read_text())
        self.assertEqual(proof['http_status'], 200)
        self.assertEqual(proof['sha256'], hashlib.sha256(PAGE).hexdigest())
        self.assertEqual(proof['source_url'], source_config()['endpoint'])

    def test_date_only_never_invents_utc_or_venue_from_broadcaster(self):
        events, evidence = parse_fixtures(PAGE, source_config())
        self.assertEqual(evidence['published_clocks_without_verified_timezone'], 8)
        self.assertTrue(all(event['date_only'] and len(event['start_time']) == 10 for event in events))
        self.assertTrue(all(event['location'] is None for event in events))
        self.assertTrue(all('T' not in event['start_time'] and 'timezone' in event['status_detail'] for event in events))
        self.assertTrue(all(event['published_kickoff_text'].endswith('hod.') for event in events))
        def modify_clock(doc):
            row = upcoming(doc)[0]
            row.xpath('.//div[@class="time"]/div[@class="long"]')[0].text = 'středa 15:00 hod.'
            row.xpath('.//div[@class="time"]/div[@class="short"]')[0].text = '15:00'
        revised, _ = parse_fixtures(changed(modify_clock), source_config())
        self.assertEqual([(event['id'], event['start_time']) for event in events],
                         [(event['id'], event['start_time']) for event in revised])

    def test_no_fake_current_cards_and_future_window_activation(self):
        events, _ = parse_fixtures(PAGE, source_config())
        def window(start, end):
            return [event for event in events if start <= datetime.date.fromisoformat(event['start_time']) <= end]
        self.assertEqual(window(datetime.date(2026, 10, 18), datetime.date(2026, 10, 25)), [])
        self.assertEqual(len(window(datetime.date(2026, 10, 20), datetime.date(2026, 10, 27))), 2)
        self.assertEqual(len(window(datetime.date(2026, 10, 21), datetime.date(2026, 10, 28))), 7)

    def test_catalog_scope_and_endpoint_must_be_exact(self):
        changes = {'id': 'uefa-soccer-czech-republic-czech-first-league-men', 'sport': 'Football',
                   'league': 'Czech Cup | Women', 'region': 'Slovakia',
                   'catalog_terms': ['Czech Cup | Men', 'Czech First League | Men'],
                   'endpoint': 'https://example.com/vysledky'}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'catalog scope'):
                parse_fixtures(PAGE, {**source_config(), key: value})

    def test_selected_edition_and_unfiltered_phase_and_team(self):
        mutations = [
            lambda doc: doc.xpath('//select[@id="id_season"]/option[@selected]')[0].set('value', '33'),
            lambda doc: setattr(doc.xpath('//select[@id="id_season"]/option[@selected]')[0], 'text', '2025/2026'),
            lambda doc: doc.xpath('//select[@id="id_stage"]/option[@selected]')[0].set('value', '5'),
            lambda doc: doc.xpath('//select[@id="id_team"]/option[2]')[0].set('selected', 'selected'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_missing_opponent_and_contradictory_club_fail_closed(self):
        for xpath, action in (
            ('.//div[@class="name right"]/div/a', lambda node: setattr(node, 'text', '')),
            ('.//div[@class="logo right"]/a/img', lambda node: node.set('alt', 'Different Club')),
            ('.//div[@class="name right"]/div/a', lambda node: node.set('href', '/wrong/12')),
        ):
            with self.subTest(xpath=xpath), self.assertRaisesRegex(ValueError, 'opponent'):
                parse_fixtures(changed(lambda doc: action(upcoming(doc)[0].xpath(xpath)[0])), source_config())

    def test_placeholder_age_reserve_and_amateur_are_visible_holds(self):
        for label, field in (('Neznámý soupeř', 'unresolved_pairings_held'),
                             ('TBD', 'unresolved_pairings_held'), ('Club U17', 'age_or_reserve_fixtures_held'),
                             ('Club B', 'age_or_reserve_fixtures_held'), ('Amateur Club', 'amateur_scope_held')):
            def mutate(doc):
                row = upcoming(doc)[0]
                row.xpath('.//div[@class="name right"]/div/a')[0].text = label
                row.xpath('.//div[@class="logo right"]/a/img')[0].set('alt', label)
            with self.subTest(label=label):
                events, evidence = parse_fixtures(changed(mutate), source_config())
                self.assertEqual((len(events), evidence[field], evidence['published_unplayed_fixtures']), (7, 1, 8))

    def test_missing_date_invalid_date_and_out_of_edition_year_fail(self):
        def remove_date(doc):
            node = upcoming(doc)[0].xpath('.//div[@class="date"]')[0]
            node.getparent().remove(node)
        def set_date(doc, long, short):
            row = upcoming(doc)[0]
            node = row.xpath('.//div[@class="date"]/div[@class="long"]')[0]
            node.clear(); node.text = long; node.set('class', 'long')
            row.xpath('.//div[@class="date"]/div[@class="short"]')[0].text = short
        for mutate in (remove_date, lambda doc: set_date(doc, '28/10/2025', '28.10.25'),
                       lambda doc: set_date(doc, '31/02/2027', '31.02.27'),
                       lambda doc: set_date(doc, '28/10/26', '28.10.26'),
                       lambda doc: set_date(doc, '28/10/2026', '29.10.26')):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_no_timezone_assumption_and_invalid_weekday_or_clock_fail(self):
        for clock in ('středa 14:00 CET', 'středa 14:00 UTC', 'středa 14:00 +01:00',
                      'čtvrtek 14:00 hod.', 'středa 25:00 hod.'):
            def mutate(doc):
                row = upcoming(doc)[0]
                row.xpath('.//div[@class="time"]/div[@class="long"]')[0].text = clock
                if '25:00' in clock:
                    row.xpath('.//div[@class="time"]/div[@class="short"]')[0].text = '25:00'
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_missing_clock_still_preserves_explicit_date(self):
        def mutate(doc):
            node = upcoming(doc)[0].xpath('.//div[@class="time"]')[0]
            node.getparent().remove(node)
        events, evidence = parse_fixtures(changed(mutate), source_config())
        self.assertEqual(len(events), 8)
        self.assertEqual(evidence['published_clocks_without_verified_timezone'], 7)
        self.assertTrue(any(event['published_kickoff_text'] is None for event in events))

    def test_missing_phase_unknown_phase_and_duplicate_fail(self):
        def remove_phase(doc):
            node = upcoming(doc)[0].xpath('.//div[@class="stage"]')[0]
            node.getparent().remove(node)
        def unknown_phase(doc):
            upcoming(doc)[0].xpath('.//div[@class="stage"]')[0].text = 'Women U19'
        def duplicate(doc):
            row = upcoming(doc)[0]
            row.addnext(copy.deepcopy(row))
        for mutate in (remove_phase, unknown_phase, duplicate):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parse_fixtures(changed(mutate), source_config())

    def test_layout_change_cannot_silently_drop_a_fixture(self):
        def mutate(doc):
            row = upcoming(doc)[0]
            wrapper = html.Element('div')
            row.addnext(wrapper); wrapper.append(row)
        with self.assertRaisesRegex(ValueError, 'layout'):
            parse_fixtures(changed(mutate), source_config())

    def test_completed_only_is_not_healthy_offseason(self):
        def mutate(doc):
            for row in upcoming(doc):
                row.getparent().remove(row)
        with self.assertRaisesRegex(ValueError, 'absence is not offseason'):
            parse_fixtures(changed(mutate), source_config())

    def test_upcoming_score_is_not_misread_as_kickoff(self):
        def mutate(doc):
            info = upcoming(doc)[0].xpath('.//div[@class="info"]')[0]
            node = html.Element('div', {'class': 'score'}); node.text = '2:1'; info.append(node)
        with self.assertRaisesRegex(ValueError, 'completed result'):
            parse_fixtures(changed(mutate), source_config())

    def test_collector_literal_date_window_and_atomic_failure(self):
        refresh = (Path(__file__).parents[1] / 'scripts/refresh_global_schedule.py').read_text()
        start = refresh.index('    if source.get("source_type") in ("official-zpl-transitional-calendars"')
        end = refresh.index('    if source.get("source_type") in ("official-european-basketball-fixtures", "official-fiba-report-fixtures"):', start)
        collector = 'for source in configured:\n' + refresh[start:end]
        def bad_last_row(doc):
            node = upcoming(doc)[-1].xpath('.//div[@class="date"]')[0]
            node.getparent().remove(node)
        for page, today, window_end, expected_ok, count in (
            (PAGE, datetime.date(2026, 10, 18), datetime.date(2026, 10, 25), True, 0),
            (PAGE, datetime.date(2026, 10, 20), datetime.date(2026, 10, 27), True, 2),
            (PAGE, datetime.date(2026, 10, 21), datetime.date(2026, 10, 28), True, 7),
            (changed(bad_last_row), datetime.date(2026, 10, 21), datetime.date(2026, 10, 28), False, 0),
        ):
            namespace = {
                'configured': [source_config()], 'requests': SimpleNamespace(get=lambda *args, **kwargs:
                    SimpleNamespace(content=page, raise_for_status=lambda: None)),
                'parse_czech_cup_fixtures': parse_fixtures, 'datetime': datetime, 'HEADERS': {},
                'TZ': ZoneInfo('America/Chicago'),
                'NOW_UTC': datetime.datetime.combine(today, datetime.time(12), datetime.timezone.utc),
                'TODAY': today, 'END': window_end, 'events': [], 'seen': set(),
                'source_status': [], 'count': 0, 'errors': [],
            }
            exec(compile(collector, 'czech-cup-collector', 'exec'), namespace)
            with self.subTest(today=today, expected_ok=expected_ok):
                self.assertEqual(len(namespace['events']), count)
                self.assertEqual(namespace['source_status'][0]['ok'], expected_ok)
                self.assertEqual(namespace['source_status'][0]['coverage_status'], 'partial')
                self.assertEqual(namespace['source_status'][0]['events'], count)
                if expected_ok:
                    self.assertEqual(namespace['source_status'][0]['published_unplayed_fixtures'], 8)
                    self.assertFalse(namespace['source_status'][0]['review_window_complete'])

    def test_section_and_encoding_identity_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'page identity'):
            parse_fixtures(PAGE.decode('iso-8859-1'), source_config())
        with self.assertRaisesRegex(ValueError, 'section identity'):
            parse_fixtures(changed(lambda doc: setattr(doc.xpath('//h2[text()="Rozpis zápasů"]')[0], 'text', 'Unknown')), source_config())


if __name__ == '__main__':
    unittest.main()
