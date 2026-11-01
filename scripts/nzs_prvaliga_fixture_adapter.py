"""NZS senior Prva Liga Telemach next-round fixtures, 2026–27."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-slovenia-slovenian-prvaliga-men"
ROOT_PATH = "/klubi/moski/prva-liga-telemach/tekme/"
LJUBLJANA = ZoneInfo("Europe/Ljubljana")
ROUND14 = {
    'dns-mura-nk-brinje-grosuplje-1snl2627-2026-11-01-150000': ('Mura', 'Brinje Grosuplje', '2026-11-01', '15:00', 'Mestni stadion Fazanerija'),
    'nk-celje-nd-lendava-1903-1snl2627-2026-11-01-173000': ('Celje', 'Nafta 1903', '2026-11-01', '17:30', "Štadion Z'dežele"),
    'nk-bravo-fc-koper-1snl2627-2026-11-02-170000': ('Bravo Ljubljana', 'Koper', '2026-11-02', '17:00', 'Stadion Stožice Ljubljana'),
    'nk-aluminij-kidricevo-nk-radomlje-1snl2627-2026-10-31-180000': ('Aluminij', 'Kalcer Radomlje', '2026-10-31', '18:00', None),
    'nk-maribor-branik-sd-nk-olimpija-ljubljana-1snl2627-2026-10-31-160000': ('Maribor', 'Olimpija Ljubljana', '2026-10-31', '16:00', None),
}
# Separately reviewed completed November 1 games, not a renewal of round scope.
NOV1_RESULTS = {
    'dns-mura-nk-brinje-grosuplje-1snl2627-2026-11-01-150000': '0 : 0 (0 : 0)',
    'nk-celje-nd-lendava-1903-1snl2627-2026-11-01-173000': '4 : 0 (3 : 0)',
}


def _document(page):
    doc = html.fromstring(page)
    for node in doc.xpath("//script|//style"):
        node.drop_tree()
    return doc


def _text(node, query):
    return ' '.join(' '.join(node.xpath(query)).split())


def _reviewed_round14(rows, today, observed_at):
    if not datetime.date(2026, 10, 31) <= today <= datetime.date(2026, 11, 2):
        raise ValueError('NZS reviewed round-14 window expired')
    now = observed_at if observed_at is not None else datetime.datetime.now(datetime.timezone.utc)
    if not isinstance(now, datetime.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('NZS aware observation clock required')
    selected = [row for row in rows if re.search(r'\bKrog\s+14\b', _text(row, './/text()'))]
    if len(selected) != 5:
        raise ValueError('NZS reviewed five-match round incomplete')
    seen = set(); clubs = set(); fixtures = []
    for row in selected:
        actions = row.xpath('.//div[@class="actions"]/a[@aria-label="Podrobnosti"]/@href')
        if len(actions) != 1 or actions[0] not in [ROOT_PATH + key for key in ROUND14]:
            raise ValueError('NZS reviewed match identity changed')
        path = actions[0]; key = path.rsplit('/', 1)[-1]
        if key in seen:
            raise ValueError('NZS duplicate reviewed match')
        seen.add(key)
        home, away, date, clock, venue = ROUND14[key]
        names = [' '.join(n.text_content().split()) for n in row.xpath('.//h5[contains(@class,"match-team-name")]')]
        if (names != [home, away] or row.xpath('.//time[@class="date"]/@datetime') != [date]
                or row.xpath('.//time[@class="time"]/@datetime') != [clock]
                or _text(row, './/div[@class="match-category"]//text()') != 'Prva liga Telemach'):
            raise ValueError('NZS reviewed pairing, kickoff or league changed')
        clubs.update(names)
        start = datetime.datetime.combine(datetime.date.fromisoformat(date), datetime.time.fromisoformat(clock), LJUBLJANA)
        links = row.xpath('.//a[contains(@href,"/prva-liga-telemach/tekme/")]/@href')
        scores = row.xpath('.//strong[@class="match-score"]')
        locations = row.xpath('.//strong[@class="match-location"]')
        if venue is not None:
            if scores:
                if (today != datetime.date(2026, 11, 1) or key not in NOV1_RESULTS
                        or len(scores) != 1 or locations or links != [path, path]
                        or scores[0].getparent().tag != 'a' or scores[0].getparent().get('href') != path
                        or ' '.join(scores[0].text_content().split()) != NOV1_RESULTS[key]
                        or start >= now):
                    raise ValueError('NZS unreviewed or future November scored result')
                continue
            if scores or links != [path] or len(locations) != 1 or ' '.join(locations[0].text_content().split()) != venue:
                raise ValueError('NZS reviewed fixture state or stadium changed')
            fixtures.append((start.date(), 14, path, names, venue, clock))
        elif (len(scores) != 1 or locations or links != [path, path]
              or scores[0].getparent().tag != 'a' or scores[0].getparent().get('href') != path
              or not re.fullmatch(r'\d{1,2} : \d{1,2} \(\d{1,2} : \d{1,2}\)', ' '.join(scores[0].text_content().split()))
              or start > now):
            raise ValueError('NZS unknown or future scored result')
    if seen != set(ROUND14) or len(clubs) != 10:
        raise ValueError('NZS reviewed round identities changed')
    # Later rounds, including their untimed placeholders, remain held.
    return fixtures, len(rows)


def next_round(page, source, today, observed_at=None):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("NZS catalog scope changed")
    doc = _document(page)
    if "2026/2027" not in " ".join(doc.xpath("//body//text()")):
        raise ValueError("NZS 2026–27 league edition changed")
    rows = doc.xpath('//tr[contains(@class,"match-tbody-tr")][.//div[contains(@class,"upcoming-match-date")]]')
    if len(rows) < 5:
        raise ValueError("NZS upcoming league page incomplete")
    if today >= datetime.date(2026, 10, 31):
        return _reviewed_round14(rows, today, observed_at)
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
