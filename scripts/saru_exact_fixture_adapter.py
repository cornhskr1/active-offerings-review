"""Two bounded 2026 SA Rugby feeds, not a general WXV or SA Rugby approval.

The existing Premier Division adapter is deliberately unchanged. This module
covers Currie Cup First Division and only USA Women's senior WXV matches.
"""

import datetime as dt
import re
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")
UTC = dt.timezone.utc
ENDPOINT = "https://springboks.rugby/api/match-centre/matches"
OFFICIAL_SCHEDULE_URL = "https://springboks.rugby/match-centre/"
USA_TEAM_ID = "23f44fd1-36cb-4f3e-8d1b-20882b5b631d"
SPECS = {
    "56038bac-544a-482e-a5da-6351054efc5d": {
        "source_id": "rugby-saru-currie-first",
        "competition_name": "Carling Currie Cup First Division",
        "season_id": "e2b76a5f-d3e9-42f8-a5cd-4df2b469bd22",
        "season_name": "2026", "league": "Currie Cup | Men",
        "required_team_id": None, "required_team_name": None,
        "catalog_terms": ["Currie Cup | Men"],
    },
    "669f0a5d-fc63-4c08-855e-2cbcf51dd401": {
        "source_id": "rugby-usa",
        "competition_name": "WXV Global Series",
        "season_id": "513e569c-09fd-46da-ad91-bd91ec0b1476",
        "season_name": "2026", "league": "Women’s USA Rugby Events | Women",
        "required_team_id": USA_TEAM_ID, "required_team_name": "USA Women",
        "catalog_terms": ["Women’s USA Rugby Events | Women"],
    },
}
UNIDENTIFIED = re.compile(r"\b(?:TBC|TBD|TBA|unknown|winner|loser|qualifier)\b", re.I)
YOUTH = re.compile(r"\b(?:U[ -]?\d{1,2}|under[ -]?\d{1,2}|youth|young guns)\b", re.I)
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.I)
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)?")


def _spec(source):
    spec = SPECS.get(source.get("competition_id"))
    if (not spec or source.get("sport") != "Rugby"
            or source.get("source_type") != "saru-exact-matches"
            or source.get("endpoint") != ENDPOINT
            or source.get("id") != spec["source_id"]
            or source.get("official_schedule_url") != OFFICIAL_SCHEDULE_URL
            or source.get("league") != spec["league"]
            or source.get("catalog_terms") != spec["catalog_terms"]
            or any(source.get(field) != spec[field] for field in
                   ("competition_name", "season_id", "season_name", "required_team_id", "required_team_name"))):
        raise ValueError("SA Rugby exact catalog, competition, team or edition scope changed")
    if source.get("coverage_status") != "partial" or source.get("coverage_complete") is not False:
        raise ValueError("SA Rugby division/USA WXV-only coverage must remain partial")
    return spec


def _window(today, end):
    if (type(today) is not dt.date or type(end) is not dt.date or today > end
            or (end - today).days > 366):
        raise ValueError("SA Rugby review window is invalid")
    if today.year > 2026:
        raise ValueError("SA Rugby configured 2026 edition expired")


def _payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("SA Rugby match payload missing")
    rows, total = payload.get("items"), payload.get("totalDataCount")
    if (not isinstance(rows, list) or type(total) is not int
            or not 0 <= total <= 1000 or not all(isinstance(row, dict) for row in rows)):
        raise ValueError("SA Rugby paginated items or total count invalid")
    return rows, total


def parse_saru_exact_matches(payload, source, today, end, evidence=None):
    """Validate a completely collected payload, then return exact in-window cards."""
    spec = _spec(source)
    _window(today, end)
    rows, total = _payload(payload)
    if total != len(rows):
        raise ValueError("SA Rugby uncollected pages or inconsistent total count")
    events, seen = [], set()
    counts = {"returned_rows": total, "scoped_rows": 0, "other_team_rows": 0,
              "held_unidentified": 0, "held_cancelled_or_postponed": 0,
              "held_scored_or_finished": 0, "held_forfeited": 0,
              "held_missing_kickoff": 0, "outside_review_window": 0,
              "emitted_events": 0, "coverage_complete": False}
    for row in rows:
        mid = row.get("matchId")
        if not isinstance(mid, str) or not UUID.fullmatch(mid) or mid in seen:
            raise ValueError("SA Rugby missing or duplicate match identifier")
        seen.add(mid)
        if (row.get("competitionId") != source["competition_id"]
                or row.get("competitionName") != spec["competition_name"]):
            raise ValueError("SA Rugby wrong competition or division")
        if (row.get("seasonId") != spec["season_id"]
                or row.get("seasonName") != spec["season_name"]):
            raise ValueError("SA Rugby wrong season or edition")
        # Unknown status must not silently become a scheduled match. A real
        # score is authoritative even when the provider's statsStatus is None.
        if any(type(row.get(flag)) is not bool for flag in
               ("isCancelled", "isPostponed", "isLive")):
            raise ValueError("SA Rugby fixture flags are missing or ambiguous")
        if row.get("statsStatus") not in ("None", "Complete", "Result"):
            raise ValueError("SA Rugby unknown match status")
        teams = row.get("teams")
        if (not isinstance(teams, list) or len(teams) != 2
                or not all(isinstance(team, dict) for team in teams)
                or sorted(str(team.get("isHomeTeam")) for team in teams) != ["False", "True"]
                or not all(type(team.get("isHomeTeam")) is bool for team in teams)):
            raise ValueError("SA Rugby home/away pairing is ambiguous")
        if any(not isinstance(team.get("teamId"), str)
               or not UUID.fullmatch(team["teamId"]) for team in teams):
            raise ValueError("SA Rugby team identifiers missing")
        if teams[0]["teamId"] == teams[1]["teamId"]:
            raise ValueError("SA Rugby repeated opponent identifier")
        if any(type(team.get("hasForfeited")) is not bool for team in teams):
            raise ValueError("SA Rugby forfeiture state missing or ambiguous")
        if any(not isinstance(team.get("name"), str) for team in teams):
            raise ValueError("SA Rugby opponent names must be strings")
        names = [" ".join(team["name"].split()) for team in teams]
        if not all(names) or names[0].casefold() == names[1].casefold():
            raise ValueError("SA Rugby unnamed or identical opponents")
        if any(UNIDENTIFIED.search(name) or YOUTH.search(name) for name in names):
            counts["held_unidentified"] += 1
            continue
        if any("score" not in team for team in teams):
            raise ValueError("SA Rugby score state missing")
        if spec["required_team_id"]:
            selected = [team for team in teams if team["teamId"] == USA_TEAM_ID]
            if not selected:
                # A lookalike name cannot substitute for the verified team ID.
                if "USA Women" in names:
                    raise ValueError("SA Rugby USA Women identifier changed")
                counts["other_team_rows"] += 1
                continue
            if len(selected) != 1 or selected[0].get("name") != "USA Women":
                raise ValueError("SA Rugby USA Women team identity changed")
            if not all(name.endswith(" Women") for name in names):
                raise ValueError("SA Rugby senior women's pairing changed")
        elif any(re.search(r"\bWomen\b", name, re.I) for name in names):
            raise ValueError("SA Rugby First Division gender scope changed")
        counts["scoped_rows"] += 1
        if any(team.get("hasForfeited") is True for team in teams):
            counts["held_forfeited"] += 1
            continue
        if row["isCancelled"] or row["isPostponed"]:
            counts["held_cancelled_or_postponed"] += 1
            continue
        if (row["statsStatus"] in ("Complete", "Result")
                or any(team["score"] is not None for team in teams)):
            counts["held_scored_or_finished"] += 1
            continue
        value = row.get("utcDate")
        if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
            counts["held_missing_kickoff"] += 1
            continue
        try:
            start = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            counts["held_missing_kickoff"] += 1
            continue
        # The official field is explicitly UTC despite omitting its suffix.
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if start.year != int(spec["season_name"]):
            raise ValueError("SA Rugby fixture date outside the configured edition")
        if not today <= start.astimezone(CENTRAL).date() <= end:
            counts["outside_review_window"] += 1
            continue
        home = names[next(i for i, team in enumerate(teams) if team["isHomeTeam"])]
        away = names[next(i for i, team in enumerate(teams) if not team["isHomeTeam"])]
        events.append({
            "id": f'{source["id"]}-{mid}', "source_id": source["id"],
            "sport": "Rugby", "league": source["league"],
            "region": source.get("region", "International"),
            "name": f"{away} at {home}",
            "start_time": start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "status": "LIVE" if row["isLive"] else "UPCOMING",
            "season_stage": "CUP" if not spec["required_team_id"] else "WXV GLOBAL SERIES",
            "location": row.get("venueName"),
            "source_endpoint": source["official_schedule_url"],
        })
    counts["emitted_events"] = len(events)
    if evidence is not None:
        evidence.update(counts)
    return events


def collect(source, today, end, get):
    """Fetch all bounded pages atomically; never follow redirects or retry denial."""
    _spec(source)
    _window(today, end)
    first = dt.datetime.combine(today, dt.time.min, CENTRAL).astimezone(UTC)
    after = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, CENTRAL).astimezone(UTC)
    # Query whole UTC dates around the Chicago window. The pure parser performs
    # the exact local-date filter, including the last evening after UTC midnight.
    params = {"startDate": first.date().isoformat(),
              "endDate": (after.date() + dt.timedelta(days=1)).isoformat(),
              "pageIndex": 0, "pageSize": 100, "IsAscending": "true",
              "competitionId": source["competition_id"]}
    rows, expected = [], None
    while expected is None or len(rows) < expected:
        response = get(ENDPOINT, params=dict(params), timeout=35, allow_redirects=False)
        status = response.status_code
        if status in (401, 403):
            raise ValueError(f"SA Rugby public feed denied access (HTTP {status}); stopped")
        if status != 200:
            raise ValueError(f"SA Rugby public feed HTTP {status}; no redirects or alternatives")
        if getattr(response, "url", ENDPOINT).split("?", 1)[0] != ENDPOINT:
            raise ValueError("SA Rugby response moved from the approved endpoint")
        page, total = _payload(response.json())
        if expected is None:
            expected = total
        if total != expected or len(page) != min(100, expected - len(rows)):
            raise ValueError("SA Rugby partial page or changing pagination count")
        rows.extend(page)
        params["pageIndex"] += 1
    evidence = {"pages_collected": params["pageIndex"],
                "query_start_date": params["startDate"], "query_end_date": params["endDate"],
                "competition_id": source["competition_id"], "season_id": source["season_id"],
                "season_name": source["season_name"]}
    events = parse_saru_exact_matches({"items": rows, "totalDataCount": expected},
                                     source, today, end, evidence)
    return events, evidence
