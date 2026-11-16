"""Bind a wake-up to immutable private provenance, never a source of approval."""
import base64
import hashlib
import os
import re


def inputs(environment=None):
    env = os.environ if environment is None else environment
    commit = env.get('NOTIFICATION_DATA_COMMIT', '')
    digest = env.get('NOTIFICATION_MANIFEST_SHA256', '')
    if not commit and not digest: return None
    if (re.fullmatch('[0-9a-f]{40}', commit) is None
        or re.fullmatch('[0-9a-f]{64}', digest) is None
        or env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
        or env.get('GITHUB_REF') != 'refs/heads/main'
        or env.get('GITHUB_RUN_ATTEMPT') != '1'
        or env.get('NOTIFICATION_RESUME', 'false') != 'false'):
        raise ValueError('Invalid publication notification')
    return commit, digest


def verify(notification, candidate, get):
    if notification is None: return
    commit, digest = notification
    current = candidate['data_commit']
    if not isinstance(current, str) or re.fullmatch('[0-9a-f]{40}', current) is None:
        raise ValueError('Invalid selected candidate')
    if current == commit:
        if candidate['manifest_sha256'] != digest: raise ValueError('Notified manifest mismatch')
        return
    # Fixed immutable endpoints bind the wake-up to the exact independently
    # fetched candidate. Never re-resolve moving main after snapshot selection.
    comparison = get('/compare/' + commit + '...' + current + '?per_page=1')
    if (not isinstance(comparison, dict) or comparison.get('status') != 'ahead'
        or comparison.get('base_commit', {}).get('sha') != commit
        or comparison.get('merge_base_commit', {}).get('sha') != commit
        or type(comparison.get('ahead_by')) is not int or comparison['ahead_by'] <= 0
        or comparison.get('behind_by') != 0):
        raise ValueError('Notification is not an ancestor of selected data')
    tree = get('/git/trees/' + commit + '?recursive=1')
    if (not isinstance(tree, dict) or tree.get('truncated') is not False
        or not isinstance(tree.get('tree'), list)):
        raise ValueError('Incomplete notified tree')
    entries = [e for e in tree['tree'] if isinstance(e, dict)
               and e.get('path') == 'published/current/manifest.json']
    if len(entries) != 1: raise ValueError('Ambiguous notified manifest')
    entry = entries[0]
    if (entry.get('type') != 'blob' or entry.get('mode') != '100644'
        or not isinstance(entry.get('sha'), str) or re.fullmatch('[0-9a-f]{40}', entry['sha']) is None
        or type(entry.get('size')) is not int or not 0 < entry['size'] <= 1_000_000):
        raise ValueError('Invalid notified manifest entry')
    blob = get('/git/blobs/' + entry['sha'])
    if (not isinstance(blob, dict) or blob.get('sha') != entry['sha']
        or blob.get('encoding') != 'base64' or blob.get('size') != entry['size']
        or not isinstance(blob.get('content'), str)):
        raise ValueError('Notified manifest identity mismatch')
    raw = base64.b64decode(''.join(blob['content'].split()), validate=True)
    if (len(raw) != entry['size']
        or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != entry['sha']
        or hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError('Notified manifest bytes mismatch')
