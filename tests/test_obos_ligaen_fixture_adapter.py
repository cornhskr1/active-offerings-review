"""OBOS next-round featured, duplicate and rescheduled fixture handling."""

import datetime
import unittest

from scripts.obos_ligaen_fixture_adapter import next_round


SOURCE = {"id":"uefa-soccer-norway-obos-ligaen-men", "sport":"Soccer",
          "league":"OBOS-ligaen | Men", "region":"Norway", "catalog_terms":["OBOS-ligaen | Men"],
          "official_schedule_url":"https://www.obos-ligaen.no/terminliste"}


def row(i, featured=False, venue="Arena"):
    day = "21" if i == 7 else "03"
    pair = f'Home {i} - <span class="schedule__team--opponent">Away {i}</span>'
    date = f'<span>{day}.10.<span class="schedule__match__item--date__year">2026</span></span>'
    if featured:
        return f'''<tr class="schedule__match schedule__match--upcoming">
          <td class="schedule__match__item--teams">{pair}</td>
          <td class="schedule__match__item--date">{date}<span class="schedule__time">16:00</span><span>#24</span></td>
          <td class="schedule__match__item--venue">{venue}</td>
          <td class="schedule__match__item--league"><img alt="OBOS-ligaen"></td></tr>'''
    return f'''<tr class="future__match__terminlist schedule__match">
        <td class="schedule__match__item--round"><span>#24</span></td>
        <td class="schedule__match__item--teams">{pair}</td>
        <td class="schedule__match__item--date">{date}<span class="schedule__time">16:00</span>
            <span class="schedule__match__item--match-round-number">#24</span><br>{venue}</td>
        <td class="schedule__match__item--league"><img alt="OBOS-ligaen"></td></tr>'''


def page():
    return '<html><title>Terminliste / OBOS-ligaen</title><table>' + row(0, True) + ''.join(row(i) for i in range(8)) + '</table></html>'


class ObosTests(unittest.TestCase):
    def test_featured_duplicate_and_rescheduled_round(self):
        fixtures, count, held = next_round(page(), SOURCE, datetime.date(2026, 9, 28))
        self.assertEqual((len(fixtures), count, held), (8, 8, 0))
        self.assertEqual(len([f for f in fixtures if f["start_time"] < "2026-10-06"]), 7)
        self.assertEqual(fixtures[-1]["start_time"], "2026-10-21T14:00:00Z")

    def test_conflicting_duplicate_and_wrong_league_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "conflicts"):
            next_round(page().replace(row(0, True), row(0, True, "Other stadium")), SOURCE,
                       datetime.date(2026, 9, 28))
        with self.assertRaisesRegex(ValueError, "competition"):
            next_round(page().replace("Terminliste / OBOS-ligaen", "Terminliste / Eliteserien"), SOURCE,
                       datetime.date(2026, 9, 28))


if __name__ == "__main__":
    unittest.main()
