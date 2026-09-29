"""Scoped exact next-fixture adapters for K League 1 and K League 2 official publications."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SEOUL = ZoneInfo("Asia/Seoul")

EXPECTED = {
    "soccer-afc-korea-k-league-1-men": {
        "league": "K League 1 | Men",
        "date": "2026-10-18",
        "clock": "16:30",
        "home": "FC Seoul",
        "away": "Gimcheon Sangmu",
        "round": "ROUND 32",
        "required": (
            "하나은행K리그12026",
            "서울대김천",
            "10월18일(일)오후4시30분",
        ),
    },
    "soccer-afc-korea-k-league-2-men": {
        "league": "K League 2 | Men",
        "date": "2026-10-09",
        "clock": "16:30",
        "home": "Gimpo FC",
        "away": "Seoul E-Land FC",
        "round": "ROUND 28",
        "required": (
            "하나은행K리그2202628라운드",
            "10월9일오후4시30분",
            "서울이랜드FC",
            "김포",
        ),
    },
}


def _compact(value):
    return re.sub(r"\s+", "", str(value or "").replace("\xa0", " "))


def parse_next_fixture(page, source):
    cfg = EXPECTED.get(source.get("id"))
    if not cfg:
        raise ValueError("K League source identity not configured")
    if source.get("league") != cfg["league"] or source.get("catalog_terms") != [cfg["league"]]:
        raise ValueError("K League catalog scope changed")

    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _compact(doc.text_content())

    for marker in cfg["required"]:
        if _compact(marker) not in text:
            raise ValueError(f"K League publication changed: missing {marker}")

    date = datetime.date.fromisoformat(cfg["date"])
    local = datetime.datetime.combine(date, datetime.time.fromisoformat(cfg["clock"]), SEOUL)
    slug = re.sub(r"[^a-z0-9]+", "-", cfg["home"].lower()).strip("-")
    return [{
        "id": f"{source['id']}-{date:%Y%m%d}-{slug}",
        "source_id": source["id"],
        "sport": source["sport"],
        "league": source["league"],
        "region": source["region"],
        "name": f"{cfg['away']} at {cfg['home']}",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING",
        "status_detail": f"K League official publication {cfg['round'].lower()}",
        "season_stage": cfg["round"],
        "source_endpoint": source["endpoint"],
    }]
