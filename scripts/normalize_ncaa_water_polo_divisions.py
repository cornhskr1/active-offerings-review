#!/usr/bin/env python3
"""Split the combined NCAA Division I Water Polo approval by competition."""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"


def normalize(payload):
    sport = next(item for item in payload["sports"] if item["sport"] == "NCAA Water Polo")
    approval = next(
        event
        for group in sport["groups"]
        for event in group["events"]
        if event["catalog_event"] == "Division I Water Polo | Men and Women"
    )
    if approval.get("coverage_children"):
        return payload

    approval["identity_model"] = "combined-approval-separate-competitions"
    approval["season_basis"] = (
        "The catalog's Division I approval covers separate men's and women's "
        "water polo competitions. The NCAA organizes separate National Collegiate "
        "men's and women's championships, rather than Division I-only championships. "
        "The men's and women's seasons differ; child schedule sources and dates "
        "require independent verification."
    )
    approval.pop("source_id", None)
    approval.pop("source_ids", None)
    approval["coverage_children"] = [
        {
            "key": f"{approval['key']}-{division.lower()}",
            "label": f"Division I Water Polo | {division}",
            "season_window": "Division-specific dates pending",
            "season_basis": "Division-specific NCAA calendar verification pending",
        }
        for division in ("Men", "Women")
    ]
    return payload


if __name__ == "__main__":
    data = normalize(json.loads(PATH.read_text(encoding="utf-8")))
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
