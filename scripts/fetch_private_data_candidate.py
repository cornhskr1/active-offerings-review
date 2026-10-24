"""Fetch a pinned private data snapshot using a read-only data-repo token.

Manual preflight only; does not deploy or refresh providers.
"""
import base64
import binascii
import json
import os
from pathlib import Path
import re
import urllib.request

from scripts.verify_external_data_candidate import verify_candidate

REPO = "cornhskr1/active-offerings-data"
FILES = ("manifest.json", "data/status.json", "data/review-data.json")
COMMIT = "fd880eac4eab92bca037fb817031ba48e83808cb"
MAX_RESPONSE = 8_000_000

def fetch_candidate(out: Path, token: str, commit: str = COMMIT, opener=None):
    if not re.fullmatch("[0-9a-f]{40}", commit):
        raise ValueError("invalid pinned commit")
    if not token:
        raise ValueError("private repository read credential is not configured")
    if out.exists() and any(out.iterdir()):
        raise ValueError("output must be empty")
    out.mkdir(parents=True, exist_ok=True)
    opener = opener or urllib.request.urlopen
    for name in FILES:
        url = f"https://api.github.com/repos/{REPO}/contents/published/pilot/{name}?ref={commit}"
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nrgc-private-read-preflight",
        })
        with opener(request, timeout=20) as response:
            if response.geturl() != url:
                raise ValueError("unexpected redirect")
            body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise ValueError("oversized API response")
        obj = json.loads(body)
        if not isinstance(obj, dict) or obj.get("type") != "file" or obj.get("path") != f"published/pilot/{name}" or obj.get("encoding") != "base64":
            raise ValueError("unexpected API file")
        try:
            raw = base64.b64decode(obj["content"], validate=False)
        except (KeyError, TypeError, ValueError, binascii.Error) as exc:
            raise ValueError("invalid encoded file") from exc
        if len(raw) > 5_000_000:
            raise ValueError("oversized data file")
        file = out / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(raw)
    return verify_candidate(out)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.fetch_private_data_candidate OUTPUT_DIR")
    try:
        print("Verified private data:", fetch_candidate(Path(sys.argv[1]), os.environ.get("DATA_REPO_READ_TOKEN", "")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Private data verification failed: {exc}") from exc
