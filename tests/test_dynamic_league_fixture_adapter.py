import unittest
import datetime
from pathlib import Path

from scripts.dynamic_league_fixture_adapter import (
    affa_latest_notice_url,
    parse_affa_notice,
    parse_bih_fixtures,
    parse_malta_tickets,
)


class DynamicLeagueAdapterTests(unittest.TestCase):
    def test_affa_discovers_latest_notice(self):
        page = '<html><body><a href="/index.php/news/misli-premyer-liqas-vii-turun-tyinatlar/99999">Misli Premyer Liqası: VII turun təyinatları</a></body></html>'.encode("utf-8")
        url = affa_latest_notice_url(page, "https://www.affa.az/index.php?lang=az&r=77")
        self.assertIn("/news/misli-premyer-liqas-vii-turun-tyinatlar/", url)

    def test_affa_notice_parses_timed_fixture(self):
        source = {
            "id":"uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men",
            "sport":"Soccer","league":"Azerbaijan Premier League (APL) | Men","region":"Azerbaijan",
            "catalog_terms":["Azerbaijan Premier League (APL) | Men"],"endpoint":"https://example.test"
        }
        page = """<html><body><div class="news_item"><h1>Misli Premyer Liqası: VII turun təyinatları</h1>
        <span class="date">Dərc olundu: <span>01.10.2026</span></span>
        <div class="texts mb3"><p>3 oktyabr</p><p>17:00. “Araz-Naxçıvan” - “İmişli”</p></div></div></body></html>"""
        events = parse_affa_notice(page, source)
        self.assertEqual(1, len(events))
        self.assertEqual("2026-10-03T13:00:00Z", events[0]["start_time"])

    def test_bih_parses_timed_rows(self):
        source = {
            "id":"uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men",
            "sport":"Soccer","league":"Premier League of Bosnia and Herzegovina | Men","region":"Bosnia and Herzegovina",
            "catalog_terms":["Premier League of Bosnia and Herzegovina | Men"],"endpoint":"https://example.test"
        }
        page = """<html><body><h1>Wwin League BH</h1><table>
        <tr><td>18.09.2026. 20:00 FK ŽELJEZNIČAR - NK ČELIK</td></tr></table></body></html>"""
        events = parse_bih_fixtures(page, source)
        self.assertEqual(1, len(events))
        self.assertEqual("2026-09-18T18:00:00Z", events[0]["start_time"])

    def affa_source(self):
        return dict(id='uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men',
            sport='Soccer',league='Azerbaijan Premier League (APL) | Men',region='Azerbaijan',
            catalog_terms=['Azerbaijan Premier League (APL) | Men'],endpoint='https://example.test')

    def test_real_affa_separate_pairing_and_stadium_clock_blocks(self):
        page=(Path(__file__).parent / 'fixtures/affa-appointments-20260917.html').read_bytes()
        events=parse_affa_notice(page,self.affa_source(),review_date=datetime.date(2026,9,17))
        self.assertEqual(6,len(events))
        self.assertEqual('Neftçi at Qəbələ',events[0]['name'])
        self.assertEqual('2026-09-18T13:30:00Z',events[0]['start_time'])
        self.assertEqual('2026-09-20T15:00:00Z',events[-1]['start_time'])

    def test_affa_past_notice_remains_an_actionable_failure(self):
        page=(Path(__file__).parent / 'fixtures/affa-appointments-20260917.html').read_bytes()
        with self.assertRaisesRegex(ValueError,'only past fixtures'):
            parse_affa_notice(page,self.affa_source(),review_date=datetime.date(2026,10,6))

    def test_affa_corrupt_metadata_does_not_damage_intact_fixture_records(self):
        page=(Path(__file__).parent / 'fixtures/affa-appointments-20260917.html').read_bytes()
        page=b'<html><head><meta name="description" content="broken \xc9"></head><body>'+page+b'</body></html>'
        self.assertEqual(6,len(parse_affa_notice(page,self.affa_source())))

    def test_affa_damaged_team_and_missing_clock_are_held(self):
        page=(Path(__file__).parent / 'fixtures/affa-appointments-20260917.html').read_text()
        for changed in [page.replace('“Neftçi”','“Neft\ufffdçi”'),page.replace('Qəbələ şəhər stadionu, 17:30','Qəbələ şəhər stadionu, TBC')]:
            with self.subTest(changed=changed[:40]),self.assertRaises(ValueError):
                parse_affa_notice(changed,self.affa_source())

    def test_affa_reads_publication_year(self):
        page=(Path(__file__).parent / 'fixtures/affa-appointments-20260917.html').read_text().replace('17.09.2026','17.09.2027')
        self.assertTrue(all(e['start_time'].startswith('2027-') for e in parse_affa_notice(page,self.affa_source())))

    def test_bih_pairing_follows_publisher_order_and_year(self):
        source=dict(id='uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men',
            sport='Soccer',league='Premier League of Bosnia and Herzegovina | Men',region='Bosnia and Herzegovina',
            catalog_terms=['Premier League of Bosnia and Herzegovina | Men'],endpoint='https://example.test')
        page='<html><h1>Wwin League BH</h1><table><tr><td>18.09.2027. 20:00 FK ŽELJEZNIČAR - NK ČELIK</td></tr></table></html>'
        event=parse_bih_fixtures(page,source)[0]
        self.assertEqual('NK ČELIK at FK ŽELJEZNIČAR',event['name'])
        self.assertEqual('2027-09-18T18:00:00Z',event['start_time'])
        source['catalog_terms']=['CUP BiH']
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            parse_bih_fixtures(page,source)

    def test_malta_ticket_fixture_is_timed(self):
        source = {
            "id":"uefa-soccer-malta-maltese-premier-league-men",
            "sport":"Soccer","league":"Maltese Premier League | Men","region":"Malta",
            "catalog_terms":["Maltese Premier League | Men"],"endpoint":"https://tickets.mfa.com.mt/"
        }
        page = """<html><body>VBet Malta Premier League 2026/2027
        Mosta FC v Birzebbuga St Peters FC 20:00
        Marsaxlokk FC v Zabbar St. Patrick FC 18:00
        Floriana FC v Balzan FC 11:00</body></html>"""
        events = parse_malta_tickets(page, source)
        self.assertEqual(3, len(events))


if __name__ == "__main__":
    unittest.main()
