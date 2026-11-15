"""Wait for exact uploaded Pages artifact visibility; never retry collection/deployment.

Read-only GitHub API calls, bounded attempts, no redirects or provider credentials.
Identity/integrity errors fail immediately; only absence/transient API errors retry.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

REPOSITORY = 'cornhskr1/active-offerings-review'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Artifact API redirect rejected')


def artifact_ready(payload, artifact_id, run_id, head_sha):
    if not isinstance(payload, dict) or type(payload.get('total_count')) is not int:
        raise ValueError('Artifact list unavailable')
    rows = payload.get('artifacts')
    if not isinstance(rows, list) or payload['total_count'] != len(rows):
        raise ValueError('Artifact list incomplete')
    if not rows:
        return False
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError('Ambiguous Pages artifact')
    a = rows[0]
    run = a.get('workflow_run')
    if (type(a.get('id')) is not int or a['id'] != artifact_id
            or a.get('name') != 'github-pages' or a.get('expired') is not False
            or type(a.get('size_in_bytes')) is not int or a['size_in_bytes'] <= 0
            or not isinstance(run, dict) or run.get('id') != run_id
            or run.get('head_branch') != 'main' or run.get('head_sha') != head_sha):
        raise ValueError('Pages artifact identity or availability mismatch')
    return True


def wait_for_artifact(fetch, artifact_id, run_id, head_sha, sleep=time.sleep):
    for attempt in range(7):
        try:
            if artifact_ready(fetch(), artifact_id, run_id, head_sha):
                return
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        if attempt < 6:
            sleep(10)
    raise ValueError('Exact uploaded Pages artifact not visible after bounded wait')


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Repository mismatch')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    artifact_id = os.environ.get('PAGES_ARTIFACT_ID', '')
    sha = os.environ.get('GITHUB_SHA', '')
    token = os.environ.get('GH_TOKEN', '')
    if not (run_id.isdigit() and artifact_id.isdigit() and int(artifact_id) > 0
            and re.fullmatch('[0-9a-f]{40}', sha) and token):
        raise ValueError('Artifact verification identity missing')
    url = f'https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?name=github-pages&per_page=100'
    opener = urllib.request.build_opener(NoRedirect())
    def fetch():
        request = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'})
        with opener.open(request, timeout=10) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError('Artifact response too large')
        return json.loads(raw)
    wait_for_artifact(fetch, int(artifact_id), int(run_id), sha)
    print(f'Exact Pages artifact {artifact_id} verified for run {run_id}; deployment may proceed.')

if __name__ == '__main__':
    main()
