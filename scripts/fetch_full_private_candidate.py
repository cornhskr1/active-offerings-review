"""Read-only complete private snapshot fetch. App-owned code; no data-code execution.

Resolve fixed repository main once, then use immutable Git tree/blob endpoints
(including binary PDF and files over Contents API's inline limit). No redirects.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request
from scripts.prepare_full_private_preview import _contract, read_full_snapshot

REPOSITORY='cornhskr1/active-offerings-data'
PREFIX='published/current/'
MAX_RESPONSE=32_000_000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Private snapshot redirect refused')

def revision(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{40}',value) is not None

def github_getter(token):
    if not isinstance(token,str) or not token:raise ValueError('Existing private-read token required')
    opener=urllib.request.build_opener(NoRedirect())
    def get(path):
        if not path.startswith(('/commits/','/git/trees/','/git/blobs/')) or any(v in path for v in ('://','#','\\','..')):
            raise ValueError('Unapproved private GitHub endpoint')
        request=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+path,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        with opener.open(request,timeout=20) as response:raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:raise ValueError('Private GitHub response too large')
        return json.loads(raw)
    return get

def fetch_candidate(output:Path,*,get):
    spec=_contract();names=set(spec['outputs'])|{'manifest.json'}
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('New unlinked candidate destination required')
    parent=output.parent.resolve(strict=True);output=parent/output.name
    selected=get('/commits/main')
    if not isinstance(selected,dict) or not revision(selected.get('sha')):raise ValueError('Immutable private main unavailable')
    commit=selected['sha']
    tree=get('/git/trees/'+commit+'?recursive=1')
    if not isinstance(tree,dict) or tree.get('truncated') is not False or not isinstance(tree.get('tree'),list):
        raise ValueError('Complete immutable private tree required')
    files={}
    for entry in tree['tree']:
        if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):raise ValueError('Malformed private tree')
        name=entry['path']
        if not name.startswith(PREFIX):continue
        relative=name[len(PREFIX):]
        if entry.get('type')=='tree':continue
        if (relative not in names or relative in files or entry.get('type')!='blob'
            or entry.get('mode')!='100644' or not revision(entry.get('sha'))):
            raise ValueError('Unexpected, executable or linked private snapshot entry')
        limit=1_000_000 if relative=='manifest.json' else spec['outputs'][relative]['max_bytes']
        if type(entry.get('size')) is not int or not 0<entry['size']<=limit:raise ValueError('Private entry size exceeds reviewed bound')
        files[relative]=entry
    if set(files)!=names:raise ValueError('Incomplete private snapshot tree')
    temporary=Path(tempfile.mkdtemp(prefix='.private-full-',dir=parent))
    try:
        total=0
        for name,entry in files.items():
            blob=get('/git/blobs/'+entry['sha'])
            if (not isinstance(blob,dict) or blob.get('sha')!=entry['sha'] or blob.get('encoding')!='base64'
                or type(blob.get('size')) is not int or blob['size']!=entry['size'] or not isinstance(blob.get('content'),str)):
                raise ValueError('Private blob identity mismatch')
            raw=base64.b64decode(''.join(blob['content'].split()),validate=True)
            if len(raw)!=entry['size'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=entry['sha']:
                raise ValueError('Private blob bytes mismatch')
            total+=len(raw)
            if total>256_000_000:raise ValueError('Aggregate private snapshot exceeds bound')
            path=temporary/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        _,manifest,_,digest=read_full_snapshot(temporary)
        if output.exists() or output.is_symlink():raise ValueError('Candidate destination appeared')
        temporary.rename(output)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return {'repository':REPOSITORY,'data_commit':commit,'manifest_sha256':digest,
            'contract':manifest['contract'],'files':sorted(spec['outputs'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--receipt',required=True,type=Path);a=p.parse_args()
    try:
        receipt=fetch_candidate(a.out,get=github_getter(os.environ.get('DATA_REPO_READ_TOKEN')))
        with a.receipt.open('x') as stream:json.dump(receipt,stream,sort_keys=True)
    except Exception:
        raise SystemExit('Private complete snapshot unavailable or invalid; publication blocked.') from None
    print('Verified complete private candidate at immutable revision',receipt['data_commit'])
