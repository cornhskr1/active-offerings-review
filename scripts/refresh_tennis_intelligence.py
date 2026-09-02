
import json, hashlib, datetime, re, html
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TZ=ZoneInfo("America/Chicago")
NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=datetime.datetime.now(TZ).date()
END=TODAY+datetime.timedelta(days=7)
HEADERS={"User-Agent":"Mozilla/5.0 ActiveOfferingsReview/1.0"}

ITF_CALENDARS={
    "itf-men":"https://www.itftennis.com/en/tournament-calendar/mens-world-tennis-tour-calendar/?categories=All&startdate={ym}",
    "itf-women":"https://www.itftennis.com/en/tournament-calendar/womens-world-tennis-tour-calendar/?categories=All&startdate={ym}",
}
UTR_CLUBS={
    "Americas":"https://app.utrsports.net/club/11313",
    "Europe":"https://app.utrsports.net/club/12083",
    "Asia & Pacific":"https://app.utrsports.net/club/12084?tab=info",
}

def load(path,default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",str(s or "").lower()).strip()

def get(url, timeout=25):
    r=requests.get(url,headers=HEADERS,timeout=timeout)
    r.raise_for_status()
    return r

def parse_month_day_range(text, year):
    m=re.search(r'(\d{1,2})\s+([A-Za-z]{3})\s+(?:to|-)\s+(\d{1,2})\s+([A-Za-z]{3})\s+'+str(year),text,re.I)
    if not m:
        m=re.search(r'(\d{1,2})\s+([A-Za-z]{3})\s*(?:to|-)\s*(\d{1,2})\s+([A-Za-z]{3})',text,re.I)
    if not m: return None,None
    for fmt in ("%d %b %Y","%d %B %Y"):
        try:
            a=datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {year}",fmt).date()
            b=datetime.datetime.strptime(f"{m.group(3)} {m.group(4)} {year}",fmt).date()
            if b<a: b=b.replace(year=year+1)
            return a,b
        except Exception: pass
    return None,None

def parse_utr_range(text, year):
    # Examples: Aug 31 - Sep 6 / Sep 7 - 13
    m=re.search(r'([A-Za-z]{3})\s+(\d{1,2})\s*-\s*(?:(?:([A-Za-z]{3})\s+)?(\d{1,2}))',text)
    if not m:return None,None
    mon1,day1,mon2,day2=m.group(1),m.group(2),m.group(3) or m.group(1),m.group(4)
    try:
        a=datetime.datetime.strptime(f"{mon1} {day1} {year}","%b %d %Y").date()
        b=datetime.datetime.strptime(f"{mon2} {day2} {year}","%b %d %Y").date()
        if b<a:b=b.replace(year=year+1)
        return a,b
    except Exception:return None,None

def overlaps(a,b):
    return bool(a and b and a<=END and b>=TODAY)

def extract_itf_tournaments(lane):
    ym=TODAY.strftime("%Y-%m")
    url=ITF_CALENDARS[lane].format(ym=ym)
    out=[]
    try:
        soup=BeautifulSoup(get(url).text,"html.parser")
    except Exception as e:
        return [],{"ok":False,"url":url,"error":str(e)[:180]}

    seen=set()
    for a in soup.find_all("a",href=True):
        href=a["href"]
        if "/en/tournament/" not in href or "/2026/" not in href:
            continue
        fact=urljoin("https://www.itftennis.com",href)
        # normalize to fact sheet
        fact=re.sub(r'/(acceptance-list|draws-and-results|order-of-play)/?$',"/fact-sheet/",fact)
        if "/fact-sheet/" not in fact:
            if not fact.endswith("/"): fact+="/"
            fact+="fact-sheet/"
        if fact in seen: continue

        container=a
        for _ in range(4):
            if not container.parent:break
            container=container.parent
            txt=" ".join(container.stripped_strings)
            if re.search(r'\d{1,2}\s+[A-Za-z]{3}\s+(?:to|-)\s+\d{1,2}\s+[A-Za-z]{3}\s+2026',txt):
                break
        txt=" ".join(container.stripped_strings)
        start,end=parse_month_day_range(txt,2026)
        if not overlaps(start,end):continue

        label=" ".join(a.stripped_strings).strip()
        if not label:
            slug=fact.split("/en/tournament/")[1].split("/")[0]
            label=slug.replace("-"," ").upper()
        if "cancelled" in txt.lower(): status="CANCELLED"
        elif start<=TODAY<=end: status="ACTIVE"
        else: status="UPCOMING"

        seen.add(fact)
        out.append({
            "id":hashlib.sha1(fact.encode()).hexdigest()[:12],
            "lane":lane,
            "tournament":label,
            "start_date":start.isoformat(),
            "end_date":end.isoformat(),
            "status":status,
            "source_url":fact,
            "acceptance_url":fact.replace("/fact-sheet/","/acceptance-list/"),
            "draw_url":fact.replace("/fact-sheet/","/draws-and-results/"),
            "participants":[],
            "participant_source":"PENDING",
        })
    return out,{"ok":True,"url":url,"events":len(out)}

def player_name_from_anchor(a):
    txt=" ".join(a.stripped_strings).strip()
    txt=re.sub(r'\s+',' ',txt)
    if not txt or len(txt)<4 or len(txt)>80:return None
    if any(x in txt.lower() for x in ("profile","view","back","draw","result","acceptance")):return None
    return txt

def scan_embedded_names(soup):
    names=set()
    # official player profile links are strongest signal
    for a in soup.find_all("a",href=True):
        href=a["href"]
        if "/en/players/" in href:
            n=player_name_from_anchor(a)
            if n:names.add((n,urljoin("https://www.itftennis.com",href)))
    return names

def parse_dob(text):
    pats=[
        r'(?:Date of Birth|Date of birth|DOB|Born)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        r'(?:Date of Birth|Date of birth|DOB|Born)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'(?:Date of Birth|Date of birth|DOB|Born)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for p in pats:
        m=re.search(p,text,re.I)
        if not m:continue
        raw=m.group(1)
        for fmt in ("%d %B %Y","%d %b %Y","%B %d, %Y","%B %d %Y","%b %d, %Y","%d/%m/%Y","%m/%d/%Y","%d-%m-%Y"):
            try:return datetime.datetime.strptime(raw,fmt).date()
            except Exception:pass
    return None

def age_on(dob,on_date):
    return on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))

profile_cache={}
def inspect_profile(name,url,event_date):
    if url in profile_cache:return profile_cache[url]
    record={"name":name,"profile_url":url,"dob":None,"age":None,"age_status":"UNRESOLVED","evidence":"Official ITF player profile link found; explicit DOB not parsed."}
    try:
        text=" ".join(BeautifulSoup(get(url,18).text,"html.parser").stripped_strings)
        dob=parse_dob(text)
        if dob:
            age=age_on(dob,event_date)
            record.update({
                "dob":dob.isoformat(),
                "age":age,
                "age_status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
                "evidence":"Explicit birth information parsed from official ITF player profile."
            })
    except Exception as e:
        record["evidence"]=f"Official ITF profile fetch failed: {str(e)[:120]}"
    profile_cache[url]=record
    return record

def enrich_itf_tournament(t):
    if t["status"]=="CANCELLED":return t
    profiles={}
    source_used=[]
    for url,label in [(t["draw_url"],"Draws & Results"),(t["acceptance_url"],"Acceptance List")]:
        try:
            soup=BeautifulSoup(get(url,20).text,"html.parser")
            found=scan_embedded_names(soup)
            if found:source_used.append(label)
            for n,u in found:profiles[u]=n
        except Exception:
            pass
    event_date=datetime.date.fromisoformat(t["start_date"])
    players=[]
    # cap deep profile checks so workflow stays reasonable
    for u,n in list(profiles.items())[:80]:
        players.append(inspect_profile(n,u,event_date))
    t["participants"]=players
    t["participant_count"]=len(players)
    t["participant_source"]=" + ".join(source_used) if source_used else "Official tournament page loaded; participant links not exposed server-side"
    t["verified_u18"]=[p for p in players if p["age_status"]=="VERIFIED U18"]
    t["verified_18plus_count"]=sum(1 for p in players if p["age_status"]=="VERIFIED 18+")
    t["unresolved_count"]=sum(1 for p in players if p["age_status"]=="UNRESOLVED")
    return t

def extract_utr_events():
    out=[]
    health=[]
    seen=set()
    for region,url in UTR_CLUBS.items():
        try:
            soup=BeautifulSoup(get(url).text,"html.parser")
            count=0
            for a in soup.find_all("a",href=True):
                href=a["href"]
                if "/events/" not in href:continue
                txt=" ".join(a.stripped_strings)
                if "UTR" not in txt or "tennis" not in txt.lower():continue
                start,end=parse_utr_range(txt,TODAY.year)
                if not overlaps(start,end):continue
                full=urljoin("https://app.utrsports.net",href)
                if full in seen:continue
                seen.add(full)
                gender="Women" if re.search(r'\bWomen\b',txt,re.I) else "Men" if re.search(r'\bMen\b',txt,re.I) else "Unknown"
                title=re.search(r'(UTR(?: Pro Fall Slam| PTT)[^$]+?(?:Men|Women)(?:\s*\+H)?)',txt,re.I)
                name=title.group(1).strip() if title else re.sub(r'^\w+\s+\d+\s*-\s*\w*\s*\d*\s*tennis.*?Verified Event\|?','',txt)[:100]
                reg=re.search(r'(\d+)\s*registered',txt,re.I)
                status="ACTIVE" if start<=TODAY<=end else "UPCOMING"
                out.append({
                    "id":hashlib.sha1(full.encode()).hexdigest()[:12],
                    "lane":"utr-women" if gender=="Women" else "utr-men",
                    "tournament":name,
                    "start_date":start.isoformat(),
                    "end_date":end.isoformat(),
                    "status":status,
                    "region":region,
                    "source_url":full,
                    "registered_count":int(reg.group(1)) if reg else None,
                    "participants":[],
                    "participant_count":0,
                    "participant_source":"Official UTR event discovered; public static event page did not expose participant list."
                })
                count+=1
            health.append({"region":region,"ok":True,"url":url,"events":count})
        except Exception as e:
            health.append({"region":region,"ok":False,"url":url,"events":0,"error":str(e)[:180]})
    return out,health

known=load(DATA/"tennis-known-u18.json",{}).get("records",[])
schedule=load(DATA/"global-schedule.json",{})
previous=load(DATA/"tennis-intelligence.json",{})

lanes=[
    {"id":"itf-men","label":"ITF Men","coverage":"LIVE OFFICIAL CALENDAR","source":"ITF Men's World Tennis Tour calendar + tournament pages","primary_age_source":"ITF official player profile"},
    {"id":"itf-women","label":"ITF Women","coverage":"LIVE OFFICIAL CALENDAR","source":"ITF Women's World Tennis Tour calendar + tournament pages","primary_age_source":"ITF official player profile"},
    {"id":"atp","label":"ATP","coverage":"MAPPED PUBLIC SCHEDULE","source":"Mapped public ATP scoreboard schedule","primary_age_source":"ATP / ITF official profile"},
    {"id":"wta","label":"WTA","coverage":"MAPPED PUBLIC SCHEDULE","source":"Mapped public WTA scoreboard schedule","primary_age_source":"WTA / ITF official profile"},
    {"id":"utr-men","label":"UTR Men","coverage":"LIVE OFFICIAL EVENT DISCOVERY","source":"Official UTR PTT regional club/event pages","primary_age_source":"Official profile where available"},
    {"id":"utr-women","label":"UTR Women","coverage":"LIVE OFFICIAL EVENT DISCOVERY","source":"Official UTR PTT regional club/event pages","primary_age_source":"Official profile where available"},
    {"id":"grand-slams","label":"Grand Slams","coverage":"DERIVED FROM ATP/WTA WHEN PRESENT","source":"Official event draw/order of play preferred","primary_age_source":"ATP / WTA / ITF / official event profile"},
]

# Existing ATP/WTA mapped matches
mapped=[]
for e in schedule.get("events",[]):
    if e.get("sport")!="Tennis":continue
    league=str(e.get("league") or "").upper()
    comp=str(e.get("competition") or e.get("tournament") or e.get("name") or "").upper()
    lane="grand-slams" if any(x in comp for x in ("AUSTRALIAN OPEN","ROLAND GARROS","FRENCH OPEN","WIMBLEDON","US OPEN")) else "atp" if league=="ATP" else "wta" if league=="WTA" else None
    if lane:mapped.append({**e,"lane":lane})

# Live ITF discovery/enrichment
itf_tournaments=[]
itf_health=[]
for lane in ("itf-men","itf-women"):
    found,h=extract_itf_tournaments(lane)
    itf_health.append({"lane":lane,**h})
    for t in found:
        itf_tournaments.append(enrich_itf_tournament(t))

# Live UTR discovery
utr_tournaments,utr_health=extract_utr_events()

# Group mapped ATP/WTA
mapped_groups={}
for e in mapped:
    tournament=e.get("tournament") or e.get("competition") or e.get("league") or "Tennis"
    key=f'{e["lane"]}|{tournament}'
    g=mapped_groups.setdefault(key,{
        "id":hashlib.sha1(key.encode()).hexdigest()[:12],
        "lane":e["lane"],"tournament":tournament,"events":[],"participants":set(),
        "source_url":e.get("source_endpoint"),"participant_source":"Mapped scoreboard competitors"
    })
    g["events"].append(e)
    parts=re.split(r"\s+(?:vs\.?|at)\s+",str(e.get("name") or ""),maxsplit=1,flags=re.I)
    for p in parts:
        if p.strip():g["participants"].add(p.strip())

known_by_name={norm(x["name"]):x for x in known}
tournaments=[]

for g in mapped_groups.values():
    parts=sorted(g["participants"])
    matched=[v for k,v in known_by_name.items() if any(k and k in norm(p) for p in parts)]
    tournaments.append({
        "id":g["id"],"lane":g["lane"],"tournament":g["tournament"],
        "status":"ACTIVE/UPCOMING","event_count":len(g["events"]),
        "participant_count":len(parts),"participants":[{"name":p,"age_status":"KNOWN U18" if any(norm(x["name"]) in norm(p) for x in matched) else "UNSCREENED"} for p in parts],
        "known_u18":matched,"known_u18_count":len(matched),
        "participant_source":g["participant_source"],"source_url":g["source_url"],
        "events":g["events"],"draw_changed":False
    })

for t in itf_tournaments:
    known_matches=[]
    for p in t.get("participants",[]):
        k=known_by_name.get(norm(p["name"]))
        if k:known_matches.append(k)
    t["known_u18"]=known_matches
    t["known_u18_count"]=len({x["name"] for x in known_matches})
    t["event_count"]=0
    t["events"]=[]
    t["draw_changed"]=False
    tournaments.append(t)

for t in utr_tournaments:
    t["known_u18"]=[]
    t["known_u18_count"]=0
    t["event_count"]=0
    t["events"]=[]
    t["draw_changed"]=False
    tournaments.append(t)

# Draw/field signature changes
prev_sig={x.get("id"):x.get("draw_signature") for x in previous.get("tournaments",[])}
risk_queue=[]
for t in tournaments:
    sig_src="|".join(sorted(p["name"] if isinstance(p,dict) else str(p) for p in t.get("participants",[])))
    sig_src+="|"+"|".join(str(e.get("id")) for e in t.get("events",[]))
    sig=hashlib.sha256(sig_src.encode()).hexdigest()[:16] if sig_src else None
    t["draw_signature"]=sig
    if sig and prev_sig.get(t["id"]) and prev_sig[t["id"]]!=sig:
        t["draw_changed"]=True
        risk_queue.append({
            "severity":"AMBER","type":"DRAW CHANGE","lane":t["lane"],"tournament":t["tournament"],
            "event":None,"start_time":t.get("events",[{}])[0].get("start_time") if t.get("events") else None,
            "player":None,"reason":"Participant/match signature changed since the prior tennis refresh.",
            "staff_action":"Re-screen the current draw/field for U18 exposure."
        })

    for p in t.get("participants",[]):
        if isinstance(p,dict) and p.get("age_status")=="VERIFIED U18":
            risk_queue.append({
                "severity":"RED","type":"VERIFIED U18","lane":t["lane"],"tournament":t["tournament"],
                "event":None,"start_time":t.get("events",[{}])[0].get("start_time") if t.get("events") else None,
                "player":p["name"],"age":p.get("age"),
                "reason":"Explicit DOB on official ITF profile calculates to under 18 on tournament start date.",
                "staff_action":"Search athlete-specific markets for this tournament/player."
            })

    for k in t.get("known_u18",[]):
        if not any(r.get("player")==k["name"] and r.get("tournament")==t["tournament"] for r in risk_queue):
            risk_queue.append({
                "severity":"RED","type":"KNOWN U18 MATCH","lane":t["lane"],"tournament":t["tournament"],
                "event":None,"start_time":t.get("events",[{}])[0].get("start_time") if t.get("events") else None,
                "player":k["name"],"age":k.get("age"),
                "reason":"Known U18 registry participant appears in the current tournament participant/match data.",
                "staff_action":"Search athlete-specific markets immediately."
            })

lane_counts={l["id"]:0 for l in lanes}
for t in tournaments:lane_counts[t["lane"]]=lane_counts.get(t["lane"],0)+1
for l in lanes:l["active_tournaments"]=lane_counts.get(l["id"],0)

summary={
    "lanes":len(lanes),
    "mapped_tournaments":len(tournaments),
    "mapped_matches":len(mapped),
    "itf_tournaments":len(itf_tournaments),
    "utr_tournaments":len(utr_tournaments),
    "known_u18_registry":len(known),
    "active_u18_triggers":sum(1 for r in risk_queue if r["severity"]=="RED"),
    "draw_changes":sum(1 for r in risk_queue if r["type"]=="DRAW CHANGE"),
    "itf_profiles_screened":sum(len(t.get("participants",[])) for t in itf_tournaments),
    "itf_age_verified":sum(sum(1 for p in t.get("participants",[]) if p.get("age_status") in ("VERIFIED U18","VERIFIED 18+")) for t in itf_tournaments),
}

out={
    "schema_version":2,
    "generated_at":NOW.isoformat(),
    "timezone":"America/Chicago",
    "window_start":TODAY.isoformat(),
    "window_end":END.isoformat(),
    "lanes":lanes,
    "tournaments":sorted(tournaments,key=lambda x:(x["lane"],x.get("start_date",""),x["tournament"])),
    "risk_queue":risk_queue,
    "known_u18_registry":known,
    "summary":summary,
    "source_health":{"itf":itf_health,"utr":utr_health},
    "methodology":{
        "itf":"Official ITF calendars discover current tournaments. Official tournament Draws & Results and Acceptance List pages are scanned for official player-profile links. Explicit DOB labels on official ITF profiles are used for age verification.",
        "utr":"Official UTR PTT regional club pages discover current/upcoming events. Participant lists are only ingested when exposed in public event HTML; otherwise event coverage is marked participant-pending.",
        "age_rule":"Bare dates are never treated as DOB. Only explicit Born / Date of Birth / DOB labels verify age.",
        "review_today_rule":"Only verified/known U18 or draw-change triggers tied to a current tournament are promoted operationally."
    }
}
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(summary))
