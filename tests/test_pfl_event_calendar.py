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

    def test_published_mena12_date_corroborates_overnight_end_stamp(self):
        raw=(ROOT/'tests/fixtures/pfl-mena12-20261006.html').read_text()
        card={'source_id':'combat-pfl-mena','title':'PFL MENA 12','url':'https://pflmma.com/event/pflmena-12'}
        event=verified_event(raw,card)
        self.assertEqual(datetime.date(2026,12,11),event['date'])
        for altered in [raw.replace('FRI DEC 11','SAT DEC 12'),raw.replace('event-info-date-large','removed'),raw.replace('EventScheduled','EventCancelled'),raw.replace('2026-12-12T','2026-12-13T')]:
            with self.subTest(altered=altered[-70:]),self.assertRaises(ValueError):
                verified_event(altered,card)

    def test_ambiguous_duplicate_event_is_not_verified(self):
        with self.assertRaisesRegex(ValueError,'uniquely'):
            verified_event(self.detail+self.detail,self.cards[0])


if __name__ == "__main__":
    unittest.main()
