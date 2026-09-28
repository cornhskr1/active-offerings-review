import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pfl_event_calendar import upcoming_event_links, verified_event


class PFLEventCalendarTests(unittest.TestCase):
    def setUp(self):
        self.cards = upcoming_event_links((ROOT / "tests/fixtures/pfl_upcoming_2026.html").read_text())
        self.detail = (ROOT / "tests/fixtures/pfl_mena11_2026.html").read_text()

    def test_separate_series_and_unclassified_main_event(self):
        self.assertEqual([c["source_id"] for c in self.cards],
                         ["combat-pfl-mena", "combat-pfl-africa"])
        event = verified_event(self.detail, self.cards[0])
        self.assertEqual(event["date"], datetime.date(2026, 10, 2))
        self.assertEqual(event["location"], "Riyadh, KSA")

    def test_detail_cannot_verify_another_series_or_date(self):
        with self.assertRaises(ValueError):
            verified_event(self.detail, self.cards[1])
        with self.assertRaises(ValueError):
            verified_event(self.detail.replace("2026-10-02T00:00:00+03:00", "2026-10-03T00:00:00+03:00", 1), self.cards[0])

    def test_missing_cards_and_foreign_detail_links_fail_closed(self):
        with self.assertRaises(ValueError):
            upcoming_event_links('<div id="nav-upcoming"></div>')
        with self.assertRaises(ValueError):
            upcoming_event_links('<div id="nav-upcoming"><div class="event-hub"><div class="event-card-info"><h3>PFL MENA 11</h3><a href="https://other.example/event/11">Details</a></div></div></div>')


if __name__ == "__main__":
    unittest.main()
