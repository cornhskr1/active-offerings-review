"""Offline preview of a validated private-data overlay on a staged public site.

Never modify production staging in place. No network access, credentials,
provider calls or Pages deployment. The two pilot files are replaced only
in an independently generated preview directory.
"""
import argparse
from pathlib import Path
import shutil

from scripts.verify_external_data_candidate import verify_candidate

PILOT = ("data/status.json", "data/review-data.json")

def overlay(site: Path, candidate: Path, preview: Path):
    site = site.resolve(strict=True)
    candidate = candidate.resolve(strict=True)
    preview = preview.resolve()
    if preview.exists():
        raise ValueError("preview destination must not already exist")
    if preview == site or preview.is_relative_to(site) or preview == candidate or preview.is_relative_to(candidate):
        raise ValueError("unsafe preview destination")
    if not (site / "index.html").is_file():
        raise ValueError("missing staged website")
    for name in PILOT:
        target = site / name
        if not target.is_file() or target.is_symlink():
            raise ValueError("missing or linked original data")
    verify_candidate(candidate)
    shutil.copytree(site, preview, symlinks=True)
    for name in PILOT:
        src = candidate / name
        dst = preview / name
        if dst.is_symlink() or not dst.is_file():
            raise ValueError("unsafe preview target")
        shutil.copyfile(src, dst)
    return list(PILOT)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--site", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--preview", type=Path, required=True)
    a = p.parse_args()
    print("Preview-only overlay:", ", ".join(overlay(a.site, a.candidate, a.preview)))
