#!/usr/bin/env python3
"""Split the combined NCAA Division I Soccer approval into operational divisions."""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"


def normalize(payload):
    soccer = next(
        sport for sport in payload["sports"] if sport["sport"] == "NCAA Soccer"
    )
    approval = next(
        event
        for group in soccer["groups"]
        for event in group["events"]
        if event["catalog_event"] == "Division I Soccer | Men and Women"
    )
    if approval.get("coverage_children"):
        return payload

    approval["identity_model"] = "combined-approval-separate-competitions"
    approval["season_basis"] = (
        "The catalog approval covers separate NCAA Division I men's and women's "
        "soccer competitions; division-specific dates and schedule coverage require "
        "independent verification."
    )
    approval.pop("source_id", None)
    approval.pop("source_ids", None)
    approval["coverage_children"] = [
        {
            "key": f"{approval['key']}-{division.lower()}",
            "label": f"Division I Soccer | {division}",
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
