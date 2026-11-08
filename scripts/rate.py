#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

import archive as A


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rate an entry in place.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", required=True)
    p.add_argument("--exact", action="store_true")
    p.add_argument("--rating", required=True, help='like "8" or "8.5"')
    p.add_argument("--position", type=int, default=None, help="move to this id")
    return p


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1
    try:
        rating = A.normalise_rating(args.rating)
    except ValueError as exc:
        return A.fail(str(exc))
    entry = entries[index]
    reason = "in place (movies are date-sorted)" if args.cat == "movies" else "in place"
    if args.position is not None:
        A.move(entries, index, args.position - 1)
        reason = f"moved to position {args.position}"
    entry["rating_text"] = rating
    A.save(args.cat, entries)
    fresh = A.load(args.cat)
    rated = fresh[A.exact(fresh, entry["title"])]
    print(f"rated: {A.describe(rated)}")
    print(f"  {reason}; {args.cat} has {len(fresh)} entries")
    return 0


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
