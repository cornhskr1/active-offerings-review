"""Lithuanian league scope, rescheduled partial round, and match detail checks."""

import datetime
import unittest

from scripts.lfflt_alyga_fixture_adapter import next_round, verified_match


SOURCE = {"id":"uefa-soccer-lithuania-a-lyga-men", "sport":"Soccer",
          "league":"A Lyga | Men", "region":"Lithuania", "catalog_terms":["A Lyga | Men"]}


def page():
    panels = []
    for number in range(36, 0, -1):
        rows = []
        for i in range(4):
            match_id = number * 100 + i
            upcoming = number >= 33 or (number == 22 and i == 0)
            date = "2026 10 10" if number == 22 and i == 0 else (
                "2026 10 19" if number == 33 else ("2026 11 07" if number > 33 else "2026 05 09"))
            status = "2" if upcoming else "1"
            prefix = "artimiausios" if upcoming else "ivykusios"
            score = "-" if upcoming else "1"
            rows.append(f'''<tr data-status="{status}" data-matchdate="{date}"
                data-hometeam="Home {number}-{i}" data-awayteam="Away {number}-{i}">
                <td>{date}</td><td>18:45</td><td>Stadionas</td>
                <td><a href="/komanda/home-{i}-23198513">Home {number}-{i}</a></td>
                <td><div class="result-home">{score}</div><div class="result-away">{score}</div></td>
                <td><a href="/komanda/away-{i}-23198513">Away {number}-{i}</a></td>
                <td><a href="/{prefix}-varzybos/fixture-{match_id}">Details</a></td></tr>''')
        panels.append(f'<div class="matches-tour-table"><h1>{number}. TURAS</h1><table class="matches-table">'
                      + ''.join(rows) + '</table></div>')
    return ('<div class="mlh-league-name">A lyga, kurią remia TOPsport 2026</div>'
            '<div class="mlh-season">Sezonas 2026</div>' + ''.join(panels))


def detail():
    return '''<span class="top_info_league">TOPLYGA 2026</span>
        <span class="top_info_league_extrainfo">33 turas</span>
        <div class="main_info_desktop"><div class="home_team"><div class="team_name">Home 33-0</div></div>
        <div class="result"><span class="top_info_right_time">Pirmadienį 10 - 19 18:45</span>
        <div class="top_info_right_facility">Stadionas</div>
        <div class="cm-btn add-calendar" data-match-id="3300"></div></div>
        <div class="away_team"><div class="team_name">Away 33-0</div></div></div>'''


class LithuanianFixtureTests(unittest.TestCase):
    def test_next_complete_round_skips_postponed_match_and_verifies_detail(self):
        rows, count, held = next_round(page(), SOURCE, datetime.date(2026, 9, 28))
        self.assertEqual((len(rows), count, held), (4, 144, 13))
        self.assertEqual({row[1] for row in rows}, {33})
        card = verified_match(detail(), rows[0], SOURCE)
        self.assertEqual(card["start_time"], "2026-10-19T15:45:00Z")
        self.assertEqual(card["name"], "Away 33-0 at Home 33-0")

    def test_scope_and_linked_detail_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "competition"):
            next_round(page().replace("A lyga, kurią remia TOPsport 2026", "I lyga 2026"), SOURCE,
                       datetime.date(2026, 9, 28))
        with self.assertRaisesRegex(ValueError, "scope"):
            next_round(page().replace("-23198513", "-other-league", 1), SOURCE,
                       datetime.date(2026, 9, 28))
        rows, _, _ = next_round(page(), SOURCE, datetime.date(2026, 9, 28))
        with self.assertRaisesRegex(ValueError, "competition"):
            verified_match(detail().replace("TOPLYGA 2026", "Youth league"), rows[0], SOURCE)


if __name__ == "__main__":
    unittest.main()
