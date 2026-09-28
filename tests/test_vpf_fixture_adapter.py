import unittest

from scripts.vpf_fixture_adapter import parse_vleague


SOURCE = {"id": "soccer-afc-vietnam-vleague-1-men", "sport": "Soccer",
          "league": "V.League 1 | Men", "region": "Vietnam",
          "catalog_terms": ["V.League 1 | Men"]}


def season_page():
    teams = list(range(14))
    rounds = []
    for _ in range(13):
        rounds.append([(teams[i], teams[13-i]) for i in range(7)])
        teams = [teams[0], teams[-1], *teams[1:-1]]
    rounds += [[(away, home) for home, away in pairs] for pairs in rounds]
    blocks = []
    for number, pairs in enumerate(rounds, 1):
        date = "10 Tháng 10, 2026" if number <= 13 else "Tháng 02, 2027"
        matches = []
        for home, away in pairs:
            matches.append(f'<div class="jstable-row"><div class="jsMatchDivTime">18:00</div>'
                           f'<div class="jsMatchDivHome"><div class="js_div_particName">'
                           f'<a href="https://vpf.vn/team/team-{home}/?sid=154439">Team {home}</a></div></div>'
                           f'<div class="jsMatchDivScore"><a href="https://vpf.vn/match/game-{number}-{home}-{away}/">v</a></div>'
                           f'<div class="jsMatchDivAway"><div class="js_div_particName">'
                           f'<a href="https://vpf.vn/team/team-{away}/?sid=154439">Team {away}</a></div></div></div>')
        blocks.append(f'<div class="jsrow-matchday-name" id="round_{number}">'
                      f'Vòng {number} LPBank V.League 1-2026/27</div>'
                      f'<div class="js-matchday-wrapper"><div class="js-matchday-title">'
                      f'<p class="js-matchday-date">{date}</p></div>'
                      f'<div class="js-matchday-matches">{"".join(matches)}</div></div>')
    return '<h1>Vô địch Quốc gia LPBank 2026/27</h1><article>' + ''.join(blocks) + '</article>'


class VpfFixtureTests(unittest.TestCase):
    def test_exact_dates_only_and_vietnam_timezone(self):
        events, held, rows = parse_vleague(season_page(), SOURCE)
        self.assertEqual((len(events), held, rows), (91, 91, 182))
        self.assertEqual("2026-10-10T11:00:00Z", events[0]["start_time"])
        self.assertEqual("V.League 1 | Men", events[0]["league"])

    def test_cross_edition_or_incomplete_page_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "club edition"):
            parse_vleague(season_page().replace("sid=154439", "sid=other", 1), SOURCE)
        with self.assertRaisesRegex(ValueError, "182-match"):
            parse_vleague(season_page().replace('class="jstable-row"', 'class="missing-row"', 1), SOURCE)


if __name__ == "__main__":
    unittest.main()
