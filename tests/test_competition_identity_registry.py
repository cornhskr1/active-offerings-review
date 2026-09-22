import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_registry_covers_catalog_mappings_and_observed_participants():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_competition_identity_registry.py")], check=True)
    registry = json.loads((ROOT / "data" / "competition-identity-registry.json").read_text(encoding="utf-8"))
    season_map = json.loads((ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8"))

    expected = set()
    for sport in season_map["sports"]:
        for group in sport.get("groups", []):
            for event in group.get("events", []):
                children = event.get("coverage_children") or []
                if children:
                    expected.update((sport["sport"], child["label"]) for child in children)
                elif event.get("catalog_event"):
                    expected.add((sport["sport"], event["catalog_event"]))
    actual = {(item["sport"], item["league"]) for item in registry["competitions"]}
    assert expected <= actual

    nfl = next(item for item in registry["competitions"] if item["sport"] == "Football" and item["league"] == "NFL")
    assert "Buffalo Bills" in nfl["participants"]
    assert "Las Vegas Raiders" in nfl["participants"]
    assert registry["coverage_gaps"]

    assert ("Soccer", "Serie A | Men") in actual
    assert ("Soccer", "Serie A | Women") in actual
    assert ("Soccer", "Serie A | Men and Women") not in actual
