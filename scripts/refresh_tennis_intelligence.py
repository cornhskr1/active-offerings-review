#!/usr/bin/env python3
import json, hashlib, datetime, re
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
YEAR=TODAY.year
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/2.0; public regulatory reference)"}

ATP_CALENDAR="https://www.atptour.com/en/tournaments/"
ATP_CHALLENGER="https://www.atptour.com/en/atp-challenger-tour"
ATP_RANKINGS="https://www.atptour.com/en/rankings/singles?rankRange=1-1000"
WTA_CALENDAR="https://www.wtatennis.com/tournaments"
WTA_125="https://www.wtatennis.com/tournaments/wta-125"
WTA_RANKINGS="https://www.wtatennis.com/rankings/singles/"
ITF_MEN=f"https://www.itftennis.com/en/tournament-calendar/mens-world-tennis-tour-calendar/?categories=All&startdate={TODAY:%Y-%m}"
ITF_WOMEN=f"https://www.itftennis.com/en/tournament-calendar/womens-world-tennis-tour-calendar/?categories=All&startdate={TODAY:%Y-%m}"
ITF_JUNIOR_BOYS="https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=B"
ITF_JUNIOR_GIRLS="https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=G"
UTR_CLUBS={
 "Americas":"https://app.utrsports.net/club/11313",
 "Europe":"https://app.utrsports.net/club/12083",
 "Asia & Pacific":"https://app.utrsports.net/club/12084?tab=info",
}

TOUR_FAMILIES=[
 {"id":"atp","gender":"MEN","tour":"ATP Tour"},
 {"id":"atp-challenger","gender":"MEN","tour":"ATP Challenger Tour"},
 {"id":"itf-men","gender":"MEN","tour":"ITF Men's World Tennis Tour"},
 {"id":"utr-men","gender":"MEN","tour":"UTR Pro Tennis Tour"},
 {"id":"wta","gender":"WOMEN","tour":"WTA Tour"},
 {"id":"wta-125","gender":"WOMEN","tour":"WTA 125"},
 {"id":"itf-women","gender":"WOMEN","tour":"ITF Women's World Tennis Tour"},
 {"id":"utr-women","gender":"WOMEN","tour":"UTR Pro Tennis Tour"},
]

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def fetch(url,timeout=25):
    r=requests.get(url,headers=HEADERS,timeout=timeout)
    r.raise_for_status()
    return r

def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\u2018\u2019'`]", "", s)
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

def overlaps(a,b):
    return bool(a and b and a<=END and b>=TODAY)

def parse_date(s):
    s=re.sub(r"\s+"," ",str(s or "")).strip()
    fmts=[
      "%d %B %Y","%d %b %Y","%B %d, %Y","%b %d, %Y",
      "%Y-%m-%d"
    ]
    for f in fmts:
        try:return datetime.datetime.strptime(s,f).date()
        except Exception:pass
    return None

def parse_range(text):
    t=re.sub(r"\s+"," ",str(text or ""))
    patterns=[
      # 7 - 13 September, 2026
      r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',
      # 30 September - 6 October, 2026
      r'(\d{1,2})\s+([A-Za-z]+)\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',
      # 7 Sep to 13 Sep 2026
      r'(\d{1,2})\s+([A-Za-z]+)\s+(?:to|[-–])\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
      # Sep 7 - 13, 2026
      r'([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})',
    ]
    for i,p in enumerate(patterns):
        m=re.search(p,t,re.I)
        if not m:continue
        try:
            if i==0:
                d1,d2,mo,y=m.groups()
                a=parse_date(f"{d1} {mo} {y}"); b=parse_date(f"{d2} {mo} {y}")
            elif i in (1,2):
                d1,mo1,d2,mo2,y=m.groups()
                a=parse_date(f"{d1} {mo1} {y}"); b=parse_date(f"{d2} {mo2} {y}")
            else:
                mo,d1,d2,y=m.groups()
                a=parse_date(f"{d1} {mo} {y}"); b=parse_date(f"{d2} {mo} {y}")
            if a and b:return a,b
        except Exception:pass
    return None,None

def explicit_age_or_dob(text,on_date):
    txt=re.sub(r"\s+"," ",str(text or ""))
    am=re.search(r'\bAge\s*:?\s*(1[4-9]|[2-4]\d)\b',txt,re.I)
    if am:
        return int(am.group(1)),None
    pats=[
      r'(?:Birthday|Date of Birth|DOB|Born)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
      r'(?:Birthday|Date of Birth|DOB|Born)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
    ]
    for p in pats:
        m=re.search(p,txt,re.I)
        if not m:continue
        raw=m.group(1)
        for f in ("%d %B %Y","%d %b %Y","%B %d, %Y","%B %d %Y","%b %d, %Y"):
            try:
                dob=datetime.datetime.strptime(raw,f).date()
                age=on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))
                return age,dob.isoformat()
            except Exception:pass
    return None,None

def clean_name(s):
    s=re.sub(r"\s+"," ",str(s or "")).strip()
    s=re.sub(r"\b(Profile|Player Profile|Results|Draws?)\b$","",s,flags=re.I).strip()
    return s

def plausible_player(name):
    if not name or len(name)<4 or len(name)>80:return False
    if len(name.split())<2:return False
    bad=("tournament","calendar","results","draws","tickets","schedule","overview","singles","doubles","official")
    return not any(x in name.lower() for x in bad)

# ---------------- age indexes ----------------
def ranking_age_index(url,profile_re,source):
    out={}; health={"ok":False,"records":0,"url":url}
    try:
        soup=BeautifulSoup(fetch(url).text,"html.parser")
        for tr in soup.find_all("tr"):
            a=tr.find("a",href=re.compile(profile_re,re.I))
            if not a:continue
            name=clean_name(" ".join(a.stripped_strings))
            if not plausible_player(name):continue
            cells=[" ".join(td.stripped_strings).strip() for td in tr.find_all(["td","th"])]
            age=None
            for c in cells:
                if re.fullmatch(r"(1[4-9]|[2-4]\d)",c):
                    age=int(c);break
            if age is None:continue
            out[norm(name)]={
              "name":name,"age":age,"age_status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
              "source":source,"source_url":urljoin(url,a.get("href","")),
              "evidence":f"Official ranking table lists age {age}."
            }
        health.update(ok=True,records=len(out))
    except Exception as e:
        health["error"]=str(e)[:180]
    return out,health

profile_cache={}
def verify_profile(name,url,on_date,source):
    key=(url,on_date.isoformat())
    if key in profile_cache:return profile_cache[key]
    rec={"name":name,"age":None,"dob":None,"age_status":"UNRESOLVED","source":source,"source_url":url,
         "evidence":"Official player profile found; explicit age/DOB not resolved."}
    try:
        txt=" ".join(BeautifulSoup(fetch(url,18).text,"html.parser").stripped_strings)
        age,dob=explicit_age_or_dob(txt,on_date)
        if age is not None:
            rec.update(age=age,dob=dob,age_status="VERIFIED U18" if age<18 else "VERIFIED 18+",
                       evidence=f"Official player profile verifies age {age}.")
    except Exception as e:
        rec["evidence"]=f"Profile fetch failed: {str(e)[:100]}"
    profile_cache[key]=rec
    return rec

# ---------------- tournament discovery ----------------
def discover_calendar(url,tour_id,tour_name,gender,profile_domain):
    out=[]; health={"ok":False,"events":0,"url":url}
    try:
        soup=BeautifulSoup(fetch(url).text,"html.parser")
        seen=set()
        href_re=r"/en/tournaments/" if "atptour.com" in url else r"/tournaments/"
        for a in soup.find_all("a",href=re.compile(href_re,re.I)):
            href=urljoin(url,a.get("href",""))
            if not href or href in seen:continue
            node=a; start=end=None
            for _ in range(7):
                txt=" ".join(node.stripped_strings)
                start,end=parse_range(txt)
                if start and end:break
                if not node.parent:break
                node=node.parent
            if not overlaps(start,end):continue
            text=" ".join(node.stripped_strings)
            name=clean_name(" ".join(a.stripped_strings))
            if not name or len(name)<3:
                # Try heading in local card.
                h=node.find(["h2","h3","h4"])
                name=clean_name(" ".join(h.stripped_strings)) if h else ""
            if not name:continue
            # WTA main calendar can contain WTA125; keep family clean.
            if tour_id=="wta" and "WTA 125" in text.upper():continue
            seen.add(href)
            loc=""
            # Usually date text is followed/preceded by city-country in the card.
            m=re.search(r'([A-Za-zÀ-ÿ .\'-]+),\s*([A-Za-zÀ-ÿ .\'-]+)',text)
            if m:loc=f"{m.group(1).strip()}, {m.group(2).strip()}"
            out.append({
              "id":hashlib.sha1(f"{tour_id}|{href}|{start}".encode()).hexdigest()[:12],
              "tour_id":tour_id,"tour":tour_name,"gender":gender,"tournament":name,
              "start_date":start.isoformat(),"end_date":end.isoformat(),
              "location":loc,"status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
              "source_url":href,"participants":[],"participant_source":"Official tournament page"
            })
        health.update(ok=True,events=len(out))
    except Exception as e:
        health["error"]=str(e)[:180]
    return out,health

def discover_itf(url,tour_id,tour_name,gender):
    out=[]; health={"ok":False,"events":0,"url":url}
    try:
        soup=BeautifulSoup(fetch(url).text,"html.parser")
        seen=set()
        # Prefer table rows; ITF server-rendered calendars expose structured rows.
        for tr in soup.find_all("tr"):
            txt=" ".join(tr.stripped_strings)
            start,end=parse_range(txt.replace("Date:",""))
            if not overlaps(start,end):continue
            if "cancelled" in txt.lower():continue
            a=tr.find("a",href=re.compile(r"/en/tournament/",re.I))
            if not a:continue
            href=urljoin("https://www.itftennis.com",a["href"])
            if href in seen:continue
            seen.add(href)
            name=clean_name(" ".join(a.stripped_strings))
            city=""
            cm=re.search(r'City/Town:([^|]+?)(?:Category:|Prize|Surface|Status:|$)',txt,re.I)
            if cm:city=cm.group(1).strip()
            cat=""
            catm=re.search(r'Category:\s*([MW]\d+)',txt,re.I)
            if catm:cat=catm.group(1).upper()
            fact=re.sub(r'/(acceptance-list|draws-and-results|order-of-play|overview)/?$','/fact-sheet/',href)
            if "/fact-sheet/" not in fact:fact=fact.rstrip("/")+"/fact-sheet/"
            out.append({
              "id":hashlib.sha1(f"{tour_id}|{fact}|{start}".encode()).hexdigest()[:12],
              "tour_id":tour_id,"tour":tour_name,"gender":gender,"tournament":name,
              "category":cat,"start_date":start.isoformat(),"end_date":end.isoformat(),
              "location":city,"status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
              "source_url":fact,
              "acceptance_url":fact.replace("/fact-sheet/","/acceptance-list/"),
              "draw_url":fact.replace("/fact-sheet/","/draws-and-results/"),
              "order_url":fact.replace("/fact-sheet/","/order-of-play/"),
              "participants":[],"participant_source":"ITF official acceptance list / draw / order of play"
            })
        # Fallback for cards rather than tables.
        if not out:
            for a in soup.find_all("a",href=re.compile(r"/en/tournament/",re.I)):
                node=a; start=end=None
                for _ in range(6):
                    txt=" ".join(node.stripped_strings); start,end=parse_range(txt.replace("Date:",""))
                    if start and end:break
                    if not node.parent:break
                    node=node.parent
                if not overlaps(start,end):continue
                href=urljoin("https://www.itftennis.com",a["href"])
                name=clean_name(" ".join(a.stripped_strings))
                fact=href.rstrip("/")+"/fact-sheet/" if "/fact-sheet/" not in href else href
                out.append({
                  "id":hashlib.sha1(f"{tour_id}|{fact}|{start}".encode()).hexdigest()[:12],
                  "tour_id":tour_id,"tour":tour_name,"gender":gender,"tournament":name,
                  "start_date":start.isoformat(),"end_date":end.isoformat(),"location":"",
                  "status":"ACTIVE" if start<=TODAY<=end else "UPCOMING","source_url":fact,
                  "acceptance_url":fact.replace("/fact-sheet/","/acceptance-list/"),
                  "draw_url":fact.replace("/fact-sheet/","/draws-and-results/"),
                  "order_url":fact.replace("/fact-sheet/","/order-of-play/"),
                  "participants":[],"participant_source":"ITF official acceptance list / draw / order of play"
                })
        health.update(ok=True,events=len(out))
    except Exception as e:
        health["error"]=str(e)[:180]
    return out,health

def discover_utr():
    out=[]; health=[]
    for region,url in UTR_CLUBS.items():
        count=0
        try:
            soup=BeautifulSoup(fetch(url).text,"html.parser")
            seen=set()
            for a in soup.find_all("a",href=True):
                href=a["href"]; text=" ".join(a.stripped_strings)
                if "/events/" not in href:continue
                start,end=parse_range(text)
                if not overlaps(start,end):continue
                full=urljoin("https://app.utrsports.net",href)
                if full in seen:continue
                seen.add(full)
                low=text.lower()
                gender="WOMEN" if "women" in low else "MEN"
                tid="utr-women" if gender=="WOMEN" else "utr-men"
                name=re.sub(r'\s+',' ',text).strip()
                name=re.sub(r'^(?:[A-Za-z]{3}\s+\d{1,2}\s*[-–]\s*(?:[A-Za-z]{3}\s+)?\d{1,2}\s*)+','',name)
                name=re.sub(r'\b\d{4}\s+tennis Tournament\s*\|\s*Verified Event\s*\|\s*','',name,flags=re.I)
                name=re.split(r'\s+(?:Free.?\\$?\d+|\$?\d+\s+Division Fees?|Division Fees?)',name,1,flags=re.I)[0].strip(" |")
                out.append({
                  "id":hashlib.sha1(f"{tid}|{full}".encode()).hexdigest()[:12],
                  "tour_id":tid,"tour":"UTR Pro Tennis Tour","gender":gender,"tournament":name[:100],
                  "start_date":start.isoformat(),"end_date":end.isoformat(),"location":region,
                  "status":"ACTIVE" if start<=TODAY<=end else "UPCOMING","source_url":full,
                  "participants":[],"participant_source":"UTR official public event page"
                });count+=1
            health.append({"ok":True,"region":region,"events":count,"url":url})
        except Exception as e:
            health.append({"ok":False,"region":region,"events":0,"url":url,"error":str(e)[:180]})
    return out,health

# ---------------- participant extraction ----------------
def profile_links_from_pages(urls,link_regex,base):
    found={}
    for url in urls:
        if not url:continue
        try:
            soup=BeautifulSoup(fetch(url,20).text,"html.parser")
            for a in soup.find_all("a",href=re.compile(link_regex,re.I)):
                name=clean_name(" ".join(a.stripped_strings))
                if plausible_player(name):
                    found[norm(name)]={"name":name,"profile_url":urljoin(base,a["href"])}
        except Exception:pass
    return list(found.values())

def enrich_tournament(t,age_index,known):
    start=datetime.date.fromisoformat(t["start_date"])
    tid=t["tour_id"]
    raw=[]
    if tid.startswith("itf-"):
        raw=profile_links_from_pages(
          [t.get("acceptance_url"),t.get("draw_url"),t.get("order_url"),t.get("source_url")],
          r"/en/players/","https://www.itftennis.com"
        )
    elif tid.startswith("atp"):
        url=t.get("source_url","")
        candidates=[url]
        if "/overview" in url:
            candidates += [url.replace("/overview","/draws"),url.replace("/overview","/results")]
        raw=profile_links_from_pages(candidates,r"/en/players/","https://www.atptour.com")
    elif tid.startswith("wta"):
        url=t.get("source_url","")
        candidates=[url,url.rstrip("/")+"/players",url.rstrip("/")+"/draws"]
        raw=profile_links_from_pages(candidates,r"/players/","https://www.wtatennis.com")
    elif tid.startswith("utr"):
        raw=profile_links_from_pages([t.get("source_url")],r"/(profiles?|players?)/","https://app.utrsports.net")

    participants=[]
    for p in raw:
        k=norm(p["name"])
        if k in known:
            participants.append({**p,**known[k]})
            continue
        if k in age_index:
            participants.append({**p,**age_index[k]})
            continue
        url=p.get("profile_url","")
        if "itftennis.com" in url:
            participants.append({**p,**verify_profile(p["name"],url,start,"ITF official player profile")})
        elif "atptour.com" in url:
            participants.append({**p,**verify_profile(p["name"],url,start,"ATP official player profile")})
        elif "wtatennis.com" in url:
            participants.append({**p,**verify_profile(p["name"],url,start,"WTA official player profile")})
        else:
            participants.append({**p,"age":None,"age_status":"UNRESOLVED","source":t["participant_source"],
                                 "evidence":"Participant is listed for the tournament; official age not resolved."})

    # Deduplicate by normalized name.
    uniq={}
    for p in participants:uniq[norm(p["name"])]=p
    participants=list(uniq.values())
    t["participants"]=sorted(participants,key=lambda p:(p.get("age_status")!="VERIFIED U18",p["name"]))
    t["participant_count"]=len(participants)
    t["verified_u18"]=[p for p in participants if p.get("age_status")=="VERIFIED U18"]
    t["verified_18plus_count"]=sum(p.get("age_status")=="VERIFIED 18+" for p in participants)
    t["unresolved_count"]=sum(p.get("age_status")=="UNRESOLVED" for p in participants)

    # Regulatory semantic:
    # RED = verified U18 accepted/listed in the professional tournament.
    # GREEN = participant field obtained AND all entrants resolved 18+.
    # AMBER = participant field unavailable or any unresolved entrant.
    if t["verified_u18"]:
        t["regulatory_status"]="NOT PERMISSIBLE — U18 EXPOSURE"
        t["status_color"]="RED"
    elif t["participant_count"] and t["unresolved_count"]==0:
        t["regulatory_status"]="OK — NO U18 IDENTIFIED"
        t["status_color"]="GREEN"
    else:
        t["regulatory_status"]="MANUAL REVIEW — PARTICIPANT/AGE COVERAGE"
        t["status_color"]="AMBER"
    return t

# ---------------- broader verified U18 watchlist ----------------
def junior_watchlist():
    out={}; health=[]
    for gender,url in [("MEN",ITF_JUNIOR_BOYS),("WOMEN",ITF_JUNIOR_GIRLS)]:
        count=0
        try:
            soup=BeautifulSoup(fetch(url).text,"html.parser")
            for tr in soup.find_all("tr"):
                txt=" | ".join(" ".join(x.stripped_strings) for x in tr.find_all(["td","th"]))
                yobm=re.search(r"\b(2008|2009|2010|2011|2012)\b",txt)
                a=tr.find("a",href=re.compile(r"/en/players/",re.I))
                if not yobm or not a:continue
                name=clean_name(" ".join(a.stripped_strings))
                if not plausible_player(name):continue
                yob=int(yobm.group(1))
                profile=urljoin("https://www.itftennis.com",a["href"])
                rec=None
                if yob>=2009:
                    age=YEAR-yob
                    rec={"name":name,"age":age,"age_status":"VERIFIED U18","gender":gender,
                         "source":"ITF official junior rankings","source_url":profile,
                         "evidence":f"Official ITF junior rankings list birth year {yob}."}
                else:
                    vr=verify_profile(name,profile,TODAY,"ITF official player profile")
                    if vr.get("age_status")=="VERIFIED U18":rec={**vr,"gender":gender}
                if rec:
                    out[norm(name)]=rec;count+=1
            health.append({"ok":True,"gender":gender,"verified_u18":count,"url":url})
        except Exception as e:
            health.append({"ok":False,"gender":gender,"verified_u18":0,"url":url,"error":str(e)[:180]})
    return out,health

seed=load(DATA/"tennis-known-u18.json",{}).get("records",[])
known={}
for x in seed:
    known[norm(x.get("name"))]={
      "name":x.get("name"),"age":x.get("age"),"age_status":"VERIFIED U18",
      "source":x.get("source") or "Verified U18 seed registry",
      "source_url":x.get("source_url"),"evidence":"Previously verified U18 registry record."
    }

junior,junior_health=junior_watchlist()
known={**junior,**known}

atp_age,atp_age_health=ranking_age_index(ATP_RANKINGS,r"/en/players/","ATP official rankings")
wta_age,wta_age_health=ranking_age_index(WTA_RANKINGS,r"/players/","WTA official rankings")
age_index={**atp_age,**wta_age}

tournaments=[]; source_health={}

x,h=discover_calendar(ATP_CALENDAR,"atp","ATP Tour","MEN","ATP");tournaments+=x;source_health["atp_calendar"]=h
x,h=discover_calendar(ATP_CHALLENGER,"atp-challenger","ATP Challenger Tour","MEN","ATP");tournaments+=x;source_health["atp_challenger"]=h
x,h=discover_calendar(WTA_CALENDAR,"wta","WTA Tour","WOMEN","WTA");tournaments+=x;source_health["wta_calendar"]=h
x,h=discover_calendar(WTA_125,"wta-125","WTA 125","WOMEN","WTA");tournaments+=x;source_health["wta_125"]=h
x,h=discover_itf(ITF_MEN,"itf-men","ITF Men's World Tennis Tour","MEN");tournaments+=x;source_health["itf_men"]=h
x,h=discover_itf(ITF_WOMEN,"itf-women","ITF Women's World Tennis Tour","WOMEN");tournaments+=x;source_health["itf_women"]=h
x,h=discover_utr();tournaments+=x;source_health["utr"]=h
source_health["atp_age"]=atp_age_health
source_health["wta_age"]=wta_age_health
source_health["itf_juniors"]=junior_health

# Remove duplicate official cards.
dedup={}
for t in tournaments:
    key=(t["tour_id"],norm(t["tournament"]),t["start_date"])
    dedup[key]=t
tournaments=list(dedup.values())

for i,t in enumerate(tournaments):
    tournaments[i]=enrich_tournament(t,age_index,known)

# Add current-exposure state to registry.
exposure=set()
for t in tournaments:
    for p in t.get("verified_u18",[]):exposure.add(norm(p["name"]))
registry=[]
for k,p in known.items():
    registry.append({**p,"current_exposure":k in exposure})
registry.sort(key=lambda p:(not p["current_exposure"],p["name"]))

risks=[]
for t in tournaments:
    for p in t.get("verified_u18",[]):
        risks.append({
          "severity":"RED","type":"VERIFIED U18 TOURNAMENT",
          "tour":t["tour"],"league":t["tour"],"sport":"Tennis",
          "tournament":t["tournament"],"event":t["tournament"],
          "start_time":t["start_date"],"player":p["name"],"athletes":[p["name"]],
          "age":p.get("age"),"source":p.get("source"),
          "reason":f'{p["name"]} is a verified U18 participant listed in {t["tournament"]}.',
          "staff_action":"Review all athlete-specific performance/nonperformance markets involving this participant across all licensed sportsbook platforms."
        })

tournaments.sort(key=lambda t:(
    0 if t["status_color"]=="RED" else 1 if t["status_color"]=="AMBER" else 2,
    t["start_date"],t["gender"],t["tour"],t["tournament"]
))

summary={
 "tournaments_mapped":len(tournaments),
 "men_tournaments":sum(t["gender"]=="MEN" for t in tournaments),
 "women_tournaments":sum(t["gender"]=="WOMEN" for t in tournaments),
 "red_tournaments":sum(t["status_color"]=="RED" for t in tournaments),
 "amber_tournaments":sum(t["status_color"]=="AMBER" for t in tournaments),
 "green_tournaments":sum(t["status_color"]=="GREEN" for t in tournaments),
 "participants_found":sum(t["participant_count"] for t in tournaments),
 "verified_u18_players":len(exposure)
}

out={
 "schema_version":4,
 "generated_at":NOW.isoformat(),
 "timezone":"America/Chicago",
 "window_start":TODAY.isoformat(),"window_end":END.isoformat(),
 "tour_families":TOUR_FAMILIES,
 "summary":summary,
 "tournaments":tournaments,
 "risk_queue":risks,
 "live_u18_registry":registry,
 "source_health":source_health,
 "methodology":{
   "red":"Verified U18 athlete appears on an official professional tournament entry/acceptance/player/draw/order-of-play source.",
   "amber":"Tournament is mapped but participant list or age coverage is incomplete.",
   "green":"Participant field was obtained and every listed participant was verified 18+.",
   "scope":"Main draw, qualifying, doubles, wild cards, accepted alternates/acceptance lists, and order-of-play participants are in scope."
 }
}
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(summary))
