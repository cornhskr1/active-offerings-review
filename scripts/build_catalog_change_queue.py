#!/usr/bin/env python3
"""Build the fail-closed Catalog Change Queue.

The queue detects changes between the live, published NRGC catalog and the
last completed season-map snapshot. Operator requests and staff recommendations
are intentionally outside this system.

Nothing emitted by this script is automatically publishable to Review Today.
The published catalog controls approval; schedule activation still requires an
explicit, reviewed mapping to that approval.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CATALOG_PATH = DATA / "catalog-live.json"
SEASON_MAP_PATH = DATA / "catalog-season-map.json"
OFFICIAL_SOURCES_PATH = DATA / "catalog-official-sources.json"
SCHEDULE_SOURCES_PATH = DATA / "global-schedule-sources.json"
OUTPUT_PATH = DATA / "catalog-change-queue.json"

COUNTRIES = {
    "Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahrain", "Belarus", "Belgium", "Bolivia",
    "Bosnia and Herzegovina", "Brazil", "Bulgaria", "Canada", "Chile", "China",
    "Colombia", "Costa Rica", "Croatia", "Cyprus", "Czech Republic", "Denmark",
    "Dominican Republic", "Ecuador", "Egypt", "England", "Estonia", "Finland",
    "France", "Georgia", "Germany", "Greece", "Hungary", "Iceland", "India",
    "Indonesia", "Ireland", "Israel", "Italy", "Japan", "Kazakhstan", "Korea",
    "Latvia", "Lithuania", "Luxembourg", "Malaysia", "Mexico", "Morocco",
    "Netherlands", "New Zealand", "North Macedonia", "Norway", "Paraguay",
    "Peru", "Poland", "Portugal", "Romania", "Saudi Arabia", "Scotland",
    "Serbia", "Singapore", "Slovakia", "Slovenia", "South Africa", "Spain",
    "Sweden", "Switzerland", "Thailand", "Turkey", "Ukraine",
    "United Arab Emirates", "United States", "Uruguay", "Venezuela",
}

SECTION_PATTERN = re.compile(
    r"^(international-level competitions|international domestic leagues|"
    r"fifa international events|confederation international events|"
    r"cross-confederation events|domestic events|summer olympic games|"
    r"winter olympic games|main tour events|road cycling|"
    r"discipline world championships|continental tours)$",
    re.I,
)

COUNTRY_PATTERN = re.compile(
    r"^(international|europe|asia|africa|oceania|north america|south america|"
    r"international\s*/\s*europe|united states\s*/\s*canada)$",
    re.I,
)

ORG_PATTERN = re.compile(
    r"(association|federation|confederation|organization|commission|council|"
    r"board|authority|committee|union|fédération|federación|confederación)",
    re.I,
)

NOTE_PATTERN = re.compile(
    r"(no proposition|no player proposition|not permissible|wager limit|"
    r"markets (?:must )?close|markets limited|must be disabled|restriction)",
    re.I,
)


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    text = str(value or "").replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().casefold()


def event_base(value: Any) -> str:
    text = str(value or "").strip()
    return canonical(
        re.sub(
            r"\s+(?:\||-)\s+(?:NO .*|MARKETS .*|WAGER .*|NOT PERMISSIBLE.*)$",
            "",
            text,
            flags=re.I,
        )
    )


def line_role(line: str) -> str:
    text = str(line or "").strip()
    if SECTION_PATTERN.search(text):
        return "hierarchy-section"
    if text in COUNTRIES or COUNTRY_PATTERN.search(text):
        return "country"
    if "|" not in text and ORG_PATTERN.search(text):
        return "governing-body"
    if NOTE_PATTERN.search(text):
        return "restriction"
    return "approved-event"


def stable_id(*parts: Any) -> str:
    digest = hashlib.sha256("\x1f".join(canonical(x) for x in parts).encode()).hexdigest()[:16]
    return f"catalog-intake-{digest}"


def source_ids(event: dict[str, Any]) -> list[str]:
    values = list(event.get("source_ids") or [])
    if event.get("source_id"):
        values.append(event["source_id"])
    for child in event.get("coverage_children") or []:
        values.extend(source_ids(child))
    return [str(value) for value in values if value]


def mapped_entities(season_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for sport in season_map.get("sports", []):
        sport_name = sport.get("sport", "")
        for group in sport.get("groups", []):
            for event in group.get("events", []):
                name = event.get("catalog_event")
                if not name:
                    continue
                mapped[f"{canonical(sport_name)}|{canonical(name)}"] = {
                    "key": event.get("key"),
                    "source_ids": source_ids(event),
                    "country": group.get("country"),
                    "governing_body": group.get("governing_body"),
                }
    for event in season_map.get("catalog_event_mappings", []):
        sport_name = event.get("sport", "")
        name = event.get("catalog_event")
        if name:
            mapped[f"{canonical(sport_name)}|{canonical(name)}"] = {
                "key": event.get("key"),
                "source_ids": source_ids(event),
                "country": event.get("country"),
                "governing_body": event.get("governing_body"),
            }
    return mapped


def derived_known_lines(sport: dict[str, Any], season_map: dict[str, Any]) -> set[str]:
    known: set[str] = set()
    for group in sport.get("groups", []):
        for key in ("country", "governing_body"):
            if group.get(key):
                known.add(canonical(group[key]))
        for event in group.get("events", []):
            if event.get("catalog_event"):
                known.add(canonical(event["catalog_event"]))
                known.add(event_base(event["catalog_event"]))
    for event in season_map.get("catalog_event_mappings", []):
        if event.get("sport") == sport.get("sport") and event.get("catalog_event"):
            known.add(canonical(event["catalog_event"]))
            known.add(event_base(event["catalog_event"]))
    return known


def setup_for(role: str, change_type: str) -> list[dict[str, str]]:
    if change_type == "catalog-removal":
        return [
            {"code": "catalog-removal-review", "label": "Confirm the catalog removal"},
            {"code": "schedule-deactivation", "label": "Disable any mapped schedule publication"},
            {"code": "crosswalk-retirement", "label": "Retire or revise the approved-event crosswalk"},
        ]
    if role == "restriction":
        return [
            {"code": "restriction-scope", "label": "Review the restriction scope and affected approvals"},
            {"code": "crosswalk-update", "label": "Update affected catalog mappings"},
            {"code": "regression-check", "label": "Verify Review Today classification"},
        ]
    if role in {"governing-body", "country", "hierarchy-section"}:
        return [
            {"code": "hierarchy", "label": "Confirm the catalog hierarchy"},
            {"code": "official-source", "label": "Verify the official governing source"},
            {"code": "crosswalk-update", "label": "Update affected event mappings"},
        ]
    return [
        {"code": "hierarchy", "label": "Confirm sport, region, and governing body"},
        {"code": "official-source", "label": "Verify the official competition source"},
        {"code": "season-mapping", "label": "Map the season or event dates"},
        {"code": "schedule-source", "label": "Configure the official schedule source and source ID"},
        {"code": "restriction-scope", "label": "Review applicable catalog restrictions"},
        {"code": "publication-validation", "label": "Validate the approved-only publication gate"},
    ]


def base_item(item_id: str, item_type: str, sport: str, detected_at: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "item_type": item_type,
        "sport": sport,
        "severity": "AMBER",
        "detected_at": detected_at,
        "publication_gate": "BLOCKED",
        "publishable": False,
        "review_today_eligible": False,
        "guardrail": "The published catalog controls approval; Review Today eligibility may not be inferred until the detected entry is explicitly mapped.",
    }


def catalog_item(
    *,
    item_type: str,
    sport: str,
    line: str | None,
    previous_line: str | None,
    catalog: dict[str, Any],
    mapped: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    current = line or previous_line or ""
    role = line_role(current)
    mapped_record = mapped.get(f"{canonical(sport)}|{canonical(current)}") or mapped.get(
        f"{canonical(sport)}|{event_base(current)}"
    )
    item = base_item(
        stable_id(item_type, sport, line, previous_line),
        item_type,
        sport,
        catalog.get("generated_at", ""),
    )
    item.update(
        {
            "status": "SETUP REQUIRED" if item_type != "catalog-removal" else "REMOVAL REVIEW REQUIRED",
            "line_role": role,
            "catalog_line": line,
            "previous_catalog_line": previous_line,
            "catalog_approval_state": "PRESENT" if line else "REMOVED — VERIFY",
            "mapped_event": mapped_record,
            "missing_setup": setup_for(role, item_type),
            "evidence": {
                "catalog_label": catalog.get("source_label"),
                "catalog_version": catalog.get("menu_version"),
                "catalog_url": catalog.get("pdf_url"),
            },
        }
    )
    if item_type == "catalog-addition":
        item["title"] = f"New approved catalog {role.replace('-', ' ')}"
        item["recommended_action"] = "Complete the mapping and source setup before the entry can appear in Review Today."
    elif item_type == "catalog-removal":
        item["title"] = f"Catalog {role.replace('-', ' ')} removed"
        item["recommended_action"] = "Confirm the removal and retire any affected mapping or schedule publication."
    else:
        item["title"] = f"Catalog {role.replace('-', ' ')} changed"
        item["recommended_action"] = "Review the wording change and update every affected mapping, source, and restriction rule."
    return item


def pair_changes(added: list[str], removed: list[str]) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    candidates: list[tuple[float, int, int]] = []
    for ai, new in enumerate(added):
        for ri, old in enumerate(removed):
            if line_role(new) != line_role(old):
                continue
            ratio = SequenceMatcher(None, canonical(new), canonical(old)).ratio()
            if ratio >= 0.68:
                candidates.append((ratio, ai, ri))
    used_a: set[int] = set()
    used_r: set[int] = set()
    pairs: list[tuple[str, str]] = []
    for _, ai, ri in sorted(candidates, reverse=True):
        if ai in used_a or ri in used_r:
            continue
        used_a.add(ai)
        used_r.add(ri)
        pairs.append((added[ai], removed[ri]))
    return (
        pairs,
        [value for index, value in enumerate(added) if index not in used_a],
        [value for index, value in enumerate(removed) if index not in used_r],
    )


def build_catalog_changes(catalog: dict[str, Any], season_map: dict[str, Any]) -> list[dict[str, Any]]:
    sections = {section.get("sport"): section for section in catalog.get("sections", [])}
    sports = {sport.get("sport"): sport for sport in season_map.get("sports", [])}
    mapped = mapped_entities(season_map)
    items: list[dict[str, Any]] = []

    ignored_containers = {"NCAA"}
    for sport_name, section in sections.items():
        if sport_name in ignored_containers:
            continue
        mapping = sports.get(sport_name)
        if not mapping:
            item = catalog_item(
                item_type="catalog-addition",
                sport=sport_name,
                line=f"New catalog sport: {sport_name}",
                previous_line=None,
                catalog=catalog,
                mapped=mapped,
            )
            item["status"] = "SPORT MAPPING REQUIRED"
            items.append(item)
            continue

        current = list(section.get("lines") or [])
        snapshot = list(mapping.get("catalog_snapshot_lines") or [])
        if snapshot:
            current_counter = Counter(current)
            snapshot_counter = Counter(snapshot)
            added = list((current_counter - snapshot_counter).elements())
            removed = list((snapshot_counter - current_counter).elements())
        else:
            known = derived_known_lines(mapping, season_map)
            added = [
                line
                for line in current
                if line_role(line) != "hierarchy-section"
                and canonical(line) not in known
                and event_base(line) not in known
            ]
            removed = []

        pairs, added, removed = pair_changes(added, removed)
        for new, old in pairs:
            items.append(
                catalog_item(
                    item_type="catalog-change",
                    sport=sport_name,
                    line=new,
                    previous_line=old,
                    catalog=catalog,
                    mapped=mapped,
                )
            )
        for line in added:
            items.append(
                catalog_item(
                    item_type="catalog-addition",
                    sport=sport_name,
                    line=line,
                    previous_line=None,
                    catalog=catalog,
                    mapped=mapped,
                )
            )
        for line in removed:
            items.append(
                catalog_item(
                    item_type="catalog-removal",
                    sport=sport_name,
                    line=None,
                    previous_line=line,
                    catalog=catalog,
                    mapped=mapped,
                )
            )
    return items


def signature_for(*payloads: Any) -> str:
    packed = json.dumps(payloads, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def build_queue(
    catalog: dict[str, Any],
    season_map: dict[str, Any],
    official_sources: dict[str, Any],
    schedule_sources: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    open_items = build_catalog_changes(catalog, season_map)
    open_items.sort(key=lambda item: (item.get("item_type", ""), item.get("sport", ""), item.get("title", "")))

    input_signature = signature_for(
        catalog.get("sha256"),
        catalog.get("sections"),
        season_map,
        official_sources,
        schedule_sources,
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    if previous and previous.get("input_signature") == input_signature:
        generated_at = previous.get("generated_at") or generated_at

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "input_signature": input_signature,
        "catalog": {
            "source_label": catalog.get("source_label"),
            "menu_version": catalog.get("menu_version"),
            "generated_at": catalog.get("generated_at"),
            "pdf_url": catalog.get("pdf_url"),
        },
        "policy": {
            "mode": "FAIL_CLOSED",
            "rule": "The published catalog controls approval. Queue records may never create Review Today eligibility before explicit mapping.",
            "catalog_authority": "PUBLISHED_CATALOG",
            "mapping_required": True,
        },
        "summary": {
            "open_total": len(open_items),
            "catalog_additions": sum(item["item_type"] == "catalog-addition" for item in open_items),
            "catalog_changes": sum(item["item_type"] == "catalog-change" for item in open_items),
            "catalog_removals": sum(item["item_type"] == "catalog-removal" for item in open_items),
            "blocked_from_review_today": len(open_items),
        },
        "open_items": open_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--season-map", type=Path, default=SEASON_MAP_PATH)
    parser.add_argument("--official-sources", type=Path, default=OFFICIAL_SOURCES_PATH)
    parser.add_argument("--schedule-sources", type=Path, default=SCHEDULE_SOURCES_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    previous = load_json(args.output, default={})
    result = build_queue(
        load_json(args.catalog),
        load_json(args.season_map),
        load_json(args.official_sources, default={}),
        load_json(args.schedule_sources, default={}),
        previous,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
