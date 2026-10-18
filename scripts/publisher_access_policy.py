"""Owner-requested collection pause; exact publisher domains, not sport categories.

This is an operational hold pending access review, not a finding of liability.
Saved observations are retained, never relabeled as freshly collected.
"""
import copy
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit

HELD_PUBLISHERS = {
    'espn.com': 'ESPN', 'ncaa.com': 'NCAA', 'itftennis.com': 'ITF',
    'usta.com': 'USTA', 'fiba.basketball': 'FIBA', 'fiba3x3.com': 'FIBA', 'faw.cymru': 'FAW',
}


def permission_hold_reason(url):
    try:
        host = (urlsplit(str(url)).hostname or '').lower().rstrip('.')
    except ValueError:
        return None
    for domain, publisher in HELD_PUBLISHERS.items():
        if host == domain or host.endswith('.' + domain):
            return f'Permission required: {publisher} automated collection is paused pending access review; saved observations are not fresh.'
    return None


def require_publisher_access(url):
    reason = permission_hold_reason(url)
    if reason:
        raise PermissionError(reason)


def install_network_guards():
    """Guard actual HTTP dispatch, including redirects, within this process only."""
    import urllib.request
    if getattr(urllib.request.OpenerDirector.open, '_publisher_guard', False) is not True:
        original = urllib.request.OpenerDirector.open
        def guarded_open(self, fullurl, *args, **kwargs):
            require_publisher_access(getattr(fullurl, 'full_url', fullurl))
            return original(self, fullurl, *args, **kwargs)
        guarded_open._publisher_guard = True
        urllib.request.OpenerDirector.open = guarded_open
    try:
        import requests
    except ImportError:
        return
    if getattr(requests.sessions.Session.send, '_publisher_guard', False) is not True:
        original_send = requests.sessions.Session.send
        def guarded_send(self, request, **kwargs):
            require_publisher_access(request.url)
            return original_send(self, request, **kwargs)
        guarded_send._publisher_guard = True
        requests.sessions.Session.send = guarded_send


def paused_snapshot(payload, reason, now=None):
    result = copy.deepcopy(payload)
    result.update(collection_paused=True, stale=True, access_status='permission_required',
                  collection_status_note=reason,
                  collection_hold_recorded_at=(now or dt.datetime.now(dt.timezone.utc)).isoformat())
    if isinstance(result.get('quality'), dict):
        result['quality'].update(passed=False, collection_paused=True, reason=reason)
    # Keep original generated_at and observation timestamps, all values and IDs.
    for key in ('sources', 'lanes'):
        for row in result.get(key, []) if isinstance(result.get(key), list) else []:
            row.update(ok=False, collection_paused=True, stale=True,
                       access_status='permission_required', errors=[reason])
    for row in result.get('events', []):
        row.update(collection_paused=True, stale=True, source_stale=True, collection_status_note=reason)
    return result


def preserve_snapshot_on_hold(path, url):
    reason = permission_hold_reason(url)
    if not reason:
        return False
    path = Path(path)
    payload = json.loads(path.read_text()) if path.exists() else {'schema_version': 1}
    path.write_text(json.dumps(paused_snapshot(payload, reason), indent=2) + '\n')
    print(reason)
    return True


def source_permission_hold_reason(source):
    # Recorded manual windows make no network request and remain available.
    if source.get('source_type') == 'official-event-window' and source.get('endpoint_validation') == 'published-window':
        return None
    if source.get('source_type') == 'coverage-gap' and source.get('id') not in {'tennis-usta-pro-circuit-men','tennis-usta-pro-circuit-women'}:
        return None
    # Informational links do not define the network target when an endpoint exists.
    if source.get('endpoint'):
        return permission_hold_reason(source['endpoint'])
    for key in ('url', 'publisher_page'):
        if source.get(key):
            return permission_hold_reason(source[key])
    if source.get('source_type') == 'tennis-intelligence' or source.get('id') in {
        'tennis-usta-pro-circuit-men', 'tennis-usta-pro-circuit-women'}:
        return permission_hold_reason(source.get('official_schedule_url', ''))
    return None


def retained_source_events(previous, source, reason):
    """Keep saved observations, labeling them stale without new collection claims."""
    rows = []
    routed_ids={r.get('source_id') for r in source.get('name_routing', []) if isinstance(r,dict)}
    for event in previous.get('events', []):
        if (event.get('source_id') == source.get('id') or
            (event.get('source_id') in routed_ids and source.get('endpoint') and event.get('source_endpoint') == source['endpoint'])):
            row = copy.deepcopy(event)
            row.update(collection_paused=True, stale=True, source_stale=True, collection_status_note=reason)
            rows.append(row)
    return rows
