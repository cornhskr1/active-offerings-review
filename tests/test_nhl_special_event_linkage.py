"""Exact NHL event calendars are not ordinary NHL fixtures or market clearance."""

import ast
from copy import deepcopy
import datetime
import json
from pathlib import Path
import re
import types
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from scripts import audit_priority2_coverage as audit
from scripts.official_window_activity import reviewable_window_start


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CALENDARS = {
    "hockey-usca-nhl-skills": "2027-02-05",
    "hockey-usca-nhl-all-star": "2027-02-06",
}
HOLDS = {"hockey-usca-four-nations", "hockey-usca-nhl-draft"}
KEYS = set(CALENDARS) | HOLDS
FORMAT_URL = "https://www.nhl.com/news/topic/nhl-all-star/nhl-unveils-new-format-for-2027-all-star-weekend"
TIME_URL = "https://www.nhl.com/news/2026-2027-national-tv-schedule-announced"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def calendar_adapter(today):
    """Load only pure helpers, never the collector's network/write main body."""
    filename = ROOT / "scripts" / "refresh_global_schedule.py"
    tree = ast.parse(filename.read_text(encoding="utf-8"), filename=str(filename))
    names = {"tournament_window_event", "fetch_official_event_window"}
    module = ast.Module(
        body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names],
        type_ignores=[],
    )
    get = Mock(return_value=Mock())
    namespace = {
        "datetime": datetime, "re": re, "TODAY": today,
        "END": today + datetime.timedelta(days=7), "TZ": ZoneInfo("America/Chicago"),
        "HEADERS": {}, "requests": types.SimpleNamespace(get=get),
        "reviewable_window_start": reviewable_window_start,
    }
    exec(compile(module, str(filename), "exec"), namespace)
    return namespace["fetch_official_event_window"], get


def fresh_inventory(season_map, config):
    """Build with static inputs and an empty fixed-window fixture, not rolling JSON."""
    rows = audit.catalog_identities(season_map)
    registry = {
        "generated_at": "2026-10-18T00:00:00Z",
        "competitions": [
            {"sport": row["sport"], "league": row["league"],
             "identity_key": row["identity_key"],
             "source_ids": sorted(row["mapped_source_ids"]), "events": []}
            for row in rows.values()
        ],
    }
    fixture = {
        "catalog-season-map.json": season_map,
        "global-schedule-sources.json": config,
        "competition-identity-registry.json": registry,
        "global-schedule.json": {
            "generated_at": "2026-10-18T00:00:00Z", "window_start": "2026-10-18",
            "window_end": "2026-10-25", "events": [], "sources": [], "coverage_gaps": [],
        },
        "catalog-live.json": {"menu_version": "NHL linkage test fixture"},
    }
    with patch.object(audit, "read", side_effect=fixture.__getitem__):
        return audit.build()


class NHLSpecialEventLinkageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season_map = read("catalog-season-map.json")
        cls.config = read("global-schedule-sources.json")
        cls.sources = {source["id"]: source for source in cls.config["sources"]}
        cls.events = {
            event["key"]: event
            for sport in cls.season_map["sports"] if sport["sport"] == "Ice Hockey"
            for group in sport["groups"] for event in group["events"]
        }

    def test_exact_four_sources_do_not_reuse_nhl_or_weekend_approval(self):
        for key in KEYS:
            event, source = self.events[key], self.sources[key]
            self.assertEqual(key, event["source_id"])
            self.assertNotIn("source_ids", event)
            self.assertEqual(event["catalog_event"], source["league"])
            self.assertEqual([event["catalog_event"]], source["catalog_terms"])
            self.assertNotIn("scope_source_ids", source)
            self.assertNotIn("season_start", event)
            self.assertNotIn("season_end", event)
        self.assertEqual("nhl", self.events["hockey-usca-nhl"]["source_id"])
        nhl = self.sources["nhl"]
        self.assertEqual("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard", nhl["endpoint"])
        self.assertFalse(KEYS.intersection(nhl.get("scope_source_ids", [])))
        self.assertNotIn("name_routing", nhl)
        crosswalk = read("competition-alias-crosswalk.json")
        self.assertFalse(any(row["alias"] == "NHL All-Star Weekend" for row in crosswalk["reviewed_aliases"]))
        self.assertTrue(any(row.get("observed_official_name") == "NHL All-Star Weekend" for row in crosswalk["review_queue"]))

    def test_two_exact_published_dates_and_normal_publisher_health(self):
        for key, date in CALENDARS.items():
            event, source = self.events[key], self.sources[key]
            self.assertEqual("official-event-window", source["source_type"])
            self.assertNotIn("endpoint_validation", source)
            self.assertEqual(FORMAT_URL, source["endpoint"])
            self.assertEqual((date, date), (event["season_start_date"], event["season_end_date"]))
            self.assertNotIn("season_status", event)
            self.assertEqual(1, len(source["official_events"]))
            official = source["official_events"][0]
            self.assertEqual(key, official["source_id"])
            self.assertEqual((date, date), (official["start_date"], official["end_date"]))
            self.assertEqual("UBS Arena, Elmont, New York", official["location"])
            self.assertNotIn("start_time", official)

    def test_published_et_times_are_evidence_with_correct_zone_conversion(self):
        expected = {
            "hockey-usca-nhl-skills": ("7 p.m. ET", "2027-02-06T00:00:00Z"),
            "hockey-usca-nhl-all-star": ("3 p.m. ET", "2027-02-06T20:00:00Z"),
        }
        for key, (announced, utc) in expected.items():
            evidence = self.sources[key]["official_events"][0]["published_start_time_evidence"]
            self.assertEqual(announced, evidence["announced_time_et"])
            self.assertEqual("America/New_York", evidence["timezone"])
            self.assertEqual(TIME_URL, evidence["evidence_url"])
            local = datetime.datetime.fromisoformat(evidence["local_datetime"])
            self.assertEqual(local.utcoffset(), local.replace(tzinfo=ZoneInfo(evidence["timezone"])).utcoffset())
            self.assertEqual(utc, local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"))
            self.assertEqual(utc, evidence["utc_datetime"])

    def test_current_october_window_has_no_new_calendar_cards(self):
        fetch, get = calendar_adapter(datetime.date(2026, 10, 18))
        for key in CALENDARS:
            self.assertEqual([], fetch(self.sources[key]))
        self.assertEqual(2, get.call_count)

    def test_calendar_cards_stay_date_only_without_published_kickoff(self):
        fetch, _ = calendar_adapter(datetime.date(2027, 2, 1))
        for key in CALENDARS:
            cards = fetch(self.sources[key])
            self.assertEqual(1, len(cards))
            card = cards[0]
            self.assertTrue(card["date_only"])
            self.assertEqual(key, card["source_id"])
            self.assertEqual(self.sources[key]["league"], card["league"])
            evidence = self.sources[key]["official_events"][0]["published_start_time_evidence"]
            self.assertNotEqual(evidence["utc_datetime"], card["start_time"])
            self.assertNotIn("published_start_time_evidence", card)
            self.assertNotRegex(card["name"], r"\s(?:vs\.?|at)\s")

    def test_expired_calendars_never_roll_into_next_year(self):
        for today in (datetime.date(2027, 2, 7), datetime.date(2028, 2, 1)):
            fetch, get = calendar_adapter(today)
            for key in CALENDARS:
                self.assertEqual([], fetch(self.sources[key]))
            get.assert_not_called()

    def test_publisher_failure_is_not_bypassed(self):
        fetch, get = calendar_adapter(datetime.date(2027, 2, 1))
        get.return_value.raise_for_status.side_effect = RuntimeError("publisher unavailable")
        with self.assertRaisesRegex(RuntimeError, "publisher unavailable"):
            fetch(self.sources["hockey-usca-nhl-all-star"])

    def test_completed_editions_are_explicit_holds_without_calendar_or_time(self):
        for key in HOLDS:
            event, source = self.events[key], self.sources[key]
            self.assertTrue(event["season_hold"])
            self.assertEqual("out", event["season_status"])
            self.assertTrue(event["hold_reason"])
            self.assertEqual("coverage-gap", source["source_type"])
            self.assertNotIn("official_events", source)
            self.assertNotIn("endpoint", source)
            for field in ("season_start_date", "season_end_date", "start_time", "market_close_time"):
                self.assertNotIn(field, event)
                self.assertNotIn(field, source)
        four = self.events["hockey-usca-four-nations"]
        self.assertIn("2025", four["season_window"])
        self.assertIn("World Cup", four["hold_reason"])
        self.assertIn("no annual recurrence", four["season_basis"])

    def test_draft_restriction_is_preserved_not_calculated(self):
        event = self.events["hockey-usca-nhl-draft"]
        self.assertEqual(["MARKETS CLOSE 1 HOUR PRIOR TO EVENT START"], event["restrictions"])
        self.assertIn("never calculate a closing time from date-only evidence", event["hold_reason"])
        self.assertNotIn("Annual June", event["season_window"])
        self.assertIn(event["restrictions"][0], self.sources[event["source_id"]]["source_note"])

    def test_fresh_inventory_distinguishes_two_windows_and_two_holds(self):
        inventory = fresh_inventory(self.season_map, self.config)
        rows = {row["identity_key"]: row for row in inventory["identities"]}
        for key in KEYS:
            row = rows[key]
            self.assertEqual([key], [source["id"] for source in row["sources"]])
            self.assertEqual(0, row["events_in_window"])
            self.assertIsNone(row["sources"][0]["refresh_ok"])
            expected = ("DATED_WINDOW", "OFFICIAL_WINDOW_ONLY") if key in CALENDARS else ("DOCUMENTED_HOLD", "ADAPTER_GAP")
            self.assertEqual(expected, (row["season_state"], row["coverage_state"]))
        baseline_map = deepcopy(self.season_map)
        for sport in baseline_map["sports"]:
            for group in sport.get("groups", []):
                for event in group.get("events", []):
                    if event.get("key") in KEYS:
                        event.pop("source_id")
        before = fresh_inventory(baseline_map, self.config)["summary"]["coverage_states"]
        after = inventory["summary"]["coverage_states"]
        self.assertEqual(before["NO_LINKED_SOURCE"] - 4, after["NO_LINKED_SOURCE"])
        self.assertEqual(before["OFFICIAL_WINDOW_ONLY"] + 2, after["OFFICIAL_WINDOW_ONLY"])
        self.assertEqual(before["ADAPTER_GAP"] + 2, after["ADAPTER_GAP"])
        self.assertEqual(before["ADAPTER_CONFIGURED"], after["ADAPTER_CONFIGURED"])


if __name__ == "__main__":
    unittest.main()
