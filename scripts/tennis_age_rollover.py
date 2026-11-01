"""Offline retention proof for athletes aging out of derived current-U18 views.

Durable registry records and their reviewed evidence are never removed. Only an
omission from the two named current-age projections can use this proof. No source
access, evidence renewal, inferred DOB or generic retained-list exception exists.
"""
from copy import deepcopy
from datetime import date, datetime
from zoneinfo import ZoneInfo
from scripts.snapshot_semantic_guards import (
    EVIDENCE_FIELDS, HOLD_LISTS, canonical, held, identity, preserve,
    retained_records, reviewed,
)

REGISTRY = 'data/tennis-u18-registry.json'
PROJECTIONS = {REGISTRY: 'verified_u18',
               'data/tennis-intelligence.json': 'live_u18_registry'}
CT = ZoneInfo('America/Chicago')


def contains_hold(value):
    if isinstance(value, dict):
        return (held(value) or any(value.get(k) for k in HOLD_LISTS)
                or any(contains_hold(v) for v in value.values()))
    return isinstance(value, list) and any(contains_hold(v) for v in value)


def generated_on(document, day):
    try:
        stamp = datetime.fromisoformat(document['generated_at'].replace('Z', '+00:00'))
        return stamp.tzinfo is not None and stamp.astimezone(CT).date() == day
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def reviewed_adult(record, day):
    if not reviewed(record) or contains_hold(record):
        return False
    evidence = record.get('age_evidence') or {}
    if evidence.get('status') != 'verified_dob':
        return False
    try:
        dob = date.fromisoformat(evidence['dob'])
        if dob.isoformat() != evidence['dob']:
            return False
        # Match the producer's conservative leap-day boundary: Feb 28 of the
        # eighteenth year cannot resolve a Feb 29 birthday convention.
        if (dob.month, dob.day) == (2, 29) and day.year == dob.year + 18 and (day.month, day.day) == (2, 28):
            return False
        return day.year - dob.year - ((day.month, day.day) < (dob.month, dob.day)) >= 18
    except (KeyError, TypeError, ValueError):
        return False


def retention_baselines(previous, current, now):
    """Return validation baselines, leaving all input and output bytes untouched.

    Generic preservation still checks every other field, list and family. The
    durable registry is independently validated before either projection changes.
    """
    old_registry, registry = previous.get(REGISTRY), current.get(REGISTRY)
    if not isinstance(old_registry, dict) or not isinstance(registry, dict):
        return previous
    if old_registry.get('schema_version') != 2 or registry.get('schema_version') != 2:
        return previous
    old_records, records = old_registry.get('records'), registry.get('records')
    if not isinstance(old_records, list) or not isinstance(records, list):
        return previous
    retained_records(old_records, records, durable=True)
    day = now.astimezone(CT).date()
    if not generated_on(registry, day):
        return previous
    indexed = {}
    for record in records:
        indexed.setdefault(identity(record), []).append(record)
    baselines = dict(previous)
    for path, field in PROJECTIONS.items():
        old, new = previous.get(path), current.get(path)
        if not isinstance(old, dict) or not isinstance(new, dict):
            continue
        if not generated_on(new, day) or not isinstance(old.get(field), list) or not isinstance(new.get(field), list):
            continue
        kept = []
        for record in old[field]:
            key = identity(record)
            candidates = indexed.get(key, [])
            omitted = key is not None and not any(identity(row) == key for row in new[field])
            permitted = (omitted and len(candidates) == 1
                         and sum(identity(row) == key for row in old[field]) == 1
                         and reviewed_adult(record, day)
                         and reviewed_adult(candidates[0], day))
            if permitted:
                authoritative = candidates[0]
                # Do not exchange an old review for a different DOB/source/name.
                permitted = all(field in authoritative and canonical(value) == canonical(authoritative[field])
                                for field, value in record.items() if field in EVIDENCE_FIELDS)
                if permitted:
                    preserve(record, authoritative)
            if not permitted:
                kept.append(record)
        if len(kept) != len(old[field]):
            baselines[path] = deepcopy(old)
            baselines[path][field] = kept
    return baselines
