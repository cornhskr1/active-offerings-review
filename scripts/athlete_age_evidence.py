"""Durable athlete identity and reviewed age evidence, independent of refresh dates.

The immutable review object records the source check; generated_at and a new
ranking observation must never replace it. Age classifications are derived at a
specified date, and historical identities remain available after they turn 18.
"""
from copy import deepcopy
from datetime import date
import calendar
import re


def name_key(value):
    value = re.sub(r"[\u2018\u2019'`]", "", str(value or "").lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def identity(record):
    if record.get("official_player_id"):
        return record["official_player_id"]
    for url in (record.get("source_url"), record.get("profile_url")):
        match = re.search(r"/players/[^/]+/(\d{6,})(?:/|$)", str(url or ""), re.I)
        if match:
            return "itf:" + match.group(1)
    return "name:" + name_key(record.get("name") or record.get("athlete"))


def reviewed(record):
    return bool((record.get("age_evidence") or {}).get("review", {}).get("id"))


def iso_date(value):
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def age_on(record, on_date):
    evidence = record.get("age_evidence") or {}
    if evidence.get("status") != "verified_dob":
        return None
    dob, target = iso_date(evidence.get("dob")), iso_date(on_date)
    if not dob or not target or target < dob:
        return None
    # The legal birthday convention is jurisdiction-dependent for leap-day
    # births. Escalate the one ambiguous eighteenth-anniversary boundary.
    if (dob.month, dob.day) == (2, 29) and target.year == dob.year + 18 and \
            not calendar.isleap(target.year) and (target.month, target.day) == (2, 28):
        return None
    return target.year - dob.year - ((target.month, target.day) < (dob.month, dob.day))


def age_status_on(record, on_date):
    """Legacy classifications remain compatible until explicit evidence exists."""
    evidence = record.get("age_evidence")
    if evidence:
        age = age_on(record, on_date)
        if age is not None:
            return "VERIFIED U18" if age < 18 else "VERIFIED 18+"
        return "TARGETED REVIEW"
    return record.get("age_status") or record.get("status") or "UNRESOLVED"


REVIEWED_FIELDS = (
    "name", "athlete", "canonical_name", "official_player_id", "age_evidence",
    "dob", "birth_year", "age", "age_as_of", "age_status", "status", "age_label",
    "source", "source_url", "profile_url", "evidence", "last_verified",
    "verification_method",
)


def reconcile_review_conflicts(result, records):
    """Conflicting reviewed dates never depend on input ordering or field count."""
    evidence = [row['age_evidence'] for row in records if reviewed(row)]
    dates = {item.get('dob') for item in evidence
             if item.get('status') == 'verified_dob' and iso_date(item.get('dob'))}
    if len(dates) < 2 and not any(item.get('status') == 'conflicting_dob' for item in evidence):
        return result
    candidates = {}
    sources = {}
    for item in evidence:
        urls = [source['url'] for source in item.get('sources') or [] if source.get('url')]
        for source in item.get('sources') or []:
            if source.get('url'):
                sources[source['url']] = deepcopy(source)
        if iso_date(item.get('dob')):
            candidates.setdefault(item['dob'], set()).update(urls)
        for candidate in item.get('candidate_dobs') or []:
            if iso_date(candidate.get('dob')):
                candidates.setdefault(candidate['dob'], set()).update(candidate.get('source_urls') or [])
    # Retain the actual prior review date and provenance, never the run date.
    base = max(evidence, key=lambda item: (item.get('status') == 'conflicting_dob',
                                          item.get('checked_at') or ''))
    merged = deepcopy(base)
    merged.pop('dob', None)
    merged['status'] = 'conflicting_dob'
    merged['sources'] = [sources[key] for key in sorted(sources)]
    merged['candidate_dobs'] = [{'dob': dob, 'source_urls': sorted(urls)}
                               for dob, urls in sorted(candidates.items())]
    merged.setdefault('review', {})['merged_review_ids'] = sorted({
        item['review']['id'] for item in evidence if item.get('review', {}).get('id')})
    result['age_evidence'] = merged
    for field in ('dob', 'age', 'birth_year', 'age_as_of'):
        result[field] = None
    result['age_status'] = 'TARGETED REVIEW'
    if 'status' in result:
        result['status'] = 'TARGETED REVIEW'
    if 'age_label' in result:
        result['age_label'] = 'DOB review needed'
    return result


def merge_refresh_record(previous, incoming):
    """Merge an automated observation without overwriting a completed review.

    This does not claim a new evidence check. New profile/ranking observations
    can update operational fields, but a change to reviewed evidence requires a
    deliberate review. Aliases are never lost, including the incoming name.
    """
    previous, incoming = previous or {}, incoming or {}
    result = {**deepcopy(previous), **deepcopy(incoming)}
    if reviewed(previous):
        for key in REVIEWED_FIELDS:
            if key in previous:
                result[key] = deepcopy(previous[key])
            else:
                result.pop(key, None)
    names = [previous.get("name"), incoming.get("name"),
             *(previous.get("aliases") or []), *(incoming.get("aliases") or [])]
    canonical = result.get("name") or result.get("athlete")
    aliases = {str(x).strip() for x in names if x and name_key(x) != name_key(canonical)}
    if aliases:
        result["aliases"] = sorted(aliases, key=str.lower)
    return reconcile_review_conflicts(result, [previous, incoming])


def merge_records(records, exposure_names=None):
    """Merge exact names/recorded aliases only when official IDs do not conflict."""
    rows = [dict(r) for r in records or [] if r and (r.get("name") or r.get("athlete"))]
    names_to_ids = {}
    for row in rows:
        key = identity(row)
        if not key.startswith("name:"):
            for name in [row.get("name") or row.get("athlete"), *(row.get("aliases") or [])]:
                names_to_ids.setdefault(name_key(name), set()).add(key)
    groups = {}
    for row in rows:
        key = identity(row)
        if key.startswith("name:"):
            matches = names_to_ids.get(name_key(row.get("name") or row.get("athlete")), set())
            if len(matches) == 1:
                key = next(iter(matches))
        groups.setdefault(key, []).append(row)
    output = []
    for key, group in groups.items():
        names = []
        for row in group:
            for value in [row.get("name") or row.get("athlete"), *(row.get("aliases") or [])]:
                if not value:
                    continue
                value = str(value).strip()
                names.append(value)
                stripped = re.sub(r"\s*\((?:WC|Q|LL|ALT)\)\s*$", "", value, flags=re.I).strip()
                if stripped != value:
                    names.append(stripped)
        def name_score(value):
            return (not bool(re.search(r"\s*\((?:WC|Q|LL|ALT)\)\s*$", value, re.I)),
                    not bool(re.search(r"(?:^|\s)[A-Za-z]\.?(?:\s|$)", value)),
                    len(value.split()), len(value))
        reviewed_rows = [row for row in group if reviewed(row)]
        canonical = ((reviewed_rows[0].get("canonical_name") or reviewed_rows[0].get("name")
                      or reviewed_rows[0].get("athlete")) if reviewed_rows else max(names, key=name_score))
        # Start with the best durable record; merge preserves its review fields.
        ordered = sorted(group, key=lambda row: (reviewed(row),
                         {"conflicting_dob": 3, "verified_dob": 2, "age_only": 1}.get(
                             (row.get("age_evidence") or {}).get("status"), 0),
                         (row.get("age_evidence") or {}).get("checked_at") or "",
                         name_key(row.get("name")) == name_key(canonical),
                         sum(v not in (None, "", [], {}) for v in row.values())), reverse=True)
        combined = deepcopy(ordered[0])
        for row in ordered[1:]:
            if reviewed(combined):
                combined = merge_refresh_record(combined, row)
            else:
                for field, value in row.items():
                    if combined.get(field) in (None, "", [], {}) and value not in (None, "", [], {}):
                        combined[field] = deepcopy(value)
        combined = reconcile_review_conflicts(combined, group)
        combined["name"] = canonical
        if not key.startswith("name:"):
            combined["official_player_id"] = key
        aliases = {name for name in names if name_key(name) != name_key(canonical)}
        if aliases:
            combined["aliases"] = sorted(aliases, key=str.lower)
        else:
            combined.pop("aliases", None)
        if exposure_names is not None:
            combined["current_exposure"] = any(name_key(name) in exposure_names for name in names)
        output.append(combined)
    return sorted(output, key=lambda row: (not row.get("current_exposure"), row["name"].lower()))


def partition_registry(records, on_date, exposure_names=None):
    """Keep a durable identity set plus date-specific backward-compatible views."""
    durable = merge_records(records, exposure_names)
    current, targeted = [], []
    for record in durable:
        status = age_status_on(record, on_date)
        if status == "VERIFIED U18":
            current.append(record)
        elif status in ("TARGETED REVIEW", "UNRESOLVED"):
            targeted.append(record)
    return durable, current, targeted


def stable_id_conflict(one, two):
    first, second = identity(one), identity(two)
    return (not first.startswith("name:") and not second.startswith("name:")
            and first != second)


def index_records(records):
    """A shared alias across distinct official IDs is an identity review."""
    output = {}
    for record in records or []:
        for name in [record.get('name') or record.get('athlete'), *(record.get('aliases') or [])]:
            if not name:
                continue
            key = name_key(name)
            previous = output.get(key)
            if previous and (previous.get('identity_review_required') or stable_id_conflict(previous, record)):
                ids = set(previous.get('identity_candidates') or [identity(previous)]) | {identity(record)}
                output[key] = {'name': name, 'age_status': 'TARGETED REVIEW',
                               'identity_review_required': True, 'identity_candidates': sorted(ids),
                               'age_evidence': {'status': 'unknown', 'sources': []}}
            else:
                output[key] = record
    return output


def update_cache(cache, incoming):
    """Protect reviews across aliases, without crossing conflicting player IDs."""
    key = name_key(incoming.get("name"))
    candidates = []
    for old in cache.values():
        if stable_id_conflict(old, incoming):
            continue
        if identity(old) == identity(incoming) or key in {
                name_key(x) for x in [old.get("name"), *(old.get("aliases") or [])]}:
            candidates.append(old)
    candidate_ids = {identity(row) for row in candidates if not identity(row).startswith("name:")}
    if identity(incoming).startswith("name:") and len(candidate_ids) > 1:
        # A shared abbreviation is not a unique identity. Preserve both people
        # and store only an unresolved observation, never either person's DOB.
        result = deepcopy(incoming)
        result.update({"age": None, "dob": None, "age_status": "TARGETED REVIEW",
                       "identity_review_required": True, "identity_candidates": sorted(candidate_ids),
                       "age_evidence": {"status": "unknown", "sources": []}})
        slot = key if key not in cache else "unresolved:" + key
        cache[slot] = result
        return result
    match = cache.get(key)
    if match and stable_id_conflict(match, incoming):
        match = None
    reviewed_candidates = [row for row in candidates if reviewed(row)]
    if reviewed_candidates:
        match = merge_records(reviewed_candidates)[0]
    result = merge_refresh_record(match, incoming)
    canonical_key = name_key(result.get("name"))
    if canonical_key in cache and stable_id_conflict(cache[canonical_key], result):
        # Same display name is not proof of identity; retain both identities.
        canonical_key = identity(result)
    cache[canonical_key] = result
    for old_key, old in list(cache.items()):
        if stable_id_conflict(old, result):
            continue
        if old_key != canonical_key and (identity(old) == identity(result) or
                old_key in {name_key(x) for x in result.get("aliases") or []}):
            cache[old_key] = result
    return result
