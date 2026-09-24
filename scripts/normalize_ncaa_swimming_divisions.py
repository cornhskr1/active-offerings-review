#!/usr/bin/env python3
"""Split the combined NCAA Division I Swimming approval into operational divisions."""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"


def normalize(payload):
    swimming = next(
        sport for sport in payload["sports"] if sport["sport"] == "NCAA Swimming"
    )
    approval = next(
        event
        for group in swimming["groups"]
        for event in group["events"]
        if event["catalog_event"] == "Division I Swimming | Men and Women"
    )
    if approval.get("coverage_children"):
        return payload

    approval["identity_model"] = "combined-approval-separate-competitions"
    approval["season_basis"] = (
        "The catalog approval covers separate NCAA Division I men's and women's "
        "swimming competitions. The NCAA organizes swimming and diving championships "
        "with separate men's and women's dates; this catalog approval names swimming "
        "only. Division-specific schedule coverage requires independent verification."
    )
    approval.pop("source_id", None)
    approval.pop("source_ids", None)
    approval["coverage_children"] = [
        {
            "key": f"{approval['key']}-{division.lower()}",
            "label": f"Division I Swimming | {division}",
            "season_window": "Division-specific dates pending",
            "season_basis": "Division-specific NCAA calendar verification pending",
        }
        for division in ("Men", "Women")
    ]
    return payload


if __name__ == "__main__":
    data = normalize(json.loads(PATH.read_text(encoding="utf-8")))
    PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
