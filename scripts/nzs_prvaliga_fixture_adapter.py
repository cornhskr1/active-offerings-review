"""NZS senior Prva Liga Telemach next-round fixtures, 2026–27."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-slovenia-slovenian-prvaliga-men"
ROOT_PATH = "/klubi/moski/prva-liga-telemach/tekme/"
LJUBLJANA = ZoneInfo("Europe/Ljubljana")


def _document(page):
    doc = html.fromstring(page)
    for node in doc.xpath("//script|//style"):
        node.drop_tree()
    return doc


def next_round(page, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("NZS catalog scope changed")
    doc = _document(page)
    if "2026/2027" not in " ".join(doc.xpath("//body//text()")):
        raise ValueError("NZS 2026–27 league edition changed")
    rows = doc.xpath('//tr[contains(@class,"match-tbody-tr")][.//div[contains(@class,"upcoming-match-date")]]')
    if len(rows) < 5:
        raise ValueError("NZS upcoming league page incomplete")
    parsed = []
    for row in rows:
        date = row.xpath('string(.//time[contains(@class,"date")]/@datetime)').strip()
        if not re.fullmatch(r"202[67]-\d{2}-\d{2}",date):
            raise ValueError("NZS fixture date changed")
        if datetime.date.fromisoformat(date) < today:
            continue
        clock = row.xpath('string(.//time[contains(@class,"time")]/@datetime)').strip()
        names = [" ".join(x.itertext()).strip() for x in row.xpath('.//h5[contains(@class,"match-team-name")]')]
        venue = row.xpath('string(.//strong[contains(@class,"match-location")])').strip()
        category = " ".join(row.xpath('.//div[contains(@class,"match-category")]//text()')).strip()
        round_text = " ".join(" ".join(row.xpath('.//text()')).split())
        round_match = re.search(r"\bKrog\s+(\d+)\b",round_text)
        link = row.xpath('.//a[contains(@href,"/prva-liga-telemach/tekme/")]/@href')
        if (not re.fullmatch(r"\d{2}:\d{2}",clock) or len(names)!=2 or
            not all(names) or not venue or "Prva liga Telemach" not in category or
            not round_match or len(link)!=1):
            raise ValueError("NZS senior fixture fields changed")
        expected = f"-1snl2627-{date}-{clock.replace(':','')}00"
        if not link[0].startswith(ROOT_PATH) or not link[0].endswith(expected):
            raise ValueError("NZS fixture edition or kickoff link changed")
        parsed.append((datetime.date.fromisoformat(date),int(round_match.group(1)),
                       link[0],names,venue,clock))
    upcoming = [item for item in parsed if item[0]>=today]
    if not upcoming:
        return [],len(rows)
    first_round = min(item[1] for item in upcoming)
    selected = [item for item in upcoming if item[1]==first_round]
    if len(selected)!=5 or len({name for item in selected for name in item[3]})!=10:
        raise ValueError("NZS five-match senior round changed")
    return selected,len(rows)


def verified_match(page, fixture, source):
    day,round_number,path,names,venue,clock = fixture
    doc = _document(page)
    competition = " ".join(" ".join(doc.xpath('//div[contains(@class,"cover-competition")]//text()')).split())
    if competition != f"PRVA LIGA TELEMACH 26/27 {round_number}. krog":
        raise ValueError("NZS match competition or round changed")
    page_names = [" ".join(x.itertext()).strip() for x in doc.xpath(
        '//div[contains(@class,"cover-match-data-team")]//span[contains(@class,"team-name")]/a')]
    date_text = " ".join(doc.xpath('//div[contains(@class,"cover-match-info-date")]/span/text()')).strip()
    page_venue = " ".join(" ".join(doc.xpath('//div[contains(@class,"cover-match-info")]//text()')).split())
    if page_names!=names or date_text!=f"{day:%d.%m.%Y}, {clock}" or venue not in page_venue:
        raise ValueError("NZS match pairing, kickoff or venue changed")
    start=datetime.datetime.combine(day,datetime.time.fromisoformat(clock),LJUBLJANA)
    return {"id":f"nzs-prvaliga-{path.rsplit('/',1)[-1]}","source_id":source["id"],
        "sport":source["sport"],"league":source["league"],"region":source["region"],
        "name":f"{names[1]} at {names[0]}",
        "start_time":start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
        "status":"UPCOMING","status_detail":"Official 2026–27 Prva Liga Telemach next round",
        "season_stage":"REGULAR","location":venue,
        "source_endpoint":"https://www.nzs.si"+path}
