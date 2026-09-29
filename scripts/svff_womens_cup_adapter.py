"""Current 2026-27 women's Svenska Cup fixtures from SvFF's official cup page."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


STOCKHOLM = ZoneInfo("Europe/Stockholm")
MONTH = {"SEP": 9, "OKT": 10}
CARD = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>SEP|OKT)\.\s+Svenska Cupen 2026/27 omg\. 1-3\s+"
    r"(?P<home>.+?)\s+-\s+(?P<away>.+?)\s+(?P<clock>\d{2}:\d{2})\s+(?P<venue>.+)$",
    re.I,
)


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_current_fixtures(page, source):
    if (source.get("id") != "uefa-soccer-sweden-svenska-cupen-women"
            or source.get("league") != "Svenska Cupen | Women"):
        raise ValueError("Sweden women's cup catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if ("Svenska Cupen" not in text or "Svenska Cupen 2026/27" not in text
            or "Dam" not in text or "Omgång 3" not in text):
        raise ValueError("SvFF women's cup page identity changed")

    events = []
    seen = set()
    for node in doc.xpath("//a"):
        card = _norm(node.text_content())
        match = CARD.fullmatch(card)
        if not match:
            continue
        day = int(match.group("day"))
        month = MONTH[match.group("month").upper()]
        date = datetime.date(2026, month, day)
        # Round 3 is the women-only current phase; men's round 2 deadline was Sep. 17.
        if not datetime.date(2026, 9, 22) <= date <= datetime.date(2026, 10, 22):
            continue
        home, away = match.group("home"), match.group("away")
        if home == away:
            raise ValueError("SvFF women's cup repeated club")
        key = (date, home, away)
        if key in seen:
            continue
        seen.add(key)
        local = datetime.datetime.combine(date, datetime.time.fromisoformat(match.group("clock")), STOCKHOLM)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"sweden-womens-cup-r3-{date:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "SvFF published Svenska Cupen women round 3",
            "season_stage": "ROUND 3",
            "location": match.group("venue"),
            "source_endpoint": source["endpoint"],
        })
    if not events:
        raise ValueError("SvFF women's cup current round has no exact fixtures")
    return events
