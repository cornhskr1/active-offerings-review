"""The Canadian women's league and Argentine men's cup keep distinct identities."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SoccerNslCopaScopeTests(unittest.TestCase):
    def test_exact_competition_feeds_and_reviewed_aliases(self):
        canadian = json.loads((ROOT / "data/soccer-concacaf-domestic-sources.json").read_text())
        argentine = json.loads((ROOT / "data/soccer-conmebol-domestic-sources.json").read_text())
        sources = {s["id"]: s for block in (canadian, argentine) for s in block["sources"]}
        expected = {
            "concacaf-soccer-canada-northern-super-league-women": "can.w.nsl",
            "conmebol-soccer-argentina-copa-argentina-men": "arg.copa",
            "conmebol-soccer-colombia-copa-colombia-men": "col.copa",
        }
        for source_id, slug in expected.items():
            with self.subTest(source_id=source_id):
                source = sources[source_id]
                self.assertEqual("espn-daily", source["source_type"])
                self.assertEqual("complete", source["coverage_status"])
                self.assertTrue(source["endpoint"].endswith(f"/{slug}/scoreboard"))
        self.assertNotEqual(sources["conmebol-soccer-argentina-primera-division-men"]["endpoint"],
                            sources["conmebol-soccer-argentina-copa-argentina-men"]["endpoint"])

        aliases = json.loads((ROOT / "data/competition-alias-crosswalk.json").read_text())
        reviewed = {(r.get("identity_key"), r.get("alias")) for r in aliases["reviewed_aliases"]}
        self.assertIn(("soccer-canada-northern-super-league-women", "Northern Super League"), reviewed)
        self.assertIn(("soccer-argentina-copa-argentina-men", "Copa Argentina AXION energy"), reviewed)
        self.assertIn(("soccer-colombia-copa-colombia-men", "Copa BetPlay DIMAYOR"), reviewed)


if __name__ == "__main__":
    unittest.main()
