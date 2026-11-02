"""Small, closed vocabulary for pending-provider failures; never store raw errors.

These receipts are diagnostics only. They do not authorize a source, emit events,
change retry budgets, or establish that an empty schedule is out of season.
"""
ERRORS = {
    'transport_failed': 'Request failed before a response was available; no retry',
    'http_rejected': 'HTTP response rejected; no redirect or retry',
    'json_invalid': 'Response was not readable JSON; no retry',
    'validation_unexpected': 'Response structure could not be validated; no retry',
    'quota_headers_missing': 'Required free-plan quota headers are missing; no retry',
    'quota_headers_malformed': 'Required free-plan quota headers are not decimal integers; no retry',
    'quota_limit_outside_free_range': 'Reported quota limit is outside the permitted free-plan range; no retry',
    'quota_remaining_inconsistent': 'Reported quota remaining is inconsistent with the request limit; no retry',
    'quota_exhausted': 'Free-plan request allowance is exhausted; no event request made',
    'nba_provider_rejected': 'NBA API rejected the request; current-season access unverified',
    'nba_query_changed': 'NBA response query identity changed',
    'nba_rows_invalid': 'NBA response rows or count are malformed',
    'nba_rows_empty': 'NBA response contains no games; season and access remain unverified',
    'nba_identity_changed': 'NBA game identity or season changed',
    'nba_start_invalid': 'NBA game start is invalid or lacks an explicit timezone',
    'nba_date_outside_season': 'NBA game is outside the requested season',
    'nba_state_unrecognized': 'NBA phase or state is unrecognized',
    'nba_participant_unverified': 'NBA senior club identity is unverified',
    'nba_participant_duplicate': 'NBA game has duplicate participants',
    'nba_window_empty': 'NBA current review-window observations are unavailable',
    'sharp_account_unverified': 'SharpAPI free account or schedule feature is unverified',
    'sharp_provider_rejected': 'SharpAPI rejected the event response',
    'sharp_rows_invalid': 'SharpAPI response rows or pagination are malformed',
    'sharp_rows_empty': 'SharpAPI returned no events; season status remains undetermined by this response',
    'sharp_page_mismatch': 'SharpAPI pagination counts do not match the requested page',
    'sharp_page_state_changed': 'SharpAPI pagination state changed',
    'sharp_updated_invalid': 'SharpAPI update time is invalid or lacks an explicit timezone',
    'sharp_updated_stale': 'SharpAPI response is stale or future dated',
    'sharp_row_invalid': 'SharpAPI event row is malformed',
    'sharp_identity_ambiguous': 'SharpAPI event identity is ambiguous',
    'sharp_scope_changed': 'SharpAPI event scope or state changed',
    'sharp_participant_unverified': 'SharpAPI senior participant is unverified',
    'sharp_phase_unrecognized': 'SharpAPI phase is unrecognized',
    'sharp_start_invalid': 'SharpAPI event start is invalid or lacks an explicit timezone',
    'sharp_date_outside_bounds': 'SharpAPI event date is outside capability bounds',
    'sharp_credential_reflected': 'SharpAPI response reflects a credential; evidence withheld',
    'legacy_nba_quota_unverified': 'NBA free-plan quota headers unverified',
    'legacy_nba_validation_failed': 'NBA preflight transport or response validation failed; no retry',
    'legacy_sharp_validation_failed': 'SharpAPI account, transport or event validation failed; no retry',
}
STAGES = frozenset(('schedule_request', 'schedule_quota', 'schedule_json',
                    'schedule_validation', 'account_request', 'account_quota',
                    'account_json', 'account_validation', 'credential_check', 'legacy'))


class PreflightError(ValueError):
    def __init__(self, code):
        # Only our static codes can cross the publication boundary.
        self.code = code if code in ERRORS else 'validation_unexpected'
        super().__init__(ERRORS[self.code])


def record_failure(result, stage, code):
    stage = stage if stage in STAGES else 'schedule_validation'
    code = code if code in ERRORS else 'validation_unexpected'
    result['preflight_diagnostic'] = {'version': 1, 'stage': stage, 'code': code}
    result['errors'] = [ERRORS[code]]


def restore_failure(result, previous):
    """Keep the cause during cooldown, reconstructing text from trusted constants."""
    diagnostic = previous.get('preflight_diagnostic')
    if isinstance(diagnostic, dict) and type(diagnostic.get('version')) is int and diagnostic['version'] == 1:
        stage, code = diagnostic.get('stage'), diagnostic.get('code')
        if isinstance(stage, str) and stage in STAGES and isinstance(code, str) and code in ERRORS:
            record_failure(result, stage, code)
            return
    # Old receipts lack a code. Preserve only exact known failures, never raw text.
    for code in ('legacy_nba_quota_unverified', 'legacy_nba_validation_failed', 'legacy_sharp_validation_failed'):
        if previous.get('errors') == [ERRORS[code]]:
            record_failure(result, 'legacy', code)
            return


def validate_quota(headers, limit_name, remaining_name, maximum):
    """Classify the failure without publishing any header names or raw values."""
    lowered = {str(name).lower(): value for name, value in headers.items()}
    limit, remaining = lowered.get(limit_name), lowered.get(remaining_name)
    if limit is None or remaining is None or limit == '' or remaining == '':
        raise PreflightError('quota_headers_missing')
    if not str(limit).isascii() or not str(remaining).isascii() or not str(limit).isdigit() or not str(remaining).isdigit():
        raise PreflightError('quota_headers_malformed')
    # Bound parsing work as well as the accepted quota; long numeric strings are
    # never retained. The provider limits here are at most three decimal digits.
    if len(str(limit)) > 9 or not 1 <= int(limit) <= maximum:
        raise PreflightError('quota_limit_outside_free_range')
    if len(str(remaining)) > 9 or not 0 <= int(remaining) < int(limit):
        raise PreflightError('quota_remaining_inconsistent')
    return int(limit), int(remaining)
