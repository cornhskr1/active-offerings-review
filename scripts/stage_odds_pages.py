"""Stage tracked public site files and recover only the prior minimal UI cache.

No provider credentials or provider requests belong in this module.
"""
from pathlib import Path
import argparse
import os
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 5_000_000
PRODUCTION = 'https://cornhskr1.github.io/active-offerings-review/'

class CacheMissing(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Previous snapshot redirect rejected')

def recover_previous(url, opener=None):
    if url != PRODUCTION + 'data/odds-api-events.json':
        raise ValueError('Unapproved previous-snapshot location')
    opener = opener or urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(url, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Previous snapshot too large')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('provider') != 'The Odds API' or data.get('schema_version') != 1:
            raise ValueError('Previous snapshot schema invalid')
        return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            # Only the old, pre-integration dashboard may bootstrap without a
            # cache. A missing cache after activation must never clear a halt.
            try:
                with opener.open(PRODUCTION, timeout=20) as page:
                    html = page.read(2_000_001)
                if len(html) > 2_000_000 or b'data/odds-api-events.json' in html or b'Upcoming Event Review' not in html:
                    raise ValueError('Existing dashboard requires its prior snapshot')
                return None
            except Exception:
                raise CacheMissing('Cannot establish safe first deployment') from None
        raise ValueError('Previous snapshot unavailable') from None
    except Exception:
        raise ValueError('Previous snapshot unavailable or invalid') from None

def stage(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination == root:
        raise ValueError('Staging must be separate')
    destination.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    for name in filter(None, tracked):
        source = root / name
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError('Unexpected tracked link')
        if not source.is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--previous', required=True)
    args = parser.parse_args()
    recovered_raw = None
    try:
        previous = recover_previous(PRODUCTION + 'data/odds-api-events.json')
    except CacheMissing:
        from recover_verified_pages_cache import recover
        proof=json.loads(Path(os.environ['RUNNER_TEMP'],'odds-recovery-proof.json').read_text())
        recovered_raw=recover(proof,int(os.environ['GITHUB_RUN_ID']))
        previous=json.loads(recovered_raw)
    # Fail the deployment on uncertain cache recovery: do not erase a halt or
    # last-good snapshot and accidentally restart collection.
    Path(args.previous).write_text(json.dumps(previous or {}))
    stage(args.root, args.stage)
    if recovered_raw is not None:
        target=Path(args.stage,'data/odds-api-events.json');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(recovered_raw)
        with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('recovered=true\n')
        print('Restored the verified saved event snapshot unchanged; provider collection is skipped.')
