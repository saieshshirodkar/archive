#!/usr/bin/env python3
"""Look things up: find entries, list top rated, show what's TBR, print the date.

The date helper exists because every ``date_watched`` must be IST and the
system clock usually is not. Run ``query.py date`` rather than reaching for
``date +%d-%m-%Y`` by hand.

Examples
--------
    python3 scripts/query.py date
    python3 scripts/query.py date --shift -1        # yesterday
    python3 scripts/query.py find neverland         # search all categories
    python3 scripts/query.py find housemaid --cat books
    python3 scripts/query.py top 10
    python3 scripts/query.py top 15 --cat books
    python3 scripts/query.py latest 5               # newest rated
    python3 scripts/query.py tbr
    python3 scripts/query.py show --cat shows
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

import archive as A


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query the archive.")
    commands = parser.add_subparsers(dest="command", required=True)

    date = commands.add_parser("date", help="print today in IST as DD-MM-YYYY")
    date.add_argument(
        "--shift", type=int, default=0, help="move N days (negative = past)"
    )
    date.add_argument("-v", "--verbose", action="store_true")
    date.set_defaults(handler=cmd_date)

    find = commands.add_parser("find", help="search titles")
    find.add_argument("title")
    find.add_argument("--cat", choices=A.category_ids())
    find.set_defaults(handler=cmd_find)

    top = commands.add_parser("top", help="highest rated first")
    top.add_argument("count", nargs="?", type=int, default=10)
    top.add_argument("--cat", choices=A.category_ids())
    top.set_defaults(handler=cmd_top)

    latest = commands.add_parser("latest", help="newest rated by id")
    latest.add_argument("count", nargs="?", type=int, default=5)
    latest.add_argument("--cat", choices=A.category_ids())
    latest.set_defaults(handler=cmd_latest)

    tbr = commands.add_parser("tbr", help="list unrated entries")
    tbr.add_argument("--cat", choices=A.category_ids())
    tbr.set_defaults(handler=cmd_tbr)

    show = commands.add_parser("show", help="print a whole category")
    show.add_argument("--cat", required=True, choices=A.category_ids())
    show.set_defaults(handler=cmd_show)

    return parser


def selected(args: argparse.Namespace) -> list[str]:
    """Categories to read: the one asked for, or all of them."""
    return [args.cat] if args.cat else A.category_ids()


def row(category: str, entry: dict) -> str:
    """Category name and entry summary on one line."""
    return f"{category:>8}  {A.describe(entry)}"


def cmd_date(args: argparse.Namespace) -> int:
    """Print IST dates. --shift moves the day for backfilling past viewings."""
    now = datetime.now(A.TZ) + timedelta(days=args.shift)
    print(f"{now:%d-%m-%Y}  ({now:%Y-%m-%d %H:%M %Z})")
    if args.verbose:
        print("  use this string as --date for movies entries")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    """Search titles across one category or all of them."""
    categories = selected(args)
    matches = 0
    for category in categories:
        entries = A.load(category)
        for index in A.find(entries, args.title):
            print(row(category, entries[index]))
            matches += 1
    if matches == 0:
        print(f"no match for {args.title!r} in {', '.join(categories)}")
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    """Highest rated first. Parses numbers properly; never string-sorts."""
    ranked = [
        (float(entry["rating_text"].split("/")[0]), category, entry)
        for category in selected(args)
        for entry in A.load(category)
        if entry["rating_text"]
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    for value, category, entry in ranked[: args.count]:
        print(f"{value:>5}  {category:>8}  {entry['title']}")
    return 0


def cmd_latest(args: argparse.Namespace) -> int:
    """Newest-rated entries: highest ids among rated, not the array tail.

    The TBR block sits at the end of every array, so "last N" would return
    unrated entries. This picks the highest ids that actually carry a rating.
    """
    ranked = [
        (entry["id"], category, entry)
        for category in selected(args)
        for entry in A.load(category)
        if entry["rating_text"]
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    for _, category, entry in ranked[: args.count]:
        print(row(category, entry))
    return 0


def cmd_tbr(args: argparse.Namespace) -> int:
    """List unrated entries, grouped by category."""
    for category in selected(args):
        pending = [entry for entry in A.load(category) if not entry["rating_text"]]
        if not pending:
            continue
        print(f"\n{category} ({len(pending)} TBR)")
        print(A.listing(pending))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print one category in full."""
    entries = A.load(args.cat)
    print(f"{args.cat} ({len(entries)})")
    print(A.listing(entries))
    return 0


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
