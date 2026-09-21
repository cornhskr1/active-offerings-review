#!/usr/bin/env python3
"""Build the minimal public tennis-risk evidence snapshot consumed by Lane 1."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def clean_aliases(record):
    names = [record.get("name")]
    if isinstance(record.get("aliases"), list):
        names.extend(record["aliases"])
    aliases = {}
    for name in names:
        label = " ".join(str(name or "").split())
        key = norm(label)
        if key:
            aliases[key] = label
    return [aliases[key] for key in sorted(aliases)]


def public_record(record, origin):
    name = " ".join(str(record.get("name") or "").split())
    return {
        "canonical_name": name,
        "aliases": clean_aliases(record),
        "age_status": "VERIFIED U18",
        "age": record.get("age"),
        "source": record.get("source") or "Verified public tennis source",
        "source_url": record.get("source_url") if isinstance(record.get("source_url"), str) else "",
        "evidence": record.get("evidence") or "",
        "last_verified": record.get("last_verified") or "",
        "origin": origin,
        "current_exposure": bool(record.get("current_exposure")),
    }


def merge_record(existing, incoming):
    alias_map = {norm(value): value for value in existing.get("aliases") or []}
    for value in incoming.get("aliases") or []:
        alias_map.setdefault(norm(value), value)
    existing["aliases"] = [alias_map[key] for key in sorted(alias_map) if key]
    for field in ("age", "source", "source_url", "evidence", "last_verified"):
        if not existing.get(field) and incoming.get(field) not in (None, ""):
            existing[field] = incoming[field]
    existing["current_exposure"] = bool(existing.get("current_exposure") or incoming.get("current_exposure"))
    origins = set(str(existing.get("origin") or "").split("+"))
    origins.update(str(incoming.get("origin") or "").split("+"))
    existing["origin"] = "+".join(sorted(value for value in origins if value))


def build_snapshot(registry, age_cache, generated_at=None):
    records = {}
    for record in registry.get("verified_u18") or []:
        key = norm(record.get("name"))
        if key:
            records[key] = public_record(record, "registry")

    cache_records = age_cache.get("records") or {}
    iterable = cache_records.values() if isinstance(cache_records, dict) else cache_records
    for record in iterable:
        if str(record.get("age_status") or "").upper() != "VERIFIED U18":
            continue
        key = norm(record.get("name"))
        if not key:
            continue
        incoming = public_record(record, "age-cache")
        if key in records:
            merge_record(records[key], incoming)
        else:
            records[key] = incoming

    entries = [records[key] for key in sorted(records)]
    alias_owners = {}
    for entry in entries:
        for alias in entry["aliases"]:
            alias_owners.setdefault(norm(alias), set()).add(norm(entry["canonical_name"]))
    ambiguous_aliases = sorted(alias for alias, owners in alias_owners.items() if alias and len(owners) > 1)

    stable = {
        "entries": entries,
        "ambiguous_aliases": ambiguous_aliases,
        "guardrails": {
            "exact_identity_or_unique_verified_alias_required": True,
            "fuzzy_name_matching_allowed": False,
            "report_row_is_participation_evidence": True,
            "absence_never_clears_u18_risk": True,
            "identity_resolution_never_implies_catalog_approval": True,
        },
    }
    snapshot_id = hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "source_generated_at": {
            "registry": registry.get("generated_at") or "",
            "age_cache": age_cache.get("generated_at") or "",
        },
        "summary": {
            "verified_u18_identities": len(entries),
            "ambiguous_aliases_blocked": len(ambiguous_aliases),
        },
        **stable,
    }


def main():
    registry = load(DATA / "tennis-u18-registry.json", {})
    age_cache = load(DATA / "tennis-age-cache.json", {})
    output = build_snapshot(registry, age_cache)
    (DATA / "tennis-risk-snapshot.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"snapshot_id": output["snapshot_id"], **output["summary"]}))


if __name__ == "__main__":
    main()
