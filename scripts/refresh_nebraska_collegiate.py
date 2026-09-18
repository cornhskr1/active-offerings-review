#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json, re, datetime, requests, time
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
DATA.mkdir(exist_ok=True)
NOW=datetime.datetime.now(datetime.timezone.utc)
TZ=ZoneInfo("America/Chicago")
TODAY=datetime.datetime.now(TZ).date()
END=TODAY+datetime.timedelta(days=7)
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

SOURCES=[
    {"school":"Nebraska","sport":"Baseball","url":"https://huskers.com/sports/baseball/schedule","parser":"nebraska","allow_unpublished":True},
    {"school":"Nebraska","sport":"Beach Volleyball","url":"https://huskers.com/sports/beach-volleyball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Football","url":"https://huskers.com/sports/football/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Men's Basketball","url":"https://huskers.com/sports/mens-basketball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Basketball","url":"https://huskers.com/sports/womens-basketball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Men's Golf","url":"https://huskers.com/sports/mens-golf/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Golf","url":"https://huskers.com/sports/womens-golf/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Men's Tennis","url":"https://huskers.com/sports/mens-tennis/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Tennis","url":"https://huskers.com/sports/womens-tennis/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Soccer","url":"https://huskers.com/sports/soccer/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Softball","url":"https://huskers.com/sports/softball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Swimming & Diving","url":"https://huskers.com/sports/swimming-and-diving/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Track & Field","url":"https://huskers.com/sports/track-and-field/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Volleyball","url":"https://huskers.com/sports/volleyball/schedule?view=list","parser":"nebraska"},
    {"school":"Nebraska","sport":"Wrestling","url":"https://huskers.com/sports/wrestling/schedule","parser":"nebraska"},

    {"school":"Creighton","sport":"Baseball","url":"https://gocreighton.com/sports/baseball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Men's Basketball","url":"https://gocreighton.com/sports/mens-basketball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Basketball","url":"https://gocreighton.com/sports/womens-basketball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Men's Golf","url":"https://gocreighton.com/sports/mens-golf/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Golf","url":"https://gocreighton.com/sports/womens-golf/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Men's Soccer","url":"https://gocreighton.com/sports/mens-soccer/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Soccer","url":"https://gocreighton.com/sports/womens-soccer/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Softball","url":"https://gocreighton.com/sports/softball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Men's Tennis","url":"https://gocreighton.com/sports/mens-tennis/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Tennis","url":"https://gocreighton.com/sports/womens-tennis/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Volleyball","url":"https://gocreighton.com/sports/womens-volleyball/schedule/text","parser":"creighton"},

    {"school":"Omaha","sport":"Baseball","url":"https://omahamavs.com/sports/baseball/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Men's Basketball","url":"https://omahamavs.com/sports/mens-basketball/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Women's Basketball","url":"https://omahamavs.com/sports/womens-basketball/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Men's Golf","url":"https://omahamavs.com/sports/mens-golf/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Women's Golf","url":"https://omahamavs.com/sports/womens-golf/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Hockey","url":"https://omahamavs.com/sports/mens-ice-hockey/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Men's Soccer","url":"https://omahamavs.com/sports/mens-soccer/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Women's Soccer","url":"https://omahamavs.com/sports/womens-soccer/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Softball","url":"https://omahamavs.com/sports/softball/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Men's Tennis","url":"https://omahamavs.com/sports/mens-tennis/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Women's Tennis","url":"https://omahamavs.com/sports/womens-tennis/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Track & Field","url":"https://omahamavs.com/sports/womens-track-and-field/schedule","parser":"omaha"},
    {"school":"Omaha","sport":"Volleyball","url":"https://omahamavs.com/sports/womens-volleyball/schedule","parser":"omaha"}
]

MONTHS={m:i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}

def clean(s): return re.sub(r"\s+"," ",s or "").strip()

def parse_date_text(s):
    m=re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s*(\d{1,2})\b",s,re.I)
    if not m: return None
    mon=m.group(1).title()
    day=int(m.group(2))
    # College seasons around new year: infer year around TODAY.
    year=TODAY.year
    candidate=datetime.date(year,MONTHS[mon],day)
    if candidate < TODAY-datetime.timedelta(days=180):
        candidate=datetime.date(year+1,MONTHS[mon],day)
    elif candidate > TODAY+datetime.timedelta(days=250):
        candidate=datetime.date(year-1,MONTHS[mon],day)
    return candidate

def result_like(s):
    return bool(re.match(r"^(W|L|T|N)\b",clean(s),re.I))

def parse_creighton(src, source):
    soup=BeautifulSoup(src,"html.parser")
    events=[]
    table=soup.find("table")
    if not table:
        raise ValueError("Creighton schedule table was not found; source markup may have changed")
    headers=[clean(x.get_text(" ",strip=True)).lower() for x in table.find_all("th")]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if len(tds)<5: continue
        vals=[clean(td.get_text(" ",strip=True)) for td in tds]
        # Expected Date Time At Opponent Location Tournament Result
        date=parse_date_text(vals[0])
        if not date or not (TODAY <= date <= END): continue
        time=vals[1] if len(vals)>1 else "TBA"
        site=(vals[2] if len(vals)>2 else "").upper()
        if site not in ("HOME","AWAY","NEUTRAL"):
            site="UNKNOWN"
        opp=vals[3] if len(vals)>3 else ""
        loc=vals[4] if len(vals)>4 else ""
        tournament=vals[5] if len(vals)>5 else ""
        result=vals[6] if len(vals)>6 else ""
        if result and result != "-" and result_like(result):
            # Completed events may still be returned; current-date completed handling can use result.
            status="FINAL"
        else:
            status="SCHEDULED"
        events.append({
            "school":source["school"],"sport":source["sport"],"date":date.isoformat(),
            "time":time,"site":site,"opponent":opp,"location":loc,
            "phase":"FALL EXHIBITION" if source["sport"]=="Softball" and date.month in (9,10,11) else "EXHIBITION" if "exhibition" in tournament.lower() else "REGULAR SEASON",
            "status":status,"result":result,"source_url":source["url"]
        })
    return events

def parse_nebraska(src, source):
    soup=BeautifulSoup(src,"html.parser")
    events=[]
    site_tokens={"home":"HOME","away":"AWAY","neutral":"NEUTRAL"}

    # Nebraska's WMT pages expose stable, field-specific schedule markup. Parse
    # those fields directly so promotional labels (for example "Ag Day" or
    # "RESCHEDULED FROM 9/6") cannot shift into opponent and location values.
    schedule_items=soup.select(".schedule-event-item")
    if not schedule_items:
        raise ValueError("Nebraska schedule event markup was not found; source markup may have changed")
    for item in schedule_items:
        site_node=item.select_one(".schedule-event-venue__type-label")
        date_node=item.select_one(".schedule-event-date__label")
        opponent_node=item.select_one(".schedule-event-item-default__opponent-name")
        location_node=item.select_one(".schedule-event-item-default__location")
        result_node=item.select_one(".schedule-event-item-result__label")
        promo_node=item.select_one(".schedule-event-item-default__promo-title")

        site=site_tokens.get(clean(site_node.get_text(" ",strip=True)).lower() if site_node else "","UNKNOWN")
        date=parse_date_text(clean(date_node.get_text(" ",strip=True)) if date_node else "")
        if not date or not (TODAY <= date <= END):
            continue

        opp=clean(opponent_node.get_text(" ",strip=True)) if opponent_node else ""
        loc=clean(location_node.get_text(" ",strip=True)) if location_node else ""
        if not loc:
            neutral_location=item.select_one(".schedule-event-item-neutral__location .schedule-event-location")
            loc=clean(neutral_location.get_text(" ",strip=True)) if neutral_location else ""

        # Tournament host pages can include neutral matches between two other
        # schools. Do not treat those as Nebraska participation merely because
        # they appear on Nebraska's schedule page.
        if site=="NEUTRAL" and not opp:
            neutral_teams=[]
            for team in item.select(".schedule-event-item-neutral__neutral-team"):
                label=clean(team.get_text(" ",strip=True))
                image=team.select_one("img[alt]")
                neutral_teams.append(label or clean(image.get("alt")) if image else label)
            nebraska_aliases=("nebraska","huskers","cornhuskers")
            participant_index=next((i for i,name in enumerate(neutral_teams) if any(alias in name.lower() for alias in nebraska_aliases)),None)
            if participant_index is None:
                continue
            opp=next((name for i,name in enumerate(neutral_teams) if i!=participant_index and name),"")
        result_or_time=clean(result_node.get_text(" ",strip=True)) if result_node else "TBA"
        promo=clean(promo_node.get_text(" ",strip=True)) if promo_node else ""
        status="FINAL" if result_like(result_or_time) else "SCHEDULED"
        result=result_or_time if status=="FINAL" else ""
        time="TBA" if status=="FINAL" else (result_or_time or "TBA")
        phase="FALL EXHIBITION" if source["sport"]=="Softball" and date.month in (9,10,11) else "EXHIBITION" if "exhibition" in item.get_text(" ",strip=True).lower() else "REGULAR SEASON"

        events.append({
            "school":source["school"],"sport":source["sport"],"date":date.isoformat(),
            "time":time,"site":site,"opponent":opp or "TBA","location":loc,
            "promotional_label":promo or None,
            "phase":phase,"status":status,"result":result,"source_url":source["url"]
        })
    # dedupe
    seen=set(); unique=[]
    for e in events:
        key=(e["school"],e["sport"],e["date"],e["time"],e["site"],e["opponent"])
        if key not in seen:
            seen.add(key); unique.append(e)
    return unique


def parse_omaha(src, source):
    """Parse Omaha's field-specific Sidearm schedule cards."""
    soup=BeautifulSoup(src,"html.parser")
    cards=soup.select(".s-game-card")
    if not cards:
        raise ValueError("Omaha schedule cards were not found; source markup may have changed")
    events=[]

    for card in cards:
        date_node=card.select_one('[data-test-id="s-game-card-standard__header-game-date-details"], [data-test-id="s-game-card-standard__header-game-date"]')
        date=parse_date_text(clean(date_node.get_text(" ",strip=True)) if date_node else "")
        if not date or not (TODAY <= date <= END):
            continue

        stamp=card.select_one(".s-stamp__text")
        token=clean(stamp.get_text(" ",strip=True)).lower() if stamp else ""
        site="AWAY" if token=="at" else "HOME" if token in ("vs","vs.") else "UNKNOWN"
        opp_node=card.select_one('[data-test-id="s-game-card-standard__header-team-opponent-link"]')
        if not opp_node:
            opp_node=card.select_one(".s-game-card__header__team-event-info .s-text-paragraph-bold")
        opp=clean(opp_node.get_text(" ",strip=True)) if opp_node else "TBA"

        facility_node=card.select_one('[data-test-id="s-game-card-facility-and-location__game-facility-title-link"]')
        location_node=card.select_one('[data-test-id="s-game-card-facility-and-location__standard-location-details"]')
        facility=clean(facility_node.get_text(" ",strip=True)) if facility_node else ""
        location=clean(location_node.get_text(" ",strip=True)) if location_node else ""
        loc=" / ".join(x for x in (location,facility) if x)
        time_node=card.select_one('[aria-label="Event Time"]')
        time_value=clean(time_node.get_text(" ",strip=True)) if time_node else "TBA"

        card_text=clean(card.get_text(" ",strip=True)).lower()
        if source["sport"]=="Softball" and date.month in (9,10,11):
            phase="FALL EXHIBITION"
        elif "exhibition" in card_text:
            phase="EXHIBITION"
        elif "championship" in card_text or "tournament" in card_text:
            phase="POSTSEASON"
        else:
            phase="REGULAR SEASON"

        events.append({
            "school":source["school"],"sport":source["sport"],"date":date.isoformat(),
            "time":time_value or "TBA","site":site,"opponent":opp,"location":loc,
            "phase":phase,"status":"SCHEDULED","result":"","source_url":source["url"]
        })

    seen=set(); unique=[]
    for e in events:
        key=(e["school"],e["sport"],e["date"],e["time"],e["site"],e["opponent"])
        if key not in seen:
            seen.add(key); unique.append(e)
    return unique

def fetch_source(source):
    last_error=None
    for attempt in range(3):
        try:
            r=requests.get(source["url"],headers=HEADERS,timeout=35)
            if r.status_code==404 and source.get("allow_unpublished"):
                return source,[],None,"schedule_not_published"
            r.raise_for_status()
            if source["parser"]=="creighton":
                parsed=parse_creighton(r.text,source)
            elif source["parser"]=="omaha":
                parsed=parse_omaha(r.text,source)
            else:
                parsed=parse_nebraska(r.text,source)
            return source,parsed,None,"published"
        except Exception as exc:
            last_error=exc
            if attempt<2:
                time.sleep(attempt+1)
    return source,[],last_error,"error"

events=[]
source_status=[]
with ThreadPoolExecutor(max_workers=8) as pool:
    futures=[pool.submit(fetch_source,source) for source in SOURCES]
    fetched=[future.result() for future in as_completed(futures)]

for source,parsed,error,availability in sorted(fetched,key=lambda row:(row[0]["school"],row[0]["sport"])):
    if error is None:
        events.extend(parsed)
        source_status.append({"school":source["school"],"sport":source["sport"],"url":source["url"],"ok":True,"schedule_available":availability=="published","availability":availability,"events_in_window":len(parsed)})
    else:
        source_status.append({"school":source["school"],"sport":source["sport"],"url":source["url"],"ok":False,"error":str(error)[:180],"events_in_window":0})

failed_sources=[x for x in source_status if not x["ok"]]
if failed_sources:
    details="; ".join(f'{x["school"]} {x["sport"]}: {x["error"]}' for x in failed_sources)
    raise RuntimeError("Official schedule coverage incomplete; keeping the previous feed. " + details)

coverage={}
for school in sorted({x["school"] for x in source_status}):
    school_sources=[x for x in source_status if x["school"]==school]
    coverage[school]={
        "configured":len(school_sources),
        "loaded":sum(x.get("schedule_available",False) for x in school_sources),
        "pending_publication":sum(x.get("availability")=="schedule_not_published" for x in school_sources),
        "events_in_window":sum(x["events_in_window"] for x in school_sources)
    }

# Sort by date/time with TBA last.
events.sort(key=lambda e:(e["date"], e["time"]=="TBA", e["time"], e["school"], e["sport"]))


NEBRASKA_VENUE_TERMS=[
    "lincoln, neb","lincoln, ne","lincoln, nebraska",
    "omaha, neb","omaha, ne","omaha, nebraska",
    "bob devaney","devaney sports center","memorial stadium",
    "pinnacle bank arena","hawks field","bowlin stadium",
    "barbara hibner","morrison stadium","dj sokol",
    "chi health center omaha","charles schwab field","baxter arena","wayne and eileen ryan","d.j. sokol","dj sokol",
    "haymarket park","seacrest field"
]

def played_in_nebraska(e):
    loc=re.sub(r"\s+"," ",str(e.get("location") or "")).lower()
    if any(term in loc for term in NEBRASKA_VENUE_TERMS):
        return True
    # State-name / abbreviation fallback when a venue string is more generic.
    return bool(re.search(r"\bnebraska\b|\bneb\.?(?:\s|$)",loc))

# Regulatory determination:
# a Nebraska collegiate participant + event physically played in Nebraska = RED.
# The source site's HOME/AWAY/NEUTRAL tag is informational only.
for e in events:
    e["played_in_nebraska"]=played_in_nebraska(e)
    e["matchup_label"]="AT" if e.get("site")=="AWAY" and not e["played_in_nebraska"] else "VS" if e.get("site") in ("HOME","NEUTRAL") or e["played_in_nebraska"] else "SITE TBD"
    if e["played_in_nebraska"]:
        e["site_test"]="NOT PERMISSIBLE"
        e["site_color"]="red"
        e["regulatory_site_label"]="PLAYED IN NEBRASKA"
    elif e.get("site")=="HOME":
        # A Nebraska school's HOME tag should never silently resolve green when
        # the parsed physical location does not identify Nebraska. Treat the
        # contradiction as a source-data failure requiring manual review.
        e["site_test"]="MANUAL LOCATION REVIEW"
        e["site_color"]="amber"
        e["regulatory_site_label"]="SOURCE LOCATION CONFLICT"
        e["location_conflict_reason"]="Official schedule marks the event HOME, but the parsed location does not identify Nebraska."
    elif e.get("location"):
        e["site_test"]="OK · OUTSIDE NEBRASKA"
        e["site_color"]="green"
        e["regulatory_site_label"]="OUTSIDE NEBRASKA"
    else:
        e["site_test"]="MANUAL LOCATION REVIEW"
        e["site_color"]="amber"
        e["regulatory_site_label"]="LOCATION UNRESOLVED"

def validate_events(rows):
    errors=[]
    seen=set()
    for e in rows:
        key=(e.get("school"),e.get("sport"),e.get("date"),e.get("time"),e.get("site"),e.get("opponent"))
        if key in seen:
            errors.append(f"duplicate event: {key}")
        seen.add(key)
        if e.get("played_in_nebraska") and e.get("site_color")!="red":
            errors.append(f"in-state event not red: {key}")
        if e.get("site")=="HOME" and not e.get("played_in_nebraska") and e.get("site_color")=="green":
            errors.append(f"HOME/location contradiction resolved green: {key}")
        expected="AT" if e.get("site")=="AWAY" and not e.get("played_in_nebraska") else "VS" if e.get("site") in ("HOME","NEUTRAL") or e.get("played_in_nebraska") else "SITE TBD"
        if e.get("matchup_label")!=expected:
            errors.append(f"matchup label mismatch: {key}")
    if errors:
        raise ValueError("Nebraska collegiate validation failed: " + "; ".join(errors))
    return {
        "events_checked":len(rows),
        "in_state_not_permissible":sum(e.get("site_color")=="red" for e in rows),
        "outside_nebraska":sum(e.get("site_color")=="green" for e in rows),
        "manual_location_review":sum(e.get("site_color")=="amber" for e in rows),
        "duplicate_events":0
    }

validation=validate_events(events)

out={
    "schema_version":1,
    "generated_at":NOW.isoformat(),
    "timezone":"America/Chicago",
    "window_start":TODAY.isoformat(),
    "window_end":END.isoformat(),
    "events":events,
    "sources":source_status,
    "coverage":coverage,
    "validation":validation
}
(DATA/"nebraska-collegiate-live.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({
    "window":f"{TODAY} through {END}",
    "events":len(events),
    "sources_ok":sum(1 for x in source_status if x["ok"]),
    "sources_total":len(source_status)
}))
