#!/usr/bin/env python3
"""Build the small, fail-closed tennis feed consumed by Review Today.

This script performs no web browsing and never determines catalog approval from a
tournament name.  A tournament is eligible only when its tour ID is explicitly
mapped to a source ID that is present in the Tennis section of the catalog season
map.  Acceptance pools are never treated as active fields.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TZ = ZoneInfo("America/Chicago")
NOW = dt.datetime.now(dt.timezone.utc)


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def norm(value):
    text = str(value or "").lower()
    text = re.sub(r"[\u2018\u2019'`]", "", text)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def tennis_catalog_source_ids(season_map):
    ids = set()
    for sport in season_map.get("sports") or []:
        if sport.get("sport") != "Tennis":
            continue
        for group in sport.get("groups") or []:
            for event in group.get("events") or []:
                source_id = event.get("source_id")
                if source_id:
                    ids.add(source_id)
    return ids


def verified_registry_index(registry):
    records = registry.get("verified_u18") or []
    out = {}
    for record in records:
        for name in [record.get("name"), *(record.get("aliases") or [])]:
            if name:
                out[norm(name)] = record
    return out


def targeted_registry_index(registry):
    records = registry.get("junior_targeted_candidates") or []
    out = {}
    for record in records:
        for name in [record.get("name"), *(record.get("aliases") or [])]:
            if name:
                out[norm(name)] = record
    return out


def verified_age_cache_index(age_cache):
    records = age_cache.get("records") or {}
    if isinstance(records, dict):
        values = records.values()
    else:
        values = records
    out = {}
    for record in values:
        if str(record.get("age_status") or "").upper() != "VERIFIED U18":
            continue
        for name in [record.get("name"), *(record.get("aliases") or [])]:
            if name:
                out[norm(name)] = record
    return out


def is_junior_competition(tournament):
    """Junior rankings may inform identity research but junior events are never approved."""
    text = " ".join(str(tournament.get(key) or "") for key in (
        "tour_id", "tour", "category"
    )).lower()
    return bool(re.search(r"\bitf[ -]?(?:world tennis tour )?juniors?\b|\bjunior(?:s)?\b", text))


def is_active_field(tournament, config):
    field_type = str(tournament.get("participant_field_type") or "").upper()
    if field_type == "ACCEPTANCE_POOL":
        return False
    configured = set(config.get("active_field_types") or [])
    has_people = bool(tournament.get("participants") or tournament.get("confirmed_u18") or tournament.get("verified_u18"))
    # A link or label is not a captured field. At least one extracted active
    # participant is required before the tournament can be screened.
    return field_type in configured and has_people


def exact_active_matches(tournament, verified, targeted):
    if not tournament.get("participants"):
        # Compatibility with the existing collector, which already separates
        # active-field confirmations from pre-draw watch records.
        participants = tournament.get("confirmed_u18") or tournament.get("verified_u18") or []
    else:
        participants = tournament.get("participants") or []

    red = {}
    amber = {}
    for participant in participants:
        key = norm(participant.get("name"))
        if key in verified:
            red[key] = {**participant, **verified[key]}
        elif key in targeted:
            amber[key] = {**participant, **targeted[key]}
    return list(red.values()), list(amber.values())


def build_review(intelligence, registry, season_map, config, age_cache=None):
    approved_source_ids = tennis_catalog_source_ids(season_map)
    tour_map = config.get("tour_approval_map") or {}
    coverage = {}
    alerts = []
    blocked = []
    # A profile already verified U18 must be actionable immediately; it must not
    # wait for the slower weekly registry rebuild to be promoted.
    verified = verified_age_cache_index(age_cache or {})
    verified.update(verified_registry_index(registry))
    targeted = targeted_registry_index(registry)

    for tournament in intelligence.get("tournaments") or []:
        tour_id = tournament.get("tour_id")
        if is_junior_competition(tournament):
            blocked.append({
                "tournament_id": tournament.get("id"),
                "tournament": tournament.get("tournament"),
                "tour_id": tour_id,
                "reason": "ITF junior competition is intelligence-only and is not catalog-approved"
            })
            continue
        source_id = tour_map.get(tour_id)
        if not source_id or source_id not in approved_source_ids:
            blocked.append({
                "tournament_id": tournament.get("id"),
                "tournament": tournament.get("tournament"),
                "tour_id": tour_id,
                "reason": "No explicit approved catalog source mapping"
            })
            continue

        lane = coverage.setdefault(source_id, {
            "source_id": source_id,
            "tournaments": 0,
            "active_fields": 0,
            "field_pending": 0,
            "u18_alerts": 0
        })
        lane["tournaments"] += 1

        if not is_active_field(tournament, config):
            lane["field_pending"] += 1
            continue

        lane["active_fields"] += 1
        red, amber = exact_active_matches(tournament, verified, targeted)

        if red:
            lane["u18_alerts"] += 1
            alerts.append({
                "id": f"tennis-u18|{tournament.get('id')}",
                "severity": "RED",
                "type": "TENNIS U18 ACTIVE FIELD",
                "sport": "Tennis",
                "league": tournament.get("tour") or "Approved Tennis",
                "event": tournament.get("tournament"),
                "start_time": f"{tournament.get('start_date')}T12:00:00Z",
                "end_date": tournament.get("end_date"),
                "location": tournament.get("location"),
                "source_id": source_id,
                "source_url": tournament.get("draw_url") or tournament.get("order_url") or tournament.get("source_url"),
                "athletes": [p.get("name") for p in red if p.get("name")],
                "reason": "Verified U18 athlete confirmed in an active draw or order of play.",
                "staff_action": "Review athlete-specific performance/nonperformance markets involving the confirmed U18 participant across all licensed sportsbook platforms."
            })

        if amber:
            alerts.append({
                "id": f"tennis-identity|{tournament.get('id')}",
                "severity": "AMBER",
                "type": "TENNIS IDENTITY REVIEW",
                "sport": "Tennis",
                "league": tournament.get("tour") or "Approved Tennis",
                "event": tournament.get("tournament"),
                "start_time": f"{tournament.get('start_date')}T12:00:00Z",
                "end_date": tournament.get("end_date"),
                "location": tournament.get("location"),
                "source_id": source_id,
                "source_url": tournament.get("draw_url") or tournament.get("order_url") or tournament.get("source_url"),
                "athletes": [p.get("name") for p in amber if p.get("name")],
                "reason": "Active-field athlete exactly matches a targeted junior-age identity that still requires DOB confirmation.",
                "staff_action": "Confirm the athlete identity and date of birth before clearing athlete-specific markets."
            })

    alerts.sort(key=lambda row: (row.get("start_time") or "", row.get("severity") != "RED", row.get("event") or ""))
    lanes = sorted(coverage.values(), key=lambda row: row["source_id"])
    return {
        "schema_version": 1,
        "generated_at": NOW.isoformat(),
        "timezone": "America/Chicago",
        "mode": config.get("mode") or "shadow",
        "window_start": intelligence.get("window_start"),
        "window_end": intelligence.get("window_end"),
        "source_generated_at": intelligence.get("generated_at"),
        "summary": {
            "approved_tournaments": sum(row["tournaments"] for row in lanes),
            "active_fields_screened": sum(row["active_fields"] for row in lanes),
            "field_pending": sum(row["field_pending"] for row in lanes),
            "actionable_alerts": len(alerts),
            "verified_u18_alerts": sum(row["severity"] == "RED" for row in alerts),
            "identity_reviews": sum(row["severity"] == "AMBER" for row in alerts),
            "blocked_unapproved_or_unmapped": len(blocked)
        },
        "alerts": alerts,
        "coverage": lanes,
        "blocked": blocked,
        "guardrails": config.get("guardrails") or {}
    }


def main():
    intelligence = load(DATA / "tennis-intelligence.json", {})
    registry = load(DATA / "tennis-u18-registry.json", {})
    season_map = load(DATA / "catalog-season-map.json", {})
    config = load(DATA / "tennis-v2-config.json", {})
    age_cache = load(DATA / "tennis-age-cache.json", {})
    output = build_review(intelligence, registry, season_map, config, age_cache)
    (DATA / "tennis-review.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["summary"]))


if __name__ == "__main__":
    main()
