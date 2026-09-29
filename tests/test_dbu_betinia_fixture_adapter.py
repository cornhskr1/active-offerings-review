"""The Danish second tier remains distinct from Superliga and Oddset Pokalen."""

import json
import unittest
from pathlib import Path

from scripts.dbu_betinia_fixture_adapter import round_fixtures, verified_fixture


ROOT = Path(__file__).resolve().parents[1]


class DbuBetiniaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/soccer-uefa-domestic-sources.json").read_text())["sources"]
        cls.source = next(x for x in sources if x["id"] == "uefa-soccer-denmark-danish-1st-division-men")
        cls.cup = next(x for x in sources if x["id"] == "uefa-soccer-denmark-danish-cup-men")
        cls.overview = (ROOT / "tests/fixtures/dbu_betinia_round_10.html").read_text()
        cls.detail = (ROOT / "tests/fixtures/dbu_betinia_match_173959.html").read_text()

    def test_complete_phase_and_verified_next_round(self):
        fixtures, total = round_fixtures(self.overview, self.source)
        self.assertEqual((6, 132), (len(fixtures), total))
        event = verified_fixture(self.detail, fixtures[0], self.source)
        self.assertEqual("Hvidovre at Vejle Boldklub", event["name"])
        self.assertEqual("2026-10-09T16:00:00Z", event["start_time"])
        self.assertEqual("Danish 1st Division | Men", event["league"])
        self.assertEqual("coverage-gap", self.cup["source_type"])

    def test_missing_or_wrong_competition_fails_closed(self):
        for changed in (self.overview.replace("173959_507530", "173999_507530", 1),
                        self.overview.replace("Betinia LIGA - Grundspil 2026/27", "3F Superliga", 1),
                        self.overview.replace("/resultater/hold/13039_507530", "/resultater/hold/13039_0", 1)):
            with self.assertRaises(ValueError):
                round_fixtures(changed, self.source)
        fixtures, _ = round_fixtures(self.overview, self.source)
        for changed in (self.detail.replace("1. Division", "Superliga", 1),
                        self.detail.replace("Kl. 18:00", "Kl. 19:00", 1),
                        self.detail.replace("Hvidovre", "AaB", 1)):
            with self.assertRaises(ValueError):
                verified_fixture(changed, fixtures[0], self.source)


if __name__ == "__main__":
    unittest.main()
