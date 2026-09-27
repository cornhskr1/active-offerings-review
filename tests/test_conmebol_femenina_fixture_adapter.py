"""The published women's group schedule remains separate from men's and unresolved labels."""

import json
import datetime
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from conmebol_femenina_fixture_adapter import parse_group_fixtures  # noqa: E402
from audit_priority2_coverage import build  # noqa: E402


class ConmebolFemeninaFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/soccer-international-sources.json").read_text())["sources"]
        cls.source = next(source for source in sources
                          if source["id"] == "soccer-conmebol-libertadores-femenina")
        cls.page = (ROOT / "tests/fixtures/conmebol_femenina_2026_group_schedule.html").read_text()

    def test_official_group_list_holds_unidentified_clubs(self):
        fixtures, held = parse_group_fixtures(self.page, self.source)
        self.assertEqual((18, 6), (len(fixtures), len(held)))
        self.assertEqual("2026-10-15T20:00:00Z", fixtures[0]["start_time"])
        self.assertEqual("Belgrano at Independiente del Valle", fixtures[0]["name"])
        self.assertTrue(all(row["source_id"] == self.source["id"] for row in fixtures))
        self.assertTrue(all("Colombia " in row["name"] for row in held))
        central_days = [datetime.datetime.fromisoformat(row["start_time"].replace("Z", "+00:00"))
                        .astimezone(ZoneInfo("America/Chicago")).date() for row in fixtures]
        self.assertEqual(15, sum(datetime.date(2026, 10, 14) <= day <= datetime.date(2026, 10, 21)
                                 for day in central_days))

    def test_changes_to_count_scope_or_time_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_group_fixtures(self.page.replace("19:00h L.D.U. Quito vs. Bolívar", "L.D.U. Quito vs. Bolívar"), self.source)
        with self.assertRaises(ValueError):
            parse_group_fixtures(self.page.replace("15:00h Independiente", "16:00h Independiente"), self.source)
        with self.assertRaises(ValueError):
            parse_group_fixtures(self.page, {**self.source, "catalog_terms": ["Copa Libertadores | Men"]})

    def test_only_one_exact_identity_changes_coverage_state(self):
        rows = {row["identity_key"]: row for row in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-international-copa-libertadores-femenina-women"]["coverage_state"])
        for key in ("soccer-international-copa-libertadores-women",
                    "soccer-international-copa-sudamericana-women",
                    "soccer-international-recopa-sudamericana-women"):
            self.assertEqual("ADAPTER_GAP", rows[key]["coverage_state"])
        self.assertEqual("partial", self.source["coverage_status"])


if __name__ == "__main__":
    unittest.main()
