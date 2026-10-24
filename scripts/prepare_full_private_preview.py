"""Protected, inactive complete-snapshot structural gate. NOT production approval.

32 exact outputs from 17 collector families are verified together. The private
bundle cannot supply a validator, contract, executable or allowlist. Per-family
semantic/freshness review remains required and is exposed in the receipt.
"""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import tempfile

from scripts.prepare_private_pilot_preview import _regular, _revision, _strict_json
from scripts.build_public_reference_snapshot import build_reference_snapshot
from scripts.snapshot_semantic_guards import validate_change
from scripts.public_data_snapshot import read_public_snapshot,build_public_snapshot
from scripts.protected_football_config import validate_football_config

CONTRACT = Path(__file__).resolve().parents[1] / 'contracts/private-snapshot-files.json'


def _contract():
    spec = _strict_json(_regular(CONTRACT))
    if (type(spec.get('schema_version')) is not int or spec['schema_version'] != 1
            or spec.get('production_enabled') is not False
            or spec.get('contract_review') != 'transport_reviewed_inactive_runtime_acceptance_pending'):
        raise ValueError('unreviewed inactive application contract')
    _revision(spec.get('app_commit'), spec.get('app_commit'))
    outputs=spec.get('outputs')
    if not isinstance(outputs,dict) or not outputs:
        raise ValueError('missing trusted output inventory')
    for name,rule in outputs.items():
        path=Path(name)
        if (path.is_absolute() or '..' in path.parts or path.as_posix()!=name
                or not isinstance(rule,dict) or type(rule.get('public')) is not bool
                or (rule['public'] and (not name.startswith('data/') or path.suffix not in ('.json','.pdf')))):
            raise ValueError('unsafe trusted output contract')
    return spec


def read_full_snapshot(candidate: Path):
    """Capture verified bytes using only the checked-in app-owned contract."""
    spec=_contract()
    if any(p.is_symlink() for p in (candidate,*candidate.parents)):
        raise ValueError('linked snapshot root')
    manifest_raw=_regular(candidate/'manifest.json')
    manifest=_strict_json(manifest_raw)
    if (set(manifest)!={'schema_version','contract','app_commit','files','configuration'}
            or type(manifest['schema_version']) is not int or manifest['schema_version']!=2
            or manifest['contract']!='complete-collector-snapshot/v1'
            or manifest['app_commit']!=spec['app_commit']
            or not isinstance(manifest['files'],dict)
            or set(manifest['files'])!=set(spec['outputs'])):
        raise ValueError('incomplete or unreviewed snapshot identity')
    configuration=manifest['configuration']
    if (not isinstance(configuration,dict) or set(configuration)!={'target_app_commit','families'}
            or not isinstance(configuration.get('families'),dict)
            or set(configuration['families'])!=set(spec['family_outputs'])):
        raise ValueError('incomplete family configuration metadata')
    _revision(configuration['target_app_commit'],configuration['target_app_commit'])
    for family,state in configuration['families'].items():
        if not isinstance(state,dict) or set(state)!={'applied_app_commit','pending_configuration'}:
            raise ValueError('unknown family configuration fields')
        applied=state['applied_app_commit']
        if applied is not None:_revision(applied,applied)
        if (type(state['pending_configuration']) is not bool
                or state['pending_configuration'] != (applied!=configuration['target_app_commit'])):
            raise ValueError('misreported pending configuration')
    paths=list(candidate.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('linked snapshot entry')
    if {p.relative_to(candidate).as_posix() for p in paths if not p.is_dir()} != set(spec['outputs'])|{'manifest.json'}:
        raise ValueError('extra or missing snapshot file')
    captured={}
    for name,rule in spec['outputs'].items():
        raw=_regular(candidate/name,rule['max_bytes'])
        if not raw or len(raw)>rule['max_bytes'] or hashlib.sha256(raw).hexdigest()!=manifest['files'][name]:
            raise ValueError('snapshot size or integrity mismatch: '+name)
        kind=rule['root_type']
        if kind=='pdf':
            if not raw.startswith(b'%PDF-'):raise ValueError('PDF signature missing')
        elif kind=='text':raw.decode('utf-8')
        elif kind=='dict':
            obj=_strict_json(raw)
            if rule.get('schema_version') is not None and obj.get('schema_version')!=rule['schema_version']:
                raise ValueError('unexpected schema version: '+name)
            for key,expected in rule['required_types'].items():
                if key not in obj or type(obj[key]).__name__!=expected:
                    raise ValueError('snapshot field shape mismatch: '+name+':'+key)
        else:raise ValueError('unsupported protected root contract')
        captured[name]=raw
        if sum(len(value) for value in captured.values())>256_000_000:
            raise ValueError('aggregate snapshot size exceeds protected bound')
    return captured,manifest,spec,hashlib.sha256(manifest_raw).hexdigest()


def prepare_full_preview(site: Path,candidate: Path,preview: Path,*,
                         expected_data_commit: str,fetched_data_commit: str,
                         expected_app_commit: str,staged_app_commit: str,previous_publication: Path,
                         expected_previous_snapshot_sha256: str,trusted_publication_run_id: int,now=None):
    """Create new isolated preview; never deploy, execute data, or replace last-good.

    Commit strings must be established independently by a trusted fetch/checkout
    caller. The manifest's applied app revision may lag the current staged target;
    that pending state is reported, never silently called current. The current
    contract represents an inventoried baseline, not accepted live semantics.
    """
    _revision(expected_data_commit,fetched_data_commit)
    _revision(expected_app_commit,staged_app_commit)
    for root in (site,candidate,previous_publication,preview.parent):
        if any(p.is_symlink() for p in (root,*root.parents)):
            raise ValueError('linked preview input or parent')
    site=site.resolve(strict=True);candidate=candidate.resolve(strict=True)
    previous_publication=previous_publication.resolve(strict=True)
    preview=preview.parent.resolve(strict=True)/preview.name
    if preview.exists() or preview.is_symlink() or preview.is_relative_to(site) or preview.is_relative_to(candidate) or preview.is_relative_to(previous_publication):
        raise ValueError('new isolated destination required')
    if not (site/'index.html').is_file():raise ValueError('missing trusted staged site')
    for path in site.rglob('*'):
        if path.is_symlink() or not (path.is_dir() or stat.S_ISREG(path.stat().st_mode)):
            raise ValueError('unsafe trusted stage')
    captured,manifest,spec,digest=read_full_snapshot(candidate)
    public={name:raw for name,raw in captured.items() if spec['outputs'][name]['public']}
    previous_bytes,previous_manifest=read_public_snapshot(previous_publication,expected_digest=expected_previous_snapshot_sha256)
    for name,raw in public.items():
        rule=spec['outputs'][name]
        if rule['root_type']=='dict':
            previous=_strict_json(previous_bytes[name])
            validate_change(previous,_strict_json(raw),now=now)
            if name=='data/ncaa-football-sources.json':
                validate_football_config(_strict_json(_regular(site/name,rule['max_bytes'])),_strict_json(raw))
    temp=Path(tempfile.mkdtemp(prefix='.full-private-preview-',dir=preview.parent))
    try:
        shutil.copytree(site,temp,dirs_exist_ok=True)
        for name,raw in public.items():
            path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        reference=build_reference_snapshot(temp,app_commit=staged_app_commit,data_commit=fetched_data_commit)
        publication=build_public_snapshot(temp,app_commit=staged_app_commit,data_commit=fetched_data_commit,
            data_contract_app_commit=manifest['app_commit'],configuration_state=manifest['configuration'],publisher_run_id=trusted_publication_run_id)
        if preview.exists() or preview.is_symlink():raise ValueError('destination appeared; refuse replacement')
        temp.rename(preview)
    finally:
        if temp.exists():shutil.rmtree(temp)
    return {'contract':'complete-collector-snapshot/v1','production_enabled':False,
            'data_commit':fetched_data_commit,'contract_app_commit':manifest['app_commit'],
            'target_app_commit':staged_app_commit,
            'contract_revision_pending':manifest['app_commit']!=staged_app_commit,
            'applied_configuration_verified':False,
            'pending_configuration':any(state['applied_app_commit']!=staged_app_commit for state in manifest['configuration']['families'].values()),
            'pending_family_configuration':sorted(family for family,state in manifest['configuration']['families'].items()
                                                  if state['applied_app_commit']!=staged_app_commit),
            'family_configuration':manifest['configuration']['families'],
            'manifest_sha256':digest,'public_files':sorted(public),'public_reference_snapshot':reference,
            'public_data_snapshot':publication,'previous_publication_snapshot':expected_previous_snapshot_sha256,
            'semantic_review_required':sorted(name for name,rule in spec['outputs'].items()
                                             if rule['semantic_review']=='required'),
            'validation_scope':'typed transport and protected prior-publication invariants; original collector semantics retained'}
