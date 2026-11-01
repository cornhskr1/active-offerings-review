"""Exact November 1 post-start result identities; no provider requests."""
import copy
import datetime as dt
from pathlib import Path
import unittest
from lxml import html
from scripts.ejl_premium_fixture_adapter import next_round, verified_match, ROUND35

FIXTURES=Path(__file__).parent/'fixtures'
SOURCE={'id':'uefa-soccer-estonia-meistriliiga-premium-liiga-men','sport':'Soccer',
        'league':'Meistriliiga / Premium Liiga | Men','region':'Estonia',
        'catalog_terms':['Meistriliiga / Premium Liiga | Men']}
NOW=dt.datetime(2026,11,1,15,1,tzinfo=dt.timezone.utc)


class ScoredRoundTests(unittest.TestCase):
    def page(self):return (FIXTURES/'ejl-round35-scored-20261101.html').read_bytes()

    def parse(self,page=None,day=dt.date(2026,11,1),now=NOW):
        return next_round(self.page() if page is None else page,SOURCE,day,now)

    def test_exact_scored_round_emits_nothing_and_keeps_later_round_held(self):
        rows,count=self.parse();self.assertEqual([],rows);self.assertEqual(15,count)
        old=(FIXTURES/'ejl-round35-20261031.html').read_bytes()
        rows,_=self.parse(old,now=dt.datetime(2026,11,1,2,tzinfo=dt.timezone.utc))
        self.assertEqual({'186279','186280'},{r[-1].rsplit('/',1)[-1] for r in rows})

    def test_both_primary_detail_heads_independently_bind_protocol_pairing_clock_venue(self):
        for key,protocol,venue in [('186279','143983','Hiiu kunstmurustaadion'),('186280','144017','Sportland Arena')]:
            page=(FIXTURES/f'ejl-scored-detail-{key}.html').read_bytes();d=html.fromstring(page)
            self.assertEqual(['/voistlused/protocol/'+protocol],d.xpath('//div[@class="actions"]/a/@href'))
            clock,home,away,_=ROUND35[key];fixture=(dt.date(2026,11,1),35,clock[-5:],[home[1],away[1]],'/voistlused/match_info/'+key)
            self.assertEqual(venue,verified_match(page,fixture,SOURCE)['location'])

    def test_new_protocol_score_tag_and_identity_changes_fail(self):
        changes=[(b'protocol/143983',b'protocol/144017'),(b'protocol/144017',b'protocol/999999'),
                 (b'1 - 0',b'1 - 1'),(b'2 - 0',b'P - P'),(b'match_info/186280',b'match_info/186281'),
                 (b'01.11.2026 kell',b'02.11.2026 kell')]
        for old,new in changes:
            self.assertTrue(old in self.page(),old)
            with self.subTest(old=old),self.assertRaises(ValueError):self.parse(self.page().replace(old,new))
        d=html.fromstring(self.page());a=d.xpath('//a[@href="/voistlused/protocol/143983"]')[0];a.tag='span'
        with self.assertRaises(ValueError):self.parse(html.tostring(d))

    def test_missing_duplicate_relabelled_or_changed_clubs_fail(self):
        for mode in ('missing','duplicate','round','club'):
            d=html.fromstring(self.page());n=d.xpath('//a[@href="/voistlused/match_info/186279"]/ancestor::li[1]')[0]
            if mode=='missing':n.getparent().remove(n)
            elif mode=='duplicate':n.getparent().append(copy.deepcopy(n))
            elif mode=='round':n.xpath('./div[contains(@class,"info")]/p')[0].text='36. Voor'
            else:n.xpath('.//p[contains(@class,"left")]/a')[0].set('href','/voistlused/52/team/999?season=2026')
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.parse(html.tostring(d))

    def test_future_scores_naive_clock_and_unreviewed_dates_fail(self):
        for now in (NOW.replace(tzinfo=None),dt.datetime(2026,11,1,11,tzinfo=dt.timezone.utc)):
            with self.subTest(now=now),self.assertRaises(ValueError):self.parse(now=now)
        for day in (dt.date(2026,10,31),dt.date(2026,11,2)):
            with self.subTest(day=day),self.assertRaises(ValueError):self.parse(day=day)


if __name__=='__main__':unittest.main()
