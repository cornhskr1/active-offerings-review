"""LFF cup exact edition, two-view evidence, and denial/date-only safeguards."""

import copy
import datetime as dt
from pathlib import Path
import unittest
from unittest.mock import Mock

from lxml import html

from scripts.baltic_cup_fixture_adapter import (
    ENDPOINT, SOURCE_ID, fetch_fixtures, parse_fixtures, source_configs,
)

FIXTURE = Path(__file__).parent / "fixtures/baltic-cups/lff-cup-20261018.html"
TODAY = dt.date(2026, 10, 18)


def page():
    return FIXTURE.read_text()


def changed(xpath, function):
    doc = html.fromstring(page())
    found = doc.xpath(xpath)
    assert found, xpath
    for node in found:
        function(node)
    return html.tostring(doc, encoding="unicode")


class BalticCupFixtureTests(unittest.TestCase):
    def parse(self, content=None, source=None, today=TODAY):
        return parse_fixtures(page() if content is None else content,
                              source or source_configs()[0], today)

    def test_one_exact_approved_mens_identity_only(self):
        configs = source_configs()
        self.assertEqual([s["id"] for s in configs], [SOURCE_ID])
        self.assertEqual(configs[0]["catalog_terms"], ["Latvian Cup / Latvijas Kauss | Men"])
        self.assertEqual(configs[0]["coverage_status"], "partial")
        self.assertIs(configs[0]["coverage_complete"], False)

    def test_real_public_snapshot_crosschecks_final_without_invented_timezone(self):
        events, evidence = self.parse(FIXTURE.read_bytes())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "lff-cup-25551787")
        self.assertEqual(events[0]["name"], "Riga FC at FK Auda")
        self.assertEqual(events[0]["start_time"], "2026-11-20")
        self.assertTrue(events[0]["date_only"])
        self.assertEqual(events[0]["published_kickoff_text"], "19:30")
        self.assertEqual(events[0]["season_stage"], "FINAL")
        self.assertEqual(events[0]["location"], "Skonto stadions")
        self.assertEqual(evidence["published_full_view_rows"], 47)
        self.assertEqual(evidence["completed_fixtures_excluded"], 46)
        self.assertFalse(evidence["review_window_complete"])
        self.assertEqual(evidence["participant_age_coverage"], "unverified")
        self.assertTrue(events[0]["participant_review_required"])
        # Future fixture remains available to the collector even beyond its 7 days.
        self.assertGreater(dt.date.fromisoformat(events[0]["start_time"]), TODAY + dt.timedelta(days=7))

    def test_scope_drift_fails_before_fetch(self):
        for field, value in {"id": "wrong", "league": "Latvian Cup | Women",
                             "region": "Estonia", "sport": "Football", "endpoint": ENDPOINT + "?p=2025",
                             "catalog_terms": [], "official_schedule_url": "https://example.test",
                             "coverage_complete": True, "coverage_status": "complete",
                             "source_type": "official-ejl-cup-fixtures"}.items():
            with self.subTest(field=field):
                source = copy.deepcopy(source_configs()[0])
                source[field] = value
                get = Mock()
                with self.assertRaisesRegex(ValueError, "scope|boundary"):
                    fetch_fixtures(source, TODAY, get)
                get.assert_not_called()

    def test_wrong_competition_edition_and_feed_id_fail_closed(self):
        for altered in (page().replace("LVBET Latvijas kauss", "Latvijas Superkauss"),
                        page().replace('>2026</option>', '>2027</option>', 1),
                        page().replace('stats_competition_23910990_', 'stats_competition_23300000_', 1),
                        page().replace('cid=23910990', 'cid=23300000', 1)):
            with self.subTest():
                with self.assertRaises(ValueError):
                    self.parse(altered)

    def test_selected_other_edition_is_not_hidden_by_first_option(self):
        altered = changed('//select[contains(@class,"pageParams")]/option[2]',
                          lambda node: node.set('selected', 'selected'))
        with self.assertRaisesRegex(ValueError, "edition"):
            self.parse(altered)

    def test_unplayed_dates_scores_venue_names_and_phase_must_match(self):
        edits = [
            ('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]//h5', "21"),
            ('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]//div[@class="h8"]', "2027"),
            ('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]//div[@class="h7"]', "20:30"),
            ('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]//div[@class="stadium"]', "Another stadium"),
            ('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]//span[@class="res1"]', "1"),
            ('//*[@id="tabContent_1_1"]//*[@data-id="25551787"]//h6', "Pusfināli"),
            ('//*[@id="tabContent_1_1"]//*[@data-id="25551787"]//a[1]', "Different team"),
        ]
        for xpath, value in edits:
            with self.subTest(xpath=xpath):
                altered = changed(xpath, lambda node: setattr(node, 'text', value))
                with self.assertRaises(ValueError):
                    self.parse(altered)

    def test_duplicate_or_missing_full_match_fails_closed(self):
        for alter in (lambda node: node.getparent().append(copy.deepcopy(node)),
                      lambda node: node.getparent().remove(node)):
            altered = changed('//*[@id="tabContent_1_2"]//*[@data-id="25551787"]', alter)
            with self.assertRaisesRegex(ValueError, "duplicate|missing"):
                self.parse(altered)

    def test_empty_upcoming_never_means_offseason(self):
        altered = changed('//*[@id="tabContent_1_1"]//*[@data-id]',
                          lambda node: node.getparent().remove(node))
        with self.assertRaisesRegex(ValueError, "absence is not offseason"):
            self.parse(altered)

    def test_yearless_or_invalid_time_is_not_invented(self):
        for altered in (page().replace('20.11.2026.', '20.11.', 1),
                        page().replace('<h4>19:30</h4>', '<h4>25:30</h4>', 1),
                        page().replace('<h4>19:30</h4>', '<h4></h4>', 1)):
            with self.assertRaises(ValueError):
                self.parse(altered)

    def test_same_day_date_only_retained_and_past_day_held(self):
        self.assertEqual(len(self.parse(today=dt.date(2026, 11, 20))[0]), 1)
        events, evidence = self.parse(today=dt.date(2026, 11, 21))
        self.assertEqual(events, [])
        self.assertEqual(evidence["past_unplayed_fixtures_held"], 1)
        self.assertFalse(evidence["review_window_complete"])
        self.assertNotIn("offseason", evidence)
        with self.assertRaisesRegex(ValueError, "expired"):
            self.parse(today=dt.date(2027, 1, 1))

    def test_unresolved_youth_reserve_and_amateur_pairings_are_held(self):
        for name, key in (("Winner TBD", "unresolved_pairings_held"),
                          ("FK Auda U19", "age_or_reserve_fixtures_held"),
                          ("FK Auda II", "age_or_reserve_fixtures_held"),
                          ("FK Auda Amatieri", "amateur_scope_held")):
            with self.subTest(name=name):
                events, evidence = self.parse(page().replace(">FK Auda</a>", f">{name}</a>"))
                self.assertEqual(events, [])
                self.assertEqual(evidence[key], 1)
                self.assertFalse(evidence["coverage_complete"])

    def test_fetch_reads_once_no_redirect_or_denial_fallback(self):
        for code in (301, 302, 401, 403, 429, 500):
            with self.subTest(code=code):
                get = Mock(return_value=Mock(status_code=code, url=ENDPOINT))
                with self.assertRaises(ValueError):
                    fetch_fixtures(source_configs()[0], TODAY, get)
                get.assert_called_once_with(ENDPOINT, timeout=30, allow_redirects=False)
        get = Mock(return_value=Mock(status_code=200, url=ENDPOINT + "?other=1", content=FIXTURE.read_bytes()))
        with self.assertRaisesRegex(ValueError, "moved"):
            fetch_fixtures(source_configs()[0], TODAY, get)
        get.assert_called_once()

    def test_fetch_uses_central_review_day_at_utc_boundary(self):
        get = Mock(return_value=Mock(status_code=200, url=ENDPOINT, content=FIXTURE.read_bytes()))
        events, _ = fetch_fixtures(source_configs()[0], dt.datetime(2026, 11, 21, 0, 30, tzinfo=dt.timezone.utc), get)
        self.assertEqual(events[0]["start_time"], "2026-11-20")
        with self.assertRaisesRegex(ValueError, "no admissible future fixture"):
            fetch_fixtures(source_configs()[0], dt.datetime(2026, 11, 21, 6, 30, tzinfo=dt.timezone.utc), get)

    def test_naive_refresh_timestamp_fails_before_network(self):
        get = Mock()
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            fetch_fixtures(source_configs()[0], dt.datetime(2026, 10, 18), get)
        get.assert_not_called()

    def test_all_held_cards_do_not_promote_a_healthy_empty_feed(self):
        for altered in (page().replace(">FK Auda</a>", ">FK Auda U19</a>"),
                        page().replace(">FK Auda</a>", ">Winner TBD</a>")):
            get = Mock(return_value=Mock(status_code=200, url=ENDPOINT, content=altered.encode()))
            with self.assertRaisesRegex(ValueError, "coverage remains unresolved, not offseason"):
                fetch_fixtures(source_configs()[0], TODAY, get)

    def test_fetch_returns_future_literal_date_and_endpoint_evidence(self):
        get = Mock(return_value=Mock(status_code=200, url=ENDPOINT, content=FIXTURE.read_bytes()))
        events, evidence = fetch_fixtures(source_configs()[0], dt.datetime(2026, 10, 18, tzinfo=dt.timezone.utc), get)
        self.assertEqual(events[0]["start_time"], "2026-11-20")
        self.assertEqual(evidence["requested_endpoints"], [ENDPOINT])
        get.assert_called_once_with(ENDPOINT, timeout=30, allow_redirects=False)


if __name__ == "__main__":
    unittest.main()
