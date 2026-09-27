"""FBS/FCS fixtures must never inherit the other subdivision's approval."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from espn_college_football_scope import exclusive_events


def event(number, home="FBS Home", away="FBS Away"):
    return {"id": str(number), "uid": f"s:20~l:23~e:{number}",
            "date": "2026-10-03T19:00Z", "name": f"{away} at {home}",
            "competitions": [{"competitors": [
                {"team": {"displayName": home}}, {"team": {"displayName": away}}]}]}


class EspnCollegeFootballScopeTests(unittest.TestCase):
    def test_both_subdivisions_have_distinct_catalog_sources(self):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        configured = {s["id"]: s for s in sources if s.get("source_type") == "espn-college-football-subdivision"}
        self.assertEqual({"ncaa-football-fbs": "80", "ncaa-football-fcs": "81"},
                         {key: source["espn_group"] for key, source in configured.items()})
        inventory = json.loads((ROOT / "data/priority2-coverage-inventory.json").read_text())
        rows = {row["identity_key"]: row for row in inventory["identities"]}
        for key in configured:
            self.assertEqual("ADAPTER_CONFIGURED", rows[key]["coverage_state"])
        season = json.loads((ROOT / "data/catalog-season-map.json").read_text())
        labels = []
        for sport in season["sports"]:
            for group in sport.get("groups", []):
                labels.extend(e.get("review_label") for e in group.get("events", []) if e.get("key") in configured)
        self.assertEqual({"Division I Football (FBS)", "Division I Football (FCS)"}, set(labels))

    def test_shared_games_are_held_out_of_both_feeds(self):
        fbs = {"groups": ["80"], "events": [event(1), event(3, "LSU", "McNeese")]}
        fcs = {"groups": ["81"], "events": [event(2, "Rhode Island", "Brown"), event(3, "LSU", "McNeese")]}
        fbs_rows, held_fbs = exclusive_events(fbs, fcs, "80")
        fcs_rows, held_fcs = exclusive_events(fcs, fbs, "81")
        self.assertEqual(["1"], [row["id"] for row in fbs_rows])
        self.assertEqual(["2"], [row["id"] for row in fcs_rows])
        self.assertEqual(["3"], [row["id"] for row in held_fbs])
        self.assertEqual(["3"], [row["id"] for row in held_fcs])

    def test_group_drift_or_unnamed_fixture_fails_closed(self):
        fbs = {"groups": ["80"], "events": [event(1)]}
        fcs = {"groups": ["81"], "events": [event(2)]}
        self.assertEqual(1, len(exclusive_events(fbs, fcs, "80")[0]))
        with self.assertRaises(ValueError):
            exclusive_events({**fbs, "groups": ["81"]}, fcs, "80")
        with self.assertRaises(ValueError):
            exclusive_events({**fbs, "events": [event(1)] * 500}, fcs, "80")
        bad = {**event(1), "competitions": [{"competitors": []}]}
        with self.assertRaises(ValueError):
            exclusive_events({**fbs, "events": [bad]}, fcs, "80")


if __name__ == "__main__":
    unittest.main()
