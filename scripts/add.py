#!/usr/bin/env python3
"""Add an entry to any archive category.

Every add goes through the same path: load, check the title is not already
present, decide where the entry belongs, insert, renumber, validate.

Position follows the category's ordering rule:

* movies      -> sorted by date_watched, oldest first, so a plain append then
                 re-sort. Missing --date means today in IST.
* others      -> rated entries first in insertion order, then the TBR block.
                 A new rated entry lands after the last rated entry; a new
                 unrated entry (rating omitted) goes at the very end.

Examples
--------
    python3 scripts/add.py --cat books --title "Dune" --author "Frank Herbert" \\
        --year 1965 --rating 9.5

    python3 scripts/add.py --cat shows --title "Severance" --year 2022

    python3 scripts/add.py --cat movies --title "Dune" --year 2021 --rating 8
"""

from __future__ import annotations

import argparse
import sys

import archive as A


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Add an entry to the archive.")
    p.add_argument("--cat", required=True, choices=A.category_ids(), help="category")
    p.add_argument("--title", required=True, help="exact title as it should appear")
    p.add_argument("--year", type=int, required=True, help="release/publication year")
    p.add_argument(
        "--rating",
        default=None,
        help='rating like "8" or "8.5"; omit for TBR. Stored as X/10.',
    )
    p.add_argument("--author", default=None, help="books and animanga only")
    p.add_argument(
        "--date",
        default=None,
        help="movies only, DD-MM-YYYY. Defaults to today in IST.",
    )
    p.add_argument(
        "--slug",
        default=None,
        help="cover filename stem. Defaults to a kebab-cased title.",
    )
    p.add_argument(
        "--cover",
        default=None,
        help="existing cover filename inside the category's cover folder. "
        "Omit to derive it from the slug.",
    )
    return p


def die(message: str) -> int:
    """Print a clean error and return an exit code.

    Rating problems raise ValueError from archive.normalise_rating, which
    prints a traceback. A bad flag should read as a bad flag, not a crash.
    """
    print(f"error: {message}", file=sys.stderr)
    return 1


def slugify(title: str) -> str:
    """Kebab-case a title for the cover filename.

    Drops apostrophes rather than encoding them (Takopi's -> takopis), and
    drops all other punctuation including colons and exclamation marks.
    """
    out = []
    for ch in title.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
        # everything else, including ' : ! , is dropped
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    # Validate the rating before touching anything, so a typo cannot half-apply.
    # Normalised once here and reused below, rather than parsing twice.
    try:
        rating = "" if args.rating is None else A.normalise_rating(args.rating)
    except ValueError as exc:
        return die(str(exc))

    entries = A.load(args.cat)

    # Refuse a duplicate title rather than silently adding a second copy.
    # An entry being rated is a stronger signal than one being added to the
    # TBR block, so near-matches there are a hard error; for a new TBR entry
    # they are only worth a note, since titles that are near-misses of each
    # other are the normal case (Baki vs Baki Hanma, Verity novel vs film).
    hits = A.find(entries, args.title)
    if args.cat == "movies" or args.rating is not None:
        if A.exact(entries, args.title) is not None:
            print(f"error: {args.title!r} already exists in {args.cat}.", file=sys.stderr)
            return 1
    elif hits:
        print(f"note: possible existing match for {args.title!r}:", file=sys.stderr)
        for i in hits:
            print("  " + A.describe(entries[i]), file=sys.stderr)

    year = args.year
    stem = args.slug or slugify(args.title)
    cover_file = args.cover or f"{stem}.webp"
    cover_url = f"assets/covers/{A.covers_dir(args.cat).name}/{cover_file}"

    # Refuse to add an entry whose cover is not actually on disk. This catches
    # a wrong slug or a typo'd --cover before the card renders as a grey box.
    cover_path = A.COVERS_DIR / A.CATEGORIES[args.cat]["folder"] / cover_file
    if not cover_path.exists():
        print(
            f"error: cover not found: {cover_path}\n"
            f"       download and resize it first, or pass --cover with the "
            f"correct filename.",
            file=sys.stderr,
        )
        return 1

    entry: dict = {"title": args.title, "rating_text": rating, "cover_url": cover_url}

    # author and date_watched are category-specific; shows deliberately have
    # neither because a show has many creators and no single watch date.
    if args.cat in ("books", "animanga"):
        if not args.author:
            print(f"error: {args.cat} entries require --author.", file=sys.stderr)
            return 1
        entry["author"] = args.author
    elif args.cat == "movies":
        entry["date_watched"] = args.date or A.today()
        if args.date:
            A.parse_watched(args.date)  # validate format early
    elif args.author:
        print("note: shows take no --author, ignoring.", file=sys.stderr)

    # year sits last in the book/animanga/show key order; normalise() fixes
    # the ordering so it can be assigned in any order here.
    entry["year"] = year

    # Insert at the right place for this category's ordering rule.
    if args.cat == "movies":
        entries.append(entry)
        entries.sort(key=lambda e: A.parse_watched(e["date_watched"]))
    elif rating:
        entries.insert(A.last_rated_index(entries) + 1, entry)
    else:
        entries.append(entry)

    A.save(args.cat, entries)

    # report what actually landed, including the renumbered id
    fresh = A.load(args.cat)
    idx = A.exact(fresh, args.title)
    print("added:")
    print("  " + A.describe(fresh[idx]))
    print(f"  {args.cat} now has {len(fresh)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))