import datetime as dt
import hashlib
import json
import re
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.usta_reference_reconciliation import (
    LANES, OWNER, SOURCE_FIELDS, reconcile_usta_references,
)


NOW = dt.datetime(2026, 10, 18, 18, tzinfo=dt.timezone.utc)
PDFS = {"men": b"%PDF-1.4\nReviewed men's calendar", "women": b"%PDF-1.4\nReviewed women's calendar"}


def fixture():
    sources, calendars = [], {}
    for lane, (usta_id, canonical_id, tour_id, gender, prefix) in LANES.items():
        sources.extend([
            {"id": usta_id, "source_type": "coverage-gap", "coverage_status": "manual-division-calendar",
             "events": 0, "ok": True, "note": "Original manual note", "source_note": "Original policy",
             "approved_catalog": True, "league": f"USTA Pro Circuit | {lane.title()}", "checked_at": NOW.isoformat()},
            {"id": canonical_id, "source_type": "tennis-intelligence", "tour_ids": [tour_id],
             "events": 2, "ok": True, "approved_catalog": True, "errors": [], "checked_at": NOW.isoformat()},
        ])
        calendars[lane] = {"source_id": usta_id,
                           "url": f"https://www.usta.com/content/dam/usta/pro-circuit/2026/2026-{lane}s-pro-circuit-calendar.pdf",
                           "sha256": hashlib.sha256(PDFS[lane]).hexdigest(), "published_revision": "2026-08-26"}
    manifest = {"reviewed_at": (NOW - dt.timedelta(hours=1)).isoformat(), "calendars": calendars, "references": []}
    payload = {"generated_at": (NOW - dt.timedelta(hours=2)).isoformat(), "window_start": "2026-10-18",
               "window_end": "2026-10-25", "tournaments": [], "quality_gate": {"passed": True, "complete": False,
               "degraded_lanes": [{"tour_id": "atp-challenger", "reason": "Blocked"}]}}
    events = []
    specs = [("men", "M25 Austin, TX", "2026-10-12", "2026-10-18"),
             ("men", "M15 Ithaca", "2026-10-19", "2026-10-25"),
             ("women", "W50 Austin", "2026-10-19", "2026-10-25"),
             ("women", "W35 Bakersfield, CA", "2026-10-19", "2026-10-25")]
    for n, (lane, name, start, end) in enumerate(specs, 1):
        usta_id, canonical_id, tour_id, gender, prefix = LANES[lane]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        url = f"https://www.itftennis.com/en/tournament/{slug}/usa/2026/{prefix}-itf-usa-2026-{n:03d}/fact-sheet/"
        row = {"calendar": lane, "source_id": canonical_id, "source_url": url, "tour_id": tour_id,
               "gender": gender, "tournament": name, "start_date": start, "end_date": end,
               "level": name.split()[0], "week_start": start, "usta_row": f"{start} {name}"}
        manifest["references"].append(row)
        item = {k: row[k] for k in ("source_url", "tour_id", "gender", "tournament", "start_date", "end_date")}
        item.update({"status": "ACTIVE" if n == 1 else "UPCOMING", "pre_draw_u18_count": 3 if n == 3 else 0,
                     "regulatory_status": "REVIEW — U18 IN PRE-DRAW ACCEPTANCE POOL"})
        payload["tournaments"].append(item)
        events.append({"id": f"{canonical_id}-{start}-{slug}", "source_id": canonical_id,
                       "sport": "Tennis", "name": name, "source_endpoint": url,
                       "start_time": "2026-10-18T17:00:00Z" if n == 1 else f"{start}T17:00:00Z",
                       "status": "LIVE" if n == 1 else "UPCOMING", "status_detail": item["regulatory_status"],
                       "catalog_approval": "EXPLICIT SOURCE MAPPING", "u18_matches": [{"name": "Review only"}],
                       "u18_risk": False, "restriction_signals": ["KEEP ORIGINAL"], "restriction_risk": True})
    return events, sources, payload, manifest


def getter(manifest, status=200, body=None):
    by_url = {c["url"]: PDFS[lane] for lane, c in manifest["calendars"].items()}
    return Mock(side_effect=lambda url, **kwargs: SimpleNamespace(status_code=status, url=url,
                content=by_url[url] if body is None else body))


class UstaReferenceReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.events, self.sources, self.payload, self.manifest = fixture()

    def run_reconciliation(self, now=NOW, get=None):
        return reconcile_usta_references(self.events, self.sources, self.payload, self.manifest,
                                         now, get=get or getter(self.manifest))

    def usta(self, sources, lane="men"):
        return next(s for s in sources if s["id"] == LANES[lane][0])

    def assert_rejected(self, code, lane="men", index=0):
        events, sources = self.run_reconciliation()
        self.assertNotIn("calendar_references", events[index])
        self.assertTrue(any(code in error for error in self.usta(sources, lane)["reference_errors"]), sources)
        return events, sources

    def test_four_exact_overlaps_preserve_every_canonical_field(self):
        before = deepcopy((self.events, self.sources, self.payload, self.manifest))
        get = getter(self.manifest)
        events, sources = self.run_reconciliation(get=get)
        self.assertEqual(len(events), 4)
        for original, annotated in zip(self.events, events):
            self.assertEqual({k: v for k, v in annotated.items() if k != "calendar_references"}, original)
            self.assertEqual(len(annotated["calendar_references"]), 1)
            reference = annotated["calendar_references"][0]
            self.assertEqual(reference["owner"], OWNER)
            self.assertEqual(reference["itf_tournament"]["source_url"], original["source_endpoint"])
            self.assertIn("ITF", reference["date_basis"])
            self.assertNotIn("end_date", reference)
        for original, annotated in zip(self.sources, sources):
            self.assertEqual({k: v for k, v in annotated.items() if k not in SOURCE_FIELDS}, original)
        for lane in LANES:
            source = self.usta(sources, lane)
            self.assertEqual(source["crosslisted_reference_count"], 2)
            self.assertEqual(source["reference_errors"], [])
            self.assertEqual(source["reference_status"], "references-verified")
            self.assertEqual(source["events"], 0)
            self.assertEqual(source["source_type"], "coverage-gap")
            self.assertEqual(source["coverage_status"], "manual-division-calendar")
        self.assertEqual(before, (self.events, self.sources, self.payload, self.manifest))
        self.assertEqual(get.call_count, 2)
        self.assertTrue(all(call.kwargs["allow_redirects"] is False for call in get.call_args_list))

    def test_frozen_seven_actual_overlaps_distinguish_shared_pdf_rows(self):
        # Frozen reviewed October 18 cells, not the rolling published schedule.
        # Exact official PDFs were verified separately; CI replaces only their
        # hashes with deterministic synthetic PDF bytes for offline execution.
        frozen = json.loads((Path(__file__).parent / "fixtures" /
                             "usta-calendar-overlap-20261018.json").read_text())
        exact_itf = [
            ('men', 'M15 Lexington, KY', 'https://www.itftennis.com/en/tournament/m15-lexington-ky/usa/2026/m-itf-usa-2026-042/fact-sheet/', '2026-10-18'),
            ('men', 'M25 Austin, TX', 'https://www.itftennis.com/en/tournament/m25-austin-tx/usa/2026/m-itf-usa-2026-045/fact-sheet/', '2026-10-18'),
            ('women', 'W100 Edmond, OK', 'https://www.itftennis.com/en/tournament/w100-edmond-ok/usa/2026/w-itf-usa-2026-049/fact-sheet/', '2026-10-18'),
            ('women', 'W35 Redding, CA', 'https://www.itftennis.com/en/tournament/w35-redding-ca/usa/2026/w-itf-usa-2026-050/fact-sheet/', '2026-10-18'),
            ('men', 'M15 Ithaca', 'https://www.itftennis.com/en/tournament/m15-ithaca/usa/2026/m-itf-usa-2026-041/fact-sheet/', '2026-10-25'),
            ('women', 'W35 Bakersfield, CA', 'https://www.itftennis.com/en/tournament/w35-bakersfield-ca/usa/2026/w-itf-usa-2026-057/fact-sheet/', '2026-10-25'),
            ('women', 'W50 Austin', 'https://www.itftennis.com/en/tournament/w50-austin/usa/2026/w-itf-usa-2026-052/fact-sheet/', '2026-10-25'),
        ]
        self.manifest = {"reviewed_at": frozen["reviewed_at"],
                         "calendars": deepcopy(frozen["calendars"]), "references": []}
        for lane, calendar in self.manifest["calendars"].items():
            calendar["sha256"] = hashlib.sha256(PDFS[lane]).hexdigest()
        self.events = []
        self.payload["tournaments"] = []
        self.assertEqual(len(frozen["rows"]), 7)
        self.assertEqual(len({(r["gender"], r["week_start"], r["row"]) for r in frozen["rows"]}), 4)
        for cell, (lane, name, url, end) in zip(frozen["rows"], exact_itf):
            usta_id, source_id, tour_id, gender, _ = LANES[lane]
            self.assertEqual(cell["gender"], gender)
            row = {"calendar": lane, "source_id": source_id, "source_url": url,
                   "tour_id": tour_id, "gender": gender, "tournament": name,
                   "start_date": cell["week_start"], "end_date": end,
                   "level": cell["level"], "week_start": cell["week_start"],
                   "usta_row": cell["row"], "usta_cell": cell["cell"]}
            self.manifest["references"].append(row)
            item = {k: row[k] for k in ("source_url", "tour_id", "gender", "tournament", "start_date", "end_date")}
            live = row["start_date"] == "2026-10-12"
            item["status"] = "ACTIVE" if live else "UPCOMING"
            self.payload["tournaments"].append(item)
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            self.events.append({
                "id": f'{source_id}-{row["start_date"]}-{slug}', "source_id": source_id,
                "sport": "Tennis", "name": name, "source_endpoint": url,
                "start_time": "2026-10-18T17:00:00Z" if live else "2026-10-19T17:00:00Z",
                "status": "LIVE" if live else "UPCOMING",
                "status_detail": "REVIEW — U18 IN PRE-DRAW ACCEPTANCE POOL" if name == "W50 Austin"
                                 else "REVIEW — PARTICIPANT FIELD INCOMPLETE",
                "catalog_approval": "EXPLICIT SOURCE MAPPING", "u18_risk": False,
                "u18_matches": [], "restriction_risk": True,
                "restriction_signals": ["Original review restriction"],
            })
        before = deepcopy((self.events, self.sources, self.payload, self.manifest))
        get = getter(self.manifest)
        events, sources = self.run_reconciliation(get=get)
        self.assertEqual(len(events), 7)
        self.assertEqual(len({e["id"] for e in events if e.get("calendar_references")}), 7)
        self.assertTrue(all(len(e["calendar_references"]) == 1 for e in events))
        self.assertEqual(self.usta(sources, "men")["crosslisted_reference_count"], 3)
        self.assertEqual(self.usta(sources, "women")["crosslisted_reference_count"], 4)
        self.assertEqual(self.usta(sources, "men")["reference_errors"], [])
        self.assertEqual(self.usta(sources, "women")["reference_errors"], [])
        self.assertEqual([{k: v for k, v in e.items() if k != "calendar_references"}
                          for e in events], self.events)
        self.assertEqual([{k: v for k, v in source.items() if k not in SOURCE_FIELDS}
                          for source in sources], self.sources)
        self.assertEqual(before, (self.events, self.sources, self.payload, self.manifest))
        self.assertEqual(get.call_count, 2)

    def test_mens_and_womens_austin_never_merge(self):
        events, _ = self.run_reconciliation()
        self.assertEqual(events[0]["calendar_references"][0]["source_id"], LANES["men"][0])
        self.assertEqual(events[2]["calendar_references"][0]["source_id"], LANES["women"][0])
        self.manifest["references"][0]["gender"] = "WOMEN"
        self.assert_rejected("REVIEWED_LANE_MISMATCH")

    def test_live_uses_original_date_in_id_not_display_start_time(self):
        events, _ = self.run_reconciliation()
        self.assertIn("2026-10-12", events[0]["id"])
        self.assertEqual(events[0]["start_time"], "2026-10-18T17:00:00Z")
        self.assertIn("calendar_references", events[0])
        self.events[0]["id"] = self.events[0]["id"].replace("2026-10-12", "2026-10-18")
        self.assert_rejected("CANONICAL_IDENTITY_MISMATCH")

    def test_wrong_tier_week_and_edition_are_rejected(self):
        for key, value, error in [("level", "M15", "REVIEWED_LEVEL_MISMATCH"),
                                  ("week_start", "2026-10-19", "REVIEWED_WEEK_MISMATCH"),
                                  ("source_url", self.manifest["references"][0]["source_url"].replace("2026-001", "2025-001"), "EDITION_OR_URL_MISMATCH")]:
            with self.subTest(key=key):
                original = self.manifest["references"][0][key]
                self.manifest["references"][0][key] = value
                self.assert_rejected(error)
                self.manifest["references"][0][key] = original

    def test_duplicate_review_rows_fail_closed(self):
        self.manifest["references"].append(deepcopy(self.manifest["references"][0]))
        events, sources = self.assert_rejected("AMBIGUOUS_REVIEWED_ROWS")
        self.assertEqual(self.usta(sources)["crosslisted_reference_count"], 1)

    def test_same_pdf_week_row_with_distinct_grade_cells_is_not_duplicate(self):
        a, b = self.manifest["references"][2:]
        a["usta_row"] = b["usta_row"] = "19-Oct-2026 Austin, TX (H) Bakersfield, CA (H)"
        a["usta_cell"], b["usta_cell"] = "Austin, TX (H)", "Bakersfield, CA (H)"
        events, sources = self.run_reconciliation()
        self.assertEqual(self.usta(sources, "women")["crosslisted_reference_count"], 2)
        self.assertEqual(events[2]["calendar_references"][0]["usta_cell"], "Austin, TX (H)")

    def test_duplicate_underlying_tournaments_fail_even_with_conflicting_name(self):
        duplicate = deepcopy(self.payload["tournaments"][0])
        duplicate["tournament"] = "M25 Other city"
        self.payload["tournaments"].append(duplicate)
        self.assert_rejected("AMBIGUOUS_TENNIS_TOURNAMENT")

    def test_duplicate_events_fail_even_with_conflicting_id(self):
        duplicate = deepcopy(self.events[0])
        duplicate["id"] = "another-id"
        self.events.append(duplicate)
        events, _ = self.assert_rejected("AMBIGUOUS_CANONICAL_EVENT")
        self.assertNotIn("calendar_references", events[-1])

    def test_changed_pdf_hash_is_not_annotated(self):
        get = getter(self.manifest, body=b"%PDF-1.4\nNew revision")
        events, sources = self.run_reconciliation(get=get)
        self.assertEqual(events, self.events)
        self.assertEqual(get.call_count, 2)
        self.assertIn("PDF_SHA256_CHANGED", self.usta(sources)["reference_errors"])

    def test_access_denials_never_retry(self):
        for status in (401, 403, 429):
            with self.subTest(status=status):
                get = getter(self.manifest, status=status)
                events, sources = self.run_reconciliation(get=get)
                self.assertEqual(events, self.events)
                self.assertEqual(get.call_count, 2)  # Once per distinct PDF, not per row.
                self.assertEqual(len({call.args[0] for call in get.call_args_list}), 2)
                self.assertIn(f"PDF_HTTP_{status}_ACCESS_DENIED", self.usta(sources)["reference_errors"])

    def test_pre_draw_and_restrictions_are_preserved_not_cleared(self):
        events, _ = self.run_reconciliation()
        for key in ("status_detail", "u18_matches", "u18_risk", "restriction_signals", "restriction_risk", "catalog_approval"):
            self.assertEqual(events[2][key], self.events[2][key])
        self.assertIn("U18 IN PRE-DRAW", events[2]["status_detail"])

    def test_idempotent_owned_metadata_only_and_failed_rebuild_removes_old_links(self):
        foreign = {"owner": "other-publisher", "source_id": "another-calendar", "data": [1, 2]}
        self.events[0]["calendar_references"] = [foreign]
        first = self.run_reconciliation()
        second = reconcile_usta_references(*first, self.payload, self.manifest, NOW, get=getter(self.manifest))
        self.assertEqual(first, second)
        events, sources = reconcile_usta_references(*second, self.payload, self.manifest, NOW,
                                                   get=getter(self.manifest, status=403))
        self.assertEqual(events, self.events)
        self.assertEqual(events[0]["calendar_references"], [foreign])
        self.assertEqual(self.usta(sources)["crosslisted_reference_count"], 0)
        self.assertEqual(self.usta(sources)["crosslisted_event_ids"], [])

    def test_expired_reviewed_rows_never_extend_to_future_editions(self):
        row = self.manifest["references"][0]
        row["start_date"] = row["week_start"] = "2026-10-05"
        row["end_date"] = "2026-10-11"
        self.assert_rejected("EXPIRED_REVIEWED_ROW")

    def test_no_exact_matches_returns_diagnostic_without_inventing_events(self):
        self.payload["tournaments"] = []
        events, sources = self.run_reconciliation()
        self.assertEqual(events, self.events)
        self.assertEqual(self.usta(sources)["crosslisted_reference_count"], 0)
        self.assertTrue(all("NO_EXACT_TENNIS_TOURNAMENT" in e for e in self.usta(sources)["reference_errors"]))

    def test_current_chicago_window_not_utc_date(self):
        now = dt.datetime(2026, 10, 19, 1, tzinfo=dt.timezone.utc)
        events, _ = self.run_reconciliation(now=now)
        self.assertIn("calendar_references", events[0])  # Still October 18 in Chicago.
        self.payload["window_start"] = "2026-10-19"
        events, sources = self.run_reconciliation(now=now)
        self.assertEqual(events, self.events)
        self.assertIn("TENNIS_PAYLOAD_WINDOW_MISMATCH", self.usta(sources)["reference_errors"])

    def test_stale_payload_global_source_and_source_specific_degradation(self):
        self.payload["generated_at"] = (NOW - dt.timedelta(hours=25)).isoformat()
        self.assert_rejected("TENNIS_PAYLOAD_STALE_OR_INVALID")
        self.payload["generated_at"] = NOW.isoformat()
        self.sources[1]["checked_at"] = (NOW - dt.timedelta(hours=25)).isoformat()
        self.assert_rejected("CANONICAL_SOURCE_STALE_OR_UNHEALTHY")
        self.sources[1]["checked_at"] = NOW.isoformat()
        self.payload["quality_gate"]["degraded_lanes"].append({"tour_id": "itf-men"})
        events, _ = self.assert_rejected("TENNIS_LANE_DEGRADED")
        self.assertIn("calendar_references", events[2])

    def test_source_unhealthy_and_event_stale_are_not_promoted(self):
        self.sources[1]["ok"] = False
        self.assert_rejected("CANONICAL_SOURCE_STALE_OR_UNHEALTHY")
        self.sources[1]["ok"] = True
        self.events[0]["source_stale"] = True
        self.assert_rejected("CANONICAL_EVENT_STALE")

    def test_wrong_underlying_name_dates_or_tour_fail_closed(self):
        for key, value in [("tournament", "M15 Austin, TX"), ("end_date", "2026-10-19"),
                           ("tour_id", "itf-women"), ("gender", "WOMEN")]:
            with self.subTest(key=key):
                original = self.payload["tournaments"][0][key]
                self.payload["tournaments"][0][key] = value
                self.assert_rejected("TENNIS_IDENTITY_MISMATCH")
                self.payload["tournaments"][0][key] = original

    def test_redirect_html_and_bad_calendar_do_not_become_evidence(self):
        for status, body, error in [(302, PDFS["men"], "PDF_HTTP_302"),
                                    (200, b"<html>blocked</html>", "PDF_INVALID_BYTES")]:
            with self.subTest(status=status):
                events, sources = self.run_reconciliation(get=getter(self.manifest, status, body))
                self.assertEqual(events, self.events)
                self.assertIn(error, self.usta(sources)["reference_errors"])
        self.manifest["calendars"]["men"]["url"] = "https://example.com/calendar.pdf"
        self.assert_rejected("INVALID_REVIEWED_CALENDAR")

    def test_missing_or_future_review_timestamp_fails_without_network(self):
        for value in (None, "2026-10-19T00:00:00Z", "2026-10-18T10:00:00", "bad"):
            with self.subTest(value=value):
                self.manifest["reviewed_at"] = value
                get = getter(self.manifest)
                events, sources = self.run_reconciliation(get=get)
                self.assertEqual(events, self.events)
                self.assertIn("INVALID_REVIEW_TIMESTAMP", self.usta(sources)["reference_errors"])
                get.assert_not_called()

    def test_usta_source_remains_exact_approved_manual_gap(self):
        for key, value in [("approved_catalog", False), ("source_type", "discovery"),
                           ("league", "USTA Pro Circuit | Women")]:
            with self.subTest(key=key):
                original = self.sources[0][key]
                self.sources[0][key] = value
                self.assert_rejected("USTA_SOURCE_SCOPE_MISMATCH")
                self.sources[0][key] = original

    def test_unapproved_canonical_source_or_event_never_gets_reference(self):
        self.sources[1]["approved_catalog"] = False
        self.assert_rejected("CANONICAL_SOURCE_STALE_OR_UNHEALTHY")
        self.sources[1]["approved_catalog"] = True
        self.events[0]["catalog_approval"] = "FUZZY DISCOVERY"
        self.assert_rejected("CANONICAL_EVENT_NOT_EXPLICITLY_APPROVED")

    def test_failed_quality_gate_and_critical_issues_block_all_references(self):
        for change in ({"passed": False}, {"critical_issues": ["Source integrity failed"]}):
            with self.subTest(change=change):
                original = deepcopy(self.payload["quality_gate"])
                self.payload["quality_gate"].update(change)
                events, sources = self.run_reconciliation()
                self.assertEqual(events, self.events)
                for lane in LANES:
                    self.assertIn("TENNIS_QUALITY_GATE_FAILED", self.usta(sources, lane)["reference_errors"])
                self.payload["quality_gate"] = original

    def test_output_deep_copies_nested_input_fields(self):
        events, sources = self.run_reconciliation()
        events[0]["restriction_signals"].append("changed output")
        events[0]["u18_matches"][0]["name"] = "output only"
        sources[1]["tour_ids"].append("output only")
        self.assertEqual(self.events[0]["restriction_signals"], ["KEEP ORIGINAL"])
        self.assertEqual(self.events[0]["u18_matches"][0]["name"], "Review only")
        self.assertEqual(self.sources[1]["tour_ids"], ["itf-men"])


if __name__ == "__main__":
    unittest.main()
