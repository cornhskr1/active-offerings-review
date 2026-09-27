"""The NWSL cup is a one-match edition, separate from league and Summer Cup."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NwslChallengeCupTests(unittest.TestCase):
    def test_exact_cup_feed_and_corrected_2026_date(self):
        sources = json.loads((ROOT / "data/soccer-concacaf-domestic-sources.json").read_text())
        cup = next(s for s in sources["sources"]
                   if s["id"] == "concacaf-soccer-united-states-nwsl-challenge-cup-women")
        self.assertEqual("espn-daily", cup["source_type"])
        self.assertTrue(cup["endpoint"].endswith("/usa.nwsl.cup/scoreboard"))

        mapping = json.loads((ROOT / "data/catalog-season-map.json").read_text())
        soccer = next(s for s in mapping["sports"] if s["sport"] == "Soccer")
        item = next(e for g in soccer["groups"] for e in g["events"]
                    if e["key"] == "soccer-united-states-nwsl-challenge-cup-women")
        self.assertEqual(("2026-06-26", "2026-06-26"),
                         (item["season_start_date"], item["season_end_date"]))
        self.assertEqual("out", item["season_status"])
        self.assertEqual(cup["id"], item["source_id"])


if __name__ == "__main__":
    unittest.main()
