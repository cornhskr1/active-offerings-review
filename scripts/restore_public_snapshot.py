"""Dormant Pages stage adapter: restore proven prior state, validate private data.

Only a successful run independently proved by the existing publication guard may
supply prior public/odds state. No data repository code executes. No provider API
is called here. The existing zero-quota collector remains a separate later step.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from scripts.check_odds_deploy_safety import successful_publication
from scripts.public_data_snapshot import public_contract,read_public_snapshot,POINTER,SNAPSHOT_ROOT
from scripts.build_public_reference_snapshot import canonical
from scripts.prepare_private_pilot_preview import _strict_json

REPO='cornhskr1/active-offerings-review'
MAX_ZIP=256_000_000
MAX_TAR=768_000_000
ODDS='data/odds-api-events.json'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def transports(token):
    if not isinstance(token,str) or not token:raise ValueError('Read-only workflow evidence token required')
    opener=urllib.request.build_opener(NoRedirect())
    def request(path):
        if not path.startswith('/actions/') or any(x in path for x in ('..','://','#','\\')):
            raise ValueError('Unapproved evidence endpoint')
        return urllib.request.Request('https://api.github.com/repos/'+REPO+path,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    def read(response,limit):
        with response:raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Evidence response exceeds bound')
        return raw
    def get(path):return json.loads(read(opener.open(request(path),timeout=30),4_000_000))
    def archive(artifact_id):
        if type(artifact_id) is not int or artifact_id<=0:raise ValueError('Artifact ID required')
        try:return read(opener.open(request('/actions/artifacts/'+str(artifact_id)+'/zip'),timeout=30),MAX_ZIP)
        except urllib.error.HTTPError as exc:
            if exc.code!=302:raise
            location=exc.headers.get('Location','');exc.close()
        url=urllib.parse.urlsplit(location);host=url.hostname or ''
        if (url.scheme!='https' or url.username or url.password or url.port not in (None,443) or url.fragment
            or not (host.endswith('.blob.core.windows.net') or host.endswith('.actions.githubusercontent.com'))):
            raise ValueError('Unapproved signed artifact location')
        # Deliberately fresh request with NO GitHub Authorization header.
        return read(opener.open(urllib.request.Request(location),timeout=30),MAX_ZIP)
    return get,archive

def _proof(proof,run_id):
    if (not isinstance(proof,dict) or set(proof)!={'repository','current_run_id','anchor_run_id'}
        or proof['repository']!=REPO or type(run_id) is not int or run_id<=0
        or type(proof['current_run_id']) is not int or proof['current_run_id']!=run_id
        or type(proof['anchor_run_id']) is not int or proof['anchor_run_id']<=0):
        raise ValueError('Prior successful publication proof required')
    return proof['anchor_run_id']

def _checkpoint(checkpoint,anchor,metadata):
    return (isinstance(checkpoint,dict) and checkpoint.get('repository')==REPO
            and type(checkpoint.get('anchor_run_id')) is int and checkpoint['anchor_run_id']==anchor
            and type(checkpoint.get('artifact_id')) is int and checkpoint['artifact_id']==metadata['id']
            and checkpoint.get('artifact_sha256')==metadata['digest'].removeprefix('sha256:'))

def _archive_files(raw,expected_digest):
    if not isinstance(raw,bytes) or len(raw)>MAX_ZIP or hashlib.sha256(raw).hexdigest()!=expected_digest:
        raise ValueError('Proven Pages artifact digest mismatch')
    _,public=public_contract();selected={};seen=set();total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        items=archive.infolist()
        if len(items)!=1 or items[0].filename!='artifact.tar' or items[0].file_size>MAX_TAR:
            raise ValueError('Unexpected Pages archive')
        with archive.open(items[0]) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
            for index,member in enumerate(tar):
                if index>=20000:raise ValueError('Pages archive member limit')
                name=member.name.removeprefix('./')
                if name in ('','.'):continue
                path=Path(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name or path.as_posix()!=name:
                    raise ValueError('Unsafe Pages archive path')
                if name in seen:raise ValueError('Duplicate Pages archive path')
                seen.add(name)
                if member.isdir():continue
                if not member.isfile():raise ValueError('Linked or special Pages archive entry')
                limit=None
                if name in public:limit=public[name]['max_bytes']
                elif name==ODDS:limit=5_000_000
                elif name==POINTER:limit=10000
                elif name.startswith(SNAPSHOT_ROOT+'/'):
                    parts=name[len(SNAPSHOT_ROOT)+1:].split('/',1)
                    if len(parts)!=2 or re.fullmatch('[0-9a-f]{64}',parts[0]) is None:
                        raise ValueError('Invalid public snapshot address')
                    relative=parts[1]
                    if relative=='manifest.json':limit=1_000_000
                    elif relative in public:limit=public[relative]['max_bytes']
                    else:raise ValueError('Unreviewed public snapshot entry')
                if limit is None:continue
                if not 0<member.size<=limit:raise ValueError('Oversized prior-publication member')
                data=tar.extractfile(member).read(limit+1)
                if len(data)!=member.size:raise ValueError('Truncated Pages archive member')
                total+=len(data)
                if total>600_000_000:raise ValueError('Prior publication aggregate bound')
                selected[name]=data
    return selected

def _odds(raw):
    data=_strict_json(raw)
    state=data.get('collector_state')
    if (data.get('provider')!='The Odds API' or type(data.get('schema_version')) is not int or data['schema_version']!=1
        or not isinstance(state,dict) or type(state.get('schema_version')) is not int or state['schema_version']!=1
        or not isinstance(state.get('sources'),dict) or not isinstance(state.get('directory'),dict)
        or ('halted' in state and type(state['halted']) is not bool)
        or not isinstance(data.get('events'),list) or not isinstance(data.get('observed_at'),str)):
        raise ValueError('Verified odds control state unavailable')
    return raw

def restore_snapshot(proof,run_id,output:Path,*,get,get_archive,checkpoint=None,retained_archive=None):
    anchor=_proof(proof,run_id)
    run=get('/actions/runs/'+str(anchor))
    if (not isinstance(run,dict) or run.get('id')!=anchor or run.get('repository',{}).get('full_name')!=REPO
        or run.get('head_branch')!='main' or run.get('path')!='.github/workflows/deploy-pages.yml'
        or not successful_publication(run,get('/actions/runs/'+str(anchor)+'/attempts/1/jobs?per_page=100'))):
        raise ValueError('Anchor is not a verified first-attempt Pages publication')
    payload=get('/actions/runs/'+str(anchor)+'/artifacts?per_page=100')
    if (not isinstance(payload,dict) or type(payload.get('total_count')) is not int
        or not isinstance(payload.get('artifacts'),list) or payload['total_count']!=len(payload['artifacts'])):
        raise ValueError('Complete artifact inventory required')
    artifacts=[a for a in payload['artifacts'] if isinstance(a,dict) and a.get('name')=='github-pages']
    if len(artifacts)!=1:raise ValueError('Unique prior Pages artifact required')
    metadata=artifacts[0];origin=metadata.get('workflow_run',{})
    if (type(metadata.get('id')) is not int or metadata['id']<=0 or not isinstance(metadata.get('digest'),str)
        or re.fullmatch('sha256:[0-9a-f]{64}',metadata['digest']) is None
        or origin.get('id')!=anchor or origin.get('head_branch')!='main' or origin.get('head_sha')!=run.get('head_sha')):
        raise ValueError('Prior Pages artifact provenance mismatch')
    if retained_archive is not None:
        if not _checkpoint(checkpoint,anchor,metadata):raise ValueError('Retained archive requires exact reviewed recovery checkpoint')
        raw=retained_archive
    else:
        if metadata.get('expired') is not False:raise ValueError('Anchor artifact expired; exact retained-archive checkpoint required')
        raw=get_archive(metadata['id'])
    files=_archive_files(raw,metadata['digest'][7:]);odds=_odds(files.get(ODDS,b''))
    _,public=public_contract()
    if POINTER in files:
        pointer=_strict_json(files[POINTER])
        if (set(pointer)!={'schema_version','contract','snapshot_sha256'} or type(pointer['schema_version']) is not int
            or pointer['schema_version']!=1 or pointer['contract']!='public-data-pointer/v1'
            or not isinstance(pointer['snapshot_sha256'],str) or re.fullmatch('[0-9a-f]{64}',pointer['snapshot_sha256']) is None):
            raise ValueError('Malformed prior publication pointer')
        digest=pointer['snapshot_sha256'];prefix=SNAPSHOT_ROOT+'/'+digest+'/'
        manifest_raw=files[prefix+'manifest.json']
        captured={name:files[prefix+name] for name in public}
        if any(captured[name]!=files.get(name) for name in public):raise ValueError('Published root differs from immutable prior snapshot')
    else:
        # Initial cutover only. Never silently regenerate a missing manifest from
        # private/latest data. Owner checkpoint binds exact legacy artifact bytes.
        if not _checkpoint(checkpoint,anchor,metadata) or not isinstance(checkpoint.get('public_manifest'),dict):
            raise ValueError('Legacy publication requires exact reviewed bootstrap checkpoint')
        manifest_raw=canonical(checkpoint['public_manifest']);digest=hashlib.sha256(manifest_raw).hexdigest()
        if checkpoint.get('public_snapshot_sha256')!=digest:raise ValueError('Bootstrap manifest checkpoint mismatch')
        captured={name:files[name] for name in public}
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('New prior-publication directory required')
    parent=output.parent.resolve(strict=True);output=parent/output.name
    temporary=Path(tempfile.mkdtemp(prefix='.prior-publication-',dir=parent))
    try:
        for name,data in {**captured,'manifest.json':manifest_raw}.items():
            path=temporary/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        _,manifest=read_public_snapshot(temporary,expected_digest=digest)
        if manifest['publisher_run_id']!=anchor:raise ValueError('Public manifest belongs to another publisher run')
        if output.exists() or output.is_symlink():raise ValueError('Prior-publication destination appeared')
        temporary.rename(output)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return {'anchor_run_id':anchor,'artifact_id':metadata['id'],'snapshot_sha256':digest},odds

def require_activation(root):
    # No real checkpoint is shipped. Its reviewed addition is a separate owner-
    # authorized source cutover, never inferred from these prepared code files.
    config=_strict_json((Path(root)/'migration/activation/pages.json').read_bytes())
    raw=(Path(root)/'.github/workflows/deploy-pages.yml').read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if (set(config)!={'schema_version','source','approved_workflow_blob'}
        or type(config['schema_version']) is not int or config['schema_version']!=1
        or config['source']!='private-complete-snapshot/v1' or config['approved_workflow_blob']!=blob):
        raise ValueError('Reviewed production source activation checkpoint required')


def stage_migration(root,stage_path,previous_odds,*,checkpoint=None,retained_archive=None):
    from scripts.stage_odds_pages import stage
    from scripts.fetch_full_private_candidate import fetch_candidate,github_getter
    from scripts.prepare_full_private_preview import prepare_full_preview
    if os.environ.get('GITHUB_REPOSITORY')!=REPO:raise ValueError('Wrong Pages execution repository')
    require_activation(root)
    run_id=int(os.environ['GITHUB_RUN_ID']);temporary_root=Path(os.environ['RUNNER_TEMP'])
    proof=_strict_json((temporary_root/'odds-recovery-proof.json').read_bytes())
    if stage_path.exists() or previous_odds.exists():raise ValueError('Fresh stage/odds paths required')
    get,download=transports(os.environ.get('GH_TOKEN'))
    with tempfile.TemporaryDirectory(prefix='validated-data-stage-',dir=temporary_root) as temp:
        work=Path(temp)
        prior_receipt,odds=restore_snapshot(proof,run_id,work/'previous-publication',get=get,get_archive=download,
            checkpoint=checkpoint,retained_archive=retained_archive)
        private=fetch_candidate(work/'candidate',get=github_getter(os.environ.get('DATA_REPO_READ_TOKEN')))
        stage(root,work/'current-app')
        app_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        receipt=prepare_full_preview(work/'current-app',work/'candidate',stage_path,
            expected_data_commit=private['data_commit'],fetched_data_commit=private['data_commit'],
            expected_app_commit=app_commit,staged_app_commit=app_commit,now=datetime.now(timezone.utc),
            previous_publication=work/'previous-publication',
            expected_previous_snapshot_sha256=prior_receipt['snapshot_sha256'],trusted_publication_run_id=run_id)
        # Exact prior control bytes feed the unchanged later collector; do not
        # mark them fresh or erase hold/cooldown fields during source migration.
        previous_odds.write_bytes(odds)
        (stage_path/ODDS).write_bytes(odds)
        with (temporary_root/'private-publication-receipt.json').open('x') as stream:json.dump(receipt,stream,sort_keys=True)
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:stream.write('recovered=false\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--previous',type=Path,required=True);p.add_argument('--checkpoint',type=Path);p.add_argument('--retained-archive',type=Path);a=p.parse_args()
    try:
        checkpoint=_strict_json(a.checkpoint.read_bytes()) if a.checkpoint else None
        retained=a.retained_archive.read_bytes() if a.retained_archive else None
        stage_migration(a.root,a.stage,a.previous,checkpoint=checkpoint,retained_archive=retained)
    except Exception:
        raise SystemExit('Complete private publication blocked: prior state or candidate evidence unavailable. No provider request made.') from None
    print('Prepared validated complete publication; prior odds control state preserved.')
