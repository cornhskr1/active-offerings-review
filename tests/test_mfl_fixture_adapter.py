"""MFL's league, FA Cup, Malaysia Cup and Charity Shield stay distinct."""

import datetime
import json
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from mfl_fixture_adapter import parse_mfl_schedule, pdf_url  # noqa: E402


class MflFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]
        cls.sources = {s["league"]: s for s in sources if s["region"] == "Malaysia"}
        cls.league = (ROOT / "tests/fixtures/mfl_league_round_five_2026.txt").read_text()
        cls.fa = (ROOT / "tests/fixtures/mfl_fa_cup_quarterfinals_2026.txt").read_text()
        cls.end = datetime.date(2026, 10, 4)

    def test_distinct_senior_rounds_and_malaysia_kickoffs(self):
        league, held = parse_mfl_schedule(self.league, self.sources["Malaysia Super League | Men"], "league", self.end)
        self.assertEqual((6, 0), (len(league), held))
        self.assertEqual("STAR CITY FC at KELANTAN RED WARRIOR FC", league[0]["name"])
        self.assertEqual("2026-10-16T13:00:00Z", league[0]["start_time"])
        self.assertEqual("mfl-league-2026-27-30", league[-1]["id"])
        self.assertTrue(all("2026-10-" in e["start_time"] for e in league))

        cup, held = parse_mfl_schedule(self.fa, self.sources["Malaysia FA Cup | Men"], "fa-cup", self.end)
        self.assertEqual((3, 1), (len(cup), held))
        self.assertEqual("PENANG FC at JOHOR DARUL TA'ZIM", cup[0]["name"])
        self.assertEqual("2026-10-09T12:15:00Z", cup[0]["start_time"])
        self.assertNotIn("KELANTAN CITY FC", " ".join(e["name"] for e in cup))
        self.assertTrue(all(e["season_stage"] == "QUARTERFINAL" for e in cup))

    def test_changed_round_revision_and_catalog_scope_fail_closed(self):
        league_source = self.sources["Malaysia Super League | Men"]
        fa_source = self.sources["Malaysia FA Cup | Men"]
        cases = (
            (self.league, {**league_source, "catalog_terms": ["Charity Shield | Men"]}, "league", self.end),
            (self.league.replace("KEMASKINI : 2 SEPTEMBER 2026", "KEMASKINI : 3 SEPTEMBER 2026"), league_source, "league", self.end),
            (self.league.replace("25 KELANTAN", "25 TBC"), league_source, "league", self.end),
            (self.league.replace("26 NEGERI", "25 NEGERI"), league_source, "league", self.end),
            (self.league, league_source, "league", datetime.date(2026, 10, 19)),
            (self.fa.replace("17 SEPTEMBER 2026", "18 SEPTEMBER 2026"), fa_source, "fa-cup", self.end),
            (self.fa.replace("21 JOHOR", "21 TBC"), fa_source, "fa-cup", self.end),
            (self.fa.replace("KELANTAN CITY FC", "SELANGOR FC"), fa_source, "fa-cup", self.end),
            (self.fa, fa_source, "fa-cup", datetime.date(2026, 10, 12)),
        )
        for page, source, kind, end in cases:
            with self.subTest(kind=kind, end=end, scope=source["catalog_terms"], page_len=len(page)):
                with self.assertRaises(ValueError):
                    parse_mfl_schedule(page, source, kind, end)

    def test_future_review_windows_admit_only_the_matching_competition(self):
        central = ZoneInfo("America/Chicago")
        for text, source, kind, start, end, expected in (
            (self.fa, self.sources["Malaysia FA Cup | Men"], "fa-cup",
             datetime.date(2026, 10, 6), datetime.date(2026, 10, 11), 3),
            (self.league, self.sources["Malaysia Super League | Men"], "league",
             datetime.date(2026, 10, 11), datetime.date(2026, 10, 18), 6),
        ):
            events, _ = parse_mfl_schedule(text, source, kind, end)
            admitted = [event for event in events if start <= datetime.datetime.fromisoformat(
                event["start_time"].replace("Z", "+00:00")).astimezone(central).date() <= end]
            self.assertEqual(expected, len(admitted))

    def test_authority_attachment_and_other_mfl_identities_stay_gaps(self):
        url = "https://files.malaysianfootballleague.com/wp-content/uploads/2026/09/JADUAL-PIALA-FA-2026-2027-PUSINGAN-SUKU-AKHIR.pdf"
        self.assertEqual(url, pdf_url(f'<a href="{url}">Schedule</a>', "fa-cup"))
        with self.assertRaises(ValueError):
            pdf_url('<a href="https://other.example/JADUAL-PIALA-FA-2026-2027-PUSINGAN-SUKU-AKHIR.pdf">Schedule</a>', "fa-cup")
        rows = {r["identity_key"]: r for r in build()["identities"]}
        for suffix in ("malaysia-super-league-men", "malaysia-fa-cup-men"):
            self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-malaysia-" + suffix]["coverage_state"])
        for suffix in ("malaysia-cup-men", "charity-shield-men"):
            self.assertEqual("ADAPTER_GAP", rows["soccer-malaysia-" + suffix]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
