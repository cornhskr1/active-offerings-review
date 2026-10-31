"""Current published Italian rounds retain exact scope and fail closed."""
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from italy_volleyball_fixtures import parse_superlega, parse_serie_a1


class ItalyCurrentCalendarsTests(unittest.TestCase):
    def setUp(self):
        self.sources = {s['id']:s for s in json.loads((ROOT/'data/global-schedule-sources.json').read_text())['sources']}
        self.women = (ROOT/'tests/fixtures/italy_serie_a1_live_2026.html').read_bytes()
        self.start, self.end = dt.date(2026,10,30), dt.date(2026,11,6)

    def parse(self, page=None, source=None, end=None):
        return parse_serie_a1(page if page is not None else self.women,
            source or self.sources['volleyball-italy-serie-a1-women'], self.start, end or self.end)

    def test_live_calendar_excludes_a2_and_preserves_published_times_both_legs(self):
        rows = self.parse()
        self.assertEqual(147, len(rows))
        self.assertEqual(147, len({r['id'] for r in rows}))
        self.assertEqual('2026-10-31T17:00:00Z', rows[0]['start_time'])
        self.assertEqual('Granda Volley Cuneo at Cbf Balducci Hr Macerata', rows[0]['name'])
        self.assertEqual('https://www.legavolleyfemminile.it/match-center/748021/', rows[0]['source_endpoint'])
        self.assertEqual('2027-03-14T16:00:00Z', rows[-1]['start_time'])
        self.assertEqual(8, sum(self.start <= dt.date.fromisoformat(r['start_time'][:10]) <= self.end for r in rows))
        self.assertTrue(any('RITORNO' in r['season_stage'] for r in rows))
        self.assertTrue(all(r['league']=='Serie A1 | Women' for r in rows))

    def test_unknown_dates_scope_edition_links_or_club_identity_fail(self):
        for old,new in [(b'31/10/2026',b'unknown-date'), (b'18:00',b'TBD'),
                        (b'2027',b'2028'), (b'LVF A1 Fineco',b'Unknown competition'),
                        (b'https://www.legavolleyfemminile.it/match-center/',b'https://other.test/match-center/'),
                        (b'/club/club/710945/',b'/club/other/710945/')]:
            with self.subTest(change=new), self.assertRaises(ValueError):
                self.assertIn(old,self.women)
                self.parse(self.women.replace(old,new,1))
        for source in [{**self.sources['volleyball-italy-serie-a1-women'],'season_code':'2027-2028'},
                       {**self.sources['volleyball-italy-serie-a1-women'],'catalog_terms':['Serie A2 | Women']}]:
            with self.assertRaises(ValueError):self.parse(source=source)

    def test_missing_fixture_round_duplicate_game_and_expired_window_fail(self):
        d=html.fromstring(self.women);first=d.xpath('//table')[0];first.getparent().remove(first)
        with self.assertRaisesRegex(ValueError,'round incomplete'):self.parse(html.tostring(d))
        d=html.fromstring(self.women)
        for t in d.xpath('//table'):
            if 'LVF A1 Fineco 7a Giornata' in t.text_content():t.getparent().remove(t)
        with self.assertRaisesRegex(ValueError,'missing round'):self.parse(html.tostring(d))
        d=html.fromstring(self.women);d.append(html.fromstring(html.tostring(d.xpath('//table')[0])))
        with self.assertRaisesRegex(ValueError,'duplicate game'):self.parse(html.tostring(d))
        with self.assertRaisesRegex(ValueError,'horizon ended'):self.parse(end=dt.date(2027,3,15))

    def test_superlega_heading_can_change_markup_without_changing_round_identity(self):
        page=(ROOT/'tests/fixtures/italy_superlega_2026.html').read_text()
        page=page.replace('id="HeadCol"','class="GiornataA"')
        source=self.sources['volleyball-italy-superlega']
        self.assertEqual(66,len(parse_superlega(page,source,self.start,self.end)))
        with self.assertRaises(ValueError):
            parse_superlega(page.replace('1ª Giornata Andata','2ª Giornata Andata',1),source,self.start,self.end)


if __name__=='__main__':unittest.main()
