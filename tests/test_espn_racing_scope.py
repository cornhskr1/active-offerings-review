"""Racing scoreboards preserve exact series scope without team assumptions."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from espn_league_scope import verified_events


class EspnRacingScopeTest(unittest.TestCase):
    def test_four_distinct_series_and_race_without_teams(self):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        racing = {s["id"]: s for s in sources if s.get("espn_event_kind") == "race"}
        self.assertEqual({
            "motorsports-nascar-cup": ("2021", "nascar-premier"),
            "motorsports-nascar-oreilly": ("2022", "nascar-secondary"),
            "motorsports-nascar-truck": ("2023", "nascar-truck"),
            "motorsports-indycar": ("2040", "irl"),
        }, {key: (s["espn_league_id"], s["espn_league_slug"]) for key, s in racing.items()})
        source = racing["motorsports-nascar-truck"]
        event = {"id": "202610160424", "uid": "s:2000~l:2023~e:202610160424",
                 "date": "2026-10-16T23:30Z", "name": "NASCAR Truck Series at Phoenix",
                 "competitions": [{"competitors": []}]}
        payload = {"leagues": [{"id": "2023", "slug": "nascar-truck"}], "events": [event]}
        self.assertEqual([event], verified_events(payload, source))
        payload["events"] = [{**event, "uid": "s:2000~l:2021~e:202610160424"}]
        with self.assertRaises(ValueError):
            verified_events(payload, source)
        payload["events"] = [{**event, "name": ""}]
        with self.assertRaises(ValueError):
            verified_events(payload, source)


if __name__ == "__main__":
    unittest.main()
