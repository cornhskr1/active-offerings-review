"""NCAA's Division I scoreboard must not publish shared lower-division games."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from official_ncaa_scoreboard import scoreboard_query, exact_contests, event_from_contest


def contest(number, home="Omaha", away="Neb. Wesleyan", timed=True):
    return {"contestId": number, "startDate": "10/03/2026", "startTimeEpoch": 1791072000,
            "hasStartTime": timed, "tba": False, "gameState": "P",
            "statusCodeDisplay": "pre", "teams": [
                {"isHome": True, "nameShort": home},
                {"isHome": False, "nameShort": away}]}


class OfficialNcaaScoreboardTests(unittest.TestCase):
    def test_three_exact_catalog_children_use_official_division_one_pages(self):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        configured = {s["id"]: s for s in sources}
        expected = {"ncaa-soccer-di-men": ("soccer-men", "MSO"),
                    "ncaa-soccer-di-women": ("soccer-women", "WSO"),
                    "ncaa-field-hockey-di": ("fieldhockey", "WFH")}
        for key, (sport, code) in expected.items():
            source = configured[key]
            self.assertEqual("official-ncaa-division-one", source["source_type"])
            self.assertEqual(f"https://www.ncaa.com/scoreboard/{sport}/d1", source["endpoint"])
            self.assertEqual(code, source["ncaa_sport_code"])
            self.assertEqual("partial", source["coverage_status"])

    def test_scope_and_overlap_hold_shared_contests(self):
        url = "https://sdataprod.ncaa.com?meta=GetContests_web&extensions=%7B%7D"
        settings = {"scoreboardWidget": {"widgets": [{"sportCode": "MSO",
                    "division": "d1", "seasonYear": 2026}]},
                    "scoreboard": {"contestsDataUrl": url}}
        page = '<script type="application/json" data-drupal-selector="drupal-settings-json">' + json.dumps(settings) + '</script>'
        self.assertEqual((url, 2026), scoreboard_query(page, "MSO"))
        settings["scoreboardWidget"]["widgets"][0]["division"] = "d3"
        with self.assertRaises(ValueError):
            scoreboard_query(page.replace('"d1"', '"d3"'), "MSO")

        payloads = {1: {"data": {"contests": [contest(1), contest(2, "Stanford", "UCLA"),
                                                contest(3, "Brown", "Yale", timed=False)]}},
                    2: {"data": {"contests": []}},
                    3: {"data": {"contests": [contest(1)]}}}
        approved, crossover, untimed = exact_contests(payloads, __import__("datetime").date(2026, 10, 3))
        self.assertEqual([2], [e["contestId"] for e in approved])
        self.assertEqual([1], [e["contestId"] for e in crossover])
        self.assertEqual([3], [e["contestId"] for e in untimed])
        source = {"id": "ncaa-soccer-di-men", "sport": "NCAA Soccer",
                  "league": "Division I Soccer | Men", "region": "United States", "endpoint": url}
        self.assertEqual("UCLA at Stanford", event_from_contest(source, approved[0])["name"])
        with self.assertRaises(ValueError):
            exact_contests({**payloads, 3: {"errors": [{"message": "failed"}]}},
                           __import__("datetime").date(2026, 10, 3))


if __name__ == "__main__":
    unittest.main()
