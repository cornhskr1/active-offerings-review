#!/usr/bin/env python3
from pathlib import Path
import json, datetime, requests, re, time, html
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA/"global-schedule-sources.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Chicago")
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()
END = TODAY + datetime.timedelta(days=int(CFG.get("window_days",7)))
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

def thesportsdb_json(endpoint, params):
    """Pace and retry the public feed so transient throttling does not erase leagues."""
    time.sleep(2.1)
    last_error = None
    for attempt in range(4):
        try:
            r=requests.get(endpoint,params=params,headers=HEADERS,timeout=18)
            if r.status_code==429:
                retry_after=r.headers.get("Retry-After")
                wait=float(retry_after) if retry_after and retry_after.isdigit() else 3.0*(attempt+1)
                time.sleep(min(wait,12.0))
                last_error=RuntimeError("TheSportsDB rate limit persisted after retry")
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last_error=exc
            if attempt<3:
                time.sleep(2.0*(attempt+1))
    raise last_error or RuntimeError("TheSportsDB request failed")

def catalog_blob():
    p = DATA/"catalog-live.json"
    if not p.exists():
        return ""
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        parts=[]
        for s in d.get("sections",[]):
            parts.append(s.get("sport",""))
            parts.extend(s.get("lines",[]))
        return " ".join(parts).lower()
    except Exception:
        return ""

CATALOG = catalog_blob()

def approved(source):
    terms=[str(x).lower() for x in source.get("catalog_terms",[])]
    if not CATALOG:
        # Catalog unavailable: do not silently declare source approved.
        return None
    return any(t in CATALOG for t in terms)

def event_status(ev):
    st=(ev.get("status") or {}).get("type") or {}
    state=(st.get("state") or "").lower()
    detail=st.get("shortDetail") or st.get("detail") or ""
    completed=bool(st.get("completed"))
    if completed or state=="post":
        return "COMPLETED", detail
    if state=="in":
        return "LIVE", detail
    return "UPCOMING", detail

def parse_event(source, ev):
    comps=ev.get("competitions") or []
    comp=comps[0] if comps else {}
    competitors=comp.get("competitors") or []
    home=None; away=None; participant_names=[]
    for c in competitors:
        entity=c.get("team") or c.get("athlete") or {}
        name=(
            entity.get("displayName")
            or entity.get("fullName")
            or entity.get("shortDisplayName")
            or entity.get("shortName")
            or entity.get("name")
        )
        if name:
            participant_names.append(name)
        if c.get("homeAway")=="home": home=name
        elif c.get("homeAway")=="away": away=name
    name=ev.get("name") or ev.get("shortName") or "Scheduled event"
    if home and away:
        name=f"{away} at {home}"
    elif len(participant_names)>=2:
        name=f"{participant_names[0]} vs {participant_names[1]}"
    dt=ev.get("date")
    status,detail=event_status(ev)

    season_type=(
        (ev.get("season") or {}).get("type")
        or (comp.get("type") or {}).get("abbreviation")
        or (comp.get("type") or {}).get("name")
        or (comp.get("type") or {}).get("text")
    )
    season_slug=str(season_type or "").upper()
    if season_slug in ("1","PRE","PRESEASON") or "PRESEASON" in season_slug:
        season_stage="PRESEASON"
    elif season_slug in ("2","REG","REGULAR","REGULAR SEASON") or "REGULAR" in season_slug:
        season_stage="REGULAR SEASON"
    elif season_slug in ("3","POST","POSTSEASON","PLAYOFFS") or "POST" in season_slug or "PLAYOFF" in season_slug:
        season_stage="POSTSEASON"
    else:
        season_stage=None

    # NFL 2026 authoritative date-stage fallback for this review system.
    # The source payload has shown inconsistent stage metadata. For the 2026
    # season, use the actual event date as the final scope control.
    if source.get("league")=="NFL" and dt:
        try:
            event_date=datetime.datetime.fromisoformat(str(dt).replace("Z","+00:00")).date()
            if event_date >= datetime.date(2026,9,9):
                season_stage="REGULAR SEASON"
            elif datetime.date(2026,8,1) <= event_date < datetime.date(2026,9,9):
                season_stage="PRESEASON"
        except Exception:
            pass

    venue=(comp.get("venue") or {}).get("fullName")
    address=(comp.get("venue") or {}).get("address") or {}
    location=", ".join(x for x in [address.get("city"),address.get("state"),address.get("country")] if x)
    if venue and location:
        location=f"{venue} · {location}"
    elif venue:
        location=venue
    parsed = {
        "id":str(ev.get("id") or f'{source["id"]}-{dt}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":dt,
        "status":status,
        "status_detail":detail,
        "season_stage":season_stage,
        "location":location or None,
        "source_endpoint":source["endpoint"]
    }
    # Cricket fixtures can remain live for several days. Keep the official
    # first-ball timestamp for auditability, but anchor an active match to the
    # current review day so it remains visible in Review Today.
    if source.get("sport")=="Cricket" and status=="LIVE" and dt:
        try:
            original=datetime.datetime.fromisoformat(str(dt).replace("Z","+00:00"))
            if original.astimezone(TZ).date()<TODAY:
                parsed["original_start_time"]=dt
                review_time=datetime.datetime.combine(TODAY,datetime.time(0,1),tzinfo=TZ)
                parsed["start_time"]=review_time.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
                parsed["status_detail"]=f"Live · began {original.astimezone(TZ).date().isoformat()}"
        except Exception:
            pass
    return parsed

def parse_thesportsdb_event(source, ev):
    timestamp=ev.get("strTimestamp")
    if timestamp and not str(timestamp).endswith("Z"):
        timestamp=f"{timestamp}Z"
    if not timestamp:
        date=ev.get("dateEvent")
        time=ev.get("strTime") or "12:00:00"
        timestamp=f"{date}T{time}Z" if date else None
    home=ev.get("strHomeTeam")
    away=ev.get("strAwayTeam")
    name=f"{away} at {home}" if home and away else (ev.get("strEvent") or "Scheduled event")
    raw_status=str(ev.get("strStatus") or "").upper()
    status="COMPLETED" if raw_status in ("FT","AET","MATCH FINISHED","FINISHED") else "UPCOMING"
    venue=ev.get("strVenue")
    country=ev.get("strCountry")
    location=" · ".join(x for x in (venue,country) if x) or None
    return {
        "id":str(ev.get("idEvent") or f'{source["id"]}-{timestamp}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":timestamp,
        "status":status,
        "status_detail":ev.get("strStatus") or "Scheduled",
        "season_stage":None,
        "location":location,
        "source_endpoint":source["endpoint"]
    }

def parse_mlbstats_event(source, game):
    teams=game.get("teams") or {}
    home=((teams.get("home") or {}).get("team") or {}).get("name")
    away=((teams.get("away") or {}).get("team") or {}).get("name")
    name=f"{away} at {home}" if home and away else "Scheduled event"
    status_obj=game.get("status") or {}
    abstract=str(status_obj.get("abstractGameState") or "").lower()
    status="COMPLETED" if abstract=="final" else ("LIVE" if abstract=="live" else "UPCOMING")
    venue=(game.get("venue") or {}).get("name")
    return {
        "id":str(game.get("gamePk") or f'{source["id"]}-{game.get("gameDate")}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":game.get("gameDate"),
        "status":status,
        "status_detail":status_obj.get("detailedState") or "Scheduled",
        "season_stage":None,
        "location":venue,
        "source_endpoint":source["endpoint"]
    }

def plain_html(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def boxing_region(location):
    low=(location or "").lower()
    if any(x in low for x in ("england","scotland","wales","northern ireland","united kingdom")):
        return "United Kingdom"
    us_markers=(
        "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
        "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
        "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
        "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
        "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
        "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
        "virginia","washington","west virginia","wisconsin","wyoming","united states","u.s."
    )
    if any(x in low for x in us_markers):
        return "United States"
    aliases={"mexico":"Mexico","canada":"Canada","japan":"Japan","australia":"Australia","puerto rico":"Puerto Rico"}
    for needle,label in aliases.items():
        if needle in low:
            return label
    return "International"

def boxing_authorities(text):
    checks=[
        (r"\bIBF\b|International Boxing Federation","IBF"),
        (r"\bWBA\b|World Boxing Association","WBA"),
        (r"\bWBC\b|World Boxing Council","WBC"),
        (r"\bWBO\b|World Boxing Organization","WBO"),
        (r"\bBBBofC\b|British Boxing Board of Control","BBBofC"),
        (r"\bBKFC\b|Bare Knuckle Fighting Championship","BKFC"),
        (r"Most Valuable Promotions|\bMVP\b","MVP")
    ]
    return [label for pattern,label in checks if re.search(pattern,text or "",re.I)]

def parse_boxing_rss(source):
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=25)
    r.raise_for_status()
    root=ET.fromstring(r.content)
    ns={"a":"http://www.w3.org/2005/Atom"}
    parsed=[]
    for entry in root.findall("a:entry",ns):
        title=entry.findtext("a:title",default="",namespaces=ns)
        content=entry.findtext("a:content",default="",namespaces=ns)
        year_match=re.search(r"\b(20\d{2})\b",title)
        year=int(year_match.group(1)) if year_match else TODAY.year
        headings=list(re.finditer(r"<(h[23])[^>]*>(.*?)</\1>",content,re.I|re.S))
        current_date=None
        for idx,match in enumerate(headings):
            tag=match.group(1).lower()
            label=plain_html(match.group(2))
            if tag=="h2":
                clean=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",label,flags=re.I)
                clean=re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*","",clean,flags=re.I)
                try:
                    current_date=datetime.datetime.strptime(f"{clean} {year}","%B %d %Y").date()
                except ValueError:
                    current_date=None
                continue
            if tag!="h3" or not current_date or not re.search(r"\b(vs\.?|v\.)\b",label,re.I):
                continue
            if current_date<TODAY or current_date>END:
                continue
            next_start=headings[idx+1].start() if idx+1<len(headings) else len(content)
            raw_context=content[match.end():next_start]
            context=plain_html(raw_context)
            time_match=re.search(r"(\d{1,2}:\d{2})\s*(am|pm)\s*ET",label,re.I)
            clock="12:00 pm"
            if time_match:
                clock=f"{time_match.group(1)} {time_match.group(2).lower()}"
            local=datetime.datetime.strptime(f"{current_date.isoformat()} {clock}","%Y-%m-%d %I:%M %p").replace(tzinfo=ZoneInfo("America/New_York"))
            start_time=local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
            fight=re.sub(r"\s*\([^)]*(?:am|pm)\s+ET[^)]*\)\s*$","",label,flags=re.I).strip()
            loc_match=re.search(r"\bFrom\s+(.+?)(?:\.|,\s+for\b)",context,re.I)
            location=loc_match.group(1).strip() if loc_match else None
            first_para_match=re.search(r"<p[^>]*>(.*?)</p>",raw_context,re.I|re.S)
            bout_description=plain_html(first_para_match.group(1)) if first_para_match else ""
            authority_context=f"{label} {bout_description}"
            slug=re.sub(r"[^a-z0-9]+","-",fight.lower()).strip("-")
            parsed.append({
                "id":f'{source["id"]}-{current_date.isoformat()}-{slug}',
                "source_id":source["id"],
                "sport":"Boxing",
                "league":source["league"],
                "region":boxing_region(location),
                "name":fight,
                "start_time":start_time,
                "status":"UPCOMING",
                "status_detail":"Bout-level authority review required",
                "season_stage":None,
                "location":location,
                "reported_authorities":boxing_authorities(authority_context),
                "source_endpoint":source["endpoint"]
            })
    return parsed

UCI_DISCIPLINES=("ROA","PIS","MTB","TRI","CRO","GRA","BMX","IND","BFR")
UCI_CONTINENT_SOURCES={
    "AFR":("cycling-uci-africa-tour","UCI African Tour"),
    "AME":("cycling-uci-america-tour","UCI America Tour"),
    "ASI":("cycling-uci-asia-tour","UCI Asia Tour"),
    "EUR":("cycling-uci-europe-tour","UCI Europe Tour"),
    "OCE":("cycling-uci-oceania-tour","UCI Oceania Tour"),
}
UCI_NAMED_ROAD={
    "tour de france":("cycling-tour-de-france","Tour de France"),
    "giro d'italia":("cycling-giro-ditalia","Giro d’Italia"),
    "la vuelta ciclista a españa":("cycling-vuelta","Vuelta a España / La Vuelta"),
    "milano-sanremo":("cycling-milan-san-remo","Milan-San Remo"),
    "ronde van vlaanderen":("cycling-tour-flanders","Tour of Flanders"),
    "paris-roubaix hauts-de-france":("cycling-paris-roubaix","Paris-Roubaix"),
    "liège-bastogne-liège":("cycling-liege-bastogne-liege","Liège-Bastogne-Liège"),
    "il lombardia":("cycling-il-lombardia","Il Lombardia / Giro di Lombardia"),
    "mapei cadel evans great ocean road race - men":("cycling-cadel-evans","Cadel Evans Great Ocean Road Race"),
    "uae tour":("cycling-uae-tour","UAE Tour"),
    "grand prix cycliste de québec":("cycling-gp-quebec","Grand Prix Cycliste de Québec"),
    "grand prix cycliste de montréal":("cycling-gp-montreal","Grand Prix Cycliste de Montréal"),
    "tour of guangxi":("cycling-tour-guangxi","Tour of Guangxi"),
}

def parse_uci_date_range(value):
    text=str(value or "").strip().replace("–","-")
    parts=[x.strip() for x in text.split(" - ")]
    try:
        if len(parts)==1:
            day=datetime.datetime.strptime(parts[0],"%d %b %Y").date()
            return day,day
        end=datetime.datetime.strptime(parts[-1],"%d %b %Y").date()
        start_text=parts[0]
        try:
            start=datetime.datetime.strptime(start_text,"%d %b %Y").date()
        except ValueError:
            start=datetime.datetime.strptime(f"{start_text} {end.year}","%d %b %Y").date()
            if start>end:
                start=start.replace(year=end.year-1)
        return start,end
    except (TypeError,ValueError):
        return None,None

def uci_country_map(payload):
    for filter_item in payload.get("filters") or []:
        if filter_item.get("queryParam")!="country":
            continue
        return {
            item.get("code"):str(item.get("text") or "").title()
            for item in filter_item.get("items") or [] if item.get("code")
        }
    return {}

def uci_country_labels(source):
    url=source.get("official_schedule_url") or "https://www.uci.org/calendar/all/2jnxYAuvjgttyHi6YQ94EJ"
    r=requests.get(url,headers=HEADERS,timeout=30)
    r.raise_for_status()
    match=re.search(r'<div[^>]*data-component="CalendarModule"[^>]*data-props="([^"]*)"',r.text)
    if not match:
        return {}
    props=json.loads(html.unescape(match.group(1)))
    return uci_country_map(props)

def uci_calendar_items(payload):
    found=[]
    seen=set()
    for month in payload.get("items") or []:
        for day in month.get("items") or []:
            for item in day.get("items") or []:
                link=((item.get("detailsLink") or {}).get("url") or "").strip()
                key=link or f'{item.get("name")}|{item.get("dates")}|{item.get("country")}'
                if key in seen:
                    continue
                seen.add(key)
                start,end=parse_uci_date_range(item.get("dates"))
                if not start or not end or end<TODAY or start>END:
                    continue
                found.append({**item,"_start":start,"_end":end,"_details_url":link})
    return found

def uci_details_class(details_url):
    if not details_url:
        return {"competition_class":"","categories":[]}
    last_error=None
    for attempt in range(3):
        try:
            r=requests.get(f'https://www.uci.org{details_url}',headers=HEADERS,timeout=25)
            r.raise_for_status()
            match=re.search(r'<div[^>]*data-component="CompetitionDetailsModule"[^>]*data-props="([^"]*)"',r.text)
            if not match:
                return {"competition_class":"","categories":[]}
            props=json.loads(html.unescape(match.group(1)))
            categories=[]
            for day in (props.get("schedule") or {}).get("items") or []:
                for race in day.get("races") or []:
                    if race.get("category"):
                        categories.append(str(race["category"]))
            return {
                "competition_class":str((props.get("competitionDetails") or {}).get("competitionClass") or ""),
                "categories":sorted(set(categories)),
            }
        except Exception as exc:
            last_error=exc
            if attempt<2:
                time.sleep(1.5*(attempt+1))
    raise last_error or RuntimeError("UCI competition details request failed")

def classify_uci_event(item,discipline,details=None):
    details=details or {}
    competition_class=str(details.get("competition_class") or "")
    categories=[str(x).lower() for x in details.get("categories") or []]
    name=str(item.get("name") or "").strip()
    low=name.casefold()
    upper=name.upper()
    if discipline=="ROA":
        if "UCI ROAD WORLD CHAMPIONSHIPS" in upper and "MASTERS" not in upper and "JUNIOR" not in upper:
            return "cycling-road-worlds","UCI Road World Championships"
        named=UCI_NAMED_ROAD.get(low)
        if named and "UCI WORLDTOUR" in competition_class.upper():
            return named
        eligible_age=not categories or any("elite" in x or "under 23" in x for x in categories)
        if eligible_age and re.match(r"^[12]\.[12](?:\b|U)",competition_class.upper()):
            return UCI_CONTINENT_SOURCES.get(str(item.get("continentCode") or "").upper())
        return None
    if discipline=="PIS" and "UCI TRACK WORLD CHAMPIONSHIPS" in upper and not any(x in upper for x in ("MASTERS","JUNIOR")):
        return "cycling-track-worlds","UCI Track Cycling World Championships"
    if discipline=="MTB":
        if "UCI MTB MARATHON WORLD CHAMPIONSHIPS" in upper and "MASTERS" not in upper:
            return "cycling-mtb-marathon-worlds","UCI Mountain Bike Marathon World Championships"
        if "UCI MTB WORLD CHAMPIONSHIPS" in upper and "MASTERS" not in upper:
            return "cycling-mtb-worlds","UCI Mountain Bike World Championships"
        if "UCI SNOW BIKE WORLD CHAMPIONSHIPS" in upper:
            return "cycling-snow-bike-worlds","UCI Snow Bike World Championships"
    if discipline in ("TRI","BFR") and "UCI URBAN CYCLING WORLD CHAMPIONSHIPS" in upper:
        return "cycling-urban-worlds","UCI Urban Cycling World Championships"
    if discipline=="CRO" and "UCI CYCLO-CROSS WORLD CHAMPIONSHIPS" in upper and "MASTERS" not in upper:
        return "cycling-cyclocross-worlds","UCI Cyclo-Cross World Championships"
    if discipline=="GRA" and "UCI GRAVEL WORLD CHAMPIONSHIPS" in upper:
        return "cycling-gravel-worlds","UCI Gravel World Championships"
    if discipline=="BMX" and "UCI BMX RACING WORLD CHAMPIONSHIPS" in upper and not any(x in upper for x in ("CHALLENGE","MASTERS")):
        return "cycling-bmx-worlds","UCI BMX Racing World Championships"
    if discipline=="IND" and "UCI INDOOR CYCLING WORLD CHAMPIONSHIPS" in upper:
        return "cycling-indoor-worlds","UCI Indoor Cycling World Championships"
    return None

def parse_uci_event(source,item,discipline,mapping,countries):
    source_id,league=mapping
    start,end=item["_start"],item["_end"]
    active=start<=TODAY<=end
    display_date=TODAY if active else start
    local=datetime.datetime.combine(display_date,datetime.time(0,1) if active else datetime.time(12,0),tzinfo=TZ)
    start_time=local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
    code=str(item.get("country") or "").upper()
    region=countries.get(code) or code or "International"
    venue=str(item.get("venue") or "").strip()
    location=" · ".join(x for x in (venue,region) if x) or None
    details_url=item.get("_details_url") or ""
    parsed={
        "id":f'{source_id}-{details_url.rsplit("/",1)[-1] or start.isoformat()}',
        "source_id":source_id,
        "sport":"Cycling",
        "league":league,
        "region":region,
        "name":item.get("name") or league,
        "start_time":start_time,
        "status":"LIVE" if active else "UPCOMING",
        "status_detail":f'{item.get("dates") or "Scheduled"} · official UCI calendar',
        "season_stage":None,
        "location":location,
        "source_endpoint":f'https://www.uci.org{details_url}' if details_url else source["endpoint"]
    }
    if active and start<TODAY:
        original=datetime.datetime.combine(start,datetime.time(12,0),tzinfo=TZ)
        parsed["original_start_time"]=original.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
    return parsed

def fetch_uci_calendar(source):
    payloads={}
    candidates=[]
    countries={}
    # The public calendar page carries the complete UCI country-code labels;
    # discipline-filtered API responses may omit that filter metadata.
    countries.update(uci_country_labels(source))
    for discipline in UCI_DISCIPLINES:
        last_error=None
        for attempt in range(3):
            try:
                r=requests.get(source["endpoint"],params={"discipline":discipline,"year":str(TODAY.year)},headers=HEADERS,timeout=40)
                r.raise_for_status()
                payload=r.json()
                payloads[discipline]=payload
                countries.update(uci_country_map(payload))
                candidates.extend((discipline,item) for item in uci_calendar_items(payload))
                break
            except Exception as exc:
                last_error=exc
                if attempt<2:
                    time.sleep(1.5*(attempt+1))
        else:
            raise last_error or RuntimeError(f"UCI {discipline} calendar request failed")

    road=[item for discipline,item in candidates if discipline=="ROA"]
    details={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(uci_details_class,item.get("_details_url")):item for item in road}
        for future in as_completed(futures):
            item=futures[future]
            details[item.get("_details_url")]=future.result()

    parsed=[]
    seen=set()
    for discipline,item in candidates:
        mapping=classify_uci_event(item,discipline,details.get(item.get("_details_url"),{}))
        if not mapping:
            continue
        event=parse_uci_event(source,item,discipline,mapping,countries)
        key=(event["source_id"],event["id"])
        if key in seen:
            continue
        seen.add(key)
        parsed.append(event)
    return parsed

DARTS_CITY_COUNTRIES={
    "aberdeen":"Scotland","antwerp":"Belgium","belfast":"Northern Ireland",
    "berlin":"Germany","birmingham":"England","brighton":"England",
    "cardiff":"Wales","den bosch":"Netherlands","dublin":"Ireland",
    "glasgow":"Scotland","hildesheim":"Germany","leeds":"England",
    "leicester":"England","liverpool":"England","london":"England",
    "manchester":"England","milton keynes":"England","newcastle":"England",
    "rotterdam":"Netherlands","sheffield":"England","wigan":"England"
}

def darts_country(city,venue=""):
    low=f"{city or ''} {venue or ''}".lower()
    for needle,country in DARTS_CITY_COUNTRIES.items():
        if needle in low:
            return country
    return "International"

def classify_pdc_tournament(item):
    attrs=item.get("attributes") or {}
    type_id=str(attrs.get("tournamentTypeID") or "")
    name=str(attrs.get("name") or "")
    if type_id in ("29","30"):
        return "darts-pdc-players-championship","PDC Players Championship"
    if type_id=="1" and "world championship" in name.lower() and "qualifier" not in name.lower():
        return "darts-pdc-world-championship","PDC World Championship"
    if type_id in ("3","54"):
        return "darts-pdc-premier-league","Premier League Darts"
    return None

def fetch_pdc_calendar(source):
    parsed=[]
    seen=set()
    years={TODAY.year}
    if TODAY.month==1:
        years.add(TODAY.year-1)
    for season_year in sorted(years):
        r=requests.get(
            source["endpoint"],
            params={"page.size":"500","filter":f"seasonID:eq:{season_year}"},
            headers=HEADERS,
            timeout=40
        )
        r.raise_for_status()
        for item in r.json().get("data") or []:
            mapping=classify_pdc_tournament(item)
            if not mapping:
                continue
            attrs=item.get("attributes") or {}
            try:
                start=datetime.date.fromisoformat(str(attrs.get("startDate") or ""))
                end=datetime.date.fromisoformat(str(attrs.get("endDate") or attrs.get("startDate") or ""))
            except ValueError:
                continue
            if end<TODAY or start>END:
                continue
            source_id,league=mapping
            event_id=f'{source_id}-{item.get("id") or start.isoformat()}'
            if event_id in seen:
                continue
            seen.add(event_id)
            active=start<=TODAY<=end
            display_date=TODAY if active else start
            local=datetime.datetime.combine(display_date,datetime.time(0,1) if active else datetime.time(12,0),tzinfo=TZ)
            city=str(attrs.get("city") or "").strip()
            venue=str(attrs.get("venue") or "").strip()
            region=darts_country(city,venue)
            location=" · ".join(x for x in (venue,city,region) if x)
            event={
                "id":event_id,
                "source_id":source_id,
                "sport":"Darts",
                "league":league,
                "region":region,
                "name":attrs.get("name") or league,
                "start_time":local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
                "status":"LIVE" if active else "UPCOMING",
                "status_detail":f'{start.isoformat()}{f" through {end.isoformat()}" if end!=start else ""} · official PDC calendar',
                "season_stage":None,
                "location":location or None,
                "source_endpoint":source.get("official_schedule_url") or source["endpoint"]
            }
            if active and start<TODAY:
                original=datetime.datetime.combine(start,datetime.time(12,0),tzinfo=TZ)
                event["original_start_time"]=original.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
            parsed.append(event)
    return parsed

def cdc_event_dates(page_text):
    text=plain_html(page_text)
    month=r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    match=re.search(rf"\b({month})\s+(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+(20\d{{2}})\b",text,re.I)
    if match:
        start=datetime.datetime.strptime(f"{match.group(1)[:3]} {match.group(2)} {match.group(4)}","%b %d %Y").date()
        end=datetime.datetime.strptime(f"{match.group(1)[:3]} {match.group(3)} {match.group(4)}","%b %d %Y").date()
        return start,end
    match=re.search(rf"\b({month})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b",text,re.I)
    if match:
        day=datetime.datetime.strptime(f"{match.group(1)[:3]} {match.group(2)} {match.group(3)}","%b %d %Y").date()
        return day,day
    return None,None

def cdc_region(text,title):
    low=f"{text} {title}".lower()
    if any(x in low for x in ("canada","newfoundland",", nl",", on",", ab",", bc")):
        return "Canada"
    if any(x in low for x in ("united states",", ny",", pa",", il",", in",", az",", nv")):
        return "United States"
    return "United States / Canada"

def fetch_cdc_calendar(source):
    main=requests.get(source["endpoint"],headers=HEADERS,timeout=35)
    main.raise_for_status()
    links=set(re.findall(r'href=["\'](https://champdarts\.com/events/[^"\'#?]+)',main.text,re.I))
    if source.get("cross_border_url"):
        links.add(source["cross_border_url"])
    parsed=[]
    for url in sorted(links):
        if any(x in url.lower() for x in ("q-school","junior-tour","jr-tour","evolution-tour","evo-tour")):
            continue
        r=requests.get(url,headers=HEADERS,timeout=30)
        r.raise_for_status()
        title_match=re.search(r'<h1[^>]*>(.*?)</h1>',r.text,re.I|re.S)
        title=plain_html(title_match.group(1)) if title_match else ""
        body=plain_html(r.text)
        low=f"{title} {body}".lower()
        if any(x in low for x in ("q-school","junior tour","jr. tour","evolution tour","evo tour")):
            continue
        is_cross="cross border darts challenge" in title.lower()
        if not is_cross and "category main tour" not in low:
            continue
        start,end=cdc_event_dates(r.text)
        if not start or not end or end<TODAY or start>END:
            continue
        source_id="darts-cdc-cross-border" if is_cross else "darts-cdc-main-tour"
        league="Cross Border Darts Challenge" if is_cross else "Main Tour Events"
        active=start<=TODAY<=end
        display_date=TODAY if active else start
        local=datetime.datetime.combine(display_date,datetime.time(0,1) if active else datetime.time(12,0),tzinfo=TZ)
        region=cdc_region(body,title)
        parsed.append({
            "id":f'{source_id}-{re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-") or start.isoformat()}',
            "source_id":source_id,
            "sport":"Darts",
            "league":league,
            "region":region,
            "name":title or league,
            "start_time":local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
            "status":"LIVE" if active else "UPCOMING",
            "status_detail":f'{start.isoformat()}{f" through {end.isoformat()}" if end!=start else ""} · official CDC calendar',
            "season_stage":None,
            "location":None,
            "source_endpoint":url
        })
    return parsed

def embedded_json_objects(text, typename):
    """Extract complete JSON objects embedded in server-rendered page data."""
    decoder=json.JSONDecoder()
    needle=f'{{"__typename":"{typename}"'
    cursor=0
    found=[]
    while True:
        cursor=text.find(needle,cursor)
        if cursor<0:
            break
        try:
            obj,_=decoder.raw_decode(text,cursor)
            found.append(obj)
        except (json.JSONDecodeError,ValueError):
            pass
        cursor+=len(needle)
    return found

LOL_LEAGUES={
    "lec":("esports-lol-lec","League of Legends Europe, Middle East, and Africa Championship (LEC)","Europe / Middle East / Africa"),
    "lck":("esports-lol-lck","League of Legends Champions Korea (LCK)","South Korea"),
    "lpl":("esports-lol-lpl","League of Legends Pro League (LPL)","China"),
    "lcp":("esports-lol-lcp","League of Legends Championship Pacific (LCP)","Asia-Pacific"),
    "cblol-brazil":("esports-lol-cblol","Campeonato Brasileiro de League of Legends (CBLOL)","Brazil"),
    "lcs":("esports-lol-lcs","League of Legends Championship Series (LCS)","United States / Canada"),
    "first_stand":("esports-lol-first-stand","First Stand Tournament","International"),
    "msi":("esports-lol-msi","Mid-Season Invitational","International"),
    "worlds":("esports-lol-worlds","League of Legends World Championship","International")
}

VALORANT_REGIONS={
    "vct_americas":"Americas",
    "vct_emea":"Europe / Middle East / Africa",
    "vct_pacific":"Asia-Pacific",
    "vct_cn":"China"
}

def classify_riot_event(source,item):
    league=item.get("league") or {}
    slug=str(league.get("slug") or "").lower()
    league_name=str(league.get("name") or "")
    tournament=str((item.get("tournament") or {}).get("name") or "")
    low=f"{slug} {league_name} {tournament}".lower()
    if source.get("game")=="lol":
        mapping=LOL_LEAGUES.get(slug)
        if not mapping:
            return None
        source_id,label,region=mapping
        if slug=="lec" and "versus" in low:
            return "esports-lol-lec-versus","The LEC Versus",region
        if slug=="lck" and "cup" in low:
            return "esports-lol-lck-cup","LCK Cup",region
        if slug=="cblol-brazil" and "cup" in low:
            return "esports-lol-cblol-cup","CBLOL Cup",region
        if slug=="lcs" and "lock" in low:
            return "esports-lol-lcs-lock-in","LCS Lock-In",region
        return source_id,label,region
    if slug in VALORANT_REGIONS:
        return "esports-valorant-regional","Regional Leagues and Stages",VALORANT_REGIONS[slug]
    if "masters" in low:
        return "esports-valorant-masters","Valorant Masters","International"
    if slug=="champions" or ("champions" in low and "game changers" not in low):
        return "esports-valorant-champions","Valorant Champions","International"
    return None

def fetch_riot_calendar(source):
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=60)
    r.raise_for_status()
    parsed=[]
    seen=set()
    for item in embedded_json_objects(r.text,"EventMatch"):
        mapping=classify_riot_event(source,item)
        if not mapping:
            continue
        try:
            start=datetime.datetime.fromisoformat(str(item.get("startTime") or "").replace("Z","+00:00"))
        except ValueError:
            continue
        local_date=start.astimezone(TZ).date()
        if local_date<TODAY or local_date>END:
            continue
        event_id=str(item.get("id") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        source_id,label,region=mapping
        teams=[str(x.get("name") or "").strip() for x in (item.get("matchTeams") or [])]
        teams=[x for x in teams if x]
        state=str(item.get("state") or "").lower()
        if state in ("inprogress","in_progress","live"):
            status="LIVE"
        elif state in ("completed","finished"):
            status="COMPLETED"
        else:
            status="UPCOMING"
        stage=" · ".join(x for x in (str((item.get("tournament") or {}).get("name") or "").strip(),str(item.get("blockName") or "").strip()) if x)
        parsed.append({
            "id":f"{source_id}-{event_id}",
            "source_id":source_id,
            "sport":"Esports",
            "league":label,
            "region":region,
            "name":" vs. ".join(teams[:2]) if len(teams)>=2 else (teams[0] if teams else stage or label),
            "start_time":start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
            "status":status,
            "status_detail":f"{stage or label} · official Riot schedule",
            "season_stage":item.get("blockName"),
            "location":region,
            "source_endpoint":source.get("official_schedule_url") or source["endpoint"]
        })
    return parsed

def r6_region(competition):
    name=str(competition.get("name") or "").lower()
    sub=str(competition.get("subRegion") or "").upper()
    if "north america" in name: return "North America"
    if "south america" in name: return "South America"
    if "europe mena" in name: return "Europe / Middle East / Africa"
    if "cnl" in name or sub=="CN": return "China"
    if "asia pacific" in name or sub in ("OCE","ASIA","APAC N"): return "Asia-Pacific"
    return "International"

def classify_r6_competition(competition):
    name=str(competition.get("name") or "")
    low=name.lower()
    if "challenger" in low:
        return "esports-r6-challenger","Challenger Series"
    if "major" in low:
        return "esports-r6-majors","BLAST R6 Major Events"
    if "six invitational" in low or "global championship" in low:
        return "esports-r6-global","Global Championships"
    if "league" in low or re.match(r"^cnl\b",low):
        return "esports-r6-regional","Regional Closed Leagues"
    return None

def fetch_ubisoft_r6_calendar(source):
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=60)
    r.raise_for_status()
    match=re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',r.text,re.S)
    if not match:
        raise RuntimeError("Ubisoft R6 calendar data was not found")
    payload=json.loads(html.unescape(match.group(1)))
    matches=payload.get("props",{}).get("pageProps",{}).get("pageData",{}).get("matches",[])
    parsed=[]
    seen=set()
    for item in matches:
        competition=item.get("competition") or {}
        mapping=classify_r6_competition(competition)
        if not mapping:
            continue
        try:
            start=datetime.datetime.fromtimestamp(int(item.get("timestamp")),datetime.timezone.utc)
        except (TypeError,ValueError,OverflowError):
            continue
        local_date=start.astimezone(TZ).date()
        if local_date<TODAY or local_date>END:
            continue
        event_id=str(item.get("id") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        source_id,label=mapping
        team1=str((item.get("team1") or {}).get("name") or "TBD")
        team2=str((item.get("team2") or {}).get("name") or "TBD")
        region=r6_region(competition)
        raw_status=int(item.get("status") or 0)
        parsed.append({
            "id":f"{source_id}-{event_id}",
            "source_id":source_id,
            "sport":"Esports",
            "league":label,
            "region":region,
            "name":f"{team1} vs. {team2}",
            "start_time":start.isoformat().replace("+00:00","Z"),
            "status":"LIVE" if raw_status==2 else ("COMPLETED" if raw_status==3 else "UPCOMING"),
            "status_detail":f'{competition.get("name") or label} · official Ubisoft schedule',
            "season_stage":competition.get("name"),
            "location":region,
            "source_endpoint":source.get("official_schedule_url") or source["endpoint"]
        })
    return parsed

MONTH_NUM={name.lower():number for number,name in enumerate((
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
),1)}
MONTH_NUM.update({name[:3].lower():number for name,number in list(MONTH_NUM.items())})

def parse_english_event_range(value,year):
    """Parse official calendar ranges such as 'October 22-October 31'."""
    text=str(value or "").strip().replace("–","-").replace("—","-")
    text=re.sub(r",?\s*(20\d{2})\s*$","",text).strip()
    match=re.fullmatch(
        r"([A-Za-z]+)\s+(\d{1,2})\s*-\s*(?:([A-Za-z]+)\s+)?(\d{1,2})",
        text
    )
    if not match:
        single=re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2})",text)
        if not single:
            return None,None
        month=MONTH_NUM.get(single.group(1).lower())
        if not month:
            return None,None
        day=datetime.date(int(year),month,int(single.group(2)))
        return day,day
    start_month=MONTH_NUM.get(match.group(1).lower())
    end_month=MONTH_NUM.get((match.group(3) or match.group(1)).lower())
    if not start_month or not end_month:
        return None,None
    start=datetime.date(int(year),start_month,int(match.group(2)))
    end_year=int(year)+(1 if end_month<start_month else 0)
    end=datetime.date(end_year,end_month,int(match.group(4)))
    return start,end

def tournament_window_event(source,source_id,league,name,start,end,location=None,endpoint=None):
    if not start or not end or end<TODAY or start>END:
        return None
    active=start<=TODAY<=end
    review_date=TODAY if active else start
    local=datetime.datetime.combine(review_date,datetime.time(12,0),tzinfo=TZ)
    slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
    return {
        "id":f"{source_id}-{start.isoformat()}-{slug}",
        "source_id":source_id,
        "sport":"Esports",
        "league":league,
        "region":source.get("region") or "International",
        "name":name,
        "start_time":local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
        "status":"LIVE" if active else "UPCOMING",
        "status_detail":f"{start.isoformat()} through {end.isoformat()} · official tournament calendar",
        "season_stage":None,
        "location":location,
        "source_endpoint":endpoint or source.get("official_schedule_url") or source["endpoint"]
    }

def fetch_official_event_window(source):
    """Use a publisher-owned page plus its published event window.

    This is intentionally tournament-level coverage. It does not invent matchups
    when the organizer publishes dates but no stable unattended match feed.
    """
    items=source.get("official_events") or []
    dated=[]
    for item in items:
        try:
            start=datetime.date.fromisoformat(item["start_date"])
            end=datetime.date.fromisoformat(item.get("end_date") or item["start_date"])
        except (KeyError,TypeError,ValueError):
            continue
        dated.append((item,start,end))
    # A completed, already-verified official tournament window cannot add an
    # event to today's queue. Avoid turning an organizer's anti-bot response
    # into a false current feed failure after the competition has ended.
    if dated and all(end<TODAY for _,_,end in dated):
        return []
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=45)
    r.raise_for_status()
    parsed=[]
    for item,start,end in dated:
        event=tournament_window_event(
            source,item["source_id"],item["league"],item["name"],start,end,
            item.get("location"),item.get("official_schedule_url")
        )
        if event:
            parsed.append(event)
    return parsed

def fetch_pgl_cs2_calendar(source):
    """Read PGL's own events API and retain only its CS2 event family."""
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=45)
    r.raise_for_status()
    payload=r.json()
    parsed=[]
    for year,items in payload.items():
        if not str(year).isdigit():
            continue
        for item in items or []:
            names=[str(x or "").strip() for x in (item.get("eventName") or [])]
            name=" ".join(x for x in names if x).strip()
            event_page=str(item.get("eventPage") or "")
            low=f"{name} {event_page}".lower()
            # PGL also publishes Dota events in this feed. Organizer identity
            # alone never broadens the catalog's PGL CS2 approval.
            if not ("/cs2/" in low or low.startswith("pgl cs2") or low.startswith("pgl masters")):
                continue
            start,end=parse_english_event_range(item.get("date"),int(year))
            event=tournament_window_event(
                source,"esports-cs2-pgl","Professional Gamers League (PGL) CS2",
                name or "PGL CS2",start,end,item.get("location") or None,
                event_page or source.get("official_schedule_url")
            )
            if event:
                parsed.append(event)
    return parsed

def fetch_esl_calendar(source):
    """Read the official ESL Pro Tour pages at tournament level."""
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=60)
    r.raise_for_status()
    page=r.text
    if source.get("game")=="dota2":
        # ESL explicitly renders this sentence when no Dota 2 EPT tournament
        # has been announced. Do not fill the gap with third-party schedules.
        if "No events are available" in plain_html(page):
            return []
        # Future cards can be classified without widening the approval:
        # DreamLeague gets its own catalog leaf; other top-level EPT events use
        # the separately approved ESL Pro Tour - Dota 2 leaf. Qualifier and
        # Division 2 cards are deliberately excluded.
        blocks=re.findall(r'<div[^>]+class="[^"]*jet-listing-grid__item[^"]*"[^>]*>(.*?)</div>\s*</div>',page,re.I|re.S)
        parsed=[]
        for block in blocks:
            text=plain_html(block)
            low=text.lower()
            if not text or "division 2" in low or "qualifier" in low:
                continue
            if "dreamleague" in low:
                source_id="esports-dota-dreamleague"; league="DreamLeague"
            elif "esl one" in low:
                source_id="esports-dota-esl-pro-tour"; league="Electronic Sports League (ESL) Pro Tour - Dota 2"
            else:
                continue
            date_match=re.search(r'([A-Z][a-z]+\s+\d{1,2}\s*-\s*(?:[A-Z][a-z]+\s+)?\d{1,2},\s*20\d{2})',text)
            if not date_match:
                continue
            year=int(re.search(r'(20\d{2})',date_match.group(1)).group(1))
            start,end=parse_english_event_range(date_match.group(1),year)
            title_match=re.search(r'(DreamLeague(?:\s+Season)?\s*\d*|ESL One\s+[^|]+)',text,re.I)
            name=title_match.group(1).strip() if title_match else league
            event=tournament_window_event(source,source_id,league,name,start,end,endpoint=source.get("official_schedule_url"))
            if event:
                parsed.append(event)
        return parsed

    parsed=[]
    # ESL Pro League event cards link to /proleague/. Their card includes the
    # public tournament start date, which precedes the arena dates.
    for match in re.finditer(r'href="([^"]*/proleague/[^"]*)"[^>]*>([^<]+)</a>',page,re.I):
        url=html.unescape(match.group(1))
        title=plain_html(match.group(2))
        context=plain_html(page[max(0,match.start()-2200):match.end()+2600])
        end_match=re.search(r'([A-Z][a-z]+\s+\d{1,2})\s*-\s*([A-Z][a-z]+\s+\d{1,2}),\s*(20\d{2})',context)
        if not end_match:
            continue
        year=int(end_match.group(3))
        card_start,card_end=parse_english_event_range(f"{end_match.group(1)}-{end_match.group(2)}",year)
        start_match=re.search(r'Tournament starts on\s+([A-Z][a-z]+\s+\d{1,2})',context,re.I)
        start=card_start
        if start_match:
            start,_=parse_english_event_range(start_match.group(1),year)
        event=tournament_window_event(
            source,"esports-cs2-esl-pro-league","Electronic Sports League (ESL) Pro League",
            f"ESL Pro League {title}".strip(),start,card_end,endpoint=url
        )
        if event and all(existing["id"]!=event["id"] for existing in parsed):
            parsed.append(event)
    return parsed

events=[]
source_status=[]
for source in CFG.get("sources",[]):
    ap=approved(source)
    if ap is False:
        source_status.append({**source,"approved_catalog":False,"ok":True,"events":0,"note":"Source adapter skipped because its match terms were not found in current catalog."})
        continue
    if ap is None:
        source_status.append({**source,"approved_catalog":None,"ok":False,"events":0,"note":"Current catalog data unavailable; approval match not evaluated."})
        continue

    count=0
    errors=[]
    seen=set()
    if source.get("source_type")=="coverage-gap":
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":True,
            "events":0,
            "note":source.get("source_note") or "Approved in-season league; no dependable complete public schedule adapter is currently available.",
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="boxing-rss":
        try:
            for parsed in parse_boxing_rss(source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="uci-calendar":
        try:
            for parsed in fetch_uci_calendar(source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type") in ("pdc-calendar","cdc-calendar"):
        try:
            adapter=fetch_pdc_calendar if source.get("source_type")=="pdc-calendar" else fetch_cdc_calendar
            for parsed in adapter(source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type") in ("riot-esports-calendar","ubisoft-r6-calendar"):
        try:
            adapter=fetch_riot_calendar if source.get("source_type")=="riot-esports-calendar" else fetch_ubisoft_r6_calendar
            for parsed in adapter(source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type") in ("official-event-window","pgl-cs2-calendar","esl-esports-calendar"):
        try:
            adapters={
                "official-event-window":fetch_official_event_window,
                "pgl-cs2-calendar":fetch_pgl_cs2_calendar,
                "esl-esports-calendar":fetch_esl_calendar
            }
            for parsed in adapters[source["source_type"]](source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="espn-daily":
        def fetch_espn_day(day):
            last_error=None
            for attempt in range(3):
                try:
                    r=requests.get(
                        source["endpoint"],
                        params={"dates":day.strftime("%Y%m%d"),"limit":"1000"},
                        headers=HEADERS,
                        timeout=25
                    )
                    r.raise_for_status()
                    return day,r.json()
                except Exception as exc:
                    last_error=exc
                    if attempt<2:
                        time.sleep(1.5*(attempt+1))
            raise last_error or RuntimeError("ESPN daily request failed")

        days=[TODAY+datetime.timedelta(days=offset) for offset in range((END-TODAY).days+1)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(fetch_espn_day,day):day for day in days}
            for future in as_completed(futures):
                day=futures[future]
                try:
                    _,data=future.result()
                    for ev in data.get("events",[]):
                        parsed=parse_event(source,ev)
                        key=(parsed["id"],parsed["start_time"])
                        if key in seen:
                            continue
                        seen.add(key)
                        events.append(parsed)
                        count+=1
                except Exception as e:
                    errors.append(f"{day.isoformat()}: {str(e)[:110]}")
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors or count>0,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="thesportsdb":
        try:
            data=thesportsdb_json(source["endpoint"],{"id":source["league_id"]})
            for ev in data.get("events") or []:
                parsed=parse_thesportsdb_event(source,ev)
                if not parsed.get("start_time"):
                    continue
                event_date=datetime.datetime.fromisoformat(parsed["start_time"].replace("Z","+00:00")).astimezone(TZ).date()
                if event_date<TODAY or event_date>END:
                    continue
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="thesportsdb-day":
        for offset in range((END-TODAY).days+1):
            day=TODAY+datetime.timedelta(days=offset)
            try:
                data=thesportsdb_json(source["endpoint"],{"d":day.isoformat(),"s":source.get("sport_query") or source["sport"]})
                for ev in data.get("events") or []:
                    if str(ev.get("idLeague") or "")!=str(source["league_id"]):
                        continue
                    parsed=parse_thesportsdb_event(source,ev)
                    key=(parsed["id"],parsed["start_time"])
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append(parsed)
                    count+=1
            except Exception as e:
                errors.append(f"{day.isoformat()}: {str(e)[:110]}")
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors or count>0,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="mlbstats":
        try:
            params={
                "sportId":source["sport_id"],
                "leagueId":source["league_id"],
                "startDate":TODAY.isoformat(),
                "endDate":END.isoformat(),
                "hydrate":"team,venue"
            }
            r=requests.get(source["endpoint"],params=params,headers=HEADERS,timeout=18)
            r.raise_for_status()
            data=r.json()
            for date_group in data.get("dates") or []:
                for game in date_group.get("games") or []:
                    parsed=parse_mlbstats_event(source,game)
                    key=(parsed["id"],parsed["start_time"])
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append(parsed)
                    count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    for offset in range((END-TODAY).days+1):
        day=TODAY+datetime.timedelta(days=offset)
        try:
            r=requests.get(source["endpoint"],params={"dates":day.strftime("%Y%m%d"),"limit":"1000"},headers=HEADERS,timeout=18)
            r.raise_for_status()
            data=r.json()
            for ev in data.get("events",[]):
                parsed=parse_event(source,ev)
                key=(parsed["id"],parsed["start_time"])
                if key in seen: continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(f"{day.isoformat()}: {str(e)[:110]}")
    source_status.append({
        **source,
        "approved_catalog":True,
        "ok": not errors or count>0,
        "events":count,
        "errors":errors[:3],
        "checked_at":NOW_UTC.isoformat()
    })

# U18 cross-reference from review data + static known registry isn't machine-readable,
# so current automatic matching uses review-data verified U18 names.
u18_names=[]
review_path=DATA/"review-data.json"
if review_path.exists():
    try:
        review=json.loads(review_path.read_text(encoding="utf-8"))
        for x in review.get("u18_matches",[]):
            n=x.get("athlete") or x.get("name")
            if n: u18_names.append(n)
    except Exception:
        pass

for ev in events:
    low=(ev.get("name") or "").lower()
    ev["u18_matches"]=[n for n in u18_names if n.lower() in low]
    ev["u18_risk"]=bool(ev["u18_matches"])

# Restriction cross-reference.
# Applicability must be event/league specific. A restriction somewhere under
# a sport must NOT automatically flag every scheduled event in that sport.
restrictions=[]
cat_path=DATA/"catalog-live.json"
if cat_path.exists():
    try:
        cat=json.loads(cat_path.read_text(encoding="utf-8"))
        restrictions=cat.get("restrictions",[])
    except Exception:
        pass

def restriction_applies(ev, x):
    text=str(x.get("text") or "").lower()
    esport=str(ev.get("sport") or "").lower()
    league=str(ev.get("league") or "").lower()
    name=str(ev.get("name") or "").lower()
    stage=str(ev.get("season_stage") or "").upper()
    scope_type=str(x.get("scope_type") or "")
    scope_sport=str(x.get("sport") or "").lower()
    hay=f"{league} {name}"

    # General professional/international U18 language is NOT a league-wide
    # schedule restriction. It requires an actual participant-age match.
    if scope_type=="GENERAL_U18_PRO":
        return False

    # NFL event-specific controls. "NFL Draft" must never attach to NFL games.
    if league=="nfl":
        if "draft" in text:
            return "draft" in name

        preseason_rule=("preseason" in text or "pre-season" in text)
        postseason_rule=("postseason" in text or "playoff" in text)
        regular_rule=("regular season" in text)

        if preseason_rule:
            return stage=="PRESEASON"
        if postseason_rule:
            return stage=="POSTSEASON"
        if regular_rule:
            return stage=="REGULAR SEASON"

    # MLB event-specific restrictions.
    if league=="mlb":
        if "draft" in text:
            return "draft" in name
        if "spring training" in text or "preseason" in text or "pre-season" in text:
            return stage=="PRESEASON" or any(k in name for k in ("spring training","preseason","pre-season"))

    # Explicit named special-event restrictions require the named event.
    special_terms=[
        "draft","all-star","home run derby","world baseball classic",
        "preseason","pre-season","spring training"
    ]
    for term in special_terms:
        if term in text:
            return term in hay

    # Restriction tied to an explicitly named league/event.
    if league and league in text:
        return True

    # Sport-level restriction can apply only when it is genuinely sport-wide.
    if scope_sport and scope_sport==esport:
        generic_event_words=["restriction","no proposition wagers","no player proposition wagers","no in-game wagers"]
        if any(g in text for g in generic_event_words) and not any(t in text for t in special_terms):
            # If the text contains a distinct league/event name not present in this
            # event, do not spread it across the entire sport.
            tokens=[t for t in re.findall(r"[a-z0-9]+",text) if len(t)>=5]
            ev_tokens=set(re.findall(r"[a-z0-9]+",hay))
            named=[t for t in tokens if t not in {"restriction","markets","wagers","player","proposition","event","games","close","prior","start","hours","hour"}]
            if named and not any(t in ev_tokens for t in named):
                return False

    return False

for ev in events:
    rel=[]
    for x in restrictions:
        if restriction_applies(ev, x):
            rel.append(x.get("text"))
    ev["restriction_signals"]=rel[:5]
    ev["restriction_risk"]=bool(rel)

events.sort(key=lambda x:(x.get("start_time") or "9999",x["sport"],x["league"],x["name"]))

# Approved catalog areas not represented by an active schedule adapter.
mapped_terms=set()
for s in CFG.get("sources",[]):
    if approved(s):
        mapped_terms.update(x.lower() for x in s.get("catalog_terms",[]))

coverage_gaps=[]
if CATALOG:
    # Broad catalog sports where a generic adapter has not yet been built.
    candidate_areas=[
        "Aussie Rules","Bowling","Boxing","Combat Sports","Cricket","Cycling","Darts",
        "Esports","Golf","Lacrosse","Motorsports","Olympics","Rodeo","Rugby",
        "Surfing","Table Tennis"
    ]
    for area in candidate_areas:
        if area.lower() in CATALOG and not any(area.lower() in x for x in mapped_terms):
            coverage_gaps.append({
                "area":area,
                "state":"SCHEDULE ADAPTER PENDING",
                "note":"Approved catalog area is recognized but not yet included in the automated global schedule feed."
            })

out={
    "schema_version":1,
    "generated_at":NOW_UTC.isoformat(),
    "timezone":"America/Chicago",
    "window_start":TODAY.isoformat(),
    "window_end":END.isoformat(),
    "event_count":len(events),
    "events":events,
    "sources":source_status,
    "coverage_gaps":coverage_gaps
}
(DATA/"global-schedule.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({
    "window":f"{TODAY} through {END}",
    "events":len(events),
    "sources_ok":sum(1 for x in source_status if x.get("ok")),
    "sources_total":len(source_status),
    "coverage_gaps":len(coverage_gaps)
}))
