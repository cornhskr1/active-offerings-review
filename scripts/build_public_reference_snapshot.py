"""Build immutable seven-file Portal references in an OFFLINE staged preview.

No network, credentials, workflow activation or production publication. Static
known-u18/catalog-season-map remain protected app-owned inputs. The caller must
already have validated any migrated generated-data overlays.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from scripts.prepare_private_pilot_preview import _regular, _revision

REFERENCE_FILES=(
    'data/catalog-live.json',
    'data/catalog-season-map.json',
    'data/competition-identity-registry.json',
    'data/known-u18.json',
    'data/nebraska-collegiate-live.json',
    'data/tennis-age-cache.json',
    'data/tennis-u18-registry.json',
)
POINTER='data/public-reference-current.json'
SNAPSHOT_ROOT='data/reference-snapshots'


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def build_reference_snapshot(stage: Path,*,app_commit: str,data_commit: str):
    """Write only to a caller-owned unpublished stage; return immutable selector.

    stage must be single-writer and isolated. Both provenance revisions must have
    been independently established by the trusted caller; their format is checked
    here, not authenticated. Retained reference bytes/timestamps are unchanged.
    """
    _revision(app_commit,app_commit);_revision(data_commit,data_commit)
    if any(p.is_symlink() for p in (stage,*stage.parents)):
        raise ValueError('linked staged root')
    stage=stage.resolve(strict=True)
    captured={name:_regular(stage/name) for name in REFERENCE_FILES}
    manifest={'schema_version':1,'contract':'public-reference-snapshot/v1',
              'app_commit':app_commit,'data_commit':data_commit,
              'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in captured.items()}}
    raw_manifest=canonical(manifest)
    digest=hashlib.sha256(raw_manifest).hexdigest()
    root=stage/SNAPSHOT_ROOT
    if any(p.is_symlink() for p in (root,*root.parents)):
        raise ValueError('linked snapshot path')
    root.mkdir(parents=True,exist_ok=True)
    target=root/digest
    expected={**captured,'manifest.json':raw_manifest}
    if target.exists() or target.is_symlink():
        # Content-addressed directories are immutable, not overwritten/repaired.
        if target.is_symlink() or not target.is_dir():raise ValueError('invalid existing snapshot')
        paths=list(target.rglob('*'))
        if any(p.is_symlink() for p in paths):raise ValueError('linked retained snapshot')
        if {p.relative_to(target).as_posix() for p in paths if not p.is_dir()}!=set(expected):
            raise ValueError('incomplete retained snapshot')
        if any(_regular(target/name)!=raw for name,raw in expected.items()):
            raise ValueError('retained snapshot integrity mismatch')
    else:
        temp=Path(tempfile.mkdtemp(prefix='.reference-snapshot-',dir=root))
        try:
            for name,raw in expected.items():
                path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            if target.exists() or target.is_symlink():raise ValueError('snapshot destination appeared')
            temp.rename(target)
        finally:
            if temp.exists():shutil.rmtree(temp)
    pointer=stage/POINTER
    if pointer.is_symlink():raise ValueError('linked current snapshot pointer')
    payload=canonical({'schema_version':1,'contract':'public-reference-pointer/v1','snapshot_sha256':digest})
    # The whole containing preview is unpublished until its final atomic rename.
    pointer.write_bytes(payload)
    return {'snapshot_sha256':digest,'pointer':POINTER,
            'manifest':f'{SNAPSHOT_ROOT}/{digest}/manifest.json','files':list(REFERENCE_FILES)}
