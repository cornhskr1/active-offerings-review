#!/usr/bin/env python3
from pathlib import Path
import datetime, json, os, re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
CACHE=DATA/"ncaa-basketball-age-cache.json"
QUEUE=DATA/"ncaa-basketball-age-research-queue.json"
SOURCES=DATA/"ncaa-basketball-age-sources.json"
RESULTS=DATA/"ncaa-basketball-age-research-results.json"

NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=NOW.date()

MAX_RECORDS=int(os.getenv("MAX_RECORDS","40"))
MIN_PRIORITY=int(os.getenv("MIN_PRIORITY","800"))
ESPN_COOLDOWN_DAYS=int(os.getenv("ESPN_COOLDOWN_DAYS","7"))
OFFICIAL_COOLDOWN_DAYS=int(os.getenv("OFFICIAL_COOLDOWN_DAYS","14"))

LEAGUES={"Men":"mens-college-basketball","Women":"womens-college-basketball"}
HEADERS={
    "User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)",
    "Accept":"text/html,application/json,text/plain,*/*",
}
ESPN_URL="https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/athletes/{pid}?lang=en&region=us"

cache=json.loads(CACHE.read_text(encoding="utf-8"))
queue=json.loads(QUEUE.read_text(encoding="utf-8"))
sources=json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else {"local_priority":[]}

def norm(v):
    s=str(v or "").lower()
    s=re.sub(r"[“”\"'’`]", "", s)
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def pdt(v):
    if not v:return None
    try:return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except:return None

def pdob(v):
    if not v:return None
    try:return datetime.date.fromisoformat(str(v)[:10])
    except:return None

def calc_age(d):
    return TODAY.year-d.year-((TODAY.month,TODAY.day)<(d.month,d.day))

def find_rec(item):
    pid=str(item.get("player_id") or "")
    if pid:
        for r in cache.get("records",[]):
            if str(r.get("player_id") or "")==pid:return r
    for r in cache.get("records",[]):
        if r.get("gender")==item.get("gender") and r.get("team")==item.get("team") and r.get("athlete")==item.get("athlete"):
            return r

# ---- local official source lookup ----
official_sources={}
for school in sources.get("local_priority",[]):
    for alias in school.get("aliases",[]):
        official_sources[norm(alias)]=school

def official_roster_url(team,gender):
    school=official_sources.get(norm(team))
    if not school:return None
    return school.get("men_roster") if gender=="Men" else school.get("women_roster")

# Cache roster page -> athlete link map so one run does not fetch the same roster repeatedly.
roster_link_cache={}

def athlete_link_map(roster_url):
    if roster_url in roster_link_cache:
        return roster_link_cache[roster_url]
    result={}
    try:
        r=requests.get(roster_url,headers=HEADERS,timeout=25)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a",href=True):
            label=" ".join(a.stripped_strings)
            href=a.get("href")
            if not label or not href:continue
            n=norm(label)
            # Only keep likely athlete detail links.
            if "/roster/" in href or "/sports/" in href:
                result.setdefault(n,urljoin(roster_url,href))
    except Exception:
        result={}
    roster_link_cache[roster_url]=result
    return result

def find_bio_url(roster_url,athlete):
    links=athlete_link_map(roster_url)
    target=norm(athlete)
    if target in links:return links[target]

    # Exact token containment handles nicknames/middle names conservatively.
    tset=set(target.split())
    candidates=[]
    for label,url in links.items():
        lset=set(label.split())
        if target and (target in label or label in target):
            candidates.append((100,url))
        elif len(tset)>=2 and len(lset)>=2:
            overlap=len(tset & lset)/max(len(tset),len(lset))
            if overlap>=0.8:candidates.append((80,url))
    candidates.sort(reverse=True)
    if not candidates:return None
    if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
        return None
    return candidates[0][1]

MONTHS={
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12
}

def explicit_dob_from_text(text):
    # Strict labels only. Do not infer from graduation years or prose.
    patterns=[
        r"(?:date of birth|dob|birthday)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        r"(?:born|born on)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        r"(?:date of birth|dob|birthday)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})",
    ]
    lower=text.lower()
    for pat in patterns:
        m=re.search(pat,lower,re.I)
        if not m:continue
        raw=m.group(1).strip().replace(",","")
        parts=raw.split()
        if len(parts)==3 and parts[0].lower() in MONTHS:
            try:return datetime.date(int(parts[2]),MONTHS[parts[0].lower()],int(parts[1]))
            except:pass
        if "/" in raw:
            try:
                mm,dd,yy=[int(x) for x in raw.split("/")]
                return datetime.date(yy,mm,dd)
            except:pass
    return None

def explicit_age_from_text(text):
    # Only labeled "Age: 17", not incidental prose.
    m=re.search(r"\bage\s*[:\-]\s*(\d{1,2})\b",text,re.I)
    if m:
        try:return int(m.group(1))
        except:return None
    return None

def school_bio_evidence(team,gender,athlete):
    roster_url=official_roster_url(team,gender)
    if not roster_url:
        return None,{"reason":"NO OFFICIAL ROSTER SOURCE"}
    bio_url=find_bio_url(roster_url,athlete)
    if not bio_url:
        return None,{"reason":"NO UNIQUE OFFICIAL BIO LINK","roster_url":roster_url}
    try:
        r=requests.get(bio_url,headers=HEADERS,timeout=25)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")

        # Structured-data birthDate is explicit evidence.
        for tag in soup.find_all("script",type="application/ld+json"):
            raw=tag.string or tag.get_text()
            if "birthDate" in raw:
                try:
                    obj=json.loads(raw)
                    objs=obj if isinstance(obj,list) else [obj]
                    stack=list(objs)
                    while stack:
                        x=stack.pop()
                        if isinstance(x,dict):
                            if x.get("birthDate"):
                                d=pdob(x["birthDate"])
                                if d:
                                    return {"dob":d.isoformat(),"age":calc_age(d),"source":"Official school athlete bio",
                                            "note":f"birthDate supplied in official school bio structured data: {d.isoformat()}",
                                            "url":bio_url},{"reason":"VERIFIED"}
                            stack.extend(x.values())
                        elif isinstance(x,list):
                            stack.extend(x)
                except Exception:
                    pass

        text=" ".join(soup.stripped_strings)
        d=explicit_dob_from_text(text)
        if d:
            return {"dob":d.isoformat(),"age":calc_age(d),"source":"Official school athlete bio",
                    "note":f"Explicit DOB/birth date on official school athlete bio: {d.isoformat()}",
                    "url":bio_url},{"reason":"VERIFIED"}
        a=explicit_age_from_text(text)
        if a is not None:
            return {"dob":None,"age":a,"source":"Official school athlete bio",
                    "note":f"Explicit age on official school athlete bio: {a}",
                    "url":bio_url},{"reason":"VERIFIED"}

        return None,{"reason":"NO EXPLICIT DOB/AGE ON OFFICIAL BIO","bio_url":bio_url}
    except Exception as exc:
        return None,{"reason":"OFFICIAL BIO REQUEST ERROR","error":str(exc)[:180],"bio_url":bio_url}

def espn_evidence(rec):
    gender=rec.get("gender"); pid=str(rec.get("player_id") or "")
    league=LEAGUES.get(gender)
    if not league or not pid:return None,{"reason":"NO ESPN PROFILE ID"}
    url=ESPN_URL.format(league=league,pid=pid)
    try:
        r=requests.get(url,headers=HEADERS,timeout=20); r.raise_for_status()
        payload=r.json()
        dob=payload.get("dateOfBirth")
        age_val=payload.get("age")
        d=pdob(dob)
        if d:
            return {"dob":d.isoformat(),"age":calc_age(d),"source":"ESPN athlete profile",
                    "note":f"Date of birth supplied by ESPN athlete profile: {d.isoformat()}","url":url},{"reason":"VERIFIED"}
        if age_val not in (None,""):
            try:
                a=int(age_val)
                return {"dob":None,"age":a,"source":"ESPN athlete profile",
                        "note":f"Age supplied by ESPN athlete profile: {a}","url":url},{"reason":"VERIFIED"}
            except:pass
        return None,{"reason":"NO DOB/AGE ON ESPN PROFILE","url":url}
    except Exception as exc:
        return None,{"reason":"ESPN PROFILE REQUEST ERROR","error":str(exc)[:180],"url":url}

espn_cutoff=NOW-datetime.timedelta(days=ESPN_COOLDOWN_DAYS)
official_cutoff=NOW-datetime.timedelta(days=OFFICIAL_COOLDOWN_DAYS)

candidates=[]
for item in queue.get("queue",[]):
    if int(item.get("priority_score") or 0)<MIN_PRIORITY:continue
    rec=find_rec(item)
    if not rec:continue
    if str(rec.get("status") or "").upper() in ("VERIFIED U18","VERIFIED 18+"):continue

    # Eligible if either source has not been tried recently.
    espn_recent=(pdt(rec.get("last_researched_espn")) or pdt(rec.get("last_researched"))) 
    official_recent=pdt(rec.get("last_researched_official"))
    espn_eligible=not espn_recent or espn_recent<=espn_cutoff
    official_eligible=bool(official_roster_url(rec.get("team"),rec.get("gender"))) and (not official_recent or official_recent<=official_cutoff)
    if not espn_eligible and not official_eligible:continue
    candidates.append((item,rec,espn_eligible,official_eligible))

candidates=candidates[:MAX_RECORDS]

results=[]; vu18=v18=unres=0
for item,rec,do_espn,do_official in candidates:
    evidence=None
    attempts=[]

    if do_espn:
        rec["last_researched_espn"]=NOW.isoformat()
        ev,meta=espn_evidence(rec); attempts.append({"source":"ESPN","result":meta})
        if ev:evidence=ev

    if not evidence and do_official:
        rec["last_researched_official"]=NOW.isoformat()
        ev,meta=school_bio_evidence(rec.get("team"),rec.get("gender"),rec.get("athlete"))
        attempts.append({"source":"OFFICIAL SCHOOL","result":meta})
        if ev:evidence=ev

    rec["last_researched"]=NOW.isoformat()
    rec["research_attempts"]=int(rec.get("research_attempts") or 0)+1

    result={
        "gender":rec.get("gender"),"team":rec.get("team"),"athlete":rec.get("athlete"),
        "player_id":rec.get("player_id"),"priority_score":item.get("priority_score"),
        "priority_reasons":item.get("priority_reasons") or [],"attempts":attempts,
        "researched_at":NOW.isoformat()
    }

    if evidence:
        a=evidence["age"]
        status="VERIFIED U18" if a<18 else "VERIFIED 18+"
        rec["status"]=status
        rec["calculated_age"]=a
        if evidence.get("dob"):rec["dob"]=evidence["dob"]
        rec["evidence_source"]=evidence["source"]
        rec["evidence_note"]=evidence["note"]
        rec["evidence_url"]=evidence["url"]
        rec["verified_at"]=NOW.isoformat()
        rec["research_result"]=status
        result.update({"result":status,"age":a,"dob":evidence.get("dob"),"evidence_source":evidence["source"],"evidence_url":evidence["url"]})
        if status=="VERIFIED U18":vu18+=1
        else:v18+=1
    else:
        rec["research_result"]="NO EXPLICIT DOB/AGE"
        result["result"]="UNRESOLVED"
        unres+=1

    results.append(result)
    time.sleep(0.08)

summary={
    "attempted":len(results),
    "verified_u18":vu18,
    "verified_18_plus":v18,
    "unresolved":unres,
    "max_records":MAX_RECORDS,
    "min_priority":MIN_PRIORITY,
    "espn_cooldown_days":ESPN_COOLDOWN_DAYS,
    "official_cooldown_days":OFFICIAL_COOLDOWN_DAYS,
    "official_school_adapter":True
}

cache["generated_at"]=NOW.isoformat()
cache["research_summary"]=summary
CACHE.write_text(json.dumps(cache,indent=2),encoding="utf-8")
RESULTS.write_text(json.dumps({"schema_version":1,"generated_at":NOW.isoformat(),"summary":summary,"results":results},indent=2),encoding="utf-8")
print(json.dumps(summary))
