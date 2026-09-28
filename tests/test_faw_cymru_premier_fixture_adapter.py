"""FAW phase-one match centres must agree with the rolling Cymru Premier cards."""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from faw_cymru_premier_fixture_adapter import parse_phase_one_fixtures  # noqa: E402


class FawCymruPremierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/soccer-uefa-domestic-sources.json").read_text())["sources"]
        cls.source = next(x for x in sources if x["id"] == "uefa-soccer-wales-cymru-premier-men")
        cls.fixture = json.loads((ROOT / "tests/fixtures/faw_cymru_premier_2026_phase_one.json").read_text())
        cls.today = datetime.date(2026, 9, 27)
        cls.end = datetime.date(2026, 10, 4)
        cls.now = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)

    def parse(self, page=None, source=None, end=None, match_pages=None):
        return parse_phase_one_fixtures(
            page if page is not None else self.fixture["listing"],
            source if source is not None else self.source,
            self.today, end if end is not None else self.end, self.now,
            (match_pages if match_pages is not None else self.fixture["match_pages"]).__getitem__,
        )

    def test_nine_named_current_window_fixtures(self):
        events = self.parse()
        self.assertEqual(9, len(events))
        self.assertEqual("Haverfordwest County AFC at Cardiff Met FC", events[0]["name"])
        self.assertEqual("2026-09-29T18:45:00Z", events[0]["start_time"])
        self.assertEqual("Penybont FC at Connah's Quay Nomads FC", events[6]["name"])
        self.assertEqual("2026-10-03T13:30:00Z", events[-1]["start_time"])
        self.assertTrue(all(x["source_id"] == self.source["id"] for x in events))

    def test_scope_status_clock_and_rolling_horizon_fail_closed(self):
        page = self.fixture["listing"]
        with self.assertRaises(ValueError):
            self.parse(source={**self.source, "catalog_terms": ["Welsh Cup | Men"]})
        with self.assertRaises(ValueError):
            self.parse(page=page.replace("fixture initial-load-match", "initial-load-match", 1))
        with self.assertRaises(ValueError):
            self.parse(page=page.replace("14:30", "15:30", 1))
        with self.assertRaises(ValueError):
            self.parse(end=datetime.date(2026, 10, 9))
        first_link = next(iter(self.fixture["match_pages"]))
        changed = dict(self.fixture["match_pages"])
        changed[first_link] = changed[first_link].replace("data-comp-id=\"107679230\"", "data-comp-id=\"other\"")
        with self.assertRaises(ValueError):
            self.parse(match_pages=changed)

    def test_only_exact_phase_one_identity_is_configured(self):
        rows = {x["identity_key"]: x for x in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-wales-cymru-premier-men"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-wales-welsh-cup-men"]["coverage_state"])
        self.assertEqual("DOCUMENTED_HOLD", rows["soccer-wales-welsh-league-cup-men"]["season_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
