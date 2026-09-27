#!/usr/bin/env python3
"""Show actionable Priority 2 cohorts from the complete identity inventory."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit


INVENTORY = Path(__file__).resolve().parents[1] / "data" / "priority2-coverage-inventory.json"
SEASON_EXCEPTIONS = {"NO_WINDOW", "PENDING_DATES", "PARTIAL_WINDOW", "DOCUMENTED_HOLD"}
COVERAGE_EXCEPTIONS = {"NO_LINKED_SOURCE", "SOURCE_SCOPE_REVIEW", "ADAPTER_GAP"}


def cohorts(inventory, sport=None):
    rows = inventory["identities"]
    keys = [row["identity_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate operational identity keys in Priority 2 inventory")
    if len(rows) != inventory["summary"]["catalog_operational_identities"]:
        raise ValueError("Priority 2 inventory total does not match its identity rows")

    grouped = defaultdict(list)
    for row in rows:
        if sport and row["sport"].lower() != sport.lower():
            continue
        for kind, state in (("season", row["season_state"]), ("coverage", row["coverage_state"])):
            if state in (SEASON_EXCEPTIONS if kind == "season" else COVERAGE_EXCEPTIONS):
                grouped[(kind, state, row["sport"])].append(row["identity_key"])
    return [
        {"kind": kind, "state": state, "sport": name, "count": len(identities), "identity_keys": sorted(identities)}
        for (kind, state, name), identities in sorted(grouped.items())
    ]


def source_config():
    data = INVENTORY.parent
    paths = [data / "global-schedule-sources.json", *sorted(data.glob("soccer-*-sources.json"))]
    return {
        (source["sport"], source["id"]): source
        for path in paths
        for source in json.loads(path.read_text(encoding="utf-8"))["sources"]
    }


def provider_cohorts(inventory, configured, sport=None, min_identities=2):
    """Group unresolved source gaps by reference host, keeping each identity once."""
    grouped = defaultdict(dict)
    for row in inventory["identities"]:
        if row["coverage_state"] != "ADAPTER_GAP" or (sport and row["sport"].lower() != sport.lower()):
            continue
        for source in row["sources"]:
            if source["type"] != "coverage-gap":
                continue
            owner = configured.get((row["sport"], source.get("configured_source_id") or source["id"]), {})
            url = owner.get("official_schedule_url") or owner.get("endpoint") or ""
            provider = (urlsplit(url).hostname or "unidentified publisher").removeprefix("www.")
            grouped[(provider, row["sport"])][row["identity_key"]] = {
                "identity_key": row["identity_key"], "league": row["league"],
                "source_id": source["id"], "official_url": url,
            }
    return [
        {"provider": provider, "sport": name, "count": len(rows),
         "identities": sorted(rows.values(), key=lambda row: row["identity_key"])}
        for (provider, name), rows in sorted(grouped.items(),
            key=lambda pair: (-len(pair[1]), pair[0]))
        if len(rows) >= min_identities
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sport", help="Limit the report to one sport")
    parser.add_argument("--json", action="store_true", help="Include identity keys as JSON")
    parser.add_argument("--by-provider", action="store_true", help="Group adapter gaps by reference source host")
    parser.add_argument("--min-identities", type=int, default=2,
                        help="Minimum identities in a provider group (default: 2)")
    args = parser.parse_args()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if args.min_identities < 1:
        parser.error("--min-identities must be positive")
    groups = (provider_cohorts(inventory, source_config(), args.sport, args.min_identities)
              if args.by_provider else cohorts(inventory, args.sport))
    if args.json:
        print(json.dumps(groups, indent=2))
    else:
        if args.by_provider:
            print("Priority 2 adapter gaps by reference host (configured and window-only coverage excluded):")
            for group in groups:
                print(f"{group['count']:3} {group['sport']:20} {group['provider']}")
        else:
            print("Priority 2 exception cohorts (a row may appear in both season and coverage):")
            for group in groups:
                print(f"{group['kind']:8} {group['state']:20} {group['sport']:20} {group['count']:3}")


if __name__ == "__main__":
    main()
