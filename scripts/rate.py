#!/usr/bin/env python3
"""Rate an existing entry, optionally moving it.

Two modes, matching the archive's rules:

* currently TBR (empty rating) -> set the rating and move it to just after the
  last rated entry. This is the documented default, confirmed 30-09-2026.
* already rated -> change the rating in place. Pass --move to reposition it
  anyway, which is what fixes a rated entry stranded in the TBR block.

Examples
--------
    python3 scripts/rate.py --cat books --title "housemaid is watching" --rating 7.5
    python3 scripts/rate.py --cat animanga --title "code geass" --rating 9
    python3 scripts/rate.py --cat shows --title "Raakh" --rating 8.3 --move
"""

from __future__ import annotations

import argparse
import sys

import archive as A


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rate an entry in the archive.")
    parser.add_argument("--cat", required=True, choices=A.category_ids())
    parser.add_argument("--title", required=True, help="substring match is fine")
    parser.add_argument(
        "--exact",
        action="store_true",
        help="require a whole-title match; needed for short titles that are a "
        "substring of another entry (Baki, Bastard)",
    )
    parser.add_argument("--rating", required=True, help='like "8" or "8.5"')
    parser.add_argument(
        "--move",
        action="store_true",
        help="force the entry after the last rated one even if already rated",
    )
    parser.add_argument(
        "--position",
        type=int,
        default=None,
        help="move to this exact id position instead (overrides the default rule)",
    )
    return parser


def reposition(
    args: argparse.Namespace, entries: list[dict], index: int
) -> tuple[list[dict], str]:
    """Reorder for this rating, returning the list and a short reason.

    Movement is decided *before* the rating is written. Writing it first makes
    the entry count itself as the last rated one, so the target equals its
    current position and the move silently does nothing. ``exclude=index``
    covers the same trap for an entry that already carries a rating and sits
    below the block, which is what --move exists for.
    """
    if args.position is not None:
        moved = A.move(entries, index, args.position - 1)
        return moved, f"moved to position {args.position}"
    if args.cat == "movies":
        return entries, "in place (movies are date-sorted)"
    if entries[index]["rating_text"] and not args.move:
        return entries, "in place (already rated)"
    target = A.last_rated_index(entries, exclude=index) + 1
    return A.move(entries, index, target), "moved after last rated"


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1

    # Validate the rating before mutating anything, so a typo cannot half-apply.
    try:
        rating = A.normalise_rating(args.rating)
    except ValueError as exc:
        return A.fail(str(exc))

    # Keep the dict itself, not the index: reposition() may move it, and the
    # object identity survives the move.
    entry = entries[index]
    entries, reason = reposition(args, entries, index)
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
