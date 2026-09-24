#!/usr/bin/env python3
"""Split combined Rugby approvals into separate operational identities.

The published approval text remains the legal parent. Each child represents
one division-specific competition identity and does not claim schedule
coverage unless that division has independently verified evidence.
"""

import json
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
SEASON_PATH = DATA / "catalog-season-map.json"
ALIAS_PATH = DATA / "competition-alias-crosswalk.json"


def normalize_season(payload):
    rugby = next(s for s in payload["sports"] if s["sport"] == "Rugby")
    for group in rugby["groups"]:
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


def normalize_aliases(payload):
    combined = {
        "SVNS | Men and Women",
        "Six Nations Rugby | Men and Women",
        "Premier Rugby Sevens (PR7s) | Men and Women",
        "Rugby Americas North Championship | Men and Women",
        "Rugby Americas North Sevens | Men and Women",
    }
    held_reasons = {
        "HSBC SVNS": "The name covers separate men's and women's SVNS competitions. Require division evidence before selecting an operational identity.",
        "HSBC SVNS Series": "The series name covers separate men's and women's competitions. Require division evidence before selecting an operational identity.",
        "Six Nations Rugby": "The organizer name covers separate men's and women's championships. Require the specific competition before resolving it.",
        "Premier Rugby Sevens": "PR7s staged paired men's and women's competitions. The umbrella name alone does not identify the division.",
        "PR7s": "The acronym covers paired men's and women's competitions and cannot select a division by itself.",
        "RAN Sevens": "RAN Sevens includes separate men's and women's competitions. Require division evidence before resolving it.",
    }
    retained = []
    moved = []
    for row in payload["reviewed_aliases"]:
        if row.get("sport") == "Rugby" and row.get("catalog_identity") in combined:
            moved.append({
                "sport": "Rugby",
                "catalog_identity": row["catalog_identity"],
                "observed_official_name": row["alias"],
                "reason": held_reasons[row["alias"]],
                "evidence_url": row.get("evidence_url", ""),
            })
        elif row.get("sport") == "Rugby" and row.get("alias") in {
            "Guinness Men’s Six Nations",
            "Guinness Women’s Six Nations",
        }:
            retained.append({key: value for key, value in row.items() if key != "catalog_identity"})
        else:
            retained.append(row)

    six_nations = {
        "Guinness Men’s Six Nations": (
            "rugby-intl-six-nations-men",
        ),
        "Guinness Women’s Six Nations": (
            "rugby-intl-six-nations-women",
        ),
    }
    queue = []
    for row in payload["review_queue"]:
        resolved = six_nations.get(row.get("observed_official_name"))
        if row.get("sport") == "Rugby" and resolved:
            identity_key = resolved[0]
            retained.append({
                "sport": "Rugby",
                "identity_key": identity_key,
                "alias": row["observed_official_name"],
                "name_type": "official",
                "evidence_url": row.get("evidence_url", ""),
            })
        else:
            queue.append(row)

    existing = {
        (row.get("sport"), row.get("catalog_identity"), row.get("observed_official_name"))
        for row in queue
    }
    queue.extend(
        row for row in moved
        if (row["sport"], row["catalog_identity"], row["observed_official_name"])
        not in existing
    )
    payload["reviewed_aliases"] = retained
    payload["review_queue"] = queue
    return payload


if __name__ == "__main__":
    season = normalize_season(
        json.loads(SEASON_PATH.read_text(encoding="utf-8"))
    )
    aliases = normalize_aliases(
        json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    )
    SEASON_PATH.write_text(
        json.dumps(season, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ALIAS_PATH.write_text(
        json.dumps(aliases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
