"""Current FIBA report fixtures fail closed on scope, dates, layout and placeholders."""

import copy
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fiba_report_fixture_adapter import (  # noqa: E402
    BASE, SPECS, _read_pdf, fetch_fiba_report_fixtures, parse_fiba_report,
    parse_fiba_report_rows, report_url,
)
from urllib.parse import urlencode


class FibaReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.today, cls.end = dt.date(2026, 10, 18), dt.date(2026, 10, 25)
        cls.sources, cls.contents, cls.tables = {}, {}, {}
        for sid, spec in SPECS.items():
            cls.sources[sid] = {
                "id": sid, "sport": "Basketball", "league": spec["league"],
                "region": "Europe", "catalog_terms": spec["catalog_terms"],
                "source_type": "official-fiba-report-fixtures", "fiba_report_path": spec["path"],
                "endpoint": BASE + "/api/list.php?" + urlencode({"path": spec["path"]}),
            }
            filename = "bcl-2027-20261014.pdf" if sid == "fiba-bcl" else "euroleague-women-2027-20261015.pdf"
            cls.contents[sid] = (ROOT / "tests/fixtures/fiba" / filename).read_bytes()
            cls.tables[sid] = _read_pdf(cls.contents[sid])

    def parse(self, sid="basketball-womens-euroleague", **changes):
        text, rows = self.tables[sid]
        return parse_fiba_report_rows(changes.get("text", text), changes.get("rows", rows),
                                      changes.get("source", self.sources[sid]),
                                      changes.get("today", self.today), changes.get("end", self.end))

    def changed_row(self, sid="basketball-womens-euroleague", **changes):
        rows = copy.deepcopy(self.tables[sid][1])
        row = next(r for r in rows if r["Game"] == "D-3")
        row.update(changes)
        return rows

    def test_actual_pdf_columns_and_complete_first_rounds(self):
        for sid, total, placeholders, horizon in (
            ("basketball-womens-euroleague", 56, 54, "2026-12-02"),
            ("fiba-bcl", 96, 40, "2026-12-23"),
        ):
            events, evidence = parse_fiba_report(self.contents[sid], self.sources[sid], self.today, self.end)
            self.assertEqual(8, len(events))
            self.assertEqual(total, evidence["published_fixtures"])
            self.assertEqual(placeholders, evidence["unresolved_published_rows"])
            self.assertEqual(0, evidence["held_review_fixtures"])
            self.assertEqual(horizon, evidence["fixture_coverage_end"])
            self.assertTrue(evidence["review_window_complete"])
            self.assertTrue(all(e["source_id"] == sid and e["source_endpoint"] == report_url(self.sources[sid]) for e in events))
        events, _ = self.parse()
        self.assertEqual(("UMCS vs USK", "2026-10-21T16:00:00Z"),
                         (events[0]["name"], events[0]["start_time"]))
        # These games straddle a page break; stream-order extraction reverses them.
        self.assertEqual("2026-10-21T18:00:00Z", next(e["start_time"] for e in events if e["name"] == "VBC vs FCB"))
        self.assertEqual("2026-10-22T18:30:00Z", next(e["start_time"] for e in events if e["name"] == "MEC vs GALA"))
        bcl, _ = self.parse("fiba-bcl")
        self.assertEqual("2026-10-20T16:00:00Z", bcl[0]["start_time"])
        self.assertEqual("FAL vs VIL", bcl[0]["name"])

    def test_no_qualifier_or_division_scope_substitution(self):
        original = self.sources["basketball-womens-euroleague"]
        for changes in (
            {"id": "basketball-fiba-world-cup-men"},
            {"catalog_terms": ["FIBA Basketball World Cup | Men and Women"]},
            {"league": "EuroLeague | Men"},
            {"fiba_report_path": "2027/EuroCup Women"},
            {"fiba_report_path": "2026/EuroLeague Women"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.parse(source={**original, **changes})
        with self.assertRaises(ValueError):
            self.parse(text=self.tables[original["id"]][0].replace("EuroLeague Women 2027", "EuroCup Women 2027"))

    def test_full_date_weekday_and_season_are_required(self):
        for day in ("WED 21 OCT", "THU 21 OCT 2026", "WED 21 OCT 2020"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.parse(rows=self.changed_row(Date=day))
        with self.assertRaises(ValueError):
            self.parse(text=self.tables["basketball-womens-euroleague"][0].replace("18-Apr-2027", "18-Apr-2028"))

    def test_time_tbd_is_date_only_not_midnight_or_local_as_utc(self):
        events, evidence = self.parse(rows=self.changed_row(Local="TBD", UTC="TBD"))
        event = next(e for e in events if e["name"] == "UMCS vs USK")
        self.assertEqual("2026-10-21", event["start_time"])
        self.assertTrue(event["date_only"])
        self.assertIn("time TBD", event["status_detail"])
        self.assertTrue(evidence["review_window_complete"])
        for values in ({"Local": "18:00", "UTC": "TBD"}, {"Local": "18:00", "UTC": "25:00"},
                       {"Local": "23:00", "UTC": "01:00"}, {"Local": "01:00", "UTC": "23:00"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.parse(rows=self.changed_row(**values))

    def test_missing_duplicate_or_unresolved_first_round_fails(self):
        rows = self.tables["basketball-womens-euroleague"][1]
        with self.assertRaises(ValueError):
            self.parse(rows=[r for r in rows if r["Game"] != "D-3"])
        with self.assertRaises(ValueError):
            self.parse(rows=rows + [next(r for r in rows if r["Game"] == "D-3")])
        for team in ("UMCS vs UMCS", "UMCS vs TBD", "Winner of Game 1 vs USK"):
            with self.subTest(team=team), self.assertRaises(ValueError):
                self.parse(rows=self.changed_row(Teams=team))

    def test_future_placeholders_and_report_horizon_never_clear_review(self):
        _, evidence = self.parse(end=dt.date(2026, 12, 17))
        self.assertEqual(6, evidence["held_review_fixtures"])
        self.assertFalse(evidence["review_window_complete"])
        events, evidence = self.parse("fiba-bcl", end=dt.date(2027, 1, 15))
        self.assertFalse(evidence["review_window_complete"])
        self.assertEqual(0, evidence["held_review_fixtures"])  # undated BCL playoff rows stay undated
        self.assertTrue(all("group" not in e["name"] for e in events))
        _, evidence = self.parse(today=dt.date(2026, 11, 1), end=dt.date(2026, 11, 7))
        self.assertFalse(evidence["review_window_complete"])
        self.assertIn("14 days", evidence["coverage_note"])

    def test_named_later_final_cannot_extend_unproven_phase_horizon(self):
        rows = copy.deepcopy(self.tables["basketball-womens-euroleague"][1])
        later = next(r for r in reversed(rows) if r["Phase"] == "Final")
        later.update({"Date": "SUN 18 APR 2027", "Local": "TBD", "UTC": "TBD", "Teams": "UMCS vs USK"})
        _, evidence = self.parse(rows=rows, end=dt.date(2027, 4, 18))
        self.assertEqual("2026-12-02", evidence["fixture_coverage_end"])
        self.assertFalse(evidence["review_window_complete"])

    def test_completed_or_cancelled_disposition_not_upcoming(self):
        events, _ = self.parse(rows=self.changed_row(Score="80-60"))
        self.assertNotIn("UMCS vs USK", {e["name"] for e in events})
        with self.assertRaises(ValueError):
            self.parse(rows=self.changed_row(Score="POSTPONED"))

    def test_pdf_html_and_publication_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_fiba_report(b"<html>Blocked</html>", self.sources["fiba-bcl"], self.today, self.end)
        text = self.tables["fiba-bcl"][0]
        with self.assertRaises(ValueError):
            self.parse("fiba-bcl", text=text.replace("Created on", "Generated"))
        with self.assertRaises(ValueError):
            self.parse("fiba-bcl", text=text.replace("14 Oct 2026 20:03", "19 Oct 2026 20:03"))

    def response(self, *, payload=None, content=b"", content_type="application/json", status=200):
        response = Mock(status_code=status, content=content, headers={"Content-Type": content_type})
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    def test_fetch_discovers_exact_public_pdf_without_login_or_retry(self):
        sid = "fiba-bcl"
        listing = self.response(payload={"files": [{"name": "competition-schedule.pdf", "lastModified": "2026-10-14T20:03:33+00:00"}]})
        pdf = self.response(content=self.contents[sid], content_type="application/pdf")
        get = Mock(side_effect=[listing, pdf])
        events, evidence = fetch_fiba_report_fixtures(self.sources[sid], self.today, self.end, get=get)
        self.assertEqual(8, len(events))
        self.assertEqual(2, get.call_count)
        self.assertEqual(self.sources[sid]["endpoint"], get.call_args_list[0].args[0])
        self.assertEqual(report_url(self.sources[sid]), get.call_args_list[1].args[0])
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual("2026-10-14T20:03:33Z", evidence["report_directory_modified_at"])
        blocked = self.response(status=403)
        blocked.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        get = Mock(return_value=blocked)
        with self.assertRaises(requests.HTTPError):
            fetch_fiba_report_fixtures(self.sources[sid], self.today, self.end, get=get)
        self.assertEqual(1, get.call_count)

    def test_directory_html_redirect_and_ambiguous_pdf_fail(self):
        sid = "fiba-bcl"
        for listing in ({"files": []}, {"files": [{"name": "competition-schedule.pdf"}]},
                        {"files": [{"name": "competition-schedule.pdf"}] * 2}):
            get = Mock(return_value=self.response(payload=listing))
            with self.subTest(listing=listing), self.assertRaises(ValueError):
                fetch_fiba_report_fixtures(self.sources[sid], self.today, self.end, get=get)
            self.assertEqual(1, get.call_count)
        get = Mock(return_value=self.response(status=302))
        with self.assertRaises(ValueError):
            fetch_fiba_report_fixtures(self.sources[sid], self.today, self.end, get=get)
        self.assertEqual(1, get.call_count)


if __name__ == "__main__":
    unittest.main()
