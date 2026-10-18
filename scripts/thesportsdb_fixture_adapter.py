"""Limited public TheSportsDB fixtures, never a full schedule or an approval source.

Vendor documentation: https://www.thesportsdb.com/documentation
Public v1 key 123 is vendor-published, not a private credential. No alternate
hosts, keys, website scraping, or access-denial fallbacks are used here.
"""
import datetime as dt
import re
import time

import requests

UTC = dt.timezone.utc
BASE = "https://www.thesportsdb.com/api/v1/json/123/"
LIMITS = {"thesportsdb": 1, "thesportsdb-day": 3}
METHODS = {"thesportsdb": "eventsnextleague.php", "thesportsdb-day": "eventsday.php"}
LIMIT_NOTE = "Limited public feed; missing fixtures and later phases remain unverified. An empty response is not evidence of offseason or no activity."
PLACEHOLDER = re.compile(r"\b(TBD|TBA|to be determined|to be announced|winner of|loser of)\b", re.I)
HELD_STATUSES = {"TBD", "TBA", "TIME TO BE DEFINED", "POST", "PST", "POSTPONED", "MATCH POSTPONED", "CANC", "CANCELLED", "MATCH CANCELLED", "SUSP", "SUSPENDED", "ABD", "ABANDONED", "AWD", "AW", "WO"}
COMPLETED = {"FT", "AET", "AOT", "AP", "PEN", "MATCH FINISHED", "FINISHED"}


class PublicClient:
    """Pace the documented public API; stop on permanent access denials."""
    def __init__(self, get=requests.get, sleep=time.sleep):
        self.get, self.sleep = get, sleep
        self.blocked = set()
        self.stop_reason = None

    def json(self, endpoint, params):
        if endpoint not in {BASE + name for name in METHODS.values()}:
            raise ValueError("TheSportsDB endpoint is not the documented public schedule route")
        if self.stop_reason:
            raise RuntimeError(self.stop_reason + "; no further requests attempted")
        if endpoint in self.blocked:
            raise RuntimeError("TheSportsDB access denied earlier in this run; no further requests attempted")
        for attempt in range(3):
            self.sleep(2.1)  # documented free limit: 30 requests/minute
            try:
                response = self.get(endpoint, params=params, timeout=25,
                                    headers={"User-Agent": "ActiveOfferingsReview/1.0 (public schedule reference)"},
                                    allow_redirects=False)
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 2:
                    raise
                self.sleep(3 * (attempt + 1))
                continue
            status = response.status_code
            if status in (401, 403):
                self.blocked.add(endpoint)
                self.stop_reason = "TheSportsDB public API access denied earlier in this run"
                response.raise_for_status()
            if 300 <= status < 400:
                raise RuntimeError("TheSportsDB public API redirected; route requires review")
            if status == 429 and attempt < 2:
                raw = response.headers.get("Retry-After", "")
                # Wait at least the vendor-documented one-minute reset. Do not
                # retry earlier than a longer Retry-After or bypass its limit.
                if raw and not raw.isdigit():
                    self.stop_reason = "TheSportsDB Retry-After is not numeric; no early retry attempted"
                    raise RuntimeError(self.stop_reason)
                wait = max(60, int(raw)) if raw.isdigit() else 60
                if wait > 120:
                    self.stop_reason = "TheSportsDB rate limited; Retry-After exceeds this run's retry budget"
                    raise RuntimeError(self.stop_reason)
                self.sleep(wait)
                continue
            if 500 <= status < 600 and attempt < 2:
                self.sleep(3 * (attempt + 1))
                continue
            if status == 429:
                self.stop_reason = "TheSportsDB rate limit persisted; requests stopped for this run"
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "events" not in data:
                raise ValueError("TheSportsDB response has no events field")
            if data["events"] is not None and not isinstance(data["events"], list):
                raise ValueError("TheSportsDB events field is not a list or null")
            return data
        raise RuntimeError("TheSportsDB request failed")


def event_time(event):
    timestamp = str(event.get("strTimestamp") or "").strip()
    if timestamp:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?", timestamp):
            raise ValueError("TheSportsDB timestamp format is unverified")
        value = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        # Vendor UTC fields may omit the suffix. Never use strTimeLocal here.
        value = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    else:
        date, clock = str(event.get("dateEvent") or ""), str(event.get("strTime") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", clock):
            raise ValueError("TheSportsDB exact kickoff missing; date-only fixture held")
        value = dt.datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=UTC)
    value = value.astimezone(UTC)
    # The vendor identifies 00:00 as a frequent unknown-time default. Without
    # independent time evidence, hold even potentially real midnight fixtures.
    if value.time() == dt.time(0):
        raise ValueError("TheSportsDB midnight kickoff requires independent verification")
    return value


def parse_event(source, event):
    if not isinstance(event, dict) or str(event.get("idLeague") or "") != str(source["league_id"]):
        raise ValueError("TheSportsDB exact league identity mismatch")
    if event.get("strSport") != source["sport"]:
        raise ValueError("TheSportsDB sport identity mismatch")
    event_id = str(event.get("idEvent") or "")
    home, away = (str(event.get(key) or "").strip() for key in ("strHomeTeam", "strAwayTeam"))
    if not event_id.isdigit() or not home or not away or home.casefold() == away.casefold() or any(PLACEHOLDER.search(x) for x in (home, away)):
        raise ValueError("TheSportsDB exact match identity or named opponents missing")
    status = str(event.get("strStatus") or "").strip().upper()
    if status in HELD_STATUSES or str(event.get("strPostponed") or "").lower() in {"yes", "true", "1"}:
        raise ValueError("TheSportsDB fixture postponed, cancelled, or time/status unresolved")
    if status not in COMPLETED | {"NS", "NOT STARTED", "SCHEDULED"}:
        raise ValueError("TheSportsDB event status is not a verified upcoming or completed fixture")
    start = event_time(event)
    season = str(event.get("strSeason") or "")
    if not re.fullmatch(r"\d{4}(?:[-/]\d{4})?", season):
        raise ValueError("TheSportsDB season is missing or unverified")
    years = [int(x) for x in re.split(r"[-/]", season)]
    if len(years) == 2 and years[1] != years[0] + 1 or start.year not in years:
        raise ValueError("TheSportsDB season and fixture year conflict")
    round_no = str(event.get("intRound") or "")
    if round_no in {"400", "500"} or re.search(r"qualif|pre.?season|friendly", str(event.get("strEvent") or ""), re.I):
        raise ValueError("TheSportsDB qualifier or preseason scope requires separate approval")
    stages = {"125": "QUARTERFINAL", "150": "SEMIFINAL", "160": "PLAYOFF", "170": "PLAYOFF", "180": "FINAL", "200": "FINAL"}
    venue = " · ".join(str(event[k]) for k in ("strVenue", "strCountry") if event.get(k)) or None
    return {"id": event_id, "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source.get("region"),
            "name": f"{away} at {home}", "start_time": start.isoformat().replace("+00:00", "Z"),
            "status": "COMPLETED" if status in COMPLETED else "UPCOMING",
            "status_detail": event.get("strStatus") or "Publisher status not supplied",
            "season_stage": stages.get(round_no), "season": season, "location": venue,
            "coverage_status": "partial", "source_endpoint": source["endpoint"]}


def collect(source, first, last, timezone, now, client):
    """Return in-window evidence and independent access/completeness diagnostics."""
    kind = source["source_type"]
    if kind not in METHODS or source["endpoint"] != BASE + METHODS[kind]:
        raise ValueError("TheSportsDB source configuration requires review")
    queries = [{"id": source["league_id"]}]
    if kind == "thesportsdb-day":
        # eventsday uses UTC calendar dates; include the UTC day intersecting
        # the final Chicago evening, then filter actual instants locally.
        utc_first = dt.datetime.combine(first, dt.time(), timezone).astimezone(UTC).date()
        utc_last = dt.datetime.combine(last, dt.time.max, timezone).astimezone(UTC).date()
        queries = [{"d": (utc_first + dt.timedelta(days=i)).isoformat(),
                    "l": source["league_id"], "s": source.get("sport_query") or source["sport"]}
                   for i in range((utc_last - utc_first).days + 1)]
    events, errors, seen = [], [], {}
    held = fetched = rows_seen = 0
    for query in queries:
        try:
            payload = client.json(source["endpoint"], query)
            rows = payload.get("events") or []
            fetched += 1
            rows_seen += len(rows)
            for row in rows:
                try:
                    parsed = parse_event(source, row)
                    start = dt.datetime.fromisoformat(parsed["start_time"].replace("Z", "+00:00"))
                    if kind == "thesportsdb-day" and start.date().isoformat() != query["d"]:
                        raise ValueError("TheSportsDB daily response crossed its UTC query date")
                    previous = seen.get(parsed["id"])
                    if previous is not None and previous != parsed:
                        raise ValueError("TheSportsDB duplicate event identity conflicts")
                    if previous is not None:
                        continue
                    seen[parsed["id"]] = parsed
                    if first <= start.astimezone(timezone).date() <= last and start > now and parsed["status"] != "COMPLETED":
                        events.append(parsed)
                except (ValueError, TypeError, KeyError) as exc:
                    held += 1
                    errors.append(str(exc))
        except Exception as exc:
            errors.append(f"{query.get('d', 'next league')}: {str(exc)[:160]}")
    # A conflicting duplicate invalidates both copies, rather than keeping the
    # first potentially wrong pairing or kickoff.
    if any("duplicate event identity conflicts" in error for error in errors):
        events = []
    return events, {"ok": not errors, "errors": list(dict.fromkeys(errors))[:3],
                    "coverage_status": "partial", "coverage_complete": False,
                    "coverage_warning": LIMIT_NOTE, "provider_free_result_limit": LIMITS[kind],
                    "requests_expected": len(queries), "requests_succeeded": fetched,
                    "published_rows": rows_seen, "fixtures_held": held}
