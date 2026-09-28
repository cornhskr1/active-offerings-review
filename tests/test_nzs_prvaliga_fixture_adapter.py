import datetime
import unittest

from scripts.nzs_prvaliga_fixture_adapter import next_round, verified_match


SOURCE = {"id":"uefa-soccer-slovenia-slovenian-prvaliga-men", "sport":"Soccer",
          "league":"Slovenian PrvaLiga | Men", "region":"Slovenia",
          "catalog_terms":["Slovenian PrvaLiga | Men"]}


def page():
    rows=[]
    for i in range(5):
        day="2026-10-10" if i<3 else "2026-10-11"
        clock="15:00" if i!=1 else "17:30"
        rows.append(f'''<tr class="match-tbody-tr"><td><div class="upcoming-match-date">
        <time class="date" datetime="{day}">{day}</time>
        <time class="time" datetime="{clock}">{clock}</time></div></td>
        <td><h5 class="match-team-name">Home {i}</h5><h5 class="match-team-name">Away {i}</h5></td>
        <td><strong class="match-location">Stadion {i}</strong></td>
        <td><div class="match-category">Prva liga Telemach</div></td>
        <td>Krog 11</td><td><a href="/klubi/moski/prva-liga-telemach/tekme/match-{i}-1snl2627-{day}-{clock.replace(':','')}00">Podrobnosti</a></td></tr>''')
    return '<html><body>2026/2027 <table>'+''.join(rows)+'</table></body></html>'


def detail():
    return '''<html><body><div class="cover-competition">PRVA LIGA TELEMACH 26/27 11. krog</div>
    <div class="cover-match-data-team"><span class="team-name"><a>Home 0</a></span></div>
    <div class="cover-match-data-team"><span class="team-name"><a>Away 0</a></span></div>
    <div class="cover-match-info"><div class="cover-match-info-date"><span>10.10.2026, 15:00</span></div>
    Stadion 0</div></body></html>'''


class NzsPrvaligaFixtureTests(unittest.TestCase):
    def test_complete_next_round_and_detail_confirmation(self):
        rows,count=next_round(page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((len(rows),count),(5,5))
        event=verified_match(detail(),rows[0],SOURCE)
        self.assertEqual(event["start_time"],"2026-10-10T13:00:00Z")
        self.assertEqual(event["name"],"Away 0 at Home 0")

    def test_incomplete_round_and_wrong_competition_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"five-match"):
            next_round(page().replace('Krog 11','Krog 12',1),SOURCE,datetime.date(2026,9,28))
        rows,_=next_round(page(),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"competition"):
            verified_match(detail().replace('PRVA LIGA TELEMACH','POKAL'),rows[0],SOURCE)


if __name__ == "__main__":
    unittest.main()
