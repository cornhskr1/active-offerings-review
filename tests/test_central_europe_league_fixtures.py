import unittest
from pathlib import Path

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
