#!/usr/bin/env python3
from pathlib import Path
import json, re, datetime, hashlib, difflib
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TZ=ZoneInfo("America/Chicago")
NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=datetime.datetime.now(TZ).date()
END=TODAY+datetime.timedelta(days=7)

ATP_CAL="https://www.atptour.com/en/tournaments/"
ATP_CHAL="https://www.atptour.com/en/atp-challenger-tour/calendar"
ATP_CHAL_ARCHIVE=f"https://www.atptour.com/en/scores/results-archive?tournamentType=ch&year={TODAY.year}"
ATP_RANK="https://www.atptour.com/en/rankings/singles?rankRange=1-1000"
WTA_CAL="https://www.wtatennis.com/tournaments"
WTA_125="https://www.wtatennis.com/tournaments/wta-125"
WTA_RANK="https://www.wtatennis.com/rankings/singles/"
ITF_MEN=f"https://www.itftennis.com/en/tournament-calendar/mens-world-tennis-tour-calendar/?categories=All&startdate={TODAY:%Y-%m}"
ITF_WOMEN=f"https://www.itftennis.com/en/tournament-calendar/womens-world-tennis-tour-calendar/?categories=All&startdate={TODAY:%Y-%m}"
ITF_JB="https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=B"
ITF_JG="https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=G"
UTR={
 "Americas":"https://app.utrsports.net/club/11313",
 "Europe":"https://app.utrsports.net/club/12083",
 "Asia & Pacific":"https://app.utrsports.net/club/12084?tab=info"
}

FAMILIES=[
 {"id":"atp","gender":"MEN","tour":"ATP Tour"},
 {"id":"atp-challenger","gender":"MEN","tour":"ATP Challenger Tour"},
 {"id":"itf-men","gender":"MEN","tour":"ITF Men's World Tennis Tour"},
 {"id":"utr-men","gender":"MEN","tour":"UTR Pro Tennis Tour"},
 {"id":"wta","gender":"WOMEN","tour":"WTA Tour"},
 {"id":"wta-125","gender":"WOMEN","tour":"WTA 125"},
 {"id":"itf-women","gender":"WOMEN","tour":"ITF Women's World Tennis Tour"},
 {"id":"utr-women","gender":"WOMEN","tour":"UTR Pro Tennis Tour"}
]

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

AGE_CACHE_PATH=DATA/"tennis-age-cache.json"

def load_age_cache():
    raw=load(AGE_CACHE_PATH,{"schema_version":1,"records":{}})
    records=raw.get("records") or {}
    # Normalize old/list forms defensively.
    if isinstance(records,list):
        records={norm(x.get("name")):x for x in records if x.get("name")}
    return records


def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\u2018\u2019'`]", "",s)
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())

def parse_date(s):
    s=" ".join(str(s or "").split())
    for f in ("%d %B %Y","%d %b %Y","%B %d, %Y","%b %d, %Y","%Y-%m-%d"):
        try:return datetime.datetime.strptime(s,f).date()
        except Exception:pass
    return None

def date_range(text):
    t=" ".join(str(text or "").split())
    pats=[
      r'(\d{1,2})\s+([A-Za-z]+)\s+(?:to|[-–])\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
      r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',
      r'([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})',
    ]
    for i,p in enumerate(pats):
        m=re.search(p,t,re.I)
        if not m:continue
        try:
            if i==0:
                d1,m1,d2,m2,y=m.groups()
                a=parse_date(f"{d1} {m1} {y}"); b=parse_date(f"{d2} {m2} {y}")
            elif i==1:
                d1,d2,m1,y=m.groups()
                a=parse_date(f"{d1} {m1} {y}"); b=parse_date(f"{d2} {m1} {y}")
            else:
                m1,d1,d2,y=m.groups()
                a=parse_date(f"{d1} {m1} {y}"); b=parse_date(f"{d2} {m1} {y}")
            if a and b:return a,b
        except Exception:pass
    return None,None

def overlaps(a,b): return bool(a and b and a<=END and b>=TODAY)

class Browser:
    def __init__(self,pw):
        self.browser=pw.chromium.launch(headless=True,args=["--disable-dev-shm-usage"])
        self.page=self.browser.new_page(viewport={"width":1440,"height":1100},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36")
        self.page.set_default_timeout(18000)

    def close(self): self.browser.close()

    def snapshot(self,url,wait=1800):
        payloads=[]
        def on_response(resp):
            try:
                ctype=(resp.headers.get("content-type") or "").lower()
                u=resp.url.lower()
                if ("json" not in ctype and not any(x in u for x in ("/api/","graphql","query","draw","player","acceptance"))):
                    return
                data=resp.json()
                # Keep payload collection bounded.
                if len(payloads)<80:
                    payloads.append({"url":resp.url,"data":data})
            except Exception:
                pass

        try:
            self.page.on("response",on_response)
            self.page.goto(url,wait_until="domcontentloaded",timeout=35000)
            self.page.wait_for_timeout(wait)
            # Give JS-heavy sports sites one extra opportunity to settle.
            try:self.page.wait_for_load_state("networkidle",timeout=5000)
            except Exception:pass
            text=self.page.locator("body").inner_text(timeout=8000)
            links=self.page.locator("a").evaluate_all(
                """els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||'',parent:(a.closest('tr,article,li,section,div')?.innerText||'').trim()}))"""
            )
            rows=self.page.locator("tr").evaluate_all(
                """els=>els.map(tr=>({cells:[...tr.querySelectorAll('th,td')].map(x=>(x.innerText||'').trim()),text:(tr.innerText||'').trim()}))"""
            )
            html=self.page.content()
            return {"ok":True,"url":self.page.url,"text":text,"links":links,"rows":rows,"html":html,"payloads":payloads}
        except Exception as e:
            return {"ok":False,"url":url,"text":"","links":[],"rows":[],"html":"","payloads":payloads,"error":str(e)[:180]}
        finally:
            try:self.page.remove_listener("response",on_response)
            except Exception:pass

def clean_tournament_name(text):
    s=" ".join(str(text or "").split())
    s=re.sub(r'\b(Date|Host Nation|City/Town|Category|Prize Money|Surface|Status)\s*:.*$','',s,flags=re.I)
    s=re.sub(r'\s+\([A-Z]{3}\)\s*$','',s)
    return s.strip(" -|")

def discover_generic(browser,url,tid,tour,gender,href_pattern):
    snap=browser.snapshot(url)
    out=[]
    if not snap["ok"]: return out,{"ok":False,"events":0,"url":url,"error":snap.get("error")}
    seen=set()
    for a in snap["links"]:
        href=a["href"]; parent=a["parent"] or a["text"]
        if not re.search(href_pattern,href,re.I):continue
        start,end=date_range(parent)
        if not overlaps(start,end):continue
        name=clean_tournament_name(a["text"])
        if not name or href in seen:continue
        seen.add(href)
        out.append({
          "id":hashlib.sha1(f"{tid}|{href}|{start}".encode()).hexdigest()[:12],
          "tour_id":tid,"tour":tour,"gender":gender,"tournament":name,
          "start_date":start.isoformat(),"end_date":end.isoformat(),
          "location":"","status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
          "source_url":href,"participants":[],"participant_source":"Official tour/tournament page"
        })
    return out,{"ok":True,"events":len(out),"url":url}

def calendar_overlap_mentions(text):
    """Count visible date ranges in the current Today+7 window."""
    count=0
    for m in re.finditer(r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',str(text or ''),re.I):
        d1,d2,mon,year=m.groups()
        a=parse_date(f"{d1} {mon} {year}")
        b=parse_date(f"{d2} {mon} {year}")
        if overlaps(a,b):count+=1
    return count

def _dict_first(d,keys):
    for k in keys:
        if k in d and d.get(k) not in (None,""):
            return d.get(k)
    # case-insensitive key fallback
    low={str(k).lower():k for k in d.keys()}
    for k in keys:
        real=low.get(str(k).lower())
        if real is not None and d.get(real) not in (None,""):
            return d.get(real)
    return None

def parse_json_date(v):
    if not v:return None
    s=str(v).strip()
    # ISO timestamps / dates
    m=re.match(r'^(\d{4}-\d{2}-\d{2})',s)
    if m:return parse_date(m.group(1))
    # common web date strings
    for piece in (s, s[:20]):
        d=parse_date(piece)
        if d:return d
    return None

def walk_json_dicts(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():
            yield from walk_json_dicts(v)
    elif isinstance(obj,list):
        for v in obj:
            yield from walk_json_dicts(v)

def discover_wta_from_payloads(browser):
    """Discover WTA/WTA125 tournaments from official calendar network/embedded data."""
    snap=browser.snapshot(WTA_CAL,3500)
    out=[]; seen=set()
    health={"ok":snap.get("ok",False),"events":0,"url":WTA_CAL,"payload_candidates":0,
            "error":snap.get("error")}
    if not snap.get("ok"):
        return out,health

    dicts=[]
    for p in snap.get("payloads",[]):
        dicts.extend(list(walk_json_dicts(p.get("data"))))

    # Also inspect JSON-looking scripts embedded in HTML.
    html=snap.get("html") or ""
    for m in re.finditer(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',html,re.I|re.S):
        try:
            data=json.loads(m.group(1))
            dicts.extend(list(walk_json_dicts(data)))
        except Exception:
            pass

    health["payload_candidates"]=len(dicts)

    for d in dicts:
        name=_dict_first(d,(
          "tournamentName","name","title","displayName","eventName","sponsorTitle"
        ))
        start=parse_json_date(_dict_first(d,(
          "startDate","start_date","dateFrom","fromDate","start","eventStartDate"
        )))
        end=parse_json_date(_dict_first(d,(
          "endDate","end_date","dateTo","toDate","end","eventEndDate"
        )))
        if not (name and start):
            continue
        if not end:end=start
        if not overlaps(start,end):
            continue

        tid=_dict_first(d,("tournamentId","tournamentID","id","eventId"))
        slug=_dict_first(d,("slug","urlSlug","seoSlug"))
        url=_dict_first(d,("url","href","path","tournamentUrl"))
        if isinstance(url,str) and url.startswith("/"):
            url=urljoin("https://www.wtatennis.com",url)
        if not url and tid and slug:
            url=f"https://www.wtatennis.com/tournaments/{tid}/{slug}/{TODAY.year}"
        if not url or "wtatennis.com" not in str(url):
            continue

        key=str(url)
        if key in seen:continue
        seen.add(key)

        level=str(_dict_first(d,("level","tournamentLevel","category","tier","levelName")) or "")
        is125=bool(re.search(r'\b125\b',level,re.I))
        tour_id="wta-125" if is125 else "wta"
        tour="WTA 125" if is125 else "WTA Tour"
        location=str(_dict_first(d,("location","city","venueCity","hostCity")) or "")
        out.append({
          "id":hashlib.sha1(f"{tour_id}|{url}|{start}".encode()).hexdigest()[:12],
          "tour_id":tour_id,"tour":tour,"gender":"WOMEN",
          "tournament":" ".join(str(name).split()),
          "start_date":start.isoformat(),"end_date":end.isoformat(),
          "location":location,"category":level,
          "status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
          "source_url":str(url),"participants":[],
          "participant_source":"WTA official calendar/tournament data"
        })

    health["events"]=len(out)
    return out,health

def discover_wta_from_visible_links(browser):
    """Fallback: official tournament links, verified by visiting each candidate page."""
    snap=browser.snapshot(WTA_CAL,3000)
    if not snap.get("ok"):
        return [],{"ok":False,"events":0,"url":WTA_CAL,"error":snap.get("error")}
    candidates=[];seen=set()
    for a in snap.get("links",[]):
        href=str(a.get("href") or "")
        if not re.search(r'/tournaments/\d+/[^/]+/2026(?:/|$)',href,re.I):continue
        if href in seen:continue
        seen.add(href);candidates.append(href)

    # Bound the fallback. Prefer links with September context in parent.
    priority=[]
    normal=[]
    for a in snap.get("links",[]):
        href=str(a.get("href") or "")
        if href not in seen:continue
        parent=str(a.get("parent") or "")
        (priority if re.search(r'Sep|September|2026',parent,re.I) else normal).append(href)
    ordered=[]
    for href in priority+candidates+normal:
        if href not in ordered:ordered.append(href)

    out=[]
    for href in ordered[:80]:
        page=browser.snapshot(href,500)
        if not page.get("ok"):continue
        text=" ".join(str(page.get("text") or "").split())
        m=re.search(r'(?:Duration\s*)?([A-Za-z]+\s+\d{1,2})\s*[-–]\s*([A-Za-z]+\s+\d{1,2}),?\s*(\d{4})',text,re.I)
        if not m:
            m2=re.search(r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',text,re.I)
            if m2:
                d1,d2,mon,yr=m2.groups()
                start=parse_date(f"{d1} {mon} {yr}");end=parse_date(f"{d2} {mon} {yr}")
            else:
                continue
        else:
            a,b,yr=m.groups()
            start=parse_date(f"{a} {yr}");end=parse_date(f"{b} {yr}")
        if not overlaps(start,end):continue

        title=""
        tm=re.search(r'#\s*(.+)',str(page.get("text") or ""))
        if tm:title=" ".join(tm.group(1).split())
        if not title:
            title=clean_tournament_name(next((x.get("text") for x in page.get("links",[]) if x.get("href")==href),"WTA Tournament"))

        is125=bool(re.search(r'\bWTA\s*125\b',text,re.I))
        tid="wta-125" if is125 else "wta"
        tour="WTA 125" if is125 else "WTA Tour"
        out.append({
          "id":hashlib.sha1(f"{tid}|{href}|{start}".encode()).hexdigest()[:12],
          "tour_id":tid,"tour":tour,"gender":"WOMEN",
          "tournament":title,"start_date":start.isoformat(),"end_date":end.isoformat(),
          "location":"","status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
          "source_url":href,"participants":[],
          "participant_source":"WTA official tournament page"
        })
    return out,{"ok":True,"events":len(out),"url":WTA_CAL,"candidate_links":len(candidates)}

def discover_atp_challenger(browser):
    """ATP Challenger discovery from official results archive, with calendar fallback."""
    sources=[ATP_CHAL_ARCHIVE,ATP_CHAL]
    out=[];seen=set();overlap_mentions=0;source_health=[]

    for source in sources:
        snap=browser.snapshot(source,3000)
        source_health.append({"url":source,"ok":snap.get("ok",False),"error":snap.get("error")})
        if not snap.get("ok"):continue
        text=snap.get("text") or ""
        overlap_mentions+=calendar_overlap_mentions(text)

        # 1) Use official tournament links and their surrounding card text.
        for a in snap.get("links",[]):
            href=str(a.get("href") or "")
            if "/en/tournaments/" not in href:continue
            parent=str(a.get("parent") or a.get("text") or "")
            st,en=date_range(parent)
            if not overlaps(st,en):continue
            name=clean_tournament_name(a.get("text"))
            if not name or href in seen:continue
            seen.add(href)
            lm=re.search(r'Challenger\s+(\d+)',parent,re.I)
            out.append({
              "id":hashlib.sha1(f"atp-challenger|{href}|{st}".encode()).hexdigest()[:12],
              "tour_id":"atp-challenger","tour":"ATP Challenger Tour","gender":"MEN",
              "tournament":name,"start_date":st.isoformat(),"end_date":en.isoformat(),
              "location":"","category":f"Challenger {lm.group(1)}" if lm else "",
              "status":"ACTIVE" if st<=TODAY<=en else "UPCOMING",
              "source_url":href,"participants":[],
              "participant_source":"ATP Challenger official archive/calendar"
            })

        # 2) Archive text fallback: match each current date-range line to a nearby
        # tournament link by visible tournament text.
        lines=[" ".join(x.split()) for x in str(text).splitlines() if x.strip()]
        current_lines=[]
        for line in lines:
            st,en=date_range(line)
            if overlaps(st,en):
                current_lines.append((line,st,en))

        links=snap.get("links",[])
        for line,st,en in current_lines:
            for a in links:
                href=str(a.get("href") or "")
                if "/en/tournaments/" not in href:continue
                atxt=" ".join(str(a.get("text") or "").split())
                if not atxt or len(atxt)<3:continue
                if norm(atxt) not in norm(line):continue
                if href in seen:continue
                seen.add(href)
                out.append({
                  "id":hashlib.sha1(f"atp-challenger|{href}|{st}".encode()).hexdigest()[:12],
                  "tour_id":"atp-challenger","tour":"ATP Challenger Tour","gender":"MEN",
                  "tournament":atxt,"start_date":st.isoformat(),"end_date":en.isoformat(),
                  "location":"","category":"",
                  "status":"ACTIVE" if st<=TODAY<=en else "UPCOMING",
                  "source_url":href,"participants":[],
                  "participant_source":"ATP Challenger official results archive"
                })

        if out:break

    health={"ok":any(x["ok"] for x in source_health),"events":len(out),
            "url":ATP_CHAL_ARCHIVE,"calendar_overlap_mentions":overlap_mentions,
            "sources":source_health}
    return out,health

def classify_wta_tournament(browser,t):
    """Classify a WTA tournament from the official tournament page."""
    snap=browser.snapshot(t.get("source_url"),700)
    if not snap.get("ok"):
        return
    txt=str(snap.get("text") or "")
    if re.search(r'\bWTA\s*125\b',txt,re.I):
        t["tour_id"]="wta-125";t["tour"]="WTA 125"
    else:
        t["tour_id"]="wta";t["tour"]="WTA Tour"

    # Record expected singles draw size where the official page exposes it.
    m=re.search(r'Singles Draw\s*(\d+)',txt,re.I)
    if m:
        t["official_singles_draw_size"]=int(m.group(1))
    dm=re.search(r'Doubles Draw\s*(\d+)',txt,re.I)
    if dm:
        t["official_doubles_draw_size"]=int(dm.group(1))

def parse_itf_fact_sheet(browser,t):
    """Read official draw sizes and key dates from the ITF fact sheet."""
    snap=browser.snapshot(t.get("source_url"),650)
    info={}
    if not snap.get("ok"):
        return info
    txt=" ".join(str(snap.get("text") or "").split())
    for key,label in (
        ("qualifying_draw_size","Singles qualifying"),
        ("main_draw_size","Singles main draw"),
        ("doubles_draw_size","Doubles main draw"),
    ):
        m=re.search(re.escape(label)+r'\s*:\s*(\d+)',txt,re.I)
        if m:info[key]=int(m.group(1))
    m=re.search(r'First day of Singles Main Draw\s*:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',txt,re.I)
    if m:
        d=parse_date(m.group(1))
        if d:info["first_main_draw_date"]=d.isoformat()
    return info

def discover_itf(browser,url,tid,tour,gender):
    snap=browser.snapshot(url,2200)
    out=[]
    if not snap["ok"]:return out,{"ok":False,"events":0,"url":url,"error":snap.get("error")}
    seen=set()
    for a in snap["links"]:
        if "/en/tournament/" not in a["href"]:continue
        parent=a["parent"] or a["text"]
        start,end=date_range(parent.replace("Date:",""))
        if not overlaps(start,end):continue
        href=a["href"]; name=clean_tournament_name(a["text"])
        if not name or href in seen:continue
        seen.add(href)
        fact=re.sub(r'/(acceptance-list|draws-and-results|order-of-play|overview)/?$','/fact-sheet/',href)
        if "/fact-sheet/" not in fact:fact=fact.rstrip("/")+"/fact-sheet/"
        cat=""
        cm=re.search(r'Category:\s*([MW]\d+)',parent,re.I)
        if cm:cat=cm.group(1).upper()
        city=""
        lm=re.search(r'City/Town:\s*(.+?)(?:Category:|Prize|Surface|Status:|$)',parent,re.I)
        if lm:city=" ".join(lm.group(1).split())
        out.append({
          "id":hashlib.sha1(f"{tid}|{fact}|{start}".encode()).hexdigest()[:12],
          "tour_id":tid,"tour":tour,"gender":gender,"tournament":name,"category":cat,
          "start_date":start.isoformat(),"end_date":end.isoformat(),"location":city,
          "status":"ACTIVE" if start<=TODAY<=end else "UPCOMING","source_url":fact,
          "acceptance_url":fact.replace("/fact-sheet/","/acceptance-list/"),
          "draw_url":fact.replace("/fact-sheet/","/draws-and-results/"),
          "order_url":fact.replace("/fact-sheet/","/order-of-play/"),
          "participants":[],"participant_source":"ITF acceptance list / draw / order of play"
        })
    return out,{"ok":True,"events":len(out),"url":url}

def fallback_global_schedule():
    x=load(DATA/"global-schedule.json",{})
    out=[]
    for e in x.get("events",[]):
        if e.get("sport")!="Tennis" or e.get("status")=="COMPLETED":continue
        try:d=datetime.datetime.fromisoformat(e["start_time"].replace("Z","+00:00")).astimezone(TZ).date()
        except Exception:continue
        if not (TODAY<=d<=END):continue
        league=str(e.get("league") or "").upper()
        if league not in ("ATP","WTA"):continue
        out.append({
          "id":f"fallback-{e['id']}-{league.lower()}","tour_id":league.lower(),
          "tour":"ATP Tour" if league=="ATP" else "WTA Tour",
          "gender":"MEN" if league=="ATP" else "WOMEN",
          "tournament":e.get("name") or league,"start_date":d.isoformat(),"end_date":d.isoformat(),
          "location":e.get("location") or "","status":"UPCOMING","source_url":e.get("source_endpoint"),
          "participants":[],"participant_source":"Mapped public schedule fallback; official tour page not resolved",
          "discovery_fallback":True
        })
    return out

def clean_player_name(name):
    name=" ".join(str(name or "").split()).strip(" -|,")
    name=re.sub(r"^[A-Z]{3}\s*", "", name).strip()
    return name

def plausible_player(name):
    name=clean_player_name(name)
    if len(name)<4 or len(name)>80 or len(name.split())<2:
        return False
    bad=(
      "player list","tournament","acceptance list","draws","results","order of play",
      "official website","singles","doubles","qualifying","withdrawal","alternate",
      "seed #","prize","ranking","currently playing","eliminated"
    )
    return not any(x in name.lower() for x in bad)

def add_person(found,name,url=None,source=None):
    name=clean_player_name(name)
    if not plausible_player(name):return
    # Doubles listings sometimes contain surname-only pairs. Do not invent full
    # identities from those; singles/qualifying pages provide full names.
    if " & " in name or "&" in name:return
    k=norm(name)
    rec=found.get(k,{"name":name})
    if url and not rec.get("profile_url"):rec["profile_url"]=url
    if source:rec["participant_evidence"]=source
    found[k]=rec

def wta_player_list_url(url):
    m=re.search(r'https?://(?:www\.)?wtatennis\.com/tournaments/(\d+)/([^/]+)/(\d{4})',str(url or ''),re.I)
    if not m:return str(url or '').rstrip("/")+"/player-list"
    return f"https://www.wtatennis.com/tournaments/{m.group(1)}/{m.group(2)}/{m.group(3)}/player-list"

def wta_draw_url(url):
    m=re.search(r'https?://(?:www\.)?wtatennis\.com/tournaments/(\d+)/([^/]+)/(\d{4})',str(url or ''),re.I)
    if not m:return None
    return f"https://www.wtatennis.com/tournament/{m.group(1)}/{m.group(2)}/{m.group(3)}/draws"

def atp_draw_urls(url):
    u=str(url or '').rstrip("/")
    if u.endswith("/overview"):
        root=u[:-len("/overview")]
    else:
        root=u
    return [root+"/draws",root+"/results",u]

def split_camel_name(name):
    """ITF draw text sometimes renders NinoEhrenschneider without a space."""
    s=clean_player_name(name)
    s=re.sub(r"(?<=[a-zà-öø-ÿ])(?=[A-ZÀ-ÖØ-Þ])"," ",s)
    return " ".join(s.split())

def extract_itf_draw_text(found,snap):
    lines=[" ".join(x.split()) for x in str(snap.get("text") or "").splitlines() if x.strip()]
    for i,line in enumerate(lines):
        if not re.match(r"^Entry status\s*:",line,re.I):
            continue
        for cand in lines[i+1:i+8]:
            x=cand.strip()
            if re.fullmatch(r"[A-Z]{3}",x):continue
            if x.upper()=="H2H":continue
            if re.fullmatch(r"(?:\d+\s*){1,6}",x):continue
            if re.match(r"^(?:Entry status|Print|Main Draw|Qualifying|Singles|Doubles)",x,re.I):break
            x=re.sub(r"\s*\[[0-9]+\]\s*$","",x)
            x=re.sub(r"\s*\((?:WC|Q|LL|JR|DA|SE|ALT)\)\s*$","",x,flags=re.I)
            x=split_camel_name(x)
            if plausible_player(x):
                add_person(found,x,source="ITF official draw text")
                break

def extract_json_people(found,payloads,source):
    """Recursively find player-shaped objects in rendered XHR/JSON responses."""
    first_keys=("firstName","firstname","first_name","givenName","given_name","forename")
    last_keys=("lastName","lastname","last_name","familyName","family_name","surname")
    full_keys=("fullName","displayName","playerName","name")

    def walk(obj,depth=0):
        if depth>12:return
        if isinstance(obj,dict):
            first=next((obj.get(k) for k in first_keys if isinstance(obj.get(k),str)),None)
            last=next((obj.get(k) for k in last_keys if isinstance(obj.get(k),str)),None)
            profile=None
            for k in ("profileUrl","profileURL","url","href","playerUrl"):
                if isinstance(obj.get(k),str) and ("player" in obj[k].lower() or "profile" in obj[k].lower()):
                    profile=obj[k];break
            if first and last:
                add_person(found,f"{first} {last}",profile,source)
            else:
                # Only accept a generic `name` from objects that look player-ish.
                playerish=any(k.lower().startswith(("player","athlete","competitor","participant","entrant")) for k in obj.keys())
                if playerish:
                    for k in full_keys:
                        val=obj.get(k)
                        if isinstance(val,str) and plausible_player(val):
                            add_person(found,val,profile,source)
                            break
            for v in obj.values():walk(v,depth+1)
        elif isinstance(obj,list):
            for v in obj:walk(v,depth+1)

    for item in payloads or []:
        try:walk(item.get("data"))
        except Exception:pass

def extract_wta_text(found,snap):
    """WTA player-list pages expose full singles/qualifying names in rendered text."""
    lines=[" ".join(x.split()) for x in str(snap.get("text") or "").splitlines() if x.strip()]
    status_words={"playing","eliminated","upcoming","finished","suspended"}
    meta_words={"filter","all players","currently playing","player list coming soon. please check back for updates."}
    for i,line in enumerate(lines):
        if line.lower() not in status_words:continue
        # The next meaningful line is normally the player's displayed name.
        for nxt in lines[i+1:i+5]:
            low=nxt.lower()
            if low in status_words or low in meta_words:continue
            if re.fullmatch(r"[A-Z]{3}",nxt):continue
            if re.match(r"^(Seed #|Wild Card|Qualifier|Lucky Loser)",nxt,re.I):continue
            if "&" not in nxt:
                add_person(found,nxt,source="WTA official player list")
            break

def extract_itf_table_text(found,snap):
    """Extract names from ITF table Player cells even when player anchors are absent."""
    for row in snap.get("rows",[]):
        cells=row.get("cells") or []
        if len(cells)<2:continue
        txt=" ".join(cells)
        # Exclude players explicitly shown as withdrawn.
        if re.search(r"\bwithdraw(al|n)?\b|Automatic Withdrawal|\bAW[A-Z]{0,3}\b",txt,re.I):
            continue
        player_cell=cells[1]
        # ITF rendered text can concatenate country code + player + next country code.
        # Insert separators where a player surname runs into the next 3-letter code.
        x=re.sub(r"([a-zà-öø-ÿ])([A-Z]{3})(?=[A-ZÀ-ÖØ-Þ])",r"\1|\2",player_cell)
        chunks=x.split("|")
        for chunk in chunks:
            m=re.match(r"^\s*[A-Z]{3}\s*(.+?)\s*$",chunk)
            if m:
                name=split_camel_name(m.group(1).strip())
                # Remove trailing ranking columns accidentally included in a cell.
                name=re.sub(r"\s+\d+(?:\s+\d+)*\s*$","",name).strip()
                add_person(found,name,source="ITF official participant table")

def extract_embedded_names(found,html,source):
    """Fallback for JS apps such as UTR where names may live in hydrated JSON."""
    text=str(html or "")
    for m in re.finditer(r'"firstName"\s*:\s*"([^"]{2,40})".{0,240}?"lastName"\s*:\s*"([^"]{2,50})"',text,re.I|re.S):
        add_person(found,f"{m.group(1)} {m.group(2)}",source=source)
    for m in re.finditer(r'"(?:displayName|fullName|playerName)"\s*:\s*"([^"]{4,80})"',text,re.I):
        add_person(found,m.group(1),source=source)

def participant_links(browser,t):
    tid=t["tour_id"]

    def take_visible_players(snap, found, source, include_itf_draw_text=False):
        for a in snap.get("links",[]):
            href=a.get("href","")
            if (
                (tid.startswith("itf-") and re.search(r"/en/players/",href,re.I))
                or (tid.startswith("wta") and re.search(r"/players/",href,re.I))
                or (tid.startswith("atp") and re.search(r"/en/players/",href,re.I))
                or (tid.startswith("utr") and re.search(r"/(profile|profiles|player|players)/",href,re.I))
            ):
                add_person(found,a.get("text"),href,source)

        if tid.startswith("itf-"):
            extract_itf_table_text(found,snap)
            if include_itf_draw_text:
                extract_itf_draw_text(found,snap)
        elif tid.startswith("wta"):
            extract_wta_text(found,snap)

        extract_embedded_names(found,snap.get("html"),source)

    # -----------------------------------------
    # ITF: active draw is separate from acceptance pool.
    # -----------------------------------------
    if tid.startswith("itf-"):
        fact=parse_itf_fact_sheet(browser,t)
        t.update(fact)

        draw_found={}
        draw_url=t.get("draw_url")
        if draw_url:
            snap=browser.snapshot(draw_url,2800)
            if snap.get("ok"):
                take_visible_players(
                    snap,draw_found,
                    "ITF official draw",
                    include_itf_draw_text=True
                )

        if t.get("order_url"):
            snap=browser.snapshot(t.get("order_url"),1800)
            if snap.get("ok"):
                take_visible_players(
                    snap,draw_found,
                    "ITF draw / order of play",
                    include_itf_draw_text=True
                )

        expected=int(t.get("main_draw_size") or 0)
        if expected:
            ratio=len(draw_found)/expected
            if 0.75<=ratio<=3.0:
                t["participant_field_basis"]="ITF active draw / order of play"
                t["participant_field_type"]="DRAW"
                t["participant_field_confidence"]="HIGH"
                t["participant_field_expected_min"]=expected
                return list(draw_found.values())
            if 8<=len(draw_found)<expected*3:
                t["participant_field_basis"]="ITF partial draw / order of play"
                t["participant_field_type"]="DRAW"
                t["participant_field_confidence"]="MEDIUM"
                t["participant_field_expected_min"]=expected
                return list(draw_found.values())
        else:
            if 16<=len(draw_found)<=128:
                t["participant_field_basis"]="ITF active draw / order of play"
                t["participant_field_type"]="DRAW"
                t["participant_field_confidence"]="HIGH"
                t["participant_field_expected_min"]=16
                return list(draw_found.values())
            if 8<=len(draw_found)<16:
                t["participant_field_basis"]="ITF partial draw / order of play"
                t["participant_field_type"]="DRAW"
                t["participant_field_confidence"]="MEDIUM"
                t["participant_field_expected_min"]=16
                return list(draw_found.values())

        # Acceptance pool is WATCH INTELLIGENCE ONLY.
        # Do not return hundreds of pool names as tournament participants.
        acceptance_found={}
        url=t.get("acceptance_url")
        if url:
            snap=browser.snapshot(url,2200)
            if snap.get("ok"):
                for a in snap.get("links",[]):
                    parent=a.get("parent","")
                    if (
                        re.search(r"/en/players/",a.get("href",""),re.I)
                        and not re.search(r"withdraw|Automatic Withdrawal",parent,re.I)
                    ):
                        add_person(acceptance_found,a.get("text"),a.get("href"),"ITF acceptance list")
                extract_itf_table_text(acceptance_found,snap)

        t["acceptance_pool_people"]=list(acceptance_found.values())
        t["acceptance_pool_screened_count"]=len(acceptance_found)
        t["participant_field_basis"]="ITF acceptance list watch only; active draw not captured"
        t["participant_field_type"]="INCOMPLETE"
        t["participant_field_confidence"]="LOW"
        t["participant_field_expected_min"]=expected or None
        return []

    # -----------------------------------------
    # WTA: visible player list / draw first.
    # -----------------------------------------
    if tid.startswith("wta"):
        classify_wta_tournament(browser,t)
        tid=t["tour_id"]
        found={}
        urls=[
            wta_player_list_url(t.get("source_url")),
            wta_draw_url(t.get("source_url")),
            t.get("source_url")
        ]
        for url in urls:
            if not url:continue
            snap=browser.snapshot(url,2400)
            if not snap.get("ok"):continue
            take_visible_players(snap,found,"WTA official player list / draw")
            if len(found)>=16:
                break

        # JSON is fallback only when visible pages produced almost nothing.
        if len(found)<4:
            for url in urls:
                if not url:continue
                snap=browser.snapshot(url,1800)
                if snap.get("ok"):
                    extract_json_people(found,snap.get("payloads"),"WTA rendered tournament data")
                if len(found)>=16:
                    break

        expected=int(t.get("official_singles_draw_size") or 16)
        t["participant_field_basis"]="WTA official player list / draw"
        t["participant_field_type"]="PLAYER_LIST"
        t["participant_field_expected_min"]=expected
        if expected and expected*0.75 <= len(found) <= max(expected*3,128):
            t["participant_field_confidence"]="HIGH"
        elif 8 <= len(found) <= max(expected*3,128):
            t["participant_field_confidence"]="MEDIUM"
        else:
            t["participant_field_confidence"]="LOW"
        return list(found.values())

    # -----------------------------------------
    # ATP / Challenger: draw/results visible first.
    # -----------------------------------------
    if tid.startswith("atp"):
        found={}
        urls=atp_draw_urls(t.get("source_url"))
        for url in urls:
            snap=browser.snapshot(url,2400)
            if not snap.get("ok"):continue
            take_visible_players(snap,found,"ATP official draw / results")
            if len(found)>=16:
                break

        if len(found)<4:
            for url in urls:
                snap=browser.snapshot(url,1800)
                if snap.get("ok"):
                    extract_json_people(found,snap.get("payloads"),"ATP rendered tournament data")
                if len(found)>=16:
                    break

        expected=32 if t.get("tour_id")=="atp-challenger" else 16
        t["participant_field_basis"]="ATP official draw / results"
        t["participant_field_type"]="DRAW"
        t["participant_field_expected_min"]=expected
        if expected*0.75 <= len(found) <= max(expected*3,128):
            t["participant_field_confidence"]="HIGH"
        elif 8 <= len(found) <= max(expected*3,128):
            t["participant_field_confidence"]="MEDIUM"
        else:
            t["participant_field_confidence"]="LOW"
        return list(found.values())

    # -----------------------------------------
    # UTR: event participant data.
    # -----------------------------------------
    found={}
    url=t.get("source_url")
    if url:
        snap=browser.snapshot(url,2400)
        if snap.get("ok"):
            take_visible_players(snap,found,"UTR official event participant data")
            if len(found)<4:
                extract_json_people(found,snap.get("payloads"),"UTR rendered event data")

    t["participant_field_basis"]="UTR event participant data"
    t["participant_field_type"]="PLAYER_LIST"
    t["participant_field_expected_min"]=8
    t["participant_field_confidence"]="HIGH" if 8<=len(found)<=128 else ("MEDIUM" if 4<=len(found)<8 else "LOW")
    return list(found.values())

PROFILE_AGE_CACHE={}

def age_from_dob(dob,on_date):
    return on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))

def parse_age_evidence(text,on_date):
    txt=" ".join(str(text or "").split())

    # Explicit age labels.
    for pat in (
      r'\bAge\s*:?\s*(1[4-9]|[2-4]\d)\b',
      r'\bage\s+(1[4-9]|[2-4]\d)\s*(?:years?|yrs?)?\b'
    ):
        m=re.search(pat,txt,re.I)
        if m:
            age=int(m.group(1))
            return age,None,f"Official profile lists age {age}."

    # Explicit DOB fields only. Bare dates elsewhere on the page are ignored.
    dob_patterns=[
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
      r'(?:Date of Birth|Date of birth|DOB|Born|Birthday)\s*:?\s*(\d{4}-\d{2}-\d{2})'
    ]
    for pat in dob_patterns:
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

def resolve_profile_age(browser,person,on_date):
    url=person.get('profile_url')
    if not url:
        return None
    if url in PROFILE_AGE_CACHE:
        return PROFILE_AGE_CACHE[url]

    # Full browser rendering is used because official tennis profiles may be JS-rendered.
    snap=browser.snapshot(url,350)
    if not snap.get('ok'):
        PROFILE_AGE_CACHE[url]=None
        return None
    age,dob,evidence=parse_age_evidence(snap.get('text',''),on_date)
    if age is None:
        PROFILE_AGE_CACHE[url]=None
        return None
    result={
      'name':person.get('name'),
      'age':age,
      'dob':dob,
      'age_status':'VERIFIED U18' if age<18 else 'VERIFIED 18+',
      'source':'Official player profile',
      'source_url':url,
      'evidence':evidence
    }
    PROFILE_AGE_CACHE[url]=result
    return result

def ranking_age_index(browser,url,profile_pattern,source):
    """Build a broad official ranking-age index before individual profile lookups."""
    out={}; snap=browser.snapshot(url,2200)
    health={'ok':snap.get('ok',False),'records':0,'url':url,'error':snap.get('error')}
    if not snap.get('ok'):
        return out,health
    for a in snap.get('links',[]):
        if not re.search(profile_pattern,a.get('href',''),re.I):continue
        name=clean_player_name(a.get('text'))
        if not plausible_player(name):continue
        row=" ".join(str(a.get('parent') or '').split())

        age=None
        explicit=re.search(r'\bAge\s*:?\s*(1[4-9]|[2-4]\d)\b',row,re.I)
        if explicit:
            age=int(explicit.group(1))
        else:
            # Ranking tables often display age as a standalone 2-digit column.
            # Keep this conservative: only 16-40 and prefer a value near the player name.
            values=[int(x) for x in re.findall(r'(?<!\d)(1[6-9]|[2-3]\d|40)(?!\d)',row)]
            if values:
                age=values[0]

        if age is None:continue
        out[norm(name)]={
          'name':name,'age':age,'dob':None,
          'age_status':'VERIFIED U18' if age<18 else 'VERIFIED 18+',
          'source':source,'source_url':a.get('href'),
          'evidence':f'{source} lists age {age}.'
        }
    health['records']=len(out)
    return out,health

def junior_watch_index(browser):
    """Build two junior layers:
    - verified U18: safe to create RED when linked to a professional tournament
    - targeted candidates: plausibly U18 and worth a narrow profile check
    """
    verified={}
    candidates={}
    health=[]
    for gender,url in [("MEN",ITF_JB),("WOMEN",ITF_JG)]:
        snap=browser.snapshot(url,2000)
        vc=0; cc=0
        if snap["ok"]:
            for a in snap["links"]:
                if "/en/players/" not in a["href"]:continue
                row=a["parent"] or ""
                m=re.search(r'\b(2008|2009|2010|2011|2012)\b',row)
                name=" ".join(a["text"].split())
                if not m or len(name.split())<2:continue
                yob=int(m.group(1))
                rec={
                  "name":name,"gender":gender,"birth_year":yob,
                  "source":"ITF official junior rankings","source_url":a["href"]
                }
                # In 2026, 2009+ birth years are unambiguously under 18.
                if yob>=2009:
                    rec.update({
                      "age":YEAR-yob,
                      "age_status":"VERIFIED U18",
                      "evidence":f"Official ITF junior ranking lists birth year {yob}."
                    })
                    verified[norm(name)]=rec;vc+=1
                else:
                    # 2008 may be age 17 or 18 depending birthday: targeted review only.
                    rec.update({
                      "age":None,
                      "age_status":"TARGETED REVIEW",
                      "candidate_reason":f"ITF junior ranking lists birth year {yob}; exact DOB needed.",
                      "evidence":f"Official ITF junior ranking lists birth year {yob}."
                    })
                    candidates[norm(name)]=rec;cc+=1
        health.append({"ok":snap["ok"],"gender":gender,"verified_u18":vc,
                       "targeted_candidates":cc,"url":url,"error":snap.get("error")})
    return verified,candidates,health

def fuzzy_watch_match(name,watch):
    """Conservative fuzzy match used only to create AMBER targeted review, never RED."""
    key=norm(name)
    toks=key.split()
    if len(toks)<2:return None
    first=toks[0]; last=toks[-1]
    scored=[]
    for wk,rec in watch.items():
        wt=wk.split()
        if len(wt)<2:continue
        # Require same surname and same first initial before similarity is considered.
        if wt[-1]!=last or wt[0][:1]!=first[:1]:continue
        score=difflib.SequenceMatcher(None,key,wk).ratio()
        if score>=0.90:
            scored.append((score,rec))
    if len(scored)==1:
        return scored[0][1]
    return None

YEAR=TODAY.year
seed=load(DATA/"tennis-known-u18.json",{}).get("records",[])
seed_index={}
for x in seed:
    if x.get("name"):
        seed_index[norm(x["name"])]={"name":x["name"],"age":x.get("age"),"age_status":"VERIFIED U18",
          "source":x.get("source") or "Verified U18 registry","source_url":x.get("source_url"),
          "evidence":"Previously verified U18 registry record."}

with sync_playwright() as pw:
    browser=Browser(pw)
    tournaments=[]; health={}

    x,h=discover_generic(browser,ATP_CAL,"atp","ATP Tour","MEN",r"/en/tournaments/");tournaments+=x;health["atp"]=h
    x,h=discover_atp_challenger(browser);tournaments+=x;health["atp_challenger"]=h

    x,h=discover_wta_from_payloads(browser)
    if not x:
        x,h2=discover_wta_from_visible_links(browser)
        h={"payload":h,"visible_fallback":h2,"ok":h2.get("ok",False),"events":len(x),"url":WTA_CAL}
    tournaments+=x;health["wta"]=h
    health["wta_125"]={"ok":h.get("ok",False),
      "events":sum(t.get("tour_id")=="wta-125" for t in x),
      "url":WTA_CAL,"method":"classified from official WTA calendar/tournament data"}
    x,h=discover_itf(browser,ITF_MEN,"itf-men","ITF Men's World Tennis Tour","MEN");tournaments+=x;health["itf_men"]=h
    x,h=discover_itf(browser,ITF_WOMEN,"itf-women","ITF Women's World Tennis Tour","WOMEN");tournaments+=x;health["itf_women"]=h

    # UTR official regional event discovery
    utr_events=[]; utr_health=[]
    for region,url in UTR.items():
        snap=browser.snapshot(url,2200);count=0
        if snap["ok"]:
            for a in snap["links"]:
                if "/events/" not in a["href"]:continue
                start,end=date_range(a["parent"] or a["text"])
                if not overlaps(start,end):continue
                text=" ".join((a["text"] or a["parent"]).split())
                gender="WOMEN" if "women" in text.lower() else "MEN"
                tid="utr-women" if gender=="WOMEN" else "utr-men"
                utr_events.append({"id":hashlib.sha1(a["href"].encode()).hexdigest()[:12],
                    "tour_id":tid,"tour":"UTR Pro Tennis Tour","gender":gender,
                    "tournament":text[:100],"start_date":start.isoformat(),"end_date":end.isoformat(),
                    "location":region,"status":"ACTIVE" if start<=TODAY<=end else "UPCOMING",
                    "source_url":a["href"],"participants":[],"participant_source":"UTR official event page"})
                count+=1
        utr_health.append({"ok":snap["ok"],"region":region,"events":count,"url":url,"error":snap.get("error")})
    tournaments+=utr_events;health["utr"]=utr_health

    junior_u18,junior_candidates,junior_health=junior_watch_index(browser)
    health["itf_juniors"]=junior_health
    u18_index={**junior_u18,**seed_index}

    # Resolve the easy majority in bulk before opening individual profiles.
    atp_age,atp_age_health=ranking_age_index(browser,ATP_RANK,r"/en/players/","ATP official rankings")
    wta_age,wta_age_health=ranking_age_index(browser,WTA_RANK,r"/players/","WTA official rankings")
    health["atp_age_index"]=atp_age_health
    health["wta_age_index"]=wta_age_health
    broad_age_index={**atp_age,**wta_age}

    # If ATP/WTA official calendar discovery failed, keep the page useful with the
    # mapped public schedule while clearly identifying it as a fallback.
    if not any(t["tour_id"]=="atp" for t in tournaments) or not any(t["tour_id"]=="wta" for t in tournaments):
        for t in fallback_global_schedule():
            if not any(x["tour_id"]==t["tour_id"] and norm(x["tournament"])==norm(t["tournament"]) for x in tournaments):
                tournaments.append(t)

    # Deduplicate
    ded={}
    for t in tournaments:
        ded[(t["tour_id"],norm(t["tournament"]),t["start_date"])]=t
    tournaments=list(ded.values())

    # Tournament entrant linkage + FAST age resolution.
    # Order: known U18 -> persistent age cache -> ATP/WTA bulk ranking ages -> unresolved.
    # Individual player profiles are intentionally NOT opened here.
    persistent_age_cache=load_age_cache()

    # Promote current bulk ATP/WTA ranking results into the persistent cache in memory
    # so they can immediately resolve tournament entrants during this run.
    for k,v in broad_age_index.items():
        persistent_age_cache[k]={**persistent_age_cache.get(k,{}),**v,
          "last_verified":NOW.isoformat(),"verification_method":"bulk_official_ranking"}

    for t in tournaments:
        people=participant_links(browser,t)
        t["participants_extracted"]=len(people)
        t["participant_extraction_status"]="EXTRACTED" if people else "NO PARTICIPANT FIELD EXTRACTED"
        t["participant_field_basis"]=t.get("participant_field_basis") or t.get("participant_source") or "Official tournament participant source"
        t["participant_field_complete"]=False
        parts=[]
        targeted=[]
        for p in people:
            k=norm(p["name"])

            # 1. Exact verified U18 universe / persistent U18 cache.
            if k in u18_index:
                rec={**p,**u18_index[k],"screening_status":"VERIFIED_U18"}
                parts.append(rec)
                continue

            cached=persistent_age_cache.get(k)
            if cached and cached.get("age_status")=="VERIFIED U18":
                parts.append({**p,**cached,"screening_status":"VERIFIED_U18"})
                continue

            # 2. Known adult evidence clears the player from targeted review.
            if cached and cached.get("age_status")=="VERIFIED 18+":
                parts.append({**p,**cached,"screening_status":"NO_U18_INDICATOR"})
                continue
            if k in broad_age_index and broad_age_index[k].get("age_status")=="VERIFIED 18+":
                parts.append({**p,**broad_age_index[k],"screening_status":"NO_U18_INDICATOR"})
                continue

            # 3. Exact junior-watch candidate (e.g. 2008 birth year).
            cand=junior_candidates.get(k)
            if cand:
                rec={**p,**cand,
                     "screening_status":"TARGETED_REVIEW",
                     "age_status":"TARGETED REVIEW",
                     "source_url":p.get("profile_url") or cand.get("source_url"),
                     "candidate_reason":cand.get("candidate_reason") or "Junior-age signal requires exact DOB verification."}
                parts.append(rec);targeted.append(rec)
                continue

            # 4. Conservative fuzzy collision with a U18/junior watch name.
            fuzzy=fuzzy_watch_match(p["name"],{**u18_index,**junior_candidates})
            if fuzzy:
                rec={**p,
                     "age":None,"dob":None,
                     "age_status":"TARGETED REVIEW",
                     "screening_status":"TARGETED_REVIEW",
                     "source":fuzzy.get("source") or t["participant_source"],
                     "source_url":p.get("profile_url") or fuzzy.get("source_url"),
                     "candidate_reason":f"Possible identity match to junior/U18 watchlist athlete {fuzzy.get('name')}.",
                     "evidence":"Name collision with the junior/U18 watch universe requires confirmation."}
                parts.append(rec);targeted.append(rec)
                continue

            # 5. No U18 indicator. Unknown DOB alone is NOT a manual-review condition.
            parts.append({**p,
                "age":None,"dob":None,
                "age_status":"NO U18 INDICATOR",
                "screening_status":"NO_U18_INDICATOR",
                "source":t["participant_source"],
                "source_url":p.get("profile_url") or t.get("source_url"),
                "evidence":"No exact or conservative fuzzy match to the verified U18 / junior-age watch universe."})

        # Deduplicate by normalized athlete name.
        dedup={}
        for person in parts:
            dedup[norm(person.get("name"))]=person
        parts=list(dedup.values())
        parts.sort(key=lambda p:(0 if p.get("screening_status")=="VERIFIED_U18"
                                 else 1 if p.get("screening_status")=="TARGETED_REVIEW"
                                 else 2,p.get("name","")))

        t["participants"]=parts
        t["participant_count"]=len(parts)

        field_type=str(t.get("participant_field_type") or "INCOMPLETE")
        confidence=str(t.get("participant_field_confidence") or "LOW")
        expected_min=t.get("participant_field_expected_min")

        # "Captured" now means credible enough to support a GREEN clearance.
        # Acceptance pools can identify a RED U18, but they can never clear a
        # tournament because they are not the final active competition field.
        if field_type=="ACCEPTANCE_POOL":
            t["field_captured"]=False
            t["field_completeness"]="PRE_DRAW_POOL"
        elif confidence=="HIGH":
            t["field_captured"]=True
            t["field_completeness"]="COMPLETE_ENOUGH_FOR_SCREEN"
        elif confidence=="MEDIUM":
            t["field_captured"]=False
            t["field_completeness"]="PARTIAL"
        else:
            t["field_captured"]=False
            t["field_completeness"]="INCOMPLETE"

        t["verified_u18"]=[p for p in parts if p.get("screening_status")=="VERIFIED_U18"]
        t["targeted_review"]=[p for p in parts if p.get("screening_status")=="TARGETED_REVIEW"]
        t["targeted_review_count"]=len(t["targeted_review"])
        t["verified_18plus_count"]=sum(p.get("age_status")=="VERIFIED 18+" for p in parts)
        t["no_u18_indicator_count"]=sum(p.get("screening_status")=="NO_U18_INDICATOR" for p in parts)
        t["unresolved_count"]=t["targeted_review_count"]

        # Active-field U18 status.
        t["confirmed_u18"]=list(t["verified_u18"])
        t["pre_draw_u18"]=[]

        # Acceptance pool is watch-only intelligence. Cross-match ONLY against
        # verified U18 sources/cache; do not count or classify the entire pool.
        for ap in t.get("acceptance_pool_people",[]) or []:
            k=norm(ap.get("name"))
            hit=None
            if k in u18_index:
                hit={**ap,**u18_index[k],"screening_status":"VERIFIED_U18"}
            else:
                cached=persistent_age_cache.get(k)
                if cached and cached.get("age_status")=="VERIFIED U18":
                    hit={**ap,**cached,"screening_status":"VERIFIED_U18"}
            if hit:
                t["pre_draw_u18"].append(hit)

        # de-dupe pool watch hits
        pd={}
        for p0 in t["pre_draw_u18"]:
            pd[norm(p0.get("name"))]=p0
        t["pre_draw_u18"]=list(pd.values())

        if t["confirmed_u18"]:
            t["status_color"]="RED";t["regulatory_status"]="NOT PERMISSIBLE — CONFIRMED U18 ACTIVE FIELD"
        elif t["pre_draw_u18"]:
            t["status_color"]="AMBER";t["regulatory_status"]="REVIEW — U18 IN PRE-DRAW ACCEPTANCE POOL"
        elif not t["field_captured"]:
            t["status_color"]="AMBER";t["regulatory_status"]="REVIEW — PARTICIPANT FIELD INCOMPLETE"
        elif t["targeted_review_count"]:
            t["status_color"]="AMBER";t["regulatory_status"]="REVIEW — TARGETED U18 CHECK"
        else:
            t["status_color"]="GREEN";t["regulatory_status"]="OK — NO U18 EXPOSURE IDENTIFIED"

    # Persist cheap bulk official age resolutions. Deep scan will add profile-based
    # resolutions to the same cache without forcing this refresh to wait on them.
    AGE_CACHE_PATH.write_text(json.dumps({
      "schema_version":1,
      "generated_at":NOW.isoformat(),
      "records":persistent_age_cache
    },indent=2,ensure_ascii=False),encoding="utf-8")

    browser.close()

exposure={norm(p["name"]) for t in tournaments for p in t.get("confirmed_u18",[])}
pre_draw_watch={norm(p["name"]) for t in tournaments for p in t.get("pre_draw_u18",[])}
registry=[]
for k,p in u18_index.items():
    registry.append({**p,"current_exposure":k in exposure})
registry.sort(key=lambda x:(not x["current_exposure"],x["name"]))

exceptions=[]
for t in tournaments:
    for p in t.get("targeted_review",[]):
        exceptions.append({
          "id":hashlib.sha1(f"{t['id']}|{norm(p.get('name'))}".encode()).hexdigest()[:14],
          "tour_id":t["tour_id"],"tour":t["tour"],"gender":t["gender"],
          "tournament":t["tournament"],"tournament_id":t["id"],
          "start_date":t["start_date"],"end_date":t["end_date"],
          "name":p.get("name"),"profile_url":p.get("profile_url") or p.get("source_url"),
          "source":p.get("source"),"candidate_reason":p.get("candidate_reason"),
          "evidence":p.get("evidence")
        })

risks=[]
for t in tournaments:
    for p in t.get("confirmed_u18",[]):
        risks.append({"severity":"RED","type":"VERIFIED U18 ACTIVE FIELD","lane":t["tour_id"],
          "tour":t["tour"],"league":t["tour"],"sport":"Tennis","tournament":t["tournament"],
          "event":t["tournament"],"start_time":t["start_date"],"player":p["name"],"athletes":[p["name"]],
          "age":p.get("age"),"source":p.get("source"),
          "reason":f'{p["name"]} is a verified U18 participant confirmed in the active field for {t["tournament"]}.',
          "staff_action":"Review athlete-specific performance/nonperformance markets involving this participant across all licensed sportsbook platforms."})
    for p in t.get("pre_draw_u18",[]):
        risks.append({"severity":"AMBER","type":"U18 PRE-DRAW WATCH","lane":t["tour_id"],
          "tour":t["tour"],"league":t["tour"],"sport":"Tennis","tournament":t["tournament"],
          "event":t["tournament"],"start_time":t["start_date"],"player":p["name"],"athletes":[p["name"]],
          "age":p.get("age"),"source":p.get("source"),
          "reason":f'{p["name"]} is verified U18 and appears in the pre-draw acceptance pool for {t["tournament"]}; active draw participation is not yet confirmed.',
          "staff_action":"Confirm whether the athlete entered the active draw/order of play before treating the tournament as not permissible."})

tournaments.sort(key=lambda t:(0 if t["status_color"]=="RED" else 1,t["start_date"],t["gender"],t["tour"],t["tournament"]))
summary={"tournaments_mapped":len(tournaments),
 "men_tournaments":sum(t["gender"]=="MEN" for t in tournaments),
 "women_tournaments":sum(t["gender"]=="WOMEN" for t in tournaments),
 "red_tournaments":sum(t["status_color"]=="RED" for t in tournaments),
 "amber_tournaments":sum(t["status_color"]=="AMBER" for t in tournaments),
 "green_tournaments":sum(t["status_color"]=="GREEN" for t in tournaments),
 "active_field_participants_screened":sum(t["participant_count"] for t in tournaments if t.get("participant_field_type")!="ACCEPTANCE_POOL"),
 "pre_draw_pool_names_screened":sum(int(t.get("acceptance_pool_screened_count") or 0) for t in tournaments),
 "verified_u18_players":len(exposure),
 "pre_draw_u18_watch_players":len(pre_draw_watch),
 "targeted_review_candidates":len(exceptions),
 "field_gaps":sum(not t.get("field_captured") for t in tournaments),
 "no_u18_indicator_count":sum(t.get("no_u18_indicator_count",0) for t in tournaments if t.get("participant_field_type")!="ACCEPTANCE_POOL"),
 "age_cache_records":len(persistent_age_cache)}

schedule_out={
 "schema_version":1,"generated_at":NOW.isoformat(),"timezone":"America/Chicago",
 "window_start":TODAY.isoformat(),"window_end":END.isoformat(),
 "tour_families":FAMILIES,
 "tournaments":[{
    "id":t["id"],"tour_id":t["tour_id"],"tour":t["tour"],"gender":t["gender"],
    "tournament":t["tournament"],"start_date":t["start_date"],"end_date":t["end_date"],
    "location":t.get("location"),"category":t.get("category"),
    "status":t.get("status"),"status_color":t.get("status_color"),
    "regulatory_status":t.get("regulatory_status"),
    "participant_count":t.get("participant_count",0),
    "verified_u18_count":len(t.get("confirmed_u18",[])),
    "pre_draw_u18_count":len(t.get("pre_draw_u18",[])),
    "acceptance_pool_screened_count":t.get("acceptance_pool_screened_count",0),
    "targeted_review_count":t.get("targeted_review_count",0),
    "official_main_draw_size":t.get("main_draw_size") or t.get("official_singles_draw_size"),
    "official_qualifying_draw_size":t.get("qualifying_draw_size"),
    "official_doubles_draw_size":t.get("doubles_draw_size") or t.get("official_doubles_draw_size"),
    "field_captured":t.get("field_captured",False),
    "participant_field_type":t.get("participant_field_type"),
    "participant_field_basis":t.get("participant_field_basis"),
    "participant_field_confidence":t.get("participant_field_confidence"),
    "field_completeness":t.get("field_completeness"),
    "source_url":t.get("source_url")
 } for t in tournaments]
}

registry_out={
 "schema_version":1,"generated_at":NOW.isoformat(),
 "verified_u18":registry,
 "junior_targeted_candidates":list(junior_candidates.values()),
 "source_health":health.get("itf_juniors",[])
}

exceptions_out={
 "schema_version":1,"generated_at":NOW.isoformat(),
 "count":len(exceptions),"exceptions":exceptions
}

out={"schema_version":6,"generated_at":NOW.isoformat(),"timezone":"America/Chicago",
 "window_start":TODAY.isoformat(),"window_end":END.isoformat(),"tour_families":FAMILIES,
 "summary":summary,"tournaments":tournaments,"risk_queue":risks,
 "live_u18_registry":registry,"targeted_exceptions":exceptions,"source_health":health,
 "methodology":{
   "red":"Verified U18 athlete is confirmed in an active draw/player field or order of play.",
   "amber":"Pre-draw acceptance pool, incomplete/partial active field, U18 pre-draw watch, or targeted U18 candidate.",
   "green":"Credible active draw/player field captured with no verified U18 exposure or targeted U18 candidate.",
   "important":"Unknown DOB alone does not create manual review. Only a specific U18/junior-age indicator creates a targeted age exception.",
   "scope":"Main draw, qualifying, doubles, wild cards, acceptance lists, accepted alternates and order of play are in scope.",
   "screening":"Tournament entrants are cross-matched against a dynamic verified-U18 registry and an ITF junior-age candidate universe."
 }}


# ---------------- Quality gate ----------------
quality_issues=[]
critical_issues=[]

# Never publish GREEN without a credible field.
for t in tournaments:
    if t.get("status_color")=="GREEN" and not t.get("field_captured"):
        critical_issues.append(f"GREEN_WITHOUT_FIELD: {t.get('tour')} | {t.get('tournament')}")
    if t.get("status_color")=="RED" and t.get("participant_field_type")=="ACCEPTANCE_POOL":
        critical_issues.append(f"RED_FROM_ACCEPTANCE_POOL: {t.get('tour')} | {t.get('tournament')}")
    if t.get("participant_field_type")!="ACCEPTANCE_POOL" and int(t.get("participant_count") or 0)>192:
        critical_issues.append(f"IMPLAUSIBLE_ACTIVE_FIELD_SIZE: {t.get('tour')} | {t.get('tournament')} | {t.get('participant_count')}")

chal_health=health.get("atp_challenger") or {}
if int(chal_health.get("calendar_overlap_mentions") or 0)>0 and not any(t.get("tour_id")=="atp-challenger" for t in tournaments):
    critical_issues.append("ATP_CHALLENGER_OFFICIAL_SOURCE_HAS_CURRENT_EVENTS_BUT_DISCOVERY_RETURNED_ZERO")

wta_events=[t for t in tournaments if t.get("tour_id") in ("wta","wta-125")]
wta_health=health.get("wta") or {}
if wta_health.get("ok") and not wta_events:
    critical_issues.append("WTA_OFFICIAL_CALENDAR_LOADED_BUT_DISCOVERY_RETURNED_ZERO")

# Coverage gaps are visible quality warnings, not fatal.
for family in FAMILIES:
    n=sum(t.get("tour_id")==family["id"] for t in tournaments)
    if n==0:
        quality_issues.append(f"NO_CURRENT_TOURNAMENTS_MAPPED: {family['tour']}")

quality_gate={
  "passed":not critical_issues,
  "critical_issues":critical_issues,
  "warnings":quality_issues,
  "checked_at":NOW.isoformat()
}
out["quality_gate"]=quality_gate
schedule_out["quality_gate"]=quality_gate

if critical_issues:
    print(json.dumps({"quality_gate":"FAILED","critical_issues":critical_issues},indent=2))
    raise SystemExit(2)

(DATA/"tennis-schedule.json").write_text(json.dumps(schedule_out,indent=2,ensure_ascii=False),encoding="utf-8")
(DATA/"tennis-u18-registry.json").write_text(json.dumps(registry_out,indent=2,ensure_ascii=False),encoding="utf-8")
(DATA/"tennis-exceptions.json").write_text(json.dumps(exceptions_out,indent=2,ensure_ascii=False),encoding="utf-8")
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(summary))
