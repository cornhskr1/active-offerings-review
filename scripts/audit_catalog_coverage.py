#!/usr/bin/env python3
"""Audit catalog-to-coverage identity and staff-facing schedule links."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def source_ids(event: dict) -> list[str]:
    values = list(event.get("source_ids") or [])
    if event.get("source_id"):
        values.append(event["source_id"])
    return [str(value) for value in values if value]


def mapped_sources(season_map: dict) -> dict[str, list[dict]]:
    mapped: dict[str, list[dict]] = defaultdict(list)
    for sport in season_map.get("sports", []):
        for group in sport.get("groups", []):
            for event in group.get("events", []):
                for source_id in source_ids(event):
                    mapped[source_id].append(
                        {
                            "sport": sport.get("sport"),
                            "country": group.get("country"),
                            "catalog_event": event.get("catalog_event"),
                        }
                    )
    for event in season_map.get("catalog_event_mappings", []):
        for source_id in source_ids(event):
            mapped[source_id].append(
                {
                    "sport": event.get("sport"),
                    "country": event.get("country"),
                    "catalog_event": event.get("catalog_event"),
                }
            )
    return mapped


def sport_family(value: str | None) -> str:
    text = str(value or "").strip()
    return text.removeprefix("NCAA ")


def main() -> None:
    season_map = load("catalog-season-map.json")
    configured = load("global-schedule-sources.json").get("sources", [])
    by_id = defaultdict(list)
    for source in configured:
        by_id[str(source.get("id") or "")].append(source)

    duplicate_ids = sorted(source_id for source_id, rows in by_id.items() if source_id and len(rows) > 1)
    mappings = mapped_sources(season_map)
    cross_sport = []
    for source_id, rows in mappings.items():
        source = (by_id.get(source_id) or [None])[0]
        if not source:
            continue
        source_sport = sport_family(source.get("sport"))
        mapped_sports = {sport_family(row.get("sport")) for row in rows}
        if source_sport not in mapped_sports:
            cross_sport.append(
                {"source_id": source_id, "source_sport": source.get("sport"), "mapped_sports": sorted(mapped_sports)}
            )

    missing_human_links = [
        {
            "id": source.get("id"),
            "sport": source.get("sport"),
            "region": source.get("region"),
            "league": source.get("league"),
        }
        for source in configured
        if not (source.get("official_schedule_url") or source.get("public_url"))
    ]
    summary = {
        "configured_sources": len(configured),
        "duplicate_source_ids": len(duplicate_ids),
        "cross_sport_mappings": len(cross_sport),
        "human_schedule_links": len(configured) - len(missing_human_links),
        "missing_human_schedule_links": len(missing_human_links),
        "missing_links_by_sport": dict(sorted(Counter(row["sport"] for row in missing_human_links).items())),
    }
    print(json.dumps({"summary": summary, "missing_human_links": missing_human_links}, indent=2, ensure_ascii=False))
    if duplicate_ids or cross_sport:
        raise SystemExit(json.dumps({"duplicate_source_ids": duplicate_ids, "cross_sport_mappings": cross_sport}, indent=2))


if __name__ == "__main__":
    main()
