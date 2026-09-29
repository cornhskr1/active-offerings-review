#!/usr/bin/env python3
"""Fast Priority 2 PR gate: structural validation plus change-scoped tests."""

from __future__ import annotations

import compileall
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
DATA = ROOT / "data"


def changed_files():
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD^1", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return {line.strip() for line in out.splitlines() if line.strip()}
    except Exception:
        return set()


def run_pattern(pattern):
    subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-q"],
        cwd=ROOT,
        check=True,
    )


def main():
    if not compileall.compile_dir(ROOT / "scripts", quiet=1):
        raise SystemExit("script compilation failed")
    if not compileall.compile_dir(TESTS, quiet=1):
        raise SystemExit("test compilation failed")

    for path in DATA.glob("*.json"):
        with path.open(encoding="utf-8") as handle:
            json.load(handle)

    changed = changed_files()
    patterns = {
        "test_priority2_coverage_inventory.py",
        "test_priority2_review_workflow.py",
        "test_competition_identity_registry.py",
    }

    for path in changed:
        if path.startswith("tests/test_") and path.endswith(".py"):
            patterns.add(Path(path).name)

    if any(path.startswith("data/soccer-") for path in changed):
        patterns.add("test_soccer_*scope.py")
    if any("rugby" in path.lower() for path in changed):
        patterns.add("test_rugby*.py")
    if any("tennis" in path.lower() for path in changed):
        patterns.add("test_*tennis*.py")
    if any("basketball" in path.lower() or "nbb" in path.lower() for path in changed):
        patterns.add("test_*basketball*.py")

    for pattern in sorted(patterns):
        run_pattern(pattern)


if __name__ == "__main__":
    main()
