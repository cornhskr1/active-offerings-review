"""The SA Rugby feed must not turn other divisions into Currie Cup cards."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.saru_fixture_adapter import parse_saru_matches


ROOT = Path(__file__).resolve().parents[1]


class SaruFixtureAdapterTests(unittest.TestCase):
    def test_exact_premier_scope_and_timed_fixtures(self):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        source = next(row for row in sources if row["id"] == "rugby-saru-currie-premier")
        self.assertEqual("partial", source["coverage_status"])
        premier = source["competition_id"]

        def match(mid, cid=premier, **changes):
            row = {"matchId": mid, "competitionId": cid,
                   "competitionName": "Carling Currie Cup Premier Division",
                   "seasonName": "2026", "utcDate": "2026-09-12T13:00:00",
                   "statsStatus": "None", "isCancelled": False, "isPostponed": False,
                   "isLive": False, "venueName": "Suzuki Stadium",
                   "teams": [{"name": "Suzuki Griquas", "isHomeTeam": True},
                             {"name": "Airlink Pumas", "isHomeTeam": False}]}
            row.update(changes)
            return row

        rows = [match("final"), match("first", cid="56038bac-544a-482e-a5da-6351054efc5d"),
                match("old", statsStatus="Complete"), match("postponed", isPostponed=True),
                match("tbc", teams=[{"name": "TBC", "isHomeTeam": True},
                                      {"name": "Airlink Pumas", "isHomeTeam": False}])]
        events = parse_saru_matches({"items": rows, "totalDataCount": len(rows)}, source,
                                    datetime.date(2026, 9, 12), datetime.date(2026, 9, 19))
        self.assertEqual(["rugby-saru-currie-premier-final"], [event["id"] for event in events])
        self.assertEqual("Airlink Pumas at Suzuki Griquas", events[0]["name"])
        self.assertEqual("2026-09-12T13:00:00Z", events[0]["start_time"])
        with self.assertRaisesRegex(ValueError, "wrong competition"):
            parse_saru_matches({"items": [rows[1]], "totalDataCount": 1}, source,
                               datetime.date(2026, 9, 12), datetime.date(2026, 9, 19))
        with self.assertRaisesRegex(ValueError, "wrong season"):
            parse_saru_matches({"items": [match("future", seasonName="2027")], "totalDataCount": 1},
                               source, datetime.date(2026, 9, 12), datetime.date(2026, 9, 19))
        with self.assertRaisesRegex(ValueError, "uncollected pages"):
            parse_saru_matches({"items": [rows[0]], "totalDataCount": 2}, source,
                               datetime.date(2026, 9, 12), datetime.date(2026, 9, 19))


if __name__ == "__main__":
    unittest.main()
