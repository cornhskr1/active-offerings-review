"""One bounded restoration of an overwritten cache; never contacts a provider.

Only the exact verified GitHub Actions artifact is accepted. No archive paths
are extracted and no timestamp, halt, or cooldown is rewritten.
"""
import hashlib,io,json,os,subprocess,tarfile,zipfile
REPO='cornhskr1/active-offerings-review'
RUN=39200456743
ARTIFACT=12163254376
DIGEST='916fe7401d5c692eb39ea80c34c891d7c576460274f6c08ec1aad89e33f5b57a'
MAX_ZIP=20_000_000
MAX_TAR=150_000_000
MAX_CACHE=5_000_000

def validate_metadata(metadata):
 return (isinstance(metadata,dict) and metadata.get('id')==ARTIFACT and metadata.get('name')=='github-pages'
  and metadata.get('expired') is False and metadata.get('digest')=='sha256:'+DIGEST
  and metadata.get('workflow_run',{}).get('id')==RUN
  and metadata.get('workflow_run',{}).get('repository_id')==1349023164
  and metadata.get('workflow_run',{}).get('head_branch')=='main'
  and metadata.get('workflow_run',{}).get('head_sha')=='d9008dba9613ad931349a78dc1e436a145303214')

def read_cache_archive(raw,expected_digest=DIGEST):
 if len(raw)>MAX_ZIP or hashlib.sha256(raw).hexdigest()!=expected_digest:raise ValueError('Artifact digest mismatch')
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  members=archive.infolist()
  if len(members)!=1 or members[0].filename!='artifact.tar' or members[0].file_size>MAX_TAR:raise ValueError('Unexpected artifact contents')
  found=[]
  with archive.open(members[0]) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
   for member in tar:
    if member.name not in ('data/odds-api-events.json','./data/odds-api-events.json'):continue
    if not member.isfile() or member.size>MAX_CACHE:raise ValueError('Unsafe cache member')
    found.append(tar.extractfile(member).read(MAX_CACHE+1))
  if len(found)!=1:raise ValueError('Cache member missing or duplicated')
 data=json.loads(found[0])
 if not isinstance(data,dict) or data.get('provider')!='The Odds API' or data.get('schema_version')!=1:raise ValueError('Invalid cache schema')
 state=data.get('collector_state')
 if not isinstance(state,dict) or state.get('schema_version')!=1 or not isinstance(state.get('sources'),dict) or not isinstance(state.get('directory'),dict):raise ValueError('Missing control state')
 if 'halted' in state and type(state['halted']) is not bool:raise ValueError('Invalid halt state')
 if not isinstance(data.get('events'),list) or not isinstance(data.get('observed_at'),str):raise ValueError('Missing observation evidence')
 return found[0]

def recover(proof,run_id,gh_api=None):
 if proof!={'repository':REPO,'current_run_id':run_id,'anchor_run_id':RUN}:raise ValueError('Recovery anchor not verified')
 def cli(path):
  # Official GitHub CLI owns authenticated redirects; no provider key is read.
  result=subprocess.run(['gh','api','repos/'+REPO+path],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=False,timeout=90,env={**os.environ,'GH_HOST':'github.com'})
  if result.returncode or len(result.stdout)>MAX_ZIP:raise ValueError('Verified artifact unavailable')
  return result.stdout
 get=gh_api or cli
 metadata=json.loads(get('/actions/artifacts/'+str(ARTIFACT)))
 if not validate_metadata(metadata):raise ValueError('Artifact provenance mismatch or expired')
 return read_cache_archive(get('/actions/artifacts/'+str(ARTIFACT)+'/zip'))
