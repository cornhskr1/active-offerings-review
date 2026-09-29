"""The SPL season feed must keep its exact league and age-review boundary."""

import datetime
import itertools
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from spl_fixture_adapter import CLUBS, SOURCE_ID, parse_fixtures


SOURCE = {
    "id": SOURCE_ID, "league": "Singapore Premier League | Men",
    "catalog_terms": ["Singapore Premier League | Men"],
    "endpoint": "https://spl.sg/fixtures/",
}


def season_page():
    clubs = sorted(CLUBS)
    pairs = list(itertools.combinations(clubs, 2)) * 3
    rows = []
    for n, (home, away) in enumerate(pairs):
        day = datetime.date(2026, 9, 11) + datetime.timedelta(days=n)
        rows.append(
            f'<div class="spl-gwrow"><div class="spl-gwrow-meta">'
            f'{day:%a}, {day.day} {day:%b %Y} · 7:30pm · Test Stadium</div>'
            f'<span class="spl-gwrow-name home">{home}</span>'
            f'<span class="spl-gwrow-vs">vs</span>'
            f'<span class="spl-gwrow-name away">{away}</span></div>'
        )
    widths = [4] * 15 + [3] * 8
    panels = []
    cursor = 0
    for width in widths:
        panels.append('<div class="spl-gwnav-panel">' + ''.join(rows[cursor:cursor + width]) + '</div>')
        cursor += width
    options = ''.join(f'<option>Matchweek {n}</option>' for n in range(1, 24))
    return ('<html><title>Fixtures – Singapore Premier League</title>'
            f'<div class="spl-gwnav"><select>{options}</select>{"".join(panels)}</div></html>')


class SplFixtureAdapterTests(unittest.TestCase):
    def test_full_season_holds_young_lions_and_converts_kickoff(self):
        events, held, total, held_starts = parse_fixtures(season_page(), SOURCE)
        self.assertEqual((63, 21, 84), (len(events), held, total))
        self.assertEqual(21, len(held_starts))
        self.assertTrue(all("Young Lions" not in event["name"] for event in events))
        self.assertEqual("2026-09-11T11:30Z", events[0]["start_time"])

    def test_missing_pairing_fails_closed(self):
        page = season_page().replace('spl-gwrow-name away">FC Jurong',
                                     'spl-gwrow-name away">Unapproved FC', 1)
        with self.assertRaisesRegex(ValueError, "club or pairing"):
            parse_fixtures(page, SOURCE)

    def test_changed_competition_identity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "page identity"):
            parse_fixtures(season_page().replace('Singapore Premier League</title>',
                                                 'Singapore Cup</title>'), SOURCE)


if __name__ == "__main__":
    unittest.main()
