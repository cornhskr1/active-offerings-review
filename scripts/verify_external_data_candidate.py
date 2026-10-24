"""Offline-only gate for verified, data-only deployment candidates.

A future trusted fetcher supplies a directory; this module never handles secrets,
downloads from networks, or activates a production data switch.
"""
import hashlib
import json
from pathlib import Path

APPROVED = frozenset({"data/status.json", "data/review-data.json"})
MAX_BYTES = 5_000_000

def verify_candidate(root: Path) -> list[str]:
    root = root.resolve(strict=True)
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("missing or symlinked manifest")
    manifest = json.loads(manifest_path.read_bytes())
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "files"} or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("bad manifest")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != APPROVED:
        raise ValueError("incomplete or unexpected file list")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if not p.is_dir()}
    if actual != APPROVED | {"manifest.json"}:
        raise ValueError("extra or missing files")
    for name in sorted(APPROVED):
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("unsafe data file")
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("oversized data file")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != files[name]:
            raise ValueError("integrity mismatch")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("invalid JSON root")
        required = {"generated_at", "sources"} if name == "data/status.json" else {"generated_at", "schema_version", "events"}
        if not required.issubset(payload):
            raise ValueError("missing required schema fields")
    return sorted(APPROVED)
