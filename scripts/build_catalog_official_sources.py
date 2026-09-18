#!/usr/bin/env python3
"""Build the catalog's official-source link registry.

Official competition URLs already researched for schedule coverage are reused when
they are first-party. Entries without a dedicated competition page fall back to
the official governing-body site. Internal approval-rule cards are not linkable.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

THIRD_PARTY_DOMAINS = {
    "espn.com",
    "www.espn.com",
    "site.api.espn.com",
}

NON_ENTITY_GROUPS = {
    "Approved Bout-Level Authorities",
    "Independently Sufficient Bout Oversight",
    "Geographic Limitation",
    "Apply Separately to Every Bout",
    "Professional Sanctioned Events Only",
}

BODY_URL_OVERRIDES = {
    "Australian Football League (AFL) Commission": "https://www.afl.com.au/",
    "Federal International Basketball Association (FIBA)": "https://www.fiba.basketball/",
    "FIBA Africa": "https://www.fiba.basketball/en/regions/africa",
    "FIBA Americas": "https://www.fiba.basketball/en/regions/americas",
    "FIBA Asia": "https://www.fiba.basketball/en/regions/asia",
    "FIBA Europe": "https://www.fiba.basketball/en/regions/europe",
    "FIBA Oceania": "https://www.fiba.basketball/en/regions/oceania",
    "Asociación de Clubes de Básquetbol (AdC)": "https://www.laliganacional.com.ar/",
    "Basketball Australia": "https://www.australia.basketball/",
    "Brazilian Basketball Confederation (CBB)": "https://www.cbb.com.br/",
    "Canada Basketball (CB)": "https://www.basketball.ca/",
    "Danish Basketball Association (DBBF)": "https://basket.dk/",
    "Ligue Nationale de Basket (LNB)": "https://www.lnb.fr/",
    "German Basketball Federation (DBB)": "https://www.basketball-bund.de/",
    "Hellenic Basketball Federation (HBF)": "https://www.basket.gr/",
    "Israel Basketball Association (IBA)": "https://ibba.co.il/",
    "Italian Basketball Federation (FIP)": "https://fip.it/",
    "Lithuanian Basketball Federation (LKF)": "https://ltu.basketball/",
    "The Mexican Basketball Sports Association (ADEMEBA)": "https://ademeba.com.mx/",
    "Games and Amusements Board (GAB)": "https://www.gab.gov.ph/",
    "Polish Basketball Federation (PZKosz)": "https://pzkosz.pl/",
    "Basketball Federation of Serbia (KSS)": "https://kss.rs/",
    "Korea Basketball Association (KBA)": "https://www.koreabasketball.or.kr/",
    "Euroleague Basketball": "https://www.euroleaguebasketball.net/",
    "Asociación de Clubs de Baloncesto (ACB)": "https://www.acb.com/",
    "Swedish Basketball Federation (SBBF)": "https://www.basket.se/",
    "Swiss Basketball Federation (FBS)": "https://swiss.basketball/",
    "Turkish Basketball Federation (TBF)": "https://www.tbf.org.tr/",
    "National Basketball Association (NBA)": "https://www.nba.com/",
    "Women’s National Basketball Association (WNBA)": "https://www.wnba.com/",
    "TBT Enterprises, LLC": "https://thetournament.com/",
    "Unrivaled Basketball": "https://www.unrivaled.basketball/",
    "BIG3": "https://big3.com/",
    "Professional Baseball League of the Dominican Republic (LIDOM)": "https://lidom.com/",
    "Nippon Professional Baseball (NPB) Organization": "https://npb.jp/",
    "Korean Baseball Organization (KBO)": "https://www.koreabaseball.com/",
    "Liga Mexicana de Béisbol (LMB)": "https://www.lmb.com.mx/",
    "Liga Mexicana del Pacífico (LMP)": "https://www.lmp.mx/",
    "World Baseball Softball Confederation (WBSC)": "https://www.wbsc.org/",
    "Major League Baseball (MLB)": "https://www.mlb.com/",
    "Professional Women’s Hockey League (PWHL)": "https://www.thepwhl.com/",
    "National Hockey League (NHL)": "https://www.nhl.com/",
    "ICE Hockey League": "https://ice.hockey/",
    "Czech Ice Hockey Association": "https://www.ceskyhokej.cz/",
    "Finnish Ice Hockey Association": "https://www.finhockey.fi/",
    "Deutsche Eishockey Liga (DEL)": "https://www.penny-del.org/",
    "Slovak Ice Hockey Federation": "https://www.hockeyslovakia.sk/",
    "Swedish Ice Hockey Association": "https://www.swehockey.se/",
    "Swiss Ice Hockey Federation": "https://www.sihf.ch/",
    "Champions Hockey League (CHL)": "https://www.championshockeyleague.com/",
    "Fédération Internationale de Motocyclisme (FIM)": "https://www.fim-moto.com/",
    "National Hot Rod Association (NHRA)": "https://www.nhra.com/",
    "SCORE International": "https://score-international.com/",
    "Superstar Racing Experience (SRX)": "https://www.srxracing.com/",
    "United States Auto Club (USAC)": "https://www.usacracing.com/",
    "Fédération Internationale de Football Association (FIFA)": "https://www.fifa.com/",
    "Asian Football Confederation (AFC)": "https://www.the-afc.com/",
    "Confederation of African Football (CAF)": "https://www.cafonline.com/",
    "Confederation of North, Central America and Caribbean Association Football (CONCACAF)": "https://www.concacaf.com/",
    "Confederación Sudamericana de Fútbol (CONMEBOL)": "https://www.conmebol.com/",
    "Oceania Football Confederation (OFC)": "https://www.oceaniafootball.com/",
    "Union of European Football Associations (UEFA)": "https://www.uefa.com/",
    "Union of European Football Associations (UEFA) / Confederación Sudamericana de Fútbol (CONMEBOL)": "https://www.uefa.com/finalissima/",
    "Colombian Football Federation (FCF)": "https://fcf.com.co/",
    "Ecuadorian Football Federation (FEF)": "https://www.fef.ec/",
    "Professional Football League (LFP)": "https://www.lfp.fr/",
    "Professional Women’s Football League (LFFP)": "https://arkema-premiereligue.fr/",
    "Lega Serie A": "https://www.legaseriea.it/",
    "Lega Nazionale Professionisti Serie B (LNPB)": "https://www.legab.it/",
    "Mexican Football Federation (FMF)": "https://fmf.mx/",
    "New Zealand Football": "https://www.nzfootball.co.nz/",
    "Liga Portugal": "https://www.ligaportugal.pt/",
    "LaLiga": "https://www.laliga.com/",
    "Liga Profesional de Fútbol Femenino (Liga F)": "https://ligaf.es/",
    "United States Soccer Federation (USSF)": "https://www.ussoccer.com/",
    "Cricket Australia (CA)": "https://www.cricket.com.au/",
    "England and Wales Cricket Board": "https://www.ecb.co.uk/",
    "Board for Control for Cricket in India": "https://www.bcci.tv/",
    "International Cricket Council": "https://www.icc-cricket.com/",
    "Union Cycliste Internationale (UCI)": "https://www.uci.org/",
    "Championship Darts Corporation (CDC)": "https://champdarts.com/",
    "Darts Regulation Authority (DRA)": "https://www.thedra.co.uk/",
    "Riot Games — League of Legends": "https://lolesports.com/",
    "Riot Games — VALORANT": "https://valorantesports.com/",
    "Valve — Dota 2": "https://www.dota2.com/",
    "Valve — Counter-Strike 2": "https://www.counter-strike.net/",
    "Ubisoft — Rainbow Six": "https://www.ubisoft.com/en-us/esports/rainbow-six/siege",
    "eAdriatic / eJadranskaLiga — Basketball Simulations": "https://eadriaticleague.com/",
    "Activision — Call of Duty": "https://www.callofdutyleague.com/",
    "Psyonix — Rocket League": "https://www.rocketleague.com/",
    "Indoor Football League (IFL)": "https://goifl.com/",
    "National Football League (NFL)": "https://www.nfl.com/",
    "Canadian Football League (CFL)": "https://www.cfl.ca/",
    "United Football League (UFL)": "https://www.theufl.com/",
    "Professional Golfers Association of Australia (PGA of Australia)": "https://pga.org.au/",
    "European Tour Group": "https://www.europeantour.com/",
    "The R&A": "https://www.randa.org/",
    "Japan Golf Tour Organization (JGTO)": "https://www.jgto.org/en",
    "Asian Tour": "https://asiantour.com/",
    "Sunshine Tour": "https://sunshinetour.com/",
    "Augusta National Golf Club": "https://www.masters.com/",
    "Professional Golfers’ Association of America (PGA of America)": "https://www.pga.com/",
    "Ladies European Tour (LET)": "https://ladieseuropeantour.com/",
    "Tomorrow’s Golf League (TGL)": "https://tglgolf.com/",
    "United States Golf Association (USGA)": "https://www.usga.org/",
    "National Collegiate Athletic Association": "https://www.ncaa.com/",
    "Comisión Sancionadora de Artes Marciales Mixtas de México": "https://luxfightleague.com/",
    "Lights Out Xtreme Fighting": "https://lightsoutxf.com/",
    "Global Association of Mixed Martial Arts (GAMMA)": "https://gamma-sport.org/",
    "Glory Sports International": "https://glorykickboxing.com/",
    "State Athletic Commission": "https://www.abcboxing.com/commission-directory/",
    "Professional Fighters League (PFL)": "https://pflmma.com/",
    "Ultimate Fighting Championship": "https://www.ufc.com/",
    "USA Rugby": "https://usa.rugby/",
    "Badminton World Federation (BWF)": "https://bwfbadminton.com/",
    "International Basketball Federation (FIBA)": "https://www.fiba.basketball/",
    "International Canoe Federation (ICF)": "https://paddleworldwide.com/",
    "International Cricket Council (ICC)": "https://www.icc-cricket.com/",
    "International Federation for Equestrian Sports (FEI)": "https://www.fei.org/",
    "International Federation of American Football (IFAF)": "https://americanfootball.sport/",
    "International Federation of Sport Climbing (IFSC)": "https://www.worldclimbing.com/",
    "International Fencing Federation (FIE)": "https://fie.org/",
    "International Golf Federation (IGF)": "https://www.igfgolf.org/",
    "International Gymnastics Federation (FIG)": "https://www.gymnastics.sport/",
    "International Handball Federation (IHF)": "https://www.ihf.info/",
    "International Hockey Federation (FIH)": "https://www.fih.hockey/",
    "International Judo Federation (IJF)": "https://www.ijf.org/",
    "International Modern Pentathlon Union (UIPM)": "https://www.uipmworld.org/",
    "International Shooting Sport Federation (ISSF)": "https://www.issf-sports.org/",
    "International Surfing Association (ISA)": "https://isasurf.org/",
    "International Weightlifting Federation (IWF)": "https://iwf.sport/",
    "United World Wrestling (UWW)": "https://uww.org/",
    "World Aquatics": "https://www.worldaquatics.com/",
    "World Archery": "https://www.worldarchery.sport/",
    "World Athletics": "https://worldathletics.org/",
    "World Boxing": "https://worldboxing.org/",
    "World Lacrosse": "https://worldlacrosse.sport/",
    "World Rowing": "https://worldrowing.com/",
    "World Sailing": "https://www.sailing.org/",
    "World Skate": "https://www.worldskate.org/",
    "World Squash Federation (WSF)": "https://www.worldsquash.org/",
    "World Taekwondo (WT)": "https://www.worldtaekwondo.org/",
    "World Triathlon": "https://triathlon.org/",
    "International Biathlon Union (IBU)": "https://www.biathlonworld.com/",
    "International Bobsleigh and Skeleton Federation (IBSF)": "https://www.ibsf.org/",
    "International Ice Hockey Federation (IIHF)": "https://www.iihf.com/",
    "International Luge Federation (FIL)": "https://www.fil-luge.org/",
    "International Skating Union (ISU)": "https://www.isu.org/",
    "International Ski Mountaineering Federation (ISMF)": "https://ismf-ski.com/",
    "International Ski and Snowboard Federation (FIS)": "https://www.fis-ski.com/",
    "World Curling Federation (WCF)": "https://worldcurling.org/",
}

EVENT_URL_OVERRIDES = {
    "boxing-ibf": "https://www.ibf-usba-boxing.com/",
    "boxing-wba": "https://www.wbaboxing.com/",
    "boxing-wbc": "https://wbcboxing.com/",
    "boxing-wbo": "https://wboboxing.com/",
    "boxing-bbbofc": "https://bbbofc.com/",
    "boxing-abccs": "https://www.abcboxing.com/",
    "boxing-state-commissions": "https://www.abcboxing.com/commission-directory/",
    "boxing-mvp": "https://www.mvppromotions.com/",
    "boxing-bkfc": "https://www.bkfc.com/",
    "combat-lux": "https://luxfightleague.com/",
    "combat-lxf": "https://lightsoutxf.com/",
    "combat-one": "https://www.onefc.com/",
    "combat-glory": "https://glorykickboxing.com/",
    "combat-mvp": "https://www.mvppromotions.com/",
    "combat-pfl-pro": "https://pflmma.com/",
    "combat-pfl-champions": "https://pflmma.com/",
    "combat-pfl-europe": "https://pflmma.com/",
    "combat-pfl-mena": "https://pflmma.com/",
    "combat-pfl-africa": "https://pflmma.com/",
    "combat-road-ufc": "https://www.ufc.com/",
    "combat-ufc": "https://www.ufc.com/",
    "combat-dwcs": "https://www.ufc.com/dwcs",
}

NOT_APPLICABLE_EVENT_KEYS = {
    "boxing-bout-level-rule",
    "combat-event-rule",
}


def first_party(url: str | None) -> bool:
    if not url:
        return False
    return urlparse(url).netloc.lower() not in THIRD_PARTY_DOMAINS


def load_schedule_sources() -> dict[str, dict]:
    paths = [DATA / "global-schedule-sources.json", *sorted(DATA.glob("soccer-*-sources.json"))]
    sources: dict[str, dict] = {}
    for path in paths:
        payload = json.loads(path.read_text())
        for source in payload.get("sources", []):
            sources[source["id"]] = source
    return sources


def source_for_event(event: dict, sources: dict[str, dict]) -> dict:
    return sources.get(event.get("source_id") or event.get("key"), {})


def has_season_mapping(event: dict) -> bool:
    return bool(
        event.get("nonseasonal")
        or event.get("season_status")
        or (event.get("season_start") and event.get("season_end"))
        or (event.get("season_start_date") and event.get("season_end_date"))
    )


def validate_season_map(season_map: dict) -> None:
    """Reject duplicate keys and stale standard summary counts."""
    seen: set[str] = set()
    for sport in season_map.get("sports", []):
        events = [event for group in sport.get("groups", []) for event in group.get("events", [])]
        for event in events:
            key = event["key"]
            if key in seen:
                raise ValueError(f"Duplicate catalog event key: {key}")
            seen.add(key)

        match = re.fullmatch(
            r"(\d+) approved (.+?) · (\d+) season mapped",
            sport.get("summary_label", ""),
        )
        if not match:
            continue
        expected = (len(events), sum(has_season_mapping(event) for event in events))
        configured = (int(match.group(1)), int(match.group(3)))
        if configured != expected:
            raise ValueError(
                f"Stale {sport['sport']} summary counts: configured={configured}, actual={expected}"
            )


def main() -> None:
    season_map = json.loads((DATA / "catalog-season-map.json").read_text())
    validate_season_map(season_map)
    schedule_sources = load_schedule_sources()
    body_rows: dict[str, dict] = {}
    event_rows: list[dict] = []

    for sport in season_map.get("sports", []):
        for group in sport.get("groups", []):
            body = group.get("governing_body", "")
            candidate_urls = []
            for event in group.get("events", []):
                url = source_for_event(event, schedule_sources).get("official_schedule_url")
                if first_party(url):
                    candidate_urls.append(url)

            body_url = BODY_URL_OVERRIDES.get(body)
            body_basis = "verified-override" if body_url else None
            if not body_url and candidate_urls and body not in NON_ENTITY_GROUPS:
                body_url = Counter(candidate_urls).most_common(1)[0][0]
                body_basis = "official-competition-source"

            if body and body not in NON_ENTITY_GROUPS:
                body_rows.setdefault(body, {
                    "name": body,
                    "official_url": body_url,
                    "status": "verified" if body_url else "pending",
                    "basis": body_basis or "unresolved",
                    "last_verified": str(date.today()),
                })

            for event in group.get("events", []):
                key = event["key"]
                source_url = source_for_event(event, schedule_sources).get("official_schedule_url")
                dedicated_url = EVENT_URL_OVERRIDES.get(key)
                if not dedicated_url and first_party(source_url):
                    dedicated_url = source_url

                if key in NOT_APPLICABLE_EVENT_KEYS:
                    official_url = None
                    status = "not-applicable"
                    basis = "internal-approval-rule"
                elif dedicated_url:
                    official_url = dedicated_url
                    status = "verified"
                    basis = "official-competition-source"
                elif body_url:
                    official_url = body_url
                    status = "verified"
                    basis = "governing-body-fallback"
                else:
                    official_url = None
                    status = "pending"
                    basis = "unresolved"

                event_rows.append({
                    "key": key,
                    "sport": sport["sport"],
                    "catalog_event": event.get("catalog_event"),
                    "governing_body": body or None,
                    "official_url": official_url,
                    "status": status,
                    "basis": basis,
                    "last_verified": str(date.today()),
                })

        if sport.get("sport") == "Olympics":
            for edition in sport.get("editions", []):
                rows = [*edition.get("crosswalk", []), *edition.get("approved_not_scheduled", [])]
                for row in rows:
                    body = row.get("governing_body")
                    if not body:
                        continue
                    body_url = BODY_URL_OVERRIDES.get(body)
                    body_rows.setdefault(body, {
                        "name": body,
                        "official_url": body_url,
                        "status": "verified" if body_url else "pending",
                        "basis": "verified-override" if body_url else "unresolved",
                        "last_verified": str(date.today()),
                    })

    bodies = sorted(body_rows.values(), key=lambda row: row["name"].casefold())
    events = sorted(event_rows, key=lambda row: (row["sport"].casefold(), row["catalog_event"].casefold()))
    output = {
        "schema_version": 1,
        "generated_at": f"{date.today()}T00:00:00-05:00",
        "description": "Official governing-body and competition links for approved catalog entries. Link availability does not determine permissibility.",
        "governing_bodies": bodies,
        "events": events,
        "coverage": {
            "governing_bodies_total": len(bodies),
            "governing_bodies_linked": sum(row["status"] == "verified" for row in bodies),
            "events_total": len(events),
            "events_linked": sum(row["status"] == "verified" for row in events),
            "events_not_applicable": sum(row["status"] == "not-applicable" for row in events),
            "events_pending": sum(row["status"] == "pending" for row in events),
        },
    }
    (DATA / "catalog-official-sources.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
