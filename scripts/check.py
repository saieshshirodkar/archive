#!/usr/bin/env python3
"""Validate every category. Read-only.

The same checks the write path runs automatically, exposed standalone so a bad
state can be diagnosed before it is deployed. Run it after any bulk edit and
after pulling changes.

    python3 scripts/check.py
"""

from __future__ import annotations

import argparse
import sys

import archive as A


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Validate every archive category.")


def run() -> int:
    failed = False
    for category in A.category_ids():
        entries = A.load(category)
        rated = sum(1 for entry in entries if entry["rating_text"])
        summary = (
            f"{category}: {len(entries)} entries "
            f"({rated} rated + {len(entries) - rated} TBR)"
        )
        problems = A.validate(category)
        if problems:
            failed = True
            print(f"FAIL  {summary}")
            for problem in problems:
                print(f"        {problem}")
        else:
            print(f"ok    {summary}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    build_parser().parse_args(argv)
    return run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
