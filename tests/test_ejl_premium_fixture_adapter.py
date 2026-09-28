import datetime
import unittest

from scripts.ejl_premium_fixture_adapter import next_round, verified_match


SOURCE = {"id":"uefa-soccer-estonia-meistriliiga-premium-liiga-men",
          "sport":"Soccer", "league":"Meistriliiga / Premium Liiga | Men",
          "region":"Estonia", "catalog_terms":["Meistriliiga / Premium Liiga | Men"]}


def page():
    rows=[]
    for round_number in (30,31):
        for i in range(5):
            match_id=round_number*100+i
            day="10.10.2026" if round_number==30 else "13.10.2026"
            rows.append(f'''<li><div class="info"><p>{round_number}. Voor</p></div>
                <div class="event-single-small"><div class="content"><p class="time">{day} kell 14:30</p>
                <div class="teams"><p class="left"><a href="/voistlused/52/team/{i*2+1}?season=2026">Home {i}</a></p>
                <div class="results-container"><span class="result"> - </span></div>
                <p class="right"><a href="/voistlused/52/team/{i*2+2}?season=2026">Away {i}</a></p></div></div>
                <a href="/voistlused/match_info/{match_id}">Details</a></div></li>''')
    return '<html><head><title>A. Le Coq Premium liiga</title></head><body><ul>'+''.join(rows)+'</ul></body></html>'


def detail():
    return '''<html><body><div id="page" class="event-detail"><div class="row"><div class="col-75">
        <div class="head"><div class="teams"><div class="team"><p><a>Home 0</a></p></div>
        <div class="team"><p><a>Away 0</a></p></div></div><div class="info"><ul>
        <li class="type"><a>A. Le Coq Premium liiga</a></li><li>30. voor</li>
        <li class="date"><p>10.10.2026 kell 14:30</p></li>
        <li class="location"><p><a>Stadion</a></p></li></ul></div></div>
        </div></div></div></body></html>'''


class EjlFixtureTests(unittest.TestCase):
    def test_next_round_and_match_detail(self):
        rows,count=next_round(page(),SOURCE,datetime.date(2026,9,28))
        self.assertEqual((len(rows),count),(5,10))
        event=verified_match(detail(),rows[0],SOURCE)
        self.assertEqual(event["start_time"],"2026-10-10T11:30:00Z")
        self.assertEqual(event["name"],"Away 0 at Home 0")

    def test_partial_round_and_wrong_competition_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"five-match"):
            next_round(page().replace('30. Voor','31. Voor',1),SOURCE,datetime.date(2026,9,28))
        rows,_=next_round(page(),SOURCE,datetime.date(2026,9,28))
        with self.assertRaisesRegex(ValueError,"competition"):
            verified_match(detail().replace('A. Le Coq Premium liiga','Esiliiga'),rows[0],SOURCE)


if __name__ == "__main__":
    unittest.main()
