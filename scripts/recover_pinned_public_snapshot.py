"""One reviewed recovery from a successful Pages publication whose artifact expired.

The manifest digest is pinned from authenticated successful-job logs. All public
files and held provider-control bytes are pinned; there is no latest-data fallback.
The caller MUST skip provider collection after this recovery.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import shutil
import urllib.request
from scripts.prepare_private_pilot_preview import _strict_json
from scripts.public_data_snapshot import public_contract, read_public_snapshot, POINTER, SNAPSHOT_ROOT

ORIGIN = 'https://cornhskr1.github.io/active-offerings-review/'
REPO = 'cornhskr1/active-offerings-review'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Recovery redirect rejected')

def public_getter(path, limit):
    if path.startswith('/') or '..' in Path(path).parts or any(c in path for c in ('\\', '?', '#', ':')):
        raise ValueError('Unapproved recovery path')
    with urllib.request.build_opener(NoRedirect()).open(ORIGIN + path, timeout=20) as response:
        raw = response.read(limit + 1)
    if not 0 < len(raw) <= limit:
        raise ValueError('Recovery response bound exceeded')
    return raw

def restore_pinned_public(run, output, checkpoint, get=public_getter):
    from scripts.restore_public_snapshot import _odds
    keys={'schema_version','repository','origin','anchor_run_id','anchor_head_sha',
          'snapshot_sha256','odds_sha256','odds_observed_at','skip_provider_collection'}
    if (not isinstance(checkpoint,dict) or set(checkpoint)!=keys
            or checkpoint['schema_version']!=1 or checkpoint['repository']!=REPO
            or checkpoint['origin']!=ORIGIN or checkpoint['skip_provider_collection'] is not True
            or type(checkpoint['anchor_run_id']) is not int
            or checkpoint['anchor_run_id']!=run.get('id')
            or checkpoint['anchor_head_sha']!=run.get('head_sha')
            or any(not isinstance(checkpoint[k],str) or not re.fullmatch('[0-9a-f]{64}',checkpoint[k])
                   for k in ('snapshot_sha256','odds_sha256'))):
        raise ValueError('Exact reviewed public recovery checkpoint required')
    digest=checkpoint['snapshot_sha256']
    def pointer():
        raw=get(POINTER,10000)
        p=_strict_json(raw)
        if p!={'schema_version':1,'contract':'public-data-pointer/v1','snapshot_sha256':digest}:
            raise ValueError('Current publication does not match reviewed successful anchor')
        return raw
    first=pointer()
    prefix=SNAPSHOT_ROOT+'/'+digest+'/'
    manifest=get(prefix+'manifest.json',1_000_000)
    if hashlib.sha256(manifest).hexdigest()!=digest:
        raise ValueError('Recovery manifest hash mismatch')
    _,public=public_contract()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('Fresh recovery output required')
    temporary=Path(tempfile.mkdtemp(prefix='.pinned-public-recovery-',dir=output.parent))
    try:
        (temporary/'manifest.json').write_bytes(manifest)
        total=0
        for name,rule in public.items():
            raw=get(prefix+name,rule['max_bytes']);total+=len(raw)
            if total>256_000_000:raise ValueError('Recovery aggregate bound exceeded')
            path=temporary/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        _,verified=read_public_snapshot(temporary,expected_digest=digest)
        if verified['publisher_run_id']!=run['id'] or verified['app_commit']!=run['head_sha']:
            raise ValueError('Recovery publisher provenance mismatch')
        odds=get('data/odds-api-events.json',5_000_000)
        if hashlib.sha256(odds).hexdigest()!=checkpoint['odds_sha256']:
            raise ValueError('Recovery provider-control hash mismatch')
        parsed=json.loads(_odds(odds))
        if parsed['collector_state'].get('halted') is not True or parsed['observed_at']!=checkpoint['odds_observed_at']:
            raise ValueError('Recovery must preserve reviewed held provider state')
        if pointer()!=first:raise ValueError('Publication changed during recovery')
        temporary.rename(output)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return {'anchor_run_id':run['id'],'snapshot_sha256':digest,'pinned_public_recovery':True},odds
