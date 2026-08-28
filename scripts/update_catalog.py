import io
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

NRGC_PAGE = "https://nrgc.nebraska.gov/gaming/sports-betting"
CATALOG_JSON = "data/catalog.json"
CATALOG_PDF = "data/catalog-current.pdf"
BASELINE_FLAG = "data/catalog-baseline-established.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 ActiveOfferingsReview/1.0"
}

BOILERPLATE = {
    "nebraska racing and gaming commission",
    "authorized sports wagering menu",
    "authorized sports",
    "wagering menu",
    "approved wagers and events",
    "table of contents",
    "contents",
    "summary",
    "sport",
    "sports",
    "league",
    "leagues",
    "event",
    "events",
    "competition",
    "competitions",
    "restriction",
    "restrictions",
    "page",
}


def get_latest_catalog_url():
    response = requests.get(NRGC_PAGE, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []

    for link in soup.find_all("a", href=True):
        text = " ".join(link.stripped_strings)
        href = link["href"]
        combined = f"{text} {href}".lower()

        if "sports wagering" in combined and (
            "menu" in combined or "authorized" in combined
        ):
            candidates.append({
                "text": text,
                "url": urljoin(NRGC_PAGE, href),
            })

    if not candidates:
        raise RuntimeError(
            "Could not locate the NRGC Authorized Sports Wagering Menu."
        )

    def extract_date(candidate):
        text = candidate["text"] + " " + candidate["url"]

        patterns = [
            r"(\d{1,2})[./_-](\d{1,2})[./_-](\d{2,4})",
            r"(\d{4})[./_-](\d{1,2})[./_-](\d{1,2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                parts = match.groups()

                try:
                    if len(parts[0]) == 4:
                        year, month, day = map(int, parts)
                    else:
                        month, day, year = map(int, parts)
                        if year < 100:
                            year += 2000

                    return datetime(year, month, day)

                except ValueError:
                    pass

        return datetime.min

    candidates.sort(key=extract_date, reverse=True)
    return candidates[0]


def download_pdf(url):
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.content


def extract_pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages)


def normalize_line(value):
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip("•|-–— ")
    return value


def looks_like_boilerplate(line):
    lowered = line.casefold().strip()

    if lowered in BOILERPLATE:
        return True

    if re.fullmatch(r"\d+", line):
        return True

    if re.fullmatch(r"page\s+\d+", lowered):
        return True

    if re.fullmatch(
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+\d{1,2},\s+\d{4}",
        lowered
    ):
        return True

    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", lowered):
        return True

    return False


def extract_catalog_entries(text):
    entries = []
    seen = set()

    for raw_line in text.splitlines():
        line = normalize_line(raw_line)

        if not line:
            continue

        if len(line) < 3:
            continue

        if looks_like_boilerplate(line):
            continue

        if not re.search(r"[A-Za-z]", line):
            continue

        key = line.casefold()

        if key not in seen:
            seen.add(key)
            entries.append(line)

    return entries


def load_existing_catalog():
    if not os.path.exists(CATALOG_JSON):
        return {}

    with open(CATALOG_JSON, "r", encoding="utf-8") as file:
        return json.load(file)


def save_catalog(data):
    os.makedirs(os.path.dirname(CATALOG_JSON), exist_ok=True)

    with open(CATALOG_JSON, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def main():
    latest = get_latest_catalog_url()

    pdf_bytes = download_pdf(latest["url"])
    text = extract_pdf_text(pdf_bytes)
    entries = extract_catalog_entries(text)

    existing = load_existing_catalog()

    baseline_exists = os.path.exists(BASELINE_FLAG)

    if baseline_exists:
        previous_entries = existing.get("entries", [])

        previous_lookup = {
            item.casefold() for item in previous_entries
        }

        new_entries = [
            item
            for item in entries
            if item.casefold() not in previous_lookup
        ]

        status = "comparison"
    else:
        new_entries = []
        status = "baseline-established"

    catalog = {
        "source_page": NRGC_PAGE,
        "catalog_title": latest["text"],
        "catalog_url": latest["url"],
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_count": len(entries),
        "new_entry_count": len(new_entries),
        "new_entries": new_entries,
        "entries": entries,
        "review_status": {
            item: "UNMAPPED / REVIEW"
            for item in new_entries
        },
        "comparison_status": status,
    }

    save_catalog(catalog)

    os.makedirs(os.path.dirname(CATALOG_PDF), exist_ok=True)

    with open(CATALOG_PDF, "wb") as file:
        file.write(pdf_bytes)

    if not baseline_exists:
        with open(BASELINE_FLAG, "w", encoding="utf-8") as file:
            file.write(
                "Clean catalog baseline established automatically.\n"
            )

    print(f"Catalog: {latest['text']}")
    print(f"Entries found: {len(entries)}")
    print(f"Comparison status: {status}")
    print(f"New entries: {len(new_entries)}")

    for item in new_entries:
        print(f"NEW: {item}")


if __name__ == "__main__":
    main()
