#!/usr/bin/env python3
import json, re, datetime, hashlib, os
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TZ=ZoneInfo("America/Chicago")
NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=datetime.datetime.now(TZ).date()

INTEL_PATH=DATA/"tennis-intelligence.json"
CACHE_PATH=DATA/"tennis-age-cache.json"
BATCH_SIZE=int(os.environ.get("TENNIS_AGE_BATCH","120"))

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\u2018\u2019'`]", "",s)
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())

def age_from_dob(dob,on_date):
    return on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))

def parse_age_evidence(text,on_date):
    txt=" ".join(str(text or "").split())

    for pat in (
      r'\bAge\s*:?\s*(1[4-9]|[2-4]\d)\b',
      r'\bage\s+(1[4-9]|[2-4]\d)\s*(?:years?|yrs?)?\b'
    ):
        m=re.search(pat,txt,re.I)
        if m:
            age=int(m.group(1))
            return age,None,f"Official profile lists age {age}."

    patterns=[
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*(\d{4}-\d{2}-\d{2})'
    ]
    for pat in patterns:
        m=re.search(pat,txt,re.I)
        if not m:continue
        raw=m.group(1)
        for fmt in ('%d %B %Y','%d %b %Y','%B %d, %Y','%B %d %Y','%b %d, %Y','%Y-%m-%d'):
            try:
                dob=datetime.datetime.strptime(raw,fmt).date()
                age=age_from_dob(dob,on_date)
                if 14 <= age <= 45:
                    return age,dob.isoformat(),f"Official profile lists date of birth {dob.isoformat()}."
            except Exception:
                pass
    return None,None,None

class Browser:
    def __init__(self,pw):
        self.browser=pw.chromium.launch(headless=True,args=["--disable-dev-shm-usage"])
        self.page=self.browser.new_page(viewport={"width":1280,"height":900},
          user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36")
        self.page.set_default_timeout(12000)

    def close(self):self.browser.close()

    def text(self,url):
        try:
            self.page.goto(url,wait_until="domcontentloaded",timeout=25000)
            self.page.wait_for_timeout(500)
            return self.page.locator("body").inner_text(timeout=7000)
        except Exception:
            return None

intel=load(INTEL_PATH,{"tournaments":[]})
cache_doc=load(CACHE_PATH,{"schema_version":1,"records":{}})
cache=cache_doc.get("records") or {}

queue={}
for t in intel.get("tournaments",[]):
    event_date=t.get("start_date") or TODAY.isoformat()
    for p in t.get("participants",[]):
        if p.get("age_status")!="UNRESOLVED":
            continue
        name=p.get("name")
        if not name:
            continue
        key=norm(name)
        if cache.get(key,{}).get("age_status") in ("VERIFIED U18","VERIFIED 18+"):
            continue
        url=p.get("profile_url") or p.get("source_url")
        # Only spend browser time on a usable official profile URL.
        if not url or not any(domain in url.lower() for domain in ("itftennis.com","atptour.com","wtatennis.com","utrsports.net")):
            continue
        queue[key]={
          "name":name,"profile_url":url,"event_date":event_date,
          "tournament":t.get("tournament"),"tour":t.get("tour")
        }

items=list(queue.values())[:BATCH_SIZE]
resolved=0
not_found=0

with sync_playwright() as pw:
    browser=Browser(pw)
    for i,item in enumerate(items,1):
        url=item["profile_url"]
        text=browser.text(url)
        if not text:
            not_found+=1
            continue
        try:on_date=datetime.date.fromisoformat(item["event_date"])
        except Exception:on_date=TODAY
        age,dob,evidence=parse_age_evidence(text,on_date)
        if age is None:
            not_found+=1
            continue
        key=norm(item["name"])
        cache[key]={
          "name":item["name"],
          "age":age,
          "dob":dob,
          "age_status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
          "source":"Official player profile",
          "source_url":url,
          "evidence":evidence,
          "last_verified":NOW.isoformat(),
          "verification_method":"deep_official_profile"
        }
        resolved+=1
        if i%20==0:
            print(f"Processed {i}/{len(items)}; resolved {resolved}")
    browser.close()

CACHE_PATH.write_text(json.dumps({
  "schema_version":1,
  "generated_at":NOW.isoformat(),
  "batch_size":BATCH_SIZE,
  "processed":len(items),
  "resolved_this_run":resolved,
  "unresolved_this_run":not_found,
  "remaining_candidates":max(0,len(queue)-len(items)),
  "records":cache
},indent=2,ensure_ascii=False),encoding="utf-8")

print(json.dumps({
  "processed":len(items),
  "resolved":resolved,
  "not_resolved":not_found,
  "remaining_candidates":max(0,len(queue)-len(items)),
  "cache_records":len(cache)
}))
