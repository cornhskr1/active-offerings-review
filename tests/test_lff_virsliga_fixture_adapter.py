import datetime
import unittest

from scripts.lff_virsliga_fixture_adapter import next_round


SOURCE = {"id":"uefa-soccer-latvia-latvian-higher-league-virsl-ga-men",
          "sport":"Soccer", "league":"Latvian Higher League / Virslīga | Men",
          "region":"Latvia", "catalog_terms":["Latvian Higher League / Virslīga | Men"],
          "official_schedule_url":"https://lff.lv/sacensibas/viriesi/virsliga/?p=2026"}


def page():
    upcoming=[];complete=[]
    for i in range(180):
        match_id=23300000+i
        future=i<5
        names=(f"Home {i}",f"Away {i}")
        clubs=''.join(f'<div class="club"><div class="title"><a href="/klubi/team-{j}/?cid=23300000">{name}</a></div>'
                      f'<span class="res{j}">{"-" if future else "1"}</span></div>'
                      for j,name in enumerate(names,1))
        venue=f"Stadion {i}"
        if future:
            upcoming.append(f'<div class="tr match" data-id="{match_id}"><div class="matchday"><h4>14:00</h4>'
                            '<h5>32</h5></div><div class="clubs">'+clubs+'</div>'
                            f'<div class="stadium">{venue}</div></div>')
        date='<h5>10</h5><h6>okt</h6>' if future else '<h5>20</h5><h6>sep</h6>'
        complete.append(f'<div class="tr match" data-id="{match_id}"><div class="date">{date}'
                        '<div class="h7">14:00</div><div class="h8">2026</div></div>'
                        '<div class="clubs">'+clubs+'</div>'
                        f'<div class="stadium">{venue}</div></div>')
    return ('<html><body><h1>Tonybet Virslīga</h1><select class="pageParams"><option selected="selected">2026</option></select>'
            '<div id="tabContent_1_1"><div class="fixtures" data-genid="stats_competition_23300000_upcoming">'
            '<div class="tr th1"><span class="h3">Sestdiena, 10.10.2026.</span></div>'+''.join(upcoming)+'</div></div>'
            '<div id="tabContent_1_2"><div class="fixtures" data-genid="stats_competition_23300000_all">'
            +''.join(complete)+'</div></div></body></html>')


class LffFixtureTests(unittest.TestCase):
    def test_full_schedule_cross_checks_next_senior_round(self):
        events,count,held=next_round(page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((len(events),count,held),(5,180,0))
        self.assertEqual(events[0]["start_time"],"2026-10-10T11:00:00Z")
        self.assertEqual(events[0]["name"],"Away 0 at Home 0")

    def test_missing_match_or_disagreeing_date_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            next_round(page().replace('data-id="23300179"','data-id="23300178"'),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"disagree"):
            next_round(page().replace('<h5>10</h5><h6>okt</h6>','<h5>11</h5><h6>okt</h6>',1),SOURCE,datetime.date(2026,9,28))


if __name__ == "__main__":
    unittest.main()
