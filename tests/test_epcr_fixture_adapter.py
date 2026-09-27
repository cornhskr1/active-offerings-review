"""EPCR fixture feeds remain separate and reject adjacent or incomplete cards."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.epcr_fixture_adapter import parse_epcr_matches


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {s["id"]: s for s in json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]}


def page(comp_id=1008, comp_name="Investec Champions Cup", away="Bordeaux-Begles", status="fixture"):
    # Nuxt's flattened data format: object properties refer to array positions.
    payload = [None] * 22
    payload[3] = {"fixtures-and-results-champions-cup": 5}
    payload[5] = [6]
    payload[6] = {"id": 7, "date": 8, "status": 9, "compId": 10,
                  "compName": 11, "homeTeam": 12, "awayTeam": 13,
                  "tbc": 14, "roundTypeId": 15}
    payload[7:16] = [293317, "2026-10-16T19:00:00.000Z", status, comp_id,
                      comp_name, {"name": 16}, {"name": 17}, 0, 1]
    payload[16:18] = ["Gloucester Rugby", away]
    return '<script id="__NUXT_DATA__" type="application/json">' + json.dumps(payload) + '</script>'


class EpcrFixtureAdapterTests(unittest.TestCase):
    def test_exact_competition_and_named_future_fixture(self):
        source = SOURCES["rugby-epcr-champions"]
        window = (datetime.date(2026, 10, 16), datetime.date(2026, 10, 23))
        events = parse_epcr_matches(page(), source, *window)
        self.assertEqual(["rugby-epcr-champions-293317"], [e["id"] for e in events])
        self.assertEqual("Bordeaux-Begles at Gloucester Rugby", events[0]["name"])
        for altered in (page(comp_id=1026), page(comp_name="European Challenge Cup"),
                        page(away="TBC"), page(status="result")):
            self.assertEqual([], parse_epcr_matches(altered, source, *window))
        self.assertEqual([], parse_epcr_matches(page(), source, datetime.date(2026, 9, 27), datetime.date(2026, 10, 4)))
        with self.assertRaises(ValueError):
            parse_epcr_matches("<html></html>", source, *window)

    def test_catalog_sources_and_aliases(self):
        rugby = next(s for s in json.loads((ROOT / "data/catalog-season-map.json").read_text())["sports"] if s["sport"] == "Rugby")
        rows = {e["key"]: e for g in rugby["groups"] for e in g["events"]}
        for key, source_id in (("rugby-eu-champions-cup", "rugby-epcr-champions"),
                               ("rugby-eu-challenge-cup", "rugby-epcr-challenge")):
            self.assertEqual(source_id, rows[key]["source_id"])
            self.assertIn("rugby-epcr", rows[key]["source_ids"])
            self.assertEqual("epcr-fixtures", SOURCES[source_id]["source_type"])
        aliases = json.loads((ROOT / "data/competition-alias-crosswalk.json").read_text())["reviewed_aliases"]
        self.assertTrue(any(a.get("alias") == "Investec Champions Cup" for a in aliases))


if __name__ == "__main__":
    unittest.main()
