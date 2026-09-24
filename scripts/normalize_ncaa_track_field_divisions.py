#!/usr/bin/env python3
"""Split NCAA Division I indoor and outdoor track and field approvals."""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"
EVENTS = (
    "Division I Indoor Track and Field | Men and Women",
    "Division I Outdoor Track and Field | Men and Women",
)


def normalize(payload):
    sport = next(item for item in payload["sports"] if item["sport"] == "NCAA Track and Field")
    approvals = {
        event["catalog_event"]: event
        for group in sport["groups"]
        for event in group["events"]
    }
    for name in EVENTS:
        approval = approvals[name]
        if approval.get("coverage_children"):
            continue
        approval["identity_model"] = "combined-approval-separate-competitions"
        approval["season_basis"] = (
            "The catalog approval covers separate NCAA Division I men's and women's "
            "track and field competitions. Indoor and outdoor are distinct championships. "
            "Division-specific schedule coverage requires independent verification."
        )
        approval.pop("source_id", None)
        approval.pop("source_ids", None)
        prefix = name.split(" | ")[0]
        approval["coverage_children"] = [
            {
                "key": f"{approval['key']}-{division.lower()}",
                "label": f"{prefix} | {division}",
                "season_window": "Division-specific dates pending",
                "season_basis": "Division-specific NCAA calendar verification pending",
            }
            for division in ("Men", "Women")
        ]
    return payload


if __name__ == "__main__":
    data = normalize(json.loads(PATH.read_text(encoding="utf-8")))
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
