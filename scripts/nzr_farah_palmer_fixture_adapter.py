"""Named 2026 Farah Palmer Cup semifinals and finals from NZ Rugby's broadcast schedule."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


AUCKLAND = ZoneInfo("Pacific/Auckland")
CLUBS = {
    "Auckland Storm", "Bay of Plenty Volcanix", "Canterbury",
    "Counties Manukau Heat", "Hawke's Bay Tui", "Manawatū Cyclones",
    "North Harbour Hibiscus", "Northland Kauri", "Otago Spirit",
    "Tasman", "Waitomo Waikato", "Wellington Pride",
}
DATES = re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\d{1,2}) "
                   r"(August|September|October), (\d{1,2})[.:](\d{2})(am|pm)")


def _text(node):
    return " ".join(" ".join(node.xpath(".//text()")).split())


def _cells(row):
    cells = row.xpath("./td")
    if len(cells) != 4:
        raise ValueError("Farah Palmer Cup broadcast table changed")
    return [_text(cell) for cell in cells]


def _date(value):
    match = DATES.fullmatch(value)
    if not match:
        raise ValueError("Farah Palmer Cup kickoff changed or is untimed")
    weekday, day, month, hour, minute, period = match.groups()
    date = datetime.date(2026, datetime.datetime.strptime(month, "%B").month, int(day))
    if date.strftime("%A") != weekday:
        raise ValueError("Farah Palmer Cup weekday and 2026 edition disagree")
    if not 1 <= int(hour) <= 12:
        raise ValueError("Farah Palmer Cup clock hour invalid")
    clock = (int(hour) % 12) + (12 if period == "pm" else 0)
    return datetime.datetime.combine(date, datetime.time(clock, int(minute)), AUCKLAND)


def parse_semifinals(page, source):
    if (source.get("id") != "rugby-nzr-farah-palmer-2026"
            or source.get("catalog_terms") != ["Farah Palmer Cup | Women"]
            or source.get("league") != "Farah Palmer Cup | Women"):
        raise ValueError("Farah Palmer Cup catalog scope changed")
    doc = html.fromstring(page, parser=html.HTMLParser(encoding="utf-8"))
    title = _text(doc.xpath("//h1")[0]) if doc.xpath("//h1") else ""
    if title != "Where to watch the Farah Palmer Cup, presented by Hilux":
        raise ValueError("NZ Rugby Farah Palmer Cup page identity changed")
    sections = doc.xpath('//section[contains(concat(" ",normalize-space(@class)," ")," fixtures-table ")]')
    if [_text(block.xpath(".//h4")[0]) for block in sections] != [
            "Round One", "Round Two", "Round Three", "Round Four", "Round Five",
            "Semi-Finals", "Grand Finals"]:
        raise ValueError("Farah Palmer Cup publication phases changed")
    regular = []
    for block in sections[:5]:
        rows = block.xpath(".//table/tbody/tr[td]")
        if len(rows) != 6:
            raise ValueError("Farah Palmer Cup round is incomplete")
        for row in rows:
            home, away, stamp, _ = _cells(row)
            if home not in CLUBS or away not in CLUBS or home == away:
                raise ValueError("Farah Palmer Cup first-phase clubs changed")
            regular.append((home, away, _date(stamp)))
    if len({club for home, away, _ in regular for club in (home, away)}) != 12:
        raise ValueError("Farah Palmer Cup club field changed")
    rows = sections[5].xpath(".//table/tbody/tr[td]")
    if len(rows) != 6:
        raise ValueError("Farah Palmer Cup semifinals incomplete")
    division = None
    division_counts = {"Championship": 0, "Premiership": 0}
    semifinalists = set()
    finalists_by_division = {"Championship": set(), "Premiership": set()}
    events = []
    for row in rows:
        home, away, stamp, watch = _cells(row)
        if home in ("Championship", "Premiership") and not away and not stamp:
            division = home
            continue
        if (division is None or home not in CLUBS or away not in CLUBS
                or home == away or any(club in semifinalists for club in (home, away))
                or not watch):
            raise ValueError("Farah Palmer Cup semifinal pairing or division changed")
        semifinalists.update((home, away))
        finalists_by_division[division].update((home, away))
        division_counts[division] += 1
        local = _date(stamp)
        if local.date() not in (datetime.date(2026, 10, 3), datetime.date(2026, 10, 4)):
            raise ValueError("Farah Palmer Cup semifinal dates changed")
        slug = lambda name: re.sub("[^a-z0-9]+", "-", name.lower()).strip("-")
        events.append({
            "id": f"nzr-fpc-2026-semi-{slug(division)}-{slug(home)}",
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"NZ Rugby published {division} semifinal",
            "season_stage": "PLAYOFF", "source_endpoint": source["endpoint"],
        })
    if len(events) != 4 or len(semifinalists) != 8 or set(division_counts.values()) != {2}:
        raise ValueError("Farah Palmer Cup semifinals incomplete")
    finals = sections[6].xpath(".//table/tbody/tr[td]")
    if len(finals) != 4:
        raise ValueError("Farah Palmer Cup final publication changed")
    aliases = {"Wellington": "Wellington Pride", "Northland": "Northland Kauri",
               "Auckland": "Auckland Storm"}
    held = 0
    for offset, division in ((0, "Championship"), (2, "Premiership")):
        if _cells(finals[offset])[:3] != [division, "", ""]:
            raise ValueError("Farah Palmer Cup final division changed")
        home, away, stamp, watch = _cells(finals[offset+1])
        if home in ("TBC", "TBD") or away in ("TBC", "TBD"):
            held += 1
            continue
        home, away = aliases.get(home, home), aliases.get(away, away)
        if (home == away or not {home, away} <= finalists_by_division[division]
                or not watch):
            raise ValueError("Farah Palmer Cup final pairing or division changed")
        local = _date(stamp)
        # Exact published season/division boundaries; read each kickoff rather than pinning it.
        expected_day = datetime.date(2026, 10, 10 if division == "Championship" else 11)
        if local.date() != expected_day:
            raise ValueError("Farah Palmer Cup final date outside verified division window")
        events.append({
            "id": f"nzr-fpc-2026-final-{division.lower()}",
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"NZ Rugby published {division} final",
            "season_stage": "FINAL", "source_endpoint": source["endpoint"],
        })
    return events, len(regular), held
