"""An empty venue in the timezone buffer cannot discard healthy window games."""
import datetime as dt
from pathlib import Path
import unittest
from lxml import html
from scripts.georgia_erovnuli_fixture_adapter import candidates, verified_match
from tests.test_georgia_erovnuli_fixture_adapter import SOURCE

FIX=Path(__file__).parent/'fixtures'


class GeorgiaBufferedVenueTests(unittest.TestCase):
    def setUp(self):
        self.page=(FIX/'georgia_current_calendar_nov1_2026.html').read_bytes()
        self.first,self.last=dt.date(2026,11,1),dt.date(2026,11,8)
        self.rows,self.count=candidates(self.page,SOURCE,self.first,self.last)
        self.buffer=next(r for r in self.rows if r[6]=='9418')
        self.detail=(FIX/'georgia_current_9418_2026.html').read_bytes()

    def test_actual_all_eight_details_verify_and_only_seven_located_fixtures_survive(self):
        self.assertEqual((28,8),(self.count,len(self.rows)))
        events=[verified_match((FIX/f'georgia_current_{r[6]}_2026.html').read_bytes(),r,SOURCE,
                              today=self.first,end=self.last) for r in self.rows]
        self.assertEqual(1,events.count(None))
        emitted=[e for e in events if e is not None]
        self.assertEqual(7,len({e['id'] for e in emitted}))
        self.assertTrue(all(e['location'] for e in emitted))
        self.assertEqual('2026-11-08T15:00:00Z',emitted[-1]['start_time'])

    def test_missing_venue_inside_window_still_rejects_entire_source(self):
        with self.assertRaisesRegex(ValueError,'venue missing'):
            candidates(self.page,SOURCE,self.first,dt.date(2026,11,9))
        d=html.fromstring(self.page)
        for e in d.xpath('//div[@data-id="9408"]//span[contains(@class,"f-game-stadium")]'):
            e.getparent().remove(e)
        with self.assertRaisesRegex(ValueError,'venue missing'):
            candidates(html.tostring(d),SOURCE,self.first,self.last)

    def test_calendar_day_after_end_can_still_be_inside_central_window(self):
        d=html.fromstring(self.page)
        t=d.xpath('//div[@data-id="9418"]//span[contains(@class,"grs-time")]//time')[0]
        t.text='09:00'  # November 9 in Tbilisi is still November 8 in Central.
        with self.assertRaisesRegex(ValueError,'venue missing'):
            candidates(html.tostring(d),SOURCE,self.first,self.last)

    def test_absent_naive_or_changed_detail_clock_cannot_prove_exclusion(self):
        for old,new in [(b'2026-11-09T16:00:00Z',b'2026-11-09T16:00:00'),
                        (b'2026-11-09T16:00:00Z',b'2026-11-08T16:00:00Z'),
                        (b'2026-11-09T16:00:00Z',b'unknown')]:
            self.assertIn(old,self.detail)
            with self.subTest(clock=new),self.assertRaises(ValueError):
                verified_match(self.detail.replace(old,new),self.buffer,SOURCE,today=self.first,end=self.last)

    def test_pairing_round_and_venue_mismatch_fail_before_buffer_exclusion(self):
        d=html.fromstring(self.detail)
        for path in ['//h1[contains(@class,"gfh-clubs-inner")]//span[contains(@class,"d-md-inline")]',
                     '//span[contains(@class,"gfh-tour")]']:
            bad=html.fromstring(self.detail);bad.xpath(path)[0].text='Unknown'
            with self.subTest(path=path),self.assertRaises(ValueError):
                verified_match(html.tostring(bad),self.buffer,SOURCE,today=self.first,end=self.last)
        wrong=(*self.buffer[:3],'Invented venue',*self.buffer[4:])
        with self.assertRaises(ValueError):
            verified_match(self.detail,wrong,SOURCE,today=self.first,end=self.last)

    def test_missing_bounds_or_extended_window_never_admits_unlocated_match(self):
        for bounds in [{},{'today':self.first},{'today':self.first,'end':dt.date(2026,11,9)},
                       {'today':self.last,'end':self.first}]:
            with self.subTest(bounds=bounds),self.assertRaises(ValueError):
                verified_match(self.detail,self.buffer,SOURCE,**bounds)


if __name__=='__main__':unittest.main()
