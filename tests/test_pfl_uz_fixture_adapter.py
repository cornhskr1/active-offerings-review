import copy
import datetime
import unittest

from scripts.pfl_uz_fixture_adapter import parse_superleague


SOURCE = {"id":"soccer-afc-uzbekistan-uzbekistan-super-league-men",
          "sport":"Soccer","league":"Uzbekistan Super League | Men",
          "region":"Uzbekistan","catalog_terms":["Uzbekistan Super League | Men"]}
NOW = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)


def calendar():
    rounds = []
    for number in range(1, 31):
        matches = []
        for index in range(8):
            def team(n):
                return {"id":n,"club":{"id":n,"title":f"Club {n}"}}
            matches.append({"id":number*100+index,
                "startDate":("2026-10-07T14:00:06.000Z" if number == 23 else
                             "2026-10-14T19:00:07.000Z" if number > 23 else
                             "2026-09-20T14:00:00.000Z"),
                "stadium":{"title":"Senior ground"} if number == 23 else None,
                "homeTeam":team(index*2),"awayTeam":team(index*2+1)})
        rounds.append({"title":f"{number}-tur","orderNumber":number,
                       "matches":matches})
    return {"data":{"tournament":{"id":1,"title":"Superliga"},
                    "season":{"id":11,"year":2026},"table":rounds}}


class PflUzFixtureTests(unittest.TestCase):
    def test_next_senior_round_only_and_placeholder_horizon(self):
        payload = calendar()
        events, held, total, next_start = parse_superleague(payload,SOURCE,NOW)
        self.assertEqual((len(events),held,total),(8,0,240))
        self.assertEqual(events[0]["start_time"],"2026-10-07T14:00:00Z")
        self.assertEqual(events[0]["source_endpoint"],"https://pfl.uz/en/match/2300")
        later, held, _, _ = parse_superleague(payload,SOURCE,
            datetime.datetime(2026,10,12,tzinfo=datetime.timezone.utc))
        self.assertEqual((len(later),held),(0,8))

    def test_edition_scope_and_incomplete_round_fail_closed(self):
        payload = calendar()
        changed = copy.deepcopy(payload)
        changed["data"]["tournament"]["id"] = 4  # U21
        with self.assertRaisesRegex(ValueError,"senior"):
            parse_superleague(changed,SOURCE,NOW)
        changed = copy.deepcopy(payload)
        changed["data"]["table"][22]["matches"].pop()
        with self.assertRaisesRegex(ValueError,"eight-match"):
            parse_superleague(changed,SOURCE,NOW)
        changed = copy.deepcopy(payload)
        changed["data"]["table"][22]["matches"][0]["homeTeam"]["club"]["title"] = "Club U21"
        with self.assertRaisesRegex(ValueError,"youth"):
            parse_superleague(changed,SOURCE,NOW)


if __name__ == "__main__":
    unittest.main()
