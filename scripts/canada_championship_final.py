"""Canada Soccer's named, timed 2026 men's Championship final only."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "concacaf-soccer-canada-canadian-championship-men"
FINAL_ID = "6384"
MONTREAL = ZoneInfo("America/Toronto")


def _text(node, selector):
    return " ".join(" ".join(node.xpath(selector)).split())


def parse_final(page, source):
    if source.get("id") != SOURCE_ID or source.get("catalog_terms") != ["Canadian Championship | Men"]:
        raise ValueError("Canadian Championship catalog scope changed")
    doc = html.fromstring(page)
    main = _text(doc, '//main//text()')
    if "2026 TELUS Canadian Championship" not in main or "The Men’s 2026 TELUS Canadian Championship" not in main:
        raise ValueError("Canada Soccer men's competition or edition changed")
    cards = doc.xpath(f'//div[@id="match-{FINAL_ID}" and contains(concat(" ",normalize-space(@class)," ")," match-card ")]')
    if len(cards) != 1:
        raise ValueError("Canada Soccer exact final match ID changed")
    card = cards[0]
    link = card.xpath('./div[contains(@class,"match-card-header")]//a/@href')
    teams = [_text(card, f'.//p[contains(@class,"{kind}-team")]//span[contains(@class,"team-name")]//text()')
             for kind in ("away", "visitor")]
    date = _text(card, './/p[contains(@class,"match-date")]/text()')
    clock = _text(card, './/p[contains(@class,"match-time")]/text()')
    footer = _text(card, './/div[contains(@class,"match-card-footer")]//text()')
    if (link != [f"https://canadasoccer.com/match/{FINAL_ID}/"]
            or teams != ["CF Montréal", "Forge FC Hamilton"]
            or date != "21 Oct 2026" or clock != "19:00 EDT"
            or "FINAL / FINALE (Local 19h00)" not in footer
            or "Stade Saputo, Montréal, Québec" not in footer):
        raise ValueError("Canada Soccer final pairing, venue, or kickoff changed")
    if not re.search(r"\bupcoming-match\b", card.get("class", "")):
        if re.search(r"\b(?:completed-match|finished-match)\b", card.get("class", "")):
            return None
        raise ValueError("Canada Soccer final match status changed")
    local = datetime.datetime(2026, 10, 21, 19, 0, tzinfo=MONTREAL)
    if local.strftime("%Z") != "EDT":
        raise ValueError("Canada Soccer local final time zone changed")
    return {"id": f"canada-championship-final-{FINAL_ID}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{teams[1]} at {teams[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "2026 TELUS Canadian Championship final — verify participant eligibility",
            "season_stage": "FINAL", "location": "Stade Saputo, Montréal, Québec",
            "source_endpoint": link[0]}
