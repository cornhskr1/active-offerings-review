"""PREM feed fixtures must remain inside the exact approved competition."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.prem_fixture_adapter import parse_prem_matches


ROOT = Path(__file__).resolve().parents[1]


class PremFixtureAdapterTests(unittest.TestCase):
    def test_two_distinct_competitions_and_fail_closed_fixture_scope(self):
        config = json.loads((ROOT / "data/global-schedule-sources.json").read_text())
        sources = {item["id"]: item for item in config["sources"]}
        league = sources["rugby-prem-gallagher"]
        cup = sources["rugby-prem-cup"]
        self.assertEqual((1011, 1297), (league["competition_id"], cup["competition_id"]))
        mapping = json.loads((ROOT / "data/catalog-season-map.json").read_text())
        rugby = next(sport for sport in mapping["sports"] if sport["sport"] == "Rugby")
        events = {item["key"]: item for group in rugby["groups"] for item in group["events"]}
        self.assertEqual(league["id"], events["rugby-eng-premiership"]["source_id"])
        self.assertEqual(cup["id"], events["rugby-eng-premiership-cup"]["source_id"])

        def match(mid, comp, *, season=202601, status="fixture", home="Bath Rugby", away="Exeter Chiefs", tbc=0):
            return {"id": mid, "compId": comp, "season": season, "status": status,
                    "tbc": tbc, "date": "2026-10-02T18:45:00.000Z",
                    "homeTeam": {"name": home}, "awayTeam": {"name": away}}

        payload = {"data": [match(1, 1011), match(2, 1297),
                            match(3, 1011, status="result"),
                            match(4, 1011, away="TBC"), match(5, 1011, tbc=1)]}
        today, end = datetime.date(2026, 9, 27), datetime.date(2026, 10, 4)
        league_events = parse_prem_matches(payload, league, today, end)
        cup_events = parse_prem_matches(payload, cup, today, end)
        self.assertEqual(["rugby-prem-gallagher-1"], [item["id"] for item in league_events])
        self.assertEqual(["rugby-prem-cup-2"], [item["id"] for item in cup_events])
        self.assertEqual("Exeter Chiefs at Bath Rugby", league_events[0]["name"])
        self.assertEqual("2026-10-02T18:45:00Z", league_events[0]["start_time"])
        with self.assertRaisesRegex(ValueError, "wrong season"):
            parse_prem_matches({"data": [match(6, 1011, season=202501)]}, league, today, end)
        with self.assertRaisesRegex(ValueError, "wrong competition"):
            parse_prem_matches({"data": [match(7, 1297)]}, league, today, end)


if __name__ == "__main__":
    unittest.main()
