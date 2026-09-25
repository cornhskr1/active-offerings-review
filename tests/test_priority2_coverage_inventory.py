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
        self.assertEqual(23, basketball["no_linked_source"])
        self.assertEqual(0, basketball["pending_dates"])
        self.assertEqual(6, self.inventory["summary"]["season_states"]["DOCUMENTED_HOLD"])

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

        self.assertEqual(23, self.inventory["by_sport"]["Basketball"]["no_linked_source"])
        self.assertEqual(0, self.inventory["by_sport"]["Basketball"]["pending_dates"])

    def test_unconfigured_reference_and_schedule_only_names_remain_visible(self):
        cycling = self.rows[("Cycling", "Cadel Evans Great Ocean Road Race")]
        self.assertEqual("SOURCE_SCOPE_REVIEW", cycling["coverage_state"])
        self.assertEqual(
            [{"sport": "Football", "league": "NCAA Football"}, {"sport": "Volleyball", "league": "NCAA Volleyball"}],
            self.inventory["summary"]["schedule_only_not_independent_approvals"],
        )
        self.assertEqual(len(self.rows), self.inventory["summary"]["catalog_operational_identities"])


if __name__ == "__main__":
    unittest.main()
