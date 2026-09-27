"""The RFL senior competition filter cannot import youth or promotion matches."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.rfl_fixture_adapter import parse_rfl_match_centre


ROOT = Path(__file__).resolve().parents[1]
SOURCE = {
    "id": "rugby-rfl-womens-super-league",
    "sport": "Rugby",
    "league": "Women’s Super League | Women",
    "region": "England",
    "division_label": "Betfred Women's Super League",
    "official_schedule_url": "https://www.rugby-league.com/match-centre",
}


def card(match_id, home, away, division, clock="17:30", round_text="Round: Final"):
    return f'''<div data-matchid="" class="card fixture-card">
      <a href="/match-centre/match-preview/{match_id}">
        <span class="team-name d-none d-lg-block">{home}</span>
        <span class="text-center ko d-block">\n {clock}\n</span>
        <span class="team-name d-none d-lg-block">{away}</span>
        <span class="division-label">{division}</span>{round_text}
        <span class="venue-label">Venue: The Brick Community Stadium</span>
      </a></div>'''


class RflFixtureAdapterTests(unittest.TestCase):
    def test_remaining_rfl_competitions_have_distinct_exact_sources(self):
        mapping = json.loads((ROOT / "data" / "catalog-season-map.json").read_text())
        configured = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text())
        sources = {source["id"]: source for source in configured["sources"]}
        expected = {
            "rugby-eng-super-league": ("rugby-rfl-super-league", 1, "Betfred Super League"),
            "rugby-eng-challenge-cup": ("rugby-rfl-challenge-cup", 4, "Betfred Challenge Cup"),
            "rugby-eng-womens-challenge-cup": ("rugby-rfl-womens-challenge-cup", 37, "Betfred Womens Challenge Cup Knock Out Stage"),
            "rugby-eng-world-club-challenge": ("rugby-rfl-world-club-challenge", 45, "World Club Challenge"),
        }
        rugby = next(sport for sport in mapping["sports"] if sport["sport"] == "Rugby")
        events = {event["key"]: event for group in rugby["groups"] for event in group["events"]}
        for key, (source_id, comp_id, label) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(source_id, events[key]["source_id"])
                self.assertIn("rugby-rfl", events[key]["source_ids"])
                self.assertEqual(("rfl-match-centre", comp_id, label),
                                 tuple(sources[source_id][field] for field in
                                       ("source_type", "competition_id", "division_label")))

    def test_cup_stages_fail_closed_on_neighboring_competitions(self):
        sources = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text())
        women = next(source for source in sources["sources"]
                     if source["id"] == "rugby-rfl-womens-challenge-cup")
        page = '<div class="match-centre"><div class="matches"><h3 class="comp-divider">Sat 30th May 2026</h3>' + "".join((
            card(11, "Wigan Warriors", "Leeds Rhinos", "Betfred Womens Challenge Cup Knock Out Stage"),
            card(12, "Wigan Warriors Under 19s", "Leeds Rhinos", "Betfred Womens Challenge Cup Knock Out Stage"),
            card(13, "Hull KR", "Warrington Wolves", "Betfred Challenge Cup"),
            card(14, "Wigan Warriors", "Leeds Rhinos", "Betfred Womens Challenge Cup Under 19s"),
        )) + '</div></div>'
        events = parse_rfl_match_centre(page, women, datetime.date(2026, 5, 30),
                                        datetime.date(2026, 6, 6))
        self.assertEqual(["rugby-rfl-womens-challenge-cup-11"],
                         [event["id"] for event in events])

    def test_admits_final_but_not_promotion_youth_or_other_divisions(self):
        page = '<div class="match-centre"><div class="matches"><h3 class="comp-divider">Sun 27th September 2026</h3>' + "".join((
            card(1, "Wigan Warriors", "York Valkyrie", "Betfred Women's Super League"),
            card(2, "Leigh Leopards", "London Broncos", "Betfred Women's Super League", "15:00", ""),
            card(3, "Wigan Warriors Under 19s", "York Valkyrie Under 19s", "Betfred Women's Super League", "12:00", "Round: 1"),
            card(4, "Wigan Warriors", "York Valkyrie", "Women's Challenge Cup"),
            card(5, "TBC", "York Valkyrie", "Betfred Women's Super League"),
        )) + '</div></div>'
        events = parse_rfl_match_centre(page, SOURCE, datetime.date(2026, 9, 26), datetime.date(2026, 10, 3))
        self.assertEqual(["rugby-rfl-womens-super-league-1"], [event["id"] for event in events])
        self.assertEqual("2026-09-27T16:30:00Z", events[0]["start_time"])
        self.assertEqual(("York Valkyrie at Wigan Warriors", "POSTSEASON"),
                         (events[0]["name"], events[0]["season_stage"]))

    def test_source_scope_retains_shared_rfl_alias_reference(self):
        mapping = json.loads((ROOT / "data" / "catalog-season-map.json").read_text())
        source_config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text())
        rugby = next(sport for sport in mapping["sports"] if sport["sport"] == "Rugby")
        women = next(e for group in rugby["groups"] for e in group["events"]
                     if e["key"] == "rugby-eng-womens-super-league")
        self.assertEqual("rugby-rfl-womens-super-league", women["source_id"])
        self.assertIn("rugby-rfl", women["source_ids"])
        sources = {source["id"]: source for source in source_config["sources"]}
        self.assertEqual((36, 2493, "Betfred Women's Super League"),
                         tuple(sources[women["source_id"]][field]
                               for field in ("competition_id", "division_id", "division_label")))
        self.assertEqual("coverage-gap", sources["rugby-rfl"]["source_type"])
        inventory = json.loads((ROOT / "data" / "priority2-coverage-inventory.json").read_text())
        row = next(row for row in inventory["identities"]
                   if row["identity_key"] == "rugby-eng-womens-super-league")
        self.assertEqual(("DATED_WINDOW", "ADAPTER_CONFIGURED"),
                         (row["season_state"], row["coverage_state"]))
        schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text())
        scoped = [event for event in schedule["events"] if event["source_id"] == women["source_id"]]
        self.assertTrue(all(event["league"] == "Women’s Super League | Women" for event in scoped))

    def test_markup_failure_is_visible_to_refresh(self):
        with self.assertRaises(ValueError):
            parse_rfl_match_centre("<html>empty</html>", SOURCE,
                                   datetime.date(2026, 9, 26), datetime.date(2026, 10, 3))


if __name__ == "__main__":
    unittest.main()
