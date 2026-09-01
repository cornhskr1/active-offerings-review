#!/usr/bin/env python3
from pathlib import Path
import json, datetime, requests, re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA/"global-schedule-sources.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Chicago")
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()
END = TODAY + datetime.timedelta(days=int(CFG.get("window_days",7)))
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

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
    home=None; away=None
    for c in competitors:
        team=c.get("team") or {}
        name=team.get("displayName") or team.get("shortDisplayName") or team.get("name")
        if c.get("homeAway")=="home": home=name
        elif c.get("homeAway")=="away": away=name
    name=ev.get("name") or ev.get("shortName") or "Scheduled event"
    if home and away:
        name=f"{away} at {home}"
    dt=ev.get("date")
    status,detail=event_status(ev)
    venue=(comp.get("venue") or {}).get("fullName")
    address=(comp.get("venue") or {}).get("address") or {}
    location=", ".join(x for x in [address.get("city"),address.get("state"),address.get("country")] if x)
    if venue and location:
        location=f"{venue} · {location}"
    elif venue:
        location=venue
    return {
        "id":str(ev.get("id") or f'{source["id"]}-{dt}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":dt,
        "status":status,
        "status_detail":detail,
        "location":location or None,
        "source_endpoint":source["endpoint"]
    }

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

# Restriction cross-reference at sport level, intentionally conservative.
restrictions=[]
cat_path=DATA/"catalog-live.json"
if cat_path.exists():
    try:
        cat=json.loads(cat_path.read_text(encoding="utf-8"))
        restrictions=cat.get("restrictions",[])
    except Exception:
        pass

for ev in events:
    rel=[]
    for x in restrictions:
        sport=(x.get("sport") or "").lower()
        if sport and (sport in ev["sport"].lower() or ev["sport"].lower() in sport or ev["league"].lower() in (x.get("text") or "").lower()):
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
        "Surfing","Table Tennis","Tennis"
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
