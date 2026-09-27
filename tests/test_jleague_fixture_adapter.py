"""J2 and Levain Cup overlap on the official page, but never share a source."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.jleague_fixture_adapter import parse_jleague_matches


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {s["id"]: s for s in json.loads((ROOT / "data/soccer-afc-domestic-sources.json").read_text())["sources"]}


def official_page():
    def match(ident, path, away, state="ticket"):
        return {"id": ident, "detailHref": path, "time": "14:00", "state": state,
                "homeTeam": {"fullName": "Albirex Niigata"},
                "awayTeam": {"fullName": away}}
    sections = [{"schedules": [
        {"leagueDisplayName": "MEIJI YASUDA J2 League", "matchDate": "$D2026-10-03T00:00:00.000Z",
         "matches": [match("2026100309", "/match/j2/2026/100309", "Tokushima Vortis"),
                     match("2026100399", "/match/leaguecup/2026/100399", "J2 Cup Opponent"),
                     match("2026100388", "/match/j2/2026/100388", "Under 18s"),
                     match("2026100377", "/match/j2/2026/100377", "Played", "finished")]},
        {"leagueDisplayName": "J.League Yamazaki Biscuits Levain Cup", "matchDate": "$D2026-10-03T00:00:00.000Z",
         "matches": [match("2026100307", "/match/leaguecup/2026/100307", "Fagiano Okayama"),
                     match("2026100308", "/match/j2/2026/100308", "Wrong Cup Path")]}]}]
    data = '10e:' + json.dumps(sections, separators=(",", ":"))
    return '<script>self.__next_f.push(' + json.dumps([1, data]) + ')</script>'


class JLeagueFixtureAdapterTests(unittest.TestCase):
    def test_exact_path_name_and_teams(self):
        page = official_page()
        a, b = datetime.date(2026, 9, 27), datetime.date(2026, 10, 4)
        j2 = parse_jleague_matches(page, SOURCES["soccer-afc-japan-j2-league-men"], a, b)
        cup = parse_jleague_matches(page, SOURCES["soccer-afc-japan-jleague-cup-men"], a, b)
        self.assertEqual(["soccer-afc-japan-j2-league-men-2026100309"], [e["id"] for e in j2])
        self.assertEqual(["soccer-afc-japan-jleague-cup-men-2026100307"], [e["id"] for e in cup])
        self.assertEqual("2026-10-03T05:00:00Z", j2[0]["start_time"])
        with self.assertRaises(ValueError):
            parse_jleague_matches("<html></html>", SOURCES["soccer-afc-japan-j2-league-men"], a, b)


if __name__ == "__main__":
    unittest.main()
