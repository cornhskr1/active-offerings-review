import datetime
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.central_europe_league_fixtures import parse_fixtures


FIRST = {"id": "uefa-soccer-czech-republic-czech-first-league-men", "sport": "Soccer",
         "league": "Czech First League | Men", "region": "Czech Republic",
         "endpoint": "https://www.chanceliga.cz/rozpis-zapasu/2027",
         "catalog_terms": ["Czech First League | Men"]}
SECOND = {"id": "uefa-soccer-czech-republic-czech-national-football-league-men",
          "sport": "Soccer", "league": "Czech National Football League | Men",
          "region": "Czech Republic", "endpoint": "https://www.chnliga.cz/zapasy/2026",
          "catalog_terms": ["Czech National Football League | Men"]}


def first_page():
    rows = []
    for n in range(16):
        date = "19/09/26" if n < 8 else "09/10/26"
        score = "2:1" if n < 8 else "pá 18:00"
        css = "number" if n < 8 else "time"
        rows.append(f'<li><span class="info-container"><span class="date"><b>#{9 if n < 8 else 10}</b> {date}</span></span>'
                    f'<span class="game-container"><span class="team"><img alt="Home {n}"></span>'
                    f'<span class="score-container"><span class="score"><b class="{css}">'
                    f'<a href="/zapas/{8300+n}-abc-def">{score}</a></b></span></span>'
                    f'<span class="team"><img alt="Away {n}"></span></span></li>')
    return '<title>Rozpis zápasů | Chance Liga</title><ul class="scoreboard-horizontal">' + ''.join(rows) + '</ul>'


def second_page():
    rows = []
    for n in range(8):
        home = f"Home {n}" if n != 0 else "Home B"
        rows.append(f'<tr><td class="schedule_table__date"><span class="schedule_table__date--full">'
                    f'<span>09.10.2026</span><span>pá 18:00 hod.</span></span></td>'
                    f'<td class="schedule_table__team--home"><span class="schedule_table__team__name">{home}</span></td>'
                    f'<td class="schedule_table__score"><a href="/zapas/{3400+n}-abc-def">-:-</a></td>'
                    f'<td class="schedule_table__team--away"><span class="schedule_table__team__name">Away {n}</span></td></tr>')
    return '<title>Rozpis zápasů | Chance Národní Liga</title><table>' + ''.join(rows) + '</table>'


class CentralEuropeFixtureTests(unittest.TestCase):
    def test_first_division_exact_round_and_time(self):
        fixtures, held, total = parse_fixtures(first_page(), FIRST)
        self.assertEqual((len(fixtures), held, total), (8, 0, 16))
        self.assertEqual(fixtures[0]["start_time"], "2026-10-09T16:00:00Z")
        self.assertEqual(fixtures[0]["name"], "Away 8 at Home 8")
        with self.assertRaisesRegex(ValueError, "match link"):
            parse_fixtures(first_page().replace('/zapas/8315-abc-def', '/not-a-match', 1), FIRST)

    def test_current_widget_includes_two_rounds_and_a_postponed_fixture(self):
        page=(Path(__file__).parent / 'fixtures/czech-current-fixtures-20261006.html').read_text()
        fixtures,held,total=parse_fixtures(page,FIRST)
        self.assertEqual((17,0,17),(len(fixtures),held,total))
        self.assertEqual('2026-10-09T16:00:00Z',fixtures[0]['start_time'])
        self.assertEqual('2026-10-14T16:00:00Z',fixtures[8]['start_time'])
        self.assertIn('round 6',fixtures[8]['status_detail'])

    def test_explicit_postponement_without_a_link_does_not_erase_timed_fixtures(self):
        page = (Path(__file__).parent / 'fixtures/czech-current-fixtures-20261018.html').read_text()
        hold_counts = {}
        fixtures, held, total = parse_fixtures(page, FIRST, hold_counts=hold_counts)
        self.assertEqual((2, 1, 4), (len(fixtures), held, total))
        self.assertEqual({'postponed_fixtures_held': 1}, hold_counts)
        self.assertEqual('FC Viktoria Plzeň at FK Jablonec', fixtures[0]['name'])
        self.assertEqual('2026-10-18T16:00:00Z', fixtures[0]['start_time'])
        self.assertNotIn('Bohemians Praha 1905 at SK Artis Brno', [event['name'] for event in fixtures])
        self.assertEqual(2, len({event['id'] for event in fixtures}))

    def test_postponement_count_does_not_include_untimed_or_reserve_rows(self):
        for page, source in ((first_page().replace('pá 18:00', 'TBC', 1), FIRST),
                             (second_page(), SECOND)):
            hold_counts = {'postponed_fixtures_held': 99}
            _, held, _ = parse_fixtures(page, source, hold_counts=hold_counts)
            self.assertEqual(1, held)
            self.assertEqual({'postponed_fixtures_held': 0}, hold_counts)

    def test_collector_publishes_explicit_postponement_count(self):
        page = (Path(__file__).parent / 'fixtures/czech-current-fixtures-20261018.html').read_text()
        refresh = (Path(__file__).parents[1] / 'scripts/refresh_global_schedule.py').read_text()
        start = refresh.index('    if source.get("source_type")=="official-central-europe-league-fixtures":')
        end = refresh.index('    if source.get("source_type")=="official-georgia-erovnuli-linked-fixtures":', start)
        collector = 'for source in configured:\n' + refresh[start:end]
        source = {**FIRST, 'source_type': 'official-central-europe-league-fixtures'}
        for text, expected_ok, expected_count in ((page, True, 1), (page.replace('odloženo', 'unknown'), False, 0)):
            namespace = {
                'configured': [source], 'requests': SimpleNamespace(get=lambda *args, **kwargs:
                    SimpleNamespace(text=text, raise_for_status=lambda: None)),
                'parse_central_europe_fixtures': parse_fixtures,
                'datetime': datetime, 'HEADERS': {}, 'TZ': datetime.timezone.utc,
                'NOW_UTC': datetime.datetime(2026, 10, 18, 10, tzinfo=datetime.timezone.utc),
                'TODAY': datetime.date(2026, 10, 18), 'END': datetime.date(2026, 10, 25),
                'events': [], 'seen': set(), 'source_status': [], 'count': 0, 'errors': [],
            }
            exec(compile(collector, 'central-europe-collector', 'exec'), namespace)
            status = namespace['source_status'][0]
            self.assertEqual(expected_ok, status['ok'])
            self.assertEqual(expected_count, status['postponed_fixtures_held'])
            self.assertEqual(2 if expected_ok else 0, status['events'])

    def test_unrecognized_or_contradictory_postponement_still_fails_closed(self):
        page = (Path(__file__).parent / 'fixtures/czech-current-fixtures-20261018.html').read_text()
        for changed in (
            page.replace('odloženo', 'unrecognized status'),
            page.replace('odloženo', 'odloženo<b class="time">18:00</b>'),
            page.replace('odloženo', 'odloženo<a href="/zapas/9000-abc-def">details</a>'),
        ):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, 'match link|postponed fixture'):
                    parse_fixtures(changed, FIRST)

    def test_postponement_requires_unique_named_opponents(self):
        from lxml import html

        page = (Path(__file__).parent / 'fixtures/czech-current-fixtures-20261018.html').read_text()
        for mutation in ('missing team', 'same team', 'duplicate row', 'unexpected date'):
            doc = html.fromstring(page)
            row = doc.xpath('//li[.//span[@class="info" and text()="odloženo"]]')[0]
            teams = row.xpath('.//img')
            if mutation == 'missing team':
                teams[0].set('alt', '')
            elif mutation == 'same team':
                teams[0].set('alt', teams[1].get('alt'))
            elif mutation == 'duplicate row':
                row.addnext(html.fromstring(html.tostring(row)))
            else:
                row.xpath('.//span[@class="date"]')[0].text = '18/10/26'
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(ValueError, 'postponed fixture'):
                    parse_fixtures(html.tostring(doc), FIRST)

    def test_variable_widget_size_does_not_silently_drop_a_valid_match(self):
        extra='<li>'+first_page().rsplit('<li>',1)[1].split('</li>',1)[0]+'</li>'
        page=first_page().replace('</ul>',extra.replace('8315-abc-def','9000-abc-def')+'</ul>')
        fixtures,held,total=parse_fixtures(page,FIRST)
        self.assertEqual((9,0,17),(len(fixtures),held,total))

    def test_duplicate_or_wrong_catalog_scope_still_fails(self):
        with self.assertRaisesRegex(ValueError,'match identity'):
            parse_fixtures(first_page().replace('8315-abc-def','8314-abc-def'),FIRST)
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            parse_fixtures(first_page(),dict(FIRST,league='Czech National Football League | Men',catalog_terms=['Czech National Football League | Men']))

    def test_untimed_fixture_is_held_without_inventing_a_kickoff(self):
        fixtures,held,total=parse_fixtures(first_page().replace('pá 18:00','TBC',1),FIRST)
        self.assertEqual((7,1,16),(len(fixtures),held,total))

    def test_unidentified_and_reserve_candidates_are_held(self):
        for name in ['TBC','Club B']:
            fixtures,held,total=parse_fixtures(first_page().replace('Home 8',name),FIRST)
            self.assertEqual((7,1,16),(len(fixtures),held,total))

    def test_second_division_holds_reserve_team_and_checks_catalog_scope(self):
        fixtures, held, total = parse_fixtures(second_page(), SECOND)
        self.assertEqual((len(fixtures), held, total), (7, 1, 8))
        self.assertTrue(all("Home B" not in event["name"] for event in fixtures))
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_fixtures(second_page(), {**SECOND, "catalog_terms": ["Czech First League | Men"]})


if __name__ == "__main__":
    unittest.main()
