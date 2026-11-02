"""Bounded owner-provided SharpAPI access evidence, never fixture approval.

Only normal publication calls this. A saved attempt receipt suppresses further
attempts for 24 hours; a discarded publication cannot retain that receipt.
"""
import datetime as dt
import json
import re
try:
    from .api_sports_nba_preflight import TEAM_NAMES, aware
    from .preflight_diagnostics import PreflightError, record_failure, restore_failure, validate_quota
except ImportError:
    from api_sports_nba_preflight import TEAM_NAMES, aware
    from preflight_diagnostics import PreflightError, record_failure, restore_failure, validate_quota

BASE = "https://api.sharpapi.io/api/v1"
SOURCE_ID = "sharp-api-events-preflight"
PARAMS = {"sport": "basketball,football", "league": "nba,nfl", "status": "upcoming",
          "is_live": "false", "limit": 200, "offset": 0}
NFL_TEAMS = frozenset(("Arizona Cardinals|Atlanta Falcons|Baltimore Ravens|Buffalo Bills|Carolina Panthers|Chicago Bears|Cincinnati Bengals|Cleveland Browns|Dallas Cowboys|Denver Broncos|Detroit Lions|Green Bay Packers|Houston Texans|Indianapolis Colts|Jacksonville Jaguars|Kansas City Chiefs|Las Vegas Raiders|Los Angeles Chargers|Los Angeles Rams|Miami Dolphins|Minnesota Vikings|New England Patriots|New Orleans Saints|New York Giants|New York Jets|Philadelphia Eagles|Pittsburgh Steelers|San Francisco 49ers|Seattle Seahawks|Tampa Bay Buccaneers|Tennessee Titans|Washington Commanders").split("|"))
UTC = dt.timezone.utc


def integer(value, low=0, high=100000):
    return type(value) is int and low <= value <= high


def inspect_events(payload, now):
    if not isinstance(payload, dict) or payload.get("error") or payload.get("errors"):
        raise PreflightError("sharp_provider_rejected")
    rows = payload.get("data"); page = payload.get("pagination")
    if isinstance(rows, list) and not rows:
        raise PreflightError("sharp_rows_empty")
    if not isinstance(rows, list) or not 0 < len(rows) <= 200 or not isinstance(page, dict):
        raise PreflightError("sharp_rows_invalid")
    if page.get("limit") != 200 or type(page.get("limit")) is not int or page.get("offset") != 0 or type(page.get("offset")) is not int or page.get("count") != len(rows) or type(page.get("count")) is not int or not integer(page.get("total"), len(rows)):
        raise PreflightError("sharp_page_mismatch")
    more = page.get("has_more")
    if type(more) is not bool or more != (page["total"] > len(rows)) or (more and page.get("next_offset") != 200) or (not more and page.get("next_offset") is not None):
        raise PreflightError("sharp_page_state_changed")
    try:
        updated = aware(payload.get("updated_at"))
    except (ValueError, TypeError):
        raise PreflightError("sharp_updated_invalid") from None
    if not now - dt.timedelta(hours=24) <= updated <= now + dt.timedelta(minutes=5):
        raise PreflightError("sharp_updated_stale")
    seen = set(); uuids = set(); previews = []; counts = {"nba": 0, "nfl": 0}; phases = {}
    for row in rows:
        if not isinstance(row, dict):
            raise PreflightError("sharp_row_invalid")
        eid = row.get("id"); uuid = row.get("uuid"); league = row.get("league")
        if not isinstance(eid, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", eid) or eid in seen or not isinstance(uuid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", uuid) or uuid in uuids:
            raise PreflightError("sharp_identity_ambiguous")
        seen.add(eid); uuids.add(uuid)
        if league not in counts or row.get("sport") != {"nba": "basketball", "nfl": "football"}[league] or row.get("status") != "upcoming" or row.get("is_live") is not False:
            raise PreflightError("sharp_scope_changed")
        names = TEAM_NAMES if league == "nba" else NFL_TEAMS
        home = row.get("home_team"); away = row.get("away_team")
        if home not in names or away not in names or home == away:
            raise PreflightError("sharp_participant_unverified")
        phase = row.get("season_type")
        if phase not in (None, "Preseason", "Regular Season"):
            raise PreflightError("sharp_phase_unrecognized")
        try:
            when = aware(row.get("start_time"))
        except (ValueError, TypeError):
            raise PreflightError("sharp_start_invalid") from None
        # A delayed feed may retain a recently started upcoming row. Record only
        # genuinely future observations; do not infer completion from its absence.
        if when < now - dt.timedelta(days=1) or when > now + dt.timedelta(days=370):
            raise PreflightError("sharp_date_outside_bounds")
        counts[league] += 1
        phases[league + ":" + (phase or "unknown")] = phases.get(league + ":" + (phase or "unknown"), 0) + 1
        if now < when <= now + dt.timedelta(days=8):
            previews.append({"provider_event_id": eid, "provider_uuid": uuid, "league": league,
                "home_team": home, "away_team": away, "start_time": when.isoformat(), "season_type": phase})
    return {"response_updated_at": updated.isoformat(), "sample_complete": not more,
            "response_events": len(rows), "reported_total": page["total"], "league_counts": counts,
            "phase_counts": phases, "schedule_preview": previews,
            "note": "Access evidence only. Unknown phase stays held; no venue or age clearance inferred."}


def collect(source, previous, now, key, get):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("SharpAPI preflight requires an aware clock")
    now = now.astimezone(UTC)
    result = {**source, "approved_catalog": True, "ok": False, "events": 0,
              "coverage_complete": False, "review_required": True, "requests_this_run": 0,
              "errors": ["SharpAPI connection pending current event and fixture-scope review"],
              "checked_at": previous.get("checked_at")}
    if source.get("id") != SOURCE_ID or source.get("source_type") != SOURCE_ID or source.get("endpoint") != BASE + "/events" or source.get("coverage_status") != "pending-fixture-review":
        result["errors"] = ["SharpAPI configuration changed; no request made"]; return result
    if previous.get("api_attempted_at"):
        try:
            attempted = aware(previous["api_attempted_at"])
        except (TypeError, ValueError):
            result["errors"] = ["SharpAPI previous receipt invalid; no request made"]; return result
        if now < attempted or now - attempted < dt.timedelta(hours=24):
            for field in ("api_attempted_at", "preflight_evidence", "api_http_status", "quota_limit", "quota_remaining"):
                if field in previous: result[field] = previous[field]
            restore_failure(result, previous)
            return result
    if not isinstance(key, str) or not key or key != key.strip() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        result["errors"] = ["SHARP_API_KEY unavailable or invalid; no request made"]; return result
    result["api_attempted_at"] = now.isoformat()
    stage = "account_request"
    def request(path, params=None):
        nonlocal stage
        prefix = "account" if path == "/account" else "schedule"
        stage = prefix + "_request"
        result["requests_this_run"] += 1
        response = get(BASE + path, params=params, headers={"X-API-Key": key}, timeout=25, allow_redirects=False)
        result["api_http_status"] = response.status_code
        if response.status_code != 200:
            raise PreflightError("http_rejected")
        stage = prefix + "_quota"
        limit, remaining = validate_quota(response.headers, "x-ratelimit-limit", "x-ratelimit-remaining", 12)
        result.update(quota_limit=limit, quota_remaining=remaining)
        stage = prefix + "_json"
        return response.json()
    try:
        account = request("/account")
        stage = "account_validation"
        data = account.get("data") if isinstance(account, dict) else None
        if not isinstance(data, dict) or data.get("tier") != "free" or (data.get("rate_limit") or {}).get("requests_per_minute") != 12 or (data.get("rate_limit") or {}).get("max_books") != 2 or "schedule" not in data.get("features", []):
            raise PreflightError("sharp_account_unverified")
        if result['quota_remaining'] == 0:
            stage = 'account_quota'
            raise PreflightError('quota_exhausted')
        payload = request("/events", dict(PARAMS))
        stage = "schedule_validation"
        evidence = inspect_events(payload, now)
        stage = "credential_check"
        if key in json.dumps(evidence):
            raise PreflightError("sharp_credential_reflected")
        result["preflight_evidence"] = {"tier": "free", **evidence}
        result["checked_at"] = now.isoformat()
    except PreflightError as error:
        record_failure(result, stage, error.code)
    except Exception:
        # Never persist raw account details, API error text, headers, URL or exceptions.
        code = 'transport_failed' if stage.endswith('_request') else 'json_invalid' if stage.endswith('_json') else 'validation_unexpected'
        record_failure(result, stage, code)
    return result
