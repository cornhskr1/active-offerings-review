"""The Priority 2 inventory keeps legal identities and schedule evidence separate."""

import json
import unittest
from pathlib import Path

from sys import path as sys_path


ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(ROOT / "scripts"))
from audit_priority2_coverage import build  # noqa: E402


class Priority2CoverageInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = build()
        cls.rows = {(row["sport"], row["league"]): row for row in cls.inventory["identities"]}

    def test_split_parent_does_not_become_a_schedule_identity(self):
        self.assertNotIn(("NCAA Water Polo", "Division I Water Polo | Men and Women"), self.rows)
        for division in ("Men", "Women"):
            row = self.rows[("NCAA Water Polo", f"Division I Water Polo | {division}")]
            self.assertEqual("split-child", row["kind"])
            self.assertEqual("NO_LINKED_SOURCE", row["coverage_state"])
            self.assertEqual("PENDING_DATES", row["season_state"])
            self.assertEqual([], row["sources"])

    def test_complete_world_cup_window_and_gap_do_not_pretend_to_be_fixture_adapter(self):
        row = self.rows[("Basketball", "FIBA Basketball World Cup | Men")]
        self.assertEqual("ADAPTER_GAP", row["coverage_state"])
        self.assertEqual("DATED_WINDOW", row["season_state"])
        self.assertEqual("November 24, 2025–September 12, 2027, including six qualifier windows and the finals", row["season_window"])
        self.assertEqual("coverage-gap", row["sources"][0]["type"])
        afl = self.rows[("Aussie Rules", "Australian Football League (AFL)")]
        self.assertEqual("ADAPTER_CONFIGURED", afl["coverage_state"])

    def test_chile_league_and_cup_keep_distinct_schedule_gaps(self):
        expected = {
            "Liga Nacional de Basquetbol de Chile (LNB) | Men": "chile-lnb",
            "Copa Chile | Men": "chile-copa",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("ADAPTER_GAP", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])

    def test_fiba_3x3_tour_keeps_mens_calendar_and_womens_scope_hold_separate(self):
        men = self.rows[("Basketball", "FIBA 3x3 World Tour | Men")]
        self.assertEqual("DATED_WINDOW", men["season_state"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", men["coverage_state"])
        self.assertEqual(
            [{
                "id": "basketball-fiba-3x3-tour-men",
                "type": "official-event-window",
                "configured_league": "FIBA 3x3 World Tour | Men",
                "refresh_ok": True,
                "events_in_window": 1,
            }],
            men["sources"],
        )

        women = self.rows[("Basketball", "FIBA 3x3 World Tour | Women")]
        self.assertEqual("DOCUMENTED_HOLD", women["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", women["coverage_state"])
        self.assertEqual([], women["sources"])
        self.assertIn("identity mismatch", women["hold_reason"])

    def test_afrobasket_divisions_keep_separate_official_windows(self):
        expected = {
            "FIBA AfroBasket | Men": "basketball-afrobasket-men",
            "FIBA AfroBasket | Women": "basketball-afrobasket-women",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual(
                    [{
                        "id": source_id,
                        "type": "official-event-window",
                        "configured_league": league,
                        "refresh_ok": True,
                        "events_in_window": 0,
                    }],
                    row["sources"],
                )

    def test_americup_divisions_keep_separate_official_windows(self):
        expected = {
            "FIBA AmeriCup | Men": "basketball-americup-men",
            "FIBA AmeriCup | Women": "basketball-americup-women",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual(
                    [{
                        "id": source_id,
                        "type": "official-event-window",
                        "configured_league": league,
                        "refresh_ok": True,
                        "events_in_window": 0,
                    }],
                    row["sources"],
                )

    def test_fiba_continental_and_oceania_windows_stay_division_specific(self):
        expected = {
            "FIBA Asia Cup | Men": "basketball-asia-cup-men",
            "FIBA Asia Cup | Women": "basketball-asia-cup-women",
            "FIBA EuroBasket | Men": "basketball-eurobasket-men",
            "FIBA EuroBasket | Women": "basketball-eurobasket-women",
            "FIBA Melanesia Cup | Men": "basketball-melanesia-men",
            "FIBA Melanesia Cup | Women": "basketball-melanesia-women",
            "FIBA Micronesia Cup | Men": "basketball-micronesia-men",
            "FIBA Micronesia Cup | Women": "basketball-micronesia-women",
            "FIBA Polynesian Basketball Cup | Men": "basketball-polynesian-men",
            "FIBA Polynesian Basketball Cup | Women": "basketball-polynesian-women",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

    def test_pacific_and_south_american_divisions_use_official_windows(self):
        expected = {
            "Pacific Games | Men": "basketball-pacific-games-men",
            "Pacific Games | Women": "basketball-pacific-games-women",
            "South American Championship | Men": "basketball-south-american-men",
            "South American Championship | Women": "basketball-south-american-women",
        }
        for league, source_id in expected.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])

    def test_tbt_mens_window_and_womens_scope_hold_remain_separate(self):
        men = self.rows[("Basketball", "The Basketball Tournament (TBT) | Men")]
        self.assertEqual("DATED_WINDOW", men["season_state"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", men["coverage_state"])
        self.assertEqual(["basketball-us-tbt-men"], [source["id"] for source in men["sources"]])

        women = self.rows[("Basketball", "The Basketball Tournament (TBT) | Women")]
        self.assertEqual("DOCUMENTED_HOLD", women["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", women["coverage_state"])
        self.assertEqual([], women["sources"])
        self.assertIn("women's TBT", women["hold_reason"])

    def test_basketball_date_reconciliation_is_complete(self):
        basketball = self.inventory["by_sport"]["Basketball"]
        self.assertEqual(89, basketball["identities"])
        self.assertEqual(6, basketball["no_linked_source"])
        self.assertEqual(0, basketball["pending_dates"])
        self.assertEqual(6, sum(row["season_state"] == "DOCUMENTED_HOLD" for row in self.rows.values() if row["sport"] == "Basketball"))

    def test_first_basketball_source_batch_uses_exact_official_windows_or_hold(self):
        expected_windows = {
            "BBL-Pokal | Men": "basketball-de-cup",
            "BIG3 | Men": "basketball-us-big3",
            "Caribbean Women's Championship | Women": "basketball-caribbean-women",
            "Central American Women's Championship | Women": "basketball-central-american-women",
            "Centrobasket Women's Championship | Women": "basketball-centrobasket-women",
        }
        for league, source_id in expected_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        champions = self.rows[("Basketball", "BBL Champions Cup")]
        self.assertEqual("DOCUMENTED_HOLD", champions["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", champions["coverage_state"])
        self.assertIn("no BBL Champions Cup", champions["hold_reason"])

    def test_second_basketball_source_batch_uses_exact_official_windows_or_hold(self):
        expected_windows = {
            "Commissioner’s Cup | Men": "basketball-ph-commissioners",
            "Copa Super 8 | Men": "basketball-br-super8",
            "Copa del Rey | Men": "basketball-es-copa",
            "Coppa Italia | Men": "basketball-it-cup",
            "EuroLeague | Men": "basketball-euroleague",
        }
        for league, source_id in expected_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        danish = self.rows[("Basketball", "Danish Cup | Men")]
        self.assertEqual("DOCUMENTED_HOLD", danish["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", danish["coverage_state"])
        self.assertEqual([], danish["sources"])
        self.assertIn("full Danish Cup schedule", danish["hold_reason"])

    def test_third_basketball_source_batch_uses_official_windows(self):
        dated_windows = {
            "FIBA Women's EuroLeague | Women": "basketball-womens-euroleague",
            "French Cup | Men": "basketball-fr-cup",
            "Greek Cup | Men": "basketball-gr-cup",
            "Greek Super Cup | Men": "basketball-gr-supercup",
            "Ignite Cup | Men": "basketball-au-ignite",
        }
        for league, source_id in dated_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        governors = self.rows[("Basketball", "Governor’s Cup | Men")]
        self.assertEqual("DESCRIPTIVE_WINDOW", governors["season_state"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", governors["coverage_state"])
        self.assertEqual(
            ["basketball-ph-governors"],
            [source["id"] for source in governors["sources"]],
        )
        self.assertIn("October 18", governors["season_window"])

    def test_fourth_basketball_source_batch_uses_exact_scoped_evidence_or_hold(self):
        dated_windows = {
            "King Mindaugas Cup | Men": "basketball-lt-cup",
            "NBA Draft": "basketball-us-nba-draft",
        }
        for league, source_id in dated_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        descriptive_windows = {
            "League Cup | Men": "basketball-il-league-cup",
            "Liga Nacional de Básquet (LNB) | Men": "basketball-ar-lnb",
        }
        for league, source_id in descriptive_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DESCRIPTIVE_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])

        holds = {
            "KBL Cup | Men": "has not published a 2026 KBL Cup schedule",
            "NBA Preseason Games v. International Teams": "no matchup against a non-NBA international club",
        }
        for league, reason in holds.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DOCUMENTED_HOLD", row["season_state"])
                self.assertEqual("NO_LINKED_SOURCE", row["coverage_state"])
                self.assertEqual([], row["sources"])
                self.assertIn(reason, row["hold_reason"])

        self.assertEqual(6, self.inventory["by_sport"]["Basketball"]["no_linked_source"])
        self.assertEqual(0, self.inventory["by_sport"]["Basketball"]["pending_dates"])

    def test_fifth_basketball_source_batch_uses_exact_or_descriptive_official_windows(self):
        dated_windows = {
            "Philippine Cup | Men": "basketball-ph-philippine-cup",
            "Polish Cup | Men": "basketball-pl-cup",
            "Polish Supercup | Men": "basketball-pl-supercup",
            "Presidential Cup | Men": "basketball-tr-presidential",
        }
        for league, source_id in dated_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        descriptive_windows = {
            "Novo Basquete Brasil (NBB) | Men": "basketball-br-nbb",
            "Philippine Basketball Association (PBA) | Men": "basketball-ph-pba",
        }
        for league, source_id in descriptive_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DESCRIPTIVE_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        self.assertEqual(6, self.inventory["by_sport"]["Basketball"]["no_linked_source"])
        self.assertEqual(0, self.inventory["by_sport"]["Basketball"]["pending_dates"])
        self.assertEqual(6, sum(row["season_state"] == "DOCUMENTED_HOLD" for row in self.rows.values() if row["sport"] == "Basketball"))

    def test_sixth_basketball_source_batch_uses_exact_official_windows(self):
        expected_windows = {
            "Radivoj Korać Cup | Men": "basketball-rs-cup",
            "SBL Cup | Men": "basketball-ch-sbl-cup",
            "State Cup | Men": "basketball-il-state-cup",
            "Super 20 Cup | Men": "basketball-ar-super20",
            "Supercopa Italia | Men": "basketball-it-supercup",
            "Supercopa de Espana | Men": "basketball-es-supercopa",
        }
        for league, source_id in expected_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        self.assertEqual(6, self.inventory["by_sport"]["Basketball"]["no_linked_source"])
        self.assertEqual(0, self.inventory["by_sport"]["Basketball"]["pending_dates"])
        self.assertEqual(6, sum(row["season_state"] == "DOCUMENTED_HOLD" for row in self.rows.values() if row["sport"] == "Basketball"))

    def test_seventh_basketball_source_batch_closes_actionable_source_gaps(self):
        dated_windows = {
            "Supercopa de Liga | Men": "basketball-ar-supercopa",
            "Svenska Basketligan (SBL) | Men": "basketball-se-sbl",
            "Swiss Cup | Men": "basketball-ch-cup",
            "Turkish Basketball Cup | Men": "basketball-tr-cup",
        }
        for league, source_id in dated_windows.items():
            with self.subTest(league=league):
                row = self.rows[("Basketball", league)]
                self.assertEqual("DATED_WINDOW", row["season_state"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])

        unrivaled = self.rows[("Basketball", "Unrivaled Basketball | Women")]
        self.assertEqual("DESCRIPTIVE_WINDOW", unrivaled["season_state"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", unrivaled["coverage_state"])
        self.assertEqual(["basketball-us-unrivaled"], [source["id"] for source in unrivaled["sources"]])
        self.assertEqual("official-event-window", unrivaled["sources"][0]["type"])

        self.assertEqual(6, self.inventory["by_sport"]["Basketball"]["no_linked_source"])
        self.assertEqual(0, self.inventory["by_sport"]["Basketball"]["pending_dates"])
        self.assertEqual(6, sum(row["season_state"] == "DOCUMENTED_HOLD" for row in self.rows.values() if row["sport"] == "Basketball"))

    def test_ncaa_division_one_adapters_match_the_exact_competition_scope(self):
        expected = {
            ("NCAA Basketball", "Division I Basketball | Men"): ("ncaa-mbb", "NCAA Men's Basketball"),
            ("NCAA Basketball", "Division I Basketball | Women"): ("ncaa-wbb", "NCAA Women's Basketball"),
            ("NCAA Volleyball", "Division I Volleyball | Women"): ("ncaa-volleyball", "NCAA Volleyball"),
        }
        for identity, (source_id, configured_league) in expected.items():
            with self.subTest(identity=identity):
                row = self.rows[identity]
                self.assertEqual("ADAPTER_CONFIGURED", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("adapter", row["sources"][0]["type"])
                self.assertEqual(configured_league, row["sources"][0]["configured_league"])

        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        configured_sources = {source["id"]: source for source in config["sources"]}
        self.assertEqual("NCAA Basketball", configured_sources["ncaa-mbb"]["sport"])
        self.assertEqual(["Division I Basketball | Men"], configured_sources["ncaa-mbb"]["catalog_terms"])
        self.assertEqual("NCAA Basketball", configured_sources["ncaa-wbb"]["sport"])
        self.assertEqual(["Division I Basketball | Women"], configured_sources["ncaa-wbb"]["catalog_terms"])
        self.assertEqual("NCAA Volleyball", configured_sources["ncaa-volleyball"]["sport"])
        self.assertEqual(["Division I Volleyball | Women"], configured_sources["ncaa-volleyball"]["catalog_terms"])

        schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text(encoding="utf-8"))
        refreshed = {source["id"]: source for source in schedule["sources"]}
        self.assertEqual("NCAA Basketball", refreshed["ncaa-mbb"]["sport"])
        self.assertEqual("NCAA Basketball", refreshed["ncaa-wbb"]["sport"])
        self.assertEqual("NCAA Volleyball", refreshed["ncaa-volleyball"]["sport"])
        self.assertTrue(all(event["sport"] == "NCAA Volleyball" for event in schedule["events"] if event["source_id"] == "ncaa-volleyball"))

        # The current college-football feed does not establish FBS-only scope.
        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])

    def test_ncaa_baseball_adapter_maps_only_division_one_men(self):
        identity = ("NCAA Baseball", "Division I Baseball | Men")
        row = self.rows[identity]
        self.assertEqual("RECURRING_WINDOW", row["season_state"])
        self.assertEqual("February–June", row["season_window"])
        self.assertEqual("ADAPTER_CONFIGURED", row["coverage_state"])
        self.assertEqual(
            [{
                "id": "ncaa-baseball",
                "type": "adapter",
                "configured_league": "NCAA Baseball",
                "refresh_ok": True,
                "events_in_window": 0,
            }],
            row["sources"],
        )

        season_map = json.loads((ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8"))
        baseball = next(sport for sport in season_map["sports"] if sport["sport"] == "NCAA Baseball")
        self.assertEqual(
            [{
                "key": "ncaa-baseball-di",
                "source_id": "ncaa-baseball",
                "catalog_event": "Division I Baseball | Men",
                "season_window": "February–June",
                "season_start": "02-01",
                "season_end": "06-30",
                "last_verified": "2026-09-16",
                "restrictions": [],
            }],
            baseball["groups"][0]["events"],
        )

        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        configured = {source["id"]: source for source in config["sources"]}["ncaa-baseball"]
        self.assertEqual("NCAA Baseball", configured["sport"])
        self.assertEqual(["Division I Baseball | Men"], configured["catalog_terms"])
        self.assertEqual("https://www.ncaa.com/scoreboard/baseball/d1", configured["official_schedule_url"])

        schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text(encoding="utf-8"))
        refreshed = {source["id"]: source for source in schedule["sources"]}["ncaa-baseball"]
        self.assertTrue(refreshed["ok"])
        self.assertEqual(0, refreshed["events"])
        self.assertFalse(any(event["source_id"] == "ncaa-baseball" for event in schedule["events"]))

        registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
        registered = next(
            competition for competition in registry["competitions"]
            if competition["sport"] == "NCAA Baseball" and competition["league"] == identity[1]
        )
        self.assertEqual(["ncaa-baseball"], registered["source_ids"])

        # The football feed still does not establish FBS-only scope.
        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])

    def test_ncaa_postseason_basketball_keeps_published_window_and_canceled_hold_distinct(self):
        crown = self.rows[("NCAA Basketball", "College Basketball Crown (CBC) | Men")]
        self.assertEqual("DATED_WINDOW", crown["season_state"])
        self.assertEqual("April 1–5, 2026", crown["season_window"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", crown["coverage_state"])
        self.assertEqual(["ncaa-basketball-cbc"], [source["id"] for source in crown["sources"]])
        self.assertEqual("official-event-window", crown["sources"][0]["type"])
        self.assertTrue(crown["sources"][0]["refresh_ok"])
        self.assertEqual(0, crown["sources"][0]["events_in_window"])

        cbi = self.rows[("NCAA Basketball", "College Basketball Invitational (CBI) | Men")]
        self.assertEqual("DOCUMENTED_HOLD", cbi["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", cbi["coverage_state"])
        self.assertEqual([], cbi["sources"])
        self.assertIn("2026 CBI was canceled", cbi["hold_reason"])
        self.assertIn("2027 dates", cbi["hold_reason"])

        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        configured = {source["id"]: source for source in config["sources"]}["ncaa-basketball-cbc"]
        self.assertEqual("NCAA Basketball", configured["sport"])
        self.assertEqual(["College Basketball Crown (CBC) | Men"], configured["catalog_terms"])
        self.assertEqual("2026-04-01", configured["official_events"][0]["start_date"])
        self.assertEqual("2026-04-05", configured["official_events"][0]["end_date"])

        registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
        registered = next(
            competition for competition in registry["competitions"]
            if competition["sport"] == "NCAA Basketball" and competition["league"] == crown["league"]
        )
        self.assertEqual(["ncaa-basketball-cbc"], registered["source_ids"])
        self.assertEqual(1, self.inventory["by_sport"]["NCAA Basketball"]["no_linked_source"])
        self.assertEqual(8, self.inventory["summary"]["season_states"]["DOCUMENTED_HOLD"])

    def test_ncaa_division_two_and_three_basketball_use_exact_child_windows(self):
        expected = {
            "Division II Basketball | Men": (
                "ncaa-basketball-dii-men", "2027-03-23", "2027-03-27",
                "https://www.ncaa.com/scoreboard/basketball-men/d2",
            ),
            "Division II Basketball | Women": (
                "ncaa-basketball-dii-women", "2027-03-22", "2027-03-26",
                "https://www.ncaa.com/scoreboard/basketball-women/d2",
            ),
            "Division III Basketball | Men": (
                "ncaa-basketball-diii-men", "2027-03-18", "2027-03-20",
                "https://www.ncaa.com/scoreboard/basketball-men/d3",
            ),
            "Division III Basketball | Women": (
                "ncaa-basketball-diii-women", "2027-03-18", "2027-03-20",
                "https://www.ncaa.com/scoreboard/basketball-women/d3",
            ),
        }
        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        configured = {source["id"]: source for source in config["sources"]}
        schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text(encoding="utf-8"))
        refreshed = {source["id"]: source for source in schedule["sources"]}
        registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
        registered = {
            competition["league"]: competition
            for competition in registry["competitions"]
            if competition["sport"] == "NCAA Basketball"
        }

        for league, (source_id, start_date, end_date, scoreboard_url) in expected.items():
            with self.subTest(league=league):
                row = self.rows[("NCAA Basketball", league)]
                self.assertEqual("RECURRING_WINDOW", row["season_state"])
                self.assertEqual("November–March", row["season_window"])
                self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
                self.assertEqual([source_id], [source["id"] for source in row["sources"]])
                self.assertEqual("official-event-window", row["sources"][0]["type"])
                self.assertTrue(row["sources"][0]["refresh_ok"])
                self.assertEqual(0, row["sources"][0]["events_in_window"])

                source = configured[source_id]
                self.assertEqual("NCAA Basketball", source["sport"])
                self.assertEqual(league, source["league"])
                self.assertEqual([league], source["catalog_terms"])
                self.assertEqual(scoreboard_url, source["official_schedule_url"])
                self.assertEqual(start_date, source["official_events"][0]["start_date"])
                self.assertEqual(end_date, source["official_events"][0]["end_date"])
                self.assertIn("regular-season fixture coverage", source["source_note"])

                self.assertTrue(refreshed[source_id]["ok"])
                self.assertEqual(0, refreshed[source_id]["events"])
                self.assertEqual([source_id], registered[league]["source_ids"])

        self.assertEqual(1, self.inventory["by_sport"]["NCAA Basketball"]["no_linked_source"])
        self.assertEqual(117, self.inventory["summary"]["coverage_states"]["NO_LINKED_SOURCE"])
        self.assertEqual(68, self.inventory["summary"]["coverage_states"]["OFFICIAL_WINDOW_ONLY"])

        # The CBI and FBS holds remain separate from these exact child windows.
        cbi = self.rows[("NCAA Basketball", "College Basketball Invitational (CBI) | Men")]
        self.assertEqual("DOCUMENTED_HOLD", cbi["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", cbi["coverage_state"])
        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])

    def test_ncaa_beach_volleyball_keeps_national_collegiate_scope_fail_closed(self):
        row = self.rows[("NCAA Beach Volleyball", "Division I Beach Volleyball | Women")]
        self.assertEqual("DOCUMENTED_HOLD", row["season_state"])
        self.assertEqual("NO_LINKED_SOURCE", row["coverage_state"])
        self.assertEqual([], row["sources"])
        self.assertIn("National Collegiate", row["season_window"])
        self.assertIn("May 7–9", row["season_window"])
        self.assertIn("Division I women", row["hold_reason"])
        self.assertIn("National Collegiate", row["hold_reason"])
        self.assertIn("Division I-only unattended source", row["hold_reason"])

        season_map = json.loads((ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8"))
        sport = next(item for item in season_map["sports"] if item["sport"] == "NCAA Beach Volleyball")
        event = sport["groups"][0]["events"][0]
        self.assertEqual("Division I Beach Volleyball | Women", event["catalog_event"])
        self.assertTrue(event["season_hold"])
        self.assertNotIn("source_id", event)
        self.assertIn("National Collegiate", event["season_basis"])

        # Broader NCAA evidence must not resolve the narrower catalog child.
        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        self.assertFalse(any(
            source.get("sport") == "NCAA Beach Volleyball"
            for source in config["sources"]
        ))
        self.assertEqual(8, self.inventory["summary"]["season_states"]["DOCUMENTED_HOLD"])

        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])

    def test_ncaa_field_hockey_uses_exact_division_one_championship_window(self):
        row = self.rows[("NCAA Field Hockey", "Division I Field Hockey | Women")]
        self.assertEqual("RECURRING_WINDOW", row["season_state"])
        self.assertEqual("OFFICIAL_WINDOW_ONLY", row["coverage_state"])
        self.assertEqual(["ncaa-field-hockey-di"], [source["id"] for source in row["sources"]])
        self.assertEqual("official-event-window", row["sources"][0]["type"])
        self.assertTrue(row["sources"][0]["refresh_ok"])
        self.assertEqual(0, row["sources"][0]["events_in_window"])

        season_map = json.loads((ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8"))
        sport = next(item for item in season_map["sports"] if item["sport"] == "NCAA Field Hockey")
        event = sport["groups"][0]["events"][0]
        self.assertEqual("Division I Field Hockey | Women", event["catalog_event"])
        self.assertEqual("ncaa-field-hockey-di", event["source_id"])
        self.assertIn("Nov. 20–22", event["season_window"])
        self.assertIn("Division I", event["season_basis"])

        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        source = {item["id"]: item for item in config["sources"]}["ncaa-field-hockey-di"]
        self.assertEqual("NCAA Field Hockey", source["sport"])
        self.assertEqual("Division I Field Hockey | Women", source["league"])
        self.assertEqual(["Division I Field Hockey | Women"], source["catalog_terms"])
        self.assertEqual("2026-11-20", source["official_events"][0]["start_date"])
        self.assertEqual("2026-11-22", source["official_events"][0]["end_date"])

        schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text(encoding="utf-8"))
        refreshed = {item["id"]: item for item in schedule["sources"]}["ncaa-field-hockey-di"]
        self.assertTrue(refreshed["ok"])
        self.assertEqual(0, refreshed["events"])

        registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
        registered = next(
            competition for competition in registry["competitions"]
            if competition["sport"] == "NCAA Field Hockey"
            and competition["league"] == "Division I Field Hockey | Women"
        )
        self.assertEqual(["ncaa-field-hockey-di"], registered["source_ids"])

        self.assertEqual(0, self.inventory["by_sport"]["NCAA Field Hockey"]["no_linked_source"])
        self.assertEqual(117, self.inventory["summary"]["coverage_states"]["NO_LINKED_SOURCE"])
        self.assertEqual(68, self.inventory["summary"]["coverage_states"]["OFFICIAL_WINDOW_ONLY"])

        # FBS scope remains unresolved and must stay fail-closed.
        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])

    def test_ncaa_football_subdivisions_use_exact_scope_sources(self):
        fbs = self.rows[("NCAA Football", "Division I Football Bowl Subdivision (FBS)")]
        self.assertEqual("ADAPTER_GAP", fbs["coverage_state"])
        self.assertEqual(["ncaa-football-fbs"], [source["id"] for source in fbs["sources"]])
        self.assertEqual("coverage-gap", fbs["sources"][0]["type"])

        fcs = self.rows[("NCAA Football", "Division I Football Championship Subdivision (FCS)")]
        self.assertEqual("OFFICIAL_WINDOW_ONLY", fcs["coverage_state"])
        self.assertEqual(["ncaa-football-fcs"], [source["id"] for source in fcs["sources"]])
        self.assertIn("Jan. 11, 2027", fcs["season_window"])

        dii = self.rows[("NCAA Football", "Division II Football")]
        self.assertEqual("OFFICIAL_WINDOW_ONLY", dii["coverage_state"])
        self.assertEqual(["ncaa-football-dii"], [source["id"] for source in dii["sources"]])
        self.assertIn("Dec. 19", dii["season_window"])

        config = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text(encoding="utf-8"))
        configured = {source["id"]: source for source in config["sources"]}
        self.assertEqual("https://www.ncaa.com/scoreboard/football/fbs", configured["ncaa-football-fbs"]["official_schedule_url"])
        self.assertEqual("2027-01-11", configured["ncaa-football-fcs"]["official_events"][0]["start_date"])
        self.assertEqual("2026-12-19", configured["ncaa-football-dii"]["official_events"][0]["start_date"])

        registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
        registered = {
            item["league"]: item["source_ids"]
            for item in registry["competitions"]
            if item["sport"] == "NCAA Football"
        }
        self.assertEqual(["ncaa-football-fbs"], registered["Division I Football Bowl Subdivision (FBS)"])
        self.assertEqual(["ncaa-football-fcs"], registered["Division I Football Championship Subdivision (FCS)"])
        self.assertEqual(["ncaa-football-dii"], registered["Division II Football"])

        self.assertEqual(0, self.inventory["by_sport"]["NCAA Football"]["no_linked_source"])
        self.assertEqual(1, self.inventory["by_sport"]["NCAA Football"]["adapter_gaps"])
        self.assertEqual(117, self.inventory["summary"]["coverage_states"]["NO_LINKED_SOURCE"])
        self.assertEqual(68, self.inventory["summary"]["coverage_states"]["OFFICIAL_WINDOW_ONLY"])
        self.assertEqual(289, self.inventory["summary"]["coverage_states"]["ADAPTER_GAP"])
        self.assertEqual(69, self.inventory["summary"]["coverage_states"]["SOURCE_SCOPE_REVIEW"])

        self.assertEqual(
            [{"sport": "Football", "league": "NCAA Football"}],
            self.inventory["summary"]["schedule_only_not_independent_approvals"],
        )

    def test_unconfigured_reference_and_schedule_only_names_remain_visible(self):
        cycling = self.rows[("Cycling", "Cadel Evans Great Ocean Road Race")]
        self.assertEqual("SOURCE_SCOPE_REVIEW", cycling["coverage_state"])
        self.assertEqual(
            [{"sport": "Football", "league": "NCAA Football"}],
            self.inventory["summary"]["schedule_only_not_independent_approvals"],
        )
        self.assertEqual(len(self.rows), self.inventory["summary"]["catalog_operational_identities"])


if __name__ == "__main__":
    unittest.main()
