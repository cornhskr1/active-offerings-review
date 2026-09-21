import unittest

from scripts.tennis_refresh_guardrails import calendar_discovery_issue


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
