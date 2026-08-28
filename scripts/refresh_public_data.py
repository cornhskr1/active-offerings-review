#!/usr/bin/env python3
"""
Background public-source health refresh for GitHub Pages.
Uses only Python standard library so GitHub Actions needs no pip install.

This job intentionally records source availability/freshness separately from
event-level ingestion. Event adapters can write data/review-data.json as they
are added without changing the staff-facing Refresh Review control.
"""
from pathlib import Path
import json, datetime, urllib.request, urllib.error, ssl, time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"
}
ctx = ssl.create_default_context()
rows = []

for source in sources:
    started = time.time()
    row = dict(source)
    row["checked_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        req = urllib.request.Request(source["url"], headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            row["http_status"] = getattr(resp, "status", 200)
            row["final_url"] = resp.geturl()
            row["ok"] = 200 <= row["http_status"] < 400
            row["content_type"] = resp.headers.get("Content-Type","")
            # Read a small amount to ensure the response body is accessible.
            resp.read(4096)
    except urllib.error.HTTPError as e:
        row["http_status"] = e.code
        row["ok"] = False
        row["error"] = f"HTTP {e.code}"
    except Exception as e:
        row["http_status"] = None
        row["ok"] = False
        row["error"] = str(e)[:200]
    row["elapsed_ms"] = int((time.time()-started)*1000)
    rows.append(row)

status = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_count": len(rows),
    "healthy_count": sum(1 for r in rows if r.get("ok")),
    "sources": rows
}
(DATA / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

# Keep review-data's generated_at aligned with the background run without
# pretending event adapters have refreshed records that do not exist yet.
review_path = DATA / "review-data.json"
if review_path.exists():
    review = json.loads(review_path.read_text(encoding="utf-8"))
else:
    review = {"schema_version":1,"review_window_days":7,"events":[],"u18_matches":[],"restriction_triggers":[],"coverage_alerts":[]}
review["background_checked_at"] = status["generated_at"]
review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")

print(json.dumps({"generated_at":status["generated_at"],"healthy":status["healthy_count"],"total":status["source_count"]}))
