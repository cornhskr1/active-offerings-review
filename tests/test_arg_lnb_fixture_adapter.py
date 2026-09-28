"""An official Argentina LNB match cannot drift into another date or competition."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from arg_lnb_fixture_adapter import parse_arg_lnb_fixtures  # noqa: E402


class ArgLnbFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        cls.source = next(s for s in sources if s["id"] == "basketball-ar-lnb")
        cls.page = (ROOT / "tests/fixtures/arg_lnb_fixture_2026.html").read_text()
        cls.start, cls.end = datetime.date(2026, 9, 28), datetime.date(2026, 10, 5)

    def test_publisher_match_and_argentina_kickoff(self):
        events = parse_arg_lnb_fixtures(self.page, self.source, self.start, self.end)
        self.assertEqual(1, len(events))
        self.assertEqual("GIMNASIA (CR) at LANÚS", events[0]["name"])
        self.assertEqual("2026-09-29T01:05:00Z", events[0]["start_time"])
        self.assertTrue(events[0]["source_endpoint"].startswith(
            "https://www.laliganacional.com.ar/laliga/partido/"))

    def test_empty_week_and_scope_changes(self):
        empty = '<div><p>No se encontraron partidos</p></div>'
        self.assertEqual([], parse_arg_lnb_fixtures(empty, self.source, self.start, self.end))
        with self.assertRaises(ValueError):
            parse_arg_lnb_fixtures("<html></html>", self.source, self.start, self.end)
        with self.assertRaises(ValueError):
            parse_arg_lnb_fixtures(self.page, self.source, datetime.date(2026, 10, 1), self.end)
        with self.assertRaises(ValueError):
            parse_arg_lnb_fixtures(self.page.replace("/laliga/partido/", "/ligaargentina/partido/"),
                                   self.source, self.start, self.end)
        with self.assertRaises(ValueError):
            parse_arg_lnb_fixtures(self.page, {**self.source, "catalog_terms": ["Argentina Liga | Women"]},
                                   self.start, self.end)


if __name__ == "__main__":
    unittest.main()
