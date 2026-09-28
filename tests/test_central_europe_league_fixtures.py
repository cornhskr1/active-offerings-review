import unittest

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

    def test_second_division_holds_reserve_team_and_checks_catalog_scope(self):
        fixtures, held, total = parse_fixtures(second_page(), SECOND)
        self.assertEqual((len(fixtures), held, total), (7, 1, 8))
        self.assertTrue(all("Home B" not in event["name"] for event in fixtures))
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_fixtures(second_page(), {**SECOND, "catalog_terms": ["Czech First League | Men"]})


if __name__ == "__main__":
    unittest.main()
