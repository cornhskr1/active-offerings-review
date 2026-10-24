"""Inactive protected-app pilot acceptance gate; offline and no deployment.

The caller must supply identities independently established by trusted checkout
and authenticated immutable fetch. Equality checks below bind those identities,
not authenticate caller-provided claims. No data-repository code is executed.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import tempfile

from scripts.pilot_data_contract import validate

FILES = ('data/status.json', 'data/review-data.json')
MAX_BYTES = 5_000_000


def _strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON')
    obj = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(obj, dict):
        raise ValueError('object required')
    return obj


def _regular(path, limit=MAX_BYTES):
    if type(limit) is not int or not 1 <= limit <= 32_000_000:
        raise ValueError("invalid protected file bound")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('linked input or parent')
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('regular file required')
    if path.stat().st_size > limit:
        raise ValueError('oversized input')
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError('oversized input')
    return raw


def _candidate(root):
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('linked candidate root')
    paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('linked candidate entry')
    inventory = {p.relative_to(root).as_posix() for p in paths if not p.is_dir()}
    if inventory != set(FILES) | {'manifest.json'}:
        raise ValueError('unexpected or missing candidate files')
    manifest_raw = _regular(root / 'manifest.json')
    manifest = _strict_json(manifest_raw)
    if (set(manifest) != {'schema_version', 'files'}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or not isinstance(manifest['files'], dict) or set(manifest['files']) != set(FILES)):
        raise ValueError('unsupported pilot manifest')
    captured = {}
    for name in FILES:
        raw = _regular(root / name)
        digest = hashlib.sha256(raw).hexdigest()
        if manifest['files'][name] != digest:
            raise ValueError('candidate integrity mismatch')
        captured[name] = raw
    # Retain exact validated bytes; never recopy possibly changed inputs later.
    return captured, hashlib.sha256(manifest_raw).hexdigest()


def _revision(expected, actual):
    if (not isinstance(expected, str) or re.fullmatch('[0-9a-f]{40}', expected) is None
            or actual != expected):
        raise ValueError('immutable source identity mismatch')


def prepare_preview(site: Path, candidate: Path, preview: Path, *, now: datetime,
                    max_age_seconds: int, expected_data_commit: str,
                    fetched_data_commit: str, expected_app_commit: str,
                    staged_app_commit: str):
    """Validate a candidate and atomically create a new isolated preview.

    Existing preview/production/retained directories are never replaced. A
    failed candidate does not advance a deployment pointer or relabel old data.
    This function has no network, token, workflow, or production-switch path.
    """
    _revision(expected_data_commit, fetched_data_commit)
    _revision(expected_app_commit, staged_app_commit)
    for root in (site, candidate, preview.parent):
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError('linked root or parent')
    site = site.resolve(strict=True)
    candidate = candidate.resolve(strict=True)
    preview = preview.parent.resolve(strict=True) / preview.name
    if preview.exists() or preview.is_symlink():
        raise ValueError('preview must be new; retain last known good')
    if preview.is_relative_to(site) or preview.is_relative_to(candidate):
        raise ValueError('preview must be outside inputs')
    if not (site / 'index.html').is_file():
        raise ValueError('trusted staged site missing')
    for path in site.rglob('*'):
        if path.is_symlink() or not (path.is_dir() or stat.S_ISREG(path.stat().st_mode)):
            raise ValueError('unsafe trusted stage entry')
    captured, manifest_hash = _candidate(candidate)
    status, review = [_strict_json(captured[name]) for name in FILES]
    prior_status, prior_review = [_strict_json(_regular(site / name)) for name in FILES]
    validate(status, review, prior_status, prior_review, now=now, max_age_seconds=max_age_seconds)
    temporary = Path(tempfile.mkdtemp(prefix='.private-preview-', dir=preview.parent))
    try:
        shutil.copytree(site, temporary, dirs_exist_ok=True)
        for name, raw in captured.items():
            (temporary / name).write_bytes(raw)
        if preview.exists() or preview.is_symlink():
            raise ValueError('preview destination appeared; refuse replacement')
        temporary.rename(preview)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {'contract': 'public-source-status/v1',
            'app_source_commit': staged_app_commit, 'data_commit': fetched_data_commit,
            'manifest_sha256': manifest_hash, 'production_enabled': False,
            'files': list(FILES)}
