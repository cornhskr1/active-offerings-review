#!/usr/bin/env python3
"""Split the combined NCAA Ice Hockey approval into operational divisions."""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"


def normalize(payload):
    hockey = next(
        sport for sport in payload["sports"] if sport["sport"] == "NCAA Ice Hockey"
    )
    approval = next(
        event
        for group in hockey["groups"]
        for event in group["events"]
        if event["catalog_event"] == "Division I Ice Hockey | Men and Women"
    )
    if approval.get("coverage_children"):
        return payload

    approval["identity_model"] = "combined-approval-separate-competitions"
    approval["season_basis"] = (
        "The catalog approval covers separate NCAA men's and women's ice hockey "
        "competitions. The NCAA formally designates the men's championship Division I "
        "and the women's championship National Collegiate; division-specific schedules "
        "require independent verification."
    )
    approval.pop("source_id", None)
    approval.pop("source_ids", None)
    approval["coverage_children"] = [
        {
            "key": f"{approval['key']}-{division.lower()}",
            "label": f"Division I Ice Hockey | {division}",
            "season_window": "Division-specific dates pending",
            "season_basis": (
                "NCAA Division I men's calendar verification pending"
                if division == "Men"
                else "NCAA National Collegiate women's calendar verification pending"
            ),
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
