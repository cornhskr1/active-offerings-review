"""Brazil's one-match Supercopa retains its event date and market restriction."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrazilSupercopaTests(unittest.TestCase):
    def test_exact_single_match_feed_and_date(self):
        block = json.loads((ROOT / "data/soccer-conmebol-domestic-sources.json").read_text())
        source = next(s for s in block["sources"]
                      if s["id"] == "conmebol-soccer-brazil-supercopa-do-brasil-men")
        self.assertEqual("espn-daily", source["source_type"])
        self.assertTrue(source["endpoint"].endswith("/bra.supercopa_do_brazil/scoreboard"))

        mapping = json.loads((ROOT / "data/catalog-season-map.json").read_text())
        soccer = next(s for s in mapping["sports"] if s["sport"] == "Soccer")
        item = next(e for g in soccer["groups"] for e in g["events"]
                    if e["key"] == "soccer-brazil-supercopa-do-brasil-men")
        self.assertEqual(("2026-02-01", "2026-02-01"),
                         (item["season_start_date"], item["season_end_date"]))
        self.assertIn("NO PROPOSITION WAGERS", item["restrictions"])
        self.assertEqual(source["id"], item["source_id"])


if __name__ == "__main__":
    unittest.main()
