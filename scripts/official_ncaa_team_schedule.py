"""Fail-closed, four-game DI subsets of two official university schedules.

This is not a National Collegiate championship or whole-team approval.
"""
import datetime as dt
import json
import re
from zoneinfo import ZoneInfo

SPECS = {
    "ncaa-water-polo-di-men": {
        "endpoint": "https://ucirvinesports.com/sports/mens-water-polo/schedule",
        "sport": "NCAA Water Polo", "league": "Division I Water Polo | Men",
        "host": "UC Irvine", "title": "2026 Men's Water Polo Schedule",
        "sport_id": 10, "shortname": "mwpolo", "gender": "m",
        "publisher_sport": "Men's Water Polo", "timezone": "America/Los_Angeles",
        "games": {14405: (149, "UC San Diego"), 14406: (115, "Air Force")},
    },
    "ncaa-ice-hockey-di-women": {
        "endpoint": "https://scsuhuskies.com/sports/womens-ice-hockey/schedule",
        "sport": "NCAA Ice Hockey", "league": "Division I Ice Hockey | Women",
        "host": "St. Cloud State", "title": "2026-27 Women's Hockey Schedule",
        "sport_id": 14, "shortname": "whockey", "gender": "f",
        "publisher_sport": "Women's Hockey", "timezone": "America/Chicago",
        "games": {16677: (16, "Bemidji State"), 16678: (16, "Bemidji State")},
    },
}
# A bounded reviewed batch, not an indefinitely renewable participant whitelist.
VALID_FROM = dt.date(2026, 10, 18)
VALID_THROUGH = dt.date(2026, 10, 25)


def _nodes(page):
    matches = re.findall(r'<script\b[^>]*\bid=[\"\x27]__NUXT_DATA__[\"\x27][^>]*>(.*?)</script>', page, re.S)
    if len(matches) != 1:
        raise ValueError("Expected one official Nuxt schedule payload")
    nodes = json.loads(matches[0])
    if not isinstance(nodes, list):
        raise ValueError("Nuxt schedule graph changed")

    def resolve(index, seen=frozenset()):
        if type(index) is not int:
            raise ValueError("Malformed Nuxt reference")
        if index == -1:  # devalue undefined
            return None
        if index < 0 or index >= len(nodes) or index in seen:
            raise ValueError("Invalid or cyclic Nuxt schedule reference")
        value = nodes[index]
        if isinstance(value, dict):
            return {key: resolve(ref, seen | {index}) for key, ref in value.items()}
        if isinstance(value, list):
            return [resolve(ref, seen | {index}) for ref in value]
        return value
    return nodes, resolve


def _field(row, snake, camel=None):
    values = [row[k] for k in (snake, camel) if k and k in row]
    if not values or any(v != values[0] for v in values):
        raise ValueError("Missing or conflicting schedule field: " + snake)
    return values[0]


def _local_time(text):
    normalized = re.sub(r"[.\s]", "", str(text)).lower()
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)", normalized)
    if not match or not 1 <= int(match[1]) <= 12:
        raise ValueError("Unconfirmed visible game time")
    hour = int(match[1]) % 12 + (12 if match[3] == "pm" else 0)
    return dt.time(hour, int(match[2] or 0))


def parse_fixtures(page, source, start_day, end_day):
    """Return (collector events, held unique game count), or raise on changes.

    Dates are inclusive America/Chicago review dates. This reviewed batch expires
    after October 25, 2026; a new verification is necessary to extend its scope.
    Missing approved games/UTC or contradictory duplicates fail the entire source.
    Unapproved IDs are never ingested. Completed, inactive and TBD games are held.
    """
    spec = SPECS.get(source.get("id"))
    if not spec or any(source.get(k) != spec[k] for k in ("endpoint", "sport", "league")):
        raise ValueError("Unverified NCAA team source identity")
    if (source.get("source_type") != "official-ncaa-reviewed-team-fixtures"
            or source.get("region") != "United States"
            or source.get("catalog_terms") != [spec["league"]]
            or source.get("coverage_status") != "partial"
            or source.get("coverage_complete") is not False):
        raise ValueError("NCAA reviewed subset configuration broadened")
    if start_day > end_day or start_day < VALID_FROM or start_day > VALID_THROUGH:
        raise ValueError("NCAA exact-team evidence window expired or invalid")
    nodes, resolve = _nodes(page)
    if spec["title"] not in nodes:
        raise ValueError("Official team schedule season changed")
    grouped = {key: [] for key in spec["games"]}
    held = set()
    for index, value in enumerate(nodes):
        if not isinstance(value, dict) or "id" not in value:
            continue
        # Only schedule-shaped nodes, not opponent/sport/result identities.
        if not any(k in value for k in ("start_date", "date")) or not any(k in value for k in ("opponent", "sport")):
            continue
        row = resolve(index)
        number = row["id"]
        if type(number) is not int:
            raise ValueError("Malformed publisher game identity")
        if number not in grouped:
            held.add(number)
            continue
        opponent = row.get("opponent") or {}
        if (opponent.get("id"), opponent.get("title")) != spec["games"][number]:
            raise ValueError("Approved game opponent changed")
        if _field(row, "location_indicator", "locationIndicator") != "H":
            raise ValueError("Approved host/home identity changed")
        sport = row.get("sport")
        if sport is not None and any(sport.get(k) != v for k, v in {
            "id": spec["sport_id"], "title": spec["publisher_sport"],
            "shortname": spec["shortname"], "gender": spec["gender"],
        }.items()):
            raise ValueError("Publisher sport or gender changed")
        local = _field(row, "start_date", "date")
        try:
            local_dt = dt.datetime.fromisoformat(local)
        except (ValueError, TypeError):
            raise ValueError("Invalid local schedule date") from None
        if local_dt.tzinfo is not None or local_dt.time() != _local_time(row.get("time")):
            raise ValueError("Visible time contradicts local schedule date")
        utc_values = [row[k] for k in ("start_date_utc", "dateUtc") if k in row]
        utc = None
        if utc_values:
            if sport is None:
                raise ValueError("Timed game missing publisher sport identity")
            if len(set(utc_values)) != 1 or not isinstance(utc_values[0], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", utc_values[0]):
                raise ValueError("Unconfirmed literal publisher UTC")
            utc = utc_values[0]
            instant = dt.datetime.fromisoformat(utc.replace("Z", "+00:00"))
            if instant.astimezone(ZoneInfo(spec["timezone"])).replace(tzinfo=None) != local_dt:
                raise ValueError("Publisher UTC contradicts visible local time")
        state = _field(row, "game_state_display", "gameStateDisplay")
        active = row.get("status") == "A" and state == "SCHEDULED"
        tbd = _field(row, "is_tdb", "tbd")
        allday = (_field(row, "is_all_day", "allday")
                  if "is_all_day" in row or "allday" in row else False)
        if type(tbd) is not bool or type(allday) is not bool:
            raise ValueError("Invalid unconfirmed-time flags")
        if (row.get("tournament") or row.get("event_name") or row.get("noplay_text")
                or row.get("type", "R") not in ("R", "upcoming")
                or row.get("neutral_hometeam") or row.get("neutralHometeam")):
            active = False
        grouped[number].append((local, utc, active, tbd, allday, row.get("location")))
    events = []
    remaining = 0
    for number, copies in grouped.items():
        if not copies or not any(c[1] for c in copies):
            raise ValueError("Reviewed game missing confirmed publisher UTC")
        comparable = {(c[0], c[2], c[3], c[4], c[5]) for c in copies}
        times = {c[1] for c in copies if c[1]}
        if len(comparable) != 1 or len(times) != 1:
            raise ValueError("Contradictory publisher game copies")
        local, active, tbd, allday, location = next(iter(comparable))
        utc = next(iter(times))
        day = dt.datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Chicago")).date()
        if not active or tbd or allday or not VALID_FROM <= day <= VALID_THROUGH:
            held.add(number)
            continue
        remaining += 1
        if not start_day <= day <= end_day:
            continue
        events.append({"id": f"{source['id']}:{number}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"],
            "region": source.get("region", "United States"),
            "name": f"{spec['games'][number][1]} at {spec['host']}",
            "start_time": utc, "status": "UPCOMING", "status_detail": "SCHEDULED",
            "season_stage": None, "location": location, "source_endpoint": source["endpoint"]})
    if not remaining:
        raise ValueError("Reviewed NCAA subset expired or has no confirmed scheduled games")
    return sorted(events, key=lambda e: (e["start_time"], e["id"])), len(held)
