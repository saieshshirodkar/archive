#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

import archive as A

SORT_NAMES = ("title", "rating", "year", "id")
SORT_KEYS: dict[str, Callable[[dict], Any]] = {
    "title": lambda e: e["title"].lower(),
    "rating": lambda e: float(e["rating_text"].split("/")[0]),
    "year": lambda e: e.get("year") or 0,
    "id": lambda e: e["id"],
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Reorder or rename entries.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", default=None)
    p.add_argument("--before", default=None)
    p.add_argument("--after", default=None)
    p.add_argument("--position", type=int, default=None)
    p.add_argument("--rename", default=None)
    p.add_argument("--exact", action="store_true")
    p.add_argument("--sort", default=None, choices=SORT_NAMES)
    p.add_argument("--descending", action="store_true")
    return p


def anchor(
    cat: str, entries: list[dict], needle: str, flag: str, strict: bool
) -> int | None:
    index = A.resolve_index(entries, needle, strict=strict)
    if index is None:
        A.report_no_match(entries, needle, cat, flag, strict)
    return index


def anchor_target(index: int, found: int, mode: str) -> int:
    """Final index for the moved entry, given the anchor's index before the move."""
    if mode == "before":
        return found - 1 if index < found else found
    return found if index < found else found + 1


def bulk_sort(args: argparse.Namespace, entries: list[dict]) -> int:
    if args.cat == "movies":
        return A.fail("movies are sorted by date_watched; no sort applies.")
    entries.sort(key=SORT_KEYS[args.sort], reverse=args.descending)
    A.save(args.cat, entries)
    direction = " desc" if args.descending else ""
    print(f"sorted {args.cat} by {args.sort}{direction}:")
    print(A.listing(A.load(args.cat)))
    return 0


def rename(args: argparse.Namespace, entries: list[dict], index: int) -> int:
    entry = entries[index]
    prev = entry["title"]
    new = args.rename.strip()
    if not new:
        return A.fail("rename needs a non-empty title.")
    clash = next(
        (
            i
            for i, e in enumerate(entries)
            if i != index and e["title"].lower() == new.lower()
        ),
        None,
    )
    if clash is not None:
        return A.fail(f"{new!r} is already used by id {clash + 1} in {args.cat}.")
    entry["title"] = new
    A.save(args.cat, entries)
    fresh = A.load(args.cat)
    print("renamed:")
    print(f"  {prev!r} -> {new!r}  (now id {A.index_of(fresh, new) + 1})")
    return 0


def reposition(args: argparse.Namespace, entries: list[dict], index: int) -> int:
    original = entries[index]["title"]
    if args.position is not None:
        target, reason = args.position - 1, f"position {args.position}"
    elif args.before:
        found = anchor(args.cat, entries, args.before, "--before", args.exact)
        if found is None:
            return 1
        target = anchor_target(index, found, "before")
        reason = f"before {entries[found]['title']!r}"
    elif args.after:
        found = anchor(args.cat, entries, args.after, "--after", args.exact)
        if found is None:
            return 1
        target = anchor_target(index, found, "after")
        reason = f"after {entries[found]['title']!r}"
    else:
        return A.fail("pass --position, --before, or --after.")
    A.save(args.cat, A.move(entries, index, target))
    fresh = A.load(args.cat)
    moved = fresh[A.index_of(fresh, original)]
    print(f"moved: {original!r}")
    print(f"  was id {index + 1}, now id {moved['id']}  ({reason})")
    return 0


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    if args.sort:
        return bulk_sort(args, entries)
    if not args.title:
        return A.fail("pass --title, or --sort for a bulk sort.")
    if args.cat == "movies" and (
        args.position is not None or args.before or args.after
    ):
        return A.fail(
            "movies are ordered by date_watched; use "
            "'rate.py --cat movies --date DD-MM-YYYY' to move one."
        )
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
