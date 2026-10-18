"""FIGC's timed women's Serie A rounds cannot leak into other competitions."""

import datetime
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402
from figc_serie_a_women_fixture_adapter import (  # noqa: E402
    ROUNDS_2_3_URL, ROUNDS_4_6_URL, parse_figc_rounds,
)


class FigcSerieAWomenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configured_source = next(
            x for x in json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
            if x["id"] == "soccer-italy-serie-a-women"
        )
        cls.old_source = {**cls.configured_source, "endpoint": ROUNDS_2_3_URL,
                          "official_schedule_url": ROUNDS_2_3_URL}
        cls.source = {**cls.configured_source, "endpoint": ROUNDS_4_6_URL,
                      "official_schedule_url": ROUNDS_4_6_URL}
        cls.old_page = (ROOT / "tests/fixtures/figc_serie_a_women_2026_rounds.html").read_text()
        cls.page = (ROOT / "tests/fixtures/figc_serie_a_women_2026_rounds_4_6.html").read_text()

    def parse(self, page=None, source=None, end=datetime.date(2026, 11, 8)):
        return parse_figc_rounds(self.page if page is None else page,
                                self.source if source is None else source, end)

    def test_old_announcement_retains_exact_rounds_and_rome_kickoffs(self):
        events = self.parse(self.old_page, self.old_source, datetime.date(2026, 10, 18))
        self.assertEqual(12, len(events))
        self.assertEqual("Ternana Women at Parma", events[0]["name"])
        self.assertEqual("2026-10-03T10:30:00Z", events[0]["start_time"])
        self.assertEqual("Como 1907 at Napoli Women", events[3]["name"])
        self.assertEqual("Inter at Como Women", events[5]["name"])
        self.assertEqual("2026-10-18T16:00:00Z", events[-1]["start_time"])

    def test_old_announcement_missing_or_duplicate_club_still_fails(self):
        for replacement in ("", "Ore 15: Milan-Parma (DAZN)"):
            with self.subTest(replacement=replacement):
                page = self.old_page.replace("Ore 15: Milan-Juventus (DAZN)", replacement)
                with self.assertRaises(ValueError):
                    self.parse(page, self.old_source, datetime.date(2026, 10, 18))

    def test_new_announcement_preserves_all_eighteen_published_pairings_and_times(self):
        events = self.parse()
        expected = [
            ("Ternana Women at Milan", "2026-10-24T10:30:00Z"),
            ("Inter at Napoli Women", "2026-10-24T14:00:00Z"),
            ("Roma at Juventus", "2026-10-24T16:30:00Z"),
            ("Como Women at Lazio", "2026-10-25T11:30:00Z"),
            ("Sassuolo at Como 1907", "2026-10-25T14:00:00Z"),
            ("Fiorentina at Parma", "2026-10-25T17:00:00Z"),
            ("Como 1907 at Ternana Women", "2026-10-31T11:30:00Z"),
            ("Parma at Sassuolo", "2026-10-31T15:45:00Z"),
            ("Lazio at Inter", "2026-11-01T11:30:00Z"),
            ("Napoli Women at Roma", "2026-11-01T14:00:00Z"),
            ("Milan at Como Women", "2026-11-01T17:00:00Z"),
            ("Juventus at Fiorentina", "2026-11-02T19:30:00Z"),
            ("Roma at Como 1907", "2026-11-07T11:30:00Z"),
            ("Inter at Milan", "2026-11-07T14:00:00Z"),
            ("Sassuolo at Juventus", "2026-11-07T17:00:00Z"),
            ("Como Women at Parma", "2026-11-08T11:30:00Z"),
            ("Fiorentina at Ternana Women", "2026-11-08T14:00:00Z"),
            ("Napoli Women at Lazio", "2026-11-08T17:00:00Z"),
        ]
        self.assertEqual(expected, [(event["name"], event["start_time"]) for event in events])
        self.assertEqual(18, len({event["id"] for event in events}))
        for event in events:
            self.assertEqual("soccer-italy-serie-a-women", event["source_id"])
            self.assertEqual("Serie A | Women", event["league"])
            self.assertEqual(ROUNDS_4_6_URL, event["source_endpoint"])
        self.assertEqual({"r4": 6, "r5": 6, "r6": 6},
                         Counter(event["id"].split("-")[5] for event in events))
        for number in (4, 5, 6):
            clubs = [club for event in events if f"-r{number}-" in event["id"]
                     for club in event["name"].split(" at ")]
            self.assertEqual(12, len(set(clubs)))
            self.assertIn("Como Women", clubs)
            self.assertIn("Como 1907", clubs)

    def test_rome_dst_transition_and_monday_are_not_fixed_offsets(self):
        events = self.parse()
        before = datetime.datetime.fromisoformat(events[0]["start_time"].replace("Z", "+00:00"))
        after = datetime.datetime.fromisoformat(events[3]["start_time"].replace("Z", "+00:00"))
        self.assertEqual(12, before.astimezone(ZoneInfo("Europe/Rome")).hour)
        self.assertEqual(12, after.astimezone(ZoneInfo("Europe/Rome")).hour)
        self.assertEqual(datetime.timedelta(hours=2), before.astimezone(ZoneInfo("Europe/Rome")).utcoffset())
        self.assertEqual(datetime.timedelta(hours=1), after.astimezone(ZoneInfo("Europe/Rome")).utcoffset())
        monday = datetime.datetime.fromisoformat(events[11]["start_time"].replace("Z", "+00:00"))
        self.assertEqual(0, monday.astimezone(ZoneInfo("Europe/Rome")).weekday())
        self.assertEqual("2026-11-02T20:30:00+01:00", monday.astimezone(ZoneInfo("Europe/Rome")).isoformat())
        self.assertEqual("2026-11-02T13:30:00-06:00", monday.astimezone(ZoneInfo("America/Chicago")).isoformat())

    def test_current_october_18_through_25_window_has_six_future_games(self):
        now = datetime.datetime(2026, 10, 18, 17, 30, tzinfo=datetime.timezone.utc)
        today = now.astimezone(ZoneInfo("America/Chicago")).date()
        end = today + datetime.timedelta(days=7)
        events = self.parse(end=end)
        current = [event for event in events
                   if now < (start := datetime.datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")))
                   and today <= start.astimezone(ZoneInfo("America/Chicago")).date() <= end]
        self.assertEqual(6, len(current))
        self.assertTrue(all("-r4-" in event["id"] for event in current))
        self.assertEqual({"2026-10-24", "2026-10-25"}, {event["start_time"][:10] for event in current})

    def test_each_announcement_fails_beyond_its_own_published_horizon(self):
        for page, source, end in (
            (self.old_page, self.old_source, datetime.date(2026, 10, 19)),
            (self.page, self.source, datetime.date(2026, 11, 9)),
        ):
            with self.subTest(end=end):
                with self.assertRaisesRegex(ValueError, "full review window"):
                    self.parse(page, source, end)

    def test_endpoint_and_announcement_must_match(self):
        for page, source in (
            (self.old_page, self.source),
            (self.page, self.old_source),
            (self.page, {**self.source, "endpoint": "https://www.figc.it/unreviewed"}),
        ):
            with self.subTest(endpoint=source["endpoint"]):
                with self.assertRaises(ValueError):
                    self.parse(page, source)

    def test_wrong_source_identity_fails_even_when_catalog_terms_are_unchanged(self):
        for field, value in (
            ("id", "soccer-italy-serie-a-men"),
            ("id", "soccer-italy-coppa-italia-women"),
            ("league", "Serie A | Men"),
            ("league", "Supercoppa Italiana | Women"),
            ("sport", "Rugby"),
            ("region", "England"),
            ("source_type", "official-cup-fixtures"),
            ("catalog_terms", ["Coppa Italia | Men and Women"]),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, "exact women’s Serie A child"):
                    self.parse(source={**self.source, field: value})

    def test_wrong_competition_or_season_in_article_fails(self):
        for heading in ("COPPA ITALIA WOMEN 2026-27", "SERIE A MEN ATHORA 2026-27",
                        "SERIE A WOMEN ATHORA 2025-26", "PRIMAVERA WOMEN 2026-27"):
            with self.subTest(heading=heading):
                with self.assertRaises(ValueError):
                    self.parse(self.page.replace("SERIE A WOMEN ATHORA 2026-27", heading))

    def test_duplicate_pairing_club_day_or_round_fails(self):
        for original, replacement in (
            ("Milan-Ternana Women", "Milan-Milan"),
            ("Napoli Women-Inter", "Milan-Inter"),
            ("6ª giornata", "5ª giornata"),
            ("Domenica 25 ottobre", "Sabato 24 ottobre"),
            ("Ore 18: Lazio-Napoli Women", "Ore 18: Milan-Napoli Women"),
        ):
            with self.subTest(replacement=replacement):
                self.assertIn(original, self.page)
                with self.assertRaises(ValueError):
                    self.parse(self.page.replace(original, replacement))

    def test_missing_or_malformed_late_row_never_returns_partial_events(self):
        for original, replacement in (
            ("Ore 18: Lazio-Napoli Women\xa0(DAZN)", ""),
            ("Ore 18: Lazio-Napoli Women", "Ore TBD: Lazio-Napoli Women"),
            ("Ore 18: Lazio-Napoli Women", "Ore 25: Lazio-Napoli Women"),
            ("Lazio-Napoli Women", "Lazio-TBD"),
            ("Lazio-Napoli Women", "Lazio-Unknown Club"),
            ("Lazio-Napoli Women", "Lazio-"),
        ):
            with self.subTest(replacement=replacement):
                self.assertIn(original, self.page)
                with self.assertRaises(ValueError):
                    self.parse(self.page.replace(original, replacement))

    def test_round_four_still_requires_six_fixtures_and_twelve_clubs(self):
        page = self.page.replace("Ore 18: Parma-Fiorentina (DAZN)", "")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.parse(page)

    def test_unpublished_or_out_of_order_dates_fail(self):
        for original, replacement in (
            ("Lunedì 2 novembre", "Domenica 2 novembre"),
            ("Lunedì 2 novembre", "Lunedì 9 novembre"),
            ("Domenica 25 ottobre", "Domenica 26 ottobre"),
            ("Domenica 25 ottobre", "Domenica 8 novembre"),
        ):
            with self.subTest(replacement=replacement):
                with self.assertRaises(ValueError):
                    self.parse(self.page.replace(original, replacement))

    def test_missing_or_repeated_schedule_fails(self):
        schedule = self.page[self.page.index("<p>"):self.page.index("</article>")]
        for page in ("", self.page.replace("SERIE A WOMEN ATHORA 2026-27", "MISSING"),
                     self.page.replace("</article>", schedule + "</article>")):
            with self.subTest(length=len(page)):
                with self.assertRaises(ValueError):
                    self.parse(page)

    def test_cup_and_supercoppa_remain_gaps_and_league_coverage_stays_partial(self):
        rows = {x["identity_key"]: x for x in build()["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-italy-serie-a-women"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-italy-coppa-italia-women"]["coverage_state"])
        self.assertEqual("ADAPTER_GAP", rows["soccer-italy-supercoppa-italiana-women"]["coverage_state"])
        self.assertEqual("partial", self.configured_source["coverage_status"])
        self.assertEqual(ROUNDS_4_6_URL, self.configured_source["endpoint"])
        self.assertEqual(ROUNDS_4_6_URL, self.configured_source["official_schedule_url"])


if __name__ == "__main__":
    unittest.main()
