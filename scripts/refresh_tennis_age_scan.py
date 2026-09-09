#!/usr/bin/env python3
import json, re, datetime, os
from pathlib import Path
from urllib.parse import urljoin
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

ATP_PLAYERS="https://www.atptour.com/en/players"
WTA_PLAYERS="https://www.wtatennis.com/players"
ITF_PLAYERS="https://www.itftennis.com/en/players/"

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def norm(s):
    s=str(s or "")
    s=re.sub(r"(?<=[a-zà-öø-ÿ])(?=[A-ZÀ-ÖØ-Þ])", " ", s)
    s=s.lower()
    s=re.sub(r"[\u2018\u2019'`]", "",s)
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())

def age_from_dob(dob,on_date):
    return on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))

def date_value(raw):
    raw=" ".join(str(raw or "").split()).strip()
    if not raw:return None
    raw=raw.replace("T00:00:00","").replace("Z","")
    for fmt in (
        "%Y-%m-%d","%Y/%m/%d","%d/%m/%Y","%m/%d/%Y",
        "%d %B %Y","%d %b %Y","%B %d, %Y","%b %d, %Y"
    ):
        try:return datetime.datetime.strptime(raw,fmt).date()
        except Exception:pass
    return None

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
        dob=date_value(m.group(1))
        if dob:
            age=age_from_dob(dob,on_date)
            if 14<=age<=50:
                return age,dob.isoformat(),f"Official profile lists date of birth {dob.isoformat()}."
    return None,None,None

def extract_age_from_json(obj,on_date):
    """Recursively inspect official JSON/XHR for age or birth-date fields."""
    if isinstance(obj,dict):
        # Direct age keys.
        for k,v in obj.items():
            lk=str(k).lower().replace("_","").replace("-","")
            if lk in ("age","playerage","currentage"):
                try:
                    age=int(v)
                    if 14<=age<=50:
                        return age,None,f"Official profile data lists age {age}."
                except Exception:pass

        # DOB/birthdate keys.
        for k,v in obj.items():
            lk=str(k).lower().replace("_","").replace("-","")
            if lk in ("dateofbirth","birthdate","dob","birthday","birth"):
                dob=date_value(v)
                if dob:
                    age=age_from_dob(dob,on_date)
                    if 14<=age<=50:
                        return age,dob.isoformat(),f"Official profile data lists date of birth {dob.isoformat()}."

        for v in obj.values():
            found=extract_age_from_json(v,on_date)
            if found:return found

    elif isinstance(obj,list):
        for v in obj:
            found=extract_age_from_json(v,on_date)
            if found:return found
    return None

class Browser:
    def __init__(self,pw):
        self.browser=pw.chromium.launch(headless=True,args=["--disable-dev-shm-usage"])
        self.page=self.browser.new_page(
            viewport={"width":1440,"height":1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
        )
        self.page.set_default_timeout(10000)

    def close(self):self.browser.close()

    def snapshot(self,url,wait=700):
        payloads=[]
        def response_handler(resp):
            try:
                ct=(resp.headers.get("content-type") or "").lower()
                lu=resp.url.lower()
                if "json" not in ct and not any(x in lu for x in ("api","graphql","player","profile")):
                    return
                if len(payloads)<60:
                    payloads.append(resp.json())
            except Exception:
                pass
        try:
            self.page.on("response",response_handler)
            self.page.goto(url,wait_until="domcontentloaded",timeout=25000)
            self.page.wait_for_timeout(wait)
            try:
                text=self.page.locator("body").inner_text(timeout=6000)
            except Exception:
                text=""
            links=self.page.locator("a").evaluate_all(
                """els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))"""
            )
            html=self.page.content()
            return {"ok":True,"url":self.page.url,"text":text,"links":links,"html":html,"payloads":payloads}
        except Exception as e:
            return {"ok":False,"url":url,"text":"","links":[],"html":"","payloads":payloads,"error":str(e)[:160]}
        finally:
            try:self.page.remove_listener("response",response_handler)
            except Exception:pass

    def fill_search(self,url,name,link_pattern,preferred_domain):
        """Search an official player directory and return the closest official profile link."""
        try:
            self.page.goto(url,wait_until="domcontentloaded",timeout=25000)
            self.page.wait_for_timeout(900)

            # Try likely search inputs, then fall back to the first visible text/search input.
            candidates=[
                'input[placeholder*="Search all ATP players" i]',
                'input[placeholder*="Search Players" i]',
                'input[placeholder*="Search players" i]',
                'input[placeholder*="Search" i]',
                'input[type="search"]',
                'input[type="text"]'
            ]
            inp=None
            for sel in candidates:
                loc=self.page.locator(sel)
                try:
                    if loc.count() and loc.first.is_visible():
                        inp=loc.first
                        break
                except Exception:pass
            if inp is None:return None

            inp.fill(name)
            self.page.wait_for_timeout(1600)

            links=self.page.locator("a").evaluate_all(
                """els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))"""
            )
            target=norm(name)

            exact=[]
            fuzzy=[]
            for a in links:
                href=a.get("href") or ""
                text=a.get("text") or ""
                if not re.search(link_pattern,href,re.I):continue
                nt=norm(text)
                if nt==target:
                    exact.append(href)
                elif target and (target in nt or nt in target):
                    fuzzy.append(href)

            for href in exact+fuzzy:
                if preferred_domain in href.lower():
                    return href
            return (exact+fuzzy)[0] if exact or fuzzy else None
        except Exception:
            return None

    def search_profile(self,name,gender=None):
        # ATP first for men / unknown, WTA first for women, ITF as universal fallback.
        order=[]
        if gender=="WOMEN":
            order=[
              (WTA_PLAYERS,name,r"/players/\d+/", "wtatennis.com"),
              (ITF_PLAYERS,name,r"/en/players/", "itftennis.com")
            ]
        else:
            order=[
              (ATP_PLAYERS,name,r"/en/players/", "atptour.com"),
              (ITF_PLAYERS,name,r"/en/players/", "itftennis.com"),
              (WTA_PLAYERS,name,r"/players/\d+/", "wtatennis.com")
            ]
        for url,n,pat,domain in order:
            found=self.fill_search(url,n,pat,domain)
            if found:return found
        return None

def resolve_official_profile(browser,name,profile_url,on_date,gender=None):
    urls=[]
    if profile_url and any(d in profile_url.lower() for d in ("atptour.com","wtatennis.com","itftennis.com","utrsports.net")):
        urls.append(profile_url)

    # If tournament extraction did not give us a profile link, search official directories.
    if not urls:
        discovered=browser.search_profile(name,gender)
        if discovered:urls.append(discovered)

    # Even when a supplied profile URL failed, try official directory search as fallback.
    searched=False
    for url in list(urls):
        snap=browser.snapshot(url)
        if snap.get("ok"):
            found=parse_age_evidence(snap.get("text"),on_date)
            if found[0] is not None:
                return found[0],found[1],found[2],snap.get("url") or url

            for payload in snap.get("payloads") or []:
                j=extract_age_from_json(payload,on_date)
                if j:
                    return j[0],j[1],j[2],snap.get("url") or url

            # HTML/JSON hydration fallback.
            found=parse_age_evidence(snap.get("html"),on_date)
            if found[0] is not None:
                return found[0],found[1],found[2],snap.get("url") or url

        if not searched:
            searched=True
            discovered=browser.search_profile(name,gender)
            if discovered and discovered not in urls:
                snap=browser.snapshot(discovered)
                if snap.get("ok"):
                    found=parse_age_evidence(snap.get("text"),on_date)
                    if found[0] is not None:
                        return found[0],found[1],found[2],snap.get("url") or discovered
                    for payload in snap.get("payloads") or []:
                        j=extract_age_from_json(payload,on_date)
                        if j:
                            return j[0],j[1],j[2],snap.get("url") or discovered
                    found=parse_age_evidence(snap.get("html"),on_date)
                    if found[0] is not None:
                        return found[0],found[1],found[2],snap.get("url") or discovered

    # No usable supplied URL at all: search once.
    if not urls:
        discovered=browser.search_profile(name,gender)
        if discovered:
            snap=browser.snapshot(discovered)
            if snap.get("ok"):
                found=parse_age_evidence(snap.get("text"),on_date)
                if found[0] is not None:
                    return found[0],found[1],found[2],snap.get("url") or discovered
                for payload in snap.get("payloads") or []:
                    j=extract_age_from_json(payload,on_date)
                    if j:
                        return j[0],j[1],j[2],snap.get("url") or discovered
                found=parse_age_evidence(snap.get("html"),on_date)
                if found[0] is not None:
                    return found[0],found[1],found[2],snap.get("url") or discovered

    return None

intel=load(INTEL_PATH,{"tournaments":[]})
cache_doc=load(CACHE_PATH,{"schema_version":1,"records":{}})
cache=cache_doc.get("records") or {}

queue={}
for t in intel.get("tournaments",[]):
    event_date=t.get("start_date") or TODAY.isoformat()
    gender=t.get("gender")
    for p in t.get("participants",[]):
        if p.get("age_status")!="UNRESOLVED":continue
        name=p.get("name")
        if not name:continue
        key=norm(name)
        if cache.get(key,{}).get("age_status") in ("VERIFIED U18","VERIFIED 18+"):
            continue
        previous=cache.get(key,{})
        queue[key]={
          "name":name,
          "profile_url":p.get("profile_url") or p.get("source_url"),
          "event_date":event_date,
          "gender":gender,
          "tournament":t.get("tournament"),
          "tour":t.get("tour"),
          "attempt_count":int(previous.get("attempt_count",0) or 0),
          "last_attempt":previous.get("last_attempt")
        }

# Always work untouched candidates first, then older/lower-attempt candidates.
# This prevents repeat runs from researching the same first batch forever.
items=sorted(
    queue.values(),
    key=lambda x:(
        int(x.get("attempt_count",0)),
        0 if x.get("profile_url") else 1,
        str(x.get("last_attempt") or ""),
        norm(x.get("name"))
    )
)[:BATCH_SIZE]
resolved=0
not_found=0

with sync_playwright() as pw:
    browser=Browser(pw)
    for i,item in enumerate(items,1):
        try:on_date=datetime.date.fromisoformat(item["event_date"])
        except Exception:on_date=TODAY

        result=resolve_official_profile(
            browser,
            item["name"],
            item.get("profile_url"),
            on_date,
            item.get("gender")
        )

        key=norm(item["name"])
        if result:
            age,dob,evidence,source_url=result
            cache[key]={
              "name":item["name"],
              "age":age,
              "dob":dob,
              "age_status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
              "source":"Official player profile",
              "source_url":source_url,
              "evidence":evidence,
              "last_verified":NOW.isoformat(),
              "verification_method":"official_directory_profile_search",
              "attempt_count":int(cache.get(key,{}).get("attempt_count",0))+1
            }
            resolved+=1
        else:
            previous=cache.get(key,{})
            cache[key]={
              **previous,
              "name":item["name"],
              "age":None,
              "dob":None,
              "age_status":"UNRESOLVED",
              "last_attempt":NOW.isoformat(),
              "attempt_count":int(previous.get("attempt_count",0))+1,
              "last_tournament":item.get("tournament"),
              "last_tour":item.get("tour")
            }
            not_found+=1

        if i%10==0:
            print(f"Processed {i}/{len(items)}; resolved {resolved}; unresolved {not_found}")

    browser.close()

CACHE_PATH.write_text(json.dumps({
  "schema_version":2,
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
