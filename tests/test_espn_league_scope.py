"""The two new CONCACAF feeds cannot cross leagues or admit unnamed fixtures."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from espn_league_scope import verified_events


class EspnLeagueScopeTest(unittest.TestCase):
    def setUp(self):
        sources = json.loads((ROOT / "data/soccer-concacaf-domestic-sources.json").read_text())["sources"]
        self.sources = {item["id"]: item for item in sources}

    def test_both_approved_leagues_have_distinct_feed_ids(self):
        costa_rica = self.sources["concacaf-soccer-costa-rica-liga-fpd-men"]
        el_salvador = self.sources["concacaf-soccer-el-salvador-primera-division-men"]
        self.assertEqual(("4005", "crc.1"),
                         (costa_rica["espn_league_id"], costa_rica["espn_league_slug"]))
        self.assertEqual(("3943", "slv.1"),
                         (el_salvador["espn_league_id"], el_salvador["espn_league_slug"]))
        self.assertEqual("espn-daily", costa_rica["source_type"])
        self.assertEqual("espn-daily", el_salvador["source_type"])

        inventory = json.loads((ROOT / "data/priority2-coverage-inventory.json").read_text())
        rows = {row["identity_key"]: row for row in inventory["identities"]}
        for key in ("soccer-costa-rica-liga-fpd-men", "soccer-el-salvador-primera-divisi-n-men"):
            self.assertEqual("ADAPTER_CONFIGURED", rows[key]["coverage_state"])
            self.assertEqual("espn-daily", rows[key]["sources"][0]["type"])

    def test_mixed_competition_or_unnamed_match_fails_closed(self):
        source = self.sources["concacaf-soccer-el-salvador-primera-division-men"]
        event = {"id": "123", "uid": "s:600~l:3943~e:123", "date": "2026-10-03T21:00Z",
                 "competitions": [{"competitors": [
                     {"team": {"displayName": "FAS"}},
                     {"team": {"displayName": "Águila"}}]}]}
        payload = {"leagues": [{"id": "3943", "slug": "slv.1"}], "events": [event]}
        self.assertEqual([event], verified_events(payload, source))
        payload["events"] = [{**event, "uid": "s:600~l:4005~e:123"}]
        with self.assertRaises(ValueError):
            verified_events(payload, source)
        payload["events"] = [{**event, "competitions": [{"competitors": []}]}]
        with self.assertRaises(ValueError):
            verified_events(payload, source)
        payload["events"] = []
        payload["leagues"] = [{"id": "4005", "slug": "crc.1"}]
        with self.assertRaises(ValueError):
            verified_events(payload, source)


if __name__ == "__main__":
    unittest.main()
