"""Minimal official-school iCalendar facts; no descriptions, images or rosters."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
try:
    from publisher_access_policy import require_publisher_access
except ImportError:
    from scripts.publisher_access_policy import require_publisher_access

UTC=timezone.utc
CT=ZoneInfo('America/Chicago')


def instant(value):
    result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None: raise ValueError('Unzoned cache timestamp')
    return result.astimezone(UTC)


def text(value):
    return re.sub(r'\\([nN,;\\])',lambda m:' ' if m[1].lower()=='n' else m[1],value).strip()


def duration(value):
    match=re.fullmatch(r'P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?',value)
    if not match: raise ValueError('Unsupported calendar refresh duration')
    seconds=sum(int(v or 0)*factor for v,factor in zip(match.groups(),(86400,3600,60,1)))
    if seconds<=0: raise ValueError('Invalid calendar refresh duration')
    return seconds


def date_value(params,value):
    """A floating, ambiguous or nonexistent clock never becomes an invented UTC time."""
    if params.get('VALUE')=='DATE' or re.fullmatch(r'\d{8}',value):
        return datetime.strptime(value,'%Y%m%d').date().isoformat(),None,True,False
    raw=datetime.strptime(value.rstrip('Z'),'%Y%m%dT%H%M%S')
    if value.endswith('Z'):
        aware=raw.replace(tzinfo=UTC)
    elif params.get('TZID'):
        try: zone=ZoneInfo(params['TZID'])
        except ZoneInfoNotFoundError: return raw.date().isoformat(),None,False,True
        candidates=[]
        for fold in (0,1):
            candidate=raw.replace(tzinfo=zone,fold=fold)
            if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)==raw:
                candidates.append(candidate.astimezone(UTC))
        if not candidates or len(set(candidates))!=1:
            return raw.date().isoformat(),None,False,True
        aware=candidates[0]
    else:
        return raw.date().isoformat(),None,False,True
    return aware.astimezone(CT).date().isoformat(),aware.astimezone(UTC).isoformat(),False,False


def parse_calendar(body,source,season_id):
    if len(body)>2_000_000: raise ValueError('Calendar exceeds bounded input size')
    lines=re.sub(r'\r?\n[ \t]','',body).splitlines()
    if 'BEGIN:VCALENDAR' not in lines or 'END:VCALENDAR' not in lines:
        raise ValueError('Not a complete iCalendar document')
    rows=[];excluded=0;stack=[];props=None;ttl=int(source.get('minimum_poll_seconds',21600));calendar_name=None
    for line in lines:
        if line.startswith('BEGIN:'):
            component=line[6:];stack.append(component)
            if component=='VEVENT':
                if props is not None: raise ValueError('Nested event')
                props={}
            continue
        if line.startswith('END:'):
            component=line[4:]
            if not stack or stack[-1]!=component: raise ValueError('Unbalanced calendar component')
            if component=='VEVENT':
                row=parse_event(props,source,season_id)
                if row is not None:rows.append(row)
                else:excluded+=1
                props=None
            stack.pop();continue
        if ':' not in line: continue
        left,value=line.split(':',1);parts=left.split(';');key=parts[0].upper()
        params=dict(piece.split('=',1) for piece in parts[1:] if '=' in piece)
        params={k.upper():v.strip('"') for k,v in params.items()}
        if stack==['VCALENDAR']:
            if key in ('REFRESH-INTERVAL','X-PUBLISHED-TTL'):ttl=max(ttl,duration(value))
            if key in ('X-WR-CALNAME','NAME'):calendar_name=text(value)
        if props is not None and stack[-1]=='VEVENT':
            if key in ('RRULE','RDATE','EXDATE','RECURRENCE-ID'): raise ValueError('Recurring calendar requires explicit review')
            if key in ('UID','DTSTART','DTEND','SUMMARY','LOCATION','STATUS','SEQUENCE','DTSTAMP','LAST-MODIFIED'):
                if key in props: raise ValueError('Duplicate event property')
                props[key]=(params,value)
    if stack: raise ValueError('Truncated calendar')
    by_uid={}
    for row in rows:
        uid=row['uid']
        if uid in by_uid and by_uid[uid]!=row: raise ValueError('Conflicting duplicate UID')
        by_uid[uid]=row
    return list(by_uid.values()),{'ttl_seconds':ttl,'calendar_name':calendar_name,'season_id':season_id,'excluded_non_school_events':excluded}


# Exact observed publisher-added suffixes, not a generic hyphen splitter.
# Team punctuation remains intact. Retain exhibition only as a normalized fact.
SUMMARY_SUFFIXES = (
    'Powder Blue Out', 'BLUE OUT', 'FAN APPRECIATION', 'STRIPE OUT',
    'INTERNATIONAL BEER & PIZZA DAY', 'Sunday Funday', 'Pink Out',
    'MILITARY APPRECIATION', 'SENIOR DAY | WHITE OUT', 'Exhibition',
    'Exhibition | Free To Attend', 'Free To Attend', 'Go Gold',
    'Girls and Women in Sports Day', 'Alumnae Night | Pennant Flag Giveaway',
    'Pink Out | Rally Towel Giveaway', 'Senior Day', 'Tony Gwynn Legacy',
    'Time changed from 2 p.m. CT', 'Moved to doubleheader', 'Gopher Tournament',
    'Rescheduled from 3/15', 'Rescheduled from 3/27', 'Time changed from 1 p.m. CT',
    'Rescheduled from 4/18', 'Time changed from 6 p.m. CT', 'Postponed from May 8',
    'Bark at the Park (click for information)', 'Game 2', 'Game 3',
)


def clean_opponent(value):
    for suffix in sorted(SUMMARY_SUFFIXES,key=len,reverse=True):
        marker='- '+suffix
        if value.casefold().endswith(marker.casefold()):
            return value[:-len(marker)].strip(), ('exhibition' if suffix.lower().startswith('exhibition') else None)
    return value,None


def parse_event(props,source,season_id):
    def val(key):return props.get(key,({},''))[1]
    uid=text(val('UID'));summary=text(val('SUMMARY'));status=val('STATUS').upper() or 'CONFIRMED'
    if not uid:raise ValueError('Missing calendar UID')
    if status not in ('CONFIRMED','TENTATIVE','CANCELLED'):raise ValueError('Unknown calendar status')
    match=re.fullmatch(source['summary_pattern'],summary,re.I)
    if not match:
        # Huskers tournament calendars can explicitly list two other schools.
        # Exclude only a structurally recognized match that does not name Nebraska.
        if source.get('discovery_kind')=='wmt-rolling':
            other=re.fullmatch(re.escape(source['sport'])+r' -\s+(?P<a>.+?) (?:vs\.?|at) (?P<b>.+)',summary,re.I)
            if other and all(not re.search(r'\bNebraska\b',v,re.I) for v in other.groupdict().values()):return None
        raise ValueError('Calendar summary does not match exact school/program scope')
    if match.groupdict().get('cancelled'):status='CANCELLED'
    elif status!='CANCELLED' and (match.groupdict().get('result') or '').upper() in ('W','L','T'):status='COMPLETED'
    opponent,event_type=clean_opponent(match.groupdict().get('opponent','').strip())
    if not opponent:raise ValueError('Missing opponent')
    if 'DTSTART' not in props:raise ValueError('Missing calendar start date')
    day,start,date_only,time_unknown=date_value(*props['DTSTART'])
    sequence=int(val('SEQUENCE') or 0)
    if sequence<0:raise ValueError('Invalid calendar sequence')
    site=(match.groupdict().get('site') or '').lower().rstrip('.')
    row={'id':source['id']+':'+hashlib.sha256(uid.encode()).hexdigest()[:20],
         'uid':uid,'source_id':source['id'],'school_id':source['school_id'],'school':source['school'],
         'sport_id':source['sport_id'],'sport':source['sport'],'season_id':season_id,
         'opponent':opponent,'date':day,'start_time':start,'date_only':date_only,'time_unknown':time_unknown,
         'time':instant(start).astimezone(CT).strftime('%-I:%M %p')+' CT' if start else 'TBA',
         'site':'AWAY' if site in ('at','@') else 'UNKNOWN',
         'location':text(val('LOCATION')) or None,'status':status,'sequence':sequence,
         'source_url':source['schedule_url'],'calendar_url':source['calendar_url'],'source':source['schedule_url']}
    if event_type:row['event_type']=event_type
    if val('LAST-MODIFIED') or val('DTSTAMP'):
        modified=val('LAST-MODIFIED') or val('DTSTAMP')
        if modified.endswith('Z'):
            row['provider_updated_at']=datetime.strptime(modified,'%Y%m%dT%H%M%SZ').replace(tzinfo=UTC).isoformat()
    return row


def discover_calendar(page,source):
    """Read only official offered-calendar routing metadata, never schedule games."""
    try:
        from official_ncaa_team_schedule import _nodes
    except ImportError:
        from scripts.official_ncaa_team_schedule import _nodes
    nodes,resolve=_nodes(page)
    sports=[];seasons=[]
    for index,node in enumerate(nodes):
        if not isinstance(node,dict) or 'scheduleId' not in node:continue
        try:row=resolve(index)
        except ValueError:continue
        if (row.get('id')==source['publisher_sport_id'] and row.get('title')==source['publisher_sport_title']
                and row.get('gender')==source['publisher_gender']):sports.append(row)
        if row.get('isCurrent') is True and row.get('globalSportNameSlug')==source['sport_slug']:seasons.append(row)
    if len(sports)!=1 or len(seasons)!=1:raise ValueError('Current official calendar routing is ambiguous')
    sport,season=sports[0],seasons[0]
    sid=season.get('scheduleId')
    if type(sid) is not int or sid<=0 or sport.get('scheduleId')!=sid:
        raise ValueError('Current calendar sport/season disagree')
    if not season.get('seasonTitle') or type(season.get('seasonId')) is not int:
        raise ValueError('Missing exact season identity')
    host=urlsplit(source['schedule_url']).netloc
    return (f'https://{host}/api/v2/Calendar/subscribe?type=ics&sportId={source["publisher_sport_id"]}&scheduleId={sid}&downloadFile=false',
            f'{season["seasonId"]}:{sid}:{season["seasonTitle"]}')


def fetch_text(url,get):
    # No redirect following: a changed destination requires fresh source review.
    require_publisher_access(url)
    response=get(url,timeout=35,allow_redirects=False)
    if response.status_code!=200:raise ValueError(f'Official calendar request returned HTTP {response.status_code}')
    if len(response.text)>2_000_000:raise ValueError('Official source exceeds bounded input size')
    return response.text


def collect_school_calendar(source,previous_cache,now,get):
    """Atomic last-good snapshots with literal publisher TTL and explicit stale rows."""
    now=instant(now)
    previous=deepcopy(previous_cache or {})
    base={k:source[k] for k in ('id','school','sport')}
    old=previous.get('events',[])
    if previous.get('source_id') not in (None,source['id']):raise ValueError('Cache belongs to another source')
    try:
        if previous.get('retry_after') and now<instant(previous['retry_after']):
            stale=[{**row,'source_stale':True,'stale_reason':'Official calendar refresh failed; last-good facts retained'} for row in old]
            return {'events':stale,'source_status':{**base,'ok':False,'status':'stale' if old else 'unavailable',
                    'reason':previous.get('last_error','Refresh retry interval has not elapsed'),
                    'fetched_at':previous.get('fetched_at'),'next_fetch_at':previous['retry_after'],
                    'season_id':previous.get('season_id'),'retained_stale_count':len(stale)},'cache':previous}
        if previous.get('next_fetch_at') and now<instant(previous['next_fetch_at']):
            status={**base,'ok':True,'status':'cached','reason':'Publisher refresh interval has not elapsed',
                    'fetched_at':previous.get('fetched_at'),'next_fetch_at':previous['next_fetch_at'],
                    'season_id':previous.get('season_id'),'calendar_url':previous.get('calendar_url'),
                    'event_count':sum(not row.get('source_stale') and row.get('status')!='REMOVED' for row in old),
                    'retained_stale_count':sum(bool(row.get('source_stale')) for row in old)}
            return {'events':old,'source_status':status,'cache':previous}
        resolved=dict(source)
        if source['discovery_kind']=='sidearm-current':
            resolved['calendar_url'],season=discover_calendar(fetch_text(source['schedule_url'],get),source)
        elif source['discovery_kind']=='wmt-rolling':season='rolling-subscription'
        else:raise ValueError('Unsupported official calendar routing')
        rows,meta=parse_calendar(fetch_text(resolved['calendar_url'],get),resolved,season)
        if not rows:raise ValueError('Empty calendar is not verified offseason; retaining last good')
        current={row['uid']:row for row in rows};removed=[];carried=[]
        for prior in old:
            same_season=prior.get('season_id',previous.get('season_id'))==season
            uid=prior['uid']
            if uid in current:
                if current[uid]['sequence']<prior.get('sequence',0):raise ValueError('Calendar sequence regressed')
            elif same_season:
                removed.append(uid)
                carried.append({**prior,'status':'REMOVED','source_stale':True,'removal_observed_at':now.isoformat(),
                                'removal_reason':'UID absent from validated same-season calendar; cancellation not asserted'})
            elif prior.get('date','')>=now.astimezone(CT).date().isoformat():
                carried.append({**prior,'source_stale':True,'stale_reason':'Prior season no longer current; not reconfirmed'})
        rows+=carried
        stamp=now.isoformat();next_at=(now+timedelta(seconds=meta['ttl_seconds'])).isoformat()
        cache={'source_id':source['id'],'season_id':season,'calendar_url':resolved['calendar_url'],
               'events':rows,'fetched_at':stamp,'next_fetch_at':next_at,'ttl_seconds':meta['ttl_seconds']}
        status={**base,'ok':True,'status':'current','reason':'Official calendar snapshot; not a real-time guarantee',
                'fetched_at':stamp,'next_fetch_at':next_at,'season_id':season,'removed_uids':removed,
                'excluded_non_school_events':meta['excluded_non_school_events'],'retained_stale_count':len(carried),'event_count':len(current),'calendar_url':resolved['calendar_url']}
        return {'events':rows,'source_status':status,'cache':cache}
    except Exception as exc:
        # Failed attempts also honor the last known publisher interval. Preserve
        # last-good fetched_at/events; only attempt metadata changes.
        previous['source_id']=source['id']
        previous['last_error']=str(exc)
        previous['retry_after']=(now+timedelta(seconds=max(int(source.get('minimum_poll_seconds',21600)),int(previous.get('ttl_seconds',0))))).isoformat()
        stale=[{**row,'source_stale':True,'stale_reason':'Official calendar refresh failed; last-good facts retained'} for row in old]
        status={**base,'ok':False,'status':'stale' if old else 'unavailable','reason':str(exc),
                'fetched_at':previous.get('fetched_at'),'next_fetch_at':previous['retry_after'],
                'season_id':previous.get('season_id'),'retained_stale_count':len(stale)}
        return {'events':stale,'source_status':status,'cache':previous}
