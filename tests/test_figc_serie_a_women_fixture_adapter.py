"""FIGC's timed women's Serie A rounds cannot leak into other competitions."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from figc_serie_a_women_fixture_adapter import parse_figc_rounds  # noqa: E402


class FigcSerieAWomenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(x for x in json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
                          if x["id"] == "soccer-italy-serie-a-women")
        cls.page = (ROOT / "tests/fixtures/figc_serie_a_women_2026_rounds.html").read_text()

    def test_exact_rounds_and_rome_kickoffs(self):
        events = parse_figc_rounds(self.page, self.source, datetime.date(2026, 10, 4))
        self.assertEqual(12, len(events))
        self.assertEqual("Ternana Women at Parma", events[0]["name"])
        self.assertEqual("2026-10-03T10:30:00Z", events[0]["start_time"])
        self.assertEqual("Como 1907 at Napoli Women", events[3]["name"])
        self.assertEqual("Inter at Como Women", events[5]["name"])
        self.assertEqual("2026-10-18T16:00:00Z", events[-1]["start_time"])

    def test_changed_scope_pairing_or_horizon_fails_closed(self):
        page = self.page
        for candidate, source, end in (
            (page, {**self.source, "catalog_terms": ["Coppa Italia | Men and Women"]}, datetime.date(2026, 10, 4)),
            (page.replace("SERIE A WOMEN ATHORA 2026-27", "COPPA ITALIA WOMEN 2026-27"), self.source, datetime.date(2026, 10, 4)),
            (page.replace("Ore 15: Milan-Juventus (DAZN)", ""), self.source, datetime.date(2026, 10, 4)),
            (page.replace("Ore 15: Milan-Juventus", "Ore 15: Milan-Parma"), self.source, datetime.date(2026, 10, 4)),
            (page, self.source, datetime.date(2026, 10, 19)),
        ):
            with self.subTest(end=end, source=source["catalog_terms"]):
                with self.assertRaises(ValueError):
                    parse_figc_rounds(candidate, source, end)

    def test_cup_and_supercoppa_remain_gaps(self):
        rows = {x["identity_key"]: x for x in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-italy-serie-a-women"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-italy-coppa-italia-women"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-italy-supercoppa-italiana-women"]["coverage_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
