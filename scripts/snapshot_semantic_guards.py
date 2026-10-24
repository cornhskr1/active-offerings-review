"""Protected transport invariants against independently trusted prior publication.

Preserve rights holds/durable reviewed identities; do not certify sporting facts.
A hold/evidence release needs a separately reviewed protected policy change.
"""
from collections import Counter
from datetime import date,datetime,timezone
import json
from urllib.parse import urlsplit

TIMESTAMPS={'generated_at','observed_at','checked_at','background_checked_at','last_verified',
    'verified_at','fetched_at','last_seen','source_generated_at','schedule_generated_at',
    'collection_hold_recorded_at'}
HOLD_FLAGS={'collection_paused','permission_held','permission_required','halted'}
HOLD_LISTS={'publisher_permission_holds'}
ADMIN_FIELDS={'collection_hold_recorded_at','collection_status_note','errors','reason'}
DERIVED_FIELDS={'age','calculated_age','current_age','current_exposure','is_u18','age_status'}
IDENTITY_FIELDS=('official_player_id','player_id','athlete_id','official_id','id')
DURABLE_IDENTITY_FIELDS={'name','canonical_name','athlete','official_player_id','player_id','athlete_id','official_id','aliases','alias'}
EVIDENCE_FIELDS={'name','canonical_name','athlete','age_evidence','age_evidence_review','dob','source_dob','source_url',
    'official_player_id','player_id','athlete_id','official_id','aliases','alias',
    'evidence','evidence_source','evidence_url','verified_at','last_verified','verification_method'}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def stamp(value,now):
    if value is None or value=='':return
    if not isinstance(value,str):raise ValueError('timestamp must be text or unknown')
    if len(value)==10:
        if date.fromisoformat(value)>now.date():raise ValueError('future evidence date')
        return
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None or parsed>now:raise ValueError('naive or future observation timestamp')


def safe_url(value):
    if value is None or value=='':return
    if isinstance(value,(list,dict)):
        for item in (value.values() if isinstance(value,dict) else value):safe_url(item)
        return
    if not isinstance(value,str):raise ValueError('URL must be text or unknown')
    if any(ord(c)<33 or ord(c)==127 for c in value):raise ValueError('control/space in URL')
    parsed=urlsplit(value)
    if parsed.scheme.lower() not in ('http','https') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('unsafe URL scheme or authority')


def observations(value,now):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in TIMESTAMPS:stamp(item,now)
            if key in ('url','href','endpoint') or key.endswith('_url') or key.endswith('_urls'):safe_url(item)
            observations(item,now)
    elif isinstance(value,list):
        for item in value:observations(item,now)


def held(node):
    return isinstance(node,dict) and (any(node.get(k) is True for k in HOLD_FLAGS)
        or node.get('access_status') in ('permission_required','permission-required','access_denied','blocked','halted'))


def reviewed(node):
    evidence=node.get('age_evidence') if isinstance(node,dict) else None
    return isinstance(evidence,dict) and isinstance(evidence.get('review'),dict) and bool(evidence['review'].get('id'))


def protected(node):
    if isinstance(node,dict):
        return (held(node) or reviewed(node) or bool(node.get('age_evidence_review'))
            or (node.get('schema_version')==2 and 'records' in node)
            or any(node.get(k) for k in HOLD_LISTS) or any(protected(v) for v in node.values()))
    if isinstance(node,list):return any(protected(v) for v in node)
    return False


def identity(node):
    if not isinstance(node,dict):return None
    for key in IDENTITY_FIELDS:
        if type(node.get(key)) in (str,int) and str(node[key]):return (key,str(node[key]))
    if isinstance(node.get('source_url'),str) and node['source_url']:
        return ('source_url',node['source_url'])
    # Never merge different official IDs by name; IDs were already selected above.
    if isinstance(node.get('name'),str):
        return ('legacy',canonical({k:node[k] for k in ('name','team','source') if k in node}))
    return None


def held_payload(value):
    if isinstance(value,dict):
        return {k:held_payload(v) for k,v in value.items() if k not in ADMIN_FIELDS|DERIVED_FIELDS}
    if isinstance(value,list):return [held_payload(v) for v in value]
    return value


def retained_records(previous,current,*,durable=False):
    if not isinstance(current,list):
        if durable or protected(previous):raise ValueError('protected retained array removed')
        return
    if canonical(previous)==canonical(current):return
    old_counts=Counter(identity(row) for row in previous)
    new_counts=Counter(identity(row) for row in current)
    for old in previous:
        if not durable and not protected(old):continue
        key=identity(old)
        if key is None:
            if canonical(old) not in {canonical(row) for row in current}:raise ValueError('unkeyed retained record removed')
            continue
        matching=[row for row in current if identity(row)==key]
        if old_counts[key]>1:
            # Preserve already-existing ambiguous records verbatim, never merge them.
            needed=Counter(canonical(row) for row in previous if identity(row)==key)
            present=Counter(canonical(row) for row in matching)
            if any(present[k]<n for k,n in needed.items()):raise ValueError('ambiguous retained records changed')
            continue
        if new_counts[key]!=1:raise ValueError('retained identity missing or duplicated')
        new=matching[0]
        if durable or reviewed(old):
            for field in (EVIDENCE_FIELDS if reviewed(old) else DURABLE_IDENTITY_FIELDS):
                if field in old and (field not in new or canonical(old[field])!=canonical(new[field])):
                    raise ValueError('durable identity/evidence changed: '+field)
        preserve(old,new)


def preserve(previous,current):
    if canonical(previous)==canonical(current):return
    if isinstance(previous,dict):
        if not isinstance(current,dict):
            if protected(previous):raise ValueError('protected observation removed')
            return
        for key in HOLD_FLAGS:
            if previous.get(key) is True and current.get(key) is not True:raise ValueError('publisher hold cleared')
        for key in HOLD_LISTS:
            if previous.get(key):
                before=previous[key];after=current.get(key)
                if isinstance(before,list) and isinstance(after,list):
                    if not set(map(canonical,before)).issubset(set(map(canonical,after))):raise ValueError('publisher hold removed')
                elif canonical(before)!=canonical(after):raise ValueError('publisher hold changed')
        if held(previous) and canonical(held_payload(previous))!=canonical(held_payload(current)):
            raise ValueError('held observation removed, changed or relabeled')
        if reviewed(previous):
            for field in EVIDENCE_FIELDS:
                if field in previous and (field not in current or canonical(previous[field])!=canonical(current[field])):
                    raise ValueError('reviewed identity/evidence changed: '+field)
        for key in ('age_evidence','age_evidence_review'):
            if previous.get(key) and (key=='age_evidence_review' or reviewed(previous)) and canonical(current.get(key))!=canonical(previous[key]):
                raise ValueError('reviewed age evidence changed')
        for key,value in previous.items():
            if key=='records' and previous.get('schema_version')==2 and isinstance(value,list):
                retained_records(value,current.get(key),durable=True)
            elif key not in current:
                if protected(value):raise ValueError('protected retained field removed')
            else:preserve(value,current[key])
    elif isinstance(previous,list):retained_records(previous,current)


def validate_change(previous,current,*,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('aware validation clock required')
    observations(current,now);preserve(previous,current)
