#!/usr/bin/env python3
"""Move, reorder, or rename an entry without touching its rating.

Reordering is how the shows list gets built: "put X before Y" and this does
it. Bulk sorts exist for the categories where a canonical order is actually
wanted; movies are excluded because their order is fixed by date_watched.

Examples
--------
    python3 scripts/reorder.py --cat shows --title "Malcolm in the Middle" \\
        --before "The Walking Dead"

    python3 scripts/reorder.py --cat shows --title "Raakh" --position 2

    python3 scripts/reorder.py --cat shows --sort title
    python3 scripts/reorder.py --cat books --sort rating --descending
    python3 scripts/reorder.py --cat books --sort year
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

import archive as A

SORT_NAMES = ("title", "rating", "year", "id")


def rating_value(entry: dict) -> float:
    """Numeric part of a rating, for sorting. Unrated entries sort last."""
    text = entry["rating_text"]
    return float(text.split("/")[0]) if text else -1.0


# The key is always ascending and never negated. Descending is expressed by
# passing reverse=True to list.sort, because negation cannot work for a string
# key at all: there is no -"abc", so --sort title --descending silently
# returned ascending order when it was done that way.
SORT_KEYS: dict[str, Callable[[dict], Any]] = {
    "title": lambda entry: entry["title"].lower(),
    "rating": rating_value,
    "year": lambda entry: entry.get("year") or 0,
    "id": lambda entry: entry["id"],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reorder or rename entries.")
    parser.add_argument("--cat", required=True, choices=A.category_ids())
    parser.add_argument("--title", default=None, help="entry to move or rename")
    parser.add_argument(
        "--before", default=None, help="move this entry before that one"
    )
    parser.add_argument("--after", default=None, help="move this entry after that one")
    parser.add_argument(
        "--position", type=int, default=None, help="move to this id position"
    )
    parser.add_argument("--rename", default=None, help="new title for --title")
    parser.add_argument(
        "--exact",
        action="store_true",
        help="require whole-title matches for --title/--before/--after",
    )
    parser.add_argument("--sort", default=None, choices=SORT_NAMES)
    parser.add_argument("--descending", action="store_true", help="with --sort")
    return parser


def anchor(
    category: str, entries: list[dict], needle: str, flag: str, strict: bool
) -> int | None:
    """Resolve a --before/--after anchor to one index, reporting why not."""
    index = A.resolve_index(entries, needle, strict=strict)
    if index is None:
        A.report_no_match(entries, needle, category, flag, strict)
    return index


def bulk_sort(args: argparse.Namespace, entries: list[dict]) -> int:
    """Sort the rated block, keeping the TBR block pinned at the end.

    The TBR block is a structural rule, not an ordering preference, so it does
    not move whatever direction the sort runs in. Splitting first also means
    the sort key never sees an unrated entry.
    """
    if args.cat == "movies":
        return A.fail(
            "movies have exactly one valid order, ascending by date_watched, "
            "and they are already in it. There is no sort to apply."
        )
    rated = [entry for entry in entries if entry["rating_text"]]
    tbr = [entry for entry in entries if not entry["rating_text"]]
    rated.sort(key=SORT_KEYS[args.sort], reverse=args.descending)
    A.save(args.cat, rated + tbr)
    direction = " desc" if args.descending else ""
    print(f"sorted {args.cat} by {args.sort}{direction}:")
    print(A.listing(A.load(args.cat)))
    return 0


def rename(args: argparse.Namespace, entries: list[dict], index: int) -> int:
    """Replace the title in place. Position is unaffected."""
    previous = entries[index]["title"]
    entries[index]["title"] = args.rename
    A.save(args.cat, entries)
    fresh = A.load(args.cat)
    renamed = fresh[A.exact(fresh, args.rename)]
    print("renamed:")
    print(f"  {previous!r} -> {args.rename!r}  (now id {renamed['id']})")
    return 0


def reposition(args: argparse.Namespace, entries: list[dict], index: int) -> int:
    """Move one entry to the place the user named."""
    original = entries[index]["title"]
    if args.position is not None:
        target, reason = args.position - 1, f"position {args.position}"
    elif args.before:
        found = anchor(args.cat, entries, args.before, "--before", args.exact)
        if found is None:
            return 1
        target, reason = found, f"before {entries[found]['title']!r}"
    elif args.after:
        found = anchor(args.cat, entries, args.after, "--after", args.exact)
        if found is None:
            return 1
        target, reason = found + 1, f"after {entries[found]['title']!r}"
    else:
        return A.fail("pass --position, --before, or --after.")

    # archive.move takes the destination in the resulting list and compensates
    # for the pop itself, so no adjustment is needed here.
    A.save(args.cat, A.move(entries, index, target))

    # Look the entry up again to report the new id: every entry below the move
    # shifts by one, so comparing old and new positions is wrong.
    fresh = A.load(args.cat)
    moved = fresh[A.exact(fresh, original)]
    print(f"moved: {original!r}")
    print(f"  was id {index + 1}, now id {moved['id']}  ({reason})")
    return 0


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)

    if args.sort:
        return bulk_sort(args, entries)
    if not args.title:
        return A.fail("pass --title, or --sort for a bulk sort.")

    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1

    if args.rename:
        return rename(args, entries, index)
    return reposition(args, entries, index)


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
