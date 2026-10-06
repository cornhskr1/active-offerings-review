"""Read exact ADNOC 2026/27 league rows from the publisher's fixture-filter API."""
import datetime
import json
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from lxml import html

DUBAI = ZoneInfo('Asia/Dubai')


def _norm(value):
    return ' '.join(str(value or '').replace('\xa0',' ').split())


def _scope(source):
    if source.get('id') != 'soccer-afc-united-arab-emirates-uae-pro-league-men' or source.get('league') != 'UAE Pro League | Men' or source.get('catalog_terms') != ['UAE Pro League | Men']:
        raise ValueError('UAE league catalog scope changed')


def discover_league_competition(page, source):
    _scope(source)
    doc=html.fromstring(page,parser=html.HTMLParser(encoding='utf-8'))
    selected=doc.xpath('//select[contains(concat(" ",normalize-space(@class)," ")," filterseason ")]/option[@selected]')
    seasons={(n.get('value'),_norm(n.text_content())) for n in selected}
    if len(seasons)!=1 or next(iter(seasons))[1]!='2026/2027':
        raise ValueError('UAE fixture directory edition missing or changed')
    season_id=next(iter(seasons))[0]
    scripts=doc.xpath('//script[not(@src)]/text()')
    matching=[t for t in scripts if re.search(r'\bvar\s+season\s*=\s*',t)]
    if len(matching)!=1:
        raise ValueError('UAE competition directory missing or ambiguous')
    marker=re.search(r'\bvar\s+season\s*=\s*',matching[0])
    mapping,_=json.JSONDecoder().raw_decode(matching[0][marker.end():])
    matches=[r for r in mapping.get(season_id,[]) if r.get('name')=='ADNOC PRO LEAGUE']
    if len(matches)!=1 or not re.fullmatch(r'[a-f0-9-]{36}',matches[0].get('id','')):
        raise ValueError('Exact ADNOC season competition not identified')
    return matches[0]['id']


def parse_league_matches(payload, source):
    _scope(source)
    if not isinstance(payload,dict) or not isinstance(payload.get('html'),str):
        raise ValueError('UAE fixture response missing HTML')
    doc=html.fromstring('<main>'+payload['html']+'</main>')
    rows=doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," upcomingMatches__box ")]')
    if not rows:
        raise ValueError('UAE league payload contains no fixture records')
    events,held,completed,seen,seen_pairs=[],0,0,set(),set()
    for row in rows:
        labels=row.xpath('.//img[contains(concat(" ",normalize-space(@class)," ")," upcomingMatches__chanel-logo ")]/@alt')
        if labels!=['ADNOC PRO LEAGUE']:
            raise ValueError('UAE response includes another competition; league scope unverified')
        match_id=row.get('id','')
        clubs=row.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," upcomingMatches__club-name ")]')
        names=[_norm(n.text_content()) for n in clubs]
        if len(names)!=2 or names[0]==names[1] or any(not n or re.search(r'\b(?:TBC|TBD|U\d{2})\b',n,re.I) for n in names):
            raise ValueError('UAE fixture opponents unidentified')
        dates=[_norm(n.text_content()) for n in row.xpath('.//time/span[contains(concat(" ",normalize-space(@class)," ")," upcomingMatches__time-info-date ")]')]
        week=next((m.group(1) for t in dates if (m:=re.fullmatch(r'GW(\d+)',t))),None)
        if not week or not 1<=int(week)<=26:
            raise ValueError('UAE league round missing or outside regular season')
        pairing=(week,*names)
        if pairing in seen_pairs:
            raise ValueError('UAE round pairing duplicated')
        seen_pairs.add(pairing)
        statuses=[_norm(n.text_content()) for n in row.xpath('.//span[@class="upcomingMatches__time-top"]')]
        clocks=[_norm(n.text_content()) for n in row.xpath('.//time/span[@class="upcomingMatches__time-info-num"]')]
        if clocks==['TBC'] and not statuses:
            held+=1
            continue
        if not re.fullmatch(r'matchList_[a-z0-9]+',match_id) or match_id in seen:
            raise ValueError('UAE timed fixture identifier missing or duplicate')
        seen.add(match_id)
        if statuses==['FT']:
            completed+=1
            continue
        if statuses:
            raise ValueError('UAE fixture status unsupported')
        if len(clocks)!=1 or not re.fullmatch(r'\d{2}:\d{2}',clocks[0]):
            raise ValueError('UAE fixture kickoff missing or ambiguous')
        date_texts=[t for t in dates if re.fullmatch(r'[A-Za-z]{3} \d{1,2} [A-Za-z]{3} \d{4}',t)]
        if len(date_texts)!=1:
            raise ValueError('UAE fixture full date missing')
        date=datetime.datetime.strptime(date_texts[0],'%a %d %b %Y').date()
        if date.strftime('%a')!=date_texts[0].split()[0] or not datetime.date(2026,7,1)<=date<=datetime.date(2027,6,30):
            raise ValueError('UAE fixture date/edition inconsistent')
        links=row.xpath('.//div[@class="upcomingMatches__right"]//a/@href')
        if len(links)!=1 or urlparse(links[0]).hostname!='www.uaeproleague.ae' or not re.fullmatch(r'/en/fixtures/[a-f0-9-]{36}',urlparse(links[0]).path):
            raise ValueError('UAE fixture detail identity missing')
        venue=_norm(row.xpath('string(.//span[@class="upcomingMatches__stadium-name"])'))
        local=datetime.datetime.combine(date,datetime.time.fromisoformat(clocks[0]),DUBAI)
        events.append(dict(id='uae-league-'+match_id.removeprefix('matchList_'),source_id=source['id'],
            sport=source['sport'],league=source['league'],region=source['region'],name=f'{names[1]} at {names[0]}',
            start_time=local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00','Z'),
            status='UPCOMING',status_detail='Official ADNOC league fixture',season_stage='ROUND '+week,
            location=venue or None,source_endpoint=links[0]))
    return events,held,completed,len(rows)
