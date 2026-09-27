#!/usr/bin/env python3
"""Show actionable Priority 2 cohorts from the complete identity inventory."""

import argparse
import json
from collections import defaultdict
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sport", help="Limit the report to one sport")
    parser.add_argument("--json", action="store_true", help="Include identity keys as JSON")
    args = parser.parse_args()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    groups = cohorts(inventory, args.sport)
    if args.json:
        print(json.dumps(groups, indent=2))
    else:
        print("Priority 2 exception cohorts (a row may appear in both season and coverage):")
        for group in groups:
            print(f"{group['kind']:8} {group['state']:20} {group['sport']:20} {group['count']:3}")


if __name__ == "__main__":
    main()
