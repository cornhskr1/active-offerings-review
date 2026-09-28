"""DFB Datencenter's exact senior women's Bundesliga season fixtures."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-germany-frauen-bundesliga-women"
EDITION = "google-pixel-frauen-bundesliga-2026-2027"
BASE = "https://datencenter.dfb.de"
BERLIN = ZoneInfo("Europe/Berlin")
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def parse_season(page, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("DFB women's senior league catalog scope changed")
    doc = html.fromstring(page)
    if _text(doc, '//title/text()') != "Google Pixel Frauen-Bundesliga 2026/27, der Spielplan - DFB Datencenter":
        raise ValueError("DFB women's league edition changed")
    headings = doc.xpath('//h3[contains(text(),"Spieltag")]')
    if len(headings) != 26:
        raise ValueError("DFB women's league matchday count changed")
    events = []
    ids = set()
    held_untimed = 0
    for number, heading in enumerate(headings, 1):
        label = _text(heading, './/text()')
        match = re.fullmatch(rf"{number}\. Spieltag \((\d{{2}}\.\d{{2}}\.20(?:26|27)) - (\d{{2}}\.\d{{2}}\.20(?:26|27))\)", label)
        if not match:
            raise ValueError("DFB women's league matchday label changed")
        first, last = (datetime.datetime.strptime(value, "%d.%m.%Y").date() for value in match.groups())
        block = heading.getparent().getparent().getparent().getparent()
        rows = block.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," c-MatchTable-row ") and ./div[starts-with(@id,"match_")]]')
        if len(rows) != 7:
            raise ValueError("DFB women's league seven-match round changed")
        clubs = set()
        for row in rows:
            match_label = row.xpath('./div[contains(@class,"info--home")]/@id')
            stamp = _text(row, './div[contains(@class,"info--home")]//p/text()')
            homes = row.xpath('./div[contains(@class,"team--home")]/a')
            aways = row.xpath('./div[contains(@class,"team--away")]/a')
            score = _text(row, './div[contains(@class,"c-MatchTable-center")]//div[contains(@class,"score")]/a/text()')
            score_links = row.xpath('./div[contains(@class,"c-MatchTable-center")]//div[contains(@class,"score")]/a/@href')
            if (len(match_label) != 1 or not re.fullmatch(r"match_(\d+)", match_label[0])
                    or match_label[0] in ids or len(homes) != 1 or len(aways) != 1
                    or len(score_links) != 1):
                raise ValueError("DFB women's league match ID or pairing changed")
            match_id = match_label[0][6:]
            names = [_text(node, './text()') for node in (homes[0], aways[0])]
            team_prefix = f"{BASE}/competitions/google-pixel-frauen-bundesliga/seasons/{EDITION}/teams/"
            if (not all(names) or names[0] == names[1] or not all((node.get("href") or "").startswith(team_prefix) for node in (homes[0], aways[0]))
                    or not re.fullmatch(rf"{BASE}/datencenter/google-pixel-frauen-bundesliga/{EDITION}/{number}-spieltag/[a-z0-9-]+-{match_id}", score_links[0])):
                raise ValueError("DFB women's league competition or linked match changed")
            ids.add(match_label[0])
            clubs.update(names)
            if not stamp and score == "- : -":
                held_untimed += 1
                continue
            date_match = re.fullmatch(r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag), (\d{2}\.\d{2}\.20(?:26|27))(?: (\d{2}:\d{2}) Uhr)?", stamp)
            if not date_match:
                raise ValueError("DFB women's league fixture date changed")
            day = datetime.datetime.strptime(date_match.group(2), "%d.%m.%Y").date()
            if not first <= day <= last or WEEKDAYS[day.weekday()] != date_match.group(1):
                raise ValueError("DFB women's league fixture outside round dates")
            if score != "- : -":
                if not re.fullmatch(r"\d+ : \d+", score):
                    raise ValueError("DFB women's league result state changed")
                continue
            if not date_match.group(3):
                held_untimed += 1
                continue
            try:
                local = datetime.datetime.combine(day, datetime.time.fromisoformat(date_match.group(3)), BERLIN)
            except ValueError as exc:
                raise ValueError("DFB women's league kickoff changed") from exc
            events.append({"id": f"dfb-frauen-bundesliga-{match_id}", "source_id": source["id"],
                "sport": source["sport"], "league": source["league"], "region": source["region"],
                "name": f"{names[1]} at {names[0]}",
                "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": f"Official 2026–27 Frauen-Bundesliga matchday {number}",
                "season_stage": "REGULAR", "source_endpoint": score_links[0]})
        if len(clubs) != 14:
            raise ValueError("DFB women's league duplicate round clubs")
    if len(ids) != 182:
        raise ValueError("DFB women's league season fixture count changed")
    return events, held_untimed, len(ids)
