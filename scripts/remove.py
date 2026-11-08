#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import archive as A


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Remove an entry and its cover.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", required=True)
    p.add_argument("--exact", action="store_true")
    return p


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1
    entry = entries.pop(index)
    cover = A.ROOT / entry["cover_url"]
    if cover.is_file():
        stash = Path(tempfile.mkdtemp(prefix="archive-remove-")) / cover.name
        shutil.move(cover, stash)
        try:
            A.save(args.cat, entries)
        except Exception:
            shutil.move(stash, cover)
            raise
        finally:
            shutil.rmtree(stash.parent, ignore_errors=True)
    else:
        A.save(args.cat, entries)
    fresh = A.load(args.cat)
    print("removed:")
    print(A.listing([entry]))
    print(f"  {args.cat} now has {len(fresh)} entries")
    return 0


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
