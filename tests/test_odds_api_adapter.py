"""Synthetic-only tests for the event-only, strictly offline provider adapter."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from odds_api_adapter import normalize_snapshot, normalize_snapshots

OBSERVED = "2026-10-19T02:00:00Z"
ROW = {
    "provider_key": "basketball_synthetic", "catalog_identity_key": "basketball-synthetic-league",
    "sport": "Basketball", "league": "Synthetic League", "region": "",
}
MAPPINGS = {"schema_version": 1, "provider": "The Odds API", "mappings": [ROW]}
EVENT = {
    "id": "synthetic-event-1", "sport_key": "basketball_synthetic",
    "sport_title": "Untrusted display title", "home_team": "Home Team", "away_team": "Away Team",
    "commence_time": "2026-10-20T19:30:00Z",
}
EXPECTED_EVENT = {
    "id": "the-odds-api:basketball_synthetic:synthetic-event-1", "provider_event_id": "synthetic-event-1",
    "source_id": "the-odds-api", "provider": "The Odds API",
    "catalog_identity_key": "basketball-synthetic-league", "provider_key": "basketball_synthetic",
    "name": "Away Team at Home Team", "participants": ["Away Team", "Home Team"],
    "start_time": "2026-10-20T19:30:00Z", "sport": "Basketball", "league": "Synthetic League", "region": "",
    "observed_at": OBSERVED, "status": "UNKNOWN", "coverage_status": "partial", "coverage_complete": False,
}


def snapshot(events=None, *, observed_at=OBSERVED, provider_key=ROW["provider_key"]):
    return {"provider_key": provider_key, "observed_at": observed_at, "events": [copy.deepcopy(EVENT)] if events is None else events}


def normalize(events=None, **kwargs):
    return normalize_snapshots([snapshot(events, **kwargs)], OBSERVED, MAPPINGS)


class EventNormalizationTests(unittest.TestCase):
    def test_direct_mapping_has_frozen_provider_provenance_and_exact_shape(self):
        bundle = normalize()
        self.assertEqual({"schema_version", "provider", "observed_at", "events", "coverage", "rejected"}, set(bundle))
        self.assertEqual(1, bundle["schema_version"])
        self.assertEqual("The Odds API", bundle["provider"])
        self.assertEqual([EXPECTED_EVENT], bundle["events"])
        self.assertEqual([], bundle["rejected"])

    def test_single_array_and_single_event_convenience(self):
        for payload in ([EVENT], EVENT):
            self.assertEqual(normalize(), normalize_snapshot(payload, ROW["provider_key"], OBSERVED, MAPPINGS))

    def test_utc_offsets_and_fractional_seconds_preserved(self):
        bundle = normalize([{**EVENT, "commence_time": "2026-10-20T21:30:00+02:00"}], observed_at="2026-10-18T21:00:00-05:00")
        self.assertEqual([EXPECTED_EVENT], bundle["events"])
        fractional = normalize([{**EVENT, "commence_time": "2026-10-20T21:30:00.123456+02:00"}])
        self.assertEqual("2026-10-20T19:30:00.123456Z", fractional["events"][0]["start_time"])

    def test_naive_date_only_malformed_and_invalid_offsets_rejected(self):
        for timestamp in (None, "", 123, "2026-10-20", "2026-10-20T19:30:00", "2026-10-20 19:30:00Z",
                          "2026-02-30T19:30:00Z", "2026-10-20T25:30:00Z", "2026-10-20T19:30:00+00:60",
                          "2026-10-20T19:30:00+24:00", "2026-10-20T19:30:00.1234567Z"):
            with self.subTest(timestamp=timestamp):
                bundle = normalize([{**EVENT, "commence_time": timestamp}])
                self.assertEqual([], bundle["events"])
                self.assertEqual("invalid_timestamp", bundle["rejected"][0]["reason"])
                self.assertEqual([], normalize(observed_at=timestamp)["events"])
                with self.assertRaisesRegex(ValueError, "invalid_timestamp"):
                    normalize_snapshots([], timestamp, MAPPINGS)

    def test_future_snapshot_is_rejected_not_relabelled(self):
        bundle = normalize(observed_at="2026-10-19T02:00:01Z")
        self.assertEqual([], bundle["events"])
        self.assertEqual("future_snapshot_observation", bundle["rejected"][0]["reason"])

    def test_stale_observation_is_preserved_without_claiming_freshness(self):
        bundle = normalize(observed_at="2020-01-01T00:00:00Z")
        self.assertEqual(OBSERVED, bundle["observed_at"])
        self.assertEqual("2020-01-01T00:00:00Z", bundle["events"][0]["observed_at"])
        self.assertEqual("unverified", bundle["coverage"]["freshness"])
        self.assertNotIn("fresh", bundle["events"][0])
        self.assertFalse(bundle["coverage"]["coverage_complete"])

    def test_past_start_and_untrusted_status_never_invent_event_status(self):
        for status in (None, "upcoming", "cancelled", "completed", "live"):
            bundle = normalize([{**EVENT, "commence_time": "2020-01-01T00:00:00Z", "status": status}])
            self.assertEqual("UNKNOWN", bundle["events"][0]["status"])
            self.assertEqual("2020-01-01T00:00:00Z", bundle["events"][0]["start_time"])

    def test_neutral_unknown_venue_age_phase_and_status_not_inferred(self):
        event = {**EVENT, "neutral_site": True, "venue": "Untrusted Venue", "location": "Untrusted City",
                 "age": 30, "age_verified": True, "season_stage": "FINAL", "season": "2026", "status": "UPCOMING"}
        self.assertEqual([EXPECTED_EVENT], normalize([event])["events"])
        for key in ("neutral_site", "venue", "location", "age", "age_verified", "season_stage", "season"):
            self.assertNotIn(key, normalize([event])["events"][0])

    def test_missing_or_invalid_identity_participants_are_rejected(self):
        for change in ({"id": None}, {"id": ""}, {"id": 123}, {"id": "https://invalid.test/event"},
                       {"home_team": None}, {"away_team": ""}, {"home_team": "Away Team"},
                       {"home_team": "AWAY TEAM"}, {"home_team": "TBD"}, {"away_team": "winner of Game 1"},
                       {"home_team": ["Home Team"]}, {"home_team": " Home Team"}, {"away_team": "Away\nTeam"}):
            with self.subTest(change=change):
                self.assertEqual([], normalize([{**EVENT, **change}])["events"])

    def test_unknown_conditional_and_nonexact_provider_keys_fail_closed(self):
        for provider_key in ("basketball_conditional", "basketball_synthetic_futures", "BASKETBALL_SYNTHETIC",
                             " basketball_synthetic", "basketball_unknown", None, []):
            with self.subTest(provider_key=provider_key):
                result = normalize(provider_key=provider_key)
                self.assertEqual([], result["events"])
                self.assertEqual("unmapped_provider_key", result["rejected"][0]["reason"])
        for provider_key in (None, "basketball_other", "BASKETBALL_SYNTHETIC"):
            result = normalize([{**EVENT, "sport_key": provider_key}])
            self.assertEqual("provider_key_mismatch", result["rejected"][0]["reason"])

    def test_empty_and_missing_payloads_never_claim_complete_coverage(self):
        empty = normalize([])
        self.assertEqual([], empty["events"])
        self.assertEqual([], empty["rejected"])
        self.assertFalse(empty["coverage"]["coverage_complete"])
        self.assertEqual("partial", empty["coverage"]["coverage_status"])
        for payload in (None, "error", {}, {"message": "secret error body"}):
            result = normalize_snapshot(payload, ROW["provider_key"], OBSERVED, MAPPINGS)
            self.assertEqual([], result["events"])
            self.assertTrue(result["rejected"])
            self.assertNotIn("secret error body", json.dumps(result))

    def test_invalid_snapshot_and_event_shapes_are_positional_rejections(self):
        result = normalize_snapshots([None, [], {}, snapshot([None, "not an event", EVENT])], OBSERVED, MAPPINGS)
        self.assertEqual([EXPECTED_EVENT], result["events"])
        self.assertEqual(5, len(result["rejected"]))
        self.assertEqual(4, result["coverage"]["snapshots_received"])
        self.assertEqual(1, result["coverage"]["snapshots_accepted"])
        self.assertEqual(3, result["coverage"]["events_received"])
        for payload in (None, {}, "not a list", ()):
            with self.assertRaisesRegex(ValueError, "invalid_snapshots"):
                normalize_snapshots(payload, OBSERVED, MAPPINGS)


class DuplicateTests(unittest.TestCase):
    def test_repeated_events_and_snapshots_collapse(self):
        result = normalize_snapshots([snapshot([EVENT, EVENT]), snapshot()], OBSERVED, MAPPINGS)
        self.assertEqual([EXPECTED_EVENT], result["events"])
        self.assertEqual(2, result["coverage"]["duplicate_events_removed"])
        self.assertEqual([], result["rejected"])

    def test_latest_observation_selected_independent_of_input_order(self):
        old = snapshot(observed_at="2026-10-18T02:00:00Z")
        latest = snapshot()
        for snapshots in ([old, latest], [latest, old]):
            self.assertEqual([EXPECTED_EVENT], normalize_snapshots(snapshots, OBSERVED, MAPPINGS)["events"])

    def test_one_id_changed_participants_or_start_invalidates_all_copies(self):
        for changes in ({"away_team": "Different Team"}, {"commence_time": "2026-10-21T19:30:00Z"},
                        {"away_team": "Home Team", "home_team": "Away Team"}):
            with self.subTest(changes=changes):
                result = normalize_snapshots([snapshot(), snapshot([{**EVENT, **changes}])], OBSERVED, MAPPINGS)
                self.assertEqual([], result["events"])
                self.assertEqual(["conflicting_event_identity"] * 2, [item["reason"] for item in result["rejected"]])

    def test_different_ids_for_same_identity_are_not_silently_merged(self):
        result = normalize([EVENT, {**EVENT, "id": "synthetic-event-2"}])
        self.assertEqual([], result["events"])
        self.assertEqual(2, len(result["rejected"]))

    def test_different_ids_with_home_away_reversal_are_still_identity_conflict(self):
        reversed_event = {**EVENT, "id": "different-id", "home_team": "Away Team", "away_team": "Home Team"}
        result = normalize([EVENT, reversed_event])
        self.assertEqual([], result["events"])
        self.assertEqual(2, len(result["rejected"]))

    def test_same_raw_id_in_different_sports_is_namespaced_and_allowed(self):
        other = {**ROW, "provider_key": "soccer_synthetic", "catalog_identity_key": "soccer-synthetic", "sport": "Soccer"}
        mappings = {**MAPPINGS, "mappings": [ROW, other]}
        result = normalize_snapshots([snapshot(), snapshot([{**EVENT, "sport_key": other["provider_key"]}], provider_key=other["provider_key"])], OBSERVED, mappings)
        self.assertEqual(2, len(result["events"]))
        self.assertEqual(2, len({event["id"] for event in result["events"]}))
        self.assertEqual({"synthetic-event-1"}, {event["provider_event_id"] for event in result["events"]})

    def test_same_raw_id_same_sport_different_catalog_identity_is_conflict(self):
        other = {**ROW, "provider_key": "basketball_other", "catalog_identity_key": "basketball-other"}
        mappings = {**MAPPINGS, "mappings": [ROW, other]}
        result = normalize_snapshots([snapshot(), snapshot([{**EVENT, "sport_key": other["provider_key"]}], provider_key=other["provider_key"])], OBSERVED, mappings)
        self.assertEqual([], result["events"])
        self.assertEqual(2, len(result["rejected"]))

    def test_conflict_does_not_discard_unrelated_valid_event(self):
        other = {**EVENT, "id": "unrelated-event", "away_team": "Other Away", "home_team": "Other Home"}
        result = normalize([EVENT, {**EVENT, "id": "duplicate-id"}, other])
        self.assertEqual(["unrelated-event"], [event["provider_event_id"] for event in result["events"]])


class ConfigurationAndPrivacyTests(unittest.TestCase):
    def test_known_mapping_metadata_is_supported_but_not_emitted(self):
        config = {**MAPPINGS, "mapping_scope": "Exact direct mappings only", "documentation_url": "https://example.invalid/docs",
                  "catalog_version": "synthetic-v1", "mappings": [{**ROW, "mapping_basis": "documented_competition_name", "coverage_complete": False}]}
        self.assertEqual([EXPECTED_EVENT], normalize_snapshots([snapshot()], OBSERVED, config)["events"])

    def test_invalid_and_conditional_mapping_configs_fail_closed(self):
        bad_rows = [{**ROW, "mapping_basis": "conditional"}, {**ROW, "coverage_complete": True},
                    {**ROW, "status": "conditional"}, {**ROW, "requires_review": True},
                    {**ROW, "provider_key": " basketball_synthetic"}, {**ROW, "league": ""},
                    {**ROW, "region": None}, {key: value for key, value in ROW.items() if key != "sport"}, None]
        configs = [None, {}, {**MAPPINGS, "schema_version": True}, {**MAPPINGS, "schema_version": 2},
                   {**MAPPINGS, "provider": "Different Provider"}, {**MAPPINGS, "conditional": []},
                   {**MAPPINGS, "mappings": {}}, {**MAPPINGS, "mappings": [ROW, ROW]}]
        configs.extend({**MAPPINGS, "mappings": [row]} for row in bad_rows)
        for config in configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                normalize_snapshots([snapshot()], OBSERVED, config)

    def test_bookmakers_prices_keys_urls_raw_fields_never_enter_bundle(self):
        marker = "SECRET_SYNTHETIC_DO_NOT_COPY"
        raw = {**EVENT, "apiKey": marker, "source_url": "https://example.invalid/?apiKey=" + marker,
               "status": marker, "bookmakers": [
                   {"key": marker, "title": marker, "url": marker, "last_update": "future_or_malformed",
                    "markets": [{"key": "h2h", "outcomes": [{"name": "Home Team", "price": -110}]}]},
                   {"key": marker, "markets": [{"key": "totals", "outcomes": [{"name": "Over", "price": float("nan"), "point": float("inf")}]}]}],
               "reference_quotes": [{"reference_id": marker}], "raw_payload": {"secret": marker}}
        incoming = {**snapshot([raw]), "api_key": marker, "odds_format": marker, "raw_response": marker}
        result = normalize_snapshots([incoming], OBSERVED, MAPPINGS)
        self.assertEqual([EXPECTED_EVENT], result["events"])
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn(marker, encoded)
        for key in ("bookmakers", "markets", "price", "reference_quotes", "api_key", "raw_payload", "source_url"):
            self.assertNotIn('"' + key + '"', encoded)

    def test_even_malformed_bookmakers_are_ignored_in_event_only_scope(self):
        for books in (None, "bad", {}, [None], [{"markets": "not markets"}]):
            self.assertEqual([EXPECTED_EVENT], normalize([{**EVENT, "bookmakers": books}])["events"])

    def test_inputs_are_not_mutated_and_results_do_not_alias_inputs(self):
        snapshots, mappings = [snapshot()], copy.deepcopy(MAPPINGS)
        original = copy.deepcopy((snapshots, mappings))
        result = normalize_snapshots(snapshots, OBSERVED, mappings)
        self.assertEqual(original, (snapshots, mappings))
        result["events"][0]["participants"].append("Injected")
        result["events"][0]["league"] = "Injected"
        self.assertEqual(original, (snapshots, mappings))

    def test_module_import_and_normalization_perform_no_io(self):
        source = (ROOT / "scripts" / "odds_api_adapter.py").read_text()
        compiled = compile(source, "odds_api_adapter.py", "exec")
        namespace = {"__name__": "offline_import_test"}
        with patch("builtins.open", side_effect=AssertionError("file I/O forbidden")), \
             patch("pathlib.Path.read_text", side_effect=AssertionError("file I/O forbidden")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("file I/O forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            exec(compiled, namespace)
            result = namespace["normalize_snapshots"]([snapshot()], OBSERVED, MAPPINGS)
        self.assertEqual([EXPECTED_EVENT], result["events"])


if __name__ == "__main__":
    unittest.main()
