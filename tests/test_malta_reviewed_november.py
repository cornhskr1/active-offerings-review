"""Exact Malta senior cards stay isolated from lower divisions and U17 games."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from dynamic_league_fixture_adapter import parse_malta_tickets


class MaltaReviewedNovemberTests(unittest.TestCase):
    def setUp(self):
        self.source={'id':'uefa-soccer-malta-maltese-premier-league-men',
            'sport':'Soccer','league':'Maltese Premier League | Men','region':'Malta',
            'endpoint':'https://tickets.mfa.com.mt/','catalog_terms':['Maltese Premier League | Men']}
        self.page=(ROOT/'tests/fixtures/malta_senior_nov1_2026.html').read_bytes()
        self.today=dt.date(2026,11,1)

    def parse(self,page=None,source=None,today=None):
        return parse_malta_tickets(self.page if page is None else page,
            self.source if source is None else source,today=today or self.today)

    def test_exact_two_senior_cards_and_separate_detail_publications(self):
        rows=self.parse()
        self.assertEqual(['Valletta FC at Floriana FC','Marsaxlokk FC at Gzira United FC'],[r['name'] for r in rows])
        self.assertEqual(['2026-11-01T14:30:00Z','2026-11-01T18:00:00Z'],[r['start_time'] for r in rows])
        self.assertEqual(2,len({r['id'] for r in rows}))
        self.assertTrue(all(r['location']=='Tony Bezzina Stadium' for r in rows))
        for name,home,away,clock in [('floriana_valletta','Floriana FC','Valletta FC','15:30'),
                                    ('gzira_marsaxlokk','Gzira United FC','Marsaxlokk FC','19:00')]:
            d=html.fromstring((ROOT/f'tests/fixtures/malta_{name}_nov1_2026.html').read_bytes())
            self.assertEqual([f'Tickets — {home} - {away} - VBet Malta Premier League 2026/2027'],d.xpath('//title/text()'))
            text=' '.join(' '.join(d.itertext()).split())
            self.assertIn('Sunday November 01, 2026 at '+clock,text)
            self.assertIn('Tony Bezzina Stadium',text)

    def test_changed_identity_pairing_date_kickoff_venue_and_link_fail(self):
        for old,new in [(b'floriana-fc-vs-valletta-fc-2026-11-01',b'floriana-fc-vs-valletta-fc-2026-11-02'),
                        (b'Floriana FC',b'Floriana U17'),(b'NOV',b'DEC'),(b'>01<',b'>02<'),
                        (b'15:30',b'00:00'),(b'Tony Bezzina Stadium',b'Unknown venue'),
                        (b'href="/matches/floriana',b'href="https://foreign.test/matches/floriana')]:
            self.assertIn(old,self.page)
            with self.subTest(change=new),self.assertRaises(ValueError):self.parse(self.page.replace(old,new,1))

    def test_missing_duplicate_and_extra_senior_card_fail(self):
        for action in ['missing','duplicate','extra']:
            d=html.fromstring(self.page);card=d.xpath('//article')[0]
            if action=='missing':card.getparent().remove(card)
            else:
                other=copy.deepcopy(card)
                if action=='extra':other.xpath('.//h3/a')[0].set('href','/matches/unreviewed')
                card.getparent().append(other)
            with self.subTest(action=action),self.assertRaises(ValueError):self.parse(html.tostring(d))

    def test_mixed_group_relabelled_competition_and_hidden_identity_fail(self):
        for old,new in [(b'VBet Malta Premier League 2026/2027',b'Unknown competition'),
                        (b'2026/2027',b'2027/2028'),(b'id="upcoming"',b'id="other"')]:
            with self.subTest(change=new),self.assertRaises(ValueError):self.parse(self.page.replace(old,new,1))
        d=html.fromstring(self.page);cards=d.xpath('//article');cards[2].xpath('.//h3/a')[0].set('href',cards[0].xpath('.//h3/a/@href')[0])
        with self.assertRaises(ValueError):self.parse(html.tostring(d))

    def test_youth_and_lower_division_clocks_cannot_supply_senior_kickoff(self):
        self.assertIn(b'00:00',self.page)
        self.assertEqual(2,len(self.parse(self.page.replace(b'00:00',b'15:30'))))
        with self.assertRaises(ValueError):self.parse(self.page.replace(b'15:30 - Tony',b'TBD - Tony',1))

    def test_expired_review_catalog_and_foreign_publisher_fail(self):
        with self.assertRaises(ValueError):self.parse(today=dt.date(2026,11,2))
        for patch in [{'endpoint':'https://foreign.test/'},{'catalog_terms':['BOV Challenge League | Men']},
                      {'id':'other'},{'league':'Women U17'}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):self.parse(source={**self.source,**patch})


if __name__=='__main__':unittest.main()
