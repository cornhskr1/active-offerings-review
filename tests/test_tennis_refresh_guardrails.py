import unittest

from scripts.tennis_refresh_guardrails import (
    calendar_discovery_issue, challenger_calendar_card_dates,
    challenger_score_event_url, date_range,
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
