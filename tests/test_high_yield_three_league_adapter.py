"""Publisher row boundaries, timezone evidence and catalog scope regression checks."""
import json
import unittest
from scripts.high_yield_three_league_adapter import parse_egypt_fixture, parse_saudi_fixture


def source(kind):
    egypt = kind == 'egypt'
    league = 'Egyptian Premier League | Men' if egypt else 'First Division League | Men'
    return dict(id='caf-soccer-egypt-egyptian-premier-league-men' if egypt else 'soccer-afc-saudi-arabia-first-division-league-men',
        sport='Soccer', league=league, region=kind, catalog_terms=[league], endpoint='https://example.test')


def egypt_page(**changes):
    row = dict(id=375909, championshipId=1667, championshipName='الدوري المصري',
        homeTeamName='القناة', awayTeamName='المصري', date='2026-10-11T17:00:00.000Z',
        homeScore=None, awayScore=None, isDelayed=False, week=6)
    row.update(changes)
    return '<script id="ng-state" type="application/json">'+json.dumps({'fixture-response':{'body':[row]}})+'</script>'


def saudi_page(day='2026-10-14', clock='18:30', competition='416', home='Al Jandal', away='Al Okhdood', fixture='33541'):
    return f'''<div><table><tr><td><a href="calendar.php?calendar_date={day}">date</a></td></tr></table>
    <table><tr><td><a href="championship.php?id={competition}">First Division League</a></td></tr></table>
    <table><tr><td id="fixture_td_1_{fixture}">{clock}</td><td>{home}</td><td>-</td><td>{away}</td><td>Stadium</td></tr></table></div>'''


class PublisherScheduleTests(unittest.TestCase):
    def test_egypt_uses_explicit_publisher_utc_instead_of_guessing_12_hour_display(self):
        event = parse_egypt_fixture(egypt_page(), source('egypt'))[0]
        self.assertEqual('2026-10-11T17:00:00Z', event['start_time'])
        self.assertEqual('المصري at القناة', event['name'])

    def test_egypt_date_and_pairing_follow_record_changes(self):
        event = parse_egypt_fixture(egypt_page(date='2026-10-12T18:00:00Z', homeTeamName='Home'), source('egypt'))[0]
        self.assertEqual('2026-10-12T18:00:00Z', event['start_time'])
        self.assertEqual('المصري at Home', event['name'])

    def test_egypt_rejects_timezone_missing_wrong_competition_and_completed_records(self):
        for changes in [dict(date='2026-10-11T17:00:00'), dict(championshipId=999), dict(homeScore=1), dict(isDelayed=True)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_egypt_fixture(egypt_page(**changes), source('egypt'))

    def test_unrelated_page_tokens_cannot_manufacture_a_fixture(self):
        with self.assertRaises(ValueError):
            parse_egypt_fixture('<html>المصري القناة الجولة 6 الأحد 11 أكتوبر 2026 05:00</html>', source('egypt'))
        with self.assertRaises(ValueError):
            parse_saudi_fixture('<html>First Division League Wednesday 14-10-2026 18:30 Al Jandal Al Okhdood</html>', source('saudi'))

    def test_saudi_dates_pairings_and_new_year_are_read_per_row(self):
        page = saudi_page()+saudi_page(day='2027-01-05', clock='15:30',home='Al Saqer',away='Al Jandal',fixture='33550')
        events = parse_saudi_fixture(page, source('saudi'))
        self.assertEqual(['2026-10-14T15:30:00Z','2027-01-05T12:30:00Z'], [e['start_time'] for e in events])
        self.assertEqual('Al Jandal at Al Saqer', events[1]['name'])

    def test_saudi_other_divisions_do_not_borrow_league_identity(self):
        with self.assertRaises(ValueError):
            parse_saudi_fixture(saudi_page(competition='999'), source('saudi'))

    def test_saudi_unscheduled_time_is_held(self):
        with self.assertRaises(ValueError):
            parse_saudi_fixture(saudi_page(clock='TBC'), source('saudi'))

    def test_wrong_catalog_scope_is_held(self):
        s=source('saudi');s['league']='Saudi Pro League | Men'
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            parse_saudi_fixture(saudi_page(),s)


if __name__ == '__main__':
    unittest.main()
