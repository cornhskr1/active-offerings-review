"""The Doha Bank Stars League fixture feed has its own exact competition scope."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from qsl_stars_league_fixture_adapter import parse_qsl_stars_fixtures  # noqa: E402


class QslStarsLeagueFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(
            source
            for source in json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]
            if source["id"] == "soccer-afc-qatar-qatar-stars-league-men"
        )
        cls.page = (ROOT / "tests/fixtures/qsl_stars_2026_upcoming_weeks.html").read_text()
        cls.now = datetime.datetime(2026, 10, 31, 7, 12, tzinfo=datetime.timezone.utc)

    def test_completed_and_upcoming_rows_prove_two_complete_senior_weeks(self):
        events = parse_qsl_stars_fixtures(
            self.page, self.source, self.now, datetime.date(2026, 11, 7)
        )
        self.assertEqual(9, len(events))
        self.assertEqual("Lusail at Al Sailiya", events[0]["name"])
        self.assertEqual("2026-10-31T14:15:00Z", events[0]["start_time"])
        self.assertEqual("Al Rayyan at Al Sadd", events[-1]["name"])
        self.assertEqual("2026-11-08T16:30:00Z", events[-1]["start_time"])
        self.assertEqual(
            {f"qsl-stars-2026-27-{number}" for number in range(46, 55)},
            {event["id"] for event in events},
        )
        self.assertEqual(
            {"QSL published league fixture, week 8", "QSL published league fixture, week 9"},
            {event["status_detail"] for event in events},
        )
        self.assertTrue(all(event["source_id"] == self.source["id"] for event in events))

    def test_scope_structure_completeness_and_freshness_fail_closed(self):
        cases = (
            (self.page, {**self.source, "catalog_terms": ["QSL Cup | Men"]}, self.now),
            (self.page.replace("Doha Bank Stars League", "QSL Cup"), self.source, self.now),
            (self.page.replace("2026-2027", "2025-2026"), self.source, self.now),
            (self.page.replace("<span>Al Duhail</span>", "<span>TBD</span>", 1), self.source, self.now),
            (self.page.replace("<span>Al Duhail</span>", "<span>Al Sailiya</span>", 1), self.source, self.now),
            (self.page.replace('<tr class="fixture-result">', '<tr>', 1), self.source, self.now),
            (self.page.replace('<tr class="result-row">', '<tr>', 1), self.source, self.now),
            (self.page.replace('<span>46</span>', '<span>47</span>', 1), self.source, self.now),
            (self.page.replace('<div class="table__result__points">2 - 0</div>',
                               '<div class="table__result__points">TBD</div>', 1), self.source, self.now),
            (self.page, self.source, datetime.datetime(2026, 11, 9, tzinfo=datetime.timezone.utc)),
        )
        for page, source, now in cases:
            with self.subTest(scope=source["catalog_terms"], now=now, length=len(page)):
                with self.assertRaises(ValueError):
                    parse_qsl_stars_fixtures(page, source, now, datetime.date(2026, 11, 7))
        with self.assertRaisesRegex(ValueError, "full review window"):
            parse_qsl_stars_fixtures(
                self.page, self.source, self.now, datetime.date(2026, 11, 9)
            )

    def test_cup_identity_remains_separate(self):
        rows = {row["identity_key"]: row for row in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qatar-stars-league-men"]["coverage_state"])
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qsl-cup-men"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-qatar-qatar-cup-men"]["coverage_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
