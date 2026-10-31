import copy
import json
import unittest
from pathlib import Path
from lxml import html
from scripts.uae_pro_league_fixtures import discover_league_competition,parse_league_matches

FIXTURES=Path(__file__).parent/'fixtures'
SOURCE=dict(id='soccer-afc-united-arab-emirates-uae-pro-league-men',sport='Soccer',league='UAE Pro League | Men',region='United Arab Emirates',catalog_terms=['UAE Pro League | Men'],endpoint='https://www.uaeproleague.ae/en/fixtures')


class UaeLeagueFixturesTests(unittest.TestCase):
    def setUp(self):
        self.directory=(FIXTURES/'uae-league-directory-20261006.html').read_text()
        self.payload=json.loads((FIXTURES/'uae-league-records-20261006.json').read_text())

    def test_selects_league_from_season_directory_while_homepage_default_is_cup(self):
        self.assertEqual('b8785e20-745f-11f1-82d0-f556dfffd44c',discover_league_competition(self.directory,SOURCE))
        with self.assertRaises(ValueError):
            discover_league_competition(self.directory.replace('ADNOC PRO LEAGUE','ADIB Cup'),SOURCE)

    def test_published_records_skip_completed_and_hold_missing_dates(self):
        events,held,completed,total=parse_league_matches(self.payload,SOURCE)
        self.assertEqual((2,1,1,4),(len(events),held,completed,total))
        self.assertEqual('United at Al Dhafra',events[0]['name'])
        self.assertEqual('2026-10-16T13:05:00Z',events[0]['start_time'])
        self.assertEqual('ROUND 6',events[0]['season_stage'])
        self.assertTrue(events[0]['source_endpoint'].startswith('https://www.uaeproleague.ae/en/fixtures/'))

    def test_cup_and_u23_rows_cannot_borrow_league_approval(self):
        for competition in ['ADIB Cup','Pro League U23']:
            p=copy.deepcopy(self.payload);p['html']=p['html'].replace('alt="ADNOC PRO LEAGUE"',f'alt="{competition}"',1)
            with self.subTest(competition=competition),self.assertRaisesRegex(ValueError,'another competition'):
                parse_league_matches(p,SOURCE)

    def test_wrong_edition_and_catalog_scope_rejected(self):
        with self.assertRaisesRegex(ValueError,'edition'):
            discover_league_competition(self.directory.replace('2026/2027','2025/2026'),SOURCE)
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            discover_league_competition(self.directory,dict(SOURCE,catalog_terms=['ADIB Cup']))

    def test_changed_date_and_clock_follow_publisher_record(self):
        p=copy.deepcopy(self.payload);p['html']=p['html'].replace('17:05','18:05')
        # Whitespace is presentation-dependent; target the normalized record's full day.
        import re
        p['html']=re.sub(r'Fri\s+16\s+Oct\s+2026','Sat 17 Oct 2026',p['html'])
        events,_,_,_=parse_league_matches(p,SOURCE)
        self.assertEqual('2026-10-17T14:05:00Z',events[0]['start_time'])

    def test_missing_clock_and_duplicate_timed_identity_rejected(self):
        with self.assertRaisesRegex(ValueError,'kickoff'):
            parse_league_matches({'html':self.payload['html'].replace('17:05','no time')},SOURCE)
        from lxml import html
        doc=html.fromstring('<main>'+self.payload['html']+'</main>')
        timed=doc.xpath('//div[@id="matchList_1lu4oerqdz5maz39qhenfzsic"]')[0]
        with self.assertRaisesRegex(ValueError,'duplicate'):
            parse_league_matches({'html':self.payload['html']+html.tostring(timed,encoding='unicode')},SOURCE)

    def ticket_payload(self, change=None):
        payload=json.loads((FIXTURES/'uae-league-ticket-records-20261031.json').read_text())
        if change:
            doc=html.fromstring('<main>'+payload['html']+'</main>')
            change(doc.xpath('//div[@id="matchList_d1h3pu0uc29oev0lc5gipzhuc"]/div[@class="upcomingMatches__right"]')[0])
            payload['html']=html.tostring(doc,encoding='unicode')
        return payload

    def test_current_ticket_cards_preserve_exact_official_match_evidence(self):
        events,held,completed,total=parse_league_matches(self.ticket_payload(),SOURCE)
        self.assertEqual((4,1,0,5),(len(events),held,completed,total))
        self.assertEqual(['Kalba at Al Dhafra','Khorfakkan at Hatta','Shabab AlAhli at Sharjah','Hatta at Al Wasl'],[e['name'] for e in events])
        self.assertEqual(['2026-11-07T12:55:00Z','2026-11-07T15:30:00Z','2026-11-07T15:30:00Z','2026-11-19T12:45:00Z'],[e['start_time'] for e in events])
        self.assertEqual('Hamdan Bin Zayed Stadium',events[0]['location'])
        self.assertEqual('https://www.uaeproleague.ae/en/fixtures/22e17f7a-7604-11f1-b32b-0289588efdb9',events[0]['source_endpoint'])
        self.assertEqual('uae-league-d1h3pu0uc29oev0lc5gipzhuc',events[0]['id'])

    def test_ticket_cannot_replace_missing_or_duplicate_official_detail(self):
        def remove(right):
            right.remove(right.xpath('./a[not(@class)]')[0])
        def duplicate(right):
            right.append(copy.deepcopy(right.xpath('./a[not(@class)]')[0]))
        def disguised_duplicate(right):
            node=copy.deepcopy(right.xpath('./a[not(@class)]')[0])
            node.set('class','btn--ticket');node.text='Buy Tickets';right.append(node)
        for change in (remove,duplicate,disguised_duplicate):
            with self.subTest(change=change.__name__),self.assertRaisesRegex(ValueError,'detail identity'):
                parse_league_matches(self.ticket_payload(change),SOURCE)

    def test_external_or_malformed_detail_identity_rejected_even_with_ticket(self):
        original='https://www.uaeproleague.ae/en/fixtures/22e17f7a-7604-11f1-b32b-0289588efdb9'
        for link in (original.replace('https:','http:'),original.replace('www.uaeproleague.ae','example.com'),
                     original.replace('www.uaeproleague.ae','www.uaeproleague.ae:8443'),original+'?match=other',
                     original+'#other',original.replace('22e17f7a','22e-7f7a'),original.replace('/fixtures/','/clubs/')):
            def change(right):right.xpath('./a[not(@class)]')[0].set('href',link)
            with self.subTest(link=link),self.assertRaisesRegex(ValueError,'detail identity'):
                parse_league_matches(self.ticket_payload(change),SOURCE)

    def test_unrecognized_extra_links_are_not_silently_discarded(self):
        for attribute,value in (('class','btn--match-report'),('href','https://example.com/tickets'),('href','http://dubai.platinumlist.net/event-tickets/109426/game')):
            def change(right):right.xpath('./a[@class]')[0].set(attribute,value)
            with self.subTest(attribute=attribute,value=value),self.assertRaisesRegex(ValueError,'detail identity'):
                parse_league_matches(self.ticket_payload(change),SOURCE)

    def test_ticket_cards_cannot_borrow_cup_or_u23_scope(self):
        for competition in ('ADIB Cup','Pro League U23'):
            payload=self.ticket_payload();payload['html']=payload['html'].replace('alt="ADNOC PRO LEAGUE"',f'alt="{competition}"',1)
            with self.subTest(competition=competition),self.assertRaisesRegex(ValueError,'another competition'):
                parse_league_matches(payload,SOURCE)


if __name__=='__main__':unittest.main()
