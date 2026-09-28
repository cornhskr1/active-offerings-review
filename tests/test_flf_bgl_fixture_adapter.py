import datetime
import unittest

from scripts.flf_bgl_fixture_adapter import overview, match_card


SOURCE = {"id":"uefa-soccer-luxembourg-national-division-bgl-ligue-men",
          "sport":"Soccer","league":"National Division / BGL Ligue | Men",
          "region":"Luxembourg","catalog_terms":["National Division / BGL Ligue | Men"]}


def season_page():
    links = []
    for round_number in range(1,31):
        day = "11.10.2026" if round_number == 9 else (
            "18.10.2026" if round_number > 9 else "20.09.2026")
        for game in range(8):
            label = f"Home {game} 16:00 {day} Away {game}" if round_number >= 9 else f"Home {game} 1 - 1 {day} Away {game}"
            links.append(f'<a href="/games/{round_number*100+game}">{label}</a>')
    return '<html><body>BGL Ligue Saison 2026/2027 ' + ''.join(links) + '</body></html>'


def detail():
    return ('<html><head><title>Home 0 / Away 0 - Spill - FLF</title></head><body>'
            'Date 11/10/2026 Heure 16:00 Ligue BGL Ligue Seniors M '
            'Jour de match 9 Lieu Stade Municipal (Luxembourg)</body></html>')


class FlfBglFixtureTests(unittest.TestCase):
    def test_exact_next_round_and_senior_game_page(self):
        number, rows, total = overview(season_page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((number,len(rows),total),(9,8,240))
        event = match_card(detail(),rows[0][0],number,rows[0][1],SOURCE)
        self.assertEqual(event["start_time"],"2026-10-11T14:00:00Z")
        self.assertEqual(event["source_endpoint"],"https://www.flf.lu/games/900")

    def test_missing_match_or_changed_league_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"240-match"):
            overview(season_page().replace('<a href="/games/900">','<span>',1),SOURCE,datetime.date(2026,9,28))
        number, rows, _ = overview(season_page(),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"senior match"):
            match_card(detail().replace("BGL Ligue Seniors M","BGL Ligue U19"),rows[0][0],number,rows[0][1],SOURCE)


if __name__ == "__main__":
    unittest.main()
