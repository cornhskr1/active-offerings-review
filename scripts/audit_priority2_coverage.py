#!/usr/bin/env python3
"""Inventory schedule coverage for every catalog operational identity."""

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "priority2-coverage-inventory.json"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def source_ids(item):
    return sorted(set(([item["source_id"]] if item.get("source_id") else []) + item.get("source_ids", [])))


def season_state(item):
    if item.get("season_hold") is True:
        return "DOCUMENTED_HOLD"
    if item.get("season_window_complete") is False:
        return "PARTIAL_WINDOW"
    if item.get("season_start_date") and item.get("season_end_date"):
        return "DATED_WINDOW"
    if item.get("season_start") and item.get("season_end"):
        return "RECURRING_WINDOW"
    window = str(item.get("season_window") or "")
    if "pending" in window.lower() or not window:
        return "PENDING_DATES" if window or "pending" in str(item.get("season_basis") or "").lower() else "NO_WINDOW"
    return "DESCRIPTIVE_WINDOW"


def catalog_identities(season_map):
    rows = {}

    def add(sport, item, parent="", kind="catalog"):
        label = item.get("label") or item.get("catalog_event")
        if not label:
            raise ValueError(f"Missing operational label: {sport}")
        key = (sport, label)
        if key in rows:
            # source_mappings repeat some sports entries; the sport hierarchy is
            # authoritative for the legal parent and child identity.
            rows[key]["mapped_source_ids"].update(source_ids(item))
            return
        rows[key] = {
            "sport": sport,
            "league": label,
            "identity_key": item.get("key") or "",
            "approval_parent": parent or item.get("catalog_event") or label,
            "kind": "split-child" if parent else kind,
            "season_window": item.get("season_window") or "",
            "season_state": season_state(item),
            "season_status": item.get("season_status") or "",
            "mapped_source_ids": set(source_ids(item)),
        }
        if item.get("hold_reason"):
            rows[key]["hold_reason"] = item["hold_reason"]

    for sport in season_map["sports"]:
        for group in sport.get("groups", []):
            for event in group.get("events", []):
                children = event.get("coverage_children") or []
                if children:
                    for child in children:
                        add(sport["sport"], child, event["catalog_event"])
                else:
                    add(sport["sport"], event)
    for field in ("source_mappings", "catalog_event_mappings"):
        for mapping in season_map.get(field, []):
            children = mapping.get("coverage_children") or []
            if children:
                for child in children:
                    add(mapping["sport"], child, mapping["catalog_event"])
            elif field == "source_mappings":
                add(mapping["sport"], mapping, kind="source-mapping")
    return rows


def build():
    season_map = read("catalog-season-map.json")
    registry = read("competition-identity-registry.json")
    schedule = read("global-schedule.json")
    source_config = read("global-schedule-sources.json")
    schedule_sources = list(source_config["sources"])
    for path in sorted(DATA.glob("soccer-*-sources.json")):
        schedule_sources.extend(json.loads(path.read_text(encoding="utf-8")).get("sources", []))
    catalog = read("catalog-live.json")
    catalog_rows = catalog_identities(season_map)
    configured = {(item["sport"], item["id"]): item for item in schedule_sources}
    observed = {(item["sport"], item["id"]): item for item in schedule.get("sources", [])}
    registry_rows = {(item["sport"], item["league"]): item for item in registry["competitions"]}
    missing = set(catalog_rows) - set(registry_rows)
    if missing:
        raise ValueError(f"Catalog identities missing from registry: {sorted(missing)[:5]}")

    identities = []
    for key, mapped in sorted(catalog_rows.items()):
        entry = registry_rows[key]
        if mapped["kind"] == "split-child" and entry.get("identity_key") != mapped["identity_key"]:
            raise ValueError(f"Child key mismatch: {key}")
        ids = sorted(set(entry.get("source_ids", [])) | mapped["mapped_source_ids"])
        sources = []
        for sid in ids:
            source = configured.get((key[0], sid))
            health = observed.get((key[0], sid))
            sources.append({
                "id": sid,
                "type": (source or {}).get("source_type") or ("adapter" if source else "not-in-schedule-config"),
                "configured_league": (source or {}).get("league") or "",
                "refresh_ok": (health or {}).get("ok"),
                "events_in_window": (health or {}).get("events", 0),
            })
        types = {source["type"] for source in sources}
        if "not-in-schedule-config" in types:
            state = "SOURCE_SCOPE_REVIEW"
        elif types and types <= {"coverage-gap"}:
            state = "ADAPTER_GAP"
        elif types and types <= {"coverage-gap", "official-event-window"}:
            state = "OFFICIAL_WINDOW_ONLY"
        elif types:
            state = "ADAPTER_CONFIGURED"
        else:
            state = "NO_LINKED_SOURCE"
        identities.append({
            **{k: v for k, v in mapped.items() if k != "mapped_source_ids"},
            "coverage_state": state,
            "sources": sources,
            "events_in_window": len(entry.get("events", [])),
        })

    schedule_only = sorted(set(registry_rows) - set(catalog_rows))
    states = Counter(item["coverage_state"] for item in identities)
    seasons = Counter(item["season_state"] for item in identities)
    sports = defaultdict(lambda: {"identities": 0, "split_children": 0, "no_linked_source": 0, "adapter_gaps": 0, "pending_dates": 0})
    for row in identities:
        sport = sports[row["sport"]]
        sport["identities"] += 1
        sport["split_children"] += row["kind"] == "split-child"
        sport["no_linked_source"] += row["coverage_state"] == "NO_LINKED_SOURCE"
        sport["adapter_gaps"] += row["coverage_state"] == "ADAPTER_GAP"
        sport["pending_dates"] += row["season_state"] in ("PENDING_DATES", "NO_WINDOW", "PARTIAL_WINDOW")
    return {
        "schema_version": 1,
        "catalog_menu_version": catalog["menu_version"],
        "registry_generated_at": registry["generated_at"],
        "schedule_generated_at": schedule["generated_at"],
        "schedule_window_start": schedule["window_start"],
        "schedule_window_end": schedule["window_end"],
        "note": "A configured source is not proof of current fixtures; no event in a seven-day window is not proof of a gap. A source ID absent from the schedule configuration may be an official-link reference, not a fixture adapter. Coverage-gap sources and absent division dates stay explicit work items. Schedule-only labels do not create catalog approval.",
        "summary": {
            "catalog_operational_identities": len(identities),
            "split_children": sum(item["kind"] == "split-child" for item in identities),
            "coverage_states": dict(sorted(states.items())),
            "season_states": dict(sorted(seasons.items())),
            "reported_gap_areas": len(schedule["coverage_gaps"]),
            "reported_gap_labels": sum(len(gap.get("competitions", [])) for gap in schedule["coverage_gaps"]),
            "schedule_only_not_independent_approvals": [{"sport": sport, "league": label} for sport, label in schedule_only],
        },
        "by_sport": dict(sorted(sports.items())),
        "identities": identities,
    }


if __name__ == "__main__":
    payload = build()
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
