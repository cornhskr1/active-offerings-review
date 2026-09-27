"""WSL2's rolling official fixture page belongs to one current catalog identity."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from wsl2_fixture_adapter import parse_wsl2_fixtures  # noqa: E402


class WSL2FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/soccer-uefa-domestic-sources.json").read_text())["sources"]
        cls.source = next(row for row in sources if row["id"] == "uefa-soccer-england-super-league-2-women")
        cls.page = (ROOT / "tests/fixtures/wsl2_2026_rolling_fixtures.html").read_text()

    def test_exact_named_fixtures_and_london_clock(self):
        fixtures = parse_wsl2_fixtures(self.page, self.source, datetime.date(2026, 10, 4))
        self.assertEqual(10, len(fixtures))
        self.assertEqual("Newcastle United at Durham", fixtures[0]["name"])
        self.assertEqual("2026-10-04T11:00:00Z", fixtures[0]["start_time"])
        self.assertEqual("2026-10-25T14:00:00Z", fixtures[-1]["start_time"])
        self.assertTrue(all(row["source_id"] == self.source["id"] for row in fixtures))

    def test_page_scope_and_truncation_fail_closed(self):
        for page, source, end in (
            (self.page.replace('alt="Barclays WSL2"', 'alt="Barclays WSL"', 1), self.source, datetime.date(2026, 10, 4)),
            (self.page, {**self.source, "catalog_terms": ["The Championship | Men and Women"]}, datetime.date(2026, 10, 4)),
            (self.page, self.source, datetime.date(2026, 10, 25)),
            (self.page.replace("2026-10-25T12:00:00", "2026-10-03T12:00:00"), self.source, datetime.date(2026, 10, 4)),
        ):
            with self.subTest(source=source["catalog_terms"], end=end, changed=page is not self.page):
                with self.assertRaises(ValueError):
                    parse_wsl2_fixtures(page, source, end)

    def test_legacy_catalog_child_is_held(self):
        rows = {row["identity_key"]: row for row in build()["identities"]}
        current = rows["soccer-england-super-league-2-women"]
        legacy = rows["soccer-england-the-championship-women"]
        self.assertEqual("ADAPTER_CONFIGURED", current["coverage_state"])
        self.assertEqual("ADAPTER_GAP", legacy["coverage_state"])
        self.assertEqual("DOCUMENTED_HOLD", legacy["season_state"])


if __name__ == "__main__":
    unittest.main()
