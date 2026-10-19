"""Fail closed after an unsuccessful source-persistence run; no provider access."""
import json
import os
import urllib.request
from datetime import datetime, timezone
try:
    from check_odds_deploy_safety import NoRedirect, stable_runs
except ImportError:
    from scripts.check_odds_deploy_safety import NoRedirect, stable_runs
REPOSITORY = 'cornhskr1/active-offerings-review'
PATH = '.github/workflows/refresh-jolpica-f1.yml'


def permitted(current, runs, resume=False, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(current, dict) or current.get('path') != PATH or current.get('head_branch') != 'main' or current.get('run_attempt') != 1:
        return False
    if type(current.get('id')) is not int or type(current.get('workflow_id')) is not int:
        return False
    if not isinstance(runs, list):
        return False
    for r in runs:
        if not isinstance(r, dict) or type(r.get('id')) is not int or r.get('workflow_id') != current['workflow_id'] or r.get('head_branch') != 'main':
            return False
    prior = [r for r in runs if r['id'] != current['id'] and r.get('status') != 'queued']
    if not prior:
        return current.get('run_number') == 1
    if any(r.get('status') != 'completed' for r in prior):
        return False
    try:
        times = [datetime.fromisoformat(r['updated_at'].replace('Z', '+00:00')) for r in prior]
        if any(t.tzinfo is None or t > now for t in times):
            return False
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    if resume:
        return True
    latest = max(times)
    return all(r.get('conclusion') == 'success' for r, t in zip(prior, times) if t == latest)


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('repository_mismatch')
    token, run_id = os.environ.get('GH_TOKEN'), os.environ.get('GITHUB_RUN_ID', '')
    if not token or not run_id.isdigit():
        raise ValueError('history_unavailable')
    opener = urllib.request.build_opener(NoRedirect())
    def get(path):
        req = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
            headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
        with opener.open(req, timeout=20) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError('history_too_large')
        return json.loads(body)
    current = get('/actions/runs/' + run_id)
    if current.get('id') != int(run_id) or current.get('repository', {}).get('full_name') != REPOSITORY or type(current.get('workflow_id')) is not int:
        raise ValueError('history_mismatch')
    runs = stable_runs(lambda page: get('/actions/workflows/' + str(current['workflow_id']) + '/runs?per_page=100&page=' + str(page)))
    resume = os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and os.environ.get('RESUME_AFTER_REVIEW') == 'true'
    if not permitted(current, runs, resume):
        raise ValueError('previous_persistence_unconfirmed')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('F1 collection blocked: prior source run failed or is uncertain. Review before resuming.') from None
