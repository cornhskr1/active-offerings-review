"""Exact MFL 2026/27 FA Cup semifinal publication, never Malaysia Cup."""
import datetime
import re
from zoneinfo import ZoneInfo
from mfl_fixture_adapter import pdf_text, SENIOR_CLUBS

SOURCE_ID = 'soccer-afc-malaysia-malaysia-fa-cup-men'
ARTICLE = 'https://www.malaysianfootballleague.com/Content/Post/Watch/6495'
PDF = 'https://files.malaysianfootballleague.com/wp-content/uploads/2026/10/JADUAL-PIALA-FA-2026-2027-PUSINGAN-SEPARUH-AKHIR-1-2-KEMASKINI-12102026.pdf'
ROW = re.compile(r'^(\d{1,2}) (Oktober|November) (2026), (Jumaat|Ahad) (\d+) (.+?) v (.+?)\s+STADIUM (.+?) (\d{1,2})\.(\d{2}) (AM|PM)$')


def source_config():
    return {'id':SOURCE_ID,'sport':'Soccer','league':'Malaysia FA Cup | Men','region':'Malaysia',
            'source_type':'official-mfl-fa-semifinal-fixtures','coverage_status':'partial',
            'endpoint':ARTICLE,'official_schedule_url':ARTICLE,'catalog_terms':['Malaysia FA Cup | Men'],
            'source_note':'Official October 12 semifinal publication replaces expired quarterfinal coverage. Four named senior-club legs, October 23 and November 8, retained as date-only because the publication does not establish a timezone. Partial published-phase coverage; no final, next edition, participant-age or market eligibility clearance.'}


def parse_fixtures(text, source, now):
    if any(source.get(k)!=v for k,v in source_config().items() if k in ('id','sport','league','region','endpoint','catalog_terms')):
        raise ValueError('MFL FA Cup semifinal catalog identity changed')
    lines=[' '.join(x.split()) for x in text.splitlines() if x.strip()]
    if (lines[0]!='TARIKH NO. PERLAWANAN (PUSINGAN SEPARUH AKHIR) VENUE SEPAK MULA'
            or lines[-1]!='KEMASKINI : 12 OKTOBER 2026'
            or lines[1]!='FA SF (1)' or len(lines)!=8 or lines[4]!='FA SF (2)'):
        raise ValueError('MFL semifinal edition, revision, or complete two-leg layout changed')
    events=[];pairings=[]
    for index,line in enumerate([lines[2],lines[3],lines[5],lines[6]]):
        row=ROW.fullmatch(line)
        if not row:raise ValueError('MFL semifinal named fixture fields changed')
        day,month,year,weekday,number,home,away,venue,hour,minute,meridiem=row.groups()
        home,away=[x.replace('’',"'") for x in (home,away)]
        if home==away or not {home,away}<=SENIOR_CLUBS or int(number)!=25+index:
            raise ValueError('MFL semifinal clubs or fixture identity changed')
        date=datetime.date(int(year),{'Oktober':10,'November':11}[month],int(day))
        if date.weekday()!={'Jumaat':4,'Ahad':6}[weekday]:raise ValueError('MFL fixture weekday contradicts date')
        if not 1<=int(hour)<=12 or not 0<=int(minute)<=59:raise ValueError('MFL printed clock invalid')
        pairings.append((home,away,date))
        events.append({'id':f'mfl-fa-cup-2026-27-{number}','source_id':SOURCE_ID,'sport':'Soccer',
            'league':source['league'],'region':'Malaysia','name':f'{away} at {home}',
            'start_time':date.isoformat(),'date_only':True,'status':'UPCOMING','season_stage':'SEMIFINAL',
            'status_detail':'Official semifinal leg date; printed kickoff has no independently verified timezone. Participant eligibility remains a separate review.',
            'published_kickoff_text':f'{hour}.{minute} {meridiem}','participant_review_required':True,
            'location':'STADIUM '+venue,'source_endpoint':PDF})
    if (len({n for pair in pairings[:2] for n in pair[:2]})!=4
            or {p[:2] for p in pairings[2:]}!={(p[1],p[0]) for p in pairings[:2]}
            or any(p[2]!=datetime.date(2026,10,23) for p in pairings[:2])
            or any(p[2]!=datetime.date(2026,11,8) for p in pairings[2:])):
        raise ValueError('MFL two-leg semifinal pairing/date inventory changed')
    if not isinstance(now,datetime.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('MFL semifinal review timestamp must be timezone-aware')
    today=now.astimezone(ZoneInfo('America/Chicago')).date()
    future=[e for e in events if datetime.date.fromisoformat(e['start_time'])>=today]
    if not future:raise ValueError('MFL semifinal publication has no future dates; not evidence of offseason')
    return future,{'coverage_status':'partial','published_fixtures':4,'published_edition':'2026/27',
        'published_revision':'2026-10-12','published_phase':'SEMIFINAL','future_date_only_fixtures':len(future),
        'timezone_status':'unverified; literal publisher dates retained','review_window_complete':False,
        'coverage_note':'Published semifinal legs only. Final and later editions remain uncovered; schedule is not participant-age or market eligibility clearance.'}


def fetch_fixtures(source, now, get=None):
    if source.get('endpoint')!=ARTICLE:raise ValueError('MFL exact semifinal article changed')
    if get is None:
        import requests
        get=requests.get
    article=get(ARTICLE,timeout=35);article.raise_for_status()
    urls=set(re.findall(r'https://files\.malaysianfootballleague\.com/[^"<>\s]+\.pdf',article.text))
    if urls!={PDF}:raise ValueError('MFL exact semifinal attachment changed')
    response=get(PDF,timeout=35);response.raise_for_status()
    return parse_fixtures(pdf_text(response.content),source,now)
