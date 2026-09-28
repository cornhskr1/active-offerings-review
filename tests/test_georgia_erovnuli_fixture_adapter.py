"""Georgian calendar local time must agree with linked match UTC time."""

import datetime
import unittest

from scripts.georgia_erovnuli_fixture_adapter import candidates, verified_match


SOURCE = {"id":"uefa-soccer-georgia-erovnuli-liga-men", "sport":"Soccer",
          "league":"Erovnuli Liga | Men", "region":"Georgia",
          "catalog_terms":["Erovnuli Liga | Men"]}


def calendar():
    return '''<html><head><title>Fixtures - Erovnuli Liga</title></head><body><h1>Fixtures</h1>
      <a class="bef-link active" href="/en/calendar">CRYSTALBET Erovnuli Liga</a>
      <section class="games-list-group"><h2>ტური 22</h2>
      <div class="row"><div><h3>Sunday, 4 October, 2026</h3></div></div>
      <div class="glg-subgroup"><div class="e-game-teaser" data-id="9278" data-status="upcoming">
      <a class="gt-main" href="/en/game/9278-ibe-dtb">
      <span class="grs-1"><span class="grs-name normal">Iberia 1999</span></span>
      <span class="grs-time"><time datetime="2026-10-04T19:00:00Z">19:00</time></span>
      <span class="grs-2"><span class="grs-name normal">Dinamo TB</span></span>
      <span class="f-game-stadium">Stadium</span></a></div></div></section></body></html>'''


def detail():
    return '''<html><head><title>Match - Erovnuli Liga</title></head><body>
       <h1 class="gfh-clubs-inner"><a class="gfh-club"><span class="d-md-inline">Iberia 1999</span></a>
       <span class="gfh-tour">ტური 22</span>
       <a class="gfh-club"><span class="d-md-inline">Dinamo TB</span></a></h1>
       <div class="gfh-status-bar"><time datetime="2026-10-04T15:00:00Z">Sunday, 4 Oct. 2026, 19:00</time></div>
       <span class="f-game-stadium">Stadium</span></body></html>'''


class GeorgiaTests(unittest.TestCase):
    def test_detail_utc_corrects_calendar_metadata(self):
        rows, count = candidates(calendar(), SOURCE, datetime.date(2026, 9, 28), datetime.date(2026, 10, 5))
        self.assertEqual((len(rows), count), (1, 1))
        card = verified_match(detail(), rows[0], SOURCE)
        self.assertEqual(card["start_time"], "2026-10-04T15:00:00Z")
        self.assertEqual(card["name"], "Dinamo TB at Iberia 1999")

    def test_wrong_division_and_detail_time_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "top division"):
            candidates(calendar().replace("CRYSTALBET Erovnuli Liga</a>", "CRYSTALBET Erovnuli Liga 2</a>"),
                       SOURCE, datetime.date(2026, 9, 28), datetime.date(2026, 10, 5))
        rows, _ = candidates(calendar(), SOURCE, datetime.date(2026, 9, 28), datetime.date(2026, 10, 5))
        with self.assertRaisesRegex(ValueError, "kickoff"):
            verified_match(detail().replace("15:00:00Z", "19:00:00Z"), rows[0], SOURCE)


if __name__ == "__main__":
    unittest.main()
