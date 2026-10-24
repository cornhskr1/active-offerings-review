"""Protected complete-publication cache format for dormant Pages integration.

The expected manifest digest must come from independently verified successful
publication artifact evidence, never from an untrusted private candidate.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from scripts.prepare_private_pilot_preview import _regular,_revision,_strict_json
from scripts.build_public_reference_snapshot import canonical

CONTRACT=Path(__file__).resolve().parents[1]/'contracts/private-snapshot-files.json'
POINTER='data/public-data-current.json'
SNAPSHOT_ROOT='data/complete-snapshots'


def public_contract():
    spec=_strict_json(_regular(CONTRACT))
    return spec,{name:rule for name,rule in spec['outputs'].items() if rule['public']}


def configuration(value,families):
    if (not isinstance(value,dict) or set(value)!={'target_app_commit','families'}
            or not isinstance(value['families'],dict) or set(value['families'])!=set(families)):
        raise ValueError('incomplete public configuration provenance')
    _revision(value['target_app_commit'],value['target_app_commit'])
    for item in value['families'].values():
        if not isinstance(item,dict) or set(item)!={'applied_app_commit','pending_configuration'}:
            raise ValueError('unknown public family provenance')
        applied=item['applied_app_commit']
        if applied is not None:_revision(applied,applied)
        if type(item['pending_configuration']) is not bool or item['pending_configuration']!=(applied!=value['target_app_commit']):
            raise ValueError('inconsistent pending configuration')


def read_public_snapshot(root: Path,*,expected_digest: str):
    if not isinstance(expected_digest,str) or re.fullmatch('[0-9a-f]{64}',expected_digest) is None:
        raise ValueError('trusted publication digest required')
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('linked prior publication')
    spec,public=public_contract()
    manifest_raw=_regular(root/'manifest.json')
    if hashlib.sha256(manifest_raw).hexdigest()!=expected_digest:raise ValueError('prior publication manifest digest mismatch')
    manifest=_strict_json(manifest_raw)
    if (set(manifest)!={'schema_version','contract','app_commit','data_commit','data_contract_app_commit','configuration','files','publisher_run_id'}
            or type(manifest['schema_version']) is not int or manifest['schema_version']!=1
            or manifest['contract']!='public-data-snapshot/v1'
            or manifest['data_contract_app_commit']!=spec['app_commit']
            or not isinstance(manifest['files'],dict) or set(manifest['files'])!=set(public)):
        raise ValueError('incompatible prior complete-publication manifest')
    if type(manifest['publisher_run_id']) is not int or manifest['publisher_run_id']<=0:
        raise ValueError('verified publisher run identity required')
    for key in ('app_commit','data_commit'):_revision(manifest[key],manifest[key])
    configuration(manifest['configuration'],spec['family_outputs'])
    paths=list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):raise ValueError('linked prior publication file')
    if {p.relative_to(root).as_posix() for p in paths if not p.is_dir()}!=set(public)|{'manifest.json'}:
        raise ValueError('incomplete prior publication cache')
    captured={}
    for name,rule in public.items():
        raw=_regular(root/name,rule['max_bytes'])
        if hashlib.sha256(raw).hexdigest()!=manifest['files'][name]:raise ValueError('prior publication file mismatch')
        captured[name]=raw
        if sum(map(len,captured.values()))>256_000_000:raise ValueError('prior publication exceeds aggregate bound')
    return captured,manifest


def build_public_snapshot(stage: Path,*,app_commit: str,data_commit: str,data_contract_app_commit: str,configuration_state: dict,publisher_run_id: int):
    """Caller owns an unpublished single-writer stage; never changes live state."""
    if type(publisher_run_id) is not int or publisher_run_id<=0:raise ValueError('positive trusted publisher run ID required')
    for value in (app_commit,data_commit,data_contract_app_commit):_revision(value,value)
    spec,public=public_contract()
    if data_contract_app_commit!=spec['app_commit']:raise ValueError('unreviewed data contract revision')
    configuration(configuration_state,spec['family_outputs'])
    captured={name:_regular(stage/name,rule['max_bytes']) for name,rule in public.items()}
    if sum(map(len,captured.values()))>256_000_000:raise ValueError('public snapshot exceeds aggregate bound')
    manifest={'schema_version':1,'contract':'public-data-snapshot/v1','app_commit':app_commit,'data_commit':data_commit,
              'data_contract_app_commit':data_contract_app_commit,'configuration':configuration_state,'publisher_run_id':publisher_run_id,
              'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in captured.items()}}
    raw_manifest=canonical(manifest);digest=hashlib.sha256(raw_manifest).hexdigest()
    root=stage/SNAPSHOT_ROOT
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('linked public snapshot destination')
    root.mkdir(parents=True,exist_ok=True);target=root/digest
    if target.exists() or target.is_symlink():
        actual,_=read_public_snapshot(target,expected_digest=digest)
        if actual!=captured:raise ValueError('immutable public snapshot changed')
    else:
        temporary=Path(tempfile.mkdtemp(prefix='.complete-publication-',dir=root))
        try:
            for name,raw in captured.items():
                path=temporary/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            (temporary/'manifest.json').write_bytes(raw_manifest)
            read_public_snapshot(temporary,expected_digest=digest)
            if target.exists() or target.is_symlink():raise ValueError('public snapshot destination appeared')
            temporary.rename(target)
        finally:
            if temporary.exists():shutil.rmtree(temporary)
    pointer=stage/POINTER
    if pointer.is_symlink():raise ValueError('linked public-data pointer')
    pointer.write_bytes(canonical({'schema_version':1,'contract':'public-data-pointer/v1','snapshot_sha256':digest}))
    return {'snapshot_sha256':digest,'pointer':POINTER,'manifest':f'{SNAPSHOT_ROOT}/{digest}/manifest.json','files':sorted(public)}
