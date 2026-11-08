#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

import archive as A


def run() -> int:
    failed = False
    for cat in A.category_ids():
        entries = A.load(cat)
        summary = f"{cat}: {len(entries)} entries"
        problems = A.validate(cat)
        if problems:
            failed = True
            print(f"FAIL  {summary}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"ok    {summary}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    argparse.ArgumentParser(description="Validate all categories.").parse_args(argv)
    return run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
