"""Durable, descriptive calendar observations; never a wagering clearance source.

Only normalized public calendar fields are copied. A calendar's completed status
is not independent proof of the actual venue or actual start time.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json

CONTRACT = 'school-calendar-observations/v1'
FIELDS = ('id', 'uid', 'source_id', 'school_id', 'school', 'sport_id', 'sport',
          'season_id', 'opponent', 'date', 'start_time', 'date_only', 'time_unknown',
          'site', 'location', 'status', 'sequence', 'source_url', 'calendar_url',
          'provider_updated_at', 'event_type', 'result', 'score', 'publisher_event_id',
          'source_links', 'evidence_kind', 'historical_calendar_uid',
          'historical_calendar_source_id', 'calendar_link_status', 'calendar_location',
          'original_source_id', 'original_event_id')
REQUIRED = ('uid', 'source_id', 'school_id', 'school', 'sport_id', 'sport',
            'season_id', 'opponent', 'date', 'source_url', 'calendar_url', 'status')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def timestamp(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('History observation must have a timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def identity(facts):
    return digest([facts[k] for k in ('source_id', 'school_id', 'sport_id', 'season_id', 'uid')])


def facts_for(row, source_id):
    facts = {key: deepcopy(row[key]) for key in FIELDS if key in row}
    if any(not isinstance(facts.get(key), str) or not facts[key].strip() for key in REQUIRED):
        raise ValueError('Incomplete calendar history identity')
    if facts['source_id'] != source_id:
        raise ValueError('Calendar history source mismatch')
    date.fromisoformat(facts['date'])
    if facts['status'] not in ('CONFIRMED', 'TENTATIVE', 'CANCELLED', 'COMPLETED', 'REMOVED'):
        raise ValueError('Unsupported calendar history status')
    return facts


def validate(history, source_id):
    if not isinstance(history, dict) or set(history) != {'contract', 'observations'} or history['contract'] != CONTRACT:
        raise ValueError('Invalid calendar history contract')
    if not isinstance(history['observations'], list):
        raise ValueError('Invalid calendar history observations')
    previous = {}
    prior_records = {}
    for record in history['observations']:
        if set(record) != {'observation_id', 'previous_observation_id', 'event_key', 'observed_at',
                           'origin', 'kind', 'facts', 'changed_fields', 'venue_basis', 'actual_venue_verified'}:
            raise ValueError('Invalid calendar history record')
        body = {k: v for k, v in record.items() if k != 'observation_id'}
        facts = facts_for(record['facts'], source_id)
        if facts != record['facts'] or record['event_key'] != identity(facts):
            raise ValueError('Invalid calendar history facts')
        if record['previous_observation_id'] != previous.get(record['event_key']) or record['observation_id'] != digest(body):
            raise ValueError('Calendar history lineage mismatch')
        when = timestamp(record['observed_at'])
        prior_record = prior_records.get(record['event_key'])
        expected_changes = sorted(k for k in set(facts) | set(prior_record['facts'])
            if facts.get(k) != prior_record['facts'].get(k)) if prior_record else []
        if record['changed_fields'] != expected_changes:
            raise ValueError('Calendar history change summary mismatch')
        if prior_record and when < timestamp(prior_record['observed_at']):
            raise ValueError('Calendar history observation regressed')
        expected_basis = 'published-official-result-location' if facts.get('evidence_kind') == 'official-school-result' else 'published-calendar-location'
        if record['actual_venue_verified'] is not False or record['venue_basis'] != expected_basis:
            raise ValueError('Calendar history cannot verify actual venue')
        if record['origin'] not in ('legacy-cache', 'validated-calendar', 'validated-official-result', 'reviewed-result-cache') or record['kind'] not in ('published', 'removed', 'season-no-longer-current'):
            raise ValueError('Invalid calendar history provenance')
        previous[record['event_key']] = record['observation_id']
        prior_records[record['event_key']] = record
    return history


def update_history(previous_cache, result, source_id):
    """Retain every version across season rollover, TTL expiry and failed fetches.

    Legacy rows are captured only with their original cache timestamp, labelled
    as legacy-cache. Missing timestamps/stale rows cannot become new evidence.
    Repeated identical observations do not extend dates or append duplicates.
    """
    history = deepcopy(previous_cache.get('event_history', {'contract': CONTRACT, 'observations': []}))
    validate(history, source_id)
    records = history['observations']
    latest = {record['event_key']: record for record in records}

    def append(row, when, origin, kind):
        facts = facts_for(row, source_id)
        key = identity(facts)
        prior = latest.get(key)
        def semantic(value):
            return {k: v for k, v in value.items() if k not in ('sequence', 'provider_updated_at', 'source_links')}
        if prior and semantic(prior['facts']) == semantic(facts) and prior['kind'] == kind and prior['origin'] == origin:
            return
        when = timestamp(when)
        if prior and timestamp(prior['observed_at']) > when:
            raise ValueError('Calendar history observation regressed')
        body = {'previous_observation_id': prior['observation_id'] if prior else None,
                'event_key': key, 'observed_at': when, 'origin': origin, 'kind': kind,
                'facts': facts, 'changed_fields': sorted(k for k in set(facts) | set(prior['facts'])
                    if facts.get(k) != prior['facts'].get(k)) if prior else [],
                'venue_basis': 'published-official-result-location' if facts.get('evidence_kind') == 'official-school-result' else 'published-calendar-location', 'actual_venue_verified': False}
        record = {'observation_id': digest(body), **body}
        records.append(record)
        latest[key] = record

    # Bootstrap once. Never recapture old cached facts after a removal record.
    if not records and previous_cache.get('fetched_at'):
        for row in previous_cache.get('events', []):
            if not row.get('source_stale') and row.get('status') != 'REMOVED':
                try:
                    facts_for(row, source_id)
                    timestamp(previous_cache['fetched_at'])
                except (ValueError, TypeError):
                    continue  # Incomplete legacy rows are not invented evidence.
                append(row, previous_cache['fetched_at'], 'legacy-cache', 'published')
    status = result['source_status']
    if status.get('ok') and status.get('status') == 'current':
        observed_at = status['fetched_at']
        origin = result.get('history_origin', 'validated-calendar')
        for row in result['events']:
            if row.get('status') == 'REMOVED':
                append(row, row['removal_observed_at'], origin, 'removed')
            elif not row.get('source_stale'):
                append(row, observed_at, origin, 'published')
        # A season switch is not cancellation, completion, or proof of venue.
        season = result['cache'].get('season_id')
        for row in previous_cache.get('events', []) if origin == 'validated-calendar' else []:
            if row.get('season_id') != season and not row.get('source_stale'):
                try:
                    facts_for(row, source_id)
                except (ValueError, TypeError):
                    continue
                append(row, observed_at, 'validated-calendar', 'season-no-longer-current')
    validate(history, source_id)
    return history


# Measured as pretty JSON embedded three levels deep in the cache. Sixteen
# programs total <= 3.2 MB history, leaving room below the existing 5 MB
# private artifact ceiling. No eviction or implicit extension of this budget.
MAX_SOURCE_HISTORY_BYTES = 200_000


def capture_history(previous_cache, result, source_id):
    previous_cache = previous_cache or {}
    prior = deepcopy(previous_cache.get('event_history', {'contract': CONTRACT, 'observations': []}))
    degraded = previous_cache.get('history_capture', {}).get('capture_status') == 'degraded'
    legacy_gap_count = previous_cache.get('history_capture', {}).get('legacy_gap_count', 0)
    if not previous_cache.get('event_history'):
        for row in previous_cache.get('events', []):
            try:
                facts_for(row, source_id)
                timestamp(previous_cache.get('fetched_at'))
                if row.get('source_stale') or row.get('status') == 'REMOVED':
                    legacy_gap_count += 1
            except (ValueError, TypeError):
                legacy_gap_count += 1
    try:
        history = update_history(previous_cache, result, source_id)
        encoded = json.dumps(history, indent=2, ensure_ascii=False, allow_nan=False)
        size = len(encoded.encode()) + 6 * (encoded.count('\n') + 1)
        if size > MAX_SOURCE_HISTORY_BYTES:
            raise ValueError('History budget reached; existing observations retained, new capture paused')
        reason = 'Earlier capture gap remains; observations are not a complete event inventory' if degraded else 'Observed calendar versions only; no claim of complete historical coverage'
        state = {'source_id': source_id, 'capture_status': 'degraded' if degraded else 'recording',
                 'reason': reason, 'observation_count': len(history['observations']), 'legacy_gap_count': legacy_gap_count}
    except (ValueError, TypeError, KeyError):
        history = prior
        state = {'source_id': source_id, 'capture_status': 'degraded',
                 'reason': 'History capture unavailable or budget reached; prior history retained without eviction',
                 'observation_count': len(prior.get('observations', [])) if isinstance(prior, dict) else 0,
                 'legacy_gap_count': legacy_gap_count}
    result['cache']['event_history'] = history
    result['cache']['history_capture'] = state
    result['source_status']['history_capture_status'] = state['capture_status']
    return result


def project_history(caches, today, classify_location, window_days=90):
    """Export bounded dates, never mutate or expire saved source observations."""
    from datetime import timedelta
    start = (today - timedelta(days=window_days)).isoformat()
    end = today.isoformat()
    events, sources = [], []
    for source_id, cache in sorted(caches.items()):
        state = deepcopy(cache.get('history_capture', {'source_id': source_id,
            'capture_status': 'degraded', 'reason': 'Historical capture is not initialized', 'observation_count': 0}))
        history = cache.get('event_history', {'contract': CONTRACT, 'observations': []})
        try:
            validate(history, source_id)
        except (ValueError, TypeError, KeyError):
            state.update(capture_status='degraded', reason='Historical lineage failed validation')
            sources.append(state)
            continue
        sources.append(state)
        grouped = {}
        for observation in history['observations']:
            grouped.setdefault(observation['event_key'], []).append(observation)
        for key, observations in grouped.items():
            # Include all versions for an event if any date is inside the window,
            # so rescheduling cannot hide an earlier date or conflicting venue.
            if not any(start <= o['facts']['date'] <= end for o in observations):
                continue
            last = observations[-1]
            published = [o for o in observations if o['kind'] == 'published']
            if not published:
                continue
            evidence = published[-1]
            row = classify_location(evidence['facts'])
            conflicts = {f for o in observations for f in o['changed_fields']
                         if f in ('date', 'location', 'opponent', 'result', 'score')}
            conflicts.discard('result'); conflicts.discard('score')
            # Missing intermediate observations cannot erase a known change.
            for field in ('start_time', 'result', 'score'):
                known = {o['facts'].get(field) for o in observations if o['facts'].get(field)}
                if len(known) > 1:
                    conflicts.add(field)
            for before, after in zip(observations, observations[1:]):
                for field in ('result', 'score'):
                    if before['facts'].get(field) and after['facts'].get(field) and before['facts'][field] != after['facts'][field]:
                        conflicts.add(field)
                old_time, new_time = before['facts'].get('start_time'), after['facts'].get('start_time')
                if old_time and new_time and old_time != new_time:
                    conflicts.add('start_time')
                old_status, new_status = before['facts']['status'], after['facts']['status']
                if old_status != new_status and not (old_status in ('CONFIRMED', 'TENTATIVE') and new_status in ('CONFIRMED', 'COMPLETED')):
                    conflicts.add('status')
            conflicts = sorted(conflicts)
            row.update(archive_event_key=key, observation_id=evidence['observation_id'],
                       observed_at=evidence['observed_at'],
                       evidence_kind='recorded-official-school-result' if row.get('evidence_kind') == 'official-school-result' else 'recorded-official-calendar-result' if row['status'] == 'COMPLETED' else 'recorded-official-calendar-schedule',
                       actual_venue_verified=False, archive_latest_kind=last['kind'],
                       archive_conflict_fields=conflicts, observations=deepcopy(observations))
            events.append(row)
    return {'contract': 'school-calendar-history-projection/v1', 'window_start': start, 'window_end': end,
            'retention_note': '90-day review projection; source observations survive rollover within an explicit storage budget. Capture gaps and changes require review. Calendar venue is not independent actual-venue verification.',
            'sources': sources, 'events': sorted(events, key=lambda row: (row['date'], row['archive_event_key']))}


# Narrow recovery of the reviewed first-run capacity failure. These fingerprints
# bind factual rows from private commits ecffce6c563e53cca0f9118046a95b6de97ce778
# and 8b808fa75054416018755e9bb95aa57835841f1c. The only row-field difference is
# the uniform provider_updated_at below; no raw cache or operator data is stored.
OMAHA_BUDGET_RECOVERY = {
    'source_id': 'official-omaha-baseball', 'rows': 56,
    'old_fetched_at': '2026-11-09T18:45:36.631287+00:00',
    'current_fetched_at': '2026-11-10T00:22:56.676029+00:00',
    'current_next_fetch_at': '2026-11-10T02:22:56.676029+00:00',
    'old_provider_updated_at': '2026-11-09T18:45:47+00:00',
    'current_provider_updated_at': '2026-11-10T00:23:05+00:00',
    'old_facts_sha256': '319f8b98c0cd6a4b7802be8bada0a72b142267f3cf808f6ec3f191e2b28b6fd6',
    'current_facts_sha256': '4b7feadd0a26ba1de9a8f9abd7c55c8de866f7a85bd213145dc7d1123a87db3e',
}


def recover_reviewed_budget_failure(previous_cache, source_id):
    """Recover only the pinned empty Omaha ledger; preserve every other hold.

    This rebuilds two actually observed versions, never a new observation. The
    existing current cache, timestamps, polling deadline and live rows are kept.
    Any later input change or uncertainty makes this a no-op requiring review.
    """
    pin = OMAHA_BUDGET_RECOVERY
    if source_id != pin['source_id'] or not isinstance(previous_cache, dict):
        return previous_cache
    state = previous_cache.get('history_capture')
    expected_state = {'source_id': source_id, 'capture_status': 'degraded',
        'reason': 'History capture unavailable or budget reached; prior history retained without eviction',
        'observation_count': 0, 'legacy_gap_count': 0}
    if (state != expected_state or previous_cache.get('event_history') != {'contract': CONTRACT, 'observations': []}
            or previous_cache.get('source_id') != source_id
            or previous_cache.get('fetched_at') != pin['current_fetched_at']
            or previous_cache.get('next_fetch_at') != pin['current_next_fetch_at']
            or previous_cache.get('retry_after') or previous_cache.get('last_error')):
        return previous_cache
    try:
        events = previous_cache.get('events', [])
        if len(events) != pin['rows'] or any(row.get('source_stale') for row in events):
            return previous_cache
        current = sorted((facts_for(row, source_id) for row in events), key=lambda row: row['uid'])
        if digest(current) != pin['current_facts_sha256'] or any(
                row.get('provider_updated_at') != pin['current_provider_updated_at'] for row in current):
            return previous_cache
        original = [{**row, 'provider_updated_at': pin['old_provider_updated_at']} for row in current]
        if digest(original) != pin['old_facts_sha256']:
            return previous_cache
        old_cache = {'source_id': source_id, 'season_id': previous_cache['season_id'],
                     'events': original, 'fetched_at': pin['old_fetched_at']}
        wrapper = {'events': events, 'cache': deepcopy(previous_cache),
                   'source_status': {'ok': True, 'status': 'current',
                                     'fetched_at': pin['current_fetched_at']}}
        recovered = capture_history(old_cache, wrapper, source_id)['cache']
        if (recovered['history_capture']['capture_status'] != 'recording'
                or len(recovered['event_history']['observations']) != pin['rows'] * 2):
            return previous_cache
        return recovered
    except (ValueError, TypeError, KeyError):
        return previous_cache
