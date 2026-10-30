#!/usr/bin/env python3
"""Rate an existing entry, optionally moving it.

Two modes, matching the archive's rules:

* Entry currently TBR (empty rating) -> set the rating and move it to just
  after the last rated entry. This is the documented default, confirmed by
  the user on 30-09-2026.
* Entry already rated -> change the rating in place, no movement. Use --move
  to override that and reposition a rated entry.

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


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Rate an entry in the archive.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", required=True, help="substring match is fine")
    p.add_argument(
        "--exact",
        action="store_true",
        help="require a whole-title match; needed for short titles that are a "
        "substring of another entry (Baki, Bastard)",
    )
    p.add_argument("--rating", required=True, help='like "8" or "8.5"')
    p.add_argument(
        "--move",
        action="store_true",
        help="force the entry after the last rated one even if already rated",
    )
    p.add_argument(
        "--position",
        type=int,
        default=None,
        help="move to this exact id position instead (overrides the default rule)",
    )
    args = p.parse_args(argv)

    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1

    entry = entries[index]
    was_tbr = not entry["rating_text"]
    try:
        rating = A.normalise_rating(args.rating)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Decide movement BEFORE writing the rating. Setting rating_text first
    # would make the entry count itself as the last rated one, computing a
    # target one position too far and stranding it inside the TBR block.
    if args.position is not None:
        reason = f"moved to position {args.position}"
        entries = A.move(entries, index, args.position - 1)
    elif args.cat == "movies":
        # movies are sorted by date_watched, so a rating never moves anything
        reason = "in place (movies are date-sorted)"
    elif was_tbr or args.move:
        # target is the last rated index + 1, measured before this entry gains
        # a rating, so the entry lands immediately after the existing block
        reason = "moved after last rated"
        entries = A.move(entries, index, A.last_rated_index(entries) + 1)
    else:
        reason = "in place (already rated)"

    entry["rating_text"] = rating

    A.save(args.cat, entries)

    fresh = A.load(args.cat)
    idx = A.exact(fresh, entry["title"])
    print(f"rated: {A.describe(fresh[idx])}")
    print(f"  {reason}; {args.cat} has {len(fresh)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))