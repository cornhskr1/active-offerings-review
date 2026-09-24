#!/usr/bin/env python3
"""Resolve combined Tennis approvals by actual competition structure.

Seven catalog lines cover distinct men's and women's competitions. United Cup
is one mixed national-team tournament and must remain one operational identity.
"""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"
MIXED_KEY = "tennis-united-cup"


def normalize(payload):
    tennis = next(sport for sport in payload["sports"] if sport["sport"] == "Tennis")
    for group in tennis["groups"]:
        for event in group["events"]:
            label = event["catalog_event"]
            if not label.endswith(" | Men and Women"):
                continue

            if event["key"] == MIXED_KEY:
                event["identity_model"] = "single-mixed-gender-competition"
                event["identity_basis"] = (
                    "United Cup is one national-team tournament. Each tie combines "
                    "men's singles, women's singles, and mixed doubles toward one team result."
                )
                event["identity_evidence_url"] = (
                    "https://www.unitedcup.com/en/about/overview"
                )
                event.pop("coverage_children", None)
                continue

            if event.get("coverage_children"):
                continue
            base = label.removesuffix(" | Men and Women")
            event["identity_model"] = "combined-approval-separate-competitions"
            event["season_basis"] = (
                "The catalog approval covers separate men's and women's competitions; "
                "division-specific dates and schedule coverage require independent verification."
            )
            event.pop("source_id", None)
            event.pop("source_ids", None)
            event["coverage_children"] = [
                {
                    "key": f"{event['key']}-{division.lower()}",
                    "label": f"{base} | {division}",
                    "season_window": "Division-specific dates pending",
                    "season_basis": "Division-specific calendar verification pending",
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
