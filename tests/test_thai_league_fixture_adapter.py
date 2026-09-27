"""Thai cup and league feeds must stay separate and exclude stale fixtures."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.thai_league_fixture_adapter import parse_thai_league_matches


ROOT = Path(__file__).resolve().parents[1]
UTC = datetime.timezone.utc


class ThaiLeagueFixtureAdapterTests(unittest.TestCase):
    def test_three_exact_tournaments_and_bangkok_kickoff(self):
        cfg = json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]
        sources = {row["tournament_id"]: row for row in cfg if row.get("source_type") == "thai-league-matches"}
        self.assertEqual({224, 230, 231}, set(sources))

        def match(mid, tournament, **changes):
            row = {"id": mid, "tournament_id": tournament,
                   "tournament_name_en": sources[tournament]["tournament_name"],
                   "start_date": "2026-10-07", "start_time": "19:00",
                   "match_status": 0, "live": False, "is_cancel": False,
                   "home_team_name_en": "FC YALA", "away_team_name_en": "PSU SURATTHANI CITY",
                   "stadium_name_en": "Yala Stadium"}
            row.update(changes)
            return row

        now = datetime.datetime(2026, 10, 6, tzinfo=UTC)
        start, end = datetime.date(2026, 10, 6), datetime.date(2026, 10, 13)
        for tournament in sources:
            with self.subTest(tournament=tournament):
                other = next(value for value in sources if value != tournament)
                rows = [match(1, tournament), match(2, other),
                        match(3, tournament, match_status=2),
                        match(4, tournament, is_cancel=True),
                        match(5, tournament, away_team_name_en="TBC")]
                events = parse_thai_league_matches(rows, sources[tournament], start, end, now)
                self.assertEqual([f'{sources[tournament]["id"]}-1'], [item["id"] for item in events])
                self.assertEqual("2026-10-07T12:00:00Z", events[0]["start_time"])
                self.assertEqual("PSU SURATTHANI CITY at FC YALA", events[0]["name"])
                self.assertEqual([],
                    parse_thai_league_matches([match(1, tournament)], sources[tournament], start, end,
                                             datetime.datetime(2026, 10, 8, tzinfo=UTC)))
                with self.assertRaisesRegex(ValueError, "wrong tournament"):
                    parse_thai_league_matches([match(2, other)], sources[tournament], start, end, now)
                with self.assertRaisesRegex(ValueError, "edition changed"):
                    parse_thai_league_matches([match(1, tournament, tournament_name_en="2025/26")],
                                             sources[tournament], start, end, now)


if __name__ == "__main__":
    unittest.main()
