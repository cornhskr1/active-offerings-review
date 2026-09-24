#!/usr/bin/env python3
"""Resolve combined Table Tennis approvals by actual competition structure.

WTT has distinct men's and women's competitions. MLTT is one mixed-gender
team league, so splitting it would invent competitions that do not exist.
"""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"


def normalize(payload):
    table_tennis = next(
        sport for sport in payload["sports"] if sport["sport"] == "Table Tennis"
    )
    events = {
        event["key"]: event
        for group in table_tennis["groups"]
        for event in group["events"]
    }

    wtt = events["table-tennis-wtt"]
    if not wtt.get("coverage_children"):
        base = wtt["catalog_event"].removesuffix(" | Men and Women")
        wtt["identity_model"] = "combined-approval-separate-competitions"
        wtt["season_basis"] = (
            "The catalog approval covers separate men's and women's competitions; "
            "division-specific dates and schedule coverage require independent verification."
        )
        wtt.pop("source_id", None)
        wtt.pop("source_ids", None)
        wtt["coverage_children"] = [
            {
                "key": f"{wtt['key']}-{division.lower()}",
                "label": f"{base} | {division}",
                "season_window": "Division-specific dates pending",
                "season_basis": "Division-specific calendar verification pending",
            }
            for division in ("Men", "Women")
        ]

    mltt = events["table-tennis-mltt"]
    mltt["identity_model"] = "single-mixed-gender-competition"
    mltt["identity_basis"] = (
        "MLTT operates one team league and one team-match schedule. Its match format "
        "includes a required women's singles position rather than separate men's and "
        "women's leagues."
    )
    mltt["identity_evidence_url"] = "https://www.mltt.com/about-us"
    mltt.pop("coverage_children", None)
    return payload


if __name__ == "__main__":
    data = normalize(json.loads(PATH.read_text(encoding="utf-8")))
    PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
