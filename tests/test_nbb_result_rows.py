"""Published results cannot discard upcoming NBB games or become fixtures."""
import json
from pathlib import Path
import sys
import unittest
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from publisher_basketball_beach import parse_nbb_fixtures


class NbbResultRowsTests(unittest.TestCase):
    def setUp(self):
        self.source = next(s for s in json.loads((ROOT / 'data/global-schedule-sources.json').read_text())['sources']
                           if s['id'] == 'basketball-br-nbb')
        self.page = (ROOT / 'tests/fixtures/nbb_results_and_fixtures_2026.html').read_bytes()

    def test_publisher_result_row_does_not_discard_remaining_schedule(self):
        events = parse_nbb_fixtures(self.page, self.source)
        self.assertEqual(20, len(events))
        self.assertNotIn('nbb-2026-27-27110', {e['id'] for e in events})
        self.assertEqual('Ceisc/União Corinthians at Flamengo', events[0]['name'])
        self.assertEqual('2026-11-01T14:00:00Z', events[0]['start_time'])
        self.assertTrue(all(e['status'] == 'UPCOMING' and '/partidas/nbb-2026-2027-' in e['source_endpoint'] for e in events))

    def test_small_remaining_schedule_uses_validated_result_rows_for_inventory(self):
        document = html.fromstring(self.page)
        for row in document.xpath('//tr')[2:]:
            a = row.xpath('.//a')[0]
            a.clear(keep_tail=True)
            a.set('class', 'match_score_relatorio')
            a.set('href', 'https://lnb.com.br/noticias/nbb-caixa-2026-27-published-result/')
            for side, score in [('home', '84'), ('away', '73')]:
                node = html.Element('span'); node.set('class', side); node.text = score; a.append(node)
        events = parse_nbb_fixtures(html.tostring(document), self.source)
        self.assertEqual(['nbb-2026-27-27143'], [e['id'] for e in events])
        remaining = document.xpath('//tr')[1].xpath('.//a')[0]
        remaining.getparent().replace(remaining, html.fromstring(html.tostring(document.xpath('//tr')[2].xpath('.//a')[0])))
        self.assertEqual([], parse_nbb_fixtures(html.tostring(document), self.source))

    def test_conflicting_result_scores_remain_blocked(self):
        document = html.fromstring(self.page)
        result = document.xpath('//tr')[0]
        original = result.xpath('.//a')[0]
        duplicate = html.fromstring(html.tostring(original))
        duplicate.xpath('./span[@class="home"]')[0].text = '85'
        result.append(duplicate)
        with self.assertRaisesRegex(ValueError, 'result identity'):
            parse_nbb_fixtures(html.tostring(document), self.source)

    def test_result_rows_still_validate_identity_pairing_time_and_edition(self):
        for old, new in [(b'>84<', b'><'), (b'>73<', b'>TBD<'),
                         (b'data-real-id="27110"', b'data-real-id="27143"'),
                         (b'17/10/2026', b'unknown-date'),
                         (b'/noticias/nbb-caixa-2026-27-', b'/noticias/nbb-caixa-2025-26-'),
                         (b'https://lnb.com.br/noticias/', b'https://untrusted.test/noticias/')]:
            with self.subTest(change=new):
                self.assertIn(old, self.page)
                with self.assertRaises(ValueError):
                    parse_nbb_fixtures(self.page.replace(old, new, 1), self.source)

    def test_missing_result_scores_cannot_hide_missing_fixture_link(self):
        page = self.page.replace(b'>84<', b'><').replace(b'>73<', b'><')
        with self.assertRaises(ValueError):
            parse_nbb_fixtures(page, self.source)

    def test_upcoming_missing_link_or_wrong_host_still_fails_whole_source(self):
        for old, new in [(b'/partidas/nbb-2026-2027-', b'/partidas/other-edition-'),
                         (b'https://lnb.com.br/partidas/', b'https://untrusted.test/partidas/')]:
            with self.subTest(change=new), self.assertRaises(ValueError):
                parse_nbb_fixtures(self.page.replace(old, new, 1), self.source)

    def test_result_rows_do_not_remove_minimum_inventory_guard(self):
        document = html.fromstring(self.page)
        for row in document.xpath('//tr')[10:]:
            row.getparent().remove(row)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            parse_nbb_fixtures(html.tostring(document), self.source)

    def test_exact_catalog_scope_remains_required(self):
        with self.assertRaises(ValueError):
            parse_nbb_fixtures(self.page, {**self.source, 'catalog_terms': ['Other basketball']})


if __name__ == '__main__':
    unittest.main()
