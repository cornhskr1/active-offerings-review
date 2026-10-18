"""Pinned current evidence and fail-closed regressions for the two SARU scopes."""

import copy
import datetime as dt
import json
from pathlib import Path
import unittest
import uuid

from scripts.saru_exact_fixture_adapter import (
    ENDPOINT, USA_TEAM_ID, collect, parse_saru_exact_matches,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/saru-20261018"
TODAY, END = dt.date(2026, 10, 18), dt.date(2026, 10, 25)


def load(name):
    return json.loads((FIXTURES / (name + ".json")).read_text())


def source(sid="rugby-usa"):
    return next(row for row in json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
                if row["id"] == sid)


def usa_match():
    return next(row for row in load("wxv")["items"]
                if row["matchId"] == "4c1b6487-733d-4378-a4eb-0c29ff5dbeb1")


def payload(rows):
    return {"items": rows, "totalDataCount": len(rows)}


class Response:
    def __init__(self, value, status=200, url=ENDPOINT):
        self.value, self.status_code, self.url = value, status, url

    def json(self):
        return copy.deepcopy(self.value)


class SaruExactFixtureAdapterTests(unittest.TestCase):
    def parse(self, row, **kwargs):
        return parse_saru_exact_matches(payload([row]), source(), TODAY, END, **kwargs)

    def test_opponent_names_are_nonempty_strings(self):
        for name in (123, None, [], {}, "", "   "):
            row = load("currie-first")["items"][0]
            row["teams"][0]["name"] = name
            for team in row["teams"]:
                team["score"] = None
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_saru_exact_matches(payload([row]), source("rugby-saru-currie-first"),
                                         dt.date(2026, 6, 13), dt.date(2026, 6, 20))

    def test_public_snapshot_exact_usa_current_match_and_counts(self):
        counts = {}
        events = parse_saru_exact_matches(load("wxv"), source(), TODAY, END, counts)
        self.assertEqual(1, len(events))
        self.assertEqual("Italy Women at USA Women", events[0]["name"])
        self.assertEqual("2026-10-24T20:15:00Z", events[0]["start_time"])
        self.assertEqual("United States", events[0]["region"])
        self.assertEqual("Women’s USA Rugby Events | Women", events[0]["league"])
        self.assertEqual(30, counts["returned_rows"])
        self.assertEqual(5, counts["scoped_rows"])
        self.assertEqual(25, counts["other_team_rows"])
        self.assertFalse(counts["coverage_complete"])
        self.assertEqual(1, counts["emitted_events"])

    def test_current_first_division_results_never_become_upcoming(self):
        counts = {}
        data = load("currie-first")
        self.assertEqual(18, data["totalDataCount"])
        self.assertTrue(all(row["statsStatus"] == "None" for row in data["items"]))
        events = parse_saru_exact_matches(data, source("rugby-saru-currie-first"),
                                         dt.date(2026, 6, 1), dt.date(2026, 7, 31), counts)
        self.assertEqual([], events)
        self.assertEqual(18, counts["held_scored_or_finished"])

    def test_first_division_unscored_mutation_is_scoped_and_timed(self):
        row = load("currie-first")["items"][-1]
        for team in row["teams"]:
            team["score"] = None
        events = parse_saru_exact_matches(payload([row]), source("rugby-saru-currie-first"),
                                         dt.date(2026, 7, 24), dt.date(2026, 7, 24))
        self.assertEqual("Valke at Dotsure SWD Eagles", events[0]["name"])
        self.assertEqual("2026-07-24T17:15:00Z", events[0]["start_time"])
        row["teams"][0]["name"] = "Valke U19"
        self.assertEqual([], parse_saru_exact_matches(payload([row]), source("rugby-saru-currie-first"),
                                                     dt.date(2026, 7, 24), dt.date(2026, 7, 24)))

    def test_non_usa_wxv_is_not_catalog_approved(self):
        row = next(row for row in load("wxv")["items"]
                   if row["utcDate"] == "2026-10-24T13:00:00")
        self.assertEqual([], self.parse(row))

    def test_usa_id_and_name_both_required(self):
        for field, value in (("teamId", "00000000-0000-0000-0000-000000000000"),
                             ("name", "USA Men")):
            row = usa_match()
            team = next(team for team in row["teams"] if team["teamId"] == USA_TEAM_ID)
            team[field] = value
            with self.assertRaisesRegex(ValueError, "USA Women"):
                self.parse(row)

    def test_source_cannot_broaden_scope_or_claim_complete_coverage(self):
        for field, value in (("required_team_id", None), ("required_team_name", None),
                             ("league", "WXV Global Series"), ("season_name", "2027"),
                             ("id", "rugby-saru"), ("id", "rugby-saru-currie-first"),
                             ("endpoint", "https://example.com/matches"),
                             ("official_schedule_url", "https://example.com/schedule"),
                             ("coverage_status", "complete"), ("coverage_complete", True)):
            scoped = source()
            scoped[field] = value
            with self.assertRaises(ValueError):
                parse_saru_exact_matches(payload([usa_match()]), scoped, TODAY, END)
        scoped = source("rugby-saru-currie-first")
        scoped["coverage_complete"] = True
        with self.assertRaisesRegex(ValueError, "partial"):
            parse_saru_exact_matches(payload([]), scoped, TODAY, END)
        for wrong_id in ("rugby-usa", "rugby-saru", "rugby-saru-currie-premier"):
            scoped = source("rugby-saru-currie-first")
            scoped["id"] = wrong_id
            with self.assertRaisesRegex(ValueError, "scope"):
                parse_saru_exact_matches(payload([]), scoped, TODAY, END)

    def test_wrong_competition_division_and_season_rejected(self):
        for field, value, error in (
            ("competitionId", "56038bac-544a-482e-a5da-6351054efc5d", "competition"),
            ("competitionName", "WXV Global Series Challenger", "competition"),
            ("seasonId", "00000000-0000-0000-0000-000000000000", "season"),
            ("seasonName", "2025", "season"),
            ("utcDate", "2027-10-24T20:15:00", "edition"),
        ):
            row = usa_match()
            row[field] = value
            with self.assertRaisesRegex(ValueError, error):
                self.parse(row)

    def test_unknown_and_incomplete_state_rejected(self):
        for field, value in (("statsStatus", "Suspended"), ("statsStatus", None),
                             ("isCancelled", None), ("isLive", "false")):
            row = usa_match()
            row[field] = value
            with self.assertRaises(ValueError):
                self.parse(row)
        row = usa_match()
        del row["teams"][0]["score"]
        with self.assertRaisesRegex(ValueError, "score"):
            self.parse(row)
        for value in (None, "true", "false", 0, 1):
            row = usa_match()
            row["teams"][0]["hasForfeited"] = value
            with self.assertRaisesRegex(ValueError, "forfeiture"):
                self.parse(row)
        row = usa_match()
        del row["teams"][1]["hasForfeited"]
        with self.assertRaisesRegex(ValueError, "forfeiture"):
            self.parse(row)

    def test_cancelled_postponed_completed_scored_and_forfeited_held(self):
        for field, value in (("isCancelled", True), ("isPostponed", True),
                             ("statsStatus", "Complete"), ("statsStatus", "Result")):
            row = usa_match()
            row[field] = value
            self.assertEqual([], self.parse(row))
        for score in (0, 17, "0"):
            row = usa_match()
            row["teams"][0]["score"] = score
            self.assertEqual([], self.parse(row))
        row = usa_match()
        row["teams"][0]["hasForfeited"] = True
        self.assertEqual([], self.parse(row))

    def test_placeholder_youth_and_missing_time_held(self):
        for name in ("TBD", "TBA", "Winner Pool A", "Italy Women U20", "Unknown"):
            row = usa_match()
            next(team for team in row["teams"] if team["teamId"] != USA_TEAM_ID)["name"] = name
            self.assertEqual([], self.parse(row))
        for timestamp in (None, "2026-10-24", "2026-10-24T99:99:99", "2026-10-24T20:15:00+02:00"):
            row = usa_match()
            row["utcDate"] = timestamp
            self.assertEqual([], self.parse(row))

    def test_utc_suffixes_and_chicago_last_evening(self):
        for timestamp in ("2026-10-24T20:15:00", "2026-10-24T20:15:00Z", "2026-10-24T20:15:00+00:00"):
            row = usa_match()
            row["utcDate"] = timestamp
            self.assertEqual("2026-10-24T20:15:00Z", self.parse(row)[0]["start_time"])
        for timestamp, admitted in (("2026-10-18T04:59:59", False),
                                    ("2026-10-18T05:00:00", True),
                                    ("2026-10-26T04:59:59", True),
                                    ("2026-10-26T05:00:00", False)):
            row = usa_match()
            row["utcDate"] = timestamp
            self.assertEqual(admitted, bool(self.parse(row)))

    def test_duplicate_inconsistent_total_and_malformed_payload_rejected(self):
        row = usa_match()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_saru_exact_matches(payload([row, row]), source(), TODAY, END)
        for data in ({"items": [row], "totalDataCount": 2},
                     {"items": [row], "totalDataCount": True},
                     {"items": [], "totalDataCount": 1001},
                     {"items": [None], "totalDataCount": 1}):
            with self.assertRaises(ValueError):
                parse_saru_exact_matches(data, source(), TODAY, END)

    def test_expired_edition_never_silently_healthy(self):
        with self.assertRaisesRegex(ValueError, "expired"):
            parse_saru_exact_matches(payload([]), source(), dt.date(2027, 1, 1), dt.date(2027, 1, 8))

    def test_atomic_paginated_collection_and_broad_utc_query(self):
        rows = []
        for index in range(101):
            row = usa_match()
            row["matchId"] = str(uuid.UUID(int=index + 1))
            rows.append(row)
        calls = []

        def get(url, **kwargs):
            calls.append((url, kwargs))
            page = kwargs["params"]["pageIndex"]
            return Response({"items": rows[page * 100:(page + 1) * 100], "totalDataCount": 101})

        events, counts = collect(source(), TODAY, END, get)
        self.assertEqual(101, len(events))
        self.assertEqual(2, counts["pages_collected"])
        self.assertEqual([0, 1], [call[1]["params"]["pageIndex"] for call in calls])
        self.assertTrue(all(call[0] == ENDPOINT and call[1]["allow_redirects"] is False for call in calls))
        self.assertEqual("2026-10-18", calls[0][1]["params"]["startDate"])
        self.assertEqual("2026-10-27", calls[0][1]["params"]["endDate"])

    def test_denial_redirect_and_bad_page_never_return_partial_events(self):
        for status in (301, 302, 401, 403, 500):
            calls = []

            def get(url, **kwargs):
                calls.append(url)
                return Response(payload([usa_match()]), status=status)

            with self.assertRaisesRegex(ValueError, f"HTTP {status}"):
                collect(source(), TODAY, END, get)
            self.assertEqual(1, len(calls))
        with self.assertRaisesRegex(ValueError, "partial page"):
            collect(source(), TODAY, END, lambda *args, **kwargs: Response(
                {"items": [usa_match()], "totalDataCount": 101}))
        with self.assertRaisesRegex(ValueError, "approved endpoint"):
            collect(source(), TODAY, END, lambda *args, **kwargs: Response(
                payload([]), url="https://other.example/matches"))

    def test_second_page_failure_and_duplicate_are_atomic(self):
        rows = []
        for index in range(100):
            row = usa_match()
            row["matchId"] = str(uuid.UUID(int=index + 1))
            rows.append(row)
        for bad_page in (Response(payload([]), status=403),
                         Response({"items": [rows[0]], "totalDataCount": 102}),
                         Response({"items": [rows[0]], "totalDataCount": 101})):
            calls = []

            def get(url, **kwargs):
                calls.append(kwargs["params"]["pageIndex"])
                if len(calls) == 1:
                    return Response({"items": rows, "totalDataCount": 101})
                return bad_page

            with self.assertRaises(ValueError):
                collect(source(), TODAY, END, get)
            self.assertEqual([0, 1], calls)

    def test_empty_result_is_partial_and_fixture_minimized(self):
        events, evidence = collect(source(), TODAY, END,
                                   lambda *args, **kwargs: Response(payload([])))
        self.assertEqual([], events)
        self.assertFalse(evidence["coverage_complete"])
        for filename in ("wxv", "currie-first"):
            text = (FIXTURES / (filename + ".json")).read_text()
            for forbidden in ("players", "imagePath", "referees"):
                self.assertNotIn('"' + forbidden + '"', text)


if __name__ == "__main__":
    unittest.main()
