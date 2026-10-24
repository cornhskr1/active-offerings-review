"""Protected application-side public-source-status/v1 semantic contract.

Reviewed source copy; never import executable code from private data snapshots.
Only source status/background timestamps are approved, not event ownership or
other data families. Keep parity tests with the data-repository preparation gate.
"""
from datetime import datetime, timezone, timedelta
import json
REVIEW_LISTS = ('events', 'u18_matches', 'restriction_triggers', 'coverage_alerts')

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be an aware ISO string')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if stamp.tzinfo is None:
        raise ValueError('naive timestamp')
    return stamp.astimezone(timezone.utc)

def validate(status, review, prior_status, prior_review, *, now, max_age_seconds):
    if now.tzinfo is None or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 86400:
        raise ValueError('explicit bounded freshness policy required')
    if not isinstance(status,dict) or set(status)!={'generated_at','source_count','healthy_count','sources'}:
        raise ValueError('unreviewed status fields')
    generated = timestamp(status.get('generated_at'))
    background = timestamp(review.get('background_checked_at'))
    if generated != background:
        raise ValueError('background timestamp mismatch')
    if generated > now or now-generated > timedelta(seconds=max_age_seconds):
        raise ValueError('future or stale source-status candidate')
    if generated < timestamp(prior_status.get('generated_at')) or background < timestamp(prior_review.get('background_checked_at')):
        raise ValueError('candidate older than retained publication')
    # The public-source health collector may never relabel old event evidence.
    if json.dumps({k:v for k,v in review.items() if k!='background_checked_at'},sort_keys=True,allow_nan=False) != json.dumps({k:v for k,v in prior_review.items() if k!='background_checked_at'},sort_keys=True,allow_nan=False):
        raise ValueError('public collector changed event-owned review records')
    if type(review.get('schema_version')) is not int or review['schema_version'] != 1:
        raise ValueError('unreviewed review schema')
    if timestamp(review.get('generated_at')) > now:
        raise ValueError('future event evidence timestamp')
    for key in REVIEW_LISTS:
        if not isinstance(review.get(key), list) or any(not isinstance(row, dict) for row in review[key]):
            raise ValueError('invalid review collection')
    rows = status.get('sources')
    if not isinstance(rows, list) or not rows:
        raise ValueError('source list required')
    if type(status.get('source_count')) is not int or status['source_count'] != len(rows):
        raise ValueError('source count mismatch')
    prior_rows = prior_status.get('sources')
    if not isinstance(prior_rows, list) or any(not isinstance(r,dict) for r in prior_rows):
        raise ValueError('prior source catalog missing')
    prior = {r.get('id'):r for r in prior_rows}
    if len(prior) != len(prior_rows) or any(not isinstance(k,str) or not k for k in prior):
        raise ValueError('ambiguous prior source identities')
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in seen or row['id'] not in prior:
            raise ValueError('unexpected or duplicate source identity')
        seen.add(row['id'])
        allowed={'id','name','url','priority','checked_at','http_status','final_url','ok',
                 'content_type','elapsed_ms','error','access_status','collection_paused','stale'}
        if set(row)-allowed:
            raise ValueError('unreviewed source status fields')
        for key in ('name','priority'):
            if not isinstance(row.get(key),str) or not row[key] or row[key]!=prior[row['id']].get(key):
                raise ValueError('source identity metadata changed')
        for key,limit in (('error',200),('content_type',1024),('final_url',4096)):
            if key in row and (not isinstance(row[key],str) or len(row[key])>limit):
                raise ValueError('invalid source detail')
        if 'elapsed_ms' in row and (type(row['elapsed_ms']) is not int or row['elapsed_ms']<0):
            raise ValueError('invalid elapsed time')
        if row.get('url') != prior[row['id']].get('url') or not isinstance(row.get('url'),str):
            raise ValueError('source URL changed without contract review')
        if type(row.get('ok')) is not bool:
            raise ValueError('source health must be boolean')
        held = prior[row['id']].get('access_status') == 'permission_required'
        if held or row.get('access_status') == 'permission_required':
            if (row.get('access_status')!='permission_required' or row['ok'] is not False
                or row.get('collection_paused') is not True or row.get('stale') is not True
                or row.get('checked_at') is not None or row.get('http_status') is not None):
                raise ValueError('publisher hold lost or falsely refreshed')
        else:
            if {'access_status','collection_paused','stale'} & set(row):
                raise ValueError('unreviewed publisher-hold state')
            checked=timestamp(row.get('checked_at'))
            if checked > generated or generated-checked > timedelta(seconds=max_age_seconds) or now-checked > timedelta(seconds=max_age_seconds):
                raise ValueError('invalid source-check timestamp')
            code=row.get('http_status')
            if code is not None and (type(code) is not int or not 100<=code<=599):
                raise ValueError('invalid HTTP status')
            if row['ok'] and (code is None or not 200<=code<400):
                raise ValueError('false healthy source')
    if seen != set(prior):
        raise ValueError('partial source catalog')
    if type(status.get('healthy_count')) is not int or status['healthy_count'] != sum(r['ok'] for r in rows):
        raise ValueError('healthy count mismatch')
