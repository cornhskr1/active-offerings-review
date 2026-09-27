"""Guatemala's Liga Nacional retains its country and proposition scope."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GuatemalaScopeTests(unittest.TestCase):
    def test_exact_league_source_and_official_alias(self):
        config = json.loads((ROOT / "data/soccer-concacaf-domestic-sources.json").read_text())
        source = next(s for s in config["sources"]
                      if s["id"] == "concacaf-soccer-guatemala-liga-nacional-men")
        self.assertEqual("espn-daily", source["source_type"])
        self.assertTrue(source["endpoint"].endswith("/gua.1/scoreboard"))
        self.assertEqual("https://ligagt.org/calendario/", source["official_schedule_url"])

        season = json.loads((ROOT / "data/catalog-season-map.json").read_text())
        soccer = next(s for s in season["sports"] if s["sport"] == "Soccer")
        item = next(e for g in soccer["groups"] for e in g["events"]
                    if e["key"] == "soccer-guatemala-liga-nacional-men")
        self.assertEqual(source["id"], item["source_id"])
        self.assertIn("NO PROPOSITION WAGERS", item["restrictions"])

        aliases = json.loads((ROOT / "data/competition-alias-crosswalk.json").read_text())
        self.assertTrue(any(r.get("identity_key") == item["key"] and
                            r.get("alias") == "Liga Bantrab"
                            for r in aliases["reviewed_aliases"]))


if __name__ == "__main__":
    unittest.main()
