"""Missing calendar games require independently verified exact final results."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from italy_volleyball_fixtures import parse_serie_a1, serie_a1_completed_round_urls


class ItalyA1CompletedRoundTests(unittest.TestCase):
    def setUp(self):
        self.source = next(s for s in json.loads((ROOT/'data/global-schedule-sources.json').read_text())['sources']
                           if s['id'] == 'volleyball-italy-serie-a1-women')
        self.page = (ROOT/'tests/fixtures/italy_a1_remaining_round6_2026.html').read_bytes()
        self.proof = {f'https://www.legavolleyfemminile.it/match-center/{mid}/':
                      (ROOT/f'tests/fixtures/italy_a1_completed_{mid}_2026.html').read_bytes()
                      for mid in (748021, 748017)}
        self.today, self.end = dt.date(2026, 10, 31), dt.date(2026, 11, 7)
        self.now = dt.datetime(2026, 11, 1, 4, 57, tzinfo=dt.timezone.utc)

    def parse(self, page=None, proof=None, now=None, today=None):
        return parse_serie_a1(page if page is not None else self.page, self.source,
                             today or self.today, self.end,
                             completed_pages=self.proof if proof is None else proof,
                             observed_at=self.now if now is None else now)

    def test_actual_remaining_panel_and_both_results_keep_future_fixtures_only(self):
        rows = self.parse()
        self.assertEqual(145, len(rows))
        self.assertEqual(145, len({r['id'] for r in rows}))
        r6 = [r for r in rows if r['season_stage'] == 'REGULAR SEASON ANDATA ROUND 6']
        self.assertEqual(5, len(r6))
        self.assertEqual('2026-11-01T15:00:00Z', r6[0]['start_time'])
        self.assertEqual('2026-11-02T19:40:00Z', r6[-1]['start_time'])
        self.assertTrue(all(dt.datetime.fromisoformat(r['start_time']) > self.now for r in r6))
        self.assertTrue(all(not r['id'].endswith(('-3040', '-3036')) for r in rows))
        self.assertTrue(all(r['league'] == 'Serie A1 | Women' for r in rows))
        self.assertEqual(set(self.proof), set(serie_a1_completed_round_urls(self.page, self.source, self.today)))

    def test_missing_swapped_extra_or_duplicated_result_evidence_fails(self):
        a, b = self.proof
        for proof in ({}, {a:self.proof[a]}, {a:self.proof[b], b:self.proof[a]},
                      {**self.proof, 'https://foreign.test/': self.proof[a]}):
            with self.subTest(keys=list(proof)), self.assertRaises(ValueError):
                self.parse(proof=proof)
        d = html.fromstring(self.proof[a]); panel=d.xpath('//div[contains(@class,"tabellone-alto-match-center")]')[0]
        d.append(copy.deepcopy(panel))
        with self.assertRaises(ValueError):self.parse(proof={**self.proof, a:html.tostring(d)})

    def test_changed_result_identity_pairing_clock_venue_or_final_score_fails(self):
        a = next(iter(self.proof))
        mutations = [(b'748021/', b'748022/'), (b'710945/', b'710949/'),
                     (b'Cbf Balducci Hr Macerata', b'Unknown club'),
                     (b'31/10/2026', b'01/11/2026'), (b'18:00', b'19:00'),
                     (b'Fontescodella', b'Unknown venue'), (b'<span>3</span>', b'<span>2</span>'),
                     (b'25-17', b'25-18'), (b'Play by Play', b'Unknown competition')]
        for old, new in mutations:
            self.assertIn(old, self.proof[a])
            with self.subTest(change=new), self.assertRaises(ValueError):
                self.parse(proof={**self.proof, a:self.proof[a].replace(old,new,1)})

    def test_future_scored_naive_missing_clock_and_expired_review_fail(self):
        for now in (dt.datetime(2026,10,31,16,tzinfo=dt.timezone.utc), self.now.replace(tzinfo=None)):
            with self.subTest(now=now), self.assertRaises(ValueError):self.parse(now=now)
        with self.assertRaises(ValueError):
            parse_serie_a1(self.page,self.source,self.today,self.end,completed_pages=self.proof)
        for day in (dt.date(2026,10,30),dt.date(2026,11,3)):
            self.assertEqual([],serie_a1_completed_round_urls(self.page,self.source,day))
            with self.assertRaises(ValueError):self.parse(today=day)

    def test_altered_remaining_identity_and_new_missing_fixture_never_request_proof(self):
        for old,new in [(b'#3042',b'#3999'),(b'748023/',b'748024/'),(b'710949/',b'710946/'),
                        (b'Il Bisonte Firenze',b'Unknown club'),(b'01/11/2026',b'02/11/2026'),
                        (b'16:00',b'TBD'),(b'Pala BigMat - Firenze',b'Unknown venue'),
                        (b'6<sup>a</sup>',b'5<sup>a</sup>')]:
            self.assertIn(old,self.page)
            p=self.page.replace(old,new,1)
            with self.subTest(change=new):
                self.assertEqual([],serie_a1_completed_round_urls(p,self.source,self.today))
                with self.assertRaises(ValueError):self.parse(page=p)
        d=html.fromstring(self.page); t=d.xpath('//table')[0];t.getparent().remove(t)
        self.assertEqual([],serie_a1_completed_round_urls(html.tostring(d),self.source,self.today))
        with self.assertRaises(ValueError):self.parse(page=html.tostring(d))

    def test_other_partial_round_or_contaminated_result_still_fails(self):
        d=html.fromstring(self.page)
        t=next(t for t in d.xpath('//table') if '7a Giornata - Andata' in ' '.join(t.text_content().split()))
        t.getparent().remove(t)
        with self.assertRaisesRegex(ValueError,'round incomplete'):self.parse(page=html.tostring(d))
        a=next(iter(self.proof));d=html.fromstring(self.proof[a])
        teams=d.xpath('//div[contains(@class,"pre-roster")]')[0]
        teams.append(html.fromstring('<div><a href="/club/club/999/">Unknown club</a></div>'))
        with self.assertRaises(ValueError):self.parse(proof={**self.proof,a:html.tostring(d)})


if __name__ == '__main__':unittest.main()
