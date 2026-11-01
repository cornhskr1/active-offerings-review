import datetime
import unittest
from pathlib import Path
from lxml import html

from scripts.ejl_premium_fixture_adapter import next_round, verified_match


SOURCE = {"id":"uefa-soccer-estonia-meistriliiga-premium-liiga-men",
          "sport":"Soccer", "league":"Meistriliiga / Premium Liiga | Men",
          "region":"Estonia", "catalog_terms":["Meistriliiga / Premium Liiga | Men"]}


def page():
    rows=[]
    for round_number in (30,31):
        for i in range(5):
            match_id=round_number*100+i
            day="10.10.2026" if round_number==30 else "13.10.2026"
            rows.append(f'''<li><div class="info"><p>{round_number}. Voor</p></div>
                <div class="event-single-small"><div class="content"><p class="time">{day} kell 14:30</p>
                <div class="teams"><p class="left"><a href="/voistlused/52/team/{i*2+1}?season=2026">Home {i}</a></p>
                <div class="results-container"><span class="result"> - </span></div>
                <p class="right"><a href="/voistlused/52/team/{i*2+2}?season=2026">Away {i}</a></p></div></div>
                <a href="/voistlused/match_info/{match_id}">Details</a></div></li>''')
    return '<html><head><title>A. Le Coq Premium liiga</title></head><body><ul>'+''.join(rows)+'</ul></body></html>'


def detail():
    return '''<html><body><div id="page" class="event-detail"><div class="row"><div class="col-75">
        <div class="head"><div class="teams"><div class="team"><p><a>Home 0</a></p></div>
        <div class="team"><p><a>Away 0</a></p></div></div><div class="info"><ul>
        <li class="type"><a>A. Le Coq Premium liiga</a></li><li>30. voor</li>
        <li class="date"><p>10.10.2026 kell 14:30</p></li>
        <li class="location"><p><a>Stadion</a></p></li></ul></div></div>
        </div></div></div></body></html>'''


class EjlFixtureTests(unittest.TestCase):
    def current(self):
        return (Path(__file__).parent/'fixtures/ejl-round35-20261031.html').read_bytes()

    def parse_current(self, page=None, **kwargs):
        return next_round(self.current() if page is None else page, SOURCE,
                          datetime.date(2026,10,31),
                          observed_at=datetime.datetime(2026,11,1,2,tzinfo=datetime.timezone.utc), **kwargs)

    def test_reviewed_mixed_round_keeps_two_details_and_holds_round36(self):
        rows,count=self.parse_current()
        self.assertEqual((len(rows),count),(2,17))
        events=[verified_match((Path(__file__).parent/f'fixtures/ejl-detail-{r[-1].split("/")[-1]}.html').read_bytes(),r,SOURCE) for r in rows]
        self.assertEqual({e['start_time'] for e in events},{'2026-11-01T10:30:00Z','2026-11-01T12:30:00Z'})
        self.assertEqual({e['location'] for e in events},{'Sportland Arena','Hiiu kunstmurustaadion'})
        self.assertTrue(all(r[1]==35 for r in rows))

    def test_reviewed_round_missing_duplicate_or_relabelled_rows_fail(self):
        for mode in ('missing','duplicate','all_missing','round'):
            doc=html.fromstring(self.current())
            nodes=doc.xpath('//li[div[@class="info"]/p="35. Voor"]')
            if mode=='missing':nodes[0].getparent().remove(nodes[0])
            elif mode=='all_missing':
                for n in nodes:n.getparent().remove(n)
            elif mode=='duplicate':nodes[0].getparent().append(html.fromstring(html.tostring(nodes[0])))
            else:nodes[0].xpath('./div[@class="info"]/p')[0].text='36. Voor'
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.parse_current(html.tostring(doc))

    def test_reviewed_identity_pairing_time_and_result_corruption_fail(self):
        changes=[(b'match_info/186280',b'match_info/186281'),
                 (b'team/6314?season=2026',b'team/11?season=2026'),
                 (b'31.10.2026 kell',b'01.11.2026 kell'),
                 (b'protocol/143981',b'protocol/999999'),
                 (b'3 - 4',b'P - P'),(b'3 - 4',b'-'),
                 (b'35. Voor',b'35. Youth')]
        for before,after in changes:
            self.assertIn(before,self.current())
            with self.subTest(change=before),self.assertRaises(ValueError):
                self.parse_current(self.current().replace(before,after))
        doc=html.fromstring(self.current());n=doc.xpath('//a[@href="/voistlused/match_info/186280"]')[0].getparent().getparent()
        n.xpath('.//span[@class="result"]')[0].text='1 - 0'
        with self.assertRaises(ValueError):self.parse_current(html.tostring(doc))

    def test_future_scores_naive_clock_and_expired_window_fail_closed(self):
        for observed in (datetime.datetime(2026,10,31,10,tzinfo=datetime.timezone.utc),datetime.datetime(2026,11,1)):
            with self.subTest(observed=observed),self.assertRaises(ValueError):
                next_round(self.current(),SOURCE,datetime.date(2026,10,31),observed_at=observed)
        with self.assertRaisesRegex(ValueError,'expired'):
            next_round(self.current(),SOURCE,datetime.date(2026,11,2))

    def test_next_round_and_match_detail(self):
        rows,count=next_round(page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((len(rows),count),(5,10))
        event=verified_match(detail(),rows[0],SOURCE)
        self.assertEqual(event["start_time"],"2026-10-10T11:30:00Z")
        self.assertEqual(event["name"],"Away 0 at Home 0")

    def test_partial_round_and_wrong_competition_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"five-match"):
            next_round(page().replace('30. Voor','31. Voor',1),SOURCE,datetime.date(2026,9,28))
        rows,_=next_round(page(),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"competition"):
            verified_match(detail().replace('A. Le Coq Premium liiga','Esiliiga'),rows[0],SOURCE)


if __name__ == "__main__":
    unittest.main()
