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
    def results_page(self):
        return (Path(__file__).parent/'fixtures/bih-round12-results-20261031.html').read_text()

    def parse_results(self,page):
        return parse_bih_fixtures(page,self.bih_source(),
            observed_at=datetime.datetime(2026,10,31,23,tzinfo=datetime.timezone.utc))

    def test_bih_exact_results_round_retains_only_two_unscored_fixtures(self):
        events=self.parse_results(self.results_page())
        self.assertEqual(['bih-wwin-54152329','bih-wwin-54152333'],[e['id'] for e in events])
        self.assertEqual(['2026-11-01T12:00:00Z','2026-11-01T14:00:00Z'],[e['start_time'] for e in events])

    def test_bih_results_scope_identity_dates_and_scores_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'round tabs'):
            parse_bih_fixtures(self.bih_page(result_round=12,fixture_round=13),self.bih_source())
        page=self.results_page()
        for a,b in [('Results round 12','Results round 13'),('54152329-bsk','99999999-bsk'),
                    ('01.11.2026. 13:00','01.11.2026. 14:00'),('2 : 0','P : P'),
                    ('BSK','UNKNOWN'),('- : -','1 : 0')]:
            with self.subTest(change=b),self.assertRaises(ValueError):
                self.parse_results(page.replace(a,b))

    def test_bih_results_missing_or_duplicate_rows_and_nonempty_footer_rejected(self):
        from lxml import html
        import copy
        for duplicate in (False,True):
            d=html.fromstring(self.results_page());r=d.xpath('//tr[td/a[contains(@href,"54152329")]]')[0]
            if duplicate:r.getparent().append(copy.deepcopy(r))
            else:r.getparent().remove(r)
            with self.assertRaises(ValueError):self.parse_results(html.tostring(d))
        page=self.results_page().replace('<td colspan="6"></td>','<td colspan="6">Unverified match</td>')
        with self.assertRaisesRegex(ValueError,'footer'):self.parse_results(page)

    BIH_FIXTURES = (
        ("01.11.2026. 13:00", "BSK", "FK SARAJEVO", "54152329"),
        ("01.11.2026. 15:00", "FK SLOGA DOBOJ", "FK VELEŽ", "54152333"),
        ("31.10.2026. 13:00", "FK RADNIK", "NK ŠIROKI BRIJEG", "54152331"),
        ("31.10.2026. 16:00", "FK ŽELJEZNIČAR", "HŠK ZRINJSKI", "54152330"),
        ("31.10.2026. 20:45", "NK ČELIK", "FK BORAC", "54152332"),
    )

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

    def test_affa_current_mixed_blocks_preserve_all_pairings_and_venues(self):
        page = '''<html><body><div class="news_item"><h1>Misli Premyer Liqası: X turun təyinatları</h1>
        <span class="date">Dərc olundu: <span>30.10.2026</span></span><div class="texts mb3">
        <div><span>30 oktyabr (cümə)</span></div>
        <div><span>“Turan Tovuz” – “Sabah”</span><br>Hakimlər: A<br>Tovuz şəhər stadionu, 18:30</div>
        <div><strong>31 oktyabr (şənbə)</strong><br><span>“Araz-Naxçıvan” – “Zirə”</span><br>
        Hakimlər: B<br>Şamaxı şəhər stadionu, 15:00<br><span>“Qəbələ” – “Qarabağ”</span><br>
        Hakimlər: C<br>Qəbələ şəhər stadionu, 17:30</div>
        <div><strong>1 noyabr (bazar)</strong></div>
        <div><span>“Şamaxı” – “Neftçi”</span><br>Hakimlər: D<br>Şamaxı şəhər stadionu, 15:00</div>
        <div><strong>“Kəpəz” – “İmişli”</strong></div>
        <div>Hakimlər: E<br>Gəncə şəhər stadionu, 17:30</div>
        </div></div></body></html>'''
        events = parse_affa_notice(page, self.affa_source(), review_date=datetime.date(2026, 10, 30))
        self.assertEqual(5, len(events))
        self.assertEqual(["Tovuz şəhər stadionu", "Şamaxı şəhər stadionu", "Qəbələ şəhər stadionu",
                          "Şamaxı şəhər stadionu", "Gəncə şəhər stadionu"],
                         [event["location"] for event in events])
        self.assertEqual(["2026-10-30T14:30:00Z", "2026-10-31T11:00:00Z",
                          "2026-10-31T13:30:00Z", "2026-11-01T11:00:00Z",
                          "2026-11-01T13:30:00Z"], [event["start_time"] for event in events])
        with self.assertRaisesRegex(ValueError, "kickoff missing"):
            parse_affa_notice(page.replace("Qəbələ şəhər stadionu, 17:30", "Qəbələ şəhər stadionu, TBC"),
                              self.affa_source())

    def bih_source(self):
        return dict(id='uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men',
            sport='Soccer',league='Premier League of Bosnia and Herzegovina | Men',region='Bosnia and Herzegovina',
            catalog_terms=['Premier League of Bosnia and Herzegovina | Men'],endpoint='https://example.test')

    def bih_page(self, fixtures=None, result_round=11, fixture_round=12, score="- : -"):
        rows = []
        for date, home, away, match_id in fixtures or self.BIH_FIXTURES:
            rows.append(f'<tr><td colspan="6" class="text-center success"><strong>{date}</strong></td></tr>')
            rows.append(f'''<tr><td>{home}</td><td></td><td>{score}</td><td></td><td>{away}</td>
                <td><a href="/en/stats/match/{match_id}-fixture/">Details</a></td></tr>''')
        return f'''<html><head><title>Wwin League BH</title></head><body><div class="tabelarni">
            <a href="#round-rezultati">Results round {result_round}</a>
            <a href="#round-naredno">Fixtures round {fixture_round}</a>
            <div id="round-naredno"><table>
            <tr><th>Host</th><th></th><th>Score</th><th></th><th>Guest</th><th></th></tr>
            {''.join(rows)}</table></div></div></body></html>'''

    def test_bih_current_complete_fixture_round_and_utc(self):
        events = parse_bih_fixtures(self.bih_page(), self.bih_source())
        self.assertEqual([f"bih-wwin-{row[3]}" for row in self.BIH_FIXTURES], [event["id"] for event in events])
        self.assertEqual(["2026-11-01T12:00:00Z", "2026-11-01T14:00:00Z",
                          "2026-10-31T12:00:00Z", "2026-10-31T15:00:00Z",
                          "2026-10-31T19:45:00Z"], [event["start_time"] for event in events])

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
        self.assertEqual('Qəbələ şəhər stadionu',events[0]['location'])
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

    def test_bih_incomplete_or_changed_fixture_round_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            parse_bih_fixtures(self.bih_page(self.BIH_FIXTURES[:-1]), self.bih_source())
        with self.assertRaisesRegex(ValueError, 'pairing, status'):
            parse_bih_fixtures(self.bih_page(score='1 : 0'), self.bih_source())
        with self.assertRaisesRegex(ValueError, 'round tabs'):
            parse_bih_fixtures(self.bih_page(result_round=12), self.bih_source())
        changed = self.bih_page().replace('/en/stats/match/54152329-fixture/', '/en/stats/cup/54152329-fixture/')
        with self.assertRaisesRegex(ValueError, 'match identity'):
            parse_bih_fixtures(changed, self.bih_source())
        source = self.bih_source(); source['catalog_terms']=['CUP BiH']
        with self.assertRaisesRegex(ValueError,'catalog scope'):
            parse_bih_fixtures(self.bih_page(),source)

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
