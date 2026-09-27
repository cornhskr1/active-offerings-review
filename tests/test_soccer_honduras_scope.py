"""The Honduras first-team league feed cannot become its reserve competition."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HondurasScopeTests(unittest.TestCase):
    def test_first_team_source_and_alias(self):
        config = json.loads((ROOT / "data/soccer-concacaf-domestic-sources.json").read_text())
        source = next(s for s in config["sources"]
                      if s["id"] == "concacaf-soccer-honduras-liga-nacional-men")
        self.assertEqual("espn-daily", source["source_type"])
        self.assertTrue(source["endpoint"].endswith("/hon.1/scoreboard"))
        self.assertEqual("https://www.lnphn.com/", source["official_schedule_url"])
        self.assertEqual(["Liga Nacional | Men"], source["catalog_terms"])

        aliases = json.loads((ROOT / "data/competition-alias-crosswalk.json").read_text())
        self.assertTrue(any(r.get("identity_key") == "soccer-honduras-liga-nacional-men"
                            and r.get("alias") == "Liga Hondubet"
                            for r in aliases["reviewed_aliases"]))


if __name__ == "__main__":
    unittest.main()
