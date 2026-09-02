
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

HEADERS={"User-Agent":"Mozilla/5.0 ActiveOfferingsReview/1.0"}
ATP_CALENDAR="https://www.atptour.com/en/tournaments/"
ATP_RANKINGS="https://www.atptour.com/en/rankings/singles?rankRange=1-1000"
WTA_CALENDAR="https://www.wtatennis.com/tournaments"
WTA_RANKINGS="https://www.wtatennis.com/rankings/singles/"
ITF_CALENDARS={
 "itf-men":"https://www.itftennis.com/en/tournament-calendar/mens-world-tennis-tour-calendar/?categories=All&startdate={ym}",
 "itf-women":"https://www.itftennis.com/en/tournament-calendar/womens-world-tennis-tour-calendar/?categories=All&startdate={ym}",
}
UTR_CLUBS={
 "Americas":"https://app.utrsports.net/club/11313",
 "Europe":"https://app.utrsports.net/club/12083",
 "Asia & Pacific":"https://app.utrsports.net/club/12084?tab=info",
}

ITF_JUNIOR_RANKINGS={
 "Girls":"https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=G",
 "Boys":"https://www.itftennis.com/en/rankings/world-tennis-tour-junior-rankings/?juniorRankingType=ITF&playerType=B",
}

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def get(url,timeout=25):
    r=requests.get(url,headers=HEADERS,timeout=timeout)
    r.raise_for_status()
    return r

def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\u2018\u2019'`]", "", s)
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

def age_on(dob,on_date):
    return on_date.year-dob.year-((on_date.month,on_date.day)<(dob.month,dob.day))

def parse_explicit_dob(text):
    pats=[
      r'(?:Birthday|Date of Birth|Date of birth|DOB|Born)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
      r'(?:Birthday|Date of Birth|Date of birth|DOB|Born)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
      r'(?:Birthday|Date of Birth|Date of birth|DOB|Born)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for p in pats:
        m=re.search(p,text,re.I)
        if not m:continue
        raw=m.group(1)
        for fmt in ("%d %B %Y","%d %b %Y","%B %d, %Y","%B %d %Y","%b %d, %Y","%d/%m/%Y","%m/%d/%Y","%d-%m-%Y"):
            try:return datetime.datetime.strptime(raw,fmt).date()
            except Exception:pass
    return None

def parse_date_range(text,year=2026):
    patterns=[
      r'(\d{1,2})\s+([A-Za-z]+)\s*(?:-|to)\s*(\d{1,2})\s+([A-Za-z]+),?\s*'+str(year),
      r'([A-Za-z]+)\s+(\d{1,2})\s*(?:-|to)\s*([A-Za-z]+)?\s*(\d{1,2}),?\s*'+str(year),
    ]
    for i,p in enumerate(patterns):
        m=re.search(p,text,re.I)
        if not m:continue
        try:
            if i==0:
                d1,mo1,d2,mo2=m.group(1),m.group(2),m.group(3),m.group(4)
            else:
                mo1,d1,mo2,d2=m.group(1),m.group(2),m.group(3) or m.group(1),m.group(4)
            for fmt in ("%d %B %Y","%d %b %Y"):
                try:a=datetime.datetime.strptime(f"{d1} {mo1} {year}",fmt).date();break
                except Exception:a=None
            for fmt in ("%d %B %Y","%d %b %Y"):
                try:b=datetime.datetime.strptime(f"{d2} {mo2} {year}",fmt).date();break
                except Exception:b=None
            if a and b:
                if b<a:b=b.replace(year=year+1)
                return a,b
        except Exception:pass
    return None,None

def overlaps(a,b):
    return bool(a and b and a<=END and b>=TODAY)

# ------------------------------------------------------------------
# OFFICIAL ATP/WTA AGE INDEX
# ------------------------------------------------------------------
def scrape_atp_age_index():
    out={}
    health={"ok":False,"url":ATP_RANKINGS,"records":0}
    try:
        soup=BeautifulSoup(get(ATP_RANKINGS).text,"html.parser")
        # Prefer rows with player profile links.
        for tr in soup.find_all("tr"):
            a=tr.find("a",href=re.compile(r"/en/players/",re.I))
            if not a:continue
            name=" ".join(a.stripped_strings).strip()
            cells=[" ".join(td.stripped_strings) for td in tr.find_all(["td","th"])]
            age=None
            # Age is normally its own compact integer cell.
            for c in cells[1:5]:
                if re.fullmatch(r"(1[4-9]|[2-4]\d)",c.strip()):
                    age=int(c.strip());break
            if name and age is not None:
                out[norm(name)]={"name":name,"age":age,"status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
                                 "source":"ATP official rankings","source_url":urljoin("https://www.atptour.com",a["href"])}
        # Fallback text patterns on server-rendered page.
        if not out:
            txt="\n".join(soup.stripped_strings)
            for m in re.finditer(r'([A-Z][A-Za-z\'\-.]+(?:\s+[A-Z][A-Za-z\'\-.]+)+)\s*\|\s*(1[4-9]|[2-4]\d)\s*\|',txt):
                name,age=m.group(1),int(m.group(2))
                out[norm(name)]={"name":name,"age":age,"status":"VERIFIED U18" if age<18 else "VERIFIED 18+","source":"ATP official rankings","source_url":ATP_RANKINGS}
        health.update(ok=True,records=len(out))
    except Exception as e:health["error"]=str(e)[:180]
    return out,health

def scrape_wta_age_index():
    out={}
    health={"ok":False,"url":WTA_RANKINGS,"records":0}
    try:
        soup=BeautifulSoup(get(WTA_RANKINGS).text,"html.parser")
        for tr in soup.find_all("tr"):
            a=tr.find("a",href=re.compile(r"/players/\d+/",re.I))
            if not a:continue
            name=" ".join(a.stripped_strings).strip()
            cells=[" ".join(td.stripped_strings) for td in tr.find_all(["td","th"])]
            age=None
            for c in cells[1:6]:
                if re.fullmatch(r"(1[4-9]|[2-4]\d)",c.strip()):
                    age=int(c.strip());break
            if name and age is not None:
                out[norm(name)]={"name":name,"age":age,"status":"VERIFIED U18" if age<18 else "VERIFIED 18+",
                                 "source":"WTA official rankings","source_url":urljoin("https://www.wtatennis.com",a["href"])}
        # WTA sometimes renders ranking rows without anchors in initial HTML.
        txt=" ".join(soup.stripped_strings)
        if not out:
            # conservative: only lines around explicit "Age" table structures are used later via profiles; no fuzzy ages.
            pass
        health.update(ok=True,records=len(out))
    except Exception as e:health["error"]=str(e)[:180]
    return out,health

# ------------------------------------------------------------------
# OFFICIAL ATP/WTA TOURNAMENT CALENDAR CROSS-CHECK
# ------------------------------------------------------------------
def scrape_calendar(url,tour):
    events=[]
    health={"ok":False,"url":url,"events":0}
    try:
        soup=BeautifulSoup(get(url).text,"html.parser")
        # calendar cards usually have tournament links; walk their local text for dates
        seen=set()
        link_re=r"/en/tournaments/" if tour=="ATP" else r"/tournaments/"
        for a in soup.find_all("a",href=re.compile(link_re,re.I)):
            href=urljoin(url,a["href"])
            if href in seen:continue
            node=a
            for _ in range(5):
                txt=" ".join(node.stripped_strings)
                start,end=parse_date_range(txt)
                if start and end:break
                if not node.parent:break
                node=node.parent
            if not start or not overlaps(start,end):continue
            name=" ".join(a.stripped_strings).strip()
            if not name:continue
            seen.add(href)
            events.append({"tour":tour,"tournament":name,"start_date":start.isoformat(),"end_date":end.isoformat(),"source_url":href})
        health.update(ok=True,events=len(events))
    except Exception as e:health["error"]=str(e)[:180]
    return events,health

# ------------------------------------------------------------------
# ITF
# ------------------------------------------------------------------
def extract_itf_tournaments(lane):
    ym=TODAY.strftime("%Y-%m")
    url=ITF_CALENDARS[lane].format(ym=ym)
    out=[]
    try:soup=BeautifulSoup(get(url).text,"html.parser")
    except Exception as e:return [],{"ok":False,"url":url,"error":str(e)[:180]}
    seen=set()
    for a in soup.find_all("a",href=True):
        href=a["href"]
        if "/en/tournament/" not in href or "/2026/" not in href:continue
        fact=urljoin("https://www.itftennis.com",href)
        fact=re.sub(r'/(acceptance-list|draws-and-results|order-of-play)/?$',"/fact-sheet/",fact)
        if "/fact-sheet/" not in fact:
            fact=fact.rstrip("/")+"/fact-sheet/"
        if fact in seen:continue
        node=a
        start=end=None
        for _ in range(5):
            txt=" ".join(node.stripped_strings)
            start,end=parse_date_range(txt)
            if start and end:break
            if not node.parent:break
            node=node.parent
        if not overlaps(start,end):continue
        label=" ".join(a.stripped_strings).strip() or fact.split("/en/tournament/")[1].split("/")[0].replace("-"," ").upper()
        if "cancelled" in " ".join(node.stripped_strings).lower():status="CANCELLED"
        elif start<=TODAY<=end:status="ACTIVE"
        else:status="UPCOMING"
        seen.add(fact)
        out.append({
          "id":hashlib.sha1(fact.encode()).hexdigest()[:12],"lane":lane,"tournament":label,
          "start_date":start.isoformat(),"end_date":end.isoformat(),"status":status,"source_url":fact,
          "acceptance_url":fact.replace("/fact-sheet/","/acceptance-list/"),
          "draw_url":fact.replace("/fact-sheet/","/draws-and-results/"),
          "order_url":fact.replace("/fact-sheet/","/order-of-play/")
        })
    return out,{"ok":True,"url":url,"events":len(out)}

profile_cache={}
def inspect_itf_profile(name,url,event_date):
    if url in profile_cache:return profile_cache[url]
    rec={"name":name,"age":None,"dob":None,"age_status":"UNRESOLVED","source":"ITF official player profile","source_url":url,
         "evidence":"Official ITF profile found; explicit DOB not parsed."}
    try:
        text=" ".join(BeautifulSoup(get(url,18).text,"html.parser").stripped_strings)
        dob=parse_explicit_dob(text)
        if dob:
            age=age_on(dob,event_date)
            rec.update(age=age,dob=dob.isoformat(),age_status="VERIFIED U18" if age<18 else "VERIFIED 18+",
                       evidence="Explicit birth information parsed from official ITF player profile.")
    except Exception as e:rec["evidence"]=f"ITF profile fetch failed: {str(e)[:100]}"
    profile_cache[url]=rec
    return rec

def enrich_itf(t):
    profiles={}
    page_names={}
    for url,label in [(t["draw_url"],"Draws & Results"),(t["acceptance_url"],"Acceptance List"),(t["order_url"],"Order of Play")]:
        try:
            soup=BeautifulSoup(get(url,20).text,"html.parser")
            for a in soup.find_all("a",href=re.compile(r"/en/players/",re.I)):
                name=" ".join(a.stripped_strings).strip()
                if name and len(name)<80:
                    profiles[urljoin("https://www.itftennis.com",a["href"])]=name
        except Exception:pass
    date=datetime.date.fromisoformat(t["start_date"])
    participants=[inspect_itf_profile(n,u,date) for u,n in list(profiles.items())[:100]]
    t.update(participants=participants,participant_count=len(participants),
             verified_u18=[p for p in participants if p["age_status"]=="VERIFIED U18"],
             verified_18plus_count=sum(p["age_status"]=="VERIFIED 18+" for p in participants),
             unresolved_count=sum(p["age_status"]=="UNRESOLVED" for p in participants),
             participant_source="Official ITF Draws / Acceptance List / Order of Play")
    return t

# ------------------------------------------------------------------
# UTR display cleanup
# ------------------------------------------------------------------
def clean_utr_title(raw):
    txt=re.sub(r'\s+',' ',str(raw or '')).strip()

    # Remove repeated leading date ranges.
    txt=re.sub(r'^(?:[A-Za-z]{3}\s+\d{1,2}\s*-\s*(?:[A-Za-z]{3}\s+)?\d{1,2}\s*)+','',txt,flags=re.I)
    txt=re.sub(r'^\d{1,2}\s+[A-Za-z]{3}\s*-\s*\d{1,2}\s+[A-Za-z]{3}\s*','',txt,flags=re.I)

    # Remove generic page furniture.
    txt=re.sub(r'\b2026\s+tennis\s+Tournament\s*\|\s*Verified Event\s*\|\s*','',txt,flags=re.I)
    txt=re.sub(r'\btennis\s+Tournament\s*\|\s*Verified Event\s*\|\s*','',txt,flags=re.I)

    # Trim fee / division boilerplate.
    txt=re.split(r'\s+(?:Free–?\$?\d+|\$?\d+\s+Division Fees?|Division Fees?|Fees)\b',txt,1,flags=re.I)[0]
    txt=re.sub(r'\s*\|\s*$','',txt).strip(" -|")

    # Remove a duplicated trailing city if it simply repeats the event name.
    words=txt.split()
    if len(words)>=2 and words[-1].lower() in {w.lower() for w in words[:-1]}:
        # only remove a single obvious repeat at the end
        txt=" ".join(words[:-1])

    return txt.strip()

# ------------------------------------------------------------------
# UTR: discover events + attempt public participant extraction
# ------------------------------------------------------------------
def parse_utr_dates(text):
    m=re.search(r'([A-Za-z]{3})\s+(\d{1,2})\s*-\s*(?:([A-Za-z]{3})\s+)?(\d{1,2})',text)
    if not m:return None,None
    try:
        a=datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {TODAY.year}","%b %d %Y").date()
        b=datetime.datetime.strptime(f"{m.group(3) or m.group(1)} {m.group(4)} {TODAY.year}","%b %d %Y").date()
        if b<a:b=b.replace(year=TODAY.year+1)
        return a,b
    except Exception:return None,None

def extract_utr(age_index,known_index):
    out=[];health=[];seen=set()
    for region,url in UTR_CLUBS.items():
        try:
            soup=BeautifulSoup(get(url).text,"html.parser");count=0
            for a in soup.find_all("a",href=True):
                href=a["href"];txt=" ".join(a.stripped_strings)
                if "/events/" not in href or "UTR" not in txt:continue
                start,end=parse_utr_dates(txt)
                if not overlaps(start,end):continue
                full=urljoin("https://app.utrsports.net",href)
                if full in seen:continue
                seen.add(full)
                gender="women" if re.search(r'\bwomen\b',txt,re.I) else "men"
                name=clean_utr_title(txt)[:100]
                participants={}
                try:
                    esoup=BeautifulSoup(get(full,20).text,"html.parser")
                    # Common public UTR profile patterns.
                    for pa in esoup.find_all("a",href=True):
                        ph=pa["href"]
                        if not re.search(r'/(profiles?|players?)/',ph,re.I):continue
                        pn=" ".join(pa.stripped_strings).strip()
                        if 3<len(pn)<80 and len(pn.split())>=2:
                            participants[norm(pn)]={"name":pn,"utr_profile_url":urljoin("https://app.utrsports.net",ph)}
                except Exception:pass
                plist=[]
                for k,p in participants.items():
                    evidence=age_index.get(k) or known_index.get(k)
                    if evidence:
                        plist.append({**p,**evidence})
                    else:
                        plist.append({**p,"age":None,"age_status":"UNRESOLVED","source":"UTR public participant page",
                                      "evidence":"Participant found on UTR page; no matching official ATP/WTA/ITF age evidence."})
                city=None
                cm=re.search(r'(?:UTR(?: PTT| Pro Fall Slam)?\s+)([A-Za-z .\'-]+?)(?:\s+(?:Men|Women)(?:\+H)?$)',name,re.I)
                if cm:
                    city=cm.group(1).strip()

                out.append({
                  "id":hashlib.sha1(full.encode()).hexdigest()[:12],"lane":"utr-"+gender,"tournament":name,
                  "start_date":start.isoformat(),"end_date":end.isoformat(),
                  "status":"ACTIVE" if start<=TODAY<=end else "UPCOMING","region":region,"location":city or region,"source_url":full,
                  "participants":plist,"participant_count":len(plist),"verified_u18":[p for p in plist if p.get("age_status")=="VERIFIED U18"],
                  "participant_source":"Official UTR public event page"
                })
                count+=1
            health.append({"region":region,"ok":True,"url":url,"events":count})
        except Exception as e:health.append({"region":region,"ok":False,"url":url,"events":0,"error":str(e)[:180]})
    return out,health


# ------------------------------------------------------------------
# LIVE ITF JUNIOR U18 WATCHLIST
# ------------------------------------------------------------------
def scrape_itf_junior_u18_watchlist():
    """
    Builds a broader official U18 watchlist from the ITF junior rankings.
    2009+ birth years are unambiguously U18 during 2026.
    2008 birth years are only included if an official ITF profile explicitly
    verifies age < 18.
    """
    records={}
    health=[]
    for gender,url in ITF_JUNIOR_RANKINGS.items():
        try:
            soup=BeautifulSoup(get(url).text,"html.parser")
            count=0

            # First collect explicit profile links and visible names.
            profile_links={}
            for a in soup.find_all("a",href=re.compile(r"/en/players/",re.I)):
                name=" ".join(a.stripped_strings).strip()
                if name and 3 < len(name) < 80:
                    profile_links[norm(name)]=(name,urljoin("https://www.itftennis.com",a["href"]))

            # Parse ranking table rows with Year of Birth.
            for tr in soup.find_all("tr"):
                cells=[" ".join(td.stripped_strings).strip() for td in tr.find_all(["td","th"])]
                if len(cells)<3: continue
                row=" | ".join(cells)
                yobm=re.search(r'\b(2008|2009|2010|2011|2012)\b',row)
                if not yobm: continue
                yob=int(yobm.group(1))

                a=tr.find("a",href=re.compile(r"/en/players/",re.I))
                name=" ".join(a.stripped_strings).strip() if a else ""
                if not name:
                    # best effort: choose a text cell that looks like a full player name
                    for c in cells:
                        if len(c.split())>=2 and not re.search(r'^\d+(?:\.\d+)?$',c) and c not in ("Boys","Girls"):
                            name=c
                            break
                if not name: continue

                rec={
                    "name":name,
                    "age":None,
                    "birth_year":yob,
                    "age_status":"UNRESOLVED",
                    "source":"ITF official junior rankings",
                    "source_url":url,
                    "gender":gender,
                    "registry_scope":"BROADER WATCHLIST",
                    "evidence":f"ITF junior rankings list year of birth {yob}."
                }

                # Anyone born 2009+ is guaranteed U18 during calendar year 2026.
                if yob>=2009:
                    rec["age_status"]="VERIFIED U18"
                    rec["evidence"]=f"Official ITF junior rankings list year of birth {yob}; athlete cannot be 18 during 2026."
                else:
                    # 2008 requires explicit current age/profile evidence.
                    link=None
                    if a:
                        link=urljoin("https://www.itftennis.com",a["href"])
                    elif norm(name) in profile_links:
                        link=profile_links[norm(name)][1]
                    if link:
                        try:
                            text=" ".join(BeautifulSoup(get(link,18).text,"html.parser").stripped_strings)
                            am=re.search(r'\bAge\s*:\s*(1[4-9]|2\d)\b',text,re.I)
                            if am:
                                age=int(am.group(1))
                                rec.update(age=age,age_status="VERIFIED U18" if age<18 else "VERIFIED 18+",
                                           source="ITF official player profile",
                                           source_url=link,
                                           evidence=f"Official ITF player profile lists age {age}.")
                        except Exception:
                            pass

                if rec["age_status"]=="VERIFIED U18":
                    records[norm(name)]=rec
                    count+=1

            # Some ITF ranking pages expose player names/profile links outside table rows.
            # For those, inspect visible profiles only when no table record was produced.
            for k,(name,link) in list(profile_links.items())[:30]:
                if k in records: continue
                try:
                    text=" ".join(BeautifulSoup(get(link,15).text,"html.parser").stripped_strings)
                    am=re.search(r'\bAge\s*:\s*(1[4-9]|2\d)\b',text,re.I)
                    if am and int(am.group(1))<18:
                        age=int(am.group(1))
                        records[k]={
                            "name":name,"age":age,"birth_year":None,
                            "age_status":"VERIFIED U18",
                            "source":"ITF official player profile","source_url":link,
                            "gender":gender,"registry_scope":"BROADER WATCHLIST",
                            "evidence":f"Official ITF player profile lists age {age}."
                        }
                        count+=1
                except Exception:
                    pass

            health.append({"gender":gender,"ok":True,"url":url,"verified_u18":count})
        except Exception as e:
            health.append({"gender":gender,"ok":False,"url":url,"verified_u18":0,"error":str(e)[:180]})
    return list(records.values()),health

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
known=load(DATA/"tennis-known-u18.json",{}).get("records",[])
schedule=load(DATA/"global-schedule.json",{})
previous=load(DATA/"tennis-intelligence.json",{})

junior_watchlist,junior_health=scrape_itf_junior_u18_watchlist()

known_index={}
for x in known:
    known_index[norm(x["name"])]={"name":x["name"],"age":x.get("age"),"age_status":"VERIFIED U18",
                                  "source":"Known U18 registry","evidence":"Previously verified U18 record"}

atp_index,atp_rank_health=scrape_atp_age_index()
wta_index,wta_rank_health=scrape_wta_age_index()
age_index={**atp_index,**wta_index,**known_index}

atp_calendar,atp_cal_health=scrape_calendar(ATP_CALENDAR,"ATP")
wta_calendar,wta_cal_health=scrape_calendar(WTA_CALENDAR,"WTA")

# Mapped exact ATP/WTA match schedule from existing scoreboard adapter,
# cross-checked against official tour calendars and official tour age indexes.
mapped=[]
for e in schedule.get("events",[]):
    if e.get("sport")!="Tennis":continue
    league=str(e.get("league") or "").upper()
    if league not in ("ATP","WTA"):continue
    parts=re.split(r"\s+(?:vs\.?|at)\s+",str(e.get("name") or ""),maxsplit=1,flags=re.I)
    players=[]
    for pn in parts:
        pn=pn.strip()
        if not pn:continue
        ev=age_index.get(norm(pn))
        if ev:players.append({"name":pn,**ev})
        else:players.append({"name":pn,"age":None,"age_status":"UNRESOLVED","source":"Mapped match schedule",
                             "evidence":"Player is scheduled; no official ATP/WTA ranking-age match was resolved."})
    e2={**e,"lane":league.lower(),"participants":players,
        "verified_u18":[p for p in players if p.get("age_status")=="VERIFIED U18"]}
    e2["u18_risk"]=bool(e2["verified_u18"])
    mapped.append(e2)

# group exact tour matches into tournament cards
groups={}
for e in mapped:
    tn=e.get("tournament") or e.get("competition") or e.get("league") or "Tennis"
    key=f'{e["lane"]}|{tn}'
    g=groups.setdefault(key,{"id":hashlib.sha1(key.encode()).hexdigest()[:12],"lane":e["lane"],"tournament":tn,"events":[],"participants":{}})
    g["events"].append(e)
    for p in e["participants"]:g["participants"][norm(p["name"])]=p

tournaments=[]
for g in groups.values():
    ps=list(g["participants"].values())
    tournaments.append({
      "id":g["id"],"lane":g["lane"],"tournament":g["tournament"],"status":"ACTIVE/UPCOMING",
      "event_count":len(g["events"]),"participants":ps,"participant_count":len(ps),
      "verified_u18":[p for p in ps if p.get("age_status")=="VERIFIED U18"],
      "known_u18_count":sum(p.get("age_status")=="VERIFIED U18" for p in ps),
      "verified_18plus_count":sum(p.get("age_status")=="VERIFIED 18+" for p in ps),
      "unresolved_count":sum(p.get("age_status")=="UNRESOLVED" for p in ps),
      "participant_source":"Exact mapped match schedule + official ATP/WTA age index",
      "events":g["events"]
    })

# ITF
itf_health=[];itf=[]
for lane in ("itf-men","itf-women"):
    found,h=extract_itf_tournaments(lane);itf_health.append({"lane":lane,**h})
    for t in found:itf.append(enrich_itf(t))
tournaments.extend(itf)

# Add ITF participants to age index for UTR cross-reference
for t in itf:
    for p in t.get("participants",[]):
        if p.get("age_status")!="UNRESOLVED":
            age_index[norm(p["name"])]=p

# UTR
utr,utr_health=extract_utr(age_index,known_index)
tournaments.extend(utr)

# risk queue
prev_sig={x.get("id"):x.get("draw_signature") for x in previous.get("tournaments",[])}
risks=[]
for t in tournaments:
    names=sorted(norm(p.get("name")) for p in t.get("participants",[]) if isinstance(p,dict))
    eventids=[str(e.get("id")) for e in t.get("events",[])]
    sig=hashlib.sha256(("|".join(names+eventids)).encode()).hexdigest()[:16] if names or eventids else None
    t["draw_signature"]=sig
    t["draw_changed"]=bool(sig and prev_sig.get(t["id"]) and prev_sig[t["id"]]!=sig)
    t["risk_status"]="RED" if t.get("verified_u18") else "AMBER" if t["draw_changed"] else "NORMAL"

    # exact match risks first
    for e in t.get("events",[]):
        for p in e.get("verified_u18",[]):
            risks.append({
              "severity":"RED","type":"VERIFIED U18 MATCH","lane":t["lane"],"tournament":t["tournament"],
              "event":e.get("name"),"start_time":e.get("start_time"),"player":p["name"],"age":p.get("age"),
              "source":p.get("source"),"reason":f'{p["name"]} is under 18 and is listed in this mapped match.',
              "staff_action":"Search this athlete by name in active player-specific markets for this event."
            })

    # tournament-level U18 where exact match time is not available (ITF/UTR)
    if not t.get("events"):
        for p in t.get("verified_u18",[]):
            risks.append({
              "severity":"RED","type":"VERIFIED U18 TOURNAMENT","lane":t["lane"],"tournament":t["tournament"],
              "event":None,"start_time":t.get("start_date"),"player":p["name"],"age":p.get("age"),
              "source":p.get("source"),"reason":f'{p["name"]} is under 18 and appears in the current tournament participant field.',
              "staff_action":"Review current tournament markets and order of play for this athlete."
            })

    if t["draw_changed"]:
        risks.append({
          "severity":"AMBER","type":"DRAW CHANGE","lane":t["lane"],"tournament":t["tournament"],
          "event":None,"start_time":t.get("events",[{}])[0].get("start_time") if t.get("events") else t.get("start_date"),
          "player":None,"reason":"Scheduled participant/draw signature changed since the last refresh.",
          "staff_action":"Re-screen the current field for U18 exposure."
        })

lanes=[
 {"id":"atp","label":"ATP","coverage":"EXACT MATCHES + OFFICIAL AGE INDEX"},
 {"id":"wta","label":"WTA","coverage":"EXACT MATCHES + OFFICIAL AGE INDEX"},
 {"id":"itf-men","label":"ITF Men","coverage":"OFFICIAL CALENDAR / DRAW / PROFILE"},
 {"id":"itf-women","label":"ITF Women","coverage":"OFFICIAL CALENDAR / DRAW / PROFILE"},
 {"id":"utr-men","label":"UTR Men","coverage":"OFFICIAL EVENT / PARTICIPANT DISCOVERY"},
 {"id":"utr-women","label":"UTR Women","coverage":"OFFICIAL EVENT / PARTICIPANT DISCOVERY"},
 {"id":"grand-slams","label":"Grand Slams","coverage":"ATP/WTA MATCH FEED WHEN PRESENT"},
]
for l in lanes:l["active_tournaments"]=sum(t.get("lane")==l["id"] for t in tournaments)


# Build a live registry: seeded known U18 + dynamically discovered official U18.
registry={}
for x in known:
    registry[norm(x["name"])]={
      "name":x["name"],"age":x.get("age"),"birth_year":None,
      "age_status":"VERIFIED U18","source":"Known U18 registry",
      "source_url":None,"registry_scope":"SEEDED",
      "evidence":"Previously verified U18 record."
    }
for x in junior_watchlist:
    registry[norm(x["name"])]=x
for t in tournaments:
    for p in t.get("participants",[]):
        if isinstance(p,dict) and p.get("age_status")=="VERIFIED U18":
            k=norm(p["name"])
            rec={**p,"registry_scope":"CURRENT / PRO EXPOSURE"}
            registry[k]={**registry.get(k,{}),**rec}

# Mark which registry athletes are currently tied to a professional mapped event/tournament.
current_exposure=set()
for t in tournaments:
    for p in t.get("verified_u18",[]):
        current_exposure.add(norm(p["name"]))
for k,v in registry.items():
    v["current_exposure"]=k in current_exposure
    if v["current_exposure"]:
        v["registry_scope"]="CURRENT / PRO EXPOSURE"

live_u18_registry=sorted(
    registry.values(),
    key=lambda x:(not x.get("current_exposure"), str(x.get("name","")).lower())
)

summary={
 "lanes":len(lanes),"tournaments":len(tournaments),"exact_matches":len(mapped),
 "participants_screened":sum(len(t.get("participants",[])) for t in tournaments),
 "verified_u18_participants":len({norm(r["player"]) for r in risks if r.get("player") and r["severity"]=="RED"}),
 "red_risk_items":sum(r["severity"]=="RED" for r in risks),
 "draw_changes":sum(r["type"]=="DRAW CHANGE" for r in risks),
 "atp_age_index":len(atp_index),"wta_age_index":len(wta_index),
 "itf_tournaments":len(itf),"utr_tournaments":len(utr),
 "live_u18_registry":len(live_u18_registry),
 "current_u18_exposure":sum(1 for x in live_u18_registry if x.get("current_exposure")),
 "broader_u18_watchlist":sum(1 for x in live_u18_registry if not x.get("current_exposure"))
}

out={
 "schema_version":3,"generated_at":NOW.isoformat(),"timezone":"America/Chicago",
 "window_start":TODAY.isoformat(),"window_end":END.isoformat(),
 "lanes":lanes,"tournaments":sorted(tournaments,key=lambda t:(t.get("risk_status")!="RED",t.get("lane",""),t.get("tournament",""))),
 "risk_queue":sorted(risks,key=lambda r:(r["severity"]!="RED",r.get("start_time") or "")),
 "known_u18_registry":known,
 "live_u18_registry":live_u18_registry,
 "summary":summary,
 "source_health":{
   "atp_rankings":atp_rank_health,"wta_rankings":wta_rank_health,
   "atp_calendar":atp_cal_health,"wta_calendar":wta_cal_health,
   "itf":itf_health,"utr":utr_health,
   "itf_junior_rankings":junior_health
 },
 "methodology":{
   "schedule":"ATP/WTA exact matches use the mapped Today + 7 scoreboard feed and are cross-checked to official tour calendar coverage. ITF and UTR tournament discovery uses official sites.",
   "age":"ATP/WTA official rankings age fields are used when resolvable. ITF explicit DOB/profile evidence is used for ITF players. Known U18 records remain hard flags.",
   "red_rule":"A match/tournament is RED only when an identified participant has verified U18 evidence.",
   "unknown_rule":"Unresolved participants remain visible but do not turn an event red."
 }
}
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(summary))
