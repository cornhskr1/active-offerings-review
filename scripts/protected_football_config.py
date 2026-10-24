"""Retain app-owned football configuration while accepting mapper state only.

The original collector writes exactly the fields enumerated below. Protected
team identities/configuration must match the independent current app stage.
New mapped URL paths are allowed only on its already-approved team hosts.
"""
from urllib.parse import urlsplit
from scripts.snapshot_semantic_guards import canonical,safe_url

TOP_GENERATED={'last_auto_map_run','last_age_discovery_run'}
TEAM_GENERATED={'mapped','mapping_status','last_mapping_check','schedule_url','roster_url','official_root'}
URL_FIELDS={'schedule_url','roster_url','official_root'}


def validate_football_config(protected,candidate):
    if not isinstance(protected,dict) or not isinstance(candidate,dict):raise ValueError('football config object required')
    project=lambda obj:{k:v for k,v in obj.items() if k not in TOP_GENERATED|{'teams'}}
    if canonical(project(protected))!=canonical(project(candidate)):
        raise ValueError('private output changed protected football configuration')
    old=protected.get('teams');new=candidate.get('teams')
    if not isinstance(old,list) or not isinstance(new,list):raise ValueError('football team inventory required')
    def identities(rows):
        if any(not isinstance(row,dict) or not isinstance(row.get('team'),str) or not row['team'] for row in rows):
            raise ValueError('football team identity missing')
        names=[row['team'] for row in rows]
        if len(names)!=len(set(names)):raise ValueError('duplicate football team identity')
        return names
    if identities(old)!=identities(new):raise ValueError('protected football team inventory changed')
    for prior,row in zip(old,new):
        if canonical({k:v for k,v in prior.items() if k not in TEAM_GENERATED})!=canonical({k:v for k,v in row.items() if k not in TEAM_GENERATED}):
            raise ValueError('private output changed protected team configuration')
        if 'mapped' in row and type(row['mapped']) is not bool:raise ValueError('mapping state must be boolean')
        if 'mapping_status' in row and not isinstance(row['mapping_status'],str):raise ValueError('mapping status must be text')
        approved=list(prior.get('candidate_roots',[])) if isinstance(prior.get('candidate_roots',[]),list) else []
        approved.extend(prior.get(k) for k in URL_FIELDS|{'official_site'})
        hosts={urlsplit(value).hostname for value in approved if isinstance(value,str) and value and urlsplit(value).scheme in ('http','https')}
        for key in URL_FIELDS:
            value=row.get(key)
            if value is None or value=='':continue
            safe_url(value)
            if urlsplit(value).hostname not in hosts:raise ValueError('unapproved football mapping host')
