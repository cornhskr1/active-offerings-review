"""Current official FIBA club-competition reports, without scope/year guessing.

FIBA's public reports index links a directory listing and PDF viewer. The website's
Games page is not an API dependency. We validate the published directory, PDF
edition, geometric columns and complete first-round inventory before emitting
fixtures. A known date without a published time is date-only; bracket placeholders
and undated games are held. World Cup qualifiers are deliberately not in SPECS.
"""

import datetime as dt
import io
import re
from urllib.parse import urlencode

import pdfplumber
import requests

BASE = "https://reports.fiba.basketball"
SPECS = {
    "basketball-womens-euroleague": {
        "path": "2027/EuroLeague Women", "title": "EuroLeague Women 2027",
        "league": "FIBA Women's EuroLeague | Women",
        "catalog_terms": ["FIBA Women's EuroLeague | Women"],
        "period": ("2026-09-23", "2027-04-18"),
        "first_phase": "Regular Season - First Round", "groups": "ABCD",
    },
    "fiba-bcl": {
        "path": "2027/BCL 2027", "title": "Basketball Champions League 2027",
        "league": "Basketball Champions League",
        "catalog_terms": ["Basketball Champions League"],
        "period": ("2026-10-06", "2027-05-16"),
        "first_phase": "Regular Season", "groups": "ABCDEFGH",
    },
}
DATE = re.compile(r"^(MON|TUE|WED|THU|FRI|SAT|SUN) (\d{2}) ([A-Z]{3}) (\d{4})$")
GAME_ID = re.compile(r"(?:[A-Z]-)?\d+")
TEAM_PAIR = re.compile(r"([A-Z][A-Z0-9]{1,8}) vs ([A-Z][A-Z0-9]{1,8})")
CLOCK = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
COLUMNS = ("Date", "Local", "UTC", "Teams", "Location", "Phase", "Game", "Score")


def _spec(source):
    spec = SPECS.get(source.get("id"))
    if (not spec or source.get("sport") != "Basketball"
            or source.get("league") != spec["league"]
            or source.get("catalog_terms") != spec["catalog_terms"]
            or source.get("fiba_report_path") != spec["path"]):
        raise ValueError("FIBA report catalog, division, competition or edition scope changed")
    return spec


def report_url(source):
    spec = _spec(source)
    return BASE + "/api/view.php?" + urlencode({"file": spec["path"] + "/competition-schedule.pdf"})


def _day(text):
    match = DATE.fullmatch(text)
    if not match:
        raise ValueError("FIBA report date is missing its explicit year or weekday")
    result = dt.datetime.strptime(text[4:], "%d %b %Y").date()
    if result.strftime("%a").upper() != match[1]:
        raise ValueError("FIBA report weekday and full calendar date disagree")
    return result


def _read_pdf(content):
    """Read cells by printed column geometry, never PDF stream text order."""
    if not isinstance(content, bytes) or not content.startswith(b"%PDF-"):
        raise ValueError("FIBA reports service did not return a PDF")
    rows, page_texts = [], []
    with pdfplumber.open(io.BytesIO(content)) as document:
        if not 1 <= len(document.pages) <= 30:
            raise ValueError("FIBA report page count changed")
        for page_number, page in enumerate(document.pages, 1):
            words = page.extract_words(x_tolerance=1, y_tolerance=2)
            text = page.extract_text(x_tolerance=1, y_tolerance=2) or ""
            page_texts.append(text)
            # Header names share a row except the two-line Local/Game labels.
            candidates = [w for w in words if w["text"] == "Date" and w["top"] < 180]
            if len(candidates) != 1:
                raise ValueError("FIBA report schedule table header changed")
            header_y = candidates[0]["top"]
            headers = {}
            for name in COLUMNS:
                matches = [w for w in words if w["text"] == name and abs(w["top"] - header_y) < 8]
                if len(matches) != 1:
                    raise ValueError("FIBA report date/local/UTC/table columns changed")
                headers[name] = matches[0]["x0"]
            if list(headers.values()) != sorted(headers.values()):
                raise ValueError("FIBA report column order changed")
            footers = [w for w in words if w["text"] == "Created" and w["top"] > page.height * .8]
            if len(footers) != 1 or not re.search(rf"Page {page_number}/{len(document.pages)}\b", text):
                raise ValueError("FIBA report page sequence or footer changed")
            footer_y = footers[0]["top"]
            anchors = [w for w in words
                       if headers["Game"] - 4 <= w["x0"] < headers["Score"] - 4
                       and header_y + 12 < w["top"] < footer_y - 3
                       and GAME_ID.fullmatch(w["text"])]
            if not anchors:
                raise ValueError("FIBA report contains no recognizable fixture rows")
            for index, anchor in enumerate(anchors):
                lower = anchor["top"] - 2
                upper = anchors[index + 1]["top"] - 2 if index + 1 < len(anchors) else footer_y - 3
                cell_words = [w for w in words if lower <= w["top"] < upper]
                row = {}
                for column_index, name in enumerate(COLUMNS):
                    left = headers[name] - 4
                    right = headers[COLUMNS[column_index + 1]] - 4 if column_index + 1 < len(COLUMNS) else page.width
                    selected = [w for w in cell_words if left <= w["x0"] < right]
                    row[name] = " ".join(w["text"] for w in selected)
                if row["Game"] != anchor["text"]:
                    raise ValueError("FIBA report match number crossed a row boundary")
                rows.append(row)
    return "\n".join(page_texts), rows


def parse_fiba_report_rows(text, rows, source, today, review_end):
    """Pure normalized-table validation, also used by mutation regression tests."""
    spec = _spec(source)
    if not isinstance(today, dt.date) or not isinstance(review_end, dt.date) or today > review_end:
        raise ValueError("Invalid FIBA review window")
    compact = " ".join(text.split())
    start, end = (dt.date.fromisoformat(x) for x in spec["period"])
    expected_period = f"From {start.strftime('%d-%b-%Y')} to {end.strftime('%d-%b-%Y')}"
    if spec["title"] not in compact or expected_period not in compact or "Competition Schedule" not in compact:
        raise ValueError("FIBA report competition title or season dates changed")
    stamps = set(re.findall(r"Created on (\d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}) UTC", text))
    if len(stamps) != 1:
        raise ValueError("FIBA report publication timestamp missing or inconsistent")
    generated = dt.datetime.strptime(stamps.pop(), "%d %b %Y %H:%M").replace(tzinfo=dt.timezone.utc)
    if generated.date() > today:
        raise ValueError("FIBA report publication date is in the future")
    day, events, inventory, first_phase_days = None, [], set(), []
    unresolved, held, published, seen = 0, 0, 0, set()
    for row in rows:
        if set(row) != set(COLUMNS):
            raise ValueError("FIBA report fixture row schema changed")
        if row["Date"]:
            day = _day(row["Date"])
        # A blank-date, blank-time playoff row is NOT dated by the last regular game.
        row_day = day if row["Date"] or row["Local"] or row["UTC"] else None
        if row_day and not start <= row_day <= end:
            raise ValueError("FIBA fixture date left the published competition season")
        phase = " ".join(row["Phase"].split())
        first_phase = re.fullmatch(re.escape(spec["first_phase"]) + r" Group ([A-Z])", phase)
        pair = TEAM_PAIR.fullmatch(row["Teams"])
        if first_phase:
            if first_phase[1] not in spec["groups"] or not re.fullmatch(rf"{first_phase[1]}-(?:[1-9]|1[0-2])", row["Game"]):
                raise ValueError("FIBA first-round group or match number changed")
            if row["Game"] in inventory:
                raise ValueError("Duplicate FIBA first-round match")
            inventory.add(row["Game"])
            if not pair or pair[1] == pair[2] or not row_day:
                raise ValueError("FIBA first-round pairing or explicit date missing")
            first_phase_days.append(row_day)
        if pair and (pair[1] == pair[2] or any(x in {"TBD", "TBC", "TBA"} for x in pair.groups())):
            raise ValueError("FIBA report pairing is not a named pair of teams")
        if not pair or not row_day:
            unresolved += 1
            if row_day and today <= row_day <= review_end:
                held += 1
            continue
        identity = (phase, row["Game"], row_day.isoformat(), row["Teams"])
        if identity in seen:
            raise ValueError("Duplicate FIBA report fixture")
        seen.add(identity)
        published += 1
        local, utc = row["Local"], row["UTC"]
        date_only = local == utc == "TBD"
        if not date_only:
            if not CLOCK.fullmatch(local) or not CLOCK.fullmatch(utc):
                raise ValueError("FIBA report time is invalid, incomplete or no longer explicit UTC")
            local_minutes = int(local[:2]) * 60 + int(local[3:])
            utc_minutes = int(utc[:2]) * 60 + int(utc[3:])
            # These two strictly scoped European club reports publish same-day
            # local/UTC columns. Reject rollover/changed geography instead of
            # guessing a zone or assigning the wrong UTC calendar date.
            if not 0 <= local_minutes - utc_minutes <= 4 * 60:
                raise ValueError("FIBA report UTC date is ambiguous; explicit day evidence required")
        score = row["Score"]
        if score and not re.fullmatch(r"\d+-\d+", score):
            raise ValueError("FIBA report result or match disposition changed")
        if score or not today <= row_day <= review_end:
            continue
        stage = "REGULAR" if phase.startswith("Regular Season") else phase
        event = {
            "id": f"{source['id']}-2027-{row_day.isoformat()}-{row['Game']}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": row["Teams"],
            "start_time": row_day.isoformat() if date_only else f"{row_day.isoformat()}T{utc}:00Z",
            "status": "UPCOMING", "status_detail": f"FIBA official report: {phase}" + ("; time TBD" if date_only else "; published UTC"),
            "season_stage": stage, "location": row["Location"] or None,
            "source_endpoint": report_url(source), "source_published_at": generated.isoformat().replace("+00:00", "Z"),
        }
        if date_only:
            event["date_only"] = True
        events.append(event)
    expected = {f"{group}-{number}" for group in spec["groups"] for number in range(1, 13)}
    if inventory != expected:
        raise ValueError("FIBA current regular-season first-round inventory is incomplete")
    # The complete group inventory proves this phase, not later playoff slots.
    # A separately named final must not stretch coverage across undated playoffs.
    horizon = max(first_phase_days) if first_phase_days else None
    age_days = (today - generated.date()).days
    fresh = age_days <= 14
    complete = bool(horizon and review_end <= horizon and not held and fresh and today <= end)
    note = "Published named fixtures only; completeness is limited to the verified first regular phase. Unresolved later-phase pairings and undated games are held."
    if not fresh:
        note += " Official report publication is more than 14 days old; freshness review required."
    if horizon and review_end > horizon:
        note += " The review window extends beyond the named-fixture horizon."
    if held:
        note += " Unresolved pairings fall inside the review window."
    return sorted(events, key=lambda e: (e["start_time"], e["id"])), {
        "report_url": report_url(source),
        "report_generated_at": generated.isoformat().replace("+00:00", "Z"),
        "published_fixtures": published, "unresolved_published_rows": unresolved,
        "held_review_fixtures": held, "fixture_coverage_end": horizon.isoformat() if horizon else None,
        "review_window_complete": complete, "report_age_days": age_days, "coverage_note": note,
    }


def parse_fiba_report(content, source, today, review_end):
    _spec(source)
    text, rows = _read_pdf(content)
    return parse_fiba_report_rows(text, rows, source, today, review_end)


def _get_public(get, url):
    response = get(url, timeout=45, allow_redirects=False)
    response.raise_for_status()
    if 300 <= response.status_code < 400:
        raise ValueError("FIBA report endpoint redirected; publisher review required")
    return response


def fetch_fiba_report_fixtures(source, today, review_end, get=requests.get):
    """Read the same unauthenticated list/view routes linked by the public index."""
    spec = _spec(source)
    listing_url = BASE + "/api/list.php?" + urlencode({"path": spec["path"]})
    if source.get("endpoint") != listing_url:
        raise ValueError("FIBA report configured endpoint left its exact public directory")
    listing = _get_public(get, listing_url).json()
    if not isinstance(listing, dict) or not isinstance(listing.get("files"), list):
        raise ValueError("FIBA public reports directory schema changed")
    matches = [x for x in listing["files"] if isinstance(x, dict) and x.get("name") == "competition-schedule.pdf"]
    if len(matches) != 1:
        raise ValueError("FIBA current competition report is absent or ambiguous")
    modified = matches[0].get("lastModified")
    try:
        stamp = dt.datetime.fromisoformat(modified.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("FIBA report directory modification time is missing") from exc
    response = _get_public(get, report_url(source))
    if "application/pdf" not in response.headers.get("Content-Type", "").lower():
        raise ValueError("FIBA report viewer returned a non-PDF content type")
    events, evidence = parse_fiba_report(response.content, source, today, review_end)
    evidence["report_directory_modified_at"] = stamp.isoformat().replace("+00:00", "Z")
    return events, evidence
