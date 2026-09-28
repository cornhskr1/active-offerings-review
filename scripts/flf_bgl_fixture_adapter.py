"""FLF 2026–27 senior BGL Ligue next-round fixture guardrails."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-luxembourg-national-division-bgl-ligue-men"
LUXEMBOURG = ZoneInfo("Europe/Luxembourg")
MATCH_PATH = re.compile(r"/games/(\d+)$")
NEXT_ROUND = re.compile(r"(.+?)\s+(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.2026|\d{2}\.\d{2}\.2027)\s+(.+)")


def _document(page):
    doc = html.fromstring(page)
    for node in doc.xpath("//script|//style"):
        node.drop_tree()
    return doc


def overview(page, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("FLF catalog scope changed")
    doc = _document(page)
    text = " ".join(" ".join(doc.xpath("//body//text()")).split())
    if "BGL Ligue" not in text or "Saison 2026/2027" not in text:
        raise ValueError("FLF BGL edition changed")
    links = doc.xpath('//a[contains(@href,"/games/")]')
    if len(links) != 240:
        raise ValueError("FLF 240-match season changed")
    ids = [MATCH_PATH.fullmatch(a.get("href") or "") for a in links]
    if any(m is None for m in ids) or len({m.group(1) for m in ids}) != 240:
        raise ValueError("FLF match links changed")
    for number in range(30):
        group = links[number*8:(number+1)*8]
        if len(group) != 8:
            raise ValueError("FLF eight-match round changed")
        future = []
        for link in group:
            label = " ".join(" ".join(link.xpath(".//text()")).split())
            match = NEXT_ROUND.fullmatch(label)
            if match:
                date = datetime.datetime.strptime(match.group(3), "%d.%m.%Y").date()
                if date >= today:
                    future.append((link.get("href"),match.groups()))
        if future:
            return number+1, future, 240
    return None, [], 240


def match_card(page, path, round_number, summary, source):
    match = MATCH_PATH.fullmatch(path)
    if not match:
        raise ValueError("FLF match identity changed")
    doc = _document(page)
    title = doc.xpath("string(//title)")
    home, clock, day, away = summary
    if not title.startswith(f"{home} / {away} - Spill"):
        raise ValueError("FLF match pairing changed")
    body = " ".join(" ".join(doc.xpath("//body//text()")).split())
    expected = (f"Date {datetime.datetime.strptime(day,'%d.%m.%Y').strftime('%d/%m/%Y')} "
                f"Heure {clock} Ligue BGL Ligue Seniors M Jour de match {round_number} Lieu ")
    if expected not in body:
        raise ValueError("FLF senior match date, kickoff or league changed")
    location = body.split(expected,1)[1].split(" Retour ",1)[0].strip()
    if not location:
        raise ValueError("FLF venue missing")
    start = datetime.datetime.strptime(f"{day} {clock}","%d.%m.%Y %H:%M").replace(tzinfo=LUXEMBOURG)
    return {"id":f"flf-bgl-{match.group(1)}","source_id":source["id"],
        "sport":source["sport"],"league":source["league"],"region":source["region"],
        "name":f"{away} at {home}",
        "start_time":start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
        "status":"UPCOMING","status_detail":"Official 2026–27 BGL Ligue senior next round",
        "season_stage":"REGULAR","location":location,
        "source_endpoint":f"https://www.flf.lu{path}"}
