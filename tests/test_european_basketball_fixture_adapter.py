"""Complete official men's EuroLeague/EuroCup schedules must not silently drift."""

import copy
import datetime
import json
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from european_basketball_fixture_adapter import (  # noqa: E402
    parse_fixtures, source_config, validate_review_window,
)


def captured_payload(season):
    fixture = json.loads((ROOT / "tests/fixtures/european_basketball_2026_schedule.json").read_text())
    captured = fixture["seasons"][season]
    games = []
    for row in captured["games"]:
        game = copy.deepcopy(captured["common_game"])
        game.update(dict(zip(fixture["columns"], row)))
        game["identifier"] = f"{season}_{game['gameCode']}"
        game["group"] = copy.deepcopy(captured["groups"][game["group"]])
        for side in ("local", "road"):
            game[side] = {"club": copy.deepcopy(captured["clubs"][game[side]])}
        games.append(game)
    return {"total": captured["total"], "data": games}


class EuropeanBasketballFixtureTests(unittest.TestCase):
    def setUp(self):
        self.el = source_config("basketball-euroleague")
        self.ec = source_config("eurocup-basketball")
        self.el_payload = captured_payload("E2026")
        self.ec_payload = captured_payload("U2026")

    @staticmethod
    def week(events, start="2026-10-18", end="2026-10-25"):
        return [event for event in events if start <= datetime.datetime.fromisoformat(
            event["start_time"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("America/Chicago")).date().isoformat() <= end]

    def test_complete_live_snapshots_and_review_counts(self):
        for source, payload, remaining, count in ((self.el, self.el_payload, 320, 10),
                                                   (self.ec, self.ec_payload, 176, 16)):
            with self.subTest(source=source["id"]):
                events = parse_fixtures(payload, source)
                self.assertEqual(remaining, len(events))
                self.assertEqual(count, len(self.week(events)))
                self.assertTrue(all(event["source_id"] == source["id"] for event in events))
                self.assertTrue(all(event["season_stage"] == "REGULAR" for event in events))
                self.assertTrue(all(event["coverage_status"] == "partial" for event in events))
                self.assertEqual(len(events), len({event["id"] for event in events}))

    def test_exact_game_identity_time_and_current_venue_change(self):
        events = parse_fixtures(self.el_payload, self.el)
        event = next(event for event in events if event["id"] == "euroleague-basketball-E2026-61")
        self.assertEqual("Virtus Bologna at Hapoel IBI Tel Aviv", event["name"])
        # Current live UTC time differs from the preseason PDF, which said 17:00.
        self.assertEqual("2026-10-21T16:00:00Z", event["start_time"])
        self.assertEqual("https://mediagamecenter.euroleague.net/E2026/61", event["source_endpoint"])
        self.assertEqual(event["source_endpoint"], event["source_url"])

    def test_cup_identity_does_not_become_league_or_womens_competition(self):
        event = self.week(parse_fixtures(self.ec_payload, self.ec))[0]
        self.assertEqual("EuroCup | Men", event["league"])
        self.assertEqual("U2026", event["season_code"])
        self.assertEqual("U", event["competition_code"])
        self.assertEqual("Europe", event["region"])
        with self.assertRaisesRegex(ValueError, "competition or season"):
            parse_fixtures({"total": 224, "data": self.el_payload["data"][:224]}, self.ec)

    def test_regular_season_boundaries_and_known_empty_week(self):
        for source in (self.el, self.ec):
            validate_review_window(source, datetime.date(2026, 10, 18), datetime.date(2026, 10, 25))
            first, last = (datetime.date.fromisoformat(source[key]) for key in ("coverage_start", "coverage_end"))
            validate_review_window(source, first, last)
            for start, end in ((first - datetime.timedelta(days=1), first),
                               (last, last + datetime.timedelta(days=1)), (last, first)):
                with self.assertRaises(ValueError):
                    validate_review_window(source, start, end)
        validate_review_window(self.ec, datetime.date(2026, 11, 22), datetime.date(2026, 11, 29))
        self.assertEqual([], self.week(parse_fixtures(self.ec_payload, self.ec), "2026-11-22", "2026-11-29"))

    def test_partial_empty_or_duplicate_payload_is_not_healthy(self):
        bad_payloads = [None, [], {}, {"total": 380, "data": []},
                        {"total": 379, "data": self.el_payload["data"][:-1]},
                        {"total": 380, "data": self.el_payload["data"][:-1]}]
        duplicate = copy.deepcopy(self.el_payload)
        duplicate["data"][0] = copy.deepcopy(duplicate["data"][1])
        bad_payloads.append(duplicate)
        for payload in bad_payloads:
            with self.subTest(payload_type=type(payload).__name__), self.assertRaises(ValueError):
                parse_fixtures(payload, self.el)

    def test_source_identity_season_and_endpoint_are_pinned(self):
        for field, bad in (("id", "basketball-womens-euroleague"),
                           ("catalog_terms", ["EuroLeague | Women"]),
                           ("league", "EuroCup | Men"), ("sport", "Soccer"),
                           ("region", "Spain"),
                           ("season_code", "E2025"), ("competition_code", "SC"),
                           ("endpoint", "https://example.com/api/games?seasonCode=E2026"),
                           ("coverage_end", "2027-05-30"), ("schedule_scope", "all-phases")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_fixtures(self.el_payload, {**self.el, field: bad})

    def test_payload_competition_season_phase_and_identity_changes_fail(self):
        mutations = [
            lambda g: g["season"].update(code="E2025"),
            lambda g: g["season"].update(competitionCode="U"),
            lambda g: g["season"].update(alias="2025-26"),
            lambda g: g["phaseType"].update(code="PO"),
            lambda g: g["group"].update(rawName="NextGen"),
            lambda g: g.update(identifier="U2026_379"),
            lambda g: g.update(gameCode=True),
            lambda g: g.update(round=39),
            lambda g: g.update(confirmedDate=False),
            lambda g: g.update(confirmedHour=False),
            lambda g: g.update(gameStatus="Cancelled"),
            lambda g: g.update(played="false"),
            lambda g: g["local"]["club"].update(isVirtual=True),
            lambda g: g["local"]["club"].update(name="TBD"),
            lambda g: g["local"]["club"].update(name="U18 Barcelona"),
            lambda g: g.update(road=copy.deepcopy(g["local"])),
        ]
        for index, mutate in enumerate(mutations):
            payload = copy.deepcopy(self.el_payload)
            mutate(payload["data"][0])
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                parse_fixtures(payload, self.el)

    def test_timezone_or_calendar_ambiguity_fails_closed(self):
        mutations = [
            {"utcDate": "2027-04-16T18:30:00"},
            {"utcDate": "2027-04-16T18:30:00+02:00"},
            {"utcDate": "2027-02-30T18:30:00Z"},
            {"utcDate": "2027-04-16T19:30:00Z"},
            {"localDate": "2027-04-16T20:30:00Z"},
            {"localTimeZone": None}, {"localTimeZone": True},
            {"localTimeZone": float("nan")}, {"localTimeZone": 15},
            {"utcDate": "2025-04-16T18:30:00Z", "localDate": "2025-04-16T20:30:00"},
        ]
        for values in mutations:
            payload = copy.deepcopy(self.el_payload)
            payload["data"][0].update(values)
            with self.subTest(values=values), self.assertRaises(ValueError):
                parse_fixtures(payload, self.el)

    def test_completed_games_never_return_as_upcoming(self):
        all_completed = copy.deepcopy(self.el_payload)
        for game in all_completed["data"]:
            game["played"] = True
        self.assertEqual([], parse_fixtures(all_completed, self.el))

    def test_full_round_structure_and_club_names_must_reconcile(self):
        payload = copy.deepcopy(self.el_payload)
        payload["data"][0]["round"] = 1
        with self.assertRaisesRegex(ValueError, "structure"):
            parse_fixtures(payload, self.el)
        payload = copy.deepcopy(self.el_payload)
        payload["data"][0]["local"]["club"]["name"] = "Different Barcelona"
        with self.assertRaisesRegex(ValueError, "conflicting names"):
            parse_fixtures(payload, self.el)
        payload = copy.deepcopy(self.ec_payload)
        payload["data"][0]["group"]["rawName"] = "A"
        with self.assertRaisesRegex(ValueError, "crossed competition groups"):
            parse_fixtures(payload, self.ec)


if __name__ == "__main__":
    unittest.main()
