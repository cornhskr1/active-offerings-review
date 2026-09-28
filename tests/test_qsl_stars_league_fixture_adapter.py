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
        cls.source = next(s for s in json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]
                          if s["id"] == "soccer-afc-qatar-qatar-stars-league-men")
        cls.page = (ROOT / "tests/fixtures/qsl_stars_2026_upcoming_weeks.html").read_text()
        cls.now = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)

    def test_two_complete_senior_weeks_and_qatar_clock(self):
        events = parse_qsl_stars_fixtures(self.page, self.source, self.now, datetime.date(2026, 10, 4))
        self.assertEqual(12, len(events))
        self.assertEqual("Al Duhail at Al Shamal", events[0]["name"])
        self.assertEqual("2026-10-08T14:45:00Z", events[0]["start_time"])
        self.assertEqual("Al Duhail at Al Sadd", events[-1]["name"])
        self.assertEqual("2026-10-18T16:45:00Z", events[-1]["start_time"])
        self.assertEqual(12, len({e["id"] for e in events}))
        self.assertTrue(all(e["source_id"] == self.source["id"] for e in events))

    def test_wrong_scope_incomplete_week_and_stale_page_fail_closed(self):
        cases = (
            (self.page, {**self.source, "catalog_terms": ["QSL Cup | Men"]}, self.now),
            (self.page.replace("Doha Bank Stars League", "QSL Cup"), self.source, self.now),
            (self.page.replace("2026-2027", "2025-2026"), self.source, self.now),
            (self.page.replace('<span>Al Duhail</span>', '<span>TBD</span>', 1), self.source, self.now),
            (self.page.replace('<span>Al Duhail</span>', '<span>Al Shamal</span>', 1), self.source, self.now),
            (self.page.replace('<tr class="fixture-result">', '<tr>', 1), self.source, self.now),
            (self.page, self.source, datetime.datetime(2026, 10, 19, tzinfo=datetime.timezone.utc)),
        )
        for page, source, now in cases:
            with self.subTest(scope=source["catalog_terms"], now=now, length=len(page)):
                with self.assertRaises(ValueError):
                    parse_qsl_stars_fixtures(page, source, now, datetime.date(2026, 10, 4))
        with self.assertRaisesRegex(ValueError, "full review window"):
            parse_qsl_stars_fixtures(self.page, self.source, self.now, datetime.date(2026, 10, 19))

    def test_cup_identity_remains_separate(self):
        rows = {x["identity_key"]: x for x in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qatar-stars-league-men"]["coverage_state"])
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-qatar-qsl-cup-men"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-qatar-qatar-cup-men"]["coverage_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
