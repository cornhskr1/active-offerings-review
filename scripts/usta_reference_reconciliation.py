#!/usr/bin/env python3
"""Fail-closed, reference-only links between reviewed USTA rows and ITF events.

``reconcile_usta_references`` returns ``(events, sources)`` as deep copies. It
never creates events, changes canonical fields, grants approval, or promotes a
USTA coverage gap. Only its owned ``calendar_references`` entries and the USTA
source reference metadata listed in ``SOURCE_FIELDS`` are rebuilt.

Manifest schema (all dates are ISO dates; reviewed_at must have a UTC offset):
    reviewed_at: UTC ISO timestamp
    calendars: {men|women: {source_id: USTA source ID, url: HTTPS USTA PDF,
                            sha256: reviewed byte digest, published_revision: str}}
    references: [{calendar: men|women, source_id: canonical ITF source ID,
                  source_url: exact ITF fact-sheet URL, tour_id, gender,
                  tournament: exact ITF name, start_date, end_date, level,
                  week_start: USTA Monday, usta_row: reviewed USTA row text}]

USTA publishes the week, grade and row, NOT the ITF end date. Dates in
``itf_tournament`` are matching guards attributed only to the underlying ITF
snapshot. This is an explicit reviewed crosswalk, not a PDF parser or a circuit
coverage claim. Updating the PDF invalidates its crosswalk until reviewed again.
The optional ``get`` accepts requests.get-compatible keyword arguments and
returns an object with status_code/content (and optionally url). Each distinct
PDF URL is requested at most once, without redirects or retries.
"""

from collections import Counter
try:
    from publisher_access_policy import permission_hold_reason
except ModuleNotFoundError:
    from scripts.publisher_access_policy import permission_hold_reason

from copy import deepcopy
import datetime as dt
import hashlib
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

OWNER = "usta_reference_reconciliation"
CHICAGO = ZoneInfo("America/Chicago")
MAX_AGE = dt.timedelta(hours=24)
LANES = {
    "men": ("tennis-usta-pro-circuit-men", "tennis-itf-world-tour-men", "itf-men", "MEN", "m"),
    "women": ("tennis-usta-pro-circuit-women", "tennis-itf-world-tour-women", "itf-women", "WOMEN", "w"),
}
SOURCE_FIELDS = (
    "reference_owner", "crosslisted_reference_count", "crosslisted_event_ids",
    "reference_status", "reference_errors", "reference_note", "reference_checked_at",
)
NOTE = (
    "Reviewed tournament cross-list references only. USTA remains a manual "
    "coverage gap with no independently collected events; these references do "
    "not establish circuit-wide or match-level coverage, new approval, or "
    "participant-age clearance."
)


def _timestamp(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _date(value):
    try:
        return dt.date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _fresh(value, now):
    checked = _timestamp(value)
    return checked is not None and dt.timedelta(0) <= now - checked <= MAX_AGE


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _event_id(row):
    return f'{row["source_id"]}-{row["start_date"]}-{_slug(row["tournament"])}'


def _pdf_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.netloc in ("www.usta.com", "usta.com")
                and not parsed.query and not parsed.fragment
                and parsed.path.startswith("/content/dam/usta/pro-circuit/")
                and parsed.path.endswith(".pdf"))
    except (TypeError, ValueError):
        return False


def _row_issue(row, lane, today, last_day):
    """Validate the reviewed identity without fuzzy city or date matching."""
    if not isinstance(row, dict):
        return "INVALID_REVIEWED_ROW"
    _, source_id, tour_id, gender, prefix = LANES[lane]
    if (row.get("source_id"), row.get("tour_id"), row.get("gender")) != (source_id, tour_id, gender):
        return "REVIEWED_LANE_MISMATCH"
    name, level = row.get("tournament"), row.get("level")
    if not isinstance(name, str) or not name or name != " ".join(name.split()):
        return "INVALID_TOURNAMENT_NAME"
    if not isinstance(level, str) or not re.fullmatch(prefix.upper() + r"\d+", level):
        return "INVALID_REVIEWED_LEVEL"
    if not name.startswith(level + " "):
        return "REVIEWED_LEVEL_MISMATCH"
    start, end, week = (_date(row.get(k)) for k in ("start_date", "end_date", "week_start"))
    if not start or not end or not week or start > end:
        return "INVALID_REVIEWED_DATES"
    # The explicit reviewed Monday must match, but end dates always come
    # from ITF. Do not synthesize an end date from a seven-day USTA week.
    if week.weekday() != 0 or week != start:
        return "REVIEWED_WEEK_MISMATCH"
    if end < today:
        return "EXPIRED_REVIEWED_ROW"
    if start > last_day:
        return "REVIEWED_ROW_OUTSIDE_WINDOW"
    if not isinstance(row.get("usta_row"), str) or not row["usta_row"].strip():
        return "MISSING_REVIEWED_USTA_ROW"
    try:
        url = urlsplit(row.get("source_url"))
        expected = rf"/en/tournament/[^/]+/usa/{start.year}/{prefix}-itf-usa-{start.year}-\d+/fact-sheet/"
        if (url.scheme != "https" or url.netloc != "www.itftennis.com"
                or url.query or url.fragment or not re.fullmatch(expected, url.path)):
            return "REVIEWED_EDITION_OR_URL_MISMATCH"
    except (TypeError, ValueError):
        return "INVALID_ITF_URL"
    return None


def _pdf_issue(calendar, get, cache):
    url, expected = calendar.get("url"), calendar.get("sha256")
    if permission_hold_reason(url):
        return "PERMISSION_REQUIRED"
    if (not _pdf_url(url) or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or not isinstance(calendar.get("published_revision"), str)
            or not calendar["published_revision"].strip()):
        return "INVALID_REVIEWED_CALENDAR"
    if url not in cache:
        try:
            response = get(url, timeout=25, allow_redirects=False,
                           headers={"User-Agent": "ActiveOfferingsReview/1.0 (public calendar reference)"})
            status = response.status_code
            if status != 200:
                suffix = "_ACCESS_DENIED" if status in (401, 403, 429) else ""
                cache[url] = (f"PDF_HTTP_{status}{suffix}", None)
            elif isinstance(getattr(response, "url", None), str) and response.url != url:
                cache[url] = ("PDF_URL_CHANGED", None)
            elif not isinstance(response.content, bytes) or not response.content.startswith(b"%PDF-"):
                cache[url] = ("PDF_INVALID_BYTES", None)
            else:
                cache[url] = (None, hashlib.sha256(response.content).hexdigest())
        except Exception as exc:  # Optional evidence must not break canonical collection.
            cache[url] = (f"PDF_FETCH_FAILED:{type(exc).__name__}", None)
    issue, actual = cache[url]
    return issue or ("PDF_SHA256_CHANGED" if actual != expected else None)


def _payload_issue(payload, now, today, last_day):
    if not isinstance(payload, dict) or not _fresh(payload.get("generated_at"), now):
        return "TENNIS_PAYLOAD_STALE_OR_INVALID"
    if payload.get("source_stale"):
        return "TENNIS_PAYLOAD_MARKED_STALE"
    if (payload.get("window_start"), payload.get("window_end")) != (today.isoformat(), last_day.isoformat()):
        return "TENNIS_PAYLOAD_WINDOW_MISMATCH"
    quality = payload.get("quality_gate") or {}
    if not isinstance(quality, dict) or quality.get("passed") is False or quality.get("critical_issues"):
        return "TENNIS_QUALITY_GATE_FAILED"
    if not isinstance(payload.get("tournaments"), list):
        return "TENNIS_TOURNAMENTS_INVALID"
    return None


def _lane_issue(payload, canonical_sources, tour_id, now):
    if len(canonical_sources) != 1:
        return "CANONICAL_SOURCE_MISSING_OR_AMBIGUOUS"
    source = canonical_sources[0]
    if (source.get("approved_catalog") is not True or source.get("ok") is not True
            or source.get("source_stale") or source.get("errors")
            or source.get("source_type") != "tennis-intelligence"
            or tour_id not in (source.get("tour_ids") or [])
            or not _fresh(source.get("checked_at"), now)):
        return "CANONICAL_SOURCE_STALE_OR_UNHEALTHY"
    quality = payload.get("quality_gate") or {}
    if not isinstance(quality, dict):
        return "TENNIS_QUALITY_GATE_INVALID"
    for degraded in quality.get("degraded_lanes") or []:
        if isinstance(degraded, dict) and degraded.get("tour_id") == tour_id:
            return "TENNIS_LANE_DEGRADED"
    # Some callers supply the fuller tennis-intelligence snapshot instead of
    # tennis-schedule; honor its lane health without conflating unrelated tours.
    health = (payload.get("source_health") or {}).get(tour_id.replace("-", "_"))
    if isinstance(health, dict) and (health.get("ok") is False or health.get("error") or health.get("source_stale")):
        return "TENNIS_LANE_UNHEALTHY"
    return None


def reconcile_usta_references(events, sources, tennis_payload, manifest, now, get=None):
    """Add only verified USTA cross-references; return independent copied lists.

    ``now`` must be timezone-aware. Today+7 is inclusive in America/Chicago.
    All failures are diagnostic on the existing USTA source rows; no failure
    changes their original status, health, count, approval or coverage fields.
    Source metadata is owned when reference_owner equals OWNER. Foreign event
    calendar references and foreign source metadata are never replaced.
    """
    hold_reason = permission_hold_reason("https://www.usta.com/")
    if hold_reason:
        # Preserve the last saved references, but never imply they were rechecked.
        held_events, held_sources = deepcopy(events), deepcopy(sources)
        for event in held_events:
            for reference in event.get("calendar_references") or []:
                if isinstance(reference, dict) and reference.get("owner") == OWNER:
                    reference.update({"collection_paused": True, "source_stale": True,
                                      "permission_required": True, "permission_hold_reason": hold_reason})
        for source in held_sources:
            if source.get("id") in {value[0] for value in LANES.values()}:
                source.update({"reference_status": "permission-required", "reference_collection_paused": True,
                               "reference_source_stale": True, "reference_permission_required": True,
                               "reference_note": hold_reason, "reference_errors": [hold_reason]})
        return held_events, held_sources
    copied_events, copied_sources = deepcopy(events), deepcopy(sources)
    for event in copied_events:
        refs = event.get("calendar_references")
        if isinstance(refs, list):
            foreign = [r for r in refs if not (isinstance(r, dict) and r.get("owner") == OWNER)]
            if foreign or not refs:
                event["calendar_references"] = foreign
            else:
                event.pop("calendar_references", None)
    for source in copied_sources:
        if source.get("reference_owner") == OWNER:
            for field in SOURCE_FIELDS:
                source.pop(field, None)

    errors = {lane: [] for lane in LANES}
    matched = {lane: [] for lane in LANES}

    def fail(lane, code, row=None):
        label = row.get("source_url") if isinstance(row, dict) else None
        message = f"{code}: {label}" if label else code
        if message not in errors[lane]:
            errors[lane].append(message)

    valid_now = isinstance(now, dt.datetime) and now.tzinfo is not None
    checked_at = now.astimezone(dt.timezone.utc).isoformat() if valid_now else None

    def finish():
        for lane, (usta_id, *_rest) in LANES.items():
            targets = [s for s in copied_sources if s.get("id") == usta_id]
            if len(targets) > 1:
                fail(lane, "USTA_SOURCE_AMBIGUOUS")
            for source in targets:
                # These keys could belong to another producer on an input that
                # did not carry our marker. Never overwrite that producer.
                if any(field in source for field in SOURCE_FIELDS):
                    continue
                count = len(matched[lane])
                source.update({
                    "reference_owner": OWNER,
                    "crosslisted_reference_count": count,
                    "crosslisted_event_ids": sorted(matched[lane]),
                    "reference_status": ("partial-references" if errors[lane] else "references-verified")
                    if count else "no-verified-references",
                    "reference_errors": errors[lane],
                    "reference_note": NOTE,
                    "reference_checked_at": checked_at,
                })
        return copied_events, copied_sources

    if not valid_now:
        for lane in LANES:
            fail(lane, "INVALID_CURRENT_TIME")
        return finish()
    now = now.astimezone(dt.timezone.utc)
    today = now.astimezone(CHICAGO).date()
    last_day = today + dt.timedelta(days=7)
    if not isinstance(manifest, dict):
        for lane in LANES:
            fail(lane, "INVALID_REFERENCE_MANIFEST")
        return finish()
    reviewed = _timestamp(manifest.get("reviewed_at"))
    try:
        review_is_utc = dt.datetime.fromisoformat(str(manifest.get("reviewed_at")).replace("Z", "+00:00")).utcoffset() == dt.timedelta(0)
    except ValueError:
        review_is_utc = False
    if reviewed is None or not review_is_utc or reviewed > now:
        for lane in LANES:
            fail(lane, "INVALID_REVIEW_TIMESTAMP")
        return finish()
    calendars, rows = manifest.get("calendars"), manifest.get("references")
    if not isinstance(calendars, dict) or not isinstance(rows, list):
        for lane in LANES:
            fail(lane, "INVALID_REFERENCE_MANIFEST")
        return finish()
    issue = _payload_issue(tennis_payload, now, today, last_day)
    if issue:
        for lane in LANES:
            fail(lane, issue)
        return finish()
    if get is None:
        import requests
        get = requests.get
    cache = {}
    for lane, (usta_id, canonical_id, tour_id, gender, _prefix) in LANES.items():
        targets = [s for s in copied_sources if s.get("id") == usta_id]
        if len(targets) != 1:
            fail(lane, "USTA_SOURCE_MISSING_OR_AMBIGUOUS")
            continue
        target = targets[0]
        if (target.get("approved_catalog") is not True or target.get("source_type") != "coverage-gap"
                or target.get("league") != f"USTA Pro Circuit | {lane.title()}"):
            fail(lane, "USTA_SOURCE_SCOPE_MISMATCH")
            continue
        if any(field in targets[0] for field in SOURCE_FIELDS):
            # No matching can be reported safely in a foreign metadata slot.
            continue
        calendar = calendars.get(lane)
        if not isinstance(calendar, dict) or calendar.get("source_id") != usta_id:
            fail(lane, "INVALID_REVIEWED_CALENDAR")
            continue
        issue = _lane_issue(tennis_payload, [s for s in copied_sources if s.get("id") == canonical_id], tour_id, now)
        if issue:
            fail(lane, issue)
            continue
        issue = _pdf_issue(calendar, get, cache)
        if issue:
            fail(lane, issue)
            continue
        lane_rows = [r for r in rows if isinstance(r, dict) and r.get("calendar") == lane]
        if not lane_rows:
            fail(lane, "NO_REVIEWED_ROWS")
            continue
        url_counts = Counter(str(r.get("source_url")) for r in lane_rows)
        # A printed PDF row can contain multiple grade columns. The cell or
        # grade distinguishes those legitimate references on the same week.
        def row_key(r):
            return (str(r.get("week_start")), str(r.get("usta_row")), str(r.get("usta_cell") or ""), str(r.get("level")))

        row_counts = Counter(row_key(r) for r in lane_rows)
        id_counts = Counter(_event_id(r) for r in lane_rows if all(isinstance(r.get(k), str) for k in ("source_id", "start_date", "tournament")))
        for row in lane_rows:
            issue = _row_issue(row, lane, today, last_day)
            if issue:
                fail(lane, issue, row)
                continue
            expected_id = _event_id(row)
            if (url_counts[row["source_url"]] != 1
                    or row_counts[row_key(row)] != 1
                    or id_counts[expected_id] != 1):
                fail(lane, "AMBIGUOUS_REVIEWED_ROWS", row)
                continue
            # Count every occurrence of the URL, including conflicting copies.
            tournaments = [t for t in tennis_payload["tournaments"] if isinstance(t, dict) and t.get("source_url") == row["source_url"]]
            if len(tournaments) != 1:
                fail(lane, "AMBIGUOUS_TENNIS_TOURNAMENT" if tournaments else "NO_EXACT_TENNIS_TOURNAMENT", row)
                continue
            item = tournaments[0]
            fields = ("tour_id", "gender", "tournament", "start_date", "end_date", "source_url")
            if any(item.get(k) != row[k] for k in fields):
                fail(lane, "TENNIS_IDENTITY_MISMATCH", row)
                continue
            if item.get("source_stale") or item.get("status") not in ("ACTIVE", "UPCOMING"):
                fail(lane, "TENNIS_TOURNAMENT_STALE_OR_INACTIVE", row)
                continue
            if item.get("level") and item["level"] != row["level"]:
                fail(lane, "TENNIS_LEVEL_MISMATCH", row)
                continue
            candidates = [e for e in copied_events if e.get("id") == expected_id or
                          (e.get("source_id") == canonical_id and e.get("source_endpoint") == row["source_url"])]
            if len(candidates) != 1:
                fail(lane, "AMBIGUOUS_CANONICAL_EVENT" if candidates else "NO_EXACT_CANONICAL_EVENT", row)
                continue
            event = candidates[0]
            if (event.get("id") != expected_id or event.get("source_id") != canonical_id
                    or event.get("source_endpoint") != row["source_url"]
                    or event.get("name") != row["tournament"]
                    or event.get("sport") != "Tennis"
                    or event.get("tour_id", tour_id) != tour_id
                    or event.get("gender", gender) != gender):
                fail(lane, "CANONICAL_IDENTITY_MISMATCH", row)
                continue
            if event.get("catalog_approval") != "EXPLICIT SOURCE MAPPING":
                fail(lane, "CANONICAL_EVENT_NOT_EXPLICITLY_APPROVED", row)
                continue
            if event.get("status") not in ("LIVE", "UPCOMING"):
                fail(lane, "CANONICAL_EVENT_INACTIVE", row)
                continue
            if event.get("source_stale") or "STALE SOURCE" in str(event.get("status_detail", "")).upper():
                fail(lane, "CANONICAL_EVENT_STALE", row)
                continue
            if "calendar_references" in event and not isinstance(event["calendar_references"], list):
                fail(lane, "FOREIGN_CALENDAR_REFERENCES_INVALID", row)
                continue
            event.setdefault("calendar_references", []).append({
                "owner": OWNER,
                "reference_type": "reviewed-calendar-cross-list",
                "source_id": usta_id,
                "calendar_url": calendar["url"],
                "calendar_sha256": calendar["sha256"],
                "published_revision": calendar["published_revision"],
                "reviewed_at": manifest["reviewed_at"],
                "verified_at": checked_at,
                "usta_week_start": row["week_start"],
                "usta_row": row["usta_row"],
                "usta_level": row["level"],
                **{key: row[key] for key in ("usta_cell", "usta_page", "usta_week_number") if key in row},
                "itf_tournament": {k: row[k] for k in ("source_id", *fields)},
                "date_basis": "ITF tournament dates; USTA calendar supplies week-start only",
            })
            matched[lane].append(event["id"])
        if not matched[lane] and not errors[lane]:
            fail(lane, "NO_EXACT_MATCHES")
    if any(not isinstance(r, dict) or r.get("calendar") not in LANES for r in rows):
        for lane in LANES:
            fail(lane, "INVALID_REVIEWED_ROW_CALENDAR")
    return finish()
