#!/usr/bin/env python3
from pathlib import Path
import datetime, json, os, time, requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
CACHE=DATA/"ncaa-basketball-age-cache.json"
QUEUE=DATA/"ncaa-basketball-age-research-queue.json"
RESULTS=DATA/"ncaa-basketball-age-research-results.json"

NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=NOW.date()
MAX_RECORDS=int(os.getenv("MAX_RECORDS","40"))
MIN_PRIORITY=int(os.getenv("MIN_PRIORITY","800"))
COOLDOWN_DAYS=int(os.getenv("RESEARCH_COOLDOWN_DAYS","7"))

LEAGUES={"Men":"mens-college-basketball","Women":"womens-college-basketball"}
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0)","Accept":"application/json,text/plain,*/*"}
URL="https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/athletes/{pid}?lang=en&region=us"

cache=json.loads(CACHE.read_text(encoding="utf-8"))
queue=json.loads(QUEUE.read_text(encoding="utf-8"))

def pdt(v):
    if not v:return None
    try:return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except:return None

def pdob(v):
    if not v:return None
    try:return datetime.date.fromisoformat(str(v)[:10])
    except:return None

def age(d):
    return TODAY.year-d.year-((TODAY.month,TODAY.day)<(d.month,d.day))

def find_rec(item):
    pid=str(item.get("player_id") or "")
    if pid:
        for r in cache.get("records",[]):
            if str(r.get("player_id") or "")==pid:return r
    for r in cache.get("records",[]):
        if r.get("gender")==item.get("gender") and r.get("team")==item.get("team") and r.get("athlete")==item.get("athlete"):
            return r

cutoff=NOW-datetime.timedelta(days=COOLDOWN_DAYS)
candidates=[]; skipped_recent=0
for item in queue.get("queue",[]):
    if int(item.get("priority_score") or 0)<MIN_PRIORITY: continue
    rec=find_rec(item)
    if not rec: continue
    if str(rec.get("status") or "").upper() in ("VERIFIED U18","VERIFIED 18+"): continue
    last=pdt(rec.get("last_researched"))
    if last and last>cutoff:
        skipped_recent+=1
        continue
    candidates.append((item,rec))
candidates=candidates[:MAX_RECORDS]

results=[]; vu18=v18=unres=0
for item,rec in candidates:
    gender=rec.get("gender"); pid=str(rec.get("player_id") or "")
    league=LEAGUES.get(gender)
    rec["last_researched"]=NOW.isoformat()
    rec["research_attempts"]=int(rec.get("research_attempts") or 0)+1
    result={"gender":gender,"team":rec.get("team"),"athlete":rec.get("athlete"),"player_id":pid or None,
            "priority_score":item.get("priority_score"),"priority_reasons":item.get("priority_reasons") or [],
            "official_roster_source":item.get("official_roster_source"),"researched_at":NOW.isoformat()}
    if not league or not pid:
        rec["research_result"]="NO PROFILE ID"; result["result"]="UNRESOLVED"; unres+=1; results.append(result); continue
    url=URL.format(league=league,pid=pid); result["profile_url"]=url
    try:
        r=requests.get(url,headers=HEADERS,timeout=20); r.raise_for_status(); payload=r.json()
        dob=payload.get("dateOfBirth") or ((payload.get("athlete") or {}).get("dateOfBirth") if isinstance(payload.get("athlete"),dict) else None)
        src_age=payload.get("age") or ((payload.get("athlete") or {}).get("age") if isinstance(payload.get("athlete"),dict) else None)
        dob_date=pdob(dob)
        resolved_age=age(dob_date) if dob_date else None
        if resolved_age is None and src_age not in (None,""):
            try: resolved_age=int(src_age)
            except: resolved_age=None
        if resolved_age is None:
            rec["research_result"]="NO DOB/AGE ON PROFILE"; result["result"]="UNRESOLVED"; unres+=1
        else:
            status="VERIFIED U18" if resolved_age<18 else "VERIFIED 18+"
            rec["status"]=status; rec["calculated_age"]=resolved_age; rec["dob"]=dob_date.isoformat() if dob_date else rec.get("dob")
            rec["evidence_source"]="ESPN athlete profile"; rec["evidence_url"]=url
            rec["evidence_note"]=(f"Date of birth supplied by ESPN athlete profile: {dob_date.isoformat()}" if dob_date
                                  else f"Age supplied by ESPN athlete profile: {resolved_age}")
            rec["verified_at"]=NOW.isoformat(); rec["research_result"]=status
            result["result"]=status; result["age"]=resolved_age; result["dob"]=dob_date.isoformat() if dob_date else None
            if status=="VERIFIED U18": vu18+=1
            else: v18+=1
    except Exception as exc:
        rec["research_result"]="PROFILE REQUEST ERROR"; result["result"]="UNRESOLVED"; result["note"]=str(exc)[:180]; unres+=1
    results.append(result); time.sleep(0.1)

summary={"attempted":len(results),"verified_u18":vu18,"verified_18_plus":v18,"unresolved":unres,
         "skipped_recent":skipped_recent,"max_records":MAX_RECORDS,"min_priority":MIN_PRIORITY,"cooldown_days":COOLDOWN_DAYS}
cache["generated_at"]=NOW.isoformat(); cache["research_summary"]=summary
CACHE.write_text(json.dumps(cache,indent=2),encoding="utf-8")
RESULTS.write_text(json.dumps({"schema_version":1,"generated_at":NOW.isoformat(),"summary":summary,"results":results},indent=2),encoding="utf-8")
print(json.dumps(summary))
