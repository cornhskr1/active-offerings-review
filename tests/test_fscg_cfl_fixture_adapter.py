import unittest
from pathlib import Path
from scripts.fscg_cfl_fixture_adapter import parse_round

SOURCE = {
    "id": "uefa-soccer-montenegro-montenegrin-first-league-men", "sport": "Soccer",
    "league": "Montenegrin First League | Men", "region": "Montenegro",
    "catalog_terms": ["Montenegrin First League | Men"],
    "endpoint": "https://fscg.me/takmicenja/meridianbet-1-cfl/",
}


def page():
    return (Path(__file__).parent / 'fixtures/mont-current-fixtures-20261006.html').read_text()


class FscgCflAdapterTests(unittest.TestCase):
    def test_current_publisher_dates_replace_the_old_pinned_round(self):
        events=parse_round(page(),SOURCE)
        self.assertEqual(5,len(events))
        self.assertEqual('2026-10-08T12:00:00Z',events[0]['start_time'])
        self.assertEqual('OFK Mladost Lob.bet at Otrant-Olympic',events[0]['name'])
        self.assertEqual('2026-10-10T17:00:00Z',events[-1]['start_time'])
        self.assertEqual('ROUND 10',events[0]['season_stage'])

    def test_published_reschedule_updates_time_without_changing_match_identity(self):
        original=parse_round(page(),SOURCE)
        changed=parse_round(page().replace('08.10.2026.','09.10.2026.').replace('<td>14:00</td>','<td>15:00</td>'),SOURCE)
        self.assertEqual(original[0]['id'],changed[0]['id'])
        self.assertEqual('2026-10-09T13:00:00Z',changed[0]['start_time'])

    def test_completed_records_are_not_upcoming(self):
        changed=page().replace('<span class="res1">-</span>','<span class="res1">1</span>').replace('<span class="res2">-</span>','<span class="res2">0</span>')
        with self.assertRaisesRegex(ValueError,'no timed upcoming'):
            parse_round(changed,SOURCE)

    def test_missing_kickoff_duplicate_match_and_wrong_edition_are_held(self):
        for changed in [page().replace('<td>14:00</td>','<td>TBC</td>',1),page().replace('data-id="9278836"','data-id="9278833"'),page().replace('<h2>2026/27</h2>','<h2>2025/26</h2>')]:
            with self.subTest(changed=changed[:30]),self.assertRaises(ValueError):
                parse_round(changed,SOURCE)

    def test_wrong_catalog_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            parse_round(page(),dict(SOURCE,league='Montenegrin Cup | Men'))

    def test_archive_cannot_supply_missing_current_fixtures(self):
        with self.assertRaisesRegex(ValueError,'current fixture table'):
            parse_round(page().replace('tabContent_1_1','tabContent_1_2'),SOURCE)


if __name__ == '__main__':
    unittest.main()
