import datetime
import unittest
from pathlib import Path
from lxml import html

from scripts.nzs_prvaliga_fixture_adapter import next_round, verified_match


SOURCE = {"id":"uefa-soccer-slovenia-slovenian-prvaliga-men", "sport":"Soccer",
          "league":"Slovenian PrvaLiga | Men", "region":"Slovenia",
          "catalog_terms":["Slovenian PrvaLiga | Men"]}


def page():
    rows=[]
    for i in range(5):
        day="2026-10-10" if i<3 else "2026-10-11"
        clock="15:00" if i!=1 else "17:30"
        rows.append(f'''<tr class="match-tbody-tr"><td><div class="upcoming-match-date">
        <time class="date" datetime="{day}">{day}</time>
        <time class="time" datetime="{clock}">{clock}</time></div></td>
        <td><h5 class="match-team-name">Home {i}</h5><h5 class="match-team-name">Away {i}</h5></td>
        <td><strong class="match-location">Stadion {i}</strong></td>
        <td><div class="match-category">Prva liga Telemach</div></td>
        <td>Krog 11</td><td><a href="/klubi/moski/prva-liga-telemach/tekme/match-{i}-1snl2627-{day}-{clock.replace(':','')}00">Podrobnosti</a></td></tr>''')
    return '<html><body>2026/2027 <table>'+''.join(rows)+'</table></body></html>'


def detail():
    return '''<html><body><div class="cover-competition">PRVA LIGA TELEMACH 26/27 11. krog</div>
    <div class="cover-match-data-team"><span class="team-name"><a>Home 0</a></span></div>
    <div class="cover-match-data-team"><span class="team-name"><a>Away 0</a></span></div>
    <div class="cover-match-info"><div class="cover-match-info-date"><span>10.10.2026, 15:00</span></div>
    Stadion 0</div></body></html>'''


class NzsPrvaligaFixtureTests(unittest.TestCase):
    def current(self):
        return (Path(__file__).parent/'fixtures/nzs-round14-20261031.html').read_bytes()

    def parse_current(self, page=None):
        return next_round(self.current() if page is None else page,SOURCE,datetime.date(2026,10,31),
            observed_at=datetime.datetime(2026,11,1,3,tzinfo=datetime.timezone.utc))

    def test_reviewed_round_keeps_three_verified_fixtures_not_later_placeholders(self):
        rows,count=self.parse_current()
        self.assertEqual((len(rows),count),(3,20))
        events=[verified_match((Path(__file__).parent/f'fixtures/nzs-detail-{i}-20261031.html').read_bytes(),r,SOURCE) for i,r in enumerate(rows)]
        self.assertEqual([e['start_time'] for e in events],['2026-11-01T14:00:00Z','2026-11-01T16:30:00Z','2026-11-02T16:00:00Z'])
        self.assertTrue(all(r[1]==14 for r in rows))

    def test_partial_duplicate_relabelled_and_missing_entire_round_fail(self):
        for mode in ('missing','duplicate','relabelled','all_missing'):
            doc=html.fromstring(self.current());nodes=[n for n in doc.xpath('//tr') if 'Krog 14' in ' '.join(n.text_content().split())]
            if mode=='missing':nodes[0].getparent().remove(nodes[0])
            elif mode=='duplicate':nodes[0].getparent().append(html.fromstring(html.tostring(nodes[0])))
            elif mode=='all_missing':
                for n in nodes:n.getparent().remove(n)
            else:
                cell=nodes[0].xpath('./td')[4];cell.clear();cell.text='Krog 15'
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.parse_current(html.tostring(doc))

    def test_changed_identity_league_pairing_time_venue_and_scores_fail(self):
        changes=[(b'dns-mura-nk-brinje-grosuplje-1snl2627-2026-11-01-150000',b'dns-mura-nk-brinje-grosuplje-1snl2627-2026-11-01-150001'),
            (b'>Brinje Grosuplje</h5>',b'>Youth</h5>'),(b'datetime="15:00"',b'datetime="16:00"'),
            (b'>Mestni stadion Fazanerija</strong>',b'>Other venue</strong>'),
            (b'>Prva liga Telemach</span>',b'>Pokal</span>'),(b'5 : 0 (2 : 0)',b'P : P'),(b'5 : 0 (2 : 0)',b'-')]
        for before,after in changes:
            self.assertIn(before,self.current())
            with self.subTest(change=before),self.assertRaises(ValueError):self.parse_current(self.current().replace(before,after))
        doc=html.fromstring(self.current());row=doc.xpath('//strong[@class="match-score"]')[0].getparent().getparent().getparent()
        link=row.xpath('.//div[@class="actions"]/a')[0]
        link.getparent().append(html.fromstring(html.tostring(link)))
        with self.assertRaises(ValueError):self.parse_current(html.tostring(doc))

    def test_future_scores_naive_clock_and_expired_window_fail(self):
        for observed in (datetime.datetime(2026,10,31,10,tzinfo=datetime.timezone.utc),datetime.datetime(2026,11,1)):
            with self.subTest(observed=observed),self.assertRaises(ValueError):
                next_round(self.current(),SOURCE,datetime.date(2026,10,31),observed_at=observed)
        with self.assertRaisesRegex(ValueError,'expired'):next_round(self.current(),SOURCE,datetime.date(2026,11,3))

    def test_changed_detail_pairing_kickoff_or_venue_remains_rejected(self):
        rows,_=self.parse_current();data=(Path(__file__).parent/'fixtures/nzs-detail-0-20261031.html').read_bytes()
        for before,after in [(b'>Mura</a>',b'>Other</a>'),(b'01.11.2026, 15:00',b'01.11.2026, 16:00'),(b'Mestni stadion Fazanerija',b'Other stadium')]:
            self.assertIn(before,data)
            with self.subTest(change=before),self.assertRaises(ValueError):verified_match(data.replace(before,after),rows[0],SOURCE)

    def test_complete_next_round_and_detail_confirmation(self):
        rows,count=next_round(page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((len(rows),count),(5,5))
        event=verified_match(detail(),rows[0],SOURCE)
        self.assertEqual(event["start_time"],"2026-10-10T13:00:00Z")
        self.assertEqual(event["name"],"Away 0 at Home 0")

    def test_incomplete_round_and_wrong_competition_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"five-match"):
            next_round(page().replace('Krog 11','Krog 12',1),SOURCE,datetime.date(2026,9,28))
        rows,_=next_round(page(),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"competition"):
            verified_match(detail().replace('PRVA LIGA TELEMACH','POKAL'),rows[0],SOURCE)


if __name__ == "__main__":
    unittest.main()
