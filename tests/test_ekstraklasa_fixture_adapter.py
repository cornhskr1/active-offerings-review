"""Next-round scope and Warsaw time conversion for the official schedule."""

import unittest
from pathlib import Path
from lxml import html

from scripts.ekstraklasa_fixture_adapter import next_round, SOURCE_ID


SOURCE = {"id": SOURCE_ID, "sport": "Soccer", "league": "Ekstraklasa | Men",
          "region": "Poland", "catalog_terms": ["Ekstraklasa | Men"]}
URL = "https://ekstraklasa.org/terminarz/2026-2027/kolejka-10/"


def sample_page():
    rows = []
    for n in range(9):
        home, away = f"Home {n}", f"Away {n}"
        rows.append(f'''<div><button aria-label="Otwórz szczegóły meczu {home} kontra {away}"></button>
          <div><div class="md:flex"><div><span>18:00</span><span>09.10</span></div></div>
          <p class="text-xsmall">Stadium {n}</p>
          <p class="w-[120px]">{home}</p><p class="w-[120px]">{away}</p>
          <p class="label-xsmall-bold">09.10, 18:00</p>
          <div><a href="/mecz/{n:08x}-0000-0000-0000-000000000000/home-away/statystyki/">Centrum meczowe</a></div>
          </div></div>''')
    return ('<html><head><meta charset="utf-8"><title>Terminarz — sezon 2026-2027, kolejka 10</title></head><body>'
            '<h1>Terminarz</h1><span>10. Kolejka</span>' + ''.join(rows) + '</body></html>').encode()


class EkstraklasaFixtureTests(unittest.TestCase):
    def live_round(self, change=None):
        doc=html.fromstring(sample_page())
        live=html.fromstring((Path(__file__).parent/'fixtures/ekstraklasa-live-card-20261031.html').read_text())
        if change:change(live)
        old=doc.xpath('//a[starts-with(@href,"/mecz/")]')[0].getparent().getparent().getparent()
        old.getparent().replace(old,live)
        return html.tostring(doc,encoding='utf-8')

    def test_live_card_counts_toward_complete_round_but_never_emits(self):
        events,number,held=next_round(self.live_round(),URL,SOURCE)
        self.assertEqual((8,10,0),(len(events),number,held))
        self.assertFalse(any('Katowice' in e['name'] or '42b84d2c' in e['id'] for e in events))

    def test_live_state_route_and_score_must_agree(self):
        def no_label(n):n.xpath('.//span[normalize-space(.)="na żywo"]')[0].text='Unknown'
        def unknown_route(n):
            a=n.xpath('.//a[contains(@href,"/relacja/")]')[0];a.set('href',a.get('href').replace('/relacja/','/unknown/'))
        def upcoming_route(n):
            a=n.xpath('.//a[contains(@href,"/relacja/")]')[0];a.set('href',a.get('href').replace('/relacja/','/statystyki/'))
        def bad_score(n):n.xpath('.//span[contains(@class,"heading-medium")]')[0].text='TBD'
        def missing_club(n):
            a=n.xpath('.//a[starts-with(@href,"/kluby/")]')[0];a.set('href','/youth/gks/')
        def completed_live(n):n.xpath('.//span[normalize-space(.)="na żywo"]')[0].text='na żywo Zakończony'
        for change in (no_label,unknown_route,upcoming_route,bad_score,missing_club,completed_live):
            with self.subTest(change=change.__name__),self.assertRaises(ValueError):
                next_round(self.live_round(change),URL,SOURCE)

    def test_live_round_still_requires_nine_unique_matches_and_eighteen_clubs(self):
        page=self.live_round()
        doc=html.fromstring(page);a=doc.xpath('//a[contains(@href,"/relacja/")]')[0]
        card=a.getparent().getparent().getparent();card.getparent().remove(card)
        with self.assertRaisesRegex(ValueError,'nine-match'):next_round(html.tostring(doc),URL,SOURCE)
        with self.assertRaisesRegex(ValueError,'duplicate or incomplete'):
            next_round(page.replace(b'Home 1',b'GKS Katowice'),URL,SOURCE)
        with self.assertRaisesRegex(ValueError,'pairing'):
            next_round(page.replace(b'00000001-0000-0000-0000-000000000000',b'42b84d2c-ed49-43ec-8baa-da622df92125'),URL,SOURCE)

    def test_exact_round_and_local_kickoff(self):
        events, number, held = next_round(sample_page(), URL, SOURCE)
        self.assertEqual((9, 10, 0), (len(events), number, held))
        self.assertEqual("2026-10-09T16:00:00Z", events[0]["start_time"])
        self.assertEqual("Away 0 at Home 0", events[0]["name"])

    def test_mismatched_edition_and_duplicate_club_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "selected season round"):
            next_round(sample_page(), URL.replace("2026-2027", "2025-2026"), SOURCE)
        with self.assertRaisesRegex(ValueError, "duplicate or incomplete"):
            next_round(sample_page().replace(b"Home 8", b"Home 0"), URL, SOURCE)


if __name__ == "__main__":
    unittest.main()
