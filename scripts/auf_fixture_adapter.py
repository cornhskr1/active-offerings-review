"""AUF's separate 2026 women's A league and men's cup fixture pages."""

import datetime
import hashlib
import re
from zoneinfo import ZoneInfo

from lxml import html


URUGUAY = ZoneInfo("America/Montevideo")
SOURCES = {
    "conmebol-soccer-uruguay-campeonato-femenino-women": {
        "title": "Campeonato Femenino A - AUF",
        "league": "Campeonato Femenino | Women",
    },
    "conmebol-soccer-uruguay-copa-uruguay-men": {
        "title": "Copa AUF Uruguay - AUF",
        "league": "Copa Uruguay | Men",
    },
}


def _phase(heading, source_id):
    """Recognize senior 2026 competitions, not a particular round's row count."""
    if source_id.endswith("-women"):
        pattern = (r"(?:FIXTURE )?(?:Primera|Segunda) Fase - "
                   r"(?:CAMPEONATO (?:APERTURA|CLAUSURA) LPD 2026|"
                   r"(?:FINAL|SERIE (?:PERMANENCIA|CAMPEONATO)) LPD FUTBOL FEMENINO 2026)")
        if re.fullmatch(pattern, heading):
            return False
    else:
        if re.fullmatch(r"(?:FIXTURE )?Primera Fase - (?:AMATEUR AUF|ELIMINATORIA EQUIPOS AMATEUR)", heading):
            return True
        if re.fullmatch(r"(?:FIXTURE )?Primera Fase - GRUPO [1-6]", heading):
            return False
        # Only explicitly professional eliminations are approved. Mixed or
        # amateur knockout rounds need separate participant-scope review.
        if re.fullmatch(r"(?:FIXTURE )?(?:Segunda Fase - FASE II|Tercera Fase - FASE III|Cuarta Fase - FASE IV) ELIM PROF", heading):
            return False
    raise ValueError("AUF competition phases changed: " + heading)


# Official senior 2026 club identities from the October 18 AUF first-phase
# draw. Separate women's links prevent cross-gender and youth substitution.
WOMEN_CLUBS = {
    '/canadian-soccer-club-femenino/': 'Canadian',
    '/ff-danubio/': 'Danubio',
    '/ff-defensor-sporting/': 'Defensor Sporting',
    '/ff-juventud/': 'Juventud',
    '/ff-liverpool/': 'Liverpool',
    '/ff-nacional/': 'Nacional',
    '/ff-san-jacinto-albion/': 'S.J. Albion',
    '/ff-wanderers/': 'Wanderers',
    '/futfem-c-a-penarol/': 'Peñarol',
    '/montevideo-city-torque/': 'Montevideo City Torque',
}
CUP_CLUBS = {
    '/albion-futbol-club/': 'Albion',
    '/boston-river/': 'Boston River',
    '/central-espanol-futbol-club/': 'Central Español',
    '/centro-atletico-fenix/': 'Fénix',
    '/cerro-largo-futbol-club/': 'Cerro Largo',
    '/club-atletico-atenas/': 'Atenas de San Carlos',
    '/club-atletico-cerro/': 'Cerro',
    '/club-atletico-juventud/': 'Juventud',
    '/club-atletico-penarol/': 'Peñarol',
    '/club-atletico-progreso-webauf/': 'Progreso',
    '/club-atletico-rentistas/': 'Rentistas',
    '/club-atletico-river-plate/': 'River Plate',
    '/club-nacional-de-football/': 'Nacional',
    '/club-oriental-de-football-m/': 'Oriental de La Paz',
    '/club-plaza-colonia-de-deportes/': 'Plaza Colonia',
    '/club-sportivo-cerrito/': 'Cerrito',
    '/colon-futbol-club/': 'Colón',
    '/danubio-futbol-club/': 'Danubio',
    '/defensor-sporting-club/': 'Def. Sporting',
    '/deportivo-maldonado-s-a-d/': 'D. Maldonado',
    '/liverpool-futbol-club/': 'Liverpool',
    '/montevideo-city-torque-f11/': 'M.C. Torque',
    '/montevideo-wanderers-futbol-club/': 'Wanderers',
    '/racing-club-de-montevideo/': 'Racing',
}


def _class(name):
    return f'contains(concat(" ",normalize-space(@class)," ")," {name} ")'


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def parse_fixtures(page, source, *, diagnostics=None):
    if diagnostics is not None:
        diagnostics["undated_pairings_held"] = 0
    scope = SOURCES.get(source.get("id"))
    if not scope or source.get("league") != scope["league"] or source.get("catalog_terms") != [scope["league"]]:
        raise ValueError("AUF competition approval scope changed")
    # AUF declares Windows-1252 in its page; the HTTP charset says ISO-8859-1.
    doc = html.fromstring(page.decode("windows-1252") if isinstance(page, bytes) else page)
    if doc.xpath('//title/text()') != [scope["title"]]:
        raise ValueError("AUF competition page identity changed")
    blocks = doc.xpath(f'//*[{_class("cont-fixture_campeonato")}]')
    if not blocks:
        raise ValueError("AUF fixture blocks missing")
    headings = [_text(block, './h3/text()') for block in blocks]
    if len(set(headings)) != len(headings):
        raise ValueError("AUF duplicate phase")
    for heading in headings:
        _phase(heading, source["id"])
    fixture_keys = set()
    match_keys = set()
    events = []
    amateur_held = 0
    published = 0
    for block, heading in zip(blocks, headings):
        amateur = _phase(heading, source["id"])
        rows = block.xpath(f'.//*[{_class("item-fixture")}]')
        if not rows:
            raise ValueError("AUF empty fixture phase")
        if amateur:
            amateur_held += len(rows)
            published += len(rows)
            continue
        for row in rows:
            home_nodes = row.xpath(f'./div[{_class("col")} and not({_class("club2")})][1]/a')
            away_nodes = row.xpath(f'./div[{_class("club2")}]/a')
            if len(home_nodes) != 1 or len(away_nodes) != 1:
                raise ValueError("AUF fixture pairing fields changed")
            home = _text(home_nodes[0], f'.//span[{_class("hidden-xs")}]/text()')
            away = _text(away_nodes[0], f'.//span[{_class("hidden-xs")}]/text()')
            if (not home or not away or home == away
                    or not home_nodes[0].get("href", "").startswith("/")
                    or not away_nodes[0].get("href", "").startswith("/")):
                raise ValueError("AUF fixture clubs changed")
            paths = (home_nodes[0].get("href"), away_nodes[0].get("href"))
            roster = WOMEN_CLUBS if source["id"].endswith("-women") else CUP_CLUBS
            if paths[0] == paths[1] or any(
                    roster.get(path) != name for path, name in zip(paths, (home, away))):
                raise ValueError("AUF senior participant scope changed")
            score = _text(row, f'./div[{_class("resultado")}]/text()')
            if score and not re.fullmatch(r"(?:\(\d+\) )?\d+ - \d+(?: \(\d+\))?", score):
                raise ValueError("AUF fixture result changed")
            published += 1
            stamps = row.xpath(f'.//div[{_class("fecha_estadio")}]/strong/text()')
            # Later rounds are often published before their kickoffs. Never
            # invent a date or turn an undated pairing into a schedule card.
            if not stamps or (len(stamps) == 1 and not stamps[0].strip()):
                if score:
                    raise ValueError("AUF completed fixture kickoff missing")
                if diagnostics is not None:
                    diagnostics["undated_pairings_held"] += 1
                continue
            if len(stamps) != 1:
                raise ValueError("AUF ambiguous fixture kickoff")
            stamp = " ".join(stamps[0].split())
            if not re.fullmatch(r"\d{2}/\d{2}/2026 - \d{2}:\d{2} h", stamp):
                raise ValueError("AUF fixture kickoff format changed")
            local = datetime.datetime.strptime(stamp, "%d/%m/%Y - %H:%M h").replace(tzinfo=URUGUAY)
            venue = _text(row, f'.//div[{_class("fecha_estadio")}]/text()')
            if not venue:
                raise ValueError("AUF fixture venue missing")
            key = (heading, *paths, local.date())
            match_key = (*paths, local.date())
            if key in fixture_keys or match_key in match_keys:
                raise ValueError("AUF duplicate fixture")
            fixture_keys.add(key)
            match_keys.add(match_key)
            if score:
                continue
            start = local.astimezone(datetime.timezone.utc)
            # Phase order can change. Stable identity includes exact club paths,
            # phase and local date, not a positional block index or lossy slug.
            identity = hashlib.sha256("|".join(map(str, key)).encode()).hexdigest()[:20]
            events.append({
                "id": f"auf-{source['id']}-{identity}",
                "source_id": source["id"], "sport": "Soccer", "league": source["league"],
                "region": "Uruguay", "name": f"{away} at {home}",
                "start_time": start.isoformat(timespec="minutes").replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "AUF official fixture",
                "location": venue, "source_endpoint": source["endpoint"],
            })
    return events, published, amateur_held
