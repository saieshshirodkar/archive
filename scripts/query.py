#!/usr/bin/env python3
"""Look things up: find entries, list top rated, show what's TBR, print the date.

The date helpers exist because every ``date_watched`` must be IST and the
system clock is usually not. Run ``python3 scripts/query.py date`` rather than
reaching for ``date +%d-%m-%Y`` by hand.

Examples
--------
    python3 scripts/query.py date
    python3 scripts/query.py date --shift -1        # yesterday
    python3 scripts/query.py find neverland         # search all categories
    python3 scripts/query.py find "housemaid" --cat books
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


def cmd_date(args: argparse.Namespace) -> int:
    """Print IST dates. --shift moves the day for backfilling past viewings."""
    now = datetime.now(A.TZ)
    if args.shift:
        now = now + timedelta(days=args.shift)
    print(f"{now:%d-%m-%Y}  ({now:%Y-%m-%d %H:%M %Z})")
    if args.verbose:
        print("  use this string as --date for movies entries")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    """Search titles across one category or all of them."""
    cats = [args.cat] if args.cat else A.category_ids()
    total = 0
    for cat in cats:
        entries = A.load(cat)
        hits = A.find(entries, args.title)
        if not hits:
            continue
        for i in hits:
            print(f"{cat:>8}  {A.describe(entries[i])}")
            total += 1
    if total == 0:
        print(f"no match for {args.title!r} in {', '.join(cats)}")
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    """Highest rated first. Parses numbers properly; never string-sorts."""
    cats = [args.cat] if args.cat else A.category_ids()
    rows = []
    for cat in cats:
        for e in A.load(cat):
            if e["rating_text"]:
                rows.append((float(e["rating_text"].split("/")[0]), cat, e))
    rows.sort(key=lambda r: r[0], reverse=True)
    for value, cat, e in rows[: args.count]:
        print(f"{value:>5}  {cat:>8}  {e['title']}")
    return 0


def cmd_latest(args: argparse.Namespace) -> int:
    """Newest-rated entries: highest ids among rated, not the array tail.

    The TBR block lives at the end of each array, so "last N" would return
    unrated entries. This picks the highest ids that actually have a rating.
    """
    cats = [args.cat] if args.cat else A.category_ids()
    rows = []
    for cat in cats:
        for e in A.load(cat):
            if e["rating_text"]:
                rows.append((e["id"], cat, e))
    rows.sort(key=lambda r: r[0], reverse=True)
    for _, cat, e in rows[: args.count]:
        print(f"{cat:>8}  {A.describe(e)}")
    return 0


def cmd_tbr(args: argparse.Namespace) -> int:
    """List unrated entries."""
    cats = [args.cat] if args.cat else A.category_ids()
    for cat in cats:
        entries = A.load(cat)
        pending = [e for e in entries if not e["rating_text"]]
        if not pending:
            continue
        print(f"\n{cat} ({len(pending)} TBR)")
        for e in pending:
            print("  " + A.describe(e))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print one category in full."""
    entries = A.load(args.cat)
    print(f"{args.cat} ({len(entries)})")
    for e in entries:
        print("  " + A.describe(e))
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Query the archive.")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("date", help="print today in IST as DD-MM-YYYY")
    d.add_argument("--shift", type=int, default=0, help="move N days (negative = past)")
    d.add_argument("-v", "--verbose", action="store_true")
    d.set_defaults(func=cmd_date)

    f = sub.add_parser("find", help="search titles")
    f.add_argument("title")
    f.add_argument("--cat", choices=A.category_ids())
    f.set_defaults(func=cmd_find)

    t = sub.add_parser("top", help="highest rated first")
    t.add_argument("count", nargs="?", type=int, default=10)
    t.add_argument("--cat", choices=A.category_ids())
    t.set_defaults(func=cmd_top)

    l = sub.add_parser("latest", help="newest rated by id")
    l.add_argument("count", nargs="?", type=int, default=5)
    l.add_argument("--cat", choices=A.category_ids())
    l.set_defaults(func=cmd_latest)

    tb = sub.add_parser("tbr", help="list unrated entries")
    tb.add_argument("--cat", choices=A.category_ids())
    tb.set_defaults(func=cmd_tbr)

    s = sub.add_parser("show", help="print a whole category")
    s.add_argument("--cat", required=True, choices=A.category_ids())
    s.set_defaults(func=cmd_show)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))