"""Estonian and Latvian calendar editions remain distinct."""

import json
import unittest
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


class EstoniaLatviaScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soccer = next(s for s in json.loads((DATA / "catalog-season-map.json").read_text())["sports"] if s["sport"] == "Soccer")
        cls.events = {e["key"]: e for g in soccer["groups"] if g.get("country") in {"Estonia", "Latvia"} for e in g["events"]}
        cls.inventory = {x["identity_key"]: x for x in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}

    def test_six_distinct_sources(self):
        self.assertEqual(6, len(self.events))
        self.assertEqual(6, len({e["source_id"] for e in self.events.values()}))
        for key, event in self.events.items():
            self.assertEqual(event["source_id"], self.inventory[key]["sources"][0]["id"])

    def test_cup_editions_and_final_bounds(self):
        estonian = self.events["soccer-estonia-estonian-cup-tipneri-karikas-men"]
        latvian = self.events["soccer-latvia-latvian-cup-latvijas-kauss-men"]
        self.assertEqual("2026-06-10", estonian["season_start_date"])
        self.assertFalse(estonian["season_window_complete"])
        self.assertNotIn("season_end_date", estonian)
        self.assertEqual(("2026-05-15", "2026-11-20"), (latvian["season_start_date"], latvian["season_end_date"]))

    def test_league_qualification_and_completed_senior_supercups(self):
        for country, league_key, date in (("estonia", "soccer-estonia-meistriliiga-premium-liiga-men", "2026-02-28"), ("latvia", "soccer-latvia-latvian-higher-league-virsl-ga-men", "2026-02-17")):
            league = self.events[league_key]
            self.assertFalse(league["season_window_complete"])
            cup = next(e for k, e in self.events.items() if k.startswith(f"soccer-{country}-") and "super" in k)
            self.assertEqual((date, date), (cup["season_start_date"], cup["season_end_date"]))
            self.assertEqual("OFFICIAL_WINDOW_ONLY", self.inventory[cup["key"]]["coverage_state"])


if __name__ == "__main__":
    unittest.main()
