"""Exact UTC fixtures from Liga Portugal's second-tier calendar export."""

import datetime
import re
import uuid
from zoneinfo import ZoneInfo


SOURCE_ID = "uefa-soccer-portugal-liga-portugal-2-men"
LISBON = ZoneInfo("Europe/Lisbon")
MATCH_URL = re.compile(r"https://www\.ligaportugal\.pt/match/20262027/ligaportugalmeusuper/(\d{1,2})/(\d{1,2})")


def parse_calendar(payload, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Portugal second-tier catalog scope changed")
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    # RFC 5545 folded lines continue the preceding property without the leading space.
    lines = re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n")).splitlines()
    if (lines[:2] != ["BEGIN:VCALENDAR", "VERSION:2.0"]
            or "Liga Portugal Meu Super - 2026-2027//PT" not in "".join(lines[:5])
            or lines[-1] != "END:VCALENDAR"):
        raise ValueError("Liga Portugal Meu Super calendar edition changed")
    blocks = []
    current = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            if current is not None:
                raise ValueError("Nested Liga Portugal calendar event")
            current = {}
        elif line == "END:VEVENT":
            if current is None:
                raise ValueError("Liga Portugal calendar event boundary changed")
            blocks.append(current)
            current = None
        elif current is not None:
            if ":" not in line:
                raise ValueError("Liga Portugal calendar property changed")
            key, value = line.split(":", 1)
            current.setdefault(key, []).append(value)
    if current is not None or not 1 <= len(blocks) <= 306:
        raise ValueError("Liga Portugal calendar event count changed")
    events = []
    ids = set()
    paths = set()
    held_placeholder = held_reserve = 0
    for row in blocks:
        def one(key):
            values = row.get(key, [])
            if len(values) != 1:
                raise ValueError(f"Liga Portugal {key} changed")
            return values[0]
        try:
            identifier = str(uuid.UUID(one("UID")))
        except ValueError as exc:
            raise ValueError("Liga Portugal fixture ID changed") from exc
        categories = row.get("CATEGORIES", [])
        summary = one("SUMMARY")
        match = re.fullmatch(r"(.+?) - (.+)", summary)
        path = one("URL")
        url = MATCH_URL.fullmatch(path)
        description = one("DESCRIPTION")
        if (not match or not url or identifier in ids or path in paths
                or categories != ["Liga Portugal", "2026-2027", "Liga Portugal Meu Super", *match.groups()]
                or not 1 <= int(url.group(1)) <= 34 or not 1 <= int(url.group(2)) <= 9
                or description != f"Liga Portugal Meu Super\\, jornada {int(url.group(1))}\\nUrl: {path}"
                or not one("LOCATION") or one("CLASS") != "PUBLIC"):
            raise ValueError("Liga Portugal second-tier competition or match fields changed")
        ids.add(identifier)
        paths.add(path)
        try:
            start = datetime.datetime.strptime(one("DTSTART"), "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
            end = datetime.datetime.strptime(one("DTEND"), "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError as exc:
            raise ValueError("Liga Portugal UTC kickoff changed") from exc
        local = start.astimezone(LISBON)
        if (end - start != datetime.timedelta(minutes=105)
                or not datetime.date(2026, 8, 8) <= local.date() <= datetime.date(2027, 5, 17)):
            raise ValueError("Liga Portugal fixture time outside season")
        # The exporter represents as-yet unscheduled matches at Lisbon midnight.
        if local.time() == datetime.time.min:
            held_placeholder += 1
            continue
        # The B teams may field minors. Their schedule alone is not an age check.
        if any(name.endswith(" B") for name in match.groups()):
            held_reserve += 1
            continue
        home, away = match.groups()
        events.append({"id": f"liga-portugal-2-{url.group(1)}-{url.group(2)}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}", "start_time": start.isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026–27 Liga Portugal Meu Super round {url.group(1)}",
            "season_stage": "REGULAR", "location": one("LOCATION"), "source_endpoint": path})
    return events, held_placeholder, held_reserve, len(blocks)
