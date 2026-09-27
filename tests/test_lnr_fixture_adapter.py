"""LNR's separate senior leagues yield only individual, timed match cards."""

import datetime
import json
import unittest
from pathlib import Path

from scripts.lnr_fixture_adapter import current_round, parse_lnr_round


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {source["id"]: source for source in
           json.loads((ROOT / "data" / "global-schedule-sources.json").read_text())["sources"]}


def card(match_id, home, away, time="14h30"):
    return f'''<div class="match-calendar-line "><div class="match-line">
      <a class="club-line__name base-link--black">{home}</a>
      <p class="match-line__time">{time}</p>
      <a class="club-line__name base-link--black">{away}</a>
      <a href="https://top14.lnr.fr/feuille-de-match/2026-2027/j5/{match_id}-match">Match</a>
      </div></div>'''


class LnrFixtureAdapterTests(unittest.TestCase):
    def test_current_round_requires_unambiguous_score_slider(self):
        self.assertEqual(5, current_round('<score-slider :weeks=\'[{"number":5}]\'></score-slider>'))
        with self.assertRaises(ValueError):
            current_round('<html>no round</html>')

    def test_only_named_timed_match_cards_in_window(self):
        page = '<div class="calendar-results__fixture-date">samedi 03 octobre</div>' + "".join((
            card(11848, "Union Bordeaux-Bègles", "LOU Rugby"),
            card(11849, "TBC", "RC Toulon"),
            card(11850, "Paris Under 19s", "RC Toulon"),
            card(11851, "Stade Toulousain", "RC Toulon", ""),
        ))
        events = parse_lnr_round(page, SOURCES["rugby-lnr-top14"], 2026,
                                 datetime.date(2026, 9, 26), datetime.date(2026, 10, 3))
        self.assertEqual(["rugby-lnr-top14-11848"], [event["id"] for event in events])
        self.assertEqual(("LOU Rugby at Union Bordeaux-Bègles", "2026-10-03T12:30:00Z"),
                         (events[0]["name"], events[0]["start_time"]))

    def test_separate_source_scope_and_legacy_alias_reference(self):
        mapping = json.loads((ROOT / "data" / "catalog-season-map.json").read_text())
        rugby = next(sport for sport in mapping["sports"] if sport["sport"] == "Rugby")
        rows = {event["key"]: event for group in rugby["groups"] for event in group["events"]}
        for key, source_id in (("rugby-fr-top14", "rugby-lnr-top14"),
                               ("rugby-fr-prod2", "rugby-lnr-prod2")):
            self.assertEqual(source_id, rows[key]["source_id"])
            self.assertIn("rugby-lnr", rows[key]["source_ids"])
            self.assertEqual("lnr-fixtures", SOURCES[source_id]["source_type"])


if __name__ == "__main__":
    unittest.main()
