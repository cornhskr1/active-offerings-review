import unittest
import datetime
from pathlib import Path

from scripts.vpf_fixture_adapter import (parse_vleague, parse_vleague_mobile_round,
                                         parse_vleague_topbar_round)


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

    def test_official_mobile_round_after_calendar_403(self):
        page = (Path(__file__).parent / "fixtures/vpf_mobile_round_three.html").read_text()
        now = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)
        events, rows = parse_vleague_mobile_round(page, SOURCE, now)
        self.assertEqual((6, 7), (len(events), rows))
        self.assertEqual("2026-10-08T12:15:00Z", events[0]["start_time"])
        self.assertEqual("HLHT at TCVT", events[0]["name"])
        for damaged in (page.replace('>ĐNFC</a>', '>ĐNFC</a>'.replace('ĐNFC', ''), 1),
                        page.replace("Vòng 3 LPBank", "Vòng 3 SACOMBANK", 1),
                        page.replace('class="jo-match-in-week"', 'class="missing"', 1)):
            with self.assertRaises(ValueError):
                parse_vleague_mobile_round(damaged, SOURCE, now)

    def test_official_topbar_round_matches_mobile_and_fails_closed(self):
        now = datetime.datetime(2026, 9, 29, tzinfo=datetime.timezone.utc)
        page = (Path(__file__).parent / "fixtures/vpf_topbar_round_three.html").read_text()
        mobile = (Path(__file__).parent / "fixtures/vpf_mobile_round_three.html").read_text()
        events, rows = parse_vleague_topbar_round(page, SOURCE, now)
        mobile_events, _ = parse_vleague_mobile_round(mobile, SOURCE, now)
        self.assertEqual((len(events), rows), (6, 7))
        self.assertEqual({(e["id"], e["start_time"]) for e in events},
                         {(e["id"], e["start_time"]) for e in mobile_events})
        for damaged in (page.replace("LPBank 2026/27", "LPBank 2025/26", 1),
                        page.replace("sid=154439", "sid=other"),
                        page.replace('class="jo-topbar-match"', 'class="missing"', 1),
                        page.replace("08/10 19:15", "08/10 19:00", 1)):
            with self.assertRaises(ValueError):
                parse_vleague_topbar_round(damaged, SOURCE, now)


if __name__ == "__main__":
    unittest.main()
