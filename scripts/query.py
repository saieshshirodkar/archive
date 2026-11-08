#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

import archive as A


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Query the archive.")
    cmds = p.add_subparsers(dest="command", required=True)

    d = cmds.add_parser("date")
    d.add_argument("--shift", type=int, default=0)
    d.add_argument("-v", "--verbose", action="store_true")
    d.set_defaults(h=cmd_date)

    f = cmds.add_parser("find")
    f.add_argument("title")
    f.add_argument("--cat", choices=A.category_ids())
    f.set_defaults(h=cmd_find)

    t = cmds.add_parser("top")
    t.add_argument("count", nargs="?", type=int, default=10)
    t.add_argument("--cat", choices=A.category_ids())
    t.set_defaults(h=cmd_top)

    latest_cmd = cmds.add_parser("latest")
    latest_cmd.add_argument("count", nargs="?", type=int, default=5)
    latest_cmd.add_argument("--cat", choices=A.category_ids())
    latest_cmd.set_defaults(h=cmd_latest)

    s = cmds.add_parser("show")
    s.add_argument("--cat", required=True, choices=A.category_ids())
    s.set_defaults(h=cmd_show)
    return p


def selected(args: argparse.Namespace) -> list[str]:
    return [args.cat] if args.cat else A.category_ids()


def row(cat: str, entry: dict) -> str:
    return f"{cat:>8}  {A.describe(entry)}"


def cmd_date(args: argparse.Namespace) -> int:
    now = datetime.now(A.TZ) + timedelta(days=args.shift)
    print(f"{now:%d-%m-%Y}  ({now:%Y-%m-%d %H:%M %Z})")
    if args.verbose:
        print("  use this string as --date for movies entries")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    cats = selected(args)
    matches = 0
    for cat in cats:
        entries = A.load(cat)
        for i in A.find(entries, args.title):
            print(row(cat, entries[i]))
            matches += 1
    if matches == 0:
        print(f"no match for {args.title!r} in {', '.join(cats)}")
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    ranked = sorted(
        (
            (float(e["rating_text"].split("/")[0]), c, e)
            for c in selected(args)
            for e in A.load(c)
        ),
        key=lambda x: x[0],
        reverse=True,
    )
    for value, cat, entry in ranked[: args.count]:
        print(f"{value:>5}  {cat:>8}  {entry['title']}")
    return 0


def cmd_latest(args: argparse.Namespace) -> int:
    ranked = sorted(
        ((e["id"], c, e) for c in selected(args) for e in A.load(c)),
        key=lambda x: x[0],
        reverse=True,
    )
    for _, cat, entry in ranked[: args.count]:
        print(row(cat, entry))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    print(f"{args.cat} ({len(entries)})")
    print(A.listing(entries))
    return 0


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.h(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
