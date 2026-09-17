#!/usr/bin/env python3
from pathlib import Path
import json, datetime, requests, re, time, html
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA/"global-schedule-sources.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Chicago")
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()
END = TODAY + datetime.timedelta(days=int(CFG.get("window_days",7)))
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

def thesportsdb_json(endpoint, params):
    """Pace and retry the public feed so transient throttling does not erase leagues."""
    time.sleep(2.1)
    last_error = None
    for attempt in range(4):
        try:
            r=requests.get(endpoint,params=params,headers=HEADERS,timeout=18)
            if r.status_code==429:
                retry_after=r.headers.get("Retry-After")
                wait=float(retry_after) if retry_after and retry_after.isdigit() else 3.0*(attempt+1)
                time.sleep(min(wait,12.0))
                last_error=RuntimeError("TheSportsDB rate limit persisted after retry")
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last_error=exc
            if attempt<3:
                time.sleep(2.0*(attempt+1))
    raise last_error or RuntimeError("TheSportsDB request failed")

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
    home=None; away=None; participant_names=[]
    for c in competitors:
        entity=c.get("team") or c.get("athlete") or {}
        name=(
            entity.get("displayName")
            or entity.get("fullName")
            or entity.get("shortDisplayName")
            or entity.get("shortName")
            or entity.get("name")
        )
        if name:
            participant_names.append(name)
        if c.get("homeAway")=="home": home=name
        elif c.get("homeAway")=="away": away=name
    name=ev.get("name") or ev.get("shortName") or "Scheduled event"
    if home and away:
        name=f"{away} at {home}"
    elif len(participant_names)>=2:
        name=f"{participant_names[0]} vs {participant_names[1]}"
    dt=ev.get("date")
    status,detail=event_status(ev)

    season_type=(
        (ev.get("season") or {}).get("type")
        or (comp.get("type") or {}).get("abbreviation")
        or (comp.get("type") or {}).get("name")
        or (comp.get("type") or {}).get("text")
    )
    season_slug=str(season_type or "").upper()
    if season_slug in ("1","PRE","PRESEASON") or "PRESEASON" in season_slug:
        season_stage="PRESEASON"
    elif season_slug in ("2","REG","REGULAR","REGULAR SEASON") or "REGULAR" in season_slug:
        season_stage="REGULAR SEASON"
    elif season_slug in ("3","POST","POSTSEASON","PLAYOFFS") or "POST" in season_slug or "PLAYOFF" in season_slug:
        season_stage="POSTSEASON"
    else:
        season_stage=None

    # NFL 2026 authoritative date-stage fallback for this review system.
    # The source payload has shown inconsistent stage metadata. For the 2026
    # season, use the actual event date as the final scope control.
    if source.get("league")=="NFL" and dt:
        try:
            event_date=datetime.datetime.fromisoformat(str(dt).replace("Z","+00:00")).date()
            if event_date >= datetime.date(2026,9,9):
                season_stage="REGULAR SEASON"
            elif datetime.date(2026,8,1) <= event_date < datetime.date(2026,9,9):
                season_stage="PRESEASON"
        except Exception:
            pass

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
        "season_stage":season_stage,
        "location":location or None,
        "source_endpoint":source["endpoint"]
    }

def parse_thesportsdb_event(source, ev):
    timestamp=ev.get("strTimestamp")
    if timestamp and not str(timestamp).endswith("Z"):
        timestamp=f"{timestamp}Z"
    if not timestamp:
        date=ev.get("dateEvent")
        time=ev.get("strTime") or "12:00:00"
        timestamp=f"{date}T{time}Z" if date else None
    home=ev.get("strHomeTeam")
    away=ev.get("strAwayTeam")
    name=f"{away} at {home}" if home and away else (ev.get("strEvent") or "Scheduled event")
    raw_status=str(ev.get("strStatus") or "").upper()
    status="COMPLETED" if raw_status in ("FT","AET","MATCH FINISHED","FINISHED") else "UPCOMING"
    venue=ev.get("strVenue")
    country=ev.get("strCountry")
    location=" · ".join(x for x in (venue,country) if x) or None
    return {
        "id":str(ev.get("idEvent") or f'{source["id"]}-{timestamp}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":timestamp,
        "status":status,
        "status_detail":ev.get("strStatus") or "Scheduled",
        "season_stage":None,
        "location":location,
        "source_endpoint":source["endpoint"]
    }

def parse_mlbstats_event(source, game):
    teams=game.get("teams") or {}
    home=((teams.get("home") or {}).get("team") or {}).get("name")
    away=((teams.get("away") or {}).get("team") or {}).get("name")
    name=f"{away} at {home}" if home and away else "Scheduled event"
    status_obj=game.get("status") or {}
    abstract=str(status_obj.get("abstractGameState") or "").lower()
    status="COMPLETED" if abstract=="final" else ("LIVE" if abstract=="live" else "UPCOMING")
    venue=(game.get("venue") or {}).get("name")
    return {
        "id":str(game.get("gamePk") or f'{source["id"]}-{game.get("gameDate")}-{name}'),
        "source_id":source["id"],
        "sport":source["sport"],
        "league":source["league"],
        "region":source.get("region"),
        "name":name,
        "start_time":game.get("gameDate"),
        "status":status,
        "status_detail":status_obj.get("detailedState") or "Scheduled",
        "season_stage":None,
        "location":venue,
        "source_endpoint":source["endpoint"]
    }

def plain_html(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def boxing_region(location):
    low=(location or "").lower()
    if any(x in low for x in ("england","scotland","wales","northern ireland","united kingdom")):
        return "United Kingdom"
    us_markers=(
        "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
        "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
        "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
        "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
        "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
        "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
        "virginia","washington","west virginia","wisconsin","wyoming","united states","u.s."
    )
    if any(x in low for x in us_markers):
        return "United States"
    aliases={"mexico":"Mexico","canada":"Canada","japan":"Japan","australia":"Australia","puerto rico":"Puerto Rico"}
    for needle,label in aliases.items():
        if needle in low:
            return label
    return "International"

def boxing_authorities(text):
    checks=[
        (r"\bIBF\b|International Boxing Federation","IBF"),
        (r"\bWBA\b|World Boxing Association","WBA"),
        (r"\bWBC\b|World Boxing Council","WBC"),
        (r"\bWBO\b|World Boxing Organization","WBO"),
        (r"\bBBBofC\b|British Boxing Board of Control","BBBofC"),
        (r"\bBKFC\b|Bare Knuckle Fighting Championship","BKFC"),
        (r"Most Valuable Promotions|\bMVP\b","MVP")
    ]
    return [label for pattern,label in checks if re.search(pattern,text or "",re.I)]

def parse_boxing_rss(source):
    r=requests.get(source["endpoint"],headers=HEADERS,timeout=25)
    r.raise_for_status()
    root=ET.fromstring(r.content)
    ns={"a":"http://www.w3.org/2005/Atom"}
    parsed=[]
    for entry in root.findall("a:entry",ns):
        title=entry.findtext("a:title",default="",namespaces=ns)
        content=entry.findtext("a:content",default="",namespaces=ns)
        year_match=re.search(r"\b(20\d{2})\b",title)
        year=int(year_match.group(1)) if year_match else TODAY.year
        headings=list(re.finditer(r"<(h[23])[^>]*>(.*?)</\1>",content,re.I|re.S))
        current_date=None
        for idx,match in enumerate(headings):
            tag=match.group(1).lower()
            label=plain_html(match.group(2))
            if tag=="h2":
                clean=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",label,flags=re.I)
                clean=re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*","",clean,flags=re.I)
                try:
                    current_date=datetime.datetime.strptime(f"{clean} {year}","%B %d %Y").date()
                except ValueError:
                    current_date=None
                continue
            if tag!="h3" or not current_date or not re.search(r"\b(vs\.?|v\.)\b",label,re.I):
                continue
            if current_date<TODAY or current_date>END:
                continue
            next_start=headings[idx+1].start() if idx+1<len(headings) else len(content)
            raw_context=content[match.end():next_start]
            context=plain_html(raw_context)
            time_match=re.search(r"(\d{1,2}:\d{2})\s*(am|pm)\s*ET",label,re.I)
            clock="12:00 pm"
            if time_match:
                clock=f"{time_match.group(1)} {time_match.group(2).lower()}"
            local=datetime.datetime.strptime(f"{current_date.isoformat()} {clock}","%Y-%m-%d %I:%M %p").replace(tzinfo=ZoneInfo("America/New_York"))
            start_time=local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00","Z")
            fight=re.sub(r"\s*\([^)]*(?:am|pm)\s+ET[^)]*\)\s*$","",label,flags=re.I).strip()
            loc_match=re.search(r"\bFrom\s+(.+?)(?:\.|,\s+for\b)",context,re.I)
            location=loc_match.group(1).strip() if loc_match else None
            first_para_match=re.search(r"<p[^>]*>(.*?)</p>",raw_context,re.I|re.S)
            bout_description=plain_html(first_para_match.group(1)) if first_para_match else ""
            authority_context=f"{label} {bout_description}"
            slug=re.sub(r"[^a-z0-9]+","-",fight.lower()).strip("-")
            parsed.append({
                "id":f'{source["id"]}-{current_date.isoformat()}-{slug}',
                "source_id":source["id"],
                "sport":"Boxing",
                "league":source["league"],
                "region":boxing_region(location),
                "name":fight,
                "start_time":start_time,
                "status":"UPCOMING",
                "status_detail":"Bout-level authority review required",
                "season_stage":None,
                "location":location,
                "reported_authorities":boxing_authorities(authority_context),
                "source_endpoint":source["endpoint"]
            })
    return parsed

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
    if source.get("source_type")=="coverage-gap":
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":True,
            "events":0,
            "note":source.get("source_note") or "Approved in-season league; no dependable complete public schedule adapter is currently available.",
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="boxing-rss":
        try:
            for parsed in parse_boxing_rss(source):
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="thesportsdb":
        try:
            data=thesportsdb_json(source["endpoint"],{"id":source["league_id"]})
            for ev in data.get("events") or []:
                parsed=parse_thesportsdb_event(source,ev)
                if not parsed.get("start_time"):
                    continue
                event_date=datetime.datetime.fromisoformat(parsed["start_time"].replace("Z","+00:00")).astimezone(TZ).date()
                if event_date<TODAY or event_date>END:
                    continue
                key=(parsed["id"],parsed["start_time"])
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="thesportsdb-day":
        for offset in range((END-TODAY).days+1):
            day=TODAY+datetime.timedelta(days=offset)
            try:
                data=thesportsdb_json(source["endpoint"],{"d":day.isoformat(),"s":source.get("sport_query") or source["sport"]})
                for ev in data.get("events") or []:
                    if str(ev.get("idLeague") or "")!=str(source["league_id"]):
                        continue
                    parsed=parse_thesportsdb_event(source,ev)
                    key=(parsed["id"],parsed["start_time"])
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append(parsed)
                    count+=1
            except Exception as e:
                errors.append(f"{day.isoformat()}: {str(e)[:110]}")
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors or count>0,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
    if source.get("source_type")=="mlbstats":
        try:
            params={
                "sportId":source["sport_id"],
                "leagueId":source["league_id"],
                "startDate":TODAY.isoformat(),
                "endDate":END.isoformat(),
                "hydrate":"team,venue"
            }
            r=requests.get(source["endpoint"],params=params,headers=HEADERS,timeout=18)
            r.raise_for_status()
            data=r.json()
            for date_group in data.get("dates") or []:
                for game in date_group.get("games") or []:
                    parsed=parse_mlbstats_event(source,game)
                    key=(parsed["id"],parsed["start_time"])
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append(parsed)
                    count+=1
        except Exception as e:
            errors.append(str(e)[:110])
        source_status.append({
            **source,
            "approved_catalog":True,
            "ok":not errors,
            "events":count,
            "errors":errors[:3],
            "checked_at":NOW_UTC.isoformat()
        })
        continue
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

# Restriction cross-reference.
# Applicability must be event/league specific. A restriction somewhere under
# a sport must NOT automatically flag every scheduled event in that sport.
restrictions=[]
cat_path=DATA/"catalog-live.json"
if cat_path.exists():
    try:
        cat=json.loads(cat_path.read_text(encoding="utf-8"))
        restrictions=cat.get("restrictions",[])
    except Exception:
        pass

def restriction_applies(ev, x):
    text=str(x.get("text") or "").lower()
    esport=str(ev.get("sport") or "").lower()
    league=str(ev.get("league") or "").lower()
    name=str(ev.get("name") or "").lower()
    stage=str(ev.get("season_stage") or "").upper()
    scope_type=str(x.get("scope_type") or "")
    scope_sport=str(x.get("sport") or "").lower()
    hay=f"{league} {name}"

    # General professional/international U18 language is NOT a league-wide
    # schedule restriction. It requires an actual participant-age match.
    if scope_type=="GENERAL_U18_PRO":
        return False

    # NFL event-specific controls. "NFL Draft" must never attach to NFL games.
    if league=="nfl":
        if "draft" in text:
            return "draft" in name

        preseason_rule=("preseason" in text or "pre-season" in text)
        postseason_rule=("postseason" in text or "playoff" in text)
        regular_rule=("regular season" in text)

        if preseason_rule:
            return stage=="PRESEASON"
        if postseason_rule:
            return stage=="POSTSEASON"
        if regular_rule:
            return stage=="REGULAR SEASON"

    # MLB event-specific restrictions.
    if league=="mlb":
        if "draft" in text:
            return "draft" in name
        if "spring training" in text or "preseason" in text or "pre-season" in text:
            return stage=="PRESEASON" or any(k in name for k in ("spring training","preseason","pre-season"))

    # Explicit named special-event restrictions require the named event.
    special_terms=[
        "draft","all-star","home run derby","world baseball classic",
        "preseason","pre-season","spring training"
    ]
    for term in special_terms:
        if term in text:
            return term in hay

    # Restriction tied to an explicitly named league/event.
    if league and league in text:
        return True

    # Sport-level restriction can apply only when it is genuinely sport-wide.
    if scope_sport and scope_sport==esport:
        generic_event_words=["restriction","no proposition wagers","no player proposition wagers","no in-game wagers"]
        if any(g in text for g in generic_event_words) and not any(t in text for t in special_terms):
            # If the text contains a distinct league/event name not present in this
            # event, do not spread it across the entire sport.
            tokens=[t for t in re.findall(r"[a-z0-9]+",text) if len(t)>=5]
            ev_tokens=set(re.findall(r"[a-z0-9]+",hay))
            named=[t for t in tokens if t not in {"restriction","markets","wagers","player","proposition","event","games","close","prior","start","hours","hour"}]
            if named and not any(t in ev_tokens for t in named):
                return False

    return False

for ev in events:
    rel=[]
    for x in restrictions:
        if restriction_applies(ev, x):
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
        "Surfing","Table Tennis"
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
