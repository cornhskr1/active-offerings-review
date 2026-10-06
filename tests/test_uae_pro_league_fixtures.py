import copy
import json
import unittest
from pathlib import Path
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


if __name__=='__main__':unittest.main()
