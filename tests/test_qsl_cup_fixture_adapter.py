"""The official QSL Cup round stays separate from Qatar's league and Qatar Cup."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from qsl_cup_fixture_adapter import parse_qsl_cup_fixtures  # noqa: E402


class QslCupFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(x for x in json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]
                          if x["id"] == "soccer-afc-qatar-qsl-cup-men")
        cls.page = (ROOT / "tests/fixtures/qsl_cup_2026_round_two.html").read_text()
        cls.now = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)

    def test_nine_senior_club_fixtures_and_qatar_clock(self):
        events = parse_qsl_cup_fixtures(self.page, self.source, self.now)
        self.assertEqual(9, len(events))
        self.assertEqual("Al Wakrah at Al Kharaitiyat", events[0]["name"])
        self.assertEqual("2026-09-28T15:00:00Z", events[0]["start_time"])
        self.assertEqual("Al Bidda at Qatar SC", events[-1]["name"])
        self.assertEqual("2026-10-01T17:15:00Z", events[-1]["start_time"])
        self.assertTrue(all(x["source_id"] == self.source["id"] for x in events))

    def test_completed_results_leave_six_upcoming_cards(self):
        rows = self.page.split('<tr>')
        self.assertEqual(10, len(rows))
        completed = ''.join('<tr>' + row.split('</tr>')[0].split('<a href=')[0] + '</tr>'
                            for row in rows[1:4])
        page = self.page.replace('<tr>' + '<tr>'.join(rows[1:4]), '')
        page += '<div class="tab-pane fade show active" id="group-121-res"><table>' + completed + '</table></div>'
        events = parse_qsl_cup_fixtures(page, self.source, self.now)
        self.assertEqual([f'qsl-cup-2026-27-{i}' for i in range(13, 19)], [e['id'] for e in events])
        with self.assertRaises(ValueError):
            parse_qsl_cup_fixtures(page.replace('<span>10</span>', '<span>12</span>'), self.source, self.now)

    def test_missing_duplicate_or_stale_round_fails_closed(self):
        for page, source, now in (
            (self.page, {**self.source, "catalog_terms": ["Qatar Cup | Men"]}, self.now),
            (self.page.replace("QSL cup", "Qatar Cup"), self.source, self.now),
            (self.page.replace("<span>Al Bidda</span>", "<span>TBD</span>"), self.source, self.now),
            (self.page.replace("<span>Al Bidda</span>", "<span>Al Wakrah</span>"), self.source, self.now),
            (self.page.replace("<span>Al Bidda</span>", ""), self.source, self.now),
            (self.page, self.source, datetime.datetime(2026, 10, 2, tzinfo=datetime.timezone.utc)),
        ):
            with self.subTest(source=source["catalog_terms"], now=now):
                with self.assertRaises(ValueError):
                    parse_qsl_cup_fixtures(page, source, now)

    def test_current_round_tbd_is_explicit_and_never_a_timed_card(self):
        page=(ROOT/'tests/fixtures/qsl-cup-tbd-20261006.html').read_text()
        with self.assertRaisesRegex(ValueError,'9 published pairings lack date/kickoff'):
            parse_qsl_cup_fixtures(page,self.source,datetime.datetime(2026,10,6,tzinfo=datetime.timezone.utc))

    def test_new_match_numbers_do_not_reuse_completed_round_dates(self):
        page=self.page
        for i in range(18,9,-1):page=page.replace(f'<span>{i}</span>',f'<span>{i+9}</span>')
        events=parse_qsl_cup_fixtures(page,self.source,self.now)
        self.assertEqual('qsl-cup-2026-27-19',events[0]['id'])

    def test_other_qatar_competitions_remain_gaps(self):
        rows = {x["identity_key"]: x for x in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qsl-cup-men"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-qatar-qatar-cup-men"]["coverage_state"])
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qatar-stars-league-men"]["coverage_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
