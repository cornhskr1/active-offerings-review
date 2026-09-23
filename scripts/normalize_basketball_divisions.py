#!/usr/bin/env python3
"""Split combined basketball approvals into separate operational identities.

The published approval text remains the parent. A child is a competition
identity, not an additional approval or a claim of live schedule coverage.
"""

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "data" / "catalog-season-map.json"
def normalize(payload):
    basketball = next(s for s in payload["sports"] if s["sport"] == "Basketball")
    for group in basketball["groups"]:
        for event in group["events"]:
            label = event["catalog_event"]
            if not label.endswith(" | Men and Women"):
                continue
            if event.get("coverage_children"):
                continue
            base = label.removesuffix(" | Men and Women")
            event["identity_model"] = "combined-approval-separate-competitions"
            event["season_basis"] = (
                "The catalog approval covers separate men's and women's competitions; "
                "division-specific dates and schedule coverage require independent verification."
            )
            children = []
            for division in ("Men", "Women"):
                child = {"key": f"{event['key']}-{division.lower()}",
                         "label": f"{base} | {division}",
                         "season_window": "Division-specific dates pending",
                         "season_basis": "Division-specific calendar verification pending"}
                children.append(child)
            event["coverage_children"] = children
    return payload


if __name__ == "__main__":
    payload = normalize(json.loads(PATH.read_text(encoding="utf-8")))
    PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
