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

    def fresh_evidence(self):
        cards = upcoming_event_links((ROOT / 'tests/fixtures/pfl_upcoming_20261018.html').read_text())
        details = [(ROOT / ('tests/fixtures/' + name)).read_text() for name in
                   ['pfl_mena12_20261018.html', 'pfl_africa_kigali_20261018.html']]
        return cards, details

    def test_fresh_official_events_recover_as_dates_only(self):
        cards, details = self.fresh_evidence()
        self.assertEqual(['combat-pfl-mena', 'combat-pfl-africa'], [c['source_id'] for c in cards])
        for card, detail, date in zip(cards, details, [datetime.date(2026, 12, 11), datetime.date(2026, 12, 12)]):
            event = verified_event(detail, card)
            self.assertEqual(date, event['date'])
            self.assertNotIn('start_time', event)
            self.assertNotIn('end_time', event)

    def test_next_event_rolls_without_number_or_city_allowlist(self):
        cards, details = self.fresh_evidence()
        # Synthetic future publisher update, not evidence of a real booking.
        card = {**cards[0], 'title': 'PFL MENA 13', 'url': 'https://pflmma.com/event/pflmena-13'}
        detail = details[0].replace('PFL MENA 12', 'PFL MENA 13').replace('pflmena-12', 'pflmena-13')
        detail = detail.replace('2026-12-11', '2027-01-08').replace('FRI DEC 11', 'FRI JAN 8')
        self.assertEqual(datetime.date(2027, 1, 8), verified_event(detail, card)['date'])

    def test_nested_card_title_markup_still_identifies_series(self):
        raw = (ROOT / 'tests/fixtures/pfl_upcoming_20261018.html').read_text()
        changed = raw.replace('PFL MENA 12</h3>', '<span>PFL MENA 12</span></h3>')
        self.assertNotEqual(raw, changed)
        self.assertEqual(upcoming_event_links(raw), upcoming_event_links(changed))

    def test_midnight_placeholder_requires_unambiguous_corroboration(self):
        cards, details = self.fresh_evidence()
        raw = details[0]
        for changed in [raw.replace('FRI DEC 11', 'SAT DEC 12'),
                        raw.replace('event-info-date-large', 'removed'),
                        raw.replace('2026-12-11T00:00:00+03:00', '2026-12-10T00:00:00+03:00'),
                        raw.replace('2026-12-11T00:00:00+03:00', '2026-12-11T01:00:00+03:00'),
                        raw.replace('2026-12-11T00:00:00+03:00', '2026-12-11T00:00:00+02:00'),
                        raw.replace('2026-12-11T00:00:00+03:00', '2026-12-11T00:00:00'),
                        raw + '<p class="event-info-date-large">FRI DEC 11</p>',
                        raw.replace('EventScheduled', 'EventPostponed')]:
            with self.subTest(change=changed[-100:]), self.assertRaises(ValueError):
                verified_event(changed, cards[0])

    def test_colon_normalization_cannot_cross_series_event_or_url(self):
        cards, details = self.fresh_evidence()
        raw = details[1]
        for changed in [raw.replace('PFL Africa Kigali', 'PFL MENA Kigali'),
                        raw.replace('PFL Africa Kigali', 'PFL Africa Johannesburg'),
                        raw.replace('pfl-africa-kigali-2026', 'pfl-africa-kigali-2025'),
                        raw.replace('PFL Africa Kigali', 'PFL Africa Kigali 2'),
                        raw + raw]:
            with self.subTest(change=changed[-100:]), self.assertRaises(ValueError):
                verified_event(changed, cards[1])


if __name__ == "__main__":
    unittest.main()
