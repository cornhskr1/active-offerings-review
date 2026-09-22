#!/usr/bin/env python3
"""Build an offline competition/event identity reference for report screening."""

from __future__ import annotations

import json
import re
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

    competitions: dict[tuple[str, str], dict] = {}
    for sport_block in season_map.get("sports", []):
        sport = clean(sport_block.get("sport"))
        for group in sport_block.get("groups", []):
            for event in group.get("events", []):
                league = clean(event.get("catalog_event"))
                if not sport or not league:
                    continue
                source_id = clean(event.get("source_id"))
                competitions[(sport, league)] = {
                    "sport": sport,
                    "league": league,
                    "source_ids": [source_id] if source_id else [],
                    "participants": [],
                    "events": [],
                }
    for mapping in season_map.get("source_mappings", []):
        sport, league = clean(mapping.get("sport")), clean(mapping.get("catalog_event"))
        if not sport or not league:
            continue
        entry = competitions.setdefault((sport, league), {"sport": sport, "league": league, "source_ids": [], "participants": [], "events": []})
        source_id = clean(mapping.get("source_id"))
        if source_id and source_id not in entry["source_ids"]:
            entry["source_ids"].append(source_id)

    observed_participants: dict[tuple[str, str], set[str]] = defaultdict(set)
    observed_events: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for event in schedule.get("events", []):
        sport, league, name = clean(event.get("sport")), clean(event.get("league")), clean(event.get("name"))
        if not sport or not league or not name:
            continue
        entry = competitions.setdefault((sport, league), {"sport": sport, "league": league, "source_ids": [], "participants": [], "events": []})
        source_id = clean(event.get("source_id"))
        if source_id and source_id not in entry["source_ids"]:
            entry["source_ids"].append(source_id)
        sides = participants(name)
        observed_participants[(sport, league)].update(sides)
        observed_events[(sport, league)][key(name)] = {
            "name": name,
            "start_time": clean(event.get("start_time")),
            "participants": sides,
        }

    output_competitions = []
    for identity, entry in sorted(competitions.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())):
        entry["source_ids"] = sorted(set(filter(None, entry["source_ids"])))
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
        "coverage_gaps": schedule.get("coverage_gaps", []),
    }
    (DATA / "competition-identity-registry.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
