"""Next-round scope and Warsaw time conversion for the official schedule."""

import unittest

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
