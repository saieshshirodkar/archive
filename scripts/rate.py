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
    hits = A.find(entries, args.title)
    if not hits:
        print(f"error: nothing in {args.cat} matches {args.title!r}.", file=sys.stderr)
        return 1
    if len(hits) > 1:
        print(f"error: {len(hits)} matches in {args.cat}, be more specific:", file=sys.stderr)
        for i in hits:
            print("  " + A.describe(entries[i]), file=sys.stderr)
        return 1

    index = hits[0]
    entry = entries[index]
    was_tbr = not entry["rating_text"]
    rating = A.normalise_rating(args.rating)

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