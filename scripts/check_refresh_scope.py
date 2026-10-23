#!/usr/bin/env python3
"""Reject unexpected staged paths before a scheduled data refresh commits."""
import argparse
import subprocess
import sys
from pathlib import PurePosixPath

def staged_paths(repo="."):
    raw = subprocess.check_output(["git", "-C", repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACDMRTUXB"])
    return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\x00") if p]

def check(paths, allowed):
    approved = set(allowed)
    if not approved:
        raise ValueError("at least one allowed path is required")
    for path in approved:
        if not path or path.startswith("/") or path.startswith("./") or ".." in PurePosixPath(path).parts:
            raise ValueError(f"invalid allowlisted path: {path!r}")
    return sorted(set(paths) - approved)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("allowed", nargs="+")
    args = parser.parse_args(argv)
    unexpected = check(staged_paths(args.repo), args.allowed)
    if unexpected:
        print("BLOCKED: unexpected staged paths: " + ", ".join(unexpected), file=sys.stderr)
        return 1
    print("PASS: staged changes restricted to approved refresh files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
