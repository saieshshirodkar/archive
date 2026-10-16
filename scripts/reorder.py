#!/usr/bin/env python3
"""Move, reorder, or rename an entry without changing its rating.

Reordering is how the shows list gets built: the user says "put X before Y"
and this does it. Also supports bulk sorts for the categories where a
canonical order is actually wanted.

Examples
--------
    # put a show before another by title
    python3 scripts/reorder.py --cat shows --title "Malcolm in the Middle" \\
        --before "The Walking Dead"

    # exact position by current id
    python3 scripts/reorder.py --cat shows --title "Raakh" --position 2

    # bulk sort (books/animanga/shows only; movies are date-sorted)
    python3 scripts/reorder.py --cat shows --sort title
    python3 scripts/reorder.py --cat books --sort rating --descending
    python3 scripts/reorder.py --cat books --sort year
"""

from __future__ import annotations

import argparse
import re
import sys

import archive as A


def rating_value(entry: dict) -> float:
    """Numeric part of a rating, for sorting. Unrated entries sort last."""
    text = entry.get("rating_text") or ""
    if not text:
        return -1.0
    return float(text.split("/")[0])


def sort_key(name: str, descending: bool):
    """Build a sort key function for one of: title, rating, year, id."""

    def key(entry: dict):
        if name == "title":
            value = entry["title"].lower()
        elif name == "rating":
            value = rating_value(entry)
        elif name == "year":
            value = entry.get("year") or 0
        elif name == "id":
            value = entry["id"]
        else:
            raise ValueError(f"unknown sort {name}")
        # Negating a number flips the order without reversing strings, which
        # would break the alphabetical case. Sentinels use tuple (is_real, value).
        return (-value if descending else value) if isinstance(value, (int, float)) else value

    return key


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Reorder or rename entries.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", default=None, help="entry to move or rename")
    p.add_argument("--before", default=None, help="move this entry before that one")
    p.add_argument("--after", default=None, help="move this entry after that one")
    p.add_argument("--position", type=int, default=None, help="move to this id position")
    p.add_argument("--rename", default=None, help="new title for --title")
    p.add_argument("--sort", default=None, choices=["title", "rating", "year", "id"])
    p.add_argument("--descending", action="store_true", help="with --sort")
    args = p.parse_args(argv)

    entries = A.load(args.cat)
    before_snapshot = [(e["id"], e["title"]) for e in entries]

    # --- bulk sort mode ---
    if args.sort:
        if args.cat == "movies":
            print(
                "error: movies are sorted by date_watched; sort those with "
                "reorder.py --cat movies --sort date.",
                file=sys.stderr,
            )
            return 1
        # Always keep the TBR block at the end regardless of sort direction,
        # because the block is a structural rule, not an ordering preference.
        rated = [e for e in entries if e["rating_text"]]
        tbr = [e for e in entries if not e["rating_text"]]
        rated.sort(key=sort_key(args.sort, args.descending))
        entries = rated + tbr
        A.save(args.cat, entries)
        print(f"sorted {args.cat} by {args.sort}{' desc' if args.descending else ''}:")
        for e in A.load(args.cat):
            print("  " + A.describe(e))
        return 0

    if not args.title:
        print("error: pass --title, or --sort for a bulk sort.", file=sys.stderr)
        return 1

    hits = A.find(entries, args.title)
    if len(hits) != 1:
        print(f"error: {len(hits)} matches for {args.title!r}.", file=sys.stderr)
        for i in hits:
            print("  " + A.describe(entries[i]), file=sys.stderr)
        return 1
    index = hits[0]
    original = entries[index]["title"]

    # --- rename ---
    if args.rename:
        entries[index]["title"] = args.rename
        A.save(args.cat, entries)
        fresh = A.load(args.cat)
        idx = A.exact(fresh, args.rename)
        print("renamed:")
        print(f"  {original!r} -> {args.rename!r}  (now id {fresh[idx]['id']})")
        return 0

    # --- move ---
    target = None
    if args.position is not None:
        target = args.position - 1
        reason = f"position {args.position}"
    elif args.before:
        anchor = A.find(entries, args.before)
        if len(anchor) != 1:
            print(f"error: {len(anchor)} matches for --before {args.before!r}.", file=sys.stderr)
            return 1
        target = anchor[0]
        reason = f"before {entries[anchor[0]]['title']!r}"
    elif args.after:
        anchor = A.find(entries, args.after)
        if len(anchor) != 1:
            print(f"error: {len(anchor)} matches for --after {args.after!r}.", file=sys.stderr)
            return 1
        target = anchor[0] + 1
        reason = f"after {entries[anchor[0]]['title']!r}"
    else:
        print("error: pass --position, --before, or --after.", file=sys.stderr)
        return 1

    # Move the entry to where the user named. Because removal shifts everything
    # below it, the target is recomputed after the pop inside archive.move.
    entries = A.move(entries, index, target)
    A.save(args.cat, entries)

    fresh = A.load(args.cat)
    # Report the new id by looking the entry up again. Comparing positions in
    # the old and new lists is wrong: every entry below the move shifts by one.
    old_id = index + 1
    new_index = A.exact(fresh, original)
    print(f"moved: {original!r}")
    print(f"  was id {old_id}, now id {fresh[new_index]['id']}  ({reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))