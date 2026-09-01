#!/usr/bin/env python3
from pathlib import Path
import json, re, datetime, hashlib, urllib.parse, requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

PAGE_URL = "https://nrgc.nebraska.gov/gaming/sports-betting"
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}
NOW = datetime.datetime.now(datetime.timezone.utc)

SPORTS = [
    "Aussie Rules","Baseball","Basketball","Bowling","Boxing","Combat Sports",
    "Cricket","Cycling","Darts","Esports","Football","Golf","Ice Hockey",
    "Lacrosse","Motorsports","National Collegiate Athletic Association (NCAA)",
    "NCAA","Olympics","Rodeo","Rugby","Soccer","Surfing","Table Tennis","Tennis","Volleyball"
]
SPORT_ALIASES = {
    "NCAA":"National Collegiate Athletic Association (NCAA)"
}

def normalize(s):
    s = (s or "").replace("ﬁ","fi").replace("ﬂ","fl").replace("ﬀ","ff").replace("ﬃ","ffi").replace("ﬄ","ffl")
    return re.sub(r"\s+"," ",s).strip()

def clean_heading(raw):
    """Normalize a candidate PDF heading while preserving indentation outside this function."""
    s = normalize(raw)
    return re.sub(r"^[•·▪◦\-–—]\s*", "", s).strip()

r = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
r.raise_for_status()
page = BeautifulSoup(r.text, "html.parser")

candidates = []
for a in page.find_all("a", href=True):
    text = normalize(a.get_text(" ", strip=True))
    href = urllib.parse.urljoin(PAGE_URL, a["href"])
    combined = (text + " " + href).lower()
    if "authorized sports wagering menu" in combined and ".pdf" in combined:
        candidates.append((text, href))
    elif "nebraska authorized sports wagering menu" in text.lower():
        candidates.append((text, href))

if not candidates:
    # Fallback: any PDF link containing wagering/menu language.
    for a in page.find_all("a", href=True):
        text = normalize(a.get_text(" ", strip=True))
        href = urllib.parse.urljoin(PAGE_URL, a["href"])
        low = (text+" "+href).lower()
        if ".pdf" in low and "wager" in low and "menu" in low:
            candidates.append((text, href))

if not candidates:
    raise RuntimeError("Could not discover the current Authorized Sports Wagering Menu from NRGC Sports Betting page.")

# Prefer a dated attachment label and latest date found in label/url.
def date_key(item):
    text, href = item
    found = re.findall(r"(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{2,4})", text+" "+href)
    if not found:
        return (0,0,0)
    m,d,y = found[-1]
    y = int(y)
    if y < 100: y += 2000
    return (y,int(m),int(d))

label, pdf_url = sorted(candidates, key=date_key, reverse=True)[0]
pdf = requests.get(pdf_url, headers=HEADERS, timeout=60)
pdf.raise_for_status()
pdf_path = DATA/"catalog-current.pdf"
pdf_path.write_bytes(pdf.content)

reader = PdfReader(str(pdf_path))

pages = []
all_lines = []
raw_pages = []

for i,p in enumerate(reader.pages, start=1):
    txt = p.extract_text() or ""
    raw_lines = [x.rstrip() for x in txt.splitlines() if normalize(x)]
    lines = [normalize(x) for x in raw_lines]
    raw_pages.append(raw_lines)
    pages.append({"page":i,"lines":lines})
    all_lines.extend(lines)

dedup=[]
for line in all_lines:
    if not dedup or line != dedup[-1]:
        dedup.append(line)
all_lines=dedup

version = None
for source in (label, " ".join(all_lines[:80])):
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", source)
    if m:
        mm,dd,yy = map(int,m.groups())
        if yy < 100: yy += 2000
        version=f"{mm}.{dd}.{str(yy)[-2:]}"
        break

NCAA_SUBSECTIONS = [
    "NCAA Baseball","NCAA Basketball","NCAA Beach Volleyball","NCAA Field Hockey",
    "NCAA Football","NCAA Golf","NCAA Ice Hockey","NCAA Lacrosse","NCAA Soccer",
    "NCAA Softball","NCAA Swimming","NCAA Tennis","NCAA Track and Field",
    "NCAA Volleyball","NCAA Water Polo","NCAA Wrestling"
]

TOP_LEVEL_SPORTS = [
    "Aussie Rules","Baseball","Basketball","Bowling","Boxing","Combat Sports",
    "Cricket","Cycling","Darts","Esports","Football","Golf","Ice Hockey",
    "Lacrosse","Motorsports","National Collegiate Athletic Association (NCAA)",
    "Olympics","Rodeo","Rugby","Soccer","Surfing","Table Tennis","Tennis","Volleyball"
]

def leading_indent(raw):
    return len(raw) - len(raw.lstrip(" \t"))

def is_pdf_header(line):
    s=clean_heading(line)
    return (
        not s
        or bool(re.fullmatch(r"\d{1,3}",s))
        or bool(re.match(r"^Table of Contents\b",s,re.I))
    )

content_start = None
for page_index, raw_lines in enumerate(raw_pages):
    if page_index < 4:
        continue
    for raw in raw_lines:
        if leading_indent(raw) != 0:
            continue
        heading=clean_heading(raw)
        if heading in TOP_LEVEL_SPORTS and not re.search(r"\.{4,}", raw):
            content_start=page_index
            break
    if content_start is not None:
        break

if content_start is None:
    raise RuntimeError("Could not locate the start of the live sport catalog in the PDF.")

sections=[]
current=None

for page_index in range(content_start, len(raw_pages)):
    for raw in raw_pages[page_index]:
        if is_pdf_header(raw):
            continue

        heading=clean_heading(raw)
        indent=leading_indent(raw)

        is_top_level = indent == 0 and heading in TOP_LEVEL_SPORTS
        is_ncaa_subsection = indent == 0 and heading in NCAA_SUBSECTIONS

        if is_top_level or is_ncaa_subsection:
            label = heading
            if label == "National Collegiate Athletic Association (NCAA)":
                label = "NCAA"

            if current and current["lines"]:
                sections.append(current)

            current={
                "sport":label,
                "lines":[],
                "page_start":page_index+1
            }
            continue

        if current:
            line=normalize(raw)
            if current["sport"].startswith("NCAA ") and line == "National Collegiate Athletic Association (NCAA)":
                continue
            current["lines"].append(line)

if current and current["lines"]:
    sections.append(current)

merged=[]
for sec in sections:
    if merged and merged[-1]["sport"] == sec["sport"]:
        merged[-1]["lines"].extend(sec["lines"])
    else:
        merged.append(sec)
sections=merged

# If the PDF's TOC polluted the first sections, retain everything but mark raw parsing.
# Restriction extraction is intentionally broad and preserves exact catalog wording.
restriction_patterns = [
    r"\bNO\b.*\bWAGER", r"\bWAGER LIMIT\b", r"\bMARKETS?\b.*\b(CLOSE|LIMIT|DISABLE|REMOVE)",
    r"\bMUST\b.*\b(CLOSE|DISABLE|REMOVE)", r"\bPROHIBIT", r"\bRESTRICT",
    r"\bNOT PERMISSIBLE\b", r"\bNO PROPOSITION\b", r"\bNO PLAYER PROPOSITION\b",
    r"\bNO IN-GAME\b"
]
restrictions=[]
for sec in sections:
    for line in sec["lines"]:
        up=line.upper()
        if any(re.search(p,up) for p in restriction_patterns):
            restrictions.append({"sport":sec["sport"],"text":line})

sha = hashlib.sha256(pdf.content).hexdigest()
out = {
    "schema_version":1,
    "generated_at":NOW.isoformat(),
    "source_page":PAGE_URL,
    "source_label":label,
    "pdf_url":pdf_url,
    "menu_version":version,
    "sha256":sha,
    "page_count":len(reader.pages),
    "line_count":len(all_lines),
    "sections":sections,
    "restrictions":restrictions,
    "pages":pages
}
(DATA/"catalog-live.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")

# Lightweight status file for header/banner use.
(DATA/"catalog-status.json").write_text(json.dumps({
    "generated_at":NOW.isoformat(),
    "source_label":label,
    "menu_version":version,
    "pdf_url":pdf_url,
    "page_count":len(reader.pages),
    "line_count":len(all_lines),
    "restriction_count":len(restrictions),
    "sha256":sha
},indent=2),encoding="utf-8")

print(json.dumps({
    "source_label":label,
    "menu_version":version,
    "page_count":len(reader.pages),
    "lines":len(all_lines),
    "sections":len(sections),
    "restrictions":len(restrictions)
}))
