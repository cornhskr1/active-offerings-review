import unittest
import datetime

from scripts.tennis_refresh_guardrails import (
    calendar_discovery_issue, challenger_calendar_card_dates, challenger_degradation,
    challenger_score_event_url, date_range,
    publisher_access_issue,
    schedule_source_warning,
)


class AtpChallengerCalendarTests(unittest.TestCase):
    def test_cross_month_score_page_date_with_comma(self):
        start, end = date_range("Columbus, United States | 28 September - 4 October, 2026")
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-09-28", "2026-10-04"))

    def test_score_tabs_resolve_to_one_event(self):
        urls = [
            "https://www.atptour.com/en/scores/current-challenger/columbus/9194/daily-schedule?day=1",
            "https://www.atptour.com/en/scores/current-challenger/columbus/9194/draws",
        ]
        self.assertEqual(
            {challenger_score_event_url(url) for url in urls},
            {"https://www.atptour.com/en/scores/current-challenger/columbus/9194/live-scores"},
        )
        self.assertIsNone(challenger_score_event_url("https://www.atptour.com/en/scores/current-challenger"))

    def test_calendar_card_uses_publisher_month_year(self):
        dates = challenger_calendar_card_dates(
            "Columbus Challenger | 28 September - 4 October, Indoor Challenger 75",
            "September, 2026 (24 events)", 2026)
        self.assertEqual(tuple(d.isoformat() for d in dates), ("2026-09-28", "2026-10-04"))

    def test_missing_year_or_multiple_cards_fail_closed(self):
        card = "Columbus Challenger | 28 September - 4 October"
        self.assertEqual(challenger_calendar_card_dates(card, "September events", 2026), (None, None))
        self.assertEqual(challenger_calendar_card_dates(card, "September, 2025", 2026), (None, None))
        multiple = card + " | Porto Open 28 September - 4 October"
        self.assertEqual(challenger_calendar_card_dates(multiple, "September, 2026", 2026), (None, None))


class CalendarDiscoveryIssueTests(unittest.TestCase):
    def test_cloudflare_block_is_source_error_not_calendar_data(self):
        self.assertEqual(publisher_access_issue(403, "Sorry, you have been blocked"), "PUBLISHER_HTTP_403")
        self.assertEqual(publisher_access_issue(200, "Sorry, you have been blocked"), "PUBLISHER_ACCESS_BLOCKED")
        self.assertIsNone(calendar_discovery_issue({"ok":False,"error":"PUBLISHER_HTTP_403"},False))

    def test_valid_empty_week_does_not_fail(self):
        health = {
            "ok": True,
            "candidate_tournament_links": 140,
            "dated_candidate_links": 140,
            "overlapping_candidate_links": 0,
        }
        self.assertIsNone(calendar_discovery_issue(health, False))

    def test_confirmed_overlap_without_event_fails(self):
        health = {
            "ok": True,
            "candidate_tournament_links": 140,
            "dated_candidate_links": 140,
            "overlapping_candidate_links": 1,
        }
        self.assertEqual(
            calendar_discovery_issue(health, False),
            "OVERLAP_WITHOUT_EVENT",
        )

    def test_unresolved_calendar_dates_fail_closed(self):
        health = {
            "ok": True,
            "candidate_tournament_links": 140,
            "dated_candidate_links": 0,
            "overlapping_candidate_links": 0,
        }
        self.assertEqual(
            calendar_discovery_issue(health, False),
            "DATES_UNRESOLVED",
        )

    def test_existing_event_passes(self):
        health = {
            "ok": True,
            "candidate_tournament_links": 140,
            "dated_candidate_links": 140,
            "overlapping_candidate_links": 1,
        }
        self.assertIsNone(calendar_discovery_issue(health, True))


class ScheduleSourceHealthTests(unittest.TestCase):
    def test_unresolved_challenger_dates_degrade_only_that_lane(self):
        health = {"ok":True,"candidate_tournament_links":100,
                  "dated_candidate_links":0,"overlapping_candidate_links":0,
                  "current_page":{"error":"PUBLISHER_HTTP_403"}}
        warning = challenger_degradation(health,False)
        self.assertIn("dates unresolved",warning)
        self.assertIsNone(challenger_degradation(health,True))
        payload = {"generated_at":"2026-09-28T18:50:00+00:00",
                   "quality_gate":{"passed":True,"complete":False,
                                   "degraded_lanes":[{"tour_id":"atp-challenger","reason":warning}]}}
        now = datetime.datetime(2026,9,28,19,tzinfo=datetime.timezone.utc)
        self.assertEqual(warning,schedule_source_warning(payload,["atp-challenger"],now))
        self.assertIsNone(schedule_source_warning(payload,["itf-men"],now))

    def test_overlap_and_archive_gaps_remain_visible(self):
        self.assertIn("overlapping tournament",challenger_degradation(
            {"ok":True,"overlapping_candidate_links":1},False))
        self.assertIn("archive",challenger_degradation(
            {"ok":False,"archive_fallback":{"calendar_overlap_mentions":1}},False))

    def test_partial_refresh_only_blocks_the_degraded_identity(self):
        now = datetime.datetime(2026, 9, 28, 12, tzinfo=datetime.timezone.utc)
        payload = {
            "generated_at": "2026-09-28T11:30:00+00:00",
            "quality_gate": {"passed": True, "complete": False, "degraded_lanes": [
                {"tour_id": "atp-challenger", "reason": "ATP Challenger publisher access blocked; manual verification required"}
            ]},
        }
        self.assertIn("blocked", schedule_source_warning(payload, ["atp-challenger"], now))
        for tour_id in ("itf-men", "itf-women", "utr-men", "utr-women"):
            with self.subTest(tour_id=tour_id):
                self.assertIsNone(schedule_source_warning(payload, [tour_id], now))
        self.assertIn("72 hours", schedule_source_warning({**payload,
            "generated_at": "2026-09-16T11:30:00+00:00"}, ["itf-men"], now))


if __name__ == "__main__":
    unittest.main()
