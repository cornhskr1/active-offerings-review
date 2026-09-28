"""League of Ireland competition, paging and fixture field gates."""

import unittest

from scripts.loi_premier_fixture_adapter import PARAMS, parse_pages, validate_page


SOURCE = {"id":"uefa-soccer-ireland-league-of-ireland-premier-division-men",
          "sport":"Soccer", "league":"League of Ireland Premier Division | Men", "region":"Ireland",
          "catalog_terms":["League of Ireland Premier Division | Men"],
          "official_schedule_url":"https://www.leagueofireland.ie/mens/sse-airtricity-mens-premier-division/fixtures/"}


def parent():
    attrs = ' '.join(f'data-{key}="{value}"' for key, value in PARAMS.items())
    return '''<html><head><title>SSE Airtricity Men's Premier Division Fixtures | League of Ireland</title></head>
        <body><h1>Men’s Premier Division Fixtures</h1><div class="fixture__items" ''' + attrs + '''></div></body></html>'''


def fixture(match_id, date, home, away):
    return f'''<h5 class="fixture__date">{date}</h5><div class="fixture__block">
        <div class="fixture__section" id="{match_id}">
        <p class="fixture__section--content--details-location">Stadium</p>
        <div class="fixture__section--content__team--home"><h5>{home}</h5><img alt="{home}"></div>
        <p class="fixture__section--content--details-time">19:45</p>
        <div class="fixture__section--content__team--away"><h5>{away}</h5><img alt="{away}"></div>
        </div></div>'''


def payload(index, following, fragment):
    return {"request": {**PARAMS, "header": True, "page": str(index)},
            "nextPage": following, "html": fragment}


class LoiPremierTests(unittest.TestCase):
    def test_paginated_premier_fixtures_and_utc(self):
        validate_page(parent(), SOURCE)
        responses = [payload(1, 2, fixture(6002, "Friday 2 October 2026", "Dundalk", "Bohemians")),
                     payload(2, 0, fixture(6020, "Friday 30 October 2026", "St Patrick's Athletic", "Bohemians"))]
        cards = parse_pages(responses, SOURCE)
        self.assertEqual([card["id"] for card in cards], ["loi-premier-6002", "loi-premier-6020"])
        self.assertEqual([card["start_time"] for card in cards],
                         ["2026-10-02T18:45:00Z", "2026-10-30T19:45:00Z"])

    def test_wrong_competition_and_missing_page_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "division"):
            validate_page(parent().replace("Men’s Premier Division", "Women’s Premier Division"), SOURCE)
        response = payload(1, 2, fixture(6002, "Friday 2 October 2026", "Dundalk", "Bohemians"))
        with self.assertRaisesRegex(ValueError, "pagination"):
            parse_pages([response], SOURCE)
        response["request"]["competition"] = "2"
        with self.assertRaisesRegex(ValueError, "competition"):
            parse_pages([response], SOURCE)


if __name__ == "__main__":
    unittest.main()
