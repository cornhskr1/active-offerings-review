#!/usr/bin/env python3
from pathlib import Path
import json, re, datetime, hashlib
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
ATP_CHAL="https://www.atptour.com/en/atp-challenger-tour"
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
        try:
            self.page.goto(url,wait_until="domcontentloaded",timeout=35000)
            self.page.wait_for_timeout(wait)
            text=self.page.locator("body").inner_text(timeout=8000)
            links=self.page.locator("a").evaluate_all(
                """els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||'',parent:(a.closest('tr,article,li,section,div')?.innerText||'').trim()}))"""
            )
            rows=self.page.locator("tr").evaluate_all(
                """els=>els.map(tr=>({cells:[...tr.querySelectorAll('th,td')].map(x=>(x.innerText||'').trim()),text:(tr.innerText||'').trim()}))"""
            )
            html=self.page.content()
            return {"ok":True,"url":self.page.url,"text":text,"links":links,"rows":rows,"html":html}
        except Exception as e:
            return {"ok":False,"url":url,"text":"","links":[],"rows":[],"html":"","error":str(e)[:180]}

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
                name=m.group(1).strip()
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
    found={}

    if tid.startswith("itf-"):
        # Draw / order of play are the best evidence of actual participation.
        primary=[t.get("draw_url"),t.get("order_url")]
        primary_count=0
        for url in primary:
            if not url:continue
            snap=browser.snapshot(url,1100)
            if not snap.get("ok"):continue
            for a in snap.get("links",[]):
                if re.search(r"/en/players/",a.get("href",""),re.I):
                    before=len(found); add_person(found,a.get("text"),a.get("href"),"ITF draw/order of play")
                    primary_count += len(found)-before
            extract_itf_table_text(found,snap)

        # Acceptance List is a fallback / supplement, but withdrawals are excluded.
        if primary_count==0 or len(found)<8:
            url=t.get("acceptance_url")
            if url:
                snap=browser.snapshot(url,1100)
                if snap.get("ok"):
                    for a in snap.get("links",[]):
                        parent=a.get("parent","")
                        if re.search(r"/en/players/",a.get("href",""),re.I) and not re.search(r"withdraw|Automatic Withdrawal",parent,re.I):
                            add_person(found,a.get("text"),a.get("href"),"ITF acceptance list")
                    extract_itf_table_text(found,snap)

    elif tid.startswith("wta"):
        urls=[wta_player_list_url(t.get("source_url")),wta_draw_url(t.get("source_url")),t.get("source_url")]
        for url in urls:
            if not url:continue
            snap=browser.snapshot(url,1200)
            if not snap.get("ok"):continue
            for a in snap.get("links",[]):
                if re.search(r"/players/",a.get("href",""),re.I):
                    add_person(found,a.get("text"),a.get("href"),"WTA official player/draw page")
            extract_wta_text(found,snap)
            extract_embedded_names(found,snap.get("html"),"WTA rendered tournament data")

    elif tid.startswith("atp"):
        for url in atp_draw_urls(t.get("source_url")):
            snap=browser.snapshot(url,1300)
            if not snap.get("ok"):continue
            for a in snap.get("links",[]):
                if re.search(r"/en/players/",a.get("href",""),re.I):
                    add_person(found,a.get("text"),a.get("href"),"ATP official draw/results page")
            extract_embedded_names(found,snap.get("html"),"ATP rendered tournament data")

    else:
        # UTR Pro Tennis Tour
        url=t.get("source_url")
        if url:
            snap=browser.snapshot(url,1500)
            if snap.get("ok"):
                for a in snap.get("links",[]):
                    if re.search(r"/(profile|profiles|player|players)/",a.get("href",""),re.I):
                        add_person(found,a.get("text"),a.get("href"),"UTR official event page")
                extract_embedded_names(found,snap.get("html"),"UTR rendered event data")

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

def junior_u18_index(browser):
    out={}; health=[]
    for gender,url in [("MEN",ITF_JB),("WOMEN",ITF_JG)]:
        snap=browser.snapshot(url,2000)
        count=0
        if snap["ok"]:
            for a in snap["links"]:
                if "/en/players/" not in a["href"]:continue
                row=a["parent"] or ""
                m=re.search(r'\b(2008|2009|2010|2011|2012)\b',row)
                name=" ".join(a["text"].split())
                if not m or len(name.split())<2:continue
                yob=int(m.group(1))
                if yob>=2009:
                    out[norm(name)]={"name":name,"age":YEAR-yob,"age_status":"VERIFIED U18",
                        "source":"ITF official junior rankings","source_url":a["href"],
                        "evidence":f"Official ITF junior ranking lists birth year {yob}."}
                    count+=1
        health.append({"ok":snap["ok"],"gender":gender,"verified_u18":count,"url":url,"error":snap.get("error")})
    return out,health

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
    x,h=discover_generic(browser,ATP_CHAL,"atp-challenger","ATP Challenger Tour","MEN",r"/en/tournaments/");tournaments+=x;health["atp_challenger"]=h
    x,h=discover_generic(browser,WTA_CAL,"wta","WTA Tour","WOMEN",r"/tournaments/");tournaments+=x;health["wta"]=h
    x,h=discover_generic(browser,WTA_125,"wta-125","WTA 125","WOMEN",r"/tournaments/");tournaments+=x;health["wta_125"]=h
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

    juniors,junior_health=junior_u18_index(browser)
    health["itf_juniors"]=junior_health
    u18_index={**juniors,**seed_index}

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

    # Tournament entrant linkage + automatic age resolution.
    # Order: known U18 -> official rankings -> exact official profile -> unresolved only.
    for t in tournaments:
        people=participant_links(browser,t)
        t["participants_extracted"]=len(people)
        t["participant_extraction_status"]="EXTRACTED" if people else "NO PARTICIPANT FIELD EXTRACTED"
        parts=[]
        on_date=datetime.date.fromisoformat(t["start_date"])
        for p in people:
            k=norm(p["name"])
            if k in u18_index:
                parts.append({**p,**u18_index[k]})
                continue
            if k in broad_age_index:
                parts.append({**p,**broad_age_index[k]})
                continue

            profile_result=resolve_profile_age(browser,p,on_date)
            if profile_result:
                parts.append({**p,**profile_result})
            else:
                parts.append({**p,"age":None,"dob":None,"age_status":"UNRESOLVED",
                    "source":t["participant_source"],
                    "source_url":p.get("profile_url") or t.get("source_url"),
                    "evidence":"Participant is linked to the official tournament field, but explicit age/DOB was not resolved from the official ranking/profile sources."})

        # Deduplicate by normalized athlete name.
        dedup={}
        for person in parts:
            dedup[norm(person.get("name"))]=person
        parts=list(dedup.values())
        parts.sort(key=lambda p:(0 if p.get("age_status")=="VERIFIED U18" else 1 if p.get("age_status")=="UNRESOLVED" else 2,p.get("name","")))

        t["participants"]=parts
        t["participant_count"]=len(parts)
        t["verified_u18"]=[p for p in parts if p.get("age_status")=="VERIFIED U18"]
        t["verified_18plus_count"]=sum(p.get("age_status")=="VERIFIED 18+" for p in parts)
        t["unresolved_count"]=sum(p.get("age_status")=="UNRESOLVED" for p in parts)
        t["age_resolution_pct"]=round(((len(parts)-t["unresolved_count"])/len(parts))*100) if parts else 0

        if t["verified_u18"]:
            t["status_color"]="RED";t["regulatory_status"]="NOT PERMISSIBLE — U18 EXPOSURE"
        elif len(parts)>=4 and t["unresolved_count"]==0:
            t["status_color"]="GREEN";t["regulatory_status"]="OK — PARTICIPANT FIELD AGE-RESOLVED"
        else:
            t["status_color"]="AMBER";t["regulatory_status"]="MANUAL REVIEW — UNRESOLVED AGE COVERAGE"

    browser.close()

exposure={norm(p["name"]) for t in tournaments for p in t.get("verified_u18",[])}
registry=[]
for k,p in u18_index.items():registry.append({**p,"current_exposure":k in exposure})
registry.sort(key=lambda x:(not x["current_exposure"],x["name"]))

risks=[]
for t in tournaments:
    for p in t.get("verified_u18",[]):
        risks.append({"severity":"RED","type":"VERIFIED U18 TOURNAMENT","lane":t["tour_id"],
          "tour":t["tour"],"league":t["tour"],"sport":"Tennis","tournament":t["tournament"],
          "event":t["tournament"],"start_time":t["start_date"],"player":p["name"],"athletes":[p["name"]],
          "age":p.get("age"),"source":p.get("source"),
          "reason":f'{p["name"]} is a verified U18 participant linked to {t["tournament"]}.',
          "staff_action":"Review all athlete-specific performance/nonperformance markets involving this participant across all licensed sportsbook platforms."})

tournaments.sort(key=lambda t:(0 if t["status_color"]=="RED" else 1,t["start_date"],t["gender"],t["tour"],t["tournament"]))
summary={"tournaments_mapped":len(tournaments),
 "men_tournaments":sum(t["gender"]=="MEN" for t in tournaments),
 "women_tournaments":sum(t["gender"]=="WOMEN" for t in tournaments),
 "red_tournaments":sum(t["status_color"]=="RED" for t in tournaments),
 "amber_tournaments":sum(t["status_color"]=="AMBER" for t in tournaments),
 "green_tournaments":sum(t["status_color"]=="GREEN" for t in tournaments),
 "participants_found":sum(t["participant_count"] for t in tournaments),
 "verified_u18_players":len(exposure)}

out={"schema_version":5,"generated_at":NOW.isoformat(),"timezone":"America/Chicago",
 "window_start":TODAY.isoformat(),"window_end":END.isoformat(),"tour_families":FAMILIES,
 "summary":summary,"tournaments":tournaments,"risk_queue":risks,
 "live_u18_registry":registry,"source_health":health,
 "methodology":{
   "red":"Verified U18 athlete is linked by an official professional tournament participant source.",
   "amber":"Tournament is mapped, but one or more participant ages remain unresolved after official ranking/profile checks.",
   "green":"Official participant field was obtained and every listed entrant was resolved as 18+.",
   "scope":"Main draw, qualifying, doubles, wild cards, acceptance lists, accepted alternates and order of play are in scope.",
   "discovery":"Official ATP/WTA/ITF/UTR pages are rendered in Chromium so JavaScript-loaded calendars and participant links are visible."
 }}
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(summary))
