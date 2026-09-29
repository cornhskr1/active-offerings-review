import unittest

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
        page = """<html><body><h1>Misli Premyer Liqası: VII turun təyinatları</h1>
        <p>3 oktyabr</p><p>17:00. “Araz-Naxçıvan” - “İmişli”</p></body></html>"""
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
