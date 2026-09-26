#!/usr/bin/env python3
"""Build an offline competition/event identity reference for report screening."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def key(value: object) -> str:
    text = clean(value).casefold()
    text = re.sub(r"\s*\([^)]*(?:game|match|leg|round|heat)\s*\d*[^)]*\)\s*$", "", text)
    text = text.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def participants(name: str) -> list[str]:
    value = clean(name)
    for separator in (" at ", " @ ", " vs. ", " vs "):
        if separator in value:
            sides = [clean(item) for item in value.split(separator, 1)]
            return sides if all(sides) and not any(key(item) == "tbd" for item in sides) else []
    return []


def main() -> None:
    schedule = json.loads((DATA / "global-schedule.json").read_text(encoding="utf-8"))
    season_map = json.loads((DATA / "catalog-season-map.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA / "catalog-live.json").read_text(encoding="utf-8"))
    alias_crosswalk = json.loads((DATA / "competition-alias-crosswalk.json").read_text(encoding="utf-8"))
    source_config = json.loads((DATA / "global-schedule-sources.json").read_text(encoding="utf-8"))

    # Catalog labels are not globally unique inside a sport. Soccer alone has
    # nine country-specific identities that share labels such as "Ligue 1" or
    # "President's Cup". Use the stable catalog key as the operational key so
    # those identities cannot absorb each other's sources or events.
    competitions: dict[tuple[str, str], dict] = {}
    split_parents: set[tuple[str, str]] = set()

    def add_competition(sport: str, event: dict, *, child: bool = False) -> None:
        league = clean(event.get("label") or event.get("catalog_event"))
        if not sport or not league:
            return
        ids = ([clean(event.get("source_id"))] if event.get("source_id") else [])
        ids.extend(clean(value) for value in event.get("source_ids") or [])
        identity_key = clean(event.get("key"))
        if not identity_key:
            raise ValueError(f"Catalog identity lacks a stable key: {sport} / {league}")
        entry = {
            "sport": sport,
            "league": league,
            "identity_key": identity_key,
            "source_ids": sorted(set(filter(None, ids))),
            "participants": [],
            "events": [],
        }
        identity = (sport, identity_key)
        if identity in competitions:
            existing = competitions[identity]
            if existing["league"] != league:
                raise ValueError(f"Catalog key changes label: {sport} / {identity_key}")
            existing["source_ids"] = sorted(set(existing["source_ids"] + entry["source_ids"]))
            return
        competitions[identity] = entry

    for sport_block in season_map.get("sports", []):
        sport = clean(sport_block.get("sport"))
        for group in sport_block.get("groups", []):
            for event in group.get("events", []):
                children = event.get("coverage_children") or []
                if children:
                    split_parents.add((sport, clean(event.get("catalog_event"))))
                    for child in children:
                        add_competition(sport, child, child=True)
                else:
                    add_competition(sport, event)
    for mapping in season_map.get("source_mappings", []):
        children = mapping.get("coverage_children") or []
        if children:
            sport = clean(mapping.get("sport"))
            split_parents.add((sport, clean(mapping.get("catalog_event"))))
            for child in children:
                add_competition(sport, child, child=True)
            continue
        sport, league = clean(mapping.get("sport")), clean(mapping.get("catalog_event"))
        if not sport or not league:
            continue
        source_id = clean(mapping.get("source_id"))
        candidates = [
            entry for (entry_sport, _), entry in competitions.items()
            if entry_sport == sport and entry["league"] == league
        ]
        source_matches = [entry for entry in candidates if source_id in entry["source_ids"]]
        if len(source_matches) == 1:
            entry = source_matches[0]
        elif len(candidates) == 1:
            entry = candidates[0]
        else:
            raise ValueError(f"Source mapping does not resolve one catalog identity: {sport} / {league} / {source_id}")
        if source_id and source_id not in entry["source_ids"]:
            entry["source_ids"].append(source_id)
    for mapping in season_map.get("catalog_event_mappings", []):
        sport = clean(mapping.get("sport"))
        children = mapping.get("coverage_children") or []
        if children:
            split_parents.add((sport, clean(mapping.get("catalog_event"))))
            for child in children:
                add_competition(sport, child, child=True)

    catalog_identities = set(competitions)

    # A source label is not a second approved competition. Resolve its events
    # to a catalog identity only when that source ID has exactly one catalog
    # target in the same sport. Shared feeds retain their explicit event label.
    source_targets: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for identity, entry in competitions.items():
        sport = entry["sport"]
        for source_id in entry["source_ids"]:
            source_targets[(sport, source_id)].add(identity)
    source_labels: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    split_source_ids = {
        (clean(source.get("sport")), clean(source.get("id")))
        for source in source_config.get("sources", [])
        if (clean(source.get("sport")), clean(source.get("league"))) in split_parents
    }

    def unique_target(sport: str, source_id: str) -> tuple[str, str] | None:
        targets = source_targets.get((sport, source_id), set())
        return next(iter(targets)) if len(targets) == 1 else None

    for source in source_config.get("sources", []):
        sport, source_id, label = (clean(source.get(field)) for field in ("sport", "id", "league"))
        target = unique_target(sport, source_id)
        if target and label and key(label) != key(competitions[target]["league"]):
            source_labels[target][label] = source_id

    observed_participants: dict[tuple[str, str], set[str]] = defaultdict(set)
    observed_events: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for event in schedule.get("events", []):
        sport, league, name = clean(event.get("sport")), clean(event.get("league")), clean(event.get("name"))
        if not sport or not league or not name:
            continue
        source_id = clean(event.get("source_id"))
        if (sport, league) in split_parents or (sport, source_id) in split_source_ids:
            # A combined legal parent with operational children is not itself
            # schedulable. Division-neutral feed rows remain held until a later
            # coverage step can prove which child identity they belong to.
            continue
        target = unique_target(sport, source_id)
        if target:
            if key(league) != key(competitions[target]["league"]):
                source_labels[target][league] = source_id
            identity = target
        else:
            label_targets = [
                candidate for candidate in catalog_identities
                if candidate[0] == sport and competitions[candidate]["league"] == league
            ]
            identity = label_targets[0] if len(label_targets) == 1 else (sport, f"schedule:{league}")
        entry = competitions.setdefault(identity, {"sport": sport, "league": league, "source_ids": [], "participants": [], "events": []})
        if source_id and source_id not in entry["source_ids"]:
            entry["source_ids"].append(source_id)
        sides = participants(name)
        observed_participants[identity].update(sides)
        observed_events[identity][key(name)] = {
            "name": name,
            "start_time": clean(event.get("start_time")),
            "participants": sides,
        }

    identities = {
        (entry["sport"], entry.get("identity_key")): entry
        for entry in competitions.values() if entry.get("identity_key")
    }
    catalog_labels: dict[tuple[str, str], list[dict]] = defaultdict(list)
    claimed_names = {}
    for identity in catalog_identities:
        entry = competitions[identity]
        normalized = (entry["sport"], key(entry["league"]))
        catalog_labels[(entry["sport"], entry["league"])].append(entry)
        claimed_names[normalized] = entry if normalized not in claimed_names else False
    alias_names = set()
    for row in alias_crosswalk["reviewed_aliases"]:
        sport, alias = row["sport"], clean(row["alias"])
        identity_key, catalog_identity = clean(row.get("identity_key")), clean(row.get("catalog_identity"))
        if bool(identity_key) == bool(catalog_identity):
            raise ValueError(f"Alias needs exactly one target type: {sport} / {alias}")
        label_targets = catalog_labels.get((sport, catalog_identity), [])
        target = identities.get((sport, identity_key)) if identity_key else (label_targets[0] if len(label_targets) == 1 else None)
        if not target:
            raise ValueError(f"Alias target is not a catalog identity: {sport} / {identity_key or catalog_identity}")
        if row.get("name_type") not in {"official", "operator", "data-provider"} or not str(row.get("evidence_url", "")).startswith("https://"):
            raise ValueError(f"Alias lacks reviewed official evidence: {sport} / {alias}")
        normalized = (sport, key(alias))
        if not normalized[1] or (normalized in claimed_names and claimed_names[normalized] is not target):
            raise ValueError(f"Alias collides with another competition: {sport} / {alias}")
        if normalized in alias_names:
            raise ValueError(f"Duplicate alias: {sport} / {alias}")
        alias_names.add(normalized)
        claimed_names[normalized] = target
        alias_entry = {
            "name": alias,
            "name_type": row["name_type"],
            "evidence_url": row["evidence_url"],
        }
        if clean(row.get("scope_note")):
            alias_entry["scope_note"] = clean(row["scope_note"])
        target.setdefault("aliases", []).append(alias_entry)

    output_competitions = []
    for identity, entry in sorted(competitions.items(), key=lambda item: (item[1]["sport"].casefold(), item[1]["league"].casefold(), item[1].get("identity_key", "").casefold())):
        entry["source_ids"] = sorted(set(filter(None, entry["source_ids"])))
        if source_labels.get(identity):
            entry["source_labels"] = [{"name": label, "source_id": source_id} for label, source_id in sorted(source_labels[identity].items(), key=lambda item: item[0].casefold())]
        entry["participants"] = sorted(observed_participants[identity], key=str.casefold)
        entry["events"] = sorted(observed_events[identity].values(), key=lambda item: (item["start_time"], item["name"].casefold()))
        entry["participant_coverage"] = "OBSERVED" if entry["participants"] else "NOT AVAILABLE"
        output_competitions.append(entry)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_menu_version": clean(catalog.get("menu_version")),
        "catalog_source": clean(catalog.get("source_label")),
        "schedule_generated_at": clean(schedule.get("generated_at")),
        "schedule_window_start": clean(schedule.get("window_start")),
        "schedule_window_end": clean(schedule.get("window_end")),
        "competition_count": len(output_competitions),
        "event_count": sum(len(item["events"]) for item in output_competitions),
        "competitions": output_competitions,
        "alias_review_queue": alias_crosswalk["review_queue"],
        "coverage_gaps": schedule.get("coverage_gaps", []),
    }
    (DATA / "competition-identity-registry.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Keep the all-sport scrub visible. A source name is evidence of schedule
    # provenance, not an organizer-verified or operator-verified approval alias.
    source_by_id = {(clean(row.get("sport")), clean(row.get("id"))): row for row in source_config.get("sources", [])}
    audit_sports = []
    for sport_block in season_map.get("sports", []):
        sport = clean(sport_block.get("sport"))
        catalog_entries = [competitions[identity] for identity in catalog_identities if identity[0] == sport]
        catalog_names = {entry["league"] for entry in catalog_entries}
        registered = [entry for entry in output_competitions if entry["sport"] == sport]
        shared_sources = []
        unmapped_sources = []
        for (source_sport, source_id), source in sorted(source_by_id.items()):
            if source_sport != sport:
                continue
            target_ids = sorted(source_targets.get((sport, source_id), set()))
            targets = [competitions[target]["league"] for target in target_ids]
            if len(targets) > 1:
                shared_sources.append({"source_id": source_id, "label": clean(source.get("league")), "catalog_targets": targets})
            elif not targets:
                unmapped_sources.append({"source_id": source_id, "label": clean(source.get("league"))})
        audit_sports.append({
            "sport": sport,
            "catalog_identities": len(catalog_entries),
            "registry_identities": len(registered),
            "organizer_alias_identities": sum(bool(entry.get("aliases")) for entry in registered),
            "source_label_identities": sum(bool(entry.get("source_labels")) for entry in registered),
            "schedule_only_labels": sorted((entry["league"] for entry in registered if not entry.get("identity_key")), key=str.casefold),
            "shared_sources_for_review": shared_sources,
            "sources_without_catalog_target": unmapped_sources,
        })
    audit = {
        "schema_version": 1,
        "note": "All catalog sports are inventoried. Source labels are matched only through a unique source ID; shared sources and schedule-only names require identity review. Organizer and operator aliases require separate evidence.",
        "sports": audit_sports,
    }
    if "--audit" in sys.argv[1:]:
        (DATA / "competition-alias-audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
