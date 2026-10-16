#!/usr/bin/env python3
"""Validate every category. Read-only.

This is the same set of checks the write path runs automatically, exposed
standalone so a bad state can be diagnosed before it is deployed. Run it after
any bulk edit, and after pulling changes.

    python3 scripts/check.py
"""

from __future__ import annotations

import sys

import archive as A


def main() -> int:
    results = A.validate_all()
    failed = False

    for cat in A.category_ids():
        problems = results[cat]
        entries = A.load(cat)
        rated = sum(1 for e in entries if e["rating_text"])
        summary = f"{cat}: {len(entries)} entries ({rated} rated + {len(entries) - rated} TBR)"
        if problems:
            failed = True
            print(f"FAIL  {summary}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"ok    {summary}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())