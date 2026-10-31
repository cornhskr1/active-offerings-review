"""KSÍ 2026 men's Besta deild: verify both final groups' next complete round."""

import datetime
import re
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-iceland-besta-deild-karla-rvalsdeild-men"
PHASES = {"7025527": "Efri hluti", "7025532": "Neðri hluti"}
MONTHS = {"september": 9, "október": 10}
COMPLETED_CLUBS = {
    "7025527": {"5364": "Víkingur R.", "5366": "Fram", "5387": "Breiðablik",
                "5698": "KR", "5735": "ÍA", "5964": "Keflavík"},
    "7025532": {"5363": "Valur", "5388": "ÍBV", "5730": "Stjarnan",
                "5731": "KA", "5733": "FH", "5965": "Þór"},
}
COMPLETED_MATCHES = {"7025527": set(map(str, range(7100149, 7100164))),
                     "7025532": set(map(str, range(7100283, 7100298)))}
REYKJAVIK = ZoneInfo("Atlantic/Reykjavik")


def urls(competition_id):
    base = f"https://www.ksi.is/oll-mot/mot?banner-tab=matches-and-results&id={competition_id}"
    return base, base + "&toggle=rounds"


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def _cards(doc, competition_id):
    phase = PHASES[competition_id]
    title = f"Besta deild karla 2026 - {phase}"
    if _text(doc, '//h1/text()') != title:
        raise ValueError("KSÍ senior 2026 phase changed")
    cards = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," grid-cols-[70%_auto] ")]')
    if len(cards) > 15 or len(cards) % 3:
        raise ValueError("KSÍ final-group fixtures incomplete")
    result = []
    for card in cards:
        info = card.xpath('./div[1]')
        teams = card.xpath('./div[contains(@class,"grid-cols-[1fr_auto_1fr]")]')
        if len(info) != 1 or len(teams) != 1:
            raise ValueError("KSÍ fixture structure changed")
        spans = info[0].xpath('.//span[contains(@class,"body-5")]')
        date_text = " ".join(spans[0].text_content().split()) if spans else ""
        match = re.fullmatch(r"\S+ (\d{1,2})\. (\S+)\s+(\d{2}:\d{2})", date_text)
        venue = " ".join(spans[1].text_content().split()) if len(spans) >= 2 else ""
        label = " ".join(spans[2].text_content().split()) if len(spans) >= 3 else ""
        links = teams[0].xpath('./a')
        if (not match or match.group(2) not in MONTHS or not venue or label != title
                or len(links) != 2):
            raise ValueError("KSÍ date, venue or competition changed")
        ids = []
        names = []
        for link in links:
            url = urlsplit(link.get("href", ""))
            qs = parse_qs(url.query)
            if (url.path != "/oll-mot/mot/lid" or qs.get("competitionId") != [competition_id]
                    or len(qs.get("id", [])) != 1 or not qs["id"][0].isdigit()):
                raise ValueError("KSÍ senior team link changed")
            ids.append(qs["id"][0])
            names.append(" ".join(link.text_content().split()))
        if not all(names) or len(set(ids)) != 2:
            raise ValueError("KSÍ pairing changed")
        day = datetime.date(2026, MONTHS[match.group(2)], int(match.group(1)))
        result.append((day, match.group(3), venue, names, ids, competition_id))
    return result


def _completed_results(doc, competition_id, today):
    rows = _cards(doc, competition_id)
    cards = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," grid-cols-[70%_auto] ")]')
    results, pairings = {}, set()
    for card, row in zip(cards, rows):
        day, clock, venue, names, ids, _ = row
        scores = card.xpath('./div[contains(@class,"grid-cols-[1fr_auto_1fr]")]/span/text()')
        links = set(card.xpath('.//a[contains(@href,"/leikir-og-urslit/felagslid/leikur")]/@href'))
        if len(links) != 1 or len(scores) != 1 or not re.fullmatch(r"\d+ - \d+", scores[0].strip()):
            raise ValueError("KSÍ completed result identity or score changed")
        link = urlsplit(links.pop())
        query = parse_qs(link.query)
        mid = query.get("id", [None])[0]
        if (link.path != "/leikir-og-urslit/felagslid/leikur" or query != {"id": [mid]}
                or mid not in COMPLETED_MATCHES[competition_id] or mid in results
                or any(COMPLETED_CLUBS[competition_id].get(cid) != name for cid, name in zip(ids, names))
                or not datetime.date(2026, 9, 13) <= day <= datetime.date(2026, 10, 24)
                or day >= today):
            raise ValueError("KSÍ completed result scope or date changed")
        pairing = frozenset(ids)
        if pairing in pairings:
            raise ValueError("KSÍ completed pairing duplicated")
        pairings.add(pairing)
        results[mid] = (day, clock, venue, tuple(names), tuple(ids), scores[0].strip())
    return results


def _completed_final_groups(pages, today):
    # A scored response must prove the whole bounded season; never emit scores as fixtures.
    docs = {cid: tuple(html.fromstring(p.decode("utf-8") if isinstance(p, bytes) else p)
                       for p in pages[cid]) for cid in PHASES}
    if not any(re.fullmatch(r"\d+ - \d+", score.strip())
               for pair in docs.values() for doc in pair
               for score in doc.xpath('//div[contains(@class,"grid-cols-[1fr_auto_1fr]")]/span/text()')):
        return False
    for cid, (all_doc, round_doc) in docs.items():
        results = _completed_results(all_doc, cid, today)
        final = _completed_results(round_doc, cid, today)
        if (set(results) != COMPLETED_MATCHES[cid] or len(final) != 3
                or _text(round_doc, '//button[contains(@class,"link-dropdown-trigger")]/span/text()') != "Umferð 5"
                or any(results.get(mid) != row or row[0] != datetime.date(2026, 10, 24)
                       for mid, row in final.items())
                or len({club for row in final.values() for club in row[4]}) != 6):
            raise ValueError("KSÍ completed final-group evidence incomplete")
    return True


def next_round(pages, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("KSÍ catalog scope changed")
    if _completed_final_groups(pages, today):
        return [], 0, 0
    selected = []
    page_count = 0
    held = 0
    round_numbers = set()
    for competition_id in PHASES:
        upcoming, round_page = pages[competition_id]
        upcoming_doc = html.fromstring(upcoming.decode("utf-8") if isinstance(upcoming, bytes) else upcoming)
        rounds_doc = html.fromstring(round_page.decode("utf-8") if isinstance(round_page, bytes) else round_page)
        cards = _cards(upcoming_doc, competition_id)
        round_cards = _cards(rounds_doc, competition_id)
        page_count += len(cards)
        if not cards and not round_cards:
            continue
        heading = _text(rounds_doc, '//button[contains(@class,"link-dropdown-trigger")]/span/text()')
        match = re.fullmatch(r"Umferð ([1-5])", heading)
        if (not match or len(round_cards) != 3 or cards[:3] != round_cards
                or any(row[0] < today for row in round_cards)
                or len({club for row in round_cards for club in row[4]}) != 6):
            raise ValueError("KSÍ next complete phase round changed")
        round_numbers.add(int(match.group(1)))
        selected.extend(round_cards)
        held += len(cards) - 3
    if selected and (len(selected) != 6 or len(round_numbers) != 1):
        raise ValueError("KSÍ upper and lower final groups disagree")
    number = round_numbers.pop() if round_numbers else None
    fixtures = []
    for day, clock, venue, names, ids, competition_id in selected:
        start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), REYKJAVIK)
        fixtures.append({"id": f"ksi-besta-{competition_id}-{day:%Y%m%d}-{ids[0]}-{ids[1]}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{names[1]} at {names[0]}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026 Besta deild final group round {number} ({PHASES[competition_id]})",
            "season_stage": "FINAL GROUP", "location": venue,
            "source_endpoint": urls(competition_id)[0]})
    return fixtures, page_count, held
