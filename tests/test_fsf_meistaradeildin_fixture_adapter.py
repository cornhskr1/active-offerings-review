import copy
import datetime
import unittest

from scripts.fsf_meistaradeildin_fixture_adapter import next_round


SOURCE = {"id":"uefa-soccer-faroe-islands-faroe-islands-premier-league-men",
          "sport":"Soccer", "league":"Faroe Islands Premier League | Men",
          "region":"Faroe Islands", "catalog_terms":["Faroe Islands Premier League | Men"]}
NOW = datetime.datetime(2026, 9, 28, tzinfo=datetime.timezone.utc)


def feed():
    rows=[]
    for number in range(1,28):
        day=datetime.datetime(2026,10,10 if number==24 else 18,17,30,tzinfo=datetime.timezone.utc)
        if number<24:day=datetime.datetime(2026,9,20,17,30,tzinfo=datetime.timezone.utc)
        for match in range(5):
            played=number<24
            rows.append({"id":number*10+match,"round":str(number),"roundOrder":number,
                "competition":{"id":6654857,"name":"Meistaradeildin menn 2026"},
                "dateTimeUTC":int(day.timestamp()*1000),
                "liveStatus":"PLAYED" if played else "SCHEDULED",
                "homeTeam":{"id":match*2+1,"name":f"Home {match}"},
                "awayTeam":{"id":match*2+2,"name":f"Away {match}"},
                "facility":{"id":match+1,"name":f"Ground {match}"},
                "homeTeamResult":{"current":1 if played else None},
                "awayTeamResult":{"current":0 if played else None}})
    return rows


class FsfFixtureTests(unittest.TestCase):
    def test_exact_senior_next_round(self):
        events,count=next_round(feed(),SOURCE,NOW)
        self.assertEqual((len(events),count),(5,135))
        self.assertEqual(events[0]["start_time"],"2026-10-10T17:30:00Z")
        self.assertEqual(events[0]["source_endpoint"],"https://www.fsf.fo/kappingar/dystur/?matchID=240")

    def test_incomplete_or_wrong_edition_fails_closed(self):
        rows=feed()
        with self.assertRaisesRegex(ValueError,"incomplete"):
            next_round(rows[:-1],SOURCE,NOW)
        changed=copy.deepcopy(rows)
        changed[115]["competition"]["name"]="MeistaraDeildin kvinnur 2026"
        with self.assertRaisesRegex(ValueError,"edition"):
            next_round(changed,SOURCE,NOW)
        changed=feed()
        changed[115]["facility"]["name"]=""
        with self.assertRaisesRegex(ValueError,"venue"):
            next_round(changed,SOURCE,NOW)


if __name__ == "__main__":
    unittest.main()
