#!/usr/bin/env python3
from pathlib import Path
import json, re, datetime, requests
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
    {"school":"Nebraska","sport":"Football","url":"https://huskers.com/sports/football/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Volleyball","url":"https://huskers.com/sports/volleyball/schedule?view=list","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Soccer","url":"https://huskers.com/sports/soccer/schedule/season/2026","parser":"nebraska"},
    {"school":"Nebraska","sport":"Men's Basketball","url":"https://huskers.com/sports/mens-basketball/schedule","parser":"nebraska"},
    {"school":"Nebraska","sport":"Women's Basketball","url":"https://huskers.com/sports/womens-basketball/schedule","parser":"nebraska"},

    {"school":"Creighton","sport":"Men's Soccer","url":"https://gocreighton.com/sports/mens-soccer/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Soccer","url":"https://gocreighton.com/sports/womens-soccer/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Volleyball","url":"https://gocreighton.com/sports/womens-volleyball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Men's Basketball","url":"https://gocreighton.com/sports/mens-basketball/schedule/text","parser":"creighton"},
    {"school":"Creighton","sport":"Women's Basketball","url":"https://gocreighton.com/sports/womens-basketball/schedule/text","parser":"creighton"}
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
    if not table: return events
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
            "phase":"EXHIBITION" if "exhibition" in tournament.lower() else "REGULAR SEASON",
            "status":status,"result":result,"source_url":source["url"]
        })
    return events

def parse_nebraska(src, source):
    soup=BeautifulSoup(src,"html.parser")
    # The Nebraska site exposes readable schedule content in page text.
    lines=[clean(x) for x in soup.get_text("\n").splitlines() if clean(x)]
    events=[]
    site_tokens={"Home":"HOME","Away":"AWAY","Neutral":"NEUTRAL"}
    i=0
    while i<len(lines):
        if lines[i] not in site_tokens:
            i+=1; continue
        site=site_tokens[lines[i]]
        block=lines[i:i+18]
        # find date in block
        date=None; date_idx=None
        for j,x in enumerate(block[1:],start=1):
            d=parse_date_text(x)
            if d:
                date=d; date_idx=j; break
        if not date:
            i+=1; continue
        # jump if outside window but still advance to next event
        # time
        time="TBA"
        for x in block[date_idx+1:]:
            if re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b",x,re.I) or x.upper()=="TBA":
                time=x; break
        # opponent after vs./at token
        opp=""
        for j,x in enumerate(block):
            if x.lower() in ("vs.","vs","at"):
                for y in block[j+1:j+5]:
                    if re.fullmatch(r"#\d+",y): continue
                    if y.lower() in ("opens in a new window","open info","watch","listen","live stats"): continue
                    if not re.search(r"\b(AM|PM)\b",y,re.I):
                        opp=y; break
                if opp: break
        # location: line after opponent that looks geographic/stadium-ish
        loc=""
        if opp in block:
            oi=block.index(opp)
            for y in block[oi+1:oi+5]:
                low=y.lower()
                if any(k in low for k in ["open info","watch","listen","box score","recap","buy tickets","preview"]): continue
                if y in site_tokens or y.lower() in ("vs.","vs","at"): continue
                loc=y; break

        result=""
        status="SCHEDULED"
        for x in block[date_idx+1:date_idx+5]:
            if re.match(r"^(W|L|T)\b",x):
                result=x; status="FINAL"; break

        phase="EXHIBITION" if any("exhibition" in x.lower() for x in block) else "REGULAR SEASON"
        if TODAY <= date <= END:
            events.append({
                "school":source["school"],"sport":source["sport"],"date":date.isoformat(),
                "time":time,"site":site,"opponent":opp or "TBA","location":loc,
                "phase":phase,"status":status,"result":result,"source_url":source["url"]
            })
        i += max(1,date_idx+2)
    # dedupe
    seen=set(); unique=[]
    for e in events:
        key=(e["school"],e["sport"],e["date"],e["time"],e["site"],e["opponent"])
        if key not in seen:
            seen.add(key); unique.append(e)
    return unique

events=[]
source_status=[]
for source in SOURCES:
    try:
        r=requests.get(source["url"],headers=HEADERS,timeout=30)
        r.raise_for_status()
        parsed=parse_creighton(r.text,source) if source["parser"]=="creighton" else parse_nebraska(r.text,source)
        events.extend(parsed)
        source_status.append({"school":source["school"],"sport":source["sport"],"url":source["url"],"ok":True,"events_in_window":len(parsed)})
    except Exception as e:
        source_status.append({"school":source["school"],"sport":source["sport"],"url":source["url"],"ok":False,"error":str(e)[:180],"events_in_window":0})

# Sort by date/time with TBA last.
events.sort(key=lambda e:(e["date"], e["time"]=="TBA", e["time"], e["school"], e["sport"]))

# Regulatory site-location determination.
for e in events:
    if e["site"]=="HOME":
        e["site_test"]="NOT PERMISSIBLE"
        e["site_color"]="red"
    elif e["site"] in ("AWAY","NEUTRAL"):
        e["site_test"]="SITE TEST PASSES"
        e["site_color"]="green"
    else:
        e["site_test"]="SITE REVIEW"
        e["site_color"]="amber"

out={
    "schema_version":1,
    "generated_at":NOW.isoformat(),
    "timezone":"America/Chicago",
    "window_start":TODAY.isoformat(),
    "window_end":END.isoformat(),
    "events":events,
    "sources":source_status
}
(DATA/"nebraska-collegiate-live.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({
    "window":f"{TODAY} through {END}",
    "events":len(events),
    "sources_ok":sum(1 for x in source_status if x["ok"]),
    "sources_total":len(source_status)
}))
