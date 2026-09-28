"""League of Ireland official 2026 men's Premier Division fixture pages."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-ireland-league-of-ireland-premier-division-men"
AJAX_PATH = "/ajax/blocks/opta/fixtures"
DUBLIN = ZoneInfo("Europe/Dublin")
PARAMS = {"bid": "23256", "cid": "337", "competition": "1", "limit": "20",
          "paginate": "1", "target": ".fixture__items--23256",
          "template": "full_fixture", "header": "1"}


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def validate_page(page, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("LOI catalog scope changed")
    doc = html.fromstring(page)
    if (_text(doc, '/html/head/title/text()') != "SSE Airtricity Men's Premier Division Fixtures | League of Ireland"
            or _text(doc, '//h1/text()') != "Men’s Premier Division Fixtures"):
        raise ValueError("LOI senior men's division changed")
    container = doc.xpath('//div[contains(@class,"fixture__items")][@data-bid]')
    if len(container) != 1 or any(container[0].get("data-" + key) != value for key, value in PARAMS.items()):
        raise ValueError("LOI Premier Division fixture endpoint changed")


def parse_pages(responses, source):
    if not responses or len(responses) > 4:
        raise ValueError("LOI fixture pagination incomplete")
    events = []
    ids = set()
    for index, response in enumerate(responses, 1):
        request = response.get("request")
        if not isinstance(request, dict) or any(str(request.get(key)).lower() != value for key, value in PARAMS.items() if key != "header"):
            raise ValueError("LOI competition request changed")
        if str(request.get("header")).lower() not in ("1", "true") or str(request.get("page")) != str(index):
            raise ValueError("LOI fixture page or header changed")
        following = response.get("nextPage")
        if following != (index + 1 if index < len(responses) else 0):
            raise ValueError("LOI fixture pagination changed")
        fragment = response.get("html")
        if not isinstance(fragment, str) or (index < len(responses) and not fragment):
            raise ValueError("LOI fixture response missing")
        doc = html.fromstring("<div>" + fragment + "</div>")
        day = None
        for node in doc:
            if node.tag == "h5" and "fixture__date" in node.get("class", "").split():
                label = " ".join(node.text_content().split())
                try:
                    day = datetime.datetime.strptime(label, "%A %d %B %Y").date()
                except ValueError as exc:
                    raise ValueError("LOI fixture date changed") from exc
                if day.year != 2026:
                    raise ValueError("LOI fixture edition changed")
                continue
            if "fixture__block" not in node.get("class", "").split() or day is None:
                raise ValueError("LOI fixture grouping changed")
            cards = node.xpath('./div[contains(@class,"fixture__section")][@id]')
            if not cards or not all(card.get("id", "").isdigit() for card in cards):
                raise ValueError("LOI fixture ID missing")
            for card in cards:
                match_id = card.get("id")
                names = [_text(card, f'.//div[contains(@class,"fixture__section--content__team--{side}")]/h5/text()')
                         for side in ("home", "away")]
                logos = [card.xpath(f'.//div[contains(@class,"fixture__section--content__team--{side}")]/img/@alt')
                         for side in ("home", "away")]
                venue = _text(card, './/p[contains(@class,"fixture__section--content--details-location")]/text()')
                clock = _text(card, './/p[contains(@class,"fixture__section--content--details-time")]/text()')
                if (match_id in ids or not all(names) or names[0] == names[1]
                        or logos != [[names[0]], [names[1]]] or not venue
                        or not re.fullmatch(r"\d{2}:\d{2}", clock)):
                    raise ValueError("LOI pairing, kickoff, stadium or duplicate ID changed")
                ids.add(match_id)
                start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), DUBLIN)
                events.append({"id": f"loi-premier-{match_id}", "source_id": source["id"],
                    "sport": source["sport"], "league": source["league"], "region": source["region"],
                    "name": f"{names[1]} at {names[0]}",
                    "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "status": "UPCOMING", "status_detail": "Official 2026 men's Premier Division fixture",
                    "season_stage": "REGULAR", "location": venue,
                    "source_endpoint": source["official_schedule_url"]})
    return events
