#!/usr/bin/env python3
from pathlib import Path
import datetime, json, re, requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
DATA.mkdir(exist_ok=True)

TZ=ZoneInfo("America/Chicago")
NOW_LOCAL=datetime.datetime.now(TZ)
TODAY=NOW_LOCAL.date()
NOW_UTC=datetime.datetime.now(datetime.timezone.utc)

SEASON_START=datetime.date(2026,8,1)
SEASON_END=datetime.date(2027,7,31)

PROMO_TERMS=(
    "opening night","presented by","fan fest","fanfest","season ticket",
    "media day","tip-off luncheon","tipoff luncheon","pep rally"
)

POSTSEASON_TERMS=(
    "big ten tournament","big east tournament","summit league tournament",
    "ncaa tournament","ncaa first round","ncaa second round","sweet 16",
    "elite eight","final four","national championship",
    "college basketball crown","cbi","college basketball invitational"
)

IN_SEASON_TERMS=(
    "classic","invitational","showcase","challenge","battle 4 atlantis",
    "maui invitational","players era","holiday hoopsgiving",
    "championship game only"
)

def in_season_window(date):
    return bool(date and SEASON_START <= date <= SEASON_END)

def looks_like_promo(text):
    t=clean(text).lower()
    return any(term in t for term in PROMO_TERMS)

def looks_like_real_opponent(name):
    n=clean(name)
    if not n or n.upper() in ("TBA","TBD"):
        return False
    if looks_like_promo(n):
        return False
    if any(term in n.lower() for term in ("opening night","presented by")):
        return False
    return True

HEADERS={"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

SOURCES=[
    {"school":"Nebraska","sport":"Men's Basketball","url":"https://huskers.com/sports/mens-basketball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Basketball","url":"https://huskers.com/sports/womens-basketball/schedule","parser":"nebraska"},

    {"school":"Creighton","sport":"Men's Basketball","url":"https://gocreighton.com/sports/mens-basketball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Basketball","url":"https://gocreighton.com/sports/womens-basketball/schedule/text","parser":"creighton"},

    {"school":"Omaha","sport":"Men's Basketball","url":"https://omahamavs.com/sports/mens-basketball/schedule/2026-27","parser":"omaha"},
    {"school":"Omaha","sport":"Women's Basketball","url":"https://omahamavs.com/sports/womens-basketball/schedule/2026-27","parser":"omaha"},
]

MONTHS={m:i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}

def clean(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()

def parse_date_text(s):
    # Month-name forms: Nov 3 / November 3
    m=re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\w*\.?\s*(\d{1,2})(?:,\s*(\d{4}))?\b",str(s),re.I)
    if not m:
        return None
    mon=m.group(1).title()
    if mon=="Sept": mon="Sep"
    day=int(m.group(2))
    if m.group(3):
        return datetime.date(int(m.group(3)),MONTHS[mon],day)

    # Basketball season spans calendar years. Infer from current season position.
    year=TODAY.year
    candidate=datetime.date(year,MONTHS[mon],day)

    # In Sep-Dec, Jan-Apr dates are normally next calendar year.
    if TODAY.month >= 8 and MONTHS[mon] <= 5:
        candidate=datetime.date(year+1,MONTHS[mon],day)
    # In Jan-May, Aug-Dec dates generally belong to prior calendar year.
    elif TODAY.month <= 5 and MONTHS[mon] >= 8:
        candidate=datetime.date(year-1,MONTHS[mon],day)
    return candidate

def phase_from_text(text):
    t=clean(text).lower()
    if any(k in t for k in ("exhibition","scrimmage")):
        return "EXHIBITION"

    # Only explicit conference/NCAA/postseason event names count as postseason.
    if any(k in t for k in POSTSEASON_TERMS):
        return "POSTSEASON"

    # In-season invitationals/classics/championship games remain regular season.
    if any(k in t for k in IN_SEASON_TERMS):
        return "REGULAR SEASON"

    return "REGULAR SEASON"

def parse_creighton(src, source):
    soup=BeautifulSoup(src,"html.parser")
    events=[]
    table=soup.find("table")
    if not table:
        return events
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if len(tds)<4:
            continue
        vals=[clean(td.get_text(" ",strip=True)) for td in tds]
        date=parse_date_text(vals[0])
        if not date or not in_season_window(date):
            continue
        time=vals[1] if len(vals)>1 and vals[1] else "TBA"
        site=(vals[2] if len(vals)>2 else "").upper()
        opponent=vals[3] if len(vals)>3 else "TBA"
        location=vals[4] if len(vals)>4 else ""
        tournament=vals[5] if len(vals)>5 else ""
        row_text=" | ".join(vals)
        if looks_like_promo(row_text) or not looks_like_real_opponent(opponent):
            continue
        events.append({
            "date":date.isoformat(),"time":time,"site":site or "UNKNOWN",
            "opponent":opponent,"location":location,
            "phase":phase_from_text(row_text),
            "source_url":source["url"]
        })
    return events

def parse_nebraska(src, source):
    soup=BeautifulSoup(src,"html.parser")
    lines=[clean(x) for x in soup.get_text("\n").splitlines() if clean(x)]
    events=[]
    site_tokens={"Home":"HOME","Away":"AWAY","Neutral":"NEUTRAL"}
    i=0
    while i<len(lines):
        if lines[i] not in site_tokens:
            i+=1
            continue
        site=site_tokens[lines[i]]
        block=lines[i:i+22]
        date=None; date_idx=None
        for j,x in enumerate(block[1:],start=1):
            d=parse_date_text(x)
            if d:
                date=d; date_idx=j; break
        if not date or not in_season_window(date):
            i+=1
            continue
        time="TBA"
        for x in block[date_idx+1:]:
            if re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b",x,re.I) or x.upper()=="TBA":
                time=x; break
        opponent=""
        for j,x in enumerate(block):
            if x.lower() in ("vs.","vs","at"):
                for y in block[j+1:j+6]:
                    if re.fullmatch(r"#\d+",y): continue
                    if y.lower() in ("opens in a new window","open info","watch","listen","live stats"): continue
                    if not re.search(r"\b(AM|PM)\b",y,re.I):
                        opponent=y; break
                if opponent: break
        location=""
        if opponent in block:
            oi=block.index(opponent)
            for y in block[oi+1:oi+6]:
                low=y.lower()
                if any(k in low for k in ["open info","watch","listen","box score","recap","buy tickets","preview"]):
                    continue
                if y in site_tokens or y.lower() in ("vs.","vs","at"):
                    continue
                location=y; break
        block_text=" | ".join(block)
        if looks_like_promo(block_text) or not looks_like_real_opponent(opponent):
            i+=max(1,(date_idx or 1)+2)
            continue
        events.append({
            "date":date.isoformat(),"time":time,"site":site,
            "opponent":opponent or "TBA","location":location,
            "phase":phase_from_text(block_text),
            "source_url":source["url"]
        })
        i+=max(1,(date_idx or 1)+2)
    # dedupe
    seen=set(); out=[]
    for e in events:
        key=(e["date"],e["time"],e["site"],e["opponent"])
        if key not in seen:
            seen.add(key); out.append(e)
    return out

def parse_omaha(src, source):
    soup=BeautifulSoup(src,"html.parser")
    lines=[clean(x) for x in soup.get_text("\n").splitlines() if clean(x)]
    events=[]
    for i,line in enumerate(lines):
        date=parse_date_text(line)
        if not date or not in_season_window(date):
            continue
        token_idx=None
        for j in range(i-1,max(-1,i-14),-1):
            if lines[j].lower() in ("at","vs","vs."):
                token_idx=j; break
        if token_idx is None:
            continue
        token=lines[token_idx].lower()
        site="AWAY" if token=="at" else "HOME"
        opponent=""
        opp_idx=None
        for j in range(token_idx+1,i):
            x=lines[j]; low=x.lower()
            if low in ("at","vs","vs.") or low.startswith("image:"):
                continue
            if re.fullmatch(r"#\d+",x):
                continue
            opponent=x; opp_idx=j; break
        if not opponent or not looks_like_real_opponent(opponent):
            continue
        location=""
        for j in range((opp_idx or token_idx)+1,i):
            x=lines[j]; low=x.lower()
            if any(k in low for k in ["live stats","history","tickets","schedule","image:"]):
                continue
            if parse_date_text(x):
                continue
            location=x; break
        time="TBA"
        for x in lines[i+1:i+8]:
            if re.search(r"\b\d{1,2}(?::\d{2})?\s*(a\.?m\.?|p\.?m\.?|am|pm)\b",x,re.I) or x.upper()=="TBA":
                time=x; break
        block=" | ".join(lines[max(0,token_idx-4):min(len(lines),i+8)])
        if looks_like_promo(block):
            continue
        events.append({
            "date":date.isoformat(),"time":time,"site":site,
            "opponent":opponent,"location":location,
            "phase":phase_from_text(block),
            "source_url":source["url"]
        })
    seen=set(); out=[]
    for e in events:
        key=(e["date"],e["time"],e["site"],e["opponent"])
        if key not in seen:
            seen.add(key); out.append(e)
    return out

def cutoff_state(cutoff):
    if not cutoff:
        return {
            "status":"NOT SCHEDULED",
            "color":"gray",
            "days_to_cutoff":None,
            "label":"CUTOFF NOT YET KNOWN"
        }
    d=datetime.date.fromisoformat(cutoff["date"])
    days=(d-TODAY).days
    if days < 0:
        return {"status":"PASSED","color":"red","days_to_cutoff":days,"label":"CUTOFF PASSED"}
    if days == 0:
        return {"status":"TODAY","color":"amber","days_to_cutoff":0,"label":"CUTOFF TODAY"}
    if days <= 7:
        return {"status":"APPROACHING","color":"amber","days_to_cutoff":days,"label":"CUTOFF APPROACHING"}
    return {"status":"NOT DUE","color":"green","days_to_cutoff":days,"label":"NOT DUE"}

programs=[]
source_status=[]

for source in SOURCES:
    events=[]
    ok=False
    error=None
    try:
        r=requests.get(source["url"],headers=HEADERS,timeout=30)
        r.raise_for_status()
        if source["parser"]=="creighton":
            events=parse_creighton(r.text,source)
        elif source["parser"]=="omaha":
            events=parse_omaha(r.text,source)
        else:
            events=parse_nebraska(r.text,source)
        ok=True
    except Exception as exc:
        error=str(exc)[:180]

    events=sorted(events,key=lambda e:(e["date"],e["time"]=="TBA",e["time"]))

    regular=[
        e for e in events
        if e["phase"]=="REGULAR SEASON"
        and looks_like_real_opponent(e.get("opponent"))
        and in_season_window(datetime.date.fromisoformat(e["date"]))
    ]
    postseason=[
        e for e in events
        if e["phase"]=="POSTSEASON"
        and looks_like_real_opponent(e.get("opponent"))
        and in_season_window(datetime.date.fromisoformat(e["date"]))
    ]

    first_regular=regular[0] if regular else None
    first_postseason=postseason[0] if postseason else None

    reg_state=cutoff_state(first_regular)
    post_state=cutoff_state(first_postseason)

    programs.append({
        "school":source["school"],
        "sport":source["sport"],
        "source_url":source["url"],
        "schedule_events_found":len(events),
        "first_regular_season_contest":first_regular,
        "regular_season_futures":{
            "rule":"Disable before first regular-season contest.",
            **reg_state
        },
        "first_postseason_contest":first_postseason,
        "postseason_futures":{
            "rule":"Disable before first postseason contest, if applicable.",
            "qualification_note":"Applies if/when the team qualifies for postseason play.",
            **post_state
        }
    })

    source_status.append({
        "school":source["school"],"sport":source["sport"],"url":source["url"],
        "ok":ok,"events_found":len(events),"error":error
    })

out={
    "schema_version":1,
    "generated_at":NOW_UTC.isoformat(),
    "timezone":"America/Chicago",
    "scope":"Nebraska collegiate Division I basketball futures cutoffs",
    "season":"2026-27",
    "rules":{
        "regular_season":"Disable Nebraska collegiate regular-season futures before the team's first regular-season contest.",
        "postseason":"Disable Nebraska collegiate postseason futures before the team's first postseason contest, if applicable."
    },
    "alert_window_days":7,
    "programs":programs,
    "sources":source_status
}

(DATA/"nebraska-collegiate-futures.json").write_text(json.dumps(out,indent=2),encoding="utf-8")

print(json.dumps({
    "programs":len(programs),
    "sources_ok":sum(1 for x in source_status if x["ok"]),
    "sources_total":len(source_status),
    "regular_cutoffs_found":sum(1 for x in programs if x["first_regular_season_contest"]),
    "postseason_cutoffs_found":sum(1 for x in programs if x["first_postseason_contest"])
}))
