"""Official women's cup round, shared headers, exact scope and atomicity."""

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from lxml import html

from scripts.dfb_womens_cup_fixture_adapter import (
    ENDPOINT, LEAGUE, PAIRINGS, SOURCE_ID, SOURCE_TYPE,
    fetch_fixtures, parse_fixtures, source_config,
)


FIXTURE = Path(__file__).parent / "fixtures/dfb-womens-cup-20261018.html"
PAGE = FIXTURE.read_bytes()
NOW = dt.datetime(2026, 10, 18, 17, tzinfo=dt.timezone.utc)


def changed(xpath, mutate):
    doc = html.fromstring(PAGE.decode("utf-8"))
    nodes = doc.xpath(xpath)
    assert nodes, xpath
    for node in nodes:
        mutate(node)
    return html.tostring(doc, encoding="utf-8")


def text_changed(xpath, value):
    return changed(xpath, lambda node: setattr(node, "text", value))


def response(page=PAGE, status=200, url=ENDPOINT):
    return SimpleNamespace(content=page, status_code=status, url=url)


class DfbWomensCupFixtureTests(unittest.TestCase):
    def parse(self, page=PAGE, source=None):
        return parse_fixtures(page, source or source_config())

    def test_exact_womens_identity_and_partial_scope(self):
        source = source_config()
        self.assertEqual(source["id"], "uefa-soccer-germany-dfb-pokal-frauen-women")
        self.assertEqual(source["catalog_terms"], ["DFB-Pokal Frauen | Women"])
        self.assertEqual(source["source_type"], SOURCE_TYPE)
        self.assertEqual(source["coverage_status"], "partial")
        self.assertIs(source["coverage_complete"], False)

    def test_public_capture_and_provenance(self):
        proof = json.loads(FIXTURE.with_suffix(".source.json").read_text())
        self.assertEqual(proof["source_url"], ENDPOINT)
        self.assertEqual(proof["http_status"], 200)
        self.assertEqual(proof["publication_date"], "2026-10-05")
        self.assertEqual(proof["retained_bytes"], len(PAGE))
        self.assertEqual(proof["sha256"], hashlib.sha256(PAGE).hexdigest())
        self.assertLess(len(PAGE), 10000)
        self.assertNotIn(b"<script", PAGE)
        self.assertNotIn(b"<img", PAGE)
        self.assertEqual(self.parse(PAGE), self.parse(PAGE.decode("utf-8")))

    def test_all_eight_pairings_and_sixteen_clubs_reconcile(self):
        events, proof = self.parse()
        self.assertEqual(len(events), 8)
        self.assertEqual(len({event["id"] for event in events}), 8)
        self.assertEqual({event["name"] for event in events}, {f"{away} at {home}" for home, away in PAIRINGS})
        self.assertEqual((proof["published_fixtures"], proof["published_clubs"]), (8, 16))
        self.assertEqual((proof["published_date_headings"], proof["published_clock_headings"]), (4, 5))
        self.assertEqual(proof["published_edition"], "2026/2027")
        self.assertEqual(proof["published_phase"], "ROUND OF 16")
        self.assertEqual(proof["published_first_fixture_date"], "2026-10-30")
        self.assertEqual(proof["published_last_fixture_date"], "2026-11-02")
        self.assertTrue(all(e["source_id"] == SOURCE_ID and e["league"] == LEAGUE for e in events))

    def test_shared_dates_and_clocks_apply_to_every_pairing(self):
        events, _ = self.parse()
        self.assertEqual([(e["start_time"], e["published_kickoff_text"], e["name"]) for e in events], [
            ("2026-10-30", "18 Uhr", "SGS Essen at VfB Stuttgart"),
            ("2026-10-31", "13 Uhr", "RB Leipzig at 1. FC Köln"),
            ("2026-10-31", "13 Uhr", "1. FC Union Berlin at Hamburger SV"),
            ("2026-11-01", "14 Uhr", "Eintracht Frankfurt at 1. FC Nürnberg"),
            ("2026-11-01", "14 Uhr", "Carl Zeiss Jena at SC Freiburg"),
            ("2026-11-01", "14 Uhr", "SV Werder Bremen at 1. FSV Mainz 05"),
            ("2026-11-01", "15 Uhr", "Bayer 04 Leverkusen at FC Bayern München"),
            ("2026-11-02", "18 Uhr", "TSG Hoffenheim at VfL Wolfsburg"),
        ])

    def test_no_timezone_professional_or_age_clearance(self):
        events, proof = self.parse()
        self.assertTrue(all(e["date_only"] and len(e["start_time"]) == 10 for e in events))
        self.assertTrue(all(e["participant_review_required"] for e in events))
        self.assertTrue(all("timezone unverified" in e["status_detail"] for e in events))
        self.assertEqual(proof["date_only_fixtures"], 8)
        self.assertEqual(proof["participant_age_coverage"], "unverified")
        self.assertEqual(proof["professional_status_coverage"], "not established by schedule")
        self.assertFalse(proof["coverage_complete"])
        self.assertFalse(proof["review_window_complete"])

    def test_future_round_remains_available_with_zero_current_window(self):
        get = Mock(return_value=response())
        events, proof = fetch_fixtures(source_config(), NOW, get)
        get.assert_called_once_with(ENDPOINT, timeout=30, allow_redirects=False)
        self.assertEqual(len(events), 8)
        self.assertEqual(proof["future_confirmed_fixtures"], 8)
        self.assertEqual(proof["past_unresolved_fixtures_held"], 0)
        self.assertEqual(proof["requested_endpoints"], [ENDPOINT])
        self.assertEqual([e for e in events if "2026-10-18" <= e["start_time"] <= "2026-10-25"], [])

    def test_scope_changes_fail_before_request(self):
        changes = {"id": "wrong", "sport": "Football", "league": "DFB-Pokal | Men",
                   "region": "Austria", "source_type": "coverage-gap", "endpoint": ENDPOINT + "/",
                   "official_schedule_url": "https://www.dfb.de", "catalog_terms": [LEAGUE, "Men"],
                   "coverage_status": "complete", "coverage_complete": True}
        for key, value in changes.items():
            get = Mock()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "scope|boundary"):
                fetch_fixtures({**source_config(), key: value}, NOW, get)
            get.assert_not_called()

    def test_title_competition_edition_and_canonical_must_agree(self):
        for content in (
            text_changed('//title', "DFB-Pokal der Männer"),
            text_changed('//h1', "DFB-Pokal der Juniorinnen"),
            text_changed('//h2', "Pokalviertelfinale"),
            PAGE.replace(b"Saison 2026/2027", b"Saison 2025/2026"),
            PAGE.replace(b"05.10.2026", b"05.10.2025"),
            changed('//link[@rel="canonical"]', lambda node: node.set("href", "https://example.com/")),
            text_changed('//h3[text()="Die Spiele im Achtelfinale"]', "Die Spiele im Viertelfinale"),
        ):
            with self.subTest(), self.assertRaises(ValueError):
                self.parse(content)

    def test_missing_and_duplicate_article_authority_fail(self):
        for xpath in ('//title', '//link[@rel="canonical"]', '//h1',
                      '//div[@class="m-Hero-info"]', '//div[@class="dfb-Rte"]'):
            for mutate in (lambda n: n.getparent().remove(n), lambda n: n.addnext(copy.deepcopy(n))):
                with self.subTest(xpath=xpath), self.assertRaises(ValueError):
                    self.parse(changed(xpath, mutate))

    def test_all_duplicate_or_missing_pairings_fail_atomically(self):
        for home, away in PAIRINGS:
            xpath = f'//p[text()="{home} vs. {away}"]'
            for mutate in (lambda n: n.getparent().remove(n), lambda n: n.addnext(copy.deepcopy(n))):
                with self.subTest(home=home), self.assertRaisesRegex(ValueError, "duplicate|missing|reconciliation"):
                    self.parse(changed(xpath, mutate))

    def test_reversed_missing_unknown_or_out_of_scope_opponent_rejected(self):
        for value in ("SGS Essen vs. VfB Stuttgart", "VfB Stuttgart vs. VfB Stuttgart", "VfB Stuttgart vs. ",
                      "VfB Stuttgart vs. Unknown", "VfB Stuttgart vs. TBD", "VfB Stuttgart vs. Sieger A/B",
                      "VfB Stuttgart U19 vs. SGS Essen", "VfB Stuttgart II vs. SGS Essen",
                      "VfB Stuttgart Amateure vs. SGS Essen", "VfB Stuttgart vs. SGS Essen 2:0"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "pairing|identity"):
                self.parse(text_changed('//p[text()="VfB Stuttgart vs. SGS Essen"]', value))

    def test_no_pairing_can_inherit_previous_date_clock(self):
        content = changed('//p[strong="13 Uhr – live auf DFB.TV"]', lambda n: n.getparent().remove(n))
        with self.assertRaisesRegex(ValueError, "missing shared date or clock"):
            self.parse(content)

    def test_missing_initial_date_or_time_fails(self):
        for xpath in ('//p[strong="Freitag, 30. Oktober"]', '//p[strong="18 Uhr – live auf DFB.TV"]'):
            with self.subTest(xpath=xpath), self.assertRaises(ValueError):
                self.parse(changed(xpath, lambda n: n.getparent().remove(n)))

    def test_bad_date_weekday_year_or_order_fails(self):
        for value in ("Freitag, 30. Oktober 2025", "Samstag, 30. Oktober", "30. Oktober",
                      "Freitag, 32. Oktober", "Freitag, 30. Unbekannt", "Freitag, 2. Oktober",
                      "Dienstag, 3. November", "Freitag, 30. Oktober 2028"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(text_changed('//strong[text()="Freitag, 30. Oktober"]', value))

    def test_explicit_same_edition_year_is_not_rejected(self):
        events, _ = self.parse(text_changed('//strong[text()="Freitag, 30. Oktober"]', "Freitag, 30. Oktober 2026"))
        self.assertEqual(events[0]["start_time"], "2026-10-30")

    def test_duplicate_or_unused_shared_headings_fail(self):
        for xpath in ('//p[strong="Freitag, 30. Oktober"]', '//p[strong="18 Uhr – live auf DFB.TV"]'):
            with self.subTest(xpath=xpath), self.assertRaises(ValueError):
                self.parse(changed(xpath, lambda n: n.addnext(copy.deepcopy(n))))
        for value in ("Dienstag, 3. November", "19 Uhr – live auf Sky"):
            def append_heading(node):
                paragraph = html.Element("p"); strong = html.Element("strong")
                strong.text = value; paragraph.append(strong); node.append(paragraph)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "missing|reconciliation"):
                self.parse(changed('//div[@class="dfb-Rte"]', append_heading))

    def test_invalid_clock_and_unverified_timezone_not_assumed(self):
        for value in ("25 Uhr – live auf DFB.TV", "18:61 Uhr – live auf DFB.TV", "TBD – live auf DFB.TV",
                      "18 Uhr CET – live auf DFB.TV", "18 Uhr CEST – live auf DFB.TV", "18:00 – live auf DFB.TV"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(text_changed('//strong[text()="18 Uhr – live auf DFB.TV"]', value))

    def test_id_stable_across_verified_date_or_clock_change(self):
        original, _ = self.parse()
        content = text_changed('//strong[text()="Freitag, 30. Oktober"]', "Donnerstag, 29. Oktober")
        moved, _ = self.parse(content)
        self.assertEqual(original[0]["id"], moved[0]["id"])
        self.assertEqual(moved[0]["start_time"], "2026-10-29")
        shifted, _ = self.parse(text_changed('//strong[text()="18 Uhr – live auf DFB.TV"]', "18.30 Uhr – live auf DFB.TV"))
        self.assertEqual(original[0]["id"], shifted[0]["id"])
        self.assertEqual(shifted[0]["published_kickoff_text"], "18.30 Uhr")
        self.assertEqual(shifted[0]["start_time"], "2026-10-30")

    def test_flagged_nested_or_unexpected_rows_fail(self):
        for attribute, value in (("hidden", "hidden"), ("class", "postponed"), ("data-status", "cancelled")):
            with self.subTest(attribute=attribute), self.assertRaises(ValueError):
                self.parse(changed('//p[text()="VfB Stuttgart vs. SGS Essen"]', lambda n: n.set(attribute, value)))
        def wrap(node):
            wrapper = html.Element("div"); node.addnext(wrapper); wrapper.append(node)
        with self.assertRaisesRegex(ValueError, "layout"):
            self.parse(changed('//p[text()="VfB Stuttgart vs. SGS Essen"]', wrap))
        with self.assertRaises(ValueError):
            self.parse(changed('//div[@class="dfb-Rte"]', lambda n: n.append(html.Element("p"))))

    def test_final_bad_row_cannot_return_earlier_valid_cards(self):
        page = text_changed('//p[text()="VfL Wolfsburg vs. TSG Hoffenheim"]', "VfL Wolfsburg vs. TBD")
        with self.assertRaises(ValueError):
            fetch_fixtures(source_config(), NOW, Mock(return_value=response(page)))

    def test_aware_time_required_before_request(self):
        for now in (None, NOW.date(), NOW.replace(tzinfo=None)):
            get = Mock()
            with self.subTest(now=now), self.assertRaisesRegex(ValueError, "aware"):
                fetch_fixtures(source_config(), now, get)
            get.assert_not_called()

    def test_outside_publication_edition_horizon_fails_before_request(self):
        for now in (NOW.replace(day=4), NOW.replace(year=2027, month=7), NOW.replace(year=2025)):
            get = Mock()
            with self.subTest(now=now), self.assertRaisesRegex(ValueError, "horizon"):
                fetch_fixtures(source_config(), now, get)
            get.assert_not_called()

    def test_chicago_date_boundary_retains_same_day_and_holds_past(self):
        still_october30 = NOW.replace(day=31, hour=1)
        events, proof = fetch_fixtures(source_config(), still_october30, Mock(return_value=response()))
        self.assertEqual((len(events), proof["past_unresolved_fixtures_held"]), (8, 0))
        events, proof = fetch_fixtures(source_config(), still_october30.replace(hour=17), Mock(return_value=response()))
        self.assertEqual((len(events), proof["past_unresolved_fixtures_held"]), (7, 1))
        events, proof = fetch_fixtures(source_config(), NOW.replace(month=11, day=2), Mock(return_value=response()))
        self.assertEqual((len(events), proof["past_unresolved_fixtures_held"]), (1, 7))
        self.assertEqual(events[0]["name"], "TSG Hoffenheim at VfL Wolfsburg")

    def test_expired_round_is_failure_not_healthy_empty_or_offseason(self):
        with self.assertRaisesRegex(ValueError, "stale publication is not offseason"):
            fetch_fixtures(source_config(), NOW.replace(month=11, day=3), Mock(return_value=response()))

    def test_denials_http_errors_redirects_and_login_html_fail_without_retry(self):
        for status in (301, 302, 401, 403, 404, 429, 500):
            get = Mock(return_value=response(status=status))
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "HTTP"):
                fetch_fixtures(source_config(), NOW, get)
            self.assertEqual(get.call_count, 1)
        for resp in (response(url="https://example.com/"), response(page=b"<html><title>Sign in</title></html>")):
            with self.subTest(resp=resp), self.assertRaises(ValueError):
                fetch_fixtures(source_config(), NOW, Mock(return_value=resp))


if __name__ == "__main__":
    unittest.main()
