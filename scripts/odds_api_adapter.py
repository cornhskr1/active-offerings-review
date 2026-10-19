"""Pure, offline normalization of explicitly supplied The Odds API snapshots.

This module performs no I/O, collection, credential handling, or publication.
Mappings must contain only reviewed, direct provider-to-catalog identities.
The output is partial third-party event evidence, not an operator inventory,
complete schedule, event-status assertion, venue assertion, or age clearance.
Bookmakers, markets, prices, and every other non-allowlisted field are discarded.
This module does not implement an odds or operator comparison integration.
"""
from __future__ import annotations

from collections import defaultdict
import datetime as dt
import re

PROVIDER = "The Odds API"
SOURCE_ID = "the-odds-api"
UTC = dt.timezone.utc
MAPPING_FIELDS = frozenset({"provider_key", "catalog_identity_key", "sport", "league", "region"})
MAPPING_METADATA = frozenset({"mapping_basis", "coverage_complete"})
CONFIG_FIELDS = frozenset({"schema_version", "provider", "mappings"})
CONFIG_METADATA = frozenset({"mapping_scope", "documentation_url", "catalog_version"})
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
PROVIDER_KEY = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*\Z")
EVENT_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
PLACEHOLDER = re.compile(r"\b(?:TBD|TBA|to be determined|to be announced|winner of|loser of)\b", re.I)


def _timestamp(value):
    """Accept explicit ISO instants only, retaining microsecond precision in UTC."""
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError("invalid_timestamp")
    # datetime accepts timezone offsets with overflowing minutes; reject them.
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError("invalid_timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("invalid_timestamp") from None


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _text(value, *, empty=False):
    return (isinstance(value, str) and (empty or bool(value))
            and value == value.strip() and not any(ord(c) < 32 for c in value))


def _mapping_index(mappings):
    if (not isinstance(mappings, dict)
            or not CONFIG_FIELDS.issubset(mappings)
            or set(mappings) - CONFIG_FIELDS - CONFIG_METADATA
            or type(mappings["schema_version"]) is not int or mappings["schema_version"] != 1
            or mappings["provider"] != PROVIDER or not isinstance(mappings["mappings"], list)
            or not all(_text(mappings[field]) for field in CONFIG_METADATA if field in mappings)):
        raise ValueError("invalid_mapping_config")
    index = {}
    for row in mappings["mappings"]:
        if (not isinstance(row, dict) or not MAPPING_FIELDS.issubset(row)
                or set(row) - MAPPING_FIELDS - MAPPING_METADATA
                or row.get("mapping_basis", "documented_competition_name") != "documented_competition_name"
                or row.get("coverage_complete", False) is not False
                or not all(_text(row.get(field), empty=field == "region") for field in MAPPING_FIELDS)
                or not PROVIDER_KEY.fullmatch(row["provider_key"])
                or row["provider_key"] in index):
            raise ValueError("invalid_or_ambiguous_mapping")
        index[row["provider_key"]] = dict(row)
    return index


def _event(raw, mapping, observed):
    if not isinstance(raw, dict):
        raise ValueError("invalid_event")
    if raw.get("sport_key") != mapping["provider_key"]:
        raise ValueError("provider_key_mismatch")
    event_id = raw.get("id")
    home, away = raw.get("home_team"), raw.get("away_team")
    if not isinstance(event_id, str) or not EVENT_ID.fullmatch(event_id):
        raise ValueError("invalid_event_id")
    if (not _text(home) or not _text(away) or home.casefold() == away.casefold()
            or any(PLACEHOLDER.search(name) for name in (home, away))):
        raise ValueError("invalid_participants")
    start = _timestamp(raw.get("commence_time"))
    return {
        'id': f'{SOURCE_ID}:{mapping["provider_key"]}:{event_id}', "provider_event_id": event_id, "source_id": SOURCE_ID, "provider": PROVIDER,
        "catalog_identity_key": mapping["catalog_identity_key"], "provider_key": mapping["provider_key"],
        "name": f"{away} at {home}", "participants": [away, home], "start_time": _iso(start),
        "sport": mapping["sport"], "league": mapping["league"], "region": mapping["region"],
        "observed_at": _iso(observed), "status": "UNKNOWN",
        "coverage_status": "partial", "coverage_complete": False,
    }


def _deduplicate(candidates, rejected):
    """Keep a whole latest snapshot; never splice fields across observations.

    A changed identity under one ID, or different IDs for one exact matchup,
    invalidates every conflicting copy. Equal-time copies must normalize equally.
    IDs are scoped to sport, while physical identities also include the catalog
    competition, exact participant pair, and exact start instant. A same-ID
    home/away reversal is also an identity conflict, not a venue inference.
    """
    ids, identities = defaultdict(list), defaultdict(list)
    for index, (event, _) in enumerate(candidates):
        key = (event["sport"], event["provider_event_id"])
        identity = (event["sport"], event["catalog_identity_key"], tuple(sorted(event["participants"])), event["start_time"])
        ids[key].append(index)
        identities[identity].append(index)
    conflicts = set()
    for indices in ids.values():
        signatures = {
            (candidates[i][0]["catalog_identity_key"], candidates[i][0]["provider_key"],
             tuple(candidates[i][0]["participants"]), candidates[i][0]["start_time"])
            for i in indices
        }
        if len(signatures) > 1:
            conflicts.update(indices)
    for indices in identities.values():
        if len({candidates[i][0]["provider_event_id"] for i in indices}) > 1:
            conflicts.update(indices)
    events, duplicate_count = [], 0
    for index in sorted(conflicts):
        rejected.append({**candidates[index][1], "scope": "event", "reason": "conflicting_event_identity"})
    for indices in ids.values():
        usable = [index for index in indices if index not in conflicts]
        if not usable:
            continue
        newest_time = max(_timestamp(candidates[i][0]["observed_at"]) for i in usable)
        latest = [i for i in usable if _timestamp(candidates[i][0]["observed_at"]) == newest_time]
        chosen = candidates[latest[0]][0]
        if any(candidates[index][0] != chosen for index in latest[1:]):
            for index in usable:
                rejected.append({**candidates[index][1], "scope": "event", "reason": "ambiguous_duplicate_snapshot"})
            continue
        events.append(chosen)
        duplicate_count += len(usable) - 1
    return sorted(events, key=lambda event: (event["start_time"], event["sport"], event["id"])), duplicate_count


def normalize_snapshots(snapshots, observed_at, mappings):
    """Normalize in-memory event/odds snapshots into an event-only bundle.

    Each snapshot is {provider_key, observed_at, events: [official event rows]},
    with all non-event fields discarded. observed_at on the bundle is an explicit
    as-of boundary, not the acquisition time of old snapshots. Snapshot
    observations cannot exceed that boundary. No wall clock is consulted or
    freshness/complete-coverage inferred.

    Invalid top-level input or mapping configuration raises ValueError. Bad
    snapshots/events are excluded with non-sensitive positional rejection
    codes. Odds are never parsed, validated, copied, or emitted.
    Inputs are never mutated. Diagnostics never echo raw provider content.
    """
    mapping_index = _mapping_index(mappings)
    as_of = _timestamp(observed_at)
    if not isinstance(snapshots, list):
        raise ValueError("invalid_snapshots")
    rejected, candidates = [], []
    accepted_snapshots = received_events = 0
    for snapshot_index, snapshot in enumerate(snapshots):
        location = {"snapshot_index": snapshot_index}
        try:
            if not isinstance(snapshot, dict):
                raise ValueError("invalid_snapshot")
            provider_key = snapshot.get("provider_key")
            if not isinstance(provider_key, str) or provider_key not in mapping_index:
                raise ValueError("unmapped_provider_key")
            observation = _timestamp(snapshot.get("observed_at"))
            if observation > as_of:
                raise ValueError("future_snapshot_observation")
            rows = snapshot.get("events")
            if not isinstance(rows, list):
                raise ValueError("invalid_events")
        except ValueError as exc:
            rejected.append({**location, "scope": "snapshot", "reason": str(exc)})
            continue
        accepted_snapshots += 1
        received_events += len(rows)
        for event_index, raw in enumerate(rows):
            event_location = {**location, "event_index": event_index}

            def reject(scope, reason, **indices):
                rejected.append({**event_location, **indices, "scope": scope, "reason": reason})

            try:
                event = _event(raw, mapping_index[provider_key], observation)
                candidates.append((event, event_location))
            except ValueError as exc:
                reject("event", str(exc))
    events, duplicates = _deduplicate(candidates, rejected)
    return {
        "schema_version": 1, "provider": PROVIDER, "observed_at": _iso(as_of), "events": events,
        "coverage": {
            "coverage_status": "partial", "coverage_complete": False, "freshness": "unverified",
            "snapshots_received": len(snapshots), "snapshots_accepted": accepted_snapshots,
            "events_received": received_events, "events_emitted": len(events),
            "duplicate_events_removed": duplicates, "rejections": len(rejected),
            "note": "Third-party event reference only; missing events are not evidence of inactivity, operator offerings, or age clearance.",
        },
        "rejected": rejected,
    }


def normalize_snapshot(payload, provider_key, observed_at, mappings):
    """Normalize one official array (or one event object) without any I/O.

    A non-event object is not interpreted as a successful empty response.
    Bookmakers and odds are discarded, even when provided by an odds endpoint.
    """
    rows = [payload] if isinstance(payload, dict) else payload
    return normalize_snapshots([
        {"provider_key": provider_key, "observed_at": observed_at, "events": rows}
    ], observed_at, mappings)
