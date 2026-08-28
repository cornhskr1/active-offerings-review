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

HEADERS = {
    "User-Agent": "Mozilla/5.0 ActiveOfferingsReview/1.0"
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
    return re.sub(r"\s+", " ", value).strip()


def extract_catalog_entries(text):
    lines = [normalize_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    entries = []
    ignored = {
        "sport",
        "league",
        "event",
        "competition",
        "restriction",
        "restrictions",
        "authorized sports wagering menu",
    }

    for line in lines:
        lowered = line.lower()

        if lowered in ignored:
            continue

        if len(line) < 3:
            continue

        if re.fullmatch(r"\d+", line):
            continue

        entries.append(line)

    seen = set()
    unique_entries = []

    for entry in entries:
        key = entry.casefold()

        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    return unique_entries


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
    previous_entries = existing.get("entries", [])

    previous_lookup = {
        item.casefold() for item in previous_entries
    }

    new_entries = [
        item
        for item in entries
        if item.casefold() not in previous_lookup
    ]

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
    }

    save_catalog(catalog)

    os.makedirs(os.path.dirname(CATALOG_PDF), exist_ok=True)

    with open(CATALOG_PDF, "wb") as file:
        file.write(pdf_bytes)

    print(f"Catalog: {latest['text']}")
    print(f"Entries found: {len(entries)}")
    print(f"New entries: {len(new_entries)}")

    for item in new_entries:
        print(f"NEW: {item}")


if __name__ == "__main__":
    main()
