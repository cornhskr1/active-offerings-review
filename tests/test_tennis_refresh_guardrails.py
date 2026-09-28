import unittest

from scripts.tennis_refresh_guardrails import (
    calendar_discovery_issue, challenger_score_event_url, date_range,
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


class CalendarDiscoveryIssueTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
